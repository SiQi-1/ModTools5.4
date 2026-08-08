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


if __name__ == "__main__":
    unittest.main()
