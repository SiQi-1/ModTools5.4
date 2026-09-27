"""Read-only asset and release checks, independent of Qt and external tools.

Workflow references: 千与千寻瀑, civ6-modding-skills / audio-pipeline (S3/S4),
煎包/Jianbao233, Civ6WorkshopUploader (S5), and 千川白浪, Civ6ArtUnpack
handover (S7). Independent implementation:
XML parsing instead of regex mutation; bounded paths; incomplete evidence is
reported explicitly. See THIRD_PARTY_NOTICES.md and licenses/.
"""
from __future__ import annotations

import json
import re
import uuid
from itertools import zip_longest
import xml.etree.ElementTree as ET
from pathlib import Path

from .extensions import safe_path

ART_SUFFIXES = {".artdef", ".xlp", ".ast", ".mtl", ".geo", ".env", ".lrg", ".tex"}
AUDIO_SECTIONS = {"Global", "Menu", "InGame", "2D", "3D", "FMV"}


def report(kind, target):
    return {"kind": kind, "target": str(target), "ok": True, "errors": [],
            "warnings": [], "unverified": [], "checked": []}


def issue(result, level, message, file=None):
    item = {"message": message}
    if file is not None:
        item["file"] = str(file)
    if item not in result[level]:
        result[level].append(item)
    if level == "errors":
        result["ok"] = False


def _tag(element):
    return element.tag.rsplit("}", 1)[-1]


def _value(element, name):
    child = next((c for c in element if _tag(c) == name), None)
    return "" if child is None else child.get("text", child.text or "").strip()


def _parse(raw):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("不支持 DTD / ENTITY")
    root = ET.fromstring(raw)
    for elem in root.iter():
        elem.tag = _tag(elem)
    return root


def _xml(path, result):
    try:
        root = _parse(path.read_bytes())
        result["checked"].append(str(path))
        return root
    except (OSError, ET.ParseError, ValueError) as exc:
        issue(result, "errors", f"XML 无法读取：{exc}", path)
        return None


def _key(path):
    return str(path).replace("\\", "/").casefold()


def _resolve(base, rel, result, *, required=True):
    """Windows-friendly lookup without following symlinks outside base."""
    try:
        if not isinstance(rel, str) or not rel.strip():
            raise ValueError("空文件引用")
        rel = rel.replace("\\", "/")
        target = safe_path(base, rel)
        if not target.exists():
            # Filesystem case sensitivity varies across CI/Windows/SDK copies.
            current = base.resolve()
            for part in rel.split("/"):
                candidates = [p for p in current.iterdir() if p.name.casefold() == part.casefold()] if current.is_dir() else []
                if len(candidates) > 1:
                    raise ValueError(f"大小写歧义：{rel}")
                current = candidates[0] if candidates else current / part
                if not current.resolve().is_relative_to(base.resolve()):
                    raise ValueError(f"引用越出目录：{rel}")
            target = current
        if required and not target.is_file():
            issue(result, "errors", f"引用文件不存在：{rel}", base)
            return None
        return target
    except (OSError, ValueError) as exc:
        issue(result, "errors", f"非法文件引用 {rel!r}：{exc}", base)
        return None


def _files_under(base, result, suffixes):
    if not base.is_dir():
        issue(result, "errors", "目录不存在", base)
        return {}
    found = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        rel = path.relative_to(base).as_posix()
        safe = _resolve(base, rel, result)
        if safe is None:
            continue
        key = _key(rel)
        if key in found:
            issue(result, "errors", f"大小写重名：{rel}", path)
        else:
            found[key] = safe
    return found


def _project(path, result):
    path = Path(path).resolve()
    if path.suffix.lower() not in {".civ6proj", ".modinfo"}:
        issue(result, "errors", "需要 .civ6proj 或 .modinfo 文件", path)
        return None
    root = _xml(path, result)
    if root is None:
        return None
    source = path.suffix.lower() == ".civ6proj"
    if root.tag != ("Project" if source else "Mod"):
        issue(result, "errors", "工程 XML 根节点错误", path)
        return None
    declared = {}
    nodes = root.iter("Content") if source else root.findall("./Files/File")
    for node in nodes:
        rel = node.get("Include", "") if source else (node.text or "").strip()
        if source and (rel == "(Mod Art Dependency File)" or "$(" in rel or "*" in rel):
            issue(result, "unverified", f"MSBuild 动态引用需构建后检查：{rel}", path)
            continue
        target = _resolve(path.parent, rel, result)
        key = _key(rel)
        if key in declared:
            issue(result, "warnings", f"重复文件声明：{rel}", path)
        declared[key] = target
    containers = root.findall("./FrontEndActions") + root.findall("./InGameActions")
    if source:
        for prop in root.iter():
            if prop.tag in {"FrontEndActionData", "InGameActionData"} and (prop.text or "").strip():
                try:
                    data = _parse(prop.text.encode("utf-8"))
                    if data.tag not in {"FrontEndActions", "InGameActions"}:
                        raise ValueError("动作根节点需为 FrontEndActions / InGameActions")
                    containers.append(data)
                except (ET.ParseError, ValueError) as exc:
                    issue(result, "errors", f"动作内嵌 XML 无效：{exc}", path)
    actions = []
    for container in containers:
        ids = set()
        for action in container:
            ident = (action.tag, action.get("id"))
            if ident in ids:
                issue(result, "errors", f"重复动作：{container.tag}/{ident}", path)
            ids.add(ident)
            refs = [(f.text or "").strip() for f in action.findall("./File")]
            if action.tag == "ReplaceUIScript":
                replacement = (action.findtext("./Properties/LuaReplace") or "").strip()
                context = (action.findtext("./Properties/LuaContext") or "").strip()
                if not replacement or not context:
                    issue(result, "errors", "ReplaceUIScript 缺少 LuaContext / LuaReplace", path)
                elif replacement not in refs:
                    refs.append(replacement)
            actions.append((action.tag, action.get("id"), refs))
            for rel in refs:
                if source and rel == "(Mod Art Dependency File)":
                    continue  # ModBuddy resolves this virtual dependency artifact.
                _resolve(path.parent, rel, result)
                if _key(rel) not in declared:
                    issue(result, "errors", f"{action.tag} 引用未登记在文件清单：{rel}", path)
    return {"path": path, "root": root, "declared": declared, "actions": actions}


def _check_cooker_classes(base, files, xmls, config, result):
    """Use the user's SDK rules, never one shared namespace or a guessed class.

    Inspired by 千川白浪's Civ6ArtUnpack handover (S7); implemented against the
    installed Civ6.cfg structure. This reads declarations, not cooked BLP bytes.
    """
    if config is None:
        issue(result, "unverified", "未提供 --cooker-config，未核对 SDK 类名及允许关系", base)
        return
    config = Path(config).resolve()
    root = _xml(config, result)
    if root is None:
        return
    package_nodes = root.findall("./m_XLPClasses/m_Classes/Element")
    class_nodes = root.findall("./m_Classes/m_Classes/Element")
    if not package_nodes or not class_nodes:
        issue(result, "errors", "Civ6.cfg 缺少 XLP / 资源类注册结构", config)
        return

    def registry(nodes, label):
        index = {}
        for node in nodes:
            name = _value(node, "m_Name")
            if not name or name in index:
                issue(result, "errors", f"配置存在空或重复 {label} 类：{name}", config)
            else:
                index[name] = node
        return index

    packages = registry(package_nodes, "XLP")
    definitions = {
        suffix: registry([e for e in class_nodes if e.get("class") == kind], kind)
        for suffix, kind in (
            (".ast", "AssetObjects..AssetClass"),
            (".geo", "AssetObjects..GeometryClass"),
            (".tex", "AssetObjects..TextureClass"),
        )
    }
    for suffix, items in definitions.items():
        if not items:
            issue(result, "errors", f"Civ6.cfg 缺少 {suffix} 类注册表", config)

    def allowed(node, field):
        return {e.get("text", "").strip() for e in node.findall(f"./{field}/Element")}

    def local_object(folder, name, suffix, owner):
        # Object names are references, not paths authorized to escape the project.
        relative = f"{folder}/{name}"
        if not name.lower().endswith(suffix):
            relative += suffix
        resolved = _resolve(base, relative, result, required=False)
        if resolved is None:
            return None
        key = _key(resolved.relative_to(base))
        if key not in xmls:
            issue(result, "unverified", f"对象 {name} 需在外部 pantry 确认：{relative}", owner)
            return None
        return xmls[key]

    for key, root in xmls.items():
        path = files[key]
        suffix = path.suffix.lower()
        cls = _value(root, "m_ClassName")
        if suffix in definitions and cls not in definitions[suffix]:
            issue(result, "errors", f"{suffix} 类 {cls!r} 不在对应 SDK 类注册表中", path)
        if suffix == ".xlp":
            package = packages.get(cls)
            if package is None:
                issue(result, "errors", f"XLP 类 {cls!r} 不在 SDK 注册表中", path)
                continue
            entity_type = (package.findtext("m_eInstanceEntityType") or "").strip()
            destination = {"ASSET": ("Assets", ".ast"), "TEXTURE": ("Textures", ".tex")}.get(entity_type)
            if destination is None:
                issue(result, "unverified", f"尚未核对 XLP 对象类型 {entity_type} 的资源类关系", path)
                continue
            permitted = allowed(package, "m_AllowedClasses")
            for entry in root.findall("./m_Entries/Element"):
                name = _value(entry, "m_ObjectName")
                if not name:
                    issue(result, "errors", f"XLP 条目 {_value(entry, 'm_EntryID')} 缺少 ObjectName", path)
                    continue
                obj = local_object(destination[0], name, destination[1], path)
                if obj is not None and _value(obj, "m_ClassName") not in permitted:
                    issue(result, "errors", f"XLP {cls} 不允许对象 {name} 的类 {_value(obj, 'm_ClassName')}", path)
        elif suffix == ".ast" and cls in definitions[".ast"]:
            permitted = allowed(definitions[".ast"][cls], "m_AllowedGeoClasses")
            for ref in root.iter("m_GeoName"):
                name = (ref.get("text") or "").strip()
                if not name:
                    continue
                geo = local_object("Geometries", name, ".geo", path)
                if geo is not None and _value(geo, "m_ClassName") not in permitted:
                    issue(result, "errors", f"AST {cls} 不允许几何 {name} 的类 {_value(geo, 'm_ClassName')}", path)
    issue(result, "unverified", "未解析 FGX 网格/骨架、验证 pantry 同名资源优先级或解码本次 BLP；类名通过不代表复原成功", base)


def check_assets(project, *, cooker_config=None):
    result = report("assets", project)
    data = _project(project, result)
    if data is None:
        return result
    base = data["path"].parent
    files = _files_under(base, result, ART_SUFFIXES)
    xmls = {}
    for key, path in files.items():
        root = _xml(path, result)
        if root is None:
            continue
        xmls[key] = root
        for elem in root.iter():
            if (elem.tail and elem.tail.strip()) or (len(elem) and elem.text and elem.text.strip()):
                issue(result, "errors", "资源 XML 存在标签外说明文字；应删除或改成注释", path)
            if any("_MissingArt" in value for value in elem.attrib.values()):
                issue(result, "errors", "资源引用为 _MissingArt", path)
            for value in elem.attrib.values():
                if re.search(r"\{[A-Z][A-Z0-9_]*\}", value):
                    issue(result, "errors", f"未替换模板占位符：{value}", path)
        if path.suffix.lower() == ".xlp":
            ids = [_value(e, "m_EntryID") for e in root.findall("./m_Entries/Element")]
            if len(ids) != len(set(ids)) or any(not ident for ident in ids):
                issue(result, "errors", "XLP 存在空或重复 EntryID", path)
        if path.suffix.lower() == ".artdef" and _value(root, "m_TemplateName") == "LeaderFallback":
            for collection in root.iter("Element"):
                if _value(collection, "m_CollectionName") != "Animations":
                    continue
                names = [_value(e, "m_Name") for e in collection.findall("./Element")]
                if len(names) != len(set(names)):
                    issue(result, "errors", "同一领袖存在重复外交状态", path)
                if names and "DEFAULT" not in names:
                    issue(result, "warnings", "领袖未声明 DEFAULT，需核对回退来源", path)
        # Binary companions are relative to the same asset folder in these formats.
        if path.suffix.lower() in {".geo", ".env", ".tex"}:
            for ref in root.iter("m_RelativePath"):
                name = ref.get("text", "")
                if name:
                    _resolve(path.parent, name, result)
        if path.suffix.lower() == ".lrg":
            for ref in root.iter("m_LightName"):
                name = ref.get("text", "")
                if name and _key(f"EnvironmentLights/{name}.env") not in xmls and _key(f"EnvironmentLights/{name}.env") not in files:
                    issue(result, "unverified", f"灯光 {name} 需在 SDK pantry 或外部依赖中确认", path)
        if path.suffix.lower() == ".mtl" and _value(root, "m_ClassName") == "Leader_Matte":
            slots = {}
            for elem in root.iter("Element"):
                slot, obj = _value(elem, "m_ParamName"), _value(elem, "m_ObjectName")
                if slot:
                    slots[slot] = obj
                if obj and slot in {"BaseColor", "Opacity"} and _key(f"Textures/{obj}.tex") not in files:
                    issue(result, "unverified", f"Leader_Matte 的 {slot} 纹理需外部确认：{obj}", path)
            for slot in ("BaseColor", "Opacity"):
                if not slots.get(slot):
                    issue(result, "errors", f"Leader_Matte 缺少 {slot} 纹理引用", path)
        if path.suffix.lower() == ".env":
            directions = root.find(".//m_DirectionTags")
            if directions is not None and not list(directions):
                issue(result, "warnings", "环境未声明方向灯；纸片领袖需核对外交场景照明", path)
    for key, root in xmls.items():
        path = files[key]
        if path.suffix.lower() not in {".artdef", ".ast"}:
            continue
        for elem in root.iter("Element"):
            if elem.get("class") != "AssetObjects..BLPEntryValue":
                continue
            entry, xlp, cls = (_value(elem, name) for name in ("m_EntryName", "m_XLPPath", "m_XLPClass"))
            if not entry:
                continue
            xlp = xlp.replace("\\", "/")
            rel = xlp if xlp.lower().startswith("xlps/") else "XLPs/" + xlp
            target = _resolve(base, rel, result, required=False) if xlp else None
            if not xlp:
                issue(result, "unverified", f"BLP 条目 {entry} 未给出 XLP 路径", path)
                continue
            xroot = xmls.get(_key(target.relative_to(base))) if target is not None else None
            if xroot is None:
                issue(result, "unverified", f"BLP 条目 {entry} 的 XLP 需在外部库确认：{xlp}", path)
                continue
            if _value(xroot, "m_ClassName") and _value(xroot, "m_ClassName") != cls:
                issue(result, "errors", f"BLP 与 XLP 类别不一致：{cls} / {_value(xroot, 'm_ClassName')}", path)
            entries = {_value(e, "m_EntryID"): _value(e, "m_ObjectName")
                       for e in xroot.findall("./m_Entries/Element")}
            if entry not in entries:
                issue(result, "errors", f"XLP {xlp} 缺少条目 {entry}", path)
            elif cls == "LeaderFallback":
                obj = entries[entry]
                if not obj:
                    issue(result, "errors", f"LeaderFallback 条目 {entry} 缺少对象名", path)
                else:
                    for suffix in (".tex", ".dds"):
                        _resolve(base, f"Textures/{obj}{suffix}", result)
    _check_cooker_classes(base, files, xmls, cooker_config, result)
    issue(result, "unverified", "未执行 SDK pantry 全量解析、Cooker 或游戏内显示验收", data["path"])
    return result


def check_audio(project):
    result = report("audio", project)
    data = _project(project, result)
    if data is None:
        return result
    base, declared = data["path"].parent, data["declared"]
    actions = [a for a in data["actions"] if a[0] == "UpdateAudio"]
    if not actions:
        issue(result, "warnings", "没有 UpdateAudio 动作", data["path"])
    checked_banks = set()
    audio_dirs = set()

    def registered(path):
        if _key(path.relative_to(base)) not in declared:
            issue(result, "errors", "音频文件未登记在 Files / Content", path)

    for _, ident, refs in actions:
        if not refs:
            issue(result, "warnings", f"UpdateAudio {ident} 没有 INI 文件", data["path"])
        for rel in refs:
            if Path(rel).suffix.lower() != ".ini":
                issue(result, "errors", f"UpdateAudio 应引用 Banks.ini，不应直接引用媒体：{rel}", data["path"])
                continue
            ini = _resolve(base, rel, result)
            if ini is None:
                continue
            registered(ini)
            audio_dirs.add(ini.parent)
            try:
                raw = ini.read_bytes()
            except OSError as exc:
                issue(result, "errors", f"Banks.ini 无法读取：{exc}", ini)
                continue
            try:
                text = raw.decode("ascii")
            except UnicodeDecodeError:
                issue(result, "errors", "Banks.ini 需要无 BOM 的 ASCII 内容", ini)
                continue
            if b"\n" in raw.replace(b"\r\n", b"") or b"\r" in raw.replace(b"\r\n", b""):
                issue(result, "warnings", "Banks.ini 推荐 CRLF 换行", ini)
            section = None
            banks = []
            for line in text.splitlines():
                line = line.split(";", 1)[0].strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    if section not in AUDIO_SECTIONS:
                        issue(result, "errors", f"未知 Banks.ini 分区：{section}", ini)
                elif section not in AUDIO_SECTIONS:
                    issue(result, "errors", f"bank 条目不在有效分区：{line}", ini)
                elif Path(line).suffix.lower() != ".bnk":
                    issue(result, "errors", f"bank 条目需要 .bnk 文件名：{line}", ini)
                else:
                    bank = _resolve(ini.parent, line, result)
                    if bank is not None:
                        registered(bank)
                        banks.append(bank)
            if not banks:
                issue(result, "warnings", "Banks.ini 没有可读取的 bank", ini)
            for bank in banks:
                if bank in checked_banks:
                    continue
                checked_banks.add(bank)
                candidates = (bank.with_suffix(".xml"), bank.parent / "SoundBanksInfo.xml")
                metadata_found = False
                for candidate in candidates:
                    metadata = _resolve(base, candidate.relative_to(base).as_posix(), result, required=False)
                    if metadata is None or not metadata.is_file():
                        continue
                    root = _xml(metadata, result)
                    if root is None:
                        continue
                    matches = [b for b in root.iter("SoundBank")
                               if b.findtext("ShortName") in {bank.stem, bank.name}
                               or Path((b.findtext("Path") or "").replace("\\", "/")).name.casefold() == bank.name.casefold()]
                    for match in matches:
                        metadata_found = True
                        for media in match.findall(".//ReferencedStreamedFiles/File"):
                            name = media.findtext("Path")
                            if not name:
                                mid = media.get("Id")
                                language = media.get("Language", "SFX")
                                if not mid or not mid.isascii() or not mid.isdigit():
                                    issue(result, "unverified", "流式媒体缺少 Path 或数字 Id", metadata)
                                    continue
                                name = ("" if language == "SFX" else language + "/") + mid + ".wem"
                            wem = _resolve(bank.parent, name, result)
                            if wem is not None:
                                registered(wem)
                    if metadata_found:
                        break
                if not metadata_found:
                    issue(result, "unverified", f"{bank.name} 无匹配 SoundBanksInfo；无法确认全部流式 WEM", bank)
    for directory in audio_dirs:
        for path in _files_under(directory, result, {".ini", ".bnk", ".wem"}).values():
            registered(path)
    issue(result, "unverified", "未验证 Wwise 编译版本、事件触发和游戏内发声", data["path"])
    return result


def _structure(root):
    """Ignore formatting/comments; preserve ordered elements and meaningful text."""
    def text(value):
        return value if value and value.strip() else ""
    return (root.tag, tuple(sorted(root.attrib.items())), text(root.text),
            tuple((_structure(c), text(c.tail)) for c in root))


def compare_art(source, cooked, *, suffixes=None):
    result = report("art-compare", cooked)
    source, cooked = Path(source).resolve(), Path(cooked).resolve()
    suffixes = set(suffixes or [".artdef"])
    if not suffixes <= ART_SUFFIXES:
        issue(result, "errors", "只支持明确的美术 XML 后缀")
        return result
    left = _files_under(source, result, suffixes)
    right = _files_under(cooked, result, suffixes)
    result["comparisons"] = []
    for key in sorted(left.keys() | right.keys()):
        if key not in left or key not in right:
            issue(result, "errors", "源目录或产物目录缺少对应文件", key)
            continue
        try:
            a, b = left[key].read_bytes(), right[key].read_bytes()
        except OSError as exc:
            issue(result, "errors", f"资源文件无法读取：{exc}", key)
            continue
        if a == b:
            status = "identical"
        else:
            ar, br = _xml(left[key], result), _xml(right[key], result)
            if ar is None or br is None:
                status = "invalid_xml"
            elif _structure(ar) == _structure(br):
                status = "format_only"
            else:
                status = "semantic_change"
                issue(result, "errors", "XML 字段、引用、有效文本或集合顺序变化；需核对具体差异", key)
                # Give reviewers the actual changed attributes, without normalizing them away.
                def describe(e, path=""):
                    path += "/" + e.tag
                    yield {"path": path, "tag": e.tag, "attributes": dict(e.attrib),
                           "text": e.text if e.text and e.text.strip() else None,
                           "tail": e.tail if e.tail and e.tail.strip() else None}
                    for index, child in enumerate(e):
                        yield from describe(child, f"{path}[{index}]")
                av, bv = list(describe(ar)), list(describe(br))
                differences = [{"index": i, "source": a, "cooked": b}
                               for i, (a, b) in enumerate(zip_longest(av, bv)) if a != b]
                result.setdefault("details", []).append(
                    {"file": key, "difference_count": len(differences), "differences": differences[:100]})
        result["comparisons"].append({"file": key, "status": status})
        try:
            br = _parse(b)
            if any("_MissingArt" in v for e in br.iter() for v in e.attrib.values()):
                issue(result, "errors", "Cooker 产物包含 _MissingArt", key)
        except (ET.ParseError, ValueError):
            if status == "identical":
                issue(result, "errors", "相同文件也不是合法美术 XML", key)
    if not left and not right:
        issue(result, "warnings", "没有匹配的美术 XML 文件")
    return result


def check_workshop(workspace, *, modinfo=None):
    base = Path(workspace).resolve()
    result = report("workshop", base)
    meta_path = _resolve(base, "workshop.json", result)
    if meta_path is not None:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
            if not isinstance(meta, dict):
                raise ValueError("workshop.json 必须为对象")
            existing = _resolve(base, "mod_id.txt", result, required=False)
            for field in ("title", "description"):
                value = meta.get(field)
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    issue(result, "errors", f"workshop.json 的 {field} 应为非空字符串或 null", meta_path)
                elif value is None and (existing is None or not existing.is_file()):
                    issue(result, "warnings", f"新条目未提供 {field}；需核对发布元数据", meta_path)
            visibility = meta.get("visibility")
            if visibility is not None and (not isinstance(visibility, str) or visibility not in {"private", "friends_only", "unlisted", "public"}):
                issue(result, "errors", "visibility 必须为 private/friends_only/unlisted/public", meta_path)
            if meta.get("changeNote") is not None and not isinstance(meta["changeNote"], str):
                issue(result, "errors", "changeNote 必须为字符串或 null", meta_path)
            tags = meta.get("tags")
            if tags is not None and (not isinstance(tags, list) or any(not isinstance(v, str) for v in tags)):
                issue(result, "errors", "tags 必须为字符串数组或 null", meta_path)
            dependencies = meta.get("dependencies")
            if dependencies is not None and (not isinstance(dependencies, list) or any(
                    type(v) is not int or not 0 < v < 2**64 for v in dependencies)):
                issue(result, "errors", "dependencies 必须为 UInt64 整数数组或 null（不是字符串 ID）", meta_path)
            locales = meta.get("localizations") if meta.get("localizations") is not None else []
            if not isinstance(locales, list):
                issue(result, "errors", "localizations 必须为数组", meta_path)
            else:
                seen = set()
                for item in locales:
                    language = item.get("language") if isinstance(item, dict) else None
                    if not isinstance(language, str) or not language.strip() or language in seen:
                        issue(result, "errors", "localizations 的 language 缺失或重复", meta_path)
                        continue
                    seen.add(language)
                    if any(item.get(field) is not None and not isinstance(item[field], str)
                           for field in ("title", "description", "changeNote")):
                        issue(result, "errors", "本地化标题、说明和变更说明必须为字符串或 null", meta_path)
        except (OSError, UnicodeError, ValueError) as exc:
            issue(result, "errors", f"workshop.json 无法解析：{exc}", meta_path)
    content = _resolve(base, "content", result, required=False)
    if content is None or not content.is_dir():
        issue(result, "errors", "缺少 content 目录", base)
        return result
    if modinfo is not None:
        selected = _resolve(content, str(modinfo), result)
    else:
        candidates = list(_files_under(content, result, {".modinfo"}).values())
        selected = candidates[0] if len(candidates) == 1 else None
        if len(candidates) != 1:
            issue(result, "errors", "content 必须有唯一 .modinfo；多个时用 --modinfo 指定相对路径", content)
    if selected is not None:
        data = _project(selected, result)
        if data is not None:
            try:
                uuid.UUID(data["root"].get("id", ""))
            except ValueError:
                issue(result, "errors", ".modinfo id 不是合法 GUID", selected)
            for field in ("Name", "Description"):
                if not (data["root"].findtext(f"./Properties/{field}") or "").strip():
                    issue(result, "errors", f".modinfo 缺少 Properties/{field}", selected)
            registered = data["declared"]
            for path in selected.parent.rglob("*"):
                if path.is_file() and path.suffix.lower() != ".modinfo":
                    safe = _resolve(content, path.relative_to(content).as_posix(), result)
                    if safe and _key(path.relative_to(selected.parent)) not in registered:
                        issue(result, "warnings", "实际文件未列入 .modinfo Files；核对是否为预期构建产物", path)
    ident = _resolve(base, "mod_id.txt", result, required=False)
    if ident is not None and ident.exists():
        try:
            if not _steam_id(ident.read_text(encoding="utf-8-sig").strip()):
                issue(result, "errors", "mod_id.txt 不是有效工坊条目 ID", ident)
        except (OSError, UnicodeError) as exc:
            issue(result, "errors", f"mod_id.txt 无法读取：{exc}", ident)
    cover = _resolve(base, "image.png", result, required=False)
    if cover is not None and cover.exists():
        try:
            with cover.open("rb") as stream:
                if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                    issue(result, "errors", "image.png 不是 PNG 文件", cover)
        except OSError as exc:
            issue(result, "errors", f"image.png 无法读取：{exc}", cover)
    issue(result, "unverified", "未连接 Steam；条目所有权、线上依赖和实际游戏加载需另行验证", base)
    return result


def _steam_id(value):
    return (isinstance(value, str) and len(value) <= 20 and value.isascii() and value.isdigit()
            and 0 < int(value) < 2**64)
