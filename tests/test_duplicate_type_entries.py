"""Regression tests: duplicate same-type entries must not duplicate rows.

同一 type 的重复条目（复制/手写 .CIV 常见）在 SQL 生成时只取第一条：
Types / 主表 / 文本均不得重复——主表同主键两行会导致游戏加载报错，
同 tag 不同文本的行按字符串去重无效，必须在条目层按 type 去重。
"""
from __future__ import annotations

import copy
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage  # noqa: E402

from sample_project import build_sample_project  # noqa: E402


class DuplicateTypeEntriesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def _project_with_duplicate(self, section: str, mutate) -> object:
        project = build_sample_project()
        entries = project.sections[section]
        dup = copy.deepcopy(entries[0])
        mutate(dup)
        entries.append(dup)
        return project

    def test_civilization_duplicate_type(self) -> None:
        project = self._project_with_duplicate("文明", lambda e: e.__setitem__("civilization_name", "第二文明"))
        self.page._project = project
        data_sql, _text_sql = self.page._build_civilization_sql_pair()
        self.assertEqual(data_sql.count("('CIVILIZATION_SIQI_DEMO', 'KIND_CIVILIZATION')"), 1)
        self.assertEqual(data_sql.count("LOC_CIVILIZATION_SIQI_DEMO_NAME"), 1)

    def test_leader_duplicate_type(self) -> None:
        project = self._project_with_duplicate("领袖", lambda e: e.__setitem__("leader_name", "第二领袖"))
        self.page._project = project
        data_sql, _text_sql = self.page._build_leader_sql_pair()
        self.assertEqual(data_sql.count("('LEADER_SIQI_DEMO', 'KIND_LEADER')"), 1)
        self.assertEqual(data_sql.count("LOC_LEADER_SIQI_DEMO_NAME"), 1)

    def test_district_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二区域"
        project = self._project_with_duplicate("区域", mutate)
        self.page._project = project
        data_sql, _text_sql = self.page._build_district_sql_pair()
        self.assertEqual(data_sql.count("('DISTRICT_SIQI_DEMO', 'KIND_DISTRICT')"), 1)
        self.assertEqual(data_sql.count("LOC_DISTRICT_SIQI_DEMO_NAME"), 1)

    def test_building_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二建筑"
        project = self._project_with_duplicate("建筑", mutate)
        self.page._project = project
        data_sql, _text_sql = self.page._build_building_sql_pair()
        self.assertEqual(data_sql.count("('BUILDING_SIQI_DEMO', 'KIND_BUILDING')"), 1)
        self.assertEqual(data_sql.count("LOC_BUILDING_SIQI_DEMO_NAME"), 1)

    def test_unit_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二单位"
        project = self._project_with_duplicate("单位", mutate)
        self.page._project = project
        unit_sql, _ability_sql, _text_sql = self.page._build_unit_sql_bundle()
        self.assertEqual(unit_sql.count("('UNIT_SIQI_DEMO', 'KIND_UNIT')"), 1)
        self.assertEqual(unit_sql.count("LOC_UNIT_SIQI_DEMO_NAME"), 1)

    def test_improvement_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二改良"
        project = self._project_with_duplicate("改良设施", mutate)
        self.page._project = project
        data_sql, _text_sql = self.page._build_improvement_sql_pair()
        self.assertEqual(data_sql.count("('IMPROVEMENT_SIQI_DEMO', 'KIND_IMPROVEMENT')"), 1)
        self.assertEqual(data_sql.count("LOC_IMPROVEMENT_SIQI_DEMO_NAME"), 1)

    def test_policy_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二政策卡"
        project = self._project_with_duplicate("政策卡", mutate)
        self.page._project = project
        data_sql, _text_sql = self.page._build_policy_sql_pair()
        self.assertEqual(data_sql.count("('POLICY_SIQI_DEMO', 'KIND_POLICY')"), 1)
        self.assertEqual(data_sql.count("LOC_POLICY_SIQI_DEMO_NAME"), 1)

    def test_project_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二项目"
        project = self._project_with_duplicate("项目", mutate)
        self.page._project = project
        data_sql, _text_sql = self.page._build_project_sql_pair()
        self.assertEqual(data_sql.count("('PROJECT_SIQI_DEMO', 'KIND_PROJECT')"), 1)
        self.assertEqual(data_sql.count("LOC_PROJECT_SIQI_DEMO_NAME"), 1)

    def test_agenda_duplicate_type(self) -> None:
        def mutate(e: dict) -> None:
            e["table_data"]["Name"] = "第二议程"
        project = self._project_with_duplicate("议程", mutate)
        self.page._project = project
        data_sql, _text_sql = self.page._build_agenda_sql_pair()
        self.assertEqual(data_sql.count("('AGENDA_SIQI_DEMO', 'KIND_AGENDA')"), 1)
        self.assertEqual(data_sql.count("LOC_AGENDA_SIQI_DEMO_NAME"), 1)

    def test_governor_duplicate_type(self) -> None:
        project = self._project_with_duplicate("总督", lambda e: e.__setitem__("Name", "第二总督"))
        self.page._project = project
        data_sql, _text_sql = self.page._build_governor_sql_pair()
        self.assertEqual(data_sql.count("('GOVERNOR_SIQI_DEMO', 'KIND_GOVERNOR')"), 1)
        self.assertEqual(data_sql.count("LOC_GOVERNOR_SIQI_DEMO_NAME"), 1)

    def test_great_people_duplicate_class(self) -> None:
        def mutate(e: dict) -> None:
            e["class_data"]["Name"] = "第二伟人职业"
        project = self._project_with_duplicate("伟人", mutate)
        self.page._project = project
        gp_sql, gw_sql, _text_sql = self.page._build_great_people_sql_bundle()
        # Types 行（含 KIND_）必须唯一；个体/巨作在 Types + 各自主表各出现一次 = 2 次
        self.assertEqual(gp_sql.count("('GREAT_PERSON_CLASS_SIQI_DEMO', 'KIND_GREAT_PERSON_CLASS')"), 1)
        self.assertEqual(gp_sql.count("('GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_GENERAL', 'KIND_GREAT_PERSON_INDIVIDUAL')"), 1)
        self.assertEqual(gp_sql.count("('GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_WRITER', 'KIND_GREAT_PERSON_INDIVIDUAL')"), 1)
        self.assertEqual(gp_sql.count("'GREAT_PERSON_INDIVIDUAL_SIQI_DEMO_GENERAL'"), 2)
        self.assertEqual(gw_sql.count("('GREATWORK_SIQI_DEMO_BOOK', 'KIND_GREATWORK')"), 1)
        # Types + GreatWorks + GreatWork_YieldChanges 各一次 = 3（无重复）
        self.assertEqual(gw_sql.count("'GREATWORK_SIQI_DEMO_BOOK'"), 3)

    def test_promotion_tree_duplicate_class(self) -> None:
        # 基准：单条晋升树
        self.page._project = build_sample_project()
        base_bundle = self.page._build_promotion_tree_sql_bundle()
        self.assertIsNotNone(base_bundle)
        base_combined = "\n".join(base_bundle.values())
        base_node_count = base_combined.count("'PROMOTION_DEMO_DEMO_A'")
        base_class_count = base_combined.count("('PROMOTION_CLASS_SIQI_DEMO', 'KIND_PROMOTION_CLASS')")

        # 同 type 两条晋升树：class 与节点行数与单条完全一致（第二条整体跳过）
        project = self._project_with_duplicate("单位晋升", lambda e: e.__setitem__("name", "第二晋升树"))
        self.page._project = project
        bundle = self.page._build_promotion_tree_sql_bundle()
        self.assertIsNotNone(bundle)
        combined = "\n".join(bundle.values())
        self.assertEqual(combined.count("('PROMOTION_CLASS_SIQI_DEMO', 'KIND_PROMOTION_CLASS')"), base_class_count)
        self.assertEqual(combined.count("'PROMOTION_DEMO_DEMO_A'"), base_node_count)


if __name__ == "__main__":
    unittest.main()
