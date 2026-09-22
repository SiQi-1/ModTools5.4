"""自定义文件通道：路径净化 + 文件动作分类/合并（GUI 与 modgen 单一实现）。

背景（2026-08-17）：AI 以前只能生成 .CIV 主内容，自定义 SQL/XML/Lua 必须人工中转
（往工程目录放文件 + 一键配置注册动作）。本模块把"自定义文件"变成工具管理的一等公民：

- 文件写入 .civ6proj 工程目录，一键生成**原样透传**（readonly，不重新生成），
  并自动进入 .civ6proj 的 Content Include 与 ActionData；
- 按路径自动分类注册 文件动作（与 GUI「一键配置」同一规则）；
- GUI（basic_info_workspace 一键配置）与 modgen（custom-file 命令）共用本模块，
  AI 控制接口（project_file_write 等）经 GUI 链路复用同一规则——单一实现，防漂移。

纯标准库，无 PyQt。
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Callable, Optional

# 动作分类规则（与 GUI 一键配置一致）：
# (scope, action_type, action_id, load_order)；scope: "front" / "in_game"
FRONT_AND_IN_GAME_ACTIONS = {"UpdateIcons", "UpdateText", "UpdateColors"}
IN_GAME_ONLY_ACTIONS = {
    "UpdateDatabase", "AddGameplayScripts", "AddUserInterfaces", "ImportFiles", "UpdateArt", "UpdateAudio",
}

# 各动作默认加载顺序（与 GUI 快速动作一致；自定义 UpdateDatabase 用 10000 > 生成数据 9999，
# 旧通道同 (type,id) 合并会保留旧顺序；受管扩展由 extensions.py 独立规划）
DEFAULT_LOAD_ORDER: dict[str, int] = {
    "UpdateText": 0,
    "UpdateColors": 0,
    "UpdateArt": 0,
    "UpdateIcons": 1000,
    "AddGameplayScripts": 9500,
    "AddUserInterfaces": 9600,
    "ImportFiles": 9700,
    "UpdateDatabase": 10000,
}


def sanitize_relative_path(raw: object) -> str | None:
    """规范化工程内相对路径（正斜杠）；拒绝绝对路径/盘符/`..` 穿越，非法返回 None。"""
    text = str(raw or "").replace("\\", "/").strip()
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return None
    return "/".join(parts)


def looks_like_ui_context_xml(xml_text: object) -> bool:
    """判断 XML 文本是否 UI Context 文件（根元素为 <Context>，含命名空间）。"""
    text = str(xml_text or "").strip()
    if not text:
        return False
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False
    tag = str(root.tag).lower()
    return tag == "context" or tag.endswith("}context")


def classify_custom_path(
    rel_path: str,
    *,
    peer_exists: Optional[Callable[[str], bool]] = None,
    read_text: Optional[Callable[[str], str]] = None,
) -> list[tuple[str, str, str, int]]:
    """自定义文件 → [(scope, action_type, action_id, load_order), ...]。

    规则（与 GUI 一键配置 `_classify_custom_import_paths` 一致）：
    - Icons/*.sql|xml        → UpdateIcons（front + in_game，load 1000）
    - Text/*.sql|xml         → UpdateText（front + in_game，load 0）
    - UI/*.xml（同名 .lua 存在且自身为 <Context> 根）→ AddUserInterfaces（in_game，load 9600）
    - UI/*.lua（同名 .xml 存在且其为 <Context> 根）→ AddUserInterfaces（in_game，load 9600）
    - Scripts/*.lua          → AddGameplayScripts（in_game，load 9500）
    - Import/*.lua           → ImportFiles（in_game，load 9700）
    - 其余 *.sql|xml         → UpdateDatabase（in_game，load 10000：在生成数据 9999 之后）
    - 其余（图片等）         → 不注册动作
    """
    rel = sanitize_relative_path(rel_path)
    if not rel:
        return []
    lower = rel.lower()
    if "." not in lower:
        return []
    ext = lower.rsplit(".", 1)[-1]
    parts = [part for part in lower.split("/") if part]
    top = parts[0] if parts else ""

    def _peer_ok(peer_rel: str) -> bool:
        return bool(peer_exists is not None and peer_exists(peer_rel))

    def _ui_context_ok(xml_rel: str) -> bool:
        return bool(read_text is not None and looks_like_ui_context_xml(read_text(xml_rel)))

    if ext in {"sql", "xml"}:
        if top == "icons":
            return [
                ("front", "UpdateIcons", "UpdateIcons", DEFAULT_LOAD_ORDER["UpdateIcons"]),
                ("in_game", "UpdateIcons", "UpdateIcons", DEFAULT_LOAD_ORDER["UpdateIcons"]),
            ]
        if top == "text":
            return [
                ("front", "UpdateText", "UpdateText", DEFAULT_LOAD_ORDER["UpdateText"]),
                ("in_game", "UpdateText", "UpdateText", DEFAULT_LOAD_ORDER["UpdateText"]),
            ]
        if top == "ui" and ext == "xml":
            lua_peer = rel[:-4] + ".lua"
            if _peer_ok(lua_peer) and _ui_context_ok(rel):
                return [("in_game", "AddUserInterfaces", "AddUserInterfaces", DEFAULT_LOAD_ORDER["AddUserInterfaces"])]
        return [("in_game", "UpdateDatabase", "UpdateDatabase", DEFAULT_LOAD_ORDER["UpdateDatabase"])]

    if ext == "lua":
        if top == "scripts":
            return [("in_game", "AddGameplayScripts", "AddGameplayScripts", DEFAULT_LOAD_ORDER["AddGameplayScripts"])]
        if top == "ui":
            xml_peer = rel[:-4] + ".xml"
            if _peer_ok(xml_peer) and _ui_context_ok(xml_peer):
                return [("in_game", "AddUserInterfaces", "AddUserInterfaces", DEFAULT_LOAD_ORDER["AddUserInterfaces"])]
            return []
        if top == "import":
            return [("in_game", "ImportFiles", "ImportFiles", DEFAULT_LOAD_ORDER["ImportFiles"])]
    return []


def merge_action_entry(
    entries: list[dict[str, object]],
    *,
    action_type: str,
    action_id: str,
    files: list[str],
    load_order: int,
    origin: str = "imported",
) -> int:
    """把文件合并进动作条目列表（与 GUI 一键配置 `_ensure_action`/`_merge_files` 同语义）。

    - 同 (type, id) 动作复用既有条目（不改其 load_order），否则新建；
    - 文件按归一化路径去重；返回新增文件数。
    """
    target: dict[str, object] | None = None
    for item in entries:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "") == action_type and str(item.get("id") or "") == action_id:
            target = item
            break
    if target is None:
        target = {
            "type": action_type,
            "id": action_id,
            "files": [],
            "load_order": load_order,
            "file_origins": {},
        }
        entries.append(target)

    file_list = target.get("files") if isinstance(target.get("files"), list) else []
    origins = target.get("file_origins") if isinstance(target.get("file_origins"), dict) else {}
    existing_lower = {str(item).replace("\\", "/").strip().lower() for item in file_list}
    added = 0
    for raw_file in files:
        rel = sanitize_relative_path(raw_file)
        if not rel:
            continue
        low = rel.lower()
        if low in existing_lower:
            if rel not in origins:
                origins[rel] = origin
            continue
        file_list.append(rel)
        origins[rel] = origin
        existing_lower.add(low)
        added += 1
    target["files"] = file_list
    target["file_origins"] = origins
    return added


def remove_action_files(entries: list[dict[str, object]], rel_path: str) -> int:
    """从动作条目列表移除指定文件（含 file_origins）；返回移除的文件数。"""
    rel = sanitize_relative_path(rel_path)
    if not rel:
        return 0
    removed = 0
    for item in entries:
        if not isinstance(item, dict):
            continue
        files = item.get("files") if isinstance(item.get("files"), list) else []
        if rel not in files:
            continue
        files.remove(rel)
        removed += 1
        origins = item.get("file_origins") if isinstance(item.get("file_origins"), dict) else {}
        origins.pop(rel, None)
        item["file_origins"] = origins
    return removed
