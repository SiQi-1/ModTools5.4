"""modgen 回归测试：规则、生成、校验、合并。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
repo_root = str(Path(__file__).resolve().parents[2])
if repo_root not in os.sys.path:
    os.sys.path.insert(0, repo_root)

from modgen.generator import (  # noqa: E402
    GenerateError,
    generate_agenda,
    generate_entry,
    generate_great_person,
    generate_promotion_tree,
    required_fields_to_fill,
)
from modgen.modifier_generator import (  # noqa: E402
    generate_ability,
    generate_modifier,
    generate_requirement,
    generate_requirement_set,
)
from modgen.modifier_validator import check_modifier_data  # noqa: E402
from modgen.merger import load_civ, merge_entry, save_civ  # noqa: E402
from modgen.rules import build_entity_type  # noqa: E402
from modgen.validator import validate_entry, validate_project  # noqa: E402

# 从共享 fixture 校验（fixture 是 GUI 已验证可用的结构）
repo_tests = str(Path(__file__).resolve().parents[2] / "tests")
if repo_tests not in os.sys.path:
    os.sys.path.insert(0, repo_tests)
from sample_project import build_sample_project  # noqa: E402


class RulesTestCase(unittest.TestCase):
    def test_entity_type_format(self) -> None:
        self.assertEqual(
            build_entity_type("SIQI", 35, head="CIVILIZATION", midfix_code="C", short_name="1"),
            "CIVILIZATION_SIQI_C0035_1",
        )
        self.assertEqual(
            build_entity_type("DEMO", 0, head="DISTRICT", midfix_code="D", short_name="DEMO"),
            "DISTRICT_DEMO_DEMO",
        )
        self.assertEqual(
            build_entity_type("", 0, head="UNIT", midfix_code="U", short_name="DEMO"),
            "UNIT_DEMO",
        )

    def test_short_token_sanitized(self) -> None:
        # 非法字符被删除（与 GUI 的 _sanitize_short_token 一致）
        self.assertEqual(build_entity_type("SIQI", 0, head="UNIT", midfix_code="U", short_name="a b-c"), "UNIT_SIQI_ABC")


class GenerateTestCase(unittest.TestCase):
    def test_generate_district(self) -> None:
        entry = generate_entry("区域", prefix="DEMO", infix=1, name="示例区域", abbr="DEMO_A")
        self.assertEqual(entry["type"], "DISTRICT_DEMO_D0001_DEMO_A")
        self.assertEqual(entry["DistrictType"], entry["type"])
        self.assertEqual(entry["table_data"]["Name"], "示例区域")
        self.assertEqual(entry["images"], {})
        self.assertEqual(entry["icon_image_name"], f"ICON_{entry['type']}")

    def test_generate_civilization(self) -> None:
        entry = generate_entry("文明", prefix="SIQI", infix=35, name="示例文明", abbr="DEMO", description="描述")
        self.assertEqual(entry["type"], "CIVILIZATION_SIQI_C0035_DEMO")
        self.assertEqual(entry["civilization_name"], "示例文明")
        self.assertEqual(entry["civilization_description"], "描述")
        self.assertEqual(entry["description_suffix"], "文明")
        self.assertEqual(entry["images"], {})

    def test_generate_leader(self) -> None:
        entry = generate_entry("领袖", prefix="SIQI", infix=35, name="示例领袖", abbr="DEMO")
        self.assertEqual(entry["leader_name"], "示例领袖")
        self.assertEqual(entry["type"], "LEADER_SIQI_L0035_DEMO")

    def test_generate_project_has_icon_size(self) -> None:
        entry = generate_entry("项目", prefix="SIQI", infix=35, name="测试项目", abbr="TEST")
        icon = entry["images"].get("icon", {})
        self.assertEqual(icon.get("target_width"), 256)
        self.assertEqual(icon.get("target_height"), 256)
        self.assertEqual(entry["icon_image_name"], "ICON_PROJECT_SIQI_P0035_TEST")

    def test_generate_belief_no_image_slot(self) -> None:
        entry = generate_entry("信仰", prefix="SIQI", infix=35, name="测试信仰", abbr="TEST")
        self.assertEqual(entry["images"], {})
        self.assertEqual(entry["icon_image_name"], "ICON_BELIEF_SIQI_B0035_TEST")

    def test_generate_unknown_section_raises(self) -> None:
        with self.assertRaises(GenerateError):
            generate_entry("不存在", prefix="X", infix=0, name="x", abbr="x")

    def test_generate_great_person(self) -> None:
        entry = generate_great_person(
            prefix="SIQI", infix=35, name="示例伟人", class_abbr="SCIENTIST", unit_abbr="SCIENTIST",
            individuals=[
                {"mode": "activation", "abbr": "NEWTON", "name_cn": "牛顿"},
                {"mode": "greatwork", "abbr": "WRITER", "name_cn": "作家",
                 "great_works": [{"abbr": "BOOK", "name_cn": "巨作"}]},
            ],
        )
        self.assertEqual(entry["type"], "GREAT_PERSON_CLASS_SIQI_G0035_SCIENTIST")
        self.assertEqual(entry["class_data"]["UnitType"], "UNIT_SIQI_U0035_SCIENTIST")
        self.assertEqual(len(entry["individuals"]), 2)
        ind = entry["individuals"][0]
        self.assertEqual(ind["mode"], "activation")
        self.assertEqual(ind["GreatPersonIndividualType"], "GREAT_PERSON_INDIVIDUAL_SIQI_G0035_NEWTON")
        self.assertEqual(ind["ActionCharges"], 1)
        greatwork = entry["individuals"][1]
        self.assertEqual(greatwork["mode"], "greatwork")
        self.assertEqual(greatwork["ActionCharges"], 0)
        self.assertEqual(greatwork["great_works"][0]["GreatWorkType"], "GREATWORK_SIQI_G0035_BOOK")

    def test_generate_promotion_tree(self) -> None:
        entry = generate_promotion_tree(
            prefix="SIQI", infix=35, name="示例晋升树", tree_abbr="MILITARY",
            nodes=[
                {"abbr": "A", "name_cn": "晋升一"},
                {"abbr": "B", "name_cn": "晋升二", "level": 2, "prereq_indices": [0]},
            ],
        )
        self.assertEqual(entry["type"], "PROMOTION_CLASS_SIQI_P0035_MILITARY")
        self.assertEqual(len(entry["nodes"]), 2)
        self.assertEqual(entry["nodes"][0]["level"], 1)
        self.assertEqual(entry["nodes"][1]["prereq_indices"], [0])

    def test_generate_agenda(self) -> None:
        entry = generate_agenda(
            prefix="SIQI", infix=35, name="示例议程", agenda_abbr="WAR",
            description="描述", leader_abbr="DEMO",
        )
        self.assertEqual(entry["type"], "AGENDA_SIQI_A0035_WAR")
        self.assertEqual(entry["historical_agendas"]["LeaderType"], "LEADER_SIQI_L0035_DEMO")
        self.assertIn("ExclusiveAgendas", entry["subtables"])
        self.assertIn("AgendaModifiers", entry["subtables"])


class ValidatorTestCase(unittest.TestCase):
    def test_generated_entry_passes_validation(self) -> None:
        for section in ("文明", "领袖", "区域", "建筑", "改良设施", "总督", "政策卡", "项目", "信仰", "议程"):
            entry = generate_entry(section, prefix="SIQI", infix=1, name="测试", abbr="TEST")
            errors = validate_entry(section, entry, prefix="SIQI", infix=1)
            self.assertEqual(errors, [], f"{section}: {errors}")

    def test_generated_unit_requires_formation_class(self) -> None:
        """单位必填且无默认值的字段（FormationClass）需 AI 填写。"""
        self.assertIn("FormationClass", required_fields_to_fill("单位"))
        entry = generate_entry("单位", prefix="SIQI", infix=1, name="测试", abbr="TEST")
        entry["table_data"]["FormationClass"] = "FORMATION_CLASS_LAND_COMBAT"
        errors = validate_entry("单位", entry, prefix="SIQI", infix=1)
        self.assertEqual(errors, [], f"{errors}")

    def test_fixture_entries_pass_validation(self) -> None:
        fixture = build_sample_project().sections
        for section in ("文明", "领袖", "区域", "建筑", "单位", "单位晋升", "改良设施", "总督", "伟人", "政策卡", "项目", "信仰", "议程"):
            entries = fixture.get(section, [])
            if not entries:
                continue
            errors = validate_entry(section, entries[0], prefix="DEMO", infix=0)
            self.assertEqual(errors, [], f"{section}: {errors}")

    def test_errors_detected(self) -> None:
        entry = generate_entry("区域", prefix="SIQI", infix=1, name="测试", abbr="TEST")
        entry["abbr"] = ""  # 清空简称
        errors = validate_entry("区域", entry, prefix="SIQI", infix=1)
        self.assertTrue(any("abbr" in e for e in errors), errors)

        entry2 = generate_entry("区域", prefix="SIQI", infix=1, name="测试", abbr="TEST")
        entry2["type"] = "WRONG_TYPE"
        errors2 = validate_entry("区域", entry2, prefix="SIQI", infix=1)
        self.assertTrue(any("type" in e for e in errors2), errors2)

    def test_validate_project(self) -> None:
        project = {"workspace": {"文明": []}}
        self.assertEqual(validate_project(project), [])
        bad = {"workspace": {"文明": [{"type": "CIVILIZATION_SIQI_C0001_X", "abbr": "", "name": ""}]}}
        errors = validate_project(bad, prefix="SIQI", infix=1)
        self.assertTrue(errors)

    def test_project_workspace_params_autodetect(self) -> None:
        project = {"workspace": {
            "基础信息": {"data": {"shared_workspace_params": {"prefix": "SIQI", "infix": 32}}},
            "区域": [{"type": "DISTRICT_SIQI_D0032_1", "abbr": "1", "name": "测试",
                      "table_data": {"Name": "测试", "MilitaryDomain": "NO_DOMAIN"}}],
        }}
        errors = validate_project(project)  # 不传 prefix/infix，自动读取
        self.assertEqual(errors, [], f"{errors}")


class MergerTestCase(unittest.TestCase):
    def test_merge_adds_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.CIV"
            payload = {"meta": {"format": "CIV_PROJECT", "schema_version": "0.1.0", "project_name": "测试"}, "workspace": {}}
            save_civ(path, payload)

            entry = generate_entry("区域", prefix="SIQI", infix=1, name="测试区域", abbr="TEST")
            loaded = load_civ(path)
            merge_entry(loaded, "区域", entry, prefix="SIQI", infix=1)
            save_civ(path, loaded)

            again = load_civ(path)
            merge_entry(again, "区域", entry, prefix="SIQI", infix=1)
            save_civ(path, again)

            final = load_civ(path)
            self.assertEqual(len(final["workspace"]["区域"]), 1, "同 type 合并应去重")
            self.assertTrue(path.with_suffix(".CIV.bak").exists(), "应自动备份")

    def test_merge_rejects_invalid_entry(self) -> None:
        payload = {"workspace": {}}
        with self.assertRaises(Exception):
            merge_entry(payload, "区域", {"type": "BAD", "abbr": "", "name": ""}, prefix="SIQI", infix=1)


class ModifierTestCase(unittest.TestCase):
    def test_generate_modifier(self) -> None:
        entry = generate_modifier(
            prefix="SIQI", infix=35, effect_type="EFFECT_DISTRICT_ADJACENCY",
            collection_type="COLLECTION_OWNER", desc="ADJ_STRENGTH",
            parameters=[{"name": "Amount", "value": 2}],
        )
        self.assertEqual(entry["modifier_id"], "MODIFIER_SIQI_0035_ADJ_STRENGTH")
        self.assertEqual(entry["effect_type"], "EFFECT_DISTRICT_ADJACENCY")
        self.assertEqual(entry["parameters"], [{"name": "Amount", "value": 2}])

    def test_generate_modifier_rejects_unknown_effect(self) -> None:
        with self.assertRaises(ValueError):
            generate_modifier(prefix="SIQI", infix=1, effect_type="EFFECT_NOT_EXIST", desc="X")

    def test_generate_modifier_param_skeleton(self) -> None:
        entry = generate_modifier(prefix="SIQI", infix=1, effect_type="EFFECT_DISTRICT_ADJACENCY", desc="X")
        names = {p["name"] for p in entry["parameters"]}
        self.assertIn("Amount", names)
        self.assertIn("YieldType", names)
        self.assertIn("DistrictType", names)

    def test_generate_requirement(self) -> None:
        entry = generate_requirement(
            prefix="SIQI", infix=35, requirement_type="REQUIREMENT_PLOT_ADJACENT_FEATURE_TYPE_MATCHES",
            desc="ADJ_FOREST",
        )
        self.assertEqual(entry["requirement_id"], "REQUIREMENT_SIQI_0035_ADJ_FOREST")
        self.assertEqual(entry["requirement_type"], "REQUIREMENT_PLOT_ADJACENT_FEATURE_TYPE_MATCHES")

    def test_generate_requirement_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            generate_requirement(prefix="SIQI", infix=1, requirement_type="REQUIREMENT_NOT_EXIST", desc="X")

    def test_generate_reqset(self) -> None:
        entry = generate_requirement_set(
            prefix="SIQI", infix=35, desc="MILITARY", logic="ANY",
            requirements=["REQUIREMENT_SIQI_0035_A", "REQUIREMENT_SIQI_0035_B"],
        )
        self.assertEqual(entry["requirement_set_id"], "REQSET_SIQI_0035_MILITARY")
        self.assertEqual(entry["logic"], "ANY")
        self.assertEqual(len(entry["bound_requirements"]), 2)

    def test_generate_ability(self) -> None:
        entry = generate_ability(prefix="SIQI", infix=35, abbr="DEMO_ABILITY", name_zh="测试能力")
        self.assertEqual(entry["unit_ability_type"], "ABILITY_SIQI_A0035_DEMO_ABILITY")

    def test_check_modifier_data_catches_bad_params(self) -> None:
        data = {
            "modifiers": [{
                "modifier_id": "MODIFIER_X",
                "modifier_type": "MODIFIER_X",
                "effect_type": "EFFECT_DISTRICT_ADJACENCY",
                "collection_type": "COLLECTION_OWNER",
                "parameters": [{"name": "WrongParam", "value": 1}],
                "owner_reqset": "REQSET_MISSING",
            }],
            "requirement_sets": [],
            "requirements": [],
            "unit_abilities": [],
        }
        errors, warnings = check_modifier_data(data)
        joined = "\n".join(errors)
        self.assertIn("WrongParam", joined, "参数名不属于 EffectType 应报错")
        self.assertIn("REQSET_MISSING", joined, "引用不存在的 reqset 应报错")

    def test_check_modifier_data_pass_on_generated(self) -> None:
        data = {
            "modifiers": [
                generate_modifier(prefix="SIQI", infix=35, effect_type="EFFECT_DISTRICT_ADJACENCY",
                                  collection_type="COLLECTION_OWNER", desc="A",
                                  parameters=[{"name": "Amount", "value": 1},
                                              {"name": "YieldType", "value": "YIELD_PRODUCTION"},
                                              {"name": "DistrictType", "value": "DISTRICT_CITY_CENTER"}]),
            ],
            "requirement_sets": [],
            "requirements": [],
            "unit_abilities": [],
        }
        errors, _warnings = check_modifier_data(data)
        self.assertEqual(errors, [], f"{errors}")

    def test_validate_project_checks_modifier_section(self) -> None:
        project = {"workspace": {
            "修改器": {"data": {
                "modifiers": [{
                    "modifier_id": "MODIFIER_X",
                    "modifier_type": "MODIFIER_X",
                    "effect_type": "EFFECT_NOT_REAL",
                    "parameters": [],
                }],
                "requirement_sets": [], "requirements": [], "unit_abilities": [],
            }},
        }}
        errors = validate_project(project)
        self.assertTrue(any("EffectType" in e for e in errors), errors)


def _has_game_db() -> bool:
    from modgen.search import default_game_db_path, resolve_db_paths

    gdb, _tdb = resolve_db_paths(None, None)
    return gdb is not None and gdb.exists()


class SearchRegistryTestCase(unittest.TestCase):
    """检索注册表（无需游戏库）：科技/市政效果必须已在检索范围内。"""

    def test_technology_and_civic_registered(self) -> None:
        from modgen.search import BINDING_TABLES, OBJECT_TYPES

        self.assertIn("technology", OBJECT_TYPES)
        self.assertIn("civic", OBJECT_TYPES)
        self.assertEqual(OBJECT_TYPES["technology"]["table"], "Technologies")
        self.assertEqual(OBJECT_TYPES["technology"]["type_col"], "TechnologyType")
        self.assertEqual(OBJECT_TYPES["civic"]["table"], "Civics")
        self.assertEqual(OBJECT_TYPES["civic"]["type_col"], "CivicType")
        self.assertIn(("TechnologyModifiers", "TechnologyType", "ModifierId", "technology"), BINDING_TABLES)
        self.assertIn(("CivicModifiers", "CivicType", "ModifierId", "civic"), BINDING_TABLES)


@unittest.skipUnless(_has_game_db(), "无游戏数据库，跳过 search 测试")
class SearchTestCase(unittest.TestCase):
    """modgen search：效果/对象查询（知识获取的内置途径）。"""

    def setUp(self) -> None:
        import sqlite3

        from modgen.search import resolve_db_paths

        self.gdb, self.tdb = resolve_db_paths(None, None)
        self.conn = sqlite3.connect(str(self.gdb))
        self.loc = sqlite3.connect(str(self.tdb)) if self.tdb else None

    def tearDown(self) -> None:
        self.conn.close()
        if self.loc is not None:
            self.loc.close()

    def test_english_keyword_finds_war_abilities(self) -> None:
        from modgen.search import search_keyword

        results = search_keyword(self.conn, self.loc, "WAR")
        self.assertTrue(results, "WAR 应命中持有相关能力的对象")
        self.assertTrue(any(item["hit"] == "能力" for item in results))

    def test_chinese_effect_word_expands_to_english(self) -> None:
        from modgen.search import search_keyword

        results = search_keyword(self.conn, self.loc, "宣战")
        self.assertTrue(results, "中文效果词'宣战'应经映射命中")
        self.assertTrue(any(item["hit"] == "能力" for item in results))

    def test_chinese_object_search_with_text_db(self) -> None:
        from modgen.search import search_keyword

        if self.loc is None:
            self.skipTest("无文本库")
        results = search_keyword(self.conn, self.loc, "农场")
        types = {item["type"] for item in results}
        self.assertIn("IMPROVEMENT_FARM", types, "中文'农场'应命中改良设施")
        self.assertIn("TRAIT_CIVILIZATION_KHMER_BARAYS", types, "应命中相邻农场加成的高棉特质")

    def test_object_modifier_summary_includes_farm_solution(self) -> None:
        """相邻农场+食物 的现成实现（EFFECT_ADJUST_PLOT_YIELD）应能被查到手。"""
        from modgen.search import object_modifier_summary

        mods = object_modifier_summary(
            self.conn, self.loc, "trait", "TRAIT_CIVILIZATION_KHMER_BARAYS"
        )
        farm_mod = next(
            (m for m in mods if m["modifier_id"] == "TRAIT_FARM_AQUEDUCT_ADJECENCY_FOOD"), None
        )
        self.assertIsNotNone(farm_mod, "大人工湖的相邻农场食物 modifier 应存在")
        self.assertEqual(farm_mod["effect_type"], "EFFECT_ADJUST_PLOT_YIELD")
        self.assertIn("YieldType=YIELD_FOOD", farm_mod["args"])
        self.assertTrue(
            any("REQUIREMENT_PLOT_IMPROVEMENT_TYPE_MATCHES" in rs for rs in farm_mod["reqsets"]),
            "条件应包含地块改良匹配（农场判定）",
        )

    def test_unknown_effect_error_hints_search(self) -> None:
        """generate-modifier 未知 EffectType 报错应附 search 引导。"""
        from modgen.cli import main

        exit_code = main(["generate-modifier", "--effect", "EFFECT_NOT_REAL", "--desc", "X"])
        self.assertNotEqual(exit_code, 0)

    def test_technology_civic_effects_searchable(self) -> None:
        """科技/市政的效果：绑定的 Modifier 能反查到对象，详情能列出实现。"""
        from modgen.search import object_modifier_summary, search_keyword

        for table, obj_col, category in (
            ("TechnologyModifiers", "TechnologyType", "technology"),
            ("CivicModifiers", "CivicType", "civic"),
        ):
            with self.subTest(table=table):
                row = self.conn.execute(
                    f"SELECT {obj_col}, ModifierId FROM {table} LIMIT 1"
                ).fetchone()
                if row is None:
                    self.skipTest(f"游戏库无 {table} 数据")
                obj_type, modifier_id = str(row[0] or ""), str(row[1] or "")
                results = search_keyword(self.conn, self.loc, modifier_id)
                self.assertTrue(
                    any(
                        item.get("category") == category and item.get("type") == obj_type
                        for item in results
                    ),
                    f"{modifier_id} 应反查到 {category} 对象 {obj_type}",
                )
                mods = object_modifier_summary(self.conn, self.loc, category, obj_type)
                self.assertTrue(
                    any(m["modifier_id"] == modifier_id for m in mods),
                    f"{category} 详情应列出其绑定的 Modifier {modifier_id}",
                )


class CustomModifierTypeRegistrationTestCase(unittest.TestCase):
    """自定义 ModifierType 注册判定（原版快照驱动，不依赖本机装过哪些 Mod）。"""

    def _modifier(self, modifier_type: str, source: str = "") -> dict:
        return {
            "modifier_id": "MODIFIER_SIQI_0055_TEST",
            "modifier_type": modifier_type,
            "comment": "t",
            "owner_reqset": None,
            "subject_reqset": None,
            "run_once": False,
            "new_only": False,
            "permanent": False,
            "owner_stack_limit": 0,
            "subject_stack_limit": 0,
            "effect_type": "EFFECT_ADJUST_UNIT_PROPERTY",
            "collection_type": "COLLECTION_PLAYER_UNITS",
            "modifier_type_source": source or None,
            "preview_text": None,
            "parameters": [{"name": "Amount", "value": 1}, {"name": "Key", "value": "X"}],
        }

    def test_snapshot_available(self) -> None:
        from modgen.vanilla_types import snapshot_available

        self.assertTrue(snapshot_available(), "缺少原版快照，先跑 modgen.tools.extract_vanilla_modifier_types")

    def test_vanilla_type_no_registration_warning(self) -> None:
        data = {"modifiers": [self._modifier("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT")],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        errors, warnings = check_modifier_data(data)
        self.assertEqual(errors, [])
        self.assertFalse(any("Types + DynamicModifiers" in w for w in warnings),
                         "原版类型不应提示需要注册")

    def test_custom_type_warns_pending_registration(self) -> None:
        data = {"modifiers": [self._modifier("MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY")],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        errors, warnings = check_modifier_data(data)
        self.assertEqual(errors, [])
        self.assertTrue(any("Types + DynamicModifiers" in w for w in warnings),
                        "自定义类型应提示将补注册行")

    def test_force_new_on_vanilla_type_is_error(self) -> None:
        data = {"modifiers": [self._modifier("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", "new")],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        errors, _warnings = check_modifier_data(data)
        self.assertTrue(any("主键冲突" in e for e in errors))

    def test_force_vanilla_on_custom_type_is_error(self) -> None:
        data = {"modifiers": [self._modifier("MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY", "vanilla")],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        errors, _warnings = check_modifier_data(data)
        self.assertTrue(any("加载失败" in e for e in errors))

    def test_generator_emits_source_field(self) -> None:
        entry = generate_modifier(
            prefix="SIQI",
            infix=55,
            effect_type="EFFECT_ADJUST_UNIT_PROPERTY",
            collection_type="COLLECTION_PLAYER_UNITS",
            desc="TEST",
        )
        self.assertIn("modifier_type_source", entry)
        self.assertIsNone(entry["modifier_type_source"])


class ModifierStringsPreviewTestCase(unittest.TestCase):
    """战斗力类 modifier 必须给 ModifierStrings 预览文本（否则战斗面板不显示来源）。"""

    def _strength_modifier(self, preview: str) -> dict:
        return {
            "modifier_id": "MODIFIER_SIQI_0055_MIL_STRENGTH_5",
            "modifier_type": "MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH",
            "comment": "军事单位+5战斗力",
            "owner_reqset": None,
            "subject_reqset": None,
            "run_once": False,
            "new_only": False,
            "permanent": False,
            "owner_stack_limit": 0,
            "subject_stack_limit": 0,
            "effect_type": "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER",
            "collection_type": "COLLECTION_UNIT_COMBAT",
            "preview_text": preview,
            "parameters": [{"name": "Amount", "value": 5}],
        }

    def test_missing_preview_warns(self) -> None:
        data = {"modifiers": [self._strength_modifier("")],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        errors, warnings = check_modifier_data(data)
        self.assertEqual(errors, [])
        self.assertTrue(any("ModifierStrings" in w for w in warnings))

    def test_with_preview_no_warning(self) -> None:
        data = {"modifiers": [self._strength_modifier("+{1_Amount} [ICON_Strength] 战斗力（恶魔的助威）")],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        errors, warnings = check_modifier_data(data)
        self.assertEqual(errors, [])
        self.assertFalse(any("ModifierStrings" in w for w in warnings))

    def test_non_supported_effect_not_warned(self) -> None:
        modifier = self._strength_modifier("")
        modifier["effect_type"] = "EFFECT_ADJUST_CITY_YIELD_CHANGE"
        modifier["modifier_type"] = "MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE"
        data = {"modifiers": [modifier],
                "requirement_sets": [], "requirements": [], "unit_abilities": []}
        _errors, warnings = check_modifier_data(data)
        self.assertFalse(any("ModifierStrings" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
