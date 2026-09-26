"""CLI for managed landmark recipes/bundles and isolated official Cooker checks."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ModTools_5_4.project.civ6proj_generator import is_art_source_path
from ModTools_5_4.artdef_parser import get_district_entry_element, get_improvement_entry_element
from ModTools_5_4.project.landmarks import (
    SDKIndex, LocalResourceIndex, compose, load_bundle, validate_assets, validate_local_sources, text_at,
)
from .merger import load_civ, save_civ


def verify_bundle(manifest: Path, sdk_assets: Path | None = None, project: Path | None = None) -> dict:
    data, files = load_bundle(manifest)
    assets = {Path(name).stem: ET.fromstring(content) for name, content in files.items() if name.endswith('.ast')}
    index = LocalResourceIndex(manifest.parent, files, SDKIndex(sdk_assets) if sdk_assets else None)
    errors = validate_assets(assets, index if sdk_assets else None)
    errors += validate_local_sources(manifest.parent, files, index) if data['version'] == 2 else []
    xlp = ET.fromstring(files['XLPs/tilebases.xlp'])
    entries = [(text_at(e, 'm_EntryID'), text_at(e, 'm_ObjectName')) for e in xlp.findall('./m_Entries/Element')]
    if set(entries) != {(name, name) for name in assets} or len(entries) != len(assets):
        errors.append('XLP must register every AST exactly once with matching EntryID/ObjectName')
    landmarks = ET.fromstring(files['ArtDefs/Landmarks.artdef'])
    for p in landmarks.findall('.//Element[@class="AssetObjects..BLPEntryValue"]'):
        if text_at(p, 'm_EntryName') not in assets:
            errors.append('Landmarks references unknown asset ' + text_at(p, 'm_EntryName'))
    for binding in data['bindings']:
        coll = 'Districts' if binding['kind'] == 'district' else 'Landmarks'
        collection = next((c for c in landmarks.findall('./m_RootCollections/Element') if text_at(c, 'm_CollectionName') == coll), None)
        if collection is None or binding['landmark'] not in {text_at(e, 'm_Name') for e in collection.findall('Element')}:
            errors.append(f"Missing landmark {binding['landmark']}")
    if project:
        for name, content in files.items():
            p = project / name
            if name == 'ArtDefs/Buildings.artdef' and p.exists():
                # Supplemental built-in entries coexist with this mod's buildings.
                exported = ET.parse(p).getroot()
                entries_by_name = {text_at(e, 'm_Name'): e for e in exported.findall('./m_RootCollections/Element/Element')}
                for e in ET.fromstring(content).findall('./m_RootCollections/Element/Element'):
                    building = text_at(e, 'm_Name')
                    actual = entries_by_name.get(building)
                    if actual is None:
                        errors.append('Missing supplemental building: ' + building)
                        continue
                    fields = {text_at(p, 'm_ParamName'): p for p in actual.findall('./m_Fields/m_Values/Element')}
                    for expected in e.findall('./m_Fields/m_Values/Element'):
                        name = text_at(expected, 'm_ParamName')
                        field = fields.get(name)
                        if field is None or field.get('class') != expected.get('class') or any(
                            field.findtext(value.tag) != value.text
                            for value in expected if value.tag != 'm_ParamName'
                        ):
                            errors.append(f'Invalid supplemental building field: {building}.{name}')
                continue
            if not p.exists() or (p.read_bytes() if isinstance(content, bytes) else p.read_text(encoding='utf-8-sig')) != content:
                errors.append(f'Generated project differs from bundle: {name}')
        for binding in data['bindings']:
            path = project / 'ArtDefs' / ('Districts.artdef' if binding['kind'] == 'district' else 'Improvements.artdef')
            if not path.exists():
                errors.append(f'Missing {path.name}'); continue
            root = ET.parse(path).getroot()
            entry = next((e for e in root.findall('./m_RootCollections/Element/Element') if text_at(e, 'm_Name') == binding['entity']), None)
            refs = [] if entry is None else [p for p in entry.findall('.//Element[@class="AssetObjects..ArtDefReferenceValue"]') if text_at(p, 'm_ParamName') == 'Xref' and text_at(p, 'm_ArtDefPath') == 'Landmarks.artdef']
            if len(refs) != 1 or text_at(refs[0], 'm_ElementName') != binding['landmark']:
                errors.append(f"Broken entity -> Landmark binding: {binding['entity']}")
        projects = list(project.glob('*.civ6proj'))
        if len(projects) != 1:
            errors.append('Expected exactly one civ6proj')
        else:
            for item in ET.parse(projects[0]).iter():
                if item.tag.rsplit('}', 1)[-1] in {'Content', 'Folder', 'None'} and is_art_source_path(item.get('Include', '')):
                    errors.append('civ6proj must not register art source: ' + item.get('Include', ''))
        art_files = list(project.glob('*.Art.xml'))
        if len(art_files) != 1:
            errors.append('Expected exactly one Art.xml')
        else:
            root = ET.parse(art_files[0]).getroot()
            # Check within the specific library/consumer; unrelated occurrences
            # elsewhere in the document do not satisfy this linkage.
            lib = next((e for e in root.findall('./gameLibraries/Element') if text_at(e, 'libraryName') == 'TileBase'), None)
            if lib is None or not any(e.get('text') == 'landmarks/tilebases' or e.text == 'landmarks/tilebases' for e in lib.iter()):
                errors.append('Art.xml TileBase library lacks landmarks/tilebases')
            actual_ids = {text_at(e, 'id') for e in root.findall('./requiredGameArtIDs/Element')}
            for identity in data.get('required_game_art_ids', []):
                if identity['id'] not in actual_ids:
                    errors.append('Art.xml missing SDK dependency: ' + identity['name'])
            consumer = next((e for e in root.findall('./artConsumers/Element') if text_at(e, 'consumerName') == 'Landmarks'), None)
            if consumer is None or not any(e.get('text') == 'Landmarks.artdef' for e in consumer.findall('./relativeArtDefPaths/Element')) or not any(e.get('text') == 'TileBase' for e in consumer.findall('./libraryDependencies/Element')):
                errors.append('Art.xml Landmarks consumer is incomplete')

    return {'ok': not errors, 'assets': len(assets), 'bindings': len(data['bindings']), 'errors': errors}


def import_bundle(civ: Path, manifest: Path, *, replace: bool = False, dry_run: bool = False) -> dict:
    report = verify_bundle(manifest)
    if not report['ok']:
        raise ValueError('\n'.join(report['errors']))
    data, _ = load_bundle(manifest)
    payload = load_civ(civ)
    workspace = payload['workspace']
    art = workspace.setdefault('美术', {})
    state = art.setdefault('data', {}) if 'data' in art or not art else art
    current = state.get('landmark_bundle')
    path = str(manifest.resolve())
    if current and current.get('manifest') != path and not replace:
        raise ValueError('CIV already has a landmark bundle; use --replace to switch it')
    for binding in data['bindings']:
        # Entity sections can be list or wrapped entries; gather type strings
        # without making assumptions about unrelated editor metadata.
        section = workspace.get('区域' if binding['kind'] == 'district' else '改良设施')
        if not isinstance(section, list) or not any(isinstance(entry, dict) and entry.get('type') == binding['entity'] for entry in section):
            raise ValueError(f"CIV does not contain entity {binding['entity']}")
        reader = get_district_entry_element if binding['kind'] == 'district' else get_improvement_entry_element
        if reader(binding['source']) is None:
            raise ValueError(f"ArtDef source not found: {binding['source']}")
        key = binding['kind'] + ':' + binding['entity']
        state.setdefault('source_map', {})[key] = binding['source']
        state.setdefault('need_map', {})[key] = True
    for config_key in ('art_xml_source_config', 'art_xml_workspace_config'):
        config = state.setdefault(config_key, {})
        required = config.setdefault('required_game_art_ids', [])
        known = {item.get('id') for item in required}
        for identity in data.get('required_game_art_ids', []):
            if identity['id'] not in known:
                required.append(dict(identity)); known.add(identity['id'])
    state['landmark_bundle'] = {'manifest': path}
    state.setdefault('extra_xlp_flags', {})['tilebases.xlp'] = True
    state.setdefault('extra_artdef_flags', {})['Landmarks.artdef'] = True
    if not dry_run:
        save_civ(civ, payload)
    return {**report, 'dry_run': dry_run, 'manifest': path}


def cook_bundle(manifest: Path, sdk_assets: Path, sdk: Path, output: Path, project: Path | None = None) -> dict:
    """Stage to ASCII because the official Cooker corrupts non-ASCII pantry paths.

    No game deployment and no full mod build. Logs and staged files remain for
    diagnosis. Each run uses a new directory, so old BLPs cannot fake success.
    """
    report = verify_bundle(manifest, sdk_assets, project)
    if not report['ok']:
        raise ValueError('\n'.join(report['errors']))
    _, files = load_bundle(manifest)
    stage = Path(tempfile.mkdtemp(prefix='civ6-landmarks-'))
    if not str(stage).isascii():
        raise ValueError('Official Cooker needs an ASCII temporary directory; set TMP/TEMP to one')
    pantry = stage / 'pantry'; pantry.mkdir()
    for name, content in files.items():
        path = pantry / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content) if isinstance(content, bytes) else path.write_text(content, encoding='utf-8')
    if project:
        # Include entity/Art.xml references, without copying textures or running
        # their XLPs. This validates this task's art in the real mod context.
        for path in (project / 'ArtDefs').glob('*.artdef'):
            if path.name != 'Landmarks.artdef':
                shutil.copy2(path, pantry / 'ArtDefs' / path.name)
        for path in project.glob('*.Art.xml'):
            shutil.copy2(path, pantry / path.name)
    cooker = sdk / 'AssetModTools/Cooker'
    executable = cooker / 'Civ6AssetCooker_FinalRelease.exe'
    if not executable.is_file():
        raise ValueError(f'Missing official Cooker: {executable}')
    pantries = [sdk_assets / 'Civ6/pantry', sdk_assets / 'Civ6/DLC/Shared/pantry',
                sdk_assets / 'Civ6/DLC/Expansion1/pantry', sdk_assets / 'Civ6/DLC/Expansion2/pantry']
    common = [str(executable), '--absolute_paths', '--no_mt', '--platform', 'Windows', '--pantry', str(pantry)]
    for path in pantries:
        if path.exists():
            common.extend(['--pantry', str(path)])
    common += ['--config', str(cooker / 'Civ6.cfg')]
    runs = []
    targets = [('XLP', 'XLPs/tilebases.xlp', '--stewpot', 'BLPs', 'BLPs/landmarks/tilebases.blp')]
    targets += [('ArtDef', 'ArtDefs/' + name + '.artdef', '--banquet_hall', 'ArtDefs', 'ArtDefs/' + name + '.artdef') for name in ('Landmarks', 'Districts', 'Improvements') if (pantry / ('ArtDefs/' + name + '.artdef')).exists()]
    for mode, relative, flag, directory, expected in targets:
        destination = stage / 'cooked' / directory; destination.mkdir(parents=True, exist_ok=True)
        cmd = common + ['--mode', mode, flag, str(destination), str(pantry / relative)]
        process = subprocess.run(cmd, cwd=cooker, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        log = process.stdout.decode('utf-8', errors='replace')
        log_path = stage / (Path(relative).stem + '-' + mode + '.log')
        log_path.write_text(log, encoding='utf-8')
        artifact = stage / 'cooked' / expected
        failures = [line.strip() for line in log.splitlines() if re.search(r'\b(error|failed|failure)\b|could not find|could not load.*(?:asset|geometry|material)|does not exist|Unable to (?:load|open)', line, re.I)]
        warnings = [line.strip() for line in log.splitlines() if re.search(r'warn|empty OB|Geometry is required|Unable to find|Unable to auto-generate', line, re.I)]
        runs.append({'target': relative, 'exit_code': process.returncode, 'artifact': expected,
                     'bytes': artifact.stat().st_size if artifact.exists() else 0,
                     'errors': failures, 'warnings': warnings})
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(stage / 'cooked', output / 'cooked', dirs_exist_ok=True)
    for log in stage.glob('*.log'):
        shutil.copy2(log, output / log.name)
    result = {'ok': all(r['exit_code'] == 0 and r['bytes'] > 0 and not r['errors'] for r in runs),
              'stage': str(stage), 'runs': runs, 'visual_verified': False}
    (output / 'cook-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def command(args) -> int:
    operation = args.landmark_operation
    if operation == 'catalog':
        result = SDKIndex(Path(args.sdk_assets)).catalog(args.query)
    elif operation == 'compose':
        result = {'manifest': str(compose(Path(args.recipe), Path(args.sdk_assets), Path(args.out)))}
    elif operation == 'import':
        result = import_bundle(Path(args.civ), Path(args.bundle), replace=args.replace, dry_run=args.dry_run)
    elif operation == 'verify':
        result = verify_bundle(Path(args.bundle), Path(args.sdk_assets) if args.sdk_assets else None, Path(args.project) if args.project else None)
    else:
        result = cook_bundle(Path(args.bundle), Path(args.sdk_assets), Path(args.sdk), Path(args.out), Path(args.project) if args.project else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not isinstance(result, dict) or result.get('ok', True) else 1


def add_parser(sub):
    parser = sub.add_parser('landmark', help='静态地标 AST、官方/本地模型资源包、引用链校验和隔离 Cooker')
    ops = parser.add_subparsers(dest='landmark_operation', required=True)
    catalog = ops.add_parser('catalog', help='只读检索 SDK TileBase AST')
    catalog.add_argument('--sdk-assets', required=True)
    catalog.add_argument('--query', default='')
    compose_parser = ops.add_parser('compose', help='从 JSON 配方生成托管 AST/XLP/Landmarks 资源包')
    compose_parser.add_argument('--recipe', required=True)
    compose_parser.add_argument('--sdk-assets', required=True)
    compose_parser.add_argument('--out', required=True)
    imp = ops.add_parser('import', help='校验后将资源包登记到 CIV，自动备份')
    imp.add_argument('civ'); imp.add_argument('--bundle', required=True)
    imp.add_argument('--replace', action='store_true'); imp.add_argument('--dry-run', action='store_true')
    verify = ops.add_parser('verify', help='校验包、可选 SDK 和已导出 ModBuddy 引用链')
    verify.add_argument('--bundle', required=True); verify.add_argument('--sdk-assets'); verify.add_argument('--project')
    cook = ops.add_parser('cook', help='ASCII 暂存目录运行官方 Cooker，不部署游戏')
    for flag in ('bundle', 'sdk-assets', 'sdk', 'out'):
        cook.add_argument('--' + flag, required=True)
    cook.add_argument('--project')
    for parser in (catalog, compose_parser, imp, verify, cook):
        parser.set_defaults(func=command)
