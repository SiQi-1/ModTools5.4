"""generate：从"意图参数"生成合规条目 JSON。

设计原则（准确性优先）：
- Type 永远由规则生成（AI 不手写），简称是唯一输入；
- 条目结构以 fixture 提取的 entry_template 为骨架（GUI 已验证可用）；
- 中文文本存 name/Name/Description 等字段，LOC tag 由导出约定生成，不存条目里；
- 图片一律空（images={}），路径留给用户。
"""
from __future__ import annotations

import copy
from typing import Any

from . import rules
from .schema_store import section_schema


class GenerateError(ValueError):
    pass


def _build_type(
    section: str,
    *,
    prefix: str,
    infix: int,
    short_name: object | None,
) -> str:
    type_rule = rules.SECTION_TYPE_RULES.get(section)
    if type_rule is None:
        raise GenerateError(f"未知分类：{section}")
    return rules.build_entity_type(
        prefix,
        infix,
        head=type_rule["head"],
        midfix_code=type_rule["midfix"],
        short_name=short_name,
    )


def _apply_table_data_defaults(section: str, table_data: dict[str, Any]) -> dict[str, Any]:
    """按主表 schema 补齐字段默认值（仅补有默认值的字段）。"""
    schema = section_schema(section)
    if not schema:
        return table_data
    main_table = schema.get("main_table")
    if not isinstance(main_table, dict):
        return table_data
    for field in main_table.get("fields", []):
        key = field.get("key")
        if not key or key in table_data:
            continue
        if field.get("default") not in (None, ""):
            table_data[key] = field.get("default")
    return table_data


def _build_base_entry(section: str, *, prefix: str, infix: int, name: str, abbr: str, description: str = "") -> dict[str, Any]:
    """生成分类条目的基础骨架（模板结构 + type 生成 + 中文名）。"""
    schema = section_schema(section)
    if schema is None:
        raise GenerateError(f"未知分类：{section}")
    template = schema.get("entry_template")
    if not isinstance(template, dict):
        raise GenerateError(f"分类 {section} 缺少条目模板")

    entity_type = _build_type(section, prefix=prefix, infix=infix, short_name=abbr)
    entry = copy.deepcopy(template)

    # 基础字段：总督用 code（与 GUI 一致），其余用 abbr；name 通用
    entry["name"] = name
    if section == "总督":
        entry["code"] = abbr
    else:
        entry["abbr"] = abbr
    entry["type"] = entity_type

    db_type_key = rules.SECTION_DB_TYPE_KEY.get(section)
    if db_type_key and db_type_key in entry:
        entry[db_type_key] = entity_type

    table_name = rules.SECTION_TABLE_NAME.get(section)
    if table_name and "table_name" in entry:
        entry["table_name"] = table_name

    # 主表 Name/Description（若模板有对应键）
    if "Name" in entry:
        entry["Name"] = name
    if "Description" in entry:
        entry["Description"] = ""

    # 图标名约定
    icon_key = "icon_image_name"
    if icon_key in entry:
        entry[icon_key] = f"ICON_{entity_type}"

    # 图片一律空
    entry["images"] = {}

    # 分类专属显示名键（GUI 编辑器读取的键）
    if section == "文明":
        entry["civilization_name"] = name
        entry["civilization_description"] = description
        entry["civilization_adjective"] = ""
        if "description_suffix" in entry:
            entry["description_suffix"] = "文明"
    elif section == "领袖":
        entry["leader_name"] = name
        entry["leader_text"] = ""

    return entry


def generate_entry(
    section: str,
    *,
    prefix: str,
    infix: int,
    name: str,
    abbr: str,
    description: str = "",
    **extra: Any,
) -> dict[str, Any]:
    """生成一个合规条目。

    Args:
        section: 分类名（文明/领袖/区域/…）
        prefix: 工程前缀（如 SIQI）
        infix: 工程中缀编号（如 35）
        name: 中文名（显示名）
        abbr: 英文简称（用于生成 Type，如 C0035_1 或 DEMO）
        description: 中文描述（可选）
        extra: 其余意图参数，直接写入条目（覆盖模板同名字段）
    """
    entry = _build_base_entry(
        section,
        prefix=prefix,
        infix=infix,
        name=name,
        abbr=abbr,
        description=description,
    )

    # 分类专属：table_data 补齐默认值
    if "table_data" in entry and isinstance(entry["table_data"], dict):
        table_data = copy.deepcopy(entry["table_data"])
        table_data["Name"] = name
        if description:
            table_data["Description"] = description
        entry["table_data"] = _apply_table_data_defaults(section, table_data)

    if "Description" in entry and description:
        entry["Description"] = description

    # extra 覆盖
    for key, value in extra.items():
        entry[key] = value

    return entry


def required_fields_to_fill(section: str) -> list[str]:
    """返回该分类"必填且无默认值"的主表字段清单（AI 需手动填写）。"""
    schema = section_schema(section)
    if not schema:
        return []
    main_table = schema.get("main_table")
    if not isinstance(main_table, dict):
        return []
    fields = []
    for field in main_table.get("fields", []):
        if field.get("required") and field.get("default") in (None, ""):
            key = field.get("key")
            if key:
                fields.append(key)
    return fields
