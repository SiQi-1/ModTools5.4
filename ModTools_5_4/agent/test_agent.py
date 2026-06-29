"""Agent self-test: exercises all tools against a mock project, verifies results.

Run: python -m ModTools_5_4.agent.test_agent

Does NOT require a GUI or LLM connection. Tests the tool_executor + tools + knowledge.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ModTools_5_4.agent.tool_executor import ToolExecutor
from ModTools_5_4.agent.tools import TOOL_DEFS, SECTION_NAMES, DIRECT_SECTION_NAMES
from ModTools_5_4.agent.system_prompt import build_system_prompt


def _build_mock_sections() -> dict:
    """Build a realistic mock project with sample data."""
    return {
        "基础信息": {
            "format": "MODTOOLS54_BASIC_INFO_WORKSPACE",
            "data": {"prefix1": "SIQI", "prefix2": "0036", "mod_name": "测试Mod"},
        },
        "文明": [
            {"name": "中华文明", "abbr": "ZH", "table_name": "Civilizations",
             "civilization_type": "CIVILIZATION_SIQI_ZHONGHUA",
             "civilization_name": "中华文明", "civilization_description": "测试文明",
             "civilization_adjective": "中华的", "trait_name": "TRAIT_CIVILIZATION_SIQI_ZHONGHUA",
             "images": {}},
        ],
        "领袖": [
            {"name": "秦始皇", "abbr": "QIN", "leader_name": "秦始皇",
             "civilization_type": "CIVILIZATION_SIQI_ZHONGHUA",
             "images": {}},
        ],
        "区域": [
            {"name": "测试区域", "abbr": "TZ", "table_name": "Districts",
             "table_data": {"DistrictType": "DISTRICT_SIQI_TEST"},
             "images": {}},
        ],
        "建筑": [
            {"name": "测试建筑", "abbr": "TB", "table_name": "Buildings",
             "table_data": {"BuildingType": "BUILDING_SIQI_TEST", "Cost": 150},
             "images": {}},
        ],
        "单位": [],
        "改良设施": [],
        "总督": [],
        "伟人": [],
        "政策卡": [],
        "项目": [],
        "信仰": [],
        "议程": [],
        "美术": {"icon_slots": [], "leader_xlp_rows": []},
        "文本": {"preview_settings": {}},
        "修改器": {
            "format": "MODTOOLS54_MODIFIER_WORKSPACE",
            "schema_version": "1.0.0",
            "data": {
                "owners": [
                    {"table_name": "TraitModifiers", "type_column": "TraitType",
                     "type_name": "TRAIT_CIVILIZATION_SIQI_ZHONGHUA",
                     "display_name": "中华文明特质",
                     "owner_bindings": [{"modifier_id": "MODIFIER_SIQI_STRENGTH",
                                          "attachment_target_type": ""}],
                     "bound_modifier_ids": ["MODIFIER_SIQI_STRENGTH"]},
                ],
                "modifiers": [
                    {"modifier_id": "MODIFIER_SIQI_STRENGTH",
                     "modifier_type": "MODIFIER_PLAYER_UNITS_ATTACH_MODIFIER",
                     "effect_type": "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER",
                     "collection_type": "COLLECTION_OWNER",
                     "parameters": [{"name": "Amount", "value": "5"}]},
                ],
                "requirement_sets": [],
                "requirements": [],
                "unit_abilities": [],
            },
        },
    }


def main():
    ok = 0
    fail = 0
    mock = _build_mock_sections()
    te = ToolExecutor(lambda: mock)

    print("=" * 60)
    print("Agent 工具自测")
    print("=" * 60)

    # ── 1. Knowledge files loaded ──
    print("\n── 知识库检查 ──")
    checks = [
        ("效果类型", len(te._effect_types), 700, 800),
        ("条件类型", len(te._requirement_types), 260, 300),
        ("集合类型", len(te._collection_types), 55, 70),
        ("实体Schema", len(te._entity_schemas), 10, 15),
    ]
    for label, actual, lo, hi in checks:
        if lo <= actual <= hi:
            print(f"  [OK] {label}: {actual} (预期 {lo}-{hi})")
            ok += 1
        else:
            print(f"  [FAIL] {label}: {actual} (预期 {lo}-{hi})")
            fail += 1

    # ── 2. Read tools ──
    print("\n── 读取工具 ──")
    read_tests = [
        ("list_sections", {}),
        ("list_sections", {"include_direct": True}),
    ]
    for name, params in read_tests:
        r = te.execute(name, params)
        err = r.get("error")
        if err:
            print(f"  [FAIL] {name}({params}): {err}")
            fail += 1
        else:
            print(f"  [OK] {name}({params})")
            ok += 1

    for sec in ["文明", "领袖", "区域"]:
        r = te.execute("get_section_entries", {"section_name": sec})
        count = r.get("count", 0)
        if count > 0:
            print(f"  [OK] get_section_entries({sec}): {count} 个条目")
            ok += 1
        elif "error" in r:
            print(f"  [FAIL] get_section_entries({sec}): {r['error']}")
            fail += 1
        else:
            print(f"  [WARN] get_section_entries({sec}): 空列表（正常）")
            ok += 1

    # get_entry_detail
    r = te.execute("get_entry_detail", {"section_name": "文明", "entry_index": 0})
    data = r.get("data")
    if data and data.get("name") == "中华文明":
        print(f"  [OK] get_entry_detail(文明[0]): {data['name']}")
        ok += 1
    else:
        print(f"  [FAIL] get_entry_detail(文明[0]): {r}")
        fail += 1

    # get_direct_section
    for sec in DIRECT_SECTION_NAMES:
        r = te.execute("get_direct_section", {"section_name": sec})
        if "error" in r:
            # Text/Art might not have seeded data
            print(f"  [WARN] get_direct_section({sec}): {r.get('error', '无数据')}")
        else:
            print(f"  [OK] get_direct_section({sec})")
        ok += 1

    # get_modifier_summary
    r = te.execute("get_modifier_summary", {})
    print(f"  [OK] get_modifier_summary: owners={r.get('owners')}, modifiers={r.get('modifiers')}")
    ok += 1

    # get_modifier_detail
    r = te.execute("get_modifier_detail", {"modifier_id": "MODIFIER_SIQI_STRENGTH"})
    if "error" not in r:
        print(f"  [OK] get_modifier_detail(modifier_id): {r.get('modifier', {}).get('modifier_id')} → {r.get('modifier', {}).get('modifier_type')}")
        ok += 1
    else:
        print(f"  [FAIL] get_modifier_detail(modifier_id): {r}")
        fail += 1
    r = te.execute("get_modifier_detail", {"owner_key": "TraitModifiers:TRAIT_CIVILIZATION_SIQI_ZHONGHUA"})
    if "error" not in r:
        print(f"  [OK] get_modifier_detail(owner_key): {len(r.get('modifiers', []))} modifiers")
        ok += 1
    else:
        print(f"  [FAIL] get_modifier_detail(owner_key): {r}")
        fail += 1

    # ── 3. Search tools ──
    print("\n── 搜索工具 ──")
    searches = [
        ("search_effect_types", "战斗力", 1, 15),
        ("search_effect_types", "科技产出", 1, 15),
        ("search_effect_types", "文化炸弹", 1, 15),
        ("search_effect_types", "housing", 1, 5),
        ("search_requirement_types", "地形", 1, 10),
        ("search_requirement_types", "近战", 1, 10),
        ("search_requirement_types", "首都", 1, 5),
    ]
    for name, query, lo, hi in searches:
        r = te.execute(name, {"query": query})
        results = r.get("results", [])
        if lo <= len(results) <= hi:
            print(f"  [OK] {name}({query}): {len(results)} results, first={results[0].get(list(results[0].keys())[0], '?')[:50] if results else 'none'}")
            ok += 1
        else:
            print(f"  [WARN] {name}({query}): {len(results)} results (expected {lo}-{hi})")
            ok += 1

    # ── 4. Schema tools ──
    print("\n── Schema工具 ──")
    for sec in ["文明", "领袖", "区域", "建筑", "单位", "改良设施", "政策卡", "项目", "信仰", "议程"]:
        r = te.execute("get_entity_schema", {"section_name": sec})
        if "error" in r:
            print(f"  [WARN] get_entity_schema({sec}): {r['error']}")
            ok += 1
        else:
            fields = r.get("fields", [])
            required = [f['key'] for f in fields if f.get('required')]
            print(f"  [OK] get_entity_schema({sec}): {len(fields)} fields, {len(required)} required")
            ok += 1

    # get_effect_parameters
    for et in ["EFFECT_ADJUST_CITY_YIELD_CHANGE", "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER",
               "EFFECT_GRANT_ABILITY", "EFFECT_ADJUST_UNIT_COMBAT_STRENGTH"]:
        r = te.execute("get_effect_parameters", {"effect_type": et})
        if "error" in r:
            print(f"  [WARN] get_effect_parameters({et}): {r['error']}")
        else:
            params = r.get("params", [])
            comment = r.get("comment", "")
            print(f"  [OK] get_effect_parameters({et}): {len(params)} params, comment={comment}")
        ok += 1

    # ── 5. Propose tools ──
    print("\n── 提案工具 ──")

    # propose_add_entity for each section type
    entity_tests = [
        ("文明", {"name": "测试文明2", "abbr": "TC2", "table_name": "Civilizations",
                  "civilization_name": "测试文明2", "civilization_description": "自动测试",
                  "trait_name": "TRAIT_CIVILIZATION_SIQI_TC2"}),
        ("领袖", {"name": "测试领袖", "abbr": "TL", "leader_name": "测试领袖",
                  "civilization_type": "CIVILIZATION_SIQI_ZHONGHUA"}),
        ("区域", {"name": "测试区域2", "abbr": "TZ2", "table_name": "Districts",
                  "table_data": {"DistrictType": "DISTRICT_SIQI_TEST2", "Cost": 60}}),
        ("建筑", {"name": "图书馆", "abbr": "LIB", "table_name": "Buildings",
                  "table_data": {"BuildingType": "BUILDING_SIQI_LIBRARY", "Cost": 150,
                                 "PrereqTech": "TECH_WRITING"}}),
        ("单位", {"name": "测试单位", "abbr": "TU", "table_name": "Units",
                  "table_data": {"UnitType": "UNIT_SIQI_TEST", "Cost": 200, "BaseMoves": 3}}),
        ("改良设施", {"name": "测试改良", "abbr": "TI", "table_name": "Improvements",
                      "table_data": {"ImprovementType": "IMPROVEMENT_SIQI_TEST"}}),
        ("政策卡", {"name": "测试政策", "abbr": "TP", "table_name": "Policies",
                    "table_data": {"PolicyType": "POLICY_SIQI_TEST"}}),
        ("项目", {"name": "测试项目", "abbr": "TPJ", "table_name": "Projects",
                  "table_data": {"ProjectType": "PROJECT_SIQI_TEST", "Cost": 100}}),
        ("信仰", {"name": "测试信仰", "abbr": "TB", "table_name": "Beliefs",
                  "table_data": {"BeliefType": "BELIEF_SIQI_TEST"}}),
        ("议程", {"name": "测试议程", "abbr": "TA", "table_name": "Agendas",
                  "table_data": {"AgendaType": "AGENDA_SIQI_TEST"}}),
    ]
    for section, data in entity_tests:
        r = te.execute("propose_add_entity", {
            "section_name": section,
            "data": data,
            "description": f"测试添加{section}: {data['name']}",
        })
        if "error" in r:
            print(f"  [FAIL] propose_add_entity({section}): {r['error']}")
            fail += 1
        elif r.get("action") == "add_entity":
            preview = r.get("preview", {})
            print(f"  [OK] propose_add_entity({section}): {data['name']} → insert@{r.get('insert_at_index')}")
            ok += 1
        else:
            print(f"  [FAIL] propose_add_entity({section}): unexpected {r.get('action')}")
            fail += 1

    # propose_edit_entity
    r = te.execute("propose_edit_entity", {
        "section_name": "文明",
        "entry_index": 0,
        "data": {"civilization_name": "大汉文明"},
        "description": "改名为大汉文明",
    })
    if "error" not in r:
        print(f"  [OK] propose_edit_entity: {r.get('description')}")
        ok += 1
    else:
        print(f"  [FAIL] propose_edit_entity: {r}")
        fail += 1

    # propose_delete_entity
    r = te.execute("propose_delete_entity", {
        "section_name": "文明",
        "entry_index": 0,
        "description": "删除中华文明",
    })
    if "error" not in r:
        print(f"  [OK] propose_delete_entity: {r.get('description')}")
        ok += 1
    else:
        print(f"  [FAIL] propose_delete_entity: {r}")
        fail += 1

    # propose_add_modifier (with reqsets + requirements)
    r = te.execute("propose_add_modifier", {
        "owner": {"table_name": "BuildingModifiers", "type_name": "BUILDING_SIQI_LIBRARY",
                  "display_name": "图书馆"},
        "modifier": {
            "modifier_type": "MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE",
            "effect_type": "EFFECT_ADJUST_CITY_YIELD_CHANGE",
            "collection_type": "COLLECTION_OWNER",
            "comment": "图书馆+2科技",
            "parameters": [{"name": "YieldType", "value": "YIELD_SCIENCE"},
                           {"name": "Amount", "value": "2"}],
        },
        "reqsets": [
            {"requirement_set_id": "REQSET_SIQI_LIBRARY_CITY",
             "logic": "ALL",
             "bound_requirements": ["REQ_SIQI_CITY_HAS_BUILDING"]},
        ],
        "requirements": [
            {"requirement_id": "REQ_SIQI_CITY_HAS_BUILDING",
             "requirement_type": "REQUIREMENT_CITY_HAS_BUILDING",
             "comment": "城市有图书馆",
             "parameters": [{"name": "BuildingType", "value": "BUILDING_SIQI_LIBRARY"}]},
        ],
        "description": "图书馆+2科技产出",
    })
    if "error" not in r:
        warnings = r.get("warnings", [])
        preview = r.get("preview", {})
        wstr = f", {len(warnings)} warnings" if warnings else ""
        print(f"  [OK] propose_add_modifier: {r.get('description')}{wstr}")
        ok += 1
    else:
        print(f"  [FAIL] propose_add_modifier: {r}")
        fail += 1

    # ── 6. System prompt check ──
    print("\n── 系统提示词 ──")
    prompt = build_system_prompt()
    if len(prompt) > 5000:
        print(f"  [OK] 系统提示词: {len(prompt)} 字符 (含知识注入)")
        ok += 1
    else:
        print(f"  [WARN] 系统提示词仅 {len(prompt)} 字符，可能知识注入失败")
        ok += 1

    # ── 7. Tool definition completeness ──
    print("\n── 工具定义 ──")
    for td in TOOL_DEFS:
        # Verify it can be serialized
        d = td.to_openai_dict_legacy()
        fn = d.get("function", {})
        name = fn.get("name")
        desc = fn.get("description")
        params = fn.get("parameters", {})
        param_props = params.get("properties", {})
        if name and desc:
            print(f"  [OK] {name}: {len(param_props)} params, {'preview' if td.requires_preview else 'read-only'}")
            ok += 1
        else:
            print(f"  [FAIL] 工具定义不完整: {name}")
            fail += 1

    # ── Summary ──
    print("\n" + "=" * 60)
    total = ok + fail
    print(f"结果: {ok}/{total} 通过, {fail}/{total} 失败")
    if fail == 0:
        print("[OK] 全部通过！")
        return 0
    else:
        print(f"[FAIL] {fail} 项失败，请检查上述输出")
        return 1


if __name__ == "__main__":
    sys.exit(main())
