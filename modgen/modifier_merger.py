"""merge 修改器：把 generate-modifier/requirement/reqset/ability（或 owner）产物
合并进工程"修改器"节（MODTOOLS54_MODIFIER_WORKSPACE）。

- 自动检测条目类型（也可 --kind 显式指定）；
- 同 id 去重更新（modifier_id / requirement_id / requirement_set_id / unit_ability_type / type_name）；
- 合并后对整个修改器 data 跑 check_modifier_data（默认开启，ERROR 拒绝写入）。
"""
from __future__ import annotations

from typing import Any

from .merger import MergeError, load_civ, save_civ
from .modifier_validator import check_modifier_data

MODIFIER_FORMAT = "MODTOOLS54_MODIFIER_WORKSPACE"
MODIFIER_SCHEMA_VERSION = "1.0.0"

MODIFIER_LIST_KEYS = (
    "owners",
    "unit_abilities",
    "modifiers",
    "requirement_sets",
    "requirements",
)

KINDS = ("modifier", "requirement", "requirement_set", "unit_ability", "owner")


def _detect_kind(entry: dict[str, Any]) -> str:
    if "modifier_id" in entry and "effect_type" in entry:
        return "modifier"
    if "requirement_id" in entry and "requirement_type" in entry:
        return "requirement"
    if "requirement_set_id" in entry and "logic" in entry:
        return "requirement_set"
    if "unit_ability_type" in entry and "name_zh" in entry:
        return "unit_ability"
    if "table_name" in entry and "type_name" in entry:
        return "owner"
    if "modifier_id" in entry and "attachment_target_type" in entry:
        return "owner_binding"
    return ""


def _id_key(kind: str) -> str:
    return {
        "modifier": "modifier_id",
        "requirement": "requirement_id",
        "requirement_set": "requirement_set_id",
        "unit_ability": "unit_ability_type",
        "owner": "type_name",
        "owner_binding": "modifier_id",
    }[kind]


def _list_key(kind: str) -> str:
    return {
        "modifier": "modifiers",
        "requirement": "requirements",
        "requirement_set": "requirement_sets",
        "unit_ability": "unit_abilities",
        "owner": "owners",
        "owner_binding": "owners",  # 绑定行合并进对应 owner（见 merge_owner_binding）
    }[kind]


def ensure_modifier_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    """确保工程有合规的"修改器"节，返回其 data dict（就地补全）。"""
    workspace = payload.get("workspace")
    if not isinstance(workspace, dict):
        raise MergeError("工程缺少 workspace 节点")
    modifier = workspace.get("修改器")
    if not isinstance(modifier, dict):
        modifier = {}
        workspace["修改器"] = modifier
    modifier.setdefault("format", MODIFIER_FORMAT)
    modifier.setdefault("schema_version", MODIFIER_SCHEMA_VERSION)
    data = modifier.get("data")
    if not isinstance(data, dict):
        data = {}
        modifier["data"] = data
    for key in MODIFIER_LIST_KEYS:
        if not isinstance(data.get(key), list):
            data[key] = []
    for key in ("prefix1", "prefix2"):
        if key not in data:
            data[key] = ""
    return data


def merge_modifier_entry(
    payload: dict[str, Any],
    entry: dict[str, Any],
    *,
    kind: str = "",
    validate: bool = True,
) -> dict[str, Any]:
    """把修改器条目合并进工程 payload（就地修改并返回）。

    kind 缺省时自动检测；不支持的类型抛 MergeError。
    """
    if not isinstance(entry, dict):
        raise MergeError("条目必须是 JSON 对象")
    detected = kind or _detect_kind(entry)
    if detected not in KINDS:
        if detected == "owner_binding":
            raise MergeError(
                "检测到 owner_binding（modifier_id + attachment_target_type）——"
                "绑定请写在 owner 条目的 owner_bindings 列表里，或直接合并 owner 条目"
            )
        raise MergeError(
            "无法识别条目类型。请用 --kind 指定：modifier / requirement / requirement_set / unit_ability / owner"
        )

    data = ensure_modifier_workspace(payload)
    list_key = _list_key(detected)
    id_key = _id_key(detected)
    entry_id = str(entry.get(id_key) or "").strip()
    if not entry_id:
        raise MergeError(f"条目缺少标识键 {id_key}")

    entries = data[list_key]
    for index, existing in enumerate(entries):
        if isinstance(existing, dict) and str(existing.get(id_key) or "").strip() == entry_id:
            entries[index] = entry
            break
    else:
        entries.append(entry)

    if validate:
        errors, _warnings = check_modifier_data(data)
        if errors:
            raise MergeError("修改器数据未通过校验：\n" + "\n".join(f"  - {e}" for e in errors))
    return payload


def merge_modifier_file(
    civ_path: str,
    entry_path: str,
    *,
    kind: str = "",
    validate: bool = True,
) -> dict[str, Any]:
    """从文件合并：加载工程 + 条目 JSON，合并后写回（自动备份 .bak）。"""
    from pathlib import Path

    import json as _json

    payload = load_civ(Path(civ_path))
    try:
        entry = _json.loads(Path(entry_path).read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as exc:
        raise MergeError(f"条目文件读取失败：{exc}") from exc
    merge_modifier_entry(payload, entry, kind=kind, validate=validate)
    save_civ(Path(civ_path), payload)
    return payload
