"""Custom LOC declarations merged into the standard generated Text output."""
from __future__ import annotations
import re
from .sql_utils import sql_escape


def text_entries(section: object) -> object:
    return section.get("custom_entries", []) if isinstance(section, dict) else []


def validate_custom_text(section: object, *, reserved_tags=()) -> list[str]:
    entries = text_entries(section)
    if not isinstance(entries, list):
        return ["文本.custom_entries 必须是列表"]
    seen = set(reserved_tags)
    errors = []
    for index, entry in enumerate(entries):
        label = f"自定义文本[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: 条目必须是对象")
            continue
        tag = entry.get("tag")
        if not isinstance(tag, str) or not re.fullmatch(r"LOC_[A-Z0-9_]+", tag):
            errors.append(f"{label}: tag 必须以 LOC_ 开头，仅包含大写字母、数字和下划线")
        elif tag in seen:
            errors.append(f"{label}: tag 重复或与生成文本冲突：{tag}")
        else:
            seen.add(tag)
        if not isinstance(entry.get("text"), str) or not entry["text"].strip():
            errors.append(f"{label}: text 不可为空")
        if "group" in entry and (not isinstance(entry["group"], str) or not entry["group"].strip()):
            errors.append(f"{label}: group 无值时应省略")
    return errors


def custom_text_groups(section: object) -> list[tuple[str, list[str]]]:
    """Call after validation; comments and SQL literals are separately escaped."""
    groups: dict[str, list[str]] = {}
    for entry in text_entries(section):
        group = " ".join(entry.get("group", "UI / Lua 文本").splitlines())
        row = f"('zh_Hans_CN','{entry['tag']}','{sql_escape(entry['text'])}')"
        groups.setdefault(group, []).append(row)
    return list(groups.items())
