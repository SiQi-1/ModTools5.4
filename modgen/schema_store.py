"""加载 entry_schemas.json（纯标准库）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMAS_PATH = Path(__file__).resolve().parent / "schemas" / "entry_schemas.json"


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
