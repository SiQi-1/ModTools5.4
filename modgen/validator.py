"""validate：条目/工程规则校验，输出可读错误清单。

检查项（与 GUI 导出规则对齐）：
- 必填字段缺失（REQUIRED_MAIN_TABLE_FIELD_RULES 已并入 schema 的 required）
- Type 命名合规（与规则生成值一致）
- 简称非空（abbr）
- 中文名非空
- 引用一致性（bindings/trait_bindings/subtables 中的 section/index 引用悬空）
- LOC 前缀约定（AI 不应手写 LOC 到文本字段）
- 主表类型键与 type 一致
"""
from __future__ import annotations

import copy
import re
from typing import Any

from . import rules
from .modifier_validator import check_modifier_data
from .schema_store import load_schemas


def _deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def validate_entry(section: str, entry: dict[str, Any], *, prefix: str = "", infix: int = 0) -> list[str]:
    """校验单个条目，返回错误清单（空列表 = 通过）。

    warnings（如 type 与规则生成值不一致，但语义式命名合法）单独输出，
    见 check_entry。
    """
    errors, _warnings = check_entry(section, entry, prefix=prefix, infix=infix)
    return errors


def check_entry(section: str, entry: dict[str, Any], *, prefix: str = "", infix: int = 0) -> tuple[list[str], list[str]]:
    """校验单个条目，返回 (errors, warnings)。

    errors 为硬错误（必填缺失/head 前缀错误/引用悬空等）；
    warnings 为建议（type 与规则生成值不一致——语义式命名合法但需确认）。
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(entry, dict):
        return ["条目必须是对象"], []

    # 1. 必填基础字段（按分类：总督用 code，议程/伟人/晋升树无顶层 abbr）
    required_keys = rules.SECTION_REQUIRED_KEYS.get(section, ("abbr", "name"))
    for key in required_keys:
        if not str(entry.get(key) or "").strip():
            errors.append(f"缺少 {key}")

    # 2. type 命名校验（总督条目不存 type，用 GovernorType；伟人用 class_data）
    entry_type = str(entry.get("type") or "").strip()
    if not entry_type and section == "总督":
        entry_type = str(entry.get("GovernorType") or "").strip()
    if not entry_type and section == "伟人":
        class_data = entry.get("class_data")
        if isinstance(class_data, dict):
            entry_type = str(class_data.get("GreatPersonClassType") or "").strip()
    if not entry_type:
        if section not in ("单位晋升",):
            errors.append("缺少 type")
    else:
        type_rule = rules.SECTION_TYPE_RULES.get(section)
        head = type_rule["head"] if type_rule else ""
        if head and not entry_type.startswith(head + "_"):
            errors.append(f"type 必须以 {head}_ 开头（实际 {entry_type}）")
        if re.search(r"[^A-Za-z0-9_]", entry_type):
            errors.append(f"type 含非法字符：{entry_type}")
        abbr = str(entry.get("abbr") or entry.get("code") or "").strip()
        expected = rules.build_entity_type(
            prefix, infix,
            head=head,
            midfix_code=type_rule["midfix"] if type_rule else "",
            short_name=abbr,
        )
        if entry_type != expected:
            warnings.append(f"type 与规则生成值不一致（规则为 {expected}，实际 {entry_type}）；语义式命名需确认")

    # 3. 主表类型键一致性
    db_type_key = rules.SECTION_DB_TYPE_KEY.get(section)
    if db_type_key and db_type_key in entry and entry_type:
        actual = str(entry.get(db_type_key) or "").strip()
        if actual and actual != entry_type:
            errors.append(f"{db_type_key}（{actual}）与 type（{entry_type}）不一致")

    # 4. 主表必填字段
    schema = load_schemas().get(section)
    if schema:
        main_table = schema.get("main_table")
        if isinstance(main_table, dict):
            table_data = entry.get("table_data")
            table_data = table_data if isinstance(table_data, dict) else {}
            for field in main_table.get("fields", []):
                if not field.get("required"):
                    continue
                key = field.get("key")
                if not key:
                    continue
                value = table_data.get(key)
                if value in (None, ""):
                    default = field.get("default")
                    if default not in (None, ""):
                        warnings.append(f"必填字段 {key} 缺失，将自动补默认值 {default}")
                    else:
                        errors.append(f"必填字段缺失：{key}（table_data，无默认值）")

    # 5. 文本字段不应手写 LOC
    for key in ("name", "Name", "Description", "civilization_name", "leader_name"):
        value = str(entry.get(key) or "").strip()
        if value.startswith("LOC_") and key in ("name", "Name", "Description"):
            errors.append(f"文本字段 {key} 不应手写 LOC tag（存中文即可，导出时自动注册）")

    # 6. 引用一致性（bindings / trait_bindings）
    bindings = entry.get("bindings")
    if isinstance(bindings, list):
        for index, binding in enumerate(bindings):
            if not isinstance(binding, dict):
                errors.append(f"bindings[{index}] 不是对象")
                continue
            section_name = str(binding.get("section") or "").strip()
            name = str(binding.get("name") or "").strip()
            if not section_name or not name:
                errors.append(f"bindings[{index}] 缺少 section/name")

    trait_bindings = entry.get("trait_bindings")
    if isinstance(trait_bindings, list):
        for index, binding in enumerate(trait_bindings):
            if not isinstance(binding, dict):
                errors.append(f"trait_bindings[{index}] 不是对象")
                continue
            if not str(binding.get("section") or "").strip():
                errors.append(f"trait_bindings[{index}] 缺少 section")

    # 7. images 结构
    images = entry.get("images")
    if images is not None and not isinstance(images, dict):
        errors.append("images 必须是对象（空 {} 或 键值对）")

    return errors, warnings


def validate_project(
    project: dict[str, Any],
    *,
    prefix: str | None = None,
    infix: int | None = None,
) -> list[str]:
    """校验整个工程（workspace 结构），返回错误清单。

    prefix/infix 未显式指定时，自动从工程基础信息读取。
    """
    errors: list[str] = []
    workspace = project.get("workspace")
    if not isinstance(workspace, dict):
        return ["工程缺少 workspace 节点"]
    if prefix is None or infix is None:
        auto_prefix, auto_infix = rules.project_workspace_params(workspace)
        if prefix is None:
            prefix = auto_prefix
        if infix is None:
            infix = auto_infix
    for section in rules.CONTENT_SECTIONS:
        entries = workspace.get(section)
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            for error in validate_entry(section, entry, prefix=prefix or "", infix=infix or 0):
                errors.append(f"{section}[{index}]: {error}")
    # 修改器直接工作区
    modifier_payload = workspace.get("修改器")
    if isinstance(modifier_payload, dict):
        modifier_data = modifier_payload.get("data")
        if isinstance(modifier_data, dict):
            sub_errors, _sub_warnings = check_modifier_data(modifier_data)
            for error in sub_errors:
                errors.append(f"修改器: {error}")
    return errors
