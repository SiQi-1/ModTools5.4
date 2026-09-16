"""modgen custom-file：把自定义 SQL/XML/Lua 文件写进 .civ6proj 工程目录并注册文件动作。

自定义文件通道（2026-08-17 新增）：
- AI 以前只能生成 .CIV 主内容，自定义 SQL/Lua 必须人工中转。本命令把"自定义文件"
  变成工具管理的一等公民：文件写入工程目录（一键生成原样透传），并自动按路径
  注册文件动作（分类规则与 GUI 一键配置同一实现，见 ModTools_5_4/project/custom_files.py）。
- 纯标准库，不依赖 PyQt；与 AI 控制接口 `project_file_write` 等动作同语义。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import mt_bridge

custom_files = mt_bridge.custom_files


class CustomFileError(ValueError):
    pass


def basic_info_payload(payload: dict[str, Any]) -> dict[str, Any]:
    workspace = payload.get("workspace")
    if not isinstance(workspace, dict):
        raise CustomFileError("工程缺少 workspace 节点")
    section = workspace.get("基础信息")
    if not isinstance(section, dict):
        raise CustomFileError("工程缺少「基础信息」节")
    data = section.get("data") if isinstance(section.get("data"), dict) else section
    return data


def project_info(payload: dict[str, Any]) -> dict[str, Any]:
    data = basic_info_payload(payload)
    info = data.get("project_info")
    if not isinstance(info, dict):
        info = {}
        data["project_info"] = info
    return info


def file_info(payload: dict[str, Any]) -> dict[str, Any]:
    data = basic_info_payload(payload)
    info = data.get("file_info")
    if not isinstance(info, dict):
        info = {}
        data["file_info"] = info
    return info


def project_root_dir(payload: dict[str, Any]) -> Path:
    """解析 .civ6proj 所在目录（必须已存在工程文件）。"""
    info = project_info(payload)
    raw = str(info.get("civ6proj_path") or "").strip()
    if not raw:
        raise CustomFileError("工程未绑定 .civ6proj：先运行 `python -m modgen.cli civ6proj 工程.CIV --update-civ`")
    proj = Path(raw)
    if not proj.exists() or not proj.is_file():
        raise CustomFileError(f"工程文件不存在：{proj}（先运行 `python -m modgen.cli civ6proj 工程.CIV --update-civ`）")
    return proj.parent


def _action_entries(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    info = file_info(payload)
    raw_front = info.get("front_end_actions")
    front = raw_front if isinstance(raw_front, list) else []
    if front is not raw_front:
        info["front_end_actions"] = front
    raw_in_game = info.get("in_game_actions")
    in_game = raw_in_game if isinstance(raw_in_game, list) else []
    if in_game is not raw_in_game:
        info["in_game_actions"] = in_game
    return front, in_game


def write_custom_file(
    payload: dict[str, Any],
    rel_path: str,
    content: str,
    *,
    action_type: str = "",
    register_action: bool = True,
) -> dict[str, Any]:
    """把自定义文件写入工程目录，并按分类注册文件动作（原地修改 payload）。

    action_type 显式指定时跳过自动分类（UpdateIcons/UpdateText/UpdateColors 同时注册
    front 与 in_game，其余注册 in_game）；register_action=False 只写文件不注册。
    返回 {"path", "absolute", "actions": [(scope, action_type), ...], "added_files": n}。
    """
    rel = custom_files.sanitize_relative_path(rel_path)
    if not rel:
        raise CustomFileError(f"非法相对路径：{rel_path}（禁止绝对路径与 .. 穿越）")
    root = project_root_dir(payload)
    target = root / Path(rel.replace("/", "\\"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(content or ""), encoding="utf-8")

    registered: list[tuple[str, str]] = []
    added_files = 0
    if register_action:
        front, in_game = _action_entries(payload)
        specs = custom_files.classify_custom_path(
            rel,
            peer_exists=lambda peer: (root / peer.replace("/", "\\")).is_file(),
            read_text=lambda text_rel: _read_text(root, text_rel),
        )
        if action_type:
            action = str(action_type).strip()
            if action not in custom_files.FRONT_AND_IN_GAME_ACTIONS and action not in custom_files.IN_GAME_ONLY_ACTIONS:
                raise CustomFileError(f"未知动作类型：{action}")
            load = custom_files.DEFAULT_LOAD_ORDER.get(action, 0)
            if action in custom_files.FRONT_AND_IN_GAME_ACTIONS:
                specs = [("front", action, action, load), ("in_game", action, action, load)]
            else:
                specs = [("in_game", action, action, load)]
        for scope, spec_type, spec_id, load_order in specs:
            entries = front if scope == "front" else in_game
            added_files += custom_files.merge_action_entry(
                entries, action_type=spec_type, action_id=spec_id,
                files=[rel], load_order=load_order, origin="custom",
            )
            registered.append((scope, spec_type))
    return {
        "path": rel,
        "absolute": str(target),
        "actions": registered,
        "added_files": added_files,
    }


def list_custom_files(payload: dict[str, Any]) -> dict[str, Any]:
    """列出工程目录磁盘文件 + 已注册的文件动作。"""
    root = project_root_dir(payload)
    files = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append({
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "size": path.stat().st_size,
                })
    front, in_game = _action_entries(payload)

    def _compact(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": str(item.get("type") or ""),
                "id": str(item.get("id") or ""),
                "load_order": int(item.get("load_order") or 0),
                "files": list(item.get("files") or []),
            }
            for item in entries
            if isinstance(item, dict)
        ]

    return {
        "root": str(root),
        "files": files,
        "front_end_actions": _compact(front),
        "in_game_actions": _compact(in_game),
    }


def remove_custom_file(
    payload: dict[str, Any],
    rel_path: str,
    *,
    keep_file: bool = False,
) -> dict[str, Any]:
    """从文件动作移除指定文件（可选删除磁盘文件）；返回移除统计。"""
    rel = custom_files.sanitize_relative_path(rel_path)
    if not rel:
        raise CustomFileError(f"非法相对路径：{rel_path}（禁止绝对路径与 .. 穿越）")
    front, in_game = _action_entries(payload)
    removed_actions = custom_files.remove_action_files(front, rel) + custom_files.remove_action_files(in_game, rel)
    deleted = False
    if not keep_file:
        root = project_root_dir(payload)
        target = root / Path(rel.replace("/", "\\"))
        if target.exists() and target.is_file():
            target.unlink()
            deleted = True
    return {"path": rel, "removed_actions": removed_actions, "deleted_file": deleted}


def _read_text(root: Path, rel: str) -> str:
    path = root / Path(rel.replace("/", "\\"))
    if not path.exists() or not path.is_file():
        return ""
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if b"\x00" in raw[:4096]:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="ignore")
