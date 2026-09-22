"""从 ModTools 源码与测试 fixture 提取 .CIV 条目 schema。

运行环境需要能 import ModTools（PyQt6）。产物写入 modgen/schemas/entry_schemas.json，
提交进 git，供 modgen（无 GUI 依赖）读取。

用法：
    python -m modgen.tools.extract_schemas
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from ModTools_5_4.ui.pages import entity_table_form as etf  # noqa: E402
from ModTools_5_4.project.civ_project import CIV_SECTION_ORDER  # noqa: E402
from sample_project import build_sample_project  # noqa: E402

from modgen import rules  # noqa: E402

OUT_PATH = Path(__file__).resolve().parents[1] / "schemas" / "entry_schemas.json"

SCHEMA_BUILDERS = {
    "文明": None,
    "领袖": None,
    "区域": etf.build_districts_main_schema,
    "建筑": etf.build_buildings_main_schema,
    "单位": etf.build_units_main_schema,
    "改良设施": etf.build_improvements_main_schema,
    "政策卡": etf.build_policies_main_schema,
    "项目": etf.build_projects_main_schema,
    "信仰": etf.build_beliefs_main_schema,
    "议程": etf.build_agendas_main_schema,
}


def _strip_entry(entry: dict) -> dict:
    """保留条目键结构，值清零（避免把 fixture 样例值带入生成结果）。

    默认值一律由主表 schema 的字段默认值决定，不由样例决定。
    """
    cleaned = {}
    for key, value in entry.items():
        if key == "images":
            cleaned[key] = {}
            continue
        if isinstance(value, dict):
            cleaned[key] = _strip_entry(value)
        elif isinstance(value, list):
            cleaned[key] = []
        elif isinstance(value, str):
            cleaned[key] = ""
        elif isinstance(value, bool):
            cleaned[key] = False
        elif isinstance(value, (int, float)):
            cleaned[key] = 0
        else:
            cleaned[key] = value
    return cleaned


def main() -> int:
    fixture = build_sample_project().sections
    sections: dict = {}
    for section in CIV_SECTION_ORDER:
        if section in ("基础信息", "美术", "文本", "修改器"):
            continue
        if section in rules.UI_ICON_SECTIONS:
            # 「UI图标」不是实体分类（无 main_table、无 Type），只由 validator 单独校验
            continue
        entries = fixture.get(section, [])
        if entries:
            sections[section] = {
                "entry_template": _strip_entry(entries[0]),
            }

    # 主表字段（含默认值 / sql_default / 必填）
    for section, builder in SCHEMA_BUILDERS.items():
        if builder is None:
            continue
        schema = builder()
        fields = []
        for field in schema.fields:
            from ModTools_5_4.ui.pages.entity_table_form import _NO_SQL_DEFAULT

            fields.append({
                "key": field.key,
                "label": field.label,
                "type": field.field_type,
                "default": field.default,
                "sql_default": None if field.sql_default is _NO_SQL_DEFAULT else field.sql_default,
                "required": field.required,
            })
        sections[section]["main_table"] = {
            "table_name": schema.table_name,
            "type_key": schema.type_key,
            "fields": fields,
        }

    payload = {
        "format": "MODGEN_ENTRY_SCHEMAS",
        "version": 1,
        "sections": sections,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # 2) 修改器 schema：EffectType/RequirementType 参数与 CollectionType
    mod_out = OUT_PATH.parent / "modifier_schemas.json"
    effect_params = json.loads((REPO_ROOT / "ModTools_5_4" / "data" / "effect_type_parameters.json").read_text(encoding="utf-8"))
    modifier_payload = {
        "format": "MODGEN_MODIFIER_SCHEMAS",
        "version": 1,
        "effect_types": {et["effect_type"]: list(et.get("parameter_names") or []) for et in effect_params.get("effect_types", [])},
        "requirement_types": {rt["requirement_type"]: list(rt.get("parameter_names") or []) for rt in effect_params.get("requirement_types", [])},
        "collection_types": [str(v) for v in effect_params.get("collection_types", [])],
    }
    mod_out.write_text(json.dumps(modifier_payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"written: {OUT_PATH} ({len(sections)} sections)")
    print(f"written: {mod_out} ({len(modifier_payload['effect_types'])} effect types)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
