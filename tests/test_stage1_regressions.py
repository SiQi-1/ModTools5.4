"""阶段 1 修复回归测试（2026-08-16）。

覆盖的修复项：
- #1 空值输出 NULL 而非 ''（违反 AGENT.md 硬规则：仅文本可填 ''，其余必须 NULL）
- #2 SQL 文本值内分号不再截断语句（Text.sql 整节静默丢失）
- #3 修改器「条件」编辑即时持久化（悬空引用）
- #4 可输入选择框占位文案不再污染 .CIV
- #5 议程 AiLists LeaderType 随历史议程加载（过期残留值）
- #6 .civ6proj Teaser 保留原始值（不被 Description 覆盖）
- #7 旧式平铺「基础信息」prefix/infix 迁移 + 加载中禁止回写
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage  # noqa: E402
from ModTools_5_4.ui.pages.modifier_workspace import HomePage as ModifierHomePage  # noqa: E402
from ModTools_5_4.ui.ui_widget_kit import build_template_widget, UnitAbilityTypeTemplate  # noqa: E402
from ModTools_5_4.ui.pages.entity_table_form import AgendaCompositeEditor  # noqa: E402

from sample_project import build_sample_project  # noqa: E402


class SqlNullSemanticsTestCase(unittest.TestCase):
    """#1：空 Prereq 等无 SQL 默认值列输出 NULL 而非 ''（fixture 自带 PrereqTech: ""）。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def setUp(self) -> None:
        self.page._project = build_sample_project()

    def test_district_sql_has_no_empty_string_literal(self) -> None:
        sql = self.page._build_district_sql_pair()[0]
        self.assertNotIn("''", sql, "区域 SQL 不应出现空串字面量")
        self.assertIn("PrereqTech", sql)

    def test_unit_sql_has_no_empty_string_literal(self) -> None:
        sql = self.page._build_unit_sql_bundle()[0]
        self.assertNotIn("''", sql, "单位 SQL 不应出现空串字面量")
        self.assertIn("PrereqTech", sql)

    def test_improvement_sql_has_no_empty_string_literal(self) -> None:
        sql = self.page._build_improvement_sql_pair()[0]
        self.assertNotIn("''", sql, "改良设施 SQL 不应出现空串字面量")

    def test_no_literal_none_string(self) -> None:
        for builder in (
            lambda: self.page._build_district_sql_pair()[0],
            lambda: self.page._build_building_sql_pair()[0],
            lambda: self.page._build_unit_sql_bundle()[0],
            lambda: self.page._build_improvement_sql_pair()[0],
        ):
            sql = builder()
            self.assertNotIn("'None'", sql, "None 不应输出为字符串 'None'")


class SqlSemicolonSplittingTestCase(unittest.TestCase):
    """#2：文本值内含分号不截断语句。"""

    def test_extract_insert_rows_handles_semicolon_in_text(self) -> None:
        sql = (
            "INSERT INTO LocalizedText (Language, Tag, Text) VALUES "
            "('zh_Hans_CN','LOC_A_NAME','含;分号;的文本'),"
            "('zh_Hans_CN','LOC_B_NAME','B');"
        )
        rows = WorkspacePage._extract_insert_rows(sql, "LocalizedText")
        self.assertEqual(len(rows), 2)
        self.assertIn("LOC_A_NAME", rows[0])
        self.assertIn("LOC_B_NAME", rows[1])

    def test_extract_insert_rows_handles_escaped_quotes(self) -> None:
        sql = (
            "INSERT INTO LocalizedText (Language, Tag, Text) VALUES "
            "('zh_Hans_CN','LOC_A_NAME','It''s fine');"
        )
        rows = WorkspacePage._extract_insert_rows(sql, "LocalizedText")
        self.assertEqual(len(rows), 1)
        self.assertIn("It''s fine", rows[0])

    def test_sql_preview_to_xml_handles_semicolon_in_text(self) -> None:
        sql = (
            "INSERT INTO LocalizedText (Language, Tag, Text) VALUES "
            "('zh_Hans_CN','LOC_A_NAME','含;分号');"
        )
        xml_text = WorkspacePage()._sql_preview_to_xml(sql)
        self.assertIn("<Row", xml_text)
        self.assertIn("LOC_A_NAME", xml_text)


class ModifierRequirementPersistTestCase(unittest.TestCase):
    """#3：条件编辑必须即时持久化。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_requirement_editor_changed_persists(self) -> None:
        page = ModifierHomePage()
        page._current_req_index = 0
        page._requirements = [mock.Mock()]
        page._loading_requirement_editor = False
        with mock.patch.object(page, "_persist_current_requirement") as persist:
            page._on_requirement_editor_changed("requirement_id")
            persist.assert_called_once()

    def test_requirement_editor_changed_skipped_while_loading(self) -> None:
        page = ModifierHomePage()
        page._current_req_index = 0
        page._requirements = [mock.Mock()]
        page._loading_requirement_editor = True
        with mock.patch.object(page, "_persist_current_requirement") as persist:
            page._on_requirement_editor_changed("requirement_id")
            persist.assert_not_called()


class PlaceholderPollutionTestCase(unittest.TestCase):
    """#4：未选择时占位文案不得进入导出数据。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_editable_combo_empty_export_is_null(self) -> None:
        widget = build_template_widget("leader_search")
        payload = widget.export_data()
        self.assertIsNone(payload.get("leader_type"))
        self.assertIsNone(payload.get("value"))
        self.assertNotIn("选择或输入", str(payload))

    def test_unit_ability_type_empty_export_is_null(self) -> None:
        widget = UnitAbilityTypeTemplate()
        payload = widget.export_data()
        self.assertIsNone(payload.get("ability_type"))
        self.assertIsNone(payload.get("value"))
        self.assertNotIn("可输入或选择", str(payload))

    def test_editable_combo_set_none_no_signal(self) -> None:
        widget = build_template_widget("project_search")
        with mock.patch.object(widget, "dataChanged") as sig:
            widget.set_current_value(None)
            sig.emit.assert_not_called()


class AgendaAiListsLeaderTestCase(unittest.TestCase):
    """#5：切换条目后 AiLists 的 LeaderType 必须跟随新历史议程。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _make_editor(self) -> AgendaCompositeEditor:
        return AgendaCompositeEditor(
            shared_params_provider=lambda: {"prefix": "SIQI", "infix": 52},
            type_builder=lambda *args: "AGENDA_SIQI_TEST",
            image_widget_factory=lambda size, has_images: QWidget(),
            leader_entries_provider=lambda: [
                {"type": "LEADER_ONE", "name": "领袖一"},
                {"type": "LEADER_TWO", "name": "领袖二"},
            ],
            random_agendas_provider=lambda: [],
            ai_list_types_provider=lambda: ["Bias", "Wonders"],
            custom_reqset_provider=lambda: [],
            text_search_provider=lambda tag: "未知",
        )

    def _entry(self, agenda_type: str, leader_type: str) -> dict[str, object]:
        return {
            "type": agenda_type,
            "abbr": agenda_type.split("_")[-1],
            "table_data": {"Name": agenda_type},
            "historical_agendas": {"LeaderType": leader_type},
            "subtables": {
                "AiLists": [{"ListType": f"AI_LIST_{agenda_type}", "System": "Bias", "LeaderType": leader_type}],
            },
        }

    def test_ai_lists_leader_follows_new_entry(self) -> None:
        editor = self._make_editor()
        editor.set_entry(self._entry("AGENDA_A", "LEADER_ONE"), "议程A")
        editor.set_entry(self._entry("AGENDA_B", "LEADER_TWO"), "议程B")
        self.assertEqual(editor._ai_lists_editor._leader_type, "LEADER_TWO")


class Civ6projTeaserTestCase(unittest.TestCase):
    """#6：Teaser 保留原始值（teaser_raw），不被 Description 覆盖。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def _basic_payload(self, teaser_raw: str) -> dict[str, object]:
        return {
            "format": "MODTOOLS54_BASIC_INFO_WORKSPACE",
            "schema_version": "0.1.0",
            "data": {
                "global_settings": {"prefix": "SIQI", "infix": 52, "language": "简体中文"},
                "project_info": {
                    "mod_name": "测试工程",
                    "file_name": "Siqi_Test",
                    "description": "描述文本",
                    "teaser_raw": teaser_raw,
                },
                "file_info": {},
            },
        }

    def test_teaser_uses_teaser_raw(self) -> None:
        self.page._project = build_sample_project()
        self.page._project.sections["基础信息"] = self._basic_payload("LOC_OLD_TEASER")
        result = self.page._build_civ6proj_preview("Siqi_Test", {}, set())
        teaser_line = [line for line in result.splitlines() if "<Teaser>" in line]
        self.assertTrue(teaser_line, "输出应包含 <Teaser> 元素")
        self.assertIn("LOC_OLD_TEASER", teaser_line[0])
        self.assertNotIn("LOC_OLD_TEASER", "".join(line for line in result.splitlines() if "<Description>" in line))

    def test_teaser_falls_back_to_description_tag(self) -> None:
        self.page._project = build_sample_project()
        self.page._project.sections["基础信息"] = self._basic_payload("")
        result = self.page._build_civ6proj_preview("Siqi_Test", {}, set())
        teaser_line = [line for line in result.splitlines() if "<Teaser>" in line]
        self.assertTrue(teaser_line)
        self.assertIn("LOC_SIQI_TEST_DESCRIPTION", teaser_line[0])


class LegacyFlatBasicInfoTestCase(unittest.TestCase):
    """#7：旧式平铺「基础信息」加载后 prefix 保留，回写不丢。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])

    def test_legacy_flat_basic_info_preserves_prefix(self) -> None:
        page = WorkspacePage()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.CIV"
            payload = {
                "meta": {"format": "CIV_PROJECT", "schema_version": "0.1.0", "project_name": "旧工程"},
                "workspace": {
                    "基础信息": {"prefix": "OLD", "infix": 7, "mod_name": "旧工程"},
                    "文明": [{"name": "旧文明", "abbr": "OLD", "type": "CIVILIZATION_OLD_1"}],
                },
            }
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            page.load_project(path)

            self.assertEqual(page._basic_info_workspace._prefix_edit.text(), "OLD")
            self.assertEqual(page._basic_info_workspace._infix_spin.value(), 7)

            # 模拟用户编辑触发回写：加载后回写应把 prefix 保留进包装格式
            page._basic_info_workspace._emit_workspace_params_changed()
            basic = page._load_basic_info_payload_from_project()
            self.assertEqual(basic["global_settings"]["prefix"], "OLD")
            self.assertEqual(basic["global_settings"]["infix"], 7)

    def test_loading_guard_blocks_writeback(self) -> None:
        """加载过程中（_loading_project=True）的回写必须被禁止。"""
        page = WorkspacePage()
        page._loading_project = True
        page._project = build_sample_project()
        page._project.sections["基础信息"] = {
            "prefix": "OLD",
            "infix": 7,
        }
        page._handle_basic_workspace_params_changed()
        section = page._project.sections["基础信息"]
        # 保持原样（平铺旧值未被空 prefix 覆盖、未被改写）
        self.assertEqual(section.get("prefix"), "OLD")
        self.assertEqual(section.get("infix"), 7)


if __name__ == "__main__":
    unittest.main()
