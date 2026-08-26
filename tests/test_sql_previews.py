"""Regression tests for the per-section SQL/XML preview builders.

Uses the shared sample project (tests/sample_project.py) with one real
entry per content section and asserts the generated preview contains the
expected tables and types.
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.pages.modifier_workspace import ModifierWorkspacePanel  # noqa: E402
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage  # noqa: E402

from sample_project import build_sample_project  # noqa: E402

GROUP_SECTIONS = [
    "文明", "领袖", "区域", "建筑", "单位", "单位晋升", "改良设施",
    "总督", "伟人", "政策卡", "项目", "信仰", "议程",
]
SECTION_TABLE_MARKERS = {
    "文明": "Civilizations",
    "领袖": "Leaders",
    "区域": "Districts",
    "建筑": "Buildings",
    "单位": "Units",
    "改良设施": "Improvements",
    "总督": "Governors",
    "政策卡": "Policies",
    "项目": "Projects",
    "信仰": "Beliefs",
    "议程": "Agendas",
}


class SqlPreviewsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def setUp(self) -> None:
        self.page._project = build_sample_project()

    def _preview(self, section: str, fmt: str):
        return self.page._build_group_data_preview_text(section, fmt)

    def test_every_group_section_produces_sql(self) -> None:
        for section in GROUP_SECTIONS:
            with self.subTest(section=section):
                result = self._preview(section, "sql")
                self.assertTrue(result, section)
                self.assertNotIn("待接入", str(result), section)

    def test_every_group_section_mentions_its_table(self) -> None:
        for section, marker in SECTION_TABLE_MARKERS.items():
            with self.subTest(section=section):
                self.assertIn(marker, str(self._preview(section, "sql")))

    def test_every_group_section_mentions_sample_type(self) -> None:
        for section in GROUP_SECTIONS:
            with self.subTest(section=section):
                self.assertIn("SIQI_DEMO", str(self._preview(section, "sql")))

    def test_xml_format_conversion(self) -> None:
        for section in ("文明", "区域", "建筑", "单位", "改良设施", "政策卡", "项目", "信仰", "议程"):
            with self.subTest(section=section):
                result = self._preview(section, "xml")
                self.assertIn("<Row", str(result), section)

    def test_leader_preview_includes_colors_pair(self) -> None:
        result = self._preview("领袖", "sql")
        self.assertIsInstance(result, dict)
        self.assertIn("Leaders.sql", result)
        self.assertIn("Colors.sql", result)
        self.assertIn("INSERT OR REPLACE INTO PlayerColors", result["Colors.sql"])
        self.assertIn("LEADER_SIQI_DEMO", result["Colors.sql"])

    def test_unit_preview_bundle_keys(self) -> None:
        result = self._preview("单位", "sql")
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"Units.sql", "UnitAbilities.sql"})

    def test_great_people_preview_bundle_keys(self) -> None:
        result = self._preview("伟人", "sql")
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"GreatPeople.sql", "GreatWorks.sql"})
        self.assertIn("GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_GENERAL", result["GreatPeople.sql"])
        self.assertIn("GREATWORK_SIQI_DEMO_BOOK", result["GreatWorks.sql"])
        self.assertIn("LOC_GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_GENERAL_ACTICE", result["GreatPeople.sql"])

    def test_promotion_tree_bundle(self) -> None:
        bundle = self.page._build_promotion_tree_sql_bundle()
        self.assertIsNotNone(bundle)
        self.assertEqual(set(bundle.keys()), {"PromotionClasses.sql"})
        combined = "\n".join(bundle.values())
        self.assertIn("PROMOTION_CLASS_SIQI_DEMO", combined)
        self.assertIn("PROMOTION_DEMO_DEMO_A", combined)
        self.assertIn("UnitPromotionPrereqs", combined)
        self.assertIn("'PROMOTION_DEMO_DEMO_B', 'PROMOTION_DEMO_DEMO_A'", combined)

    def test_promotion_text_merged_into_unified_text(self) -> None:
        text_sql = self.page._build_text_workspace_preview("sql")
        self.assertIn("PROMOTION_DEMO_DEMO_A", text_sql, "晋升文本应并入统一 Text.sql")
        self.assertIn("示例晋升一", text_sql)
        # 晋升文本不再单独产出文件
        manifest_files, _folders, _ok, _path = self.page._project_root_manifest()
        self.assertNotIn(
            True,
            [name.lower().endswith("unitpromotions_text.sql") for name in manifest_files.keys()],
            "不应再生成 UnitPromotions_Text.sql",
        )

    def test_agenda_preview_content(self) -> None:
        sql = self._preview("议程", "sql")
        self.assertIn("AGENDA_SIQI_DEMO", sql)
        self.assertIn("TRAIT_AGENDA_SIQI_DEMO", sql)
        self.assertIn("HistoricalAgendas", sql)
        self.assertIn("AGENDA_EXPANSIONIST", sql)
        self.assertIn("AI_LIST_SIQI_DEMO", sql)

    def test_civilization_sql_pair_has_text(self) -> None:
        data_sql, text_sql = self.page._build_civilization_sql_pair()
        self.assertIn("CIVILIZATION_SIQI_DEMO", data_sql)
        self.assertIn("LOC_CIVILIZATION_SIQI_DEMO_NAME", text_sql)

    def test_text_workspace_preview_contains_fixture_texts(self) -> None:
        sql = self.page._build_text_workspace_preview("sql")
        self.assertIn("LOC_CIVILIZATION_SIQI_DEMO_NAME", sql)
        self.assertIn("示例文明", sql)
        self.assertIn("LOC_UNIT_SIQI_DEMO_NAME", sql)

    def test_empty_sections_still_produce_header(self) -> None:
        from ModTools_5_4.project.civ_project import create_empty_project

        self.page._project = create_empty_project("空")
        sql = self._preview("区域", "sql")
        self.assertTrue(sql)
        self.assertNotIn("SIQI_DEMO", sql)

    def test_moments_sql_preview_runs(self) -> None:
        sql = self.page._build_moments_sql_preview()
        self.assertIsInstance(sql, str)

    # ---- NOT NULL 无 SQL 默认值字段必须始终输出（防止数据库 NOT NULL 约束失败） ----

    def test_district_not_null_no_default_fields_always_emitted(self) -> None:
        sql = self._preview("区域", "sql")
        for column in ("RequiresPlacement", "NoAdjacentCity", "Aqueduct", "InternalOnly",
                       "CaptureRemovesBuildings", "CaptureRemovesCityDefenses",
                       "PlunderType", "MilitaryDomain"):
            with self.subTest(column=column):
                self.assertIn(column, sql)

    def test_improvement_not_null_no_default_fields_always_emitted(self) -> None:
        sql = self._preview("改良设施", "sql")
        for column in ("PlunderType", "Icon"):
            with self.subTest(column=column):
                self.assertIn(column, sql)

    def test_unit_not_null_no_default_fields_always_emitted(self) -> None:
        result = self._preview("单位", "sql")
        unit_sql = result["Units.sql"] if isinstance(result, dict) else str(result)
        for column in ("BaseMoves", "BaseSightRange", "Domain", "FormationClass", "Cost"):
            with self.subTest(column=column):
                self.assertIn(column, unit_sql)

    def test_building_cost_always_emitted(self) -> None:
        self.assertIn("Cost", self._preview("建筑", "sql"))

    def test_fields_with_sql_default_are_omitted(self) -> None:
        district_sql = self._preview("区域", "sql")
        self.assertNotIn("RequiresPopulation", district_sql)  # DEFAULT 1，等于默认值省略
        self.assertNotIn("OnePerCity", district_sql)  # DEFAULT 1
        improvement_sql = self._preview("改良设施", "sql")
        self.assertNotIn("Workable", improvement_sql)  # DEFAULT 1

    def test_district_requires_placement_unchecked_still_emitted(self) -> None:
        project = build_sample_project()
        project.sections["区域"][0]["table_data"]["RequiresPlacement"] = 0
        self.page._project = project
        sql = self._preview("区域", "sql")
        self.assertIn("RequiresPlacement", sql)


def _make_belief(type_name: str, name: str, desc: str) -> dict[str, object]:
    return {
        "name": name,
        "abbr": type_name.split("_")[-1],
        "type": type_name,
        "table_name": "Beliefs",
        "table_data": {
            "Name": name,
            "Description": desc,
            "BeliefClassType": "BELIEF_CLASS_FOLLOWER",
        },
        "Name": name,
        "Description": desc,
        "icon_image_name": f"ICON_{type_name}",
        "images": {},
        "use_official_icon": True,
    }


class BeliefTextDuplicationTestCase(unittest.TestCase):
    """信仰文本重复输出回归：type 前缀重叠 / 同 type 条目不得导致 Text 两遍。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_prefix_overlap_types_not_duplicated_in_text(self) -> None:
        # BELIEF_DEMO 是 BELIEF_DEMO_X 的前缀：分组子串匹配会把后者的行分进两个组，
        # 输出组装必须跨组去重（行只出现一次，归入第一个匹配组）。
        project = build_sample_project()
        project.sections["信仰"] = [
            _make_belief("BELIEF_DEMO", "信仰甲", "甲描述。"),
            _make_belief("BELIEF_DEMO_X", "信仰乙", "乙描述。"),
        ]
        self.page._project = project
        text_sql = self.page._build_text_workspace_preview("sql")
        self.assertEqual(text_sql.count("LOC_BELIEF_DEMO_X_NAME"), 1)
        self.assertEqual(text_sql.count("LOC_BELIEF_DEMO_X_DESCRIPTION"), 1)
        self.assertEqual(text_sql.count("LOC_BELIEF_DEMO_NAME"), 1)

    def test_same_type_entries_not_duplicated_in_data_and_text(self) -> None:
        # 同 type 两条目：Beliefs 表会生成同主键两行（游戏报错），文本同 tag 两行
        # 字符串不同无法按行去重——必须按 type 只取第一条。
        project = build_sample_project()
        project.sections["信仰"] = [
            _make_belief("BELIEF_TITHE", "什一税", "第一份描述。"),
            _make_belief("BELIEF_TITHE", "什一税改", "第二份描述。"),
        ]
        self.page._project = project
        data_sql, _text_sql = self.page._build_belief_sql_pair()
        self.assertEqual(data_sql.count("('BELIEF_TITHE', 'KIND_BELIEF')"), 1, "Types 不应重复")
        self.assertEqual(data_sql.count("LOC_BELIEF_TITHE_NAME"), 1, "Beliefs 表不应出现同主键两行")
        text_sql = self.page._build_text_workspace_preview("sql")
        self.assertEqual(text_sql.count("LOC_BELIEF_TITHE_NAME"), 1)
        self.assertEqual(text_sql.count("LOC_BELIEF_TITHE_DESCRIPTION"), 1)

    def test_normal_text_unified_sql_ends_with_semicolon(self) -> None:
        # 去重计数与实际输出行数必须一致，SQL 以单分号结尾。
        self.page._project = build_sample_project()
        text_sql = self.page._build_text_workspace_preview("sql")
        self.assertTrue(text_sql.rstrip().endswith(";"))
        self.assertEqual(text_sql.count(";"), 1, "LocalizedText VALUES 块只允许一个分号结尾")


class EmptyParamHandlingTestCase(unittest.TestCase):
    """AI 写入 \"\"/null 的参数必须被跳过或输出 NULL，绝不输出 '' 字面量。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_empty_modifier_params_skipped(self) -> None:
        panel = ModifierWorkspacePanel()
        panel._handle_add_modifier()
        record = panel._modifiers[0]
        record.modifier_id = "MODIFIER_TEST_X"
        record.modifier_type = "MODIFIER_PLAYER_UNITS_ADJUST_COMBAT_STRENGTH"
        record.effect_type = "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER"
        record.parameters = [
            {"name": "Amount", "value": 5},
            {"name": "BadEmpty", "value": ""},
            {"name": "BadNone", "value": None},
            {"name": "BadDict", "value": {}},
            {"name": "Good", "value": "TEXT"},
        ]
        sql = panel.generate_sql_preview_text()
        self.assertNotIn("BadEmpty", sql)
        self.assertNotIn("BadNone", sql)
        self.assertNotIn("BadDict", sql)
        self.assertIn("'MODIFIER_TEST_X', 'Amount', 5", sql)
        self.assertIn("'MODIFIER_TEST_X', 'Good', 'TEXT'", sql)
        self.assertNotIn("''", sql)

    def test_empty_requirement_params_skipped(self) -> None:
        from ModTools_5_4.ui.pages.modifier_workspace import RequirementRecord
        panel = ModifierWorkspacePanel()
        panel._requirements.append(
            RequirementRecord(
                requirement_id="REQ_TEST_X",
                requirement_type="REQUIREMENT_PLAYER_IS_HUMAN",
                parameters=[
                    {"name": "Flag", "value": ""},
                    {"name": "Real", "value": 1},
                ],
            )
        )
        sql = panel.generate_sql_preview_text()
        self.assertNotIn("'REQ_TEST_X', 'Flag'", sql)
        self.assertIn("'REQ_TEST_X', 'Real', 1", sql)


if __name__ == "__main__":
    unittest.main()
