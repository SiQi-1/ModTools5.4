"""Portable extension sources and action planning; shared by CLI, GUI and AI.

The optional top-level .CIV `extensions` manifest owns source paths. Generated
ModBuddy files are copies. Dependencies describe project requirements; numerical
ordering is calculated only within the same action type and scope.
"""
from __future__ import annotations

import copy
import hashlib
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .custom_files import DEFAULT_LOAD_ORDER, sanitize_relative_path

ROLES = {
    "database": "UpdateDatabase", "text": "UpdateText", "icons": "UpdateIcons",
    "colors": "UpdateColors", "gameplay": "AddGameplayScripts",
    "ui": "AddUserInterfaces", "import": "ImportFiles",
}
TEXT_ROLES = {"database", "text", "icons", "colors"}


class ExtensionError(ValueError):
    pass


def safe_path(root: Path, relative: object) -> Path:
    """Reject traversal, Windows aliases/ADS and symlink escapes on every platform."""
    rel = sanitize_relative_path(relative)
    if not rel or any(
        re.search(r'[<>:"|?*\x00-\x1f]', part) or part.endswith((" ", "."))
        or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part)
        for part in rel.split("/")
    ):
        raise ExtensionError(f"非法扩展相对路径：{relative}")
    base = root.resolve()
    target = (base / rel).resolve()
    if not target.is_relative_to(base) or target == base:
        raise ExtensionError(f"扩展路径越出目录：{relative}")
    return target


def basic_data(payload: dict) -> dict:
    basic = payload.get("workspace", {}).get("基础信息", {})
    return basic.get("data", basic) if isinstance(basic, dict) else {}


def manifest(payload: dict) -> dict | None:
    value = payload.get("extensions")
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ExtensionError("extensions 必须为 version=1 的对象")
    if not isinstance(value.get("files"), list):
        raise ExtensionError("extensions.files 必须为数组")
    return value


def source_root(payload: dict, civ_path: Path | None) -> Path:
    spec = manifest(payload)
    if spec is None or civ_path is None:
        raise ExtensionError("先保存 .CIV 并执行 extension init")
    root = safe_path(civ_path.parent, spec.get("source_root"))
    output = basic_data(payload).get("project_info", {}).get("civ6proj_path")
    if output:
        output_root = Path(output).resolve().parent
        if root.is_relative_to(output_root) or output_root.is_relative_to(root):
            raise ExtensionError("扩展源码目录与 ModBuddy 输出目录必须分离，不能互相包含")
    return root


def basename(payload: dict, civ_path: Path) -> str:
    raw = basic_data(payload).get("project_info", {}).get("file_name") or civ_path.stem
    return re.sub(r'[^\w-]', '_', str(raw)) or "Mod"


def infer_role(path: str) -> str:
    rel = str(path).replace("\\", "/").lower()
    top, suffix = rel.split("/")[0], Path(rel).suffix
    if top == "ui" and suffix in {".xml", ".lua"}:
        return "ui"
    if suffix == ".lua":
        return "gameplay" if top == "scripts" else "import"
    if suffix in {".sql", ".xml"}:
        return {"text": "text", "icons": "icons"}.get(top, "database")
    raise ExtensionError("扩展源码支持 SQL/XML/Lua；图片与纹理请使用 .CIV 美术通道")


def _entry(path: str, *, role: str | None = None, **metadata: Any) -> dict:
    role = role or infer_role(path)
    if role not in ROLES:
        raise ExtensionError(f"未知扩展角色：{role}")
    entry = {
        "id": "file_" + hashlib.sha256(path.casefold().encode()).hexdigest()[:12],
        "path": path, "role": role,
        "scope": "both" if role in {"text", "icons", "colors"} else "in_game",
        "feature": "core", "depends_on": [],
    }
    if role == "database":
        entry["phase"] = "after_generated"
    entry.update({key: value for key, value in metadata.items() if value is not None})
    return entry


def _scopes(entry: dict) -> tuple[str, ...]:
    return ("front", "in_game") if entry["scope"] == "both" else (entry["scope"],)


def plan_extensions(payload: dict, civ_path: Path | None, *, generated_paths=(),
                    check_sources: bool = True, contents: dict[str, str] | None = None) -> dict:
    """Read-only validation and deterministic source/action plan. Never writes output."""
    result: dict[str, Any] = {"errors": [], "warnings": [], "files": {}, "entries": [],
                              "front_end_actions": [], "in_game_actions": []}
    errors = result["errors"]

    def error(message: str, entry: dict | None = None) -> None:
        errors.append({"message": message, **({"file": entry.get("path"),
                       "feature": entry.get("feature")} if entry else {})})

    try:
        spec = manifest(payload)
        if spec is None:
            return result
        root = source_root(payload, civ_path)
        result["source_root"] = str(root)
        ids: dict[str, dict] = {}
        paths: dict[str, dict] = {}
        generated = {str(p).replace("\\", "/").casefold() for p in generated_paths}
        for raw in spec["files"]:
            if not isinstance(raw, dict):
                error("扩展条目必须为对象")
                continue
            entry = copy.deepcopy(raw)
            path, ident, role = entry.get("path"), entry.get("id"), entry.get("role")
            safe_path(root, path)
            output = basic_data(payload).get("project_info", {}).get("civ6proj_path")
            if output:
                safe_path(Path(output).resolve().parent, path)
            if not isinstance(path, str) or path != sanitize_relative_path(path):
                error("path 需为使用 / 的规范相对路径", entry)
                continue
            if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", ident):
                error("id 需为稳定的英文标识（字母/数字/下划线/连字符）", entry)
                continue
            if ident in ids or path.casefold() in paths:
                error("重复的扩展 id 或输出路径", entry)
            ids[ident], paths[path.casefold()] = entry, entry
            if role not in ROLES:
                error("未知 role", entry)
                continue
            suffix = Path(path).suffix.lower()
            allowed = {".sql", ".xml"} if role in TEXT_ROLES else {".lua", ".xml"} if role == "ui" else {".lua"}
            if suffix not in allowed:
                error("文件后缀与 role 不符", entry)
            if entry.get("scope") not in {"front", "in_game", "both"}:
                error("scope 需为 front / in_game / both", entry)
            elif role in {"gameplay", "ui", "import"} and entry["scope"] != "in_game":
                error("脚本/UI 角色目前仅支持 in_game", entry)
            expected_top = {"gameplay": "Scripts", "ui": "UI", "import": "Import"}.get(role)
            if expected_top and not path.startswith(expected_top + "/"):
                error(f"{role} 文件必须位于 {expected_top}/", entry)
            if not isinstance(entry.get("feature"), str) or not entry["feature"].strip():
                error("feature 需为非空功能名称", entry)
            deps = entry.get("depends_on", [])
            if not isinstance(deps, list) or any(not isinstance(v, str) for v in deps):
                error("depends_on 需为扩展 id 数组", entry)
            if role == "database" and entry.get("phase") not in {"before_generated", "after_generated"}:
                error("database.phase 需为 before_generated / after_generated", entry)
            if role != "database" and "phase" in entry:
                error("phase 仅用于 database；跨角色依赖不转换为统一 LoadOrder", entry)
            if path.casefold() in generated:
                error("扩展路径与 .CIV 生成文件重名", entry)
            result["entries"].append(entry)
            if check_sources:
                try:
                    text = (contents or {}).get(path)
                    if text is None:
                        text = safe_path(root, path).read_text(encoding="utf-8-sig")
                    result["files"][path] = text
                    if suffix == ".xml":
                        xml = ET.fromstring(text)
                        context = str(xml.tag).split("}")[-1].lower() == "context"
                        if context != (role == "ui"):
                            error("Context XML 必须声明为 ui，数据库 XML 不得使用 Context 根", entry)
                except (OSError, UnicodeError, ET.ParseError) as exc:
                    error(f"扩展源码缺失、非 UTF-8 或 XML 无效：{exc}", entry)
        if errors:
            return result
        for entry in ids.values():
            for dep in entry.get("depends_on", []):
                if dep not in ids:
                    error(f"依赖不存在：{dep}", entry)
                    continue
                target = ids[dep]
                if target["role"] == "ui" and target["path"].lower().endswith(".lua"):
                    error("依赖 UI 时请引用 XML 入口 id", entry)
                if entry["role"] == target["role"] == "database":
                    if set(_scopes(entry)) != set(_scopes(target)):
                        error("数据库文件之间的顺序依赖必须使用相同 scope", entry)
                    if entry["phase"] == "before_generated" and target["phase"] == "after_generated":
                        error("before_generated 不得依赖 after_generated", entry)
            if entry["role"] == "ui":
                peer = str(Path(entry["path"]).with_suffix(".lua" if entry["path"].lower().endswith(".xml") else ".xml")).replace("\\", "/")
                other = paths.get(peer.casefold())
                if not other or other["role"] != "ui":
                    error(f"UI 缺少已声明的配套文件：{peer}", entry)
                elif set(entry.get("depends_on", [])) != set(other.get("depends_on", [])):
                    error("UI XML/Lua 的 depends_on 必须一致，二者是一个加载单元", entry)
        order: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(ident: str) -> None:
            if ident in visiting:
                raise ExtensionError(f"扩展依赖存在循环：{ident}")
            if ident in visited or ident not in ids:
                return
            visiting.add(ident)
            for dep in ids[ident].get("depends_on", []):
                visit(dep)
            visiting.remove(ident)
            visited.add(ident)
            order.append(ident)

        for ident in sorted(ids):
            visit(ident)
        if errors:
            return result
        result["entries"] = [ids[ident] for ident in order]
        info = basic_data(payload).get("file_info", {})
        for scope, key in (("front", "front_end_actions"), ("in_game", "in_game_actions")):
            entries = copy.deepcopy(info.get(key) or [])
            clean = []
            for action in entries:
                if not isinstance(action, dict):
                    continue
                action["files"] = [p for p in action.get("files", [])
                                   if str(p).replace("\\", "/").casefold() not in paths]
                if generated_paths and action.get("type") == "UpdateColors":
                    optional = f"data/{basename(payload, civ_path)}_colors".casefold()
                    action["files"] = [p for p in action["files"] if not (
                        str(p).rsplit(".", 1)[0].casefold() == optional and str(p).casefold() not in generated)]
                if action["files"]:
                    clean.append(action)
            database_orders = [int(a.get("load_order") or 0) for a in clean if a.get("type") == "UpdateDatabase"] or [9999]
            before_count = sum(e["role"] == "database" and e["phase"] == "before_generated" and scope in _scopes(e) for e in ids.values())
            counters: dict[tuple[str, str], int] = {}
            groups: dict[str, dict] = {}
            for entry in result["entries"]:
                if scope not in _scopes(entry):
                    continue
                role = entry["role"]
                if role == "ui" and entry["path"].lower().endswith(".lua"):
                    continue  # XML is the action entry; paired Lua is Content only.
                action_type = ROLES[role]
                phase = entry.get("phase", "default")
                group = entry["path"].rsplit(".", 1)[0].casefold() if role == "ui" else entry["id"]
                action_id = "MTX_" + (hashlib.sha256(group.encode()).hexdigest()[:12] if role == "ui" else entry["id"])
                if any(a.get("id") == action_id for a in clean):
                    error(f"保留动作 ID 冲突：{action_id}", entry)
                counter = (action_type, phase)
                if action_id in groups:
                    groups[action_id]["files"].append(entry["path"])
                    continue
                n = counters.get(counter, 0)
                if role == "database":
                    load = min(database_orders) - before_count + n if phase == "before_generated" else max(database_orders) + 1 + n
                    if load <= 0:
                        error("生成数据库动作之前没有正 LoadOrder 空间；请调整生成动作顺序", entry)
                else:
                    existing_orders = [int(a.get("load_order") or 0) for a in clean if a.get("type") == action_type]
                    load = max([DEFAULT_LOAD_ORDER.get(action_type, 0), *existing_orders]) + 1 + n
                counters[counter] = n + 1
                action = {"type": action_type, "id": action_id, "load_order": load,
                          "files": [entry["path"]], "file_origins": {entry["path"]: "extension"}}
                groups[action_id] = action
            result[key] = clean + list(groups.values())
        return result
    except (ExtensionError, TypeError, ValueError, OSError) as exc:
        error(str(exc))
        return result


def _require_valid(plan: dict) -> None:
    if plan["errors"]:
        raise ExtensionError("\n".join(item["message"] for item in plan["errors"]))


def write_extension(payload: dict, civ_path: Path, path: str, content: str, *,
                    role: str | None = None, **metadata: Any) -> dict:
    """Validate metadata before writing; UI peers may be authored in either order."""
    if not isinstance(content, str):
        raise ExtensionError("content 必须为字符串")
    root = source_root(payload, civ_path)
    target = safe_path(root, path)
    rel = target.relative_to(root).as_posix()
    proposed = copy.deepcopy(payload)
    files = proposed["extensions"]["files"]
    old = next((e for e in files if isinstance(e, dict) and str(e.get("path")).casefold() == rel.casefold()), None)
    if old:
        rel = old["path"]
        target = safe_path(root, rel)
    updates = {k: v for k, v in metadata.items() if v is not None}
    entry = {**old, **updates, **({"role": role} if role else {})} if old else _entry(rel, role=role, **updates)
    if entry["role"] != "database":
        if updates.get("phase") is not None:
            raise ExtensionError("phase 仅用于 database")
        entry.pop("phase", None)
    if old:
        files[files.index(old)] = entry
    else:
        files.append(entry)
    if entry["role"] == "ui" and "depends_on" in updates:
        stem = entry["path"].rsplit(".", 1)[0].casefold()
        for peer in files:
            if peer["role"] == "ui" and peer["path"].rsplit(".", 1)[0].casefold() == stem:
                peer["depends_on"] = list(entry["depends_on"])
    # Missing peers/dependencies are allowed during authoring; check/build reject them.
    plan = plan_extensions(proposed, civ_path, check_sources=False)
    blocking = [e for e in plan["errors"] if not (e["message"].startswith("UI 缺少") or e["message"].startswith("依赖不存在"))]
    _require_valid({"errors": blocking})
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    proposed["extensions"]["retired_paths"] = [p for p in proposed["extensions"].get("retired_paths", []) if p.casefold() != rel.casefold()]
    deletes = basic_data(payload).get("file_info", {}).get("delete_requests", [])
    deletes[:] = [p for p in deletes if str(p).casefold() != rel.casefold()]
    payload["extensions"] = proposed["extensions"]
    return {"ok": True, "path": rel, "absolute": str(target), "entry": entry, "actions": [], "added_files": 0}


def init_extensions(payload: dict, civ_path: Path, *, gameplay: bool = False, ui: bool = False) -> dict:
    """Create the default Core and optional Gameplay/UI bundle, preserving all files."""
    proposed = copy.deepcopy(payload)
    if manifest(proposed) is None:
        proposed["extensions"] = {"version": 1, "source_root": f"{civ_path.stem}.extensions", "files": []}
    root = source_root(proposed, civ_path)
    name = basename(proposed, civ_path)
    bundle = [(f"Data/{name}_Core.sql", "core", "database", "-- Project extension data. Keep supported entities in .CIV.\n", [])]
    if gameplay:
        bundle.append((f"Scripts/{name}_Gameplay.lua", "gameplay", "gameplay", "-- Gameplay context; read extension configuration through GameInfo.\n", ["core"]))
    if ui:
        bundle.extend([
            (f"UI/{name}_Panel.xml", "ui_xml", "ui", '<Context Name="' + name + '_Panel"/>\n', ["core"]),
            (f"UI/{name}_Panel.lua", "ui_lua", "ui", "-- UI context. Add event handlers and controls here.\n", ["core"]),
        ])
    contents = {}
    adopted = []
    existing = {entry["id"]: entry for entry in proposed["extensions"]["files"]}
    for path, ident, role, content, deps in bundle:
        if ident in existing:
            continue
        if safe_path(root, path).exists():
            raise ExtensionError(f"源码文件已存在但未声明，拒绝覆盖：{path}；请用 extension write 纳管")
        output = basic_data(payload).get("project_info", {}).get("civ6proj_path")
        if output:
            previous = safe_path(Path(output).resolve().parent, path)
            if previous.is_file():
                content = previous.read_text(encoding="utf-8-sig")
                adopted.append(path)
        proposed["extensions"]["files"].append(_entry(path, role=role, id=ident, depends_on=deps))
        contents[path] = content
    _require_valid(plan_extensions(proposed, civ_path, contents=contents))
    written = []
    try:
        for path, content in contents.items():
            target = safe_path(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as stream:
                stream.write(content)
            written.append(target)
    except OSError:
        for target in written:
            target.unlink(missing_ok=True)
        raise
    payload["extensions"] = proposed["extensions"]
    return {"ok": True, "source_root": str(root), "created": list(contents), "adopted": adopted, "manifest": copy.deepcopy(proposed["extensions"])}


def remove_extension(payload: dict, civ_path: Path, path: str, *, keep_file: bool = False) -> dict:
    root = source_root(payload, civ_path)
    safe_path(root, path)
    spec = manifest(payload)
    entry = next((e for e in spec["files"] if e["path"].casefold() == path.casefold()), None)
    if entry is None:
        raise ExtensionError(f"扩展未声明：{path}")
    users = [e["id"] for e in spec["files"] if entry["id"] in e.get("depends_on", [])]
    if users:
        raise ExtensionError(f"仍有扩展依赖该文件：{', '.join(users)}")
    target = safe_path(root, entry["path"])
    existed = target.is_file()
    if not keep_file:
        target.unlink(missing_ok=True)
    spec["files"].remove(entry)
    retired = spec.setdefault("retired_paths", [])
    if entry["path"] not in retired:
        retired.append(entry["path"])
    # Leave old output untouched until generate_all applies the explicit delete plan.
    info = basic_data(payload).setdefault("file_info", {})
    deletes = info.setdefault("delete_requests", [])
    if entry["path"] not in deletes:
        deletes.append(entry["path"])
    for key in ("front_end_actions", "in_game_actions"):
        for action in info.get(key, []):
            action["files"] = [p for p in action.get("files", []) if str(p).casefold() != entry["path"].casefold()]
    return {"ok": True, "path": entry["path"], "deleted_file": existed and not keep_file,
            "removed_actions": 0, "output_delete_pending": True}


def copy_sources_for_save_as(payload: dict, old_path: Path, new_path: Path) -> None:
    """Copy the declared source set when Save As changes directory; no overwrites."""
    if manifest(payload) is None or old_path.resolve().parent == new_path.resolve().parent:
        return
    plan = plan_extensions(payload, old_path)
    _require_valid(plan)
    root = source_root(payload, new_path)
    for path, text in plan["files"].items():
        target = safe_path(root, path)
        if target.exists() and target.read_text(encoding="utf-8-sig") != text:
            raise ExtensionError(f"另存目录有不同内容的扩展源码，拒绝覆盖：{target}")
    for path, text in plan["files"].items():
        target = safe_path(root, path)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
