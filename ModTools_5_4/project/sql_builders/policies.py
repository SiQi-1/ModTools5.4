"""Policy SQL generation independent of the editor and Qt."""
from __future__ import annotations

import re

from ..entity_defaults import POLICY_FIELD_DEFAULTS
from ..sql_utils import build_insert_block, deduplicate_rows, sql_escape, sql_literal


def build_policy_sql_pair(entries: object) -> tuple[str, str]:
    """Build data SQL and localized text from a .CIV policy section.

    Accept the legacy section shapes, preserve row order and first-type-wins
    behavior, and leave the caller's data untouched. No GUI or database is used.
    """
    policy_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
    if not policy_entries:
        return "-- Policies.sql\n-- 暂无政策卡数据", "-- Text.sql\n-- 暂无政策卡文本数据"

    field_defaults = POLICY_FIELD_DEFAULTS

    types_rows: list[str] = []
    policies_rows: list[str] = []
    policies_xp1_rows: list[str] = []
    policy_exclusive_rows: list[str] = []
    text_rows: list[str] = []

    def _value_or_default(data: dict[str, object], key: str) -> object:
        value = data.get(key)
        if value is None:
            return field_defaults.get(key)
        return value

    def _normalized(field_key: str, value: object) -> object:
        default = field_defaults.get(field_key)
        if isinstance(default, int):
            try:
                return int(value if value is not None else default)
            except (TypeError, ValueError):
                return int(default)
        return str(value or "").strip()

    seen_types: set[str] = set()
    for index, entry in enumerate(policy_entries, start=1):
        policy_type = str(entry.get("type") or "").strip()
        if not policy_type:
            policy_type = f"POLICY_CUSTOM_{index}"
        if policy_type in seen_types:
            # 同 type 重复条目：只取第一条，避免主表同主键两行与文本重复。
            continue
        seen_types.add(policy_type)

        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        policy_name = str(_value_or_default(table_data, "Name") or "")
        policy_desc = str(_value_or_default(table_data, "Description") or "")

        prereq_civic = str(_normalized("PrereqCivic", _value_or_default(table_data, "PrereqCivic")) or "")
        prereq_tech = str(_normalized("PrereqTech", _value_or_default(table_data, "PrereqTech")) or "")
        slot_type = str(_normalized("GovernmentSlotType", _value_or_default(table_data, "GovernmentSlotType")) or "")
        if not slot_type:
            slot_type = "SLOT_WILDCARD"
        requires_unlock = int(_normalized("RequiresGovernmentUnlock", _value_or_default(table_data, "RequiresGovernmentUnlock")) or 0)
        explicit_unlock = int(_normalized("ExplicitUnlock", _value_or_default(table_data, "ExplicitUnlock")) or 0)

        types_rows.append(f"('{policy_type}', 'KIND_POLICY')")

        text_rows.append(f"('zh_Hans_CN','LOC_{policy_type}_NAME','{sql_escape(policy_name)}')")
        text_rows.append(f"('zh_Hans_CN','LOC_{policy_type}_DESCRIPTION','{sql_escape(policy_desc)}')")

        policy_values: list[object | None] = [
            policy_type,
            f"LOC_{policy_type}_NAME",
            f"LOC_{policy_type}_DESCRIPTION",
            prereq_civic or None,
            prereq_tech or None,
            slot_type,
            requires_unlock,
            explicit_unlock,
        ]

        policies_rows.append("(" + ", ".join(sql_literal(item) for item in policy_values) + ")")

        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
        xp1_payload = subtables.get("Policies_XP1") if isinstance(subtables.get("Policies_XP1"), dict) else entry.get("policies_xp1") if isinstance(entry.get("policies_xp1"), dict) else {}
        min_era = str(xp1_payload.get("MinimumGameEra") or "").strip()
        max_era = str(xp1_payload.get("MaximumGameEra") or "").strip()
        requires_dark_age = int(xp1_payload.get("RequiresDarkAge", 0) or 0)
        requires_golden_age = int(xp1_payload.get("RequiresGoldenAge", 0) or 0)
        if min_era or max_era or requires_dark_age or requires_golden_age:
            policies_xp1_rows.append(
                "(" + ", ".join(
                    sql_literal(item)
                    for item in [policy_type, min_era or None, max_era or None, requires_dark_age, requires_golden_age]
                ) + ")"
            )

        exclusive_payload = subtables.get("Policy_GovernmentExclusives_XP2") if isinstance(subtables.get("Policy_GovernmentExclusives_XP2"), dict) else entry.get("policy_government_exclusive") if isinstance(entry.get("policy_government_exclusive"), dict) else {}
        government_type = str(exclusive_payload.get("GovernmentType") or "").strip()
        if government_type:
            policy_exclusive_rows.append(f"('{sql_escape(policy_type)}', '{sql_escape(government_type)}')")

    types_rows = deduplicate_rows(types_rows)
    policies_rows = deduplicate_rows(policies_rows)
    policies_xp1_rows = deduplicate_rows(policies_xp1_rows)
    policy_exclusive_rows = deduplicate_rows(policy_exclusive_rows)
    text_rows = deduplicate_rows(text_rows)

    sql_blocks: list[str] = []
    sql_blocks.append(build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
    if policies_rows:
        sql_blocks.append(
            build_insert_block(
                "Policies",
                "Policies",
                [
                    "PolicyType",
                    "Name",
                    "Description",
                    "PrereqCivic",
                    "PrereqTech",
                    "GovernmentSlotType",
                    "RequiresGovernmentUnlock",
                    "ExplicitUnlock",
                ],
                policies_rows,
            )
        )
    if policies_xp1_rows:
        sql_blocks.append(
            build_insert_block(
                "Policies_XP1",
                "Policies_XP1",
                ["PolicyType", "MinimumGameEra", "MaximumGameEra", "RequiresDarkAge", "RequiresGoldenAge"],
                policies_xp1_rows,
            )
        )
    if policy_exclusive_rows:
        sql_blocks.append(
            build_insert_block(
                "Policy_GovernmentExclusives_XP2",
                "Policy_GovernmentExclusives_XP2",
                ["PolicyType", "GovernmentType"],
                policy_exclusive_rows,
            )
        )

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
