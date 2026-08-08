"""加载 entry_schemas.json / modifier_schemas.json（纯标准库）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMAS_PATH = Path(__file__).resolve().parent / "schemas" / "entry_schemas.json"
MODIFIER_SCHEMAS_PATH = Path(__file__).resolve().parent / "schemas" / "modifier_schemas.json"


def load_schemas() -> dict[str, Any]:
    payload = json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))
    sections = payload.get("sections")
    return sections if isinstance(sections, dict) else {}


def section_schema(section: str) -> dict[str, Any] | None:
    schemas = load_schemas()
    return schemas.get(section)


def main_table_fields(section: str) -> list[dict[str, Any]] | None:
    schema = section_schema(section)
    if not schema:
        return None
    main_table = schema.get("main_table")
    if not isinstance(main_table, dict):
        return None
    return main_table.get("fields")


def load_modifier_schemas() -> dict[str, Any]:
    payload = json.loads(MODIFIER_SCHEMAS_PATH.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def effect_type_params(effect_type: str) -> list[str] | None:
    """EffectType 的参数名列表；不存在返回 None。"""
    schemas = load_modifier_schemas()
    params = schemas.get("effect_types")
    if not isinstance(params, dict):
        return None
    return params.get(effect_type)


def requirement_type_params(requirement_type: str) -> list[str] | None:
    """RequirementType 的参数名列表；不存在返回 None。"""
    schemas = load_modifier_schemas()
    params = schemas.get("requirement_types")
    if not isinstance(params, dict):
        return None
    return params.get(requirement_type)


def collection_type_exists(collection_type: str) -> bool:
    schemas = load_modifier_schemas()
    values = schemas.get("collection_types")
    if not isinstance(values, list):
        return True  # 无数据时宽松
    return collection_type in values
