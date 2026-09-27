"""Build offline adjacency references from official XML, never a modded cache.

Profiles include Base and the selected expansion's Core actions, in modinfo
LoadOrder/file order. Civilization packs and game modes are deliberately not
enabled implicitly. Their two non-unique districts are listed separately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

TABLES = {'Districts': ('DistrictType',), 'Adjacency_YieldChanges': ('ID',),
          'District_Adjacencies': ('DistrictType', 'YieldChangeId'),
          'Improvement_Adjacencies': ('ImprovementType', 'YieldChangeId')}
DEFAULT_OUT = Path(__file__).resolve().parents[2] / 'ModTools_5_4/data/vanilla_adjacencies.json'


def values(node):
    raw = dict(node.attrib)
    raw.update({child.tag: child.text for child in node})
    def typed(value):
        if value in ('true', 'false'): return value == 'true'
        try: return int(value)
        except (TypeError, ValueError): return value
    return {k: typed(v) for k, v in raw.items()}


def apply_xml(tables, root, source, origins):
    """Apply the actual Row/Update/Delete operations, including FK cascades."""
    for block in root:
        if block.tag not in TABLES: continue
        rows = tables[block.tag]
        keys = TABLES[block.tag]
        for operation in block:
            op = operation.tag
            if op in ('Row', 'Replace'):
                row = values(operation); key = tuple(row[k] for k in keys)
                if key in rows and op == 'Row':
                    raise ValueError(f'Duplicate {block.tag}{key} in {source}')
                rows[key] = row
                origins[(block.tag, key)] = source
            elif op in ('Update', 'Delete'):
                where = operation.find('Where') if op == 'Update' else operation
                if where is None: raise ValueError(f'Missing Where in {source}')
                conditions = values(where)
                selected = [key for key, row in rows.items()
                            if all(row.get(k) == v for k, v in conditions.items())]
                for key in selected:
                    if op == 'Update':
                        setting = operation.find('Set')
                        if setting is None: raise ValueError(f'Missing Set in {source}')
                        rows[key].update(values(setting))
                        origins[(block.tag, key)] = source
                    else:
                        del rows[key]
                        if block.tag == 'Adjacency_YieldChanges':
                            for bridge in ('District_Adjacencies', 'Improvement_Adjacencies'):
                                for bkey in list(tables[bridge]):
                                    if bkey[1] == key[0]: del tables[bridge][bkey]
            else:
                raise ValueError(f'Unsupported XML operation {op} in {source}')


def core_files(game, expansion):
    manifest = game / 'DLC' / expansion / (expansion + '.modinfo')
    root = ET.parse(manifest).getroot()
    actions = [a for a in root.findall('./InGameActions/UpdateDatabase')
               if a.get('criteria') == expansion]
    actions.sort(key=lambda a: int(a.findtext('./Properties/LoadOrder', '0')))
    files = []
    for action in actions:
        for item in action.findall('File'):
            files.append(manifest.parent / item.text)
    return manifest, files


def extract(game):
    game = Path(game)
    base_files = [game / 'Base/Assets/Gameplay/Data' / name
                  for name in ('Districts.xml', 'Features.xml', 'Improvements.xml')]
    files_seen = {}
    profiles = {}
    for profile, expansion in [('base', None), ('expansion1', 'Expansion1'), ('expansion2', 'Expansion2')]:
        tables = {t: {} for t in TABLES}; origins = {}; files = list(base_files)
        if expansion:
            manifest, extension_files = core_files(game, expansion)
            files_seen[manifest.relative_to(game).as_posix()] = hashlib.sha256(manifest.read_bytes()).hexdigest()
            files += extension_files
        applied = []
        for path in files:
            raw = path.read_bytes(); relative = path.relative_to(game).as_posix()
            if path.suffix.lower() == '.sql':
                # Schema SQL declares the tables/columns, not adjacency rules.
                if 'Schema' not in path.parts and any(t.encode() in raw for t in TABLES if t != 'Districts'):
                    raise ValueError(f'Adjacency SQL requires explicit extractor support: {relative}')
                continue
            if path.suffix.lower() != '.xml': continue
            root = ET.fromstring(raw)
            if not any(node.tag in TABLES for node in root): continue
            apply_xml(tables, root, relative, origins)
            applied.append(relative); files_seen[relative] = hashlib.sha256(raw).hexdigest()
        definitions = {key[0]: {**row, '_source': origins[('Adjacency_YieldChanges', key)]}
                       for key, row in sorted(tables['Adjacency_YieldChanges'].items())}
        bridges = {}
        for kind, table in [('districts', 'District_Adjacencies'), ('improvements', 'Improvement_Adjacencies')]:
            links = {}
            for entity, ident in sorted(tables[table]):
                if ident not in definitions: raise ValueError(f'Undefined adjacency {ident} for {entity}')
                links.setdefault(entity, []).append(ident)
            bridges[kind] = links
        base_districts = {key[0]: {'name': row.get('Name'), 'source': origins[('Districts', key)],
                                  'adjacencies': bridges['districts'].get(key[0], [])}
                          for key, row in sorted(tables['Districts'].items()) if not row.get('TraitType')}
        profiles[profile] = {'source_order': applied, 'base_districts': base_districts,
                             **bridges, 'definitions': definitions}
    optional = {}
    for relative in ('DLC/Ethiopia/Data/Ethiopia_Districts.xml',
                     'DLC/KublaiKhan_Vietnam/Data/KublaiKhan_Vietnam_Districts.xml'):
        path = game / relative
        if not path.is_file(): continue
        root = ET.parse(path).getroot()
        for row in root.findall('./Districts/Row'):
            if row.get('TraitType'): continue
            typ = row.get('DistrictType')
            links = [r.get('YieldChangeId') for r in root.findall('./District_Adjacencies/Row') if r.get('DistrictType') == typ]
            if links: raise ValueError(f'Optional district gained adjacency; add a profile: {typ}')
            optional[typ] = {'source': relative, 'adjacencies': [], 'requires_pack': relative.split('/')[1]}
        files_seen[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'format_version': 1, 'source': 'Firaxis official game XML and expansion modinfo',
            'scope': 'Base + selected expansion Core; civilization-pack adjustments and game modes are not active in these profiles',
            'profiles': profiles, 'optional_base_districts': optional,
            'source_sha256': dict(sorted(files_seen.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', required=True, type=Path)
    parser.add_argument('--out', default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()
    data = extract(args.game_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.out), 'profiles': {k: len(v['base_districts']) for k,v in data['profiles'].items()},
                      'optional_base_districts': sorted(data['optional_base_districts'])}, ensure_ascii=False))


if __name__ == '__main__': main()
