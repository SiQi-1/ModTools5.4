"""merge：把条目合并进 .CIV 工程文件。

- 自动备份原文件为 .bak（写入前）；
- 按 type 去重：同 section 同 type 视为更新，否则追加；
- 校验通过才写回（默认开启）。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import rules
from .validator import validate_entry


class MergeError(ValueError):
    pass


def load_civ(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MergeError(f"工程文件不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MergeError(f"工程文件不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict) or "workspace" not in payload:
        raise MergeError("工程文件缺少 workspace 节点")
    return payload


def save_civ(path: Path, payload: dict[str, Any]) -> None:
    backup = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(path, backup)
    except OSError:
        pass
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_entry(
    payload: dict[str, Any],
    section: str,
    entry: dict[str, Any],
    *,
    prefix: str = "",
    infix: int = 0,
    validate: bool = True,
) -> dict[str, Any]:
    """把条目合并进工程 payload（就地修改并返回）。

    Returns:
        更新后的 payload
    """
    if section not in rules.CONTENT_SECTIONS:
        raise MergeError(f"未知分类：{section}")

    if validate:
        errors = validate_entry(section, entry, prefix=prefix, infix=infix)
        if errors:
            raise MergeError("条目未通过校验：\n" + "\n".join(f"  - {e}" for e in errors))

    workspace = payload["workspace"]
    if not isinstance(workspace, dict):
        raise MergeError("workspace 不是对象")
    entries = workspace.get(section)
    if not isinstance(entries, list):
        entries = []
        workspace[section] = entries

    entry_type = str(entry.get("type") or "").strip()
    if entry_type:
        for index, existing in enumerate(entries):
            if isinstance(existing, dict) and str(existing.get("type") or "").strip() == entry_type:
                entries[index] = entry
                return payload
    entries.append(entry)
    return payload


def merge_entries(
    payload: dict[str, Any],
    section: str,
    entries: list[dict[str, Any]],
    *,
    prefix: str = "",
    infix: int = 0,
    validate: bool = True,
) -> dict[str, Any]:
    for entry in entries:
        merge_entry(payload, section, entry, prefix=prefix, infix=infix, validate=validate)
    return payload
