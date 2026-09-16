"""new-project：生成工程级 .CIV 骨架（基础信息/美术/修改器/文本 结构就位）。

骨架默认结构来自 schemas/project_scaffold.json —— 由 modgen/tools/extract_scaffold.py
从 GUI 编辑器默认导出提取（结构变化后重新提取并提交）。运行时不依赖 PyQt。

用途：解决"每个新工程都要手写脚本/拷贝旧工程"的问题——AI 只需
`modgen new-project` 一次，随后 generate/merge 条目、preview 验证。
"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any

from . import rules
from .merger import save_civ

SCAFFOLD_FILE = Path(__file__).resolve().parent / "schemas" / "project_scaffold.json"

# 直接工作区节（存 dict）：与 CIV_SECTION_ORDER 的直接工作区一致
DIRECT_SECTIONS = ("基础信息", "美术", "文本", "修改器")


class ScaffoldError(ValueError):
    pass


def load_scaffold() -> dict[str, Any]:
    """读取骨架 JSON（失败时给出重新提取指引）。"""
    try:
        payload = json.loads(SCAFFOLD_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScaffoldError(
            f"骨架文件不可用：{SCAFFOLD_FILE}（{exc}）。"
            "请在有 PyQt 的环境运行 `python modgen/tools/extract_scaffold.py` 重新提取。"
        ) from exc
    if not isinstance(payload, dict):
        raise ScaffoldError("骨架文件格式错误：应为对象")
    return payload


def build_workspace(
    *,
    prefix: str = "",
    infix: int = 0,
    file_name: str = "",
    mod_name: str = "",
    description: str = "",
    authors: str = "",
    guid: str = "",
    language: str = "简体中文",
) -> dict[str, Any]:
    """构建 17 节 workspace（内容分类为空列表，直接工作区取骨架默认结构）。"""
    scaffold = load_scaffold()

    workspace: dict[str, Any] = {}
    # 内容分类：空列表（按 CIV_SECTION_ORDER 顺序）
    for section in rules.CONTENT_SECTIONS:
        workspace[section] = []

    # 基础信息：应用 prefix/infix/file_name/mod_name 等工程参数
    basic = copy.deepcopy(scaffold.get("基础信息") or {})
    if not isinstance(basic.get("data"), dict):
        raise ScaffoldError("骨架缺少 基础信息.data")
    bdata = basic["data"]
    bdata["global_settings"] = {
        "prefix": str(prefix or "").strip(),
        "infix": max(0, int(infix or 0)),
        "language": language,
    }
    bdata["shared_workspace_params"] = {
        "prefix": str(prefix or "").strip(),
        "infix": max(0, int(infix or 0)),
        "file_name": file_name,
    }
    info = bdata.get("project_info")
    if not isinstance(info, dict):
        info = {}
        bdata["project_info"] = info
    info.update({
        "civ6proj_path": "",
        "mod_name": mod_name,
        "teaser": description,
        "description": description,
        "thanks": "",
        "authors": authors,
        "guid": guid or str(uuid.uuid4()).upper(),
        "file_name": file_name,
        "affects_saved_games": False,
        "supports_single_player": True,
        "supports_multiplayer": True,
        "supports_hotseat": True,
        "name_raw": file_name,
        "teaser_raw": file_name,
        "description_raw": file_name,
        "localized_text_data": "",
    })
    file_info = bdata.get("file_info")
    if not isinstance(file_info, dict):
        file_info = {}
        bdata["file_info"] = file_info
    file_info.setdefault("front_end_actions", [])
    file_info.setdefault("in_game_actions", [])
    file_info.setdefault("delete_requests", [])
    workspace["基础信息"] = basic

    # 美术：原样取骨架（已含 format/schema_version/data 包装）
    art = scaffold.get("美术")
    if not isinstance(art, dict):
        raise ScaffoldError("骨架缺少 美术")
    workspace["美术"] = copy.deepcopy(art)

    # 修改器：取骨架并写入 prefix1
    mod = scaffold.get("修改器")
    if not isinstance(mod, dict) or not isinstance(mod.get("data"), dict):
        raise ScaffoldError("骨架缺少 修改器")
    mod_data = copy.deepcopy(mod["data"])
    mod_data["prefix1"] = str(prefix or "").strip()
    mod_data["prefix2"] = ""
    workspace["修改器"] = {
        "format": mod.get("format") or "MODTOOLS54_MODIFIER_WORKSPACE",
        "schema_version": mod.get("schema_version") or "1.0.0",
        "data": mod_data,
    }

    # 文本
    workspace["文本"] = copy.deepcopy(scaffold.get("文本") or {"preview_settings": {}})

    # 按 CIV_SECTION_ORDER 重排（基础信息 → 内容分类 → 美术/文本/修改器）
    ordered: dict[str, Any] = {}
    for section in ("基础信息",) + rules.CONTENT_SECTIONS + ("美术", "文本", "修改器"):
        if section in workspace:
            ordered[section] = workspace[section]
    return ordered


def build_project(
    project_name: str,
    *,
    prefix: str = "",
    infix: int = 0,
    file_name: str = "",
    mod_name: str = "",
    description: str = "",
    authors: str = "",
    guid: str = "",
) -> dict[str, Any]:
    """构建完整 .CIV payload（meta + workspace）。"""
    return {
        "meta": {
            "format": "CIV_PROJECT",
            "schema_version": "0.1.0",
            "project_name": project_name,
        },
        "workspace": build_workspace(
            prefix=prefix,
            infix=infix,
            file_name=file_name,
            mod_name=mod_name,
            description=description,
            authors=authors,
            guid=guid,
        ),
    }


def create_new_project_file(
    out_path: Path,
    project_name: str,
    *,
    prefix: str = "",
    infix: int = 0,
    file_name: str = "",
    mod_name: str = "",
    description: str = "",
    authors: str = "",
) -> Path:
    """生成 .CIV 骨架文件（已存在的 .CIV 会拒绝覆盖；另存场景用 build_project）。"""
    if out_path.exists():
        raise ScaffoldError(f"目标文件已存在：{out_path}（如确认覆盖请先删除，或改用其它输出路径）")
    payload = build_project(
        project_name,
        prefix=prefix,
        infix=infix,
        file_name=file_name,
        mod_name=mod_name,
        description=description,
        authors=authors,
    )
    save_civ(out_path, payload)
    return out_path
