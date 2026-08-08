"""Regression tests for adjacency-effect Description auto-naming pipeline."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.pages.modifier_workspace import (  # noqa: E402
    ADJACENCY_DESCRIPTION_EFFECTS,
    ModifierRecord,
    _AdjacencyDescriptionEdit,
)
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage  # noqa: E402
from ModTools_5_4.project.civ_project import create_empty_project  # noqa: E402


class AdjacencyDescriptionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])

    # ---- 自动生成文本格式 ----

    def test_auto_build_text_format(self) -> None:
        widget = _AdjacencyDescriptionEdit(sibling_values_provider=lambda: {
            "Amount": 2,
            "YieldType": "YIELD_PRODUCTION",
            "DistrictType": "DISTRICT_CITY_CENTER",
        })
        text = widget._auto_build_text()
        self.assertIn("+2", text)
        self.assertIn("生产力", text)
        self.assertNotIn("DISTRICT_CITY_CENTER", text, "来源 Type 应本地化为中文")

    def test_auto_build_text_negative_and_tiles(self) -> None:
        widget = _AdjacencyDescriptionEdit(sibling_values_provider=lambda: {
            "Amount": -1,
            "YieldType": "YIELD_FOOD",
            "TerrainType": "TERRAIN_MOUNTAIN",
            "TilesRequired": 2,
        })
        text = widget._auto_build_text()
        self.assertIn("-1", text)
        self.assertIn("食物", text)
        # 地形名依赖文本库词条；有词条则显示中文，缺词条时回退原 Type
        if "TERRAIN_MOUNTAIN" in text:
            self.assertIn("TERRAIN_MOUNTAIN", text)
        self.assertIn("需2地块", text)

    # ---- 覆盖规则 ----

    def test_auto_generate_overwrites_only_auto_or_empty(self) -> None:
        widget = _AdjacencyDescriptionEdit(sibling_values_provider=lambda: {"Amount": 1, "YieldType": "YIELD_GOLD"})
        widget._auto_generate()
        self.assertTrue(widget.is_auto_managed())
        generated = widget.current_value()
        self.assertTrue(generated)

        # 手动修改后，再次生成不应覆盖
        widget.set_value("手动内容")
        self.assertFalse(widget.is_auto_managed())
        widget._auto_generate()
        self.assertEqual(widget.current_value(), "手动内容")

        # 空值时生成应填充
        widget.set_value("")
        widget._auto_generate()
        self.assertTrue(widget.current_value())

    # ---- SQL 与 Text.sql 输出 ----

    def _build_page_with_adjacency_modifier(self, description_value, effect_type="EFFECT_DISTRICT_ADJACENCY"):
        project = create_empty_project("测试")
        page = WorkspacePage()
        page._project = project
        home = page._modifier_workspace
        home._modifiers = [
            ModifierRecord(
                modifier_id="MODIFIER_ADJ_DEMO",
                modifier_type="MODIFIER_CUSTOM_ADJ_DEMO",
                effect_type=effect_type,
                collection_type="COLLECTION_OWNER",
                parameters=[
                    {"name": "Amount", "value": 2},
                    {"name": "YieldType", "value": "YIELD_PRODUCTION"},
                    {"name": "DistrictType", "value": "DISTRICT_CITY_CENTER"},
                    {"name": "Description", "value": description_value},
                ],
            )
        ]
        return page, home

    def test_sql_output_chinese_registers_loc(self) -> None:
        _page, home = self._build_page_with_adjacency_modifier("与城市中心相邻+2生产力")
        sql = home.generate_sql_preview_text()
        self.assertIn("'LOC_MODIFIER_ADJ_DEMO_DESCRIPTION'", sql)
        self.assertIn("'与城市中心相邻+2生产力'", sql)
        self.assertIn("INSERT INTO LocalizedText", sql)

    def test_sql_output_loc_passthrough_no_register(self) -> None:
        _page, home = self._build_page_with_adjacency_modifier("LOC_MY_DESC_TAG")
        sql = home.generate_sql_preview_text()
        self.assertIn("'LOC_MY_DESC_TAG'", sql)
        self.assertNotIn("INSERT INTO LocalizedText", sql)

    def test_text_workspace_includes_description(self) -> None:
        page, _home = self._build_page_with_adjacency_modifier("与城市中心相邻+2生产力")
        text_sql = page._build_text_workspace_preview("sql")
        self.assertIn("LOC_MODIFIER_ADJ_DEMO_DESCRIPTION", text_sql)
        self.assertIn("与城市中心相邻+2生产力", text_sql)

    def test_non_adjacency_description_not_touched(self) -> None:
        _page, home = self._build_page_with_adjacency_modifier(
            "随便一个描述", effect_type="EFFECT_ADD_BELIEF"
        )
        sql = home.generate_sql_preview_text()
        self.assertIn("'随便一个描述'", sql)
        self.assertNotIn("LOC_MODIFIER_ADJ_DEMO_DESCRIPTION", sql)
        self.assertNotIn("INSERT INTO LocalizedText", sql)

    def test_adjacency_effects_set_complete(self) -> None:
        self.assertEqual(
            ADJACENCY_DESCRIPTION_EFFECTS,
            {
                "EFFECT_DISTRICT_ADJACENCY",
                "EFFECT_FEATURE_ADJACENCY",
                "EFFECT_IMPROVEMENT_ADJACENCY",
                "EFFECT_RIVER_ADJACENCY",
                "EFFECT_TERRAIN_ADJACENCY",
            },
        )


if __name__ == "__main__":
    unittest.main()
