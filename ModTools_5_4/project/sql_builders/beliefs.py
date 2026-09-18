"""Belief SQL generation independent of the editor and Qt."""
from __future__ import annotations

import logging
import re

from ..entity_defaults import BELIEF_FIELD_DEFAULTS
from ..sql_utils import build_insert_block, deduplicate_rows, sql_escape

LOGGER = logging.getLogger(__name__)


def build_belief_sql_pair(entries: object) -> tuple[str, str]:
    """Build belief data SQL and localized text without GUI or database access.

    Legacy section shapes and first-type-wins behavior are preserved.
    """
    belief_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
    if not belief_entries:
        return "-- Beliefs.sql\n-- 暂无信仰数据", "-- Text.sql\n-- 暂无信仰文本数据"

    field_defaults = BELIEF_FIELD_DEFAULTS

    types_rows: list[str] = []
    beliefs_rows: list[str] = []
    text_rows: list[str] = []

    def _value_or_default(data: dict[str, object], key: str) -> object:
        value = data.get(key)
        if value is None:
            return field_defaults.get(key)
        return value

    seen_types: set[str] = set()
    for index, entry in enumerate(belief_entries, start=1):
        belief_type = str(entry.get("type") or "").strip()
        if not belief_type:
            belief_type = f"BELIEF_CUSTOM_{index}"
        if belief_type in seen_types:
            # 同 type 重复条目（复制/手动编辑 .CIV 常见）：只取第一条，
            # 避免 Types/Beliefs/Text 重复输出与 Beliefs 主键冲突。
            continue
        seen_types.add(belief_type)

        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        belief_name = str(_value_or_default(table_data, "Name") or "")
        belief_desc = str(_value_or_default(table_data, "Description") or "")
        belief_class_type = str(_value_or_default(table_data, "BeliefClassType") or "").strip()
        if not belief_class_type:
            belief_class_type = "BELIEF_CLASS_PANTHEON"

        types_rows.append(f"('{sql_escape(belief_type)}', 'KIND_BELIEF')")
        beliefs_rows.append(
            "(" + ", ".join(
                [
                    f"'{sql_escape(belief_type)}'",
                    f"'LOC_{sql_escape(belief_type)}_NAME'",
                    f"'LOC_{sql_escape(belief_type)}_DESCRIPTION'",
                    f"'{sql_escape(belief_class_type)}'",
                ]
            ) + ")"
        )
        text_rows.append(f"('zh_Hans_CN','LOC_{belief_type}_NAME','{sql_escape(belief_name)}')")
        text_rows.append(f"('zh_Hans_CN','LOC_{belief_type}_DESCRIPTION','{sql_escape(belief_desc)}')")

    types_rows = deduplicate_rows(types_rows)
    beliefs_rows = deduplicate_rows(beliefs_rows)
    text_rows = deduplicate_rows(text_rows)

    LOGGER.info("Built belief SQL preview: entries=%d", len(belief_entries))

    sql_blocks: list[str] = []
    sql_blocks.append(build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
    sql_blocks.append(build_insert_block("Beliefs", "Beliefs", ["BeliefType", "Name", "Description", "BeliefClassType"], beliefs_rows))

    data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
    data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

    text_sql = "\n".join(
        [
            "-- Text.sql",
            "",
            build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
        ]
    ).rstrip()
    return data_sql, text_sql
