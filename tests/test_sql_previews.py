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
        self.assertEqual(set(bundle.keys()), {"PromotionClasses.sql", "UnitPromotions_Text.sql"})
        combined = "\n".join(bundle.values())
        self.assertIn("PROMOTION_CLASS_SIQI_DEMO", combined)
        self.assertIn("PROMOTION_DEMO_DEMO_A", combined)
        self.assertIn("UnitPromotionPrereqs", combined)
        self.assertIn("'PROMOTION_DEMO_DEMO_B', 'PROMOTION_DEMO_DEMO_A'", combined)

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


if __name__ == "__main__":
    unittest.main()
