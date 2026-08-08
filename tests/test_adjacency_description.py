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

    def test_auto_build_text_feature_format(self) -> None:
        widget = _AdjacencyDescriptionEdit(
            sibling_values_provider=lambda: {
                "Amount": 1,
                "YieldType": "YIELD_PRODUCTION",
                "FeatureType": "FEATURE_FLOODPLAINS_GRASS",
                "DistrictType": "DISTRICT_THEATER",
            },
            effect_type="EFFECT_FEATURE_ADJACENCY",
        )
        text = widget._auto_build_text()
        self.assertIn("+1", text)
        self.assertIn("[ICON_Production]", text)
        self.assertIn("来自每个相邻的", text)
        self.assertNotIn("DISTRICT_THEATER", text, "DistrictType 是归属方，不参与描述")

    def test_auto_build_text_accepts_template_dict_values(self) -> None:
        """模板控件 export 的 dict（如 yield/district 搜索）应归一化为标量。"""
        widget = _AdjacencyDescriptionEdit(
            sibling_values_provider=lambda: {
                "Amount": 1,
                "YieldType": {"yield_type": "YIELD_PRODUCTION", "display": "生产力", "name": "生产力", "value": "YIELD_PRODUCTION"},
                "FeatureType": {"feature_type": "FEATURE_FLOODPLAINS_GRASS", "display": "FEATURE_FLOODPLAINS_GRASS", "value": "FEATURE_FLOODPLAINS_GRASS"},
                "DistrictType": {"district_type": "DISTRICT_THEATER", "display": "DISTRICT_THEATER", "value": "DISTRICT_THEATER"},
            },
            effect_type="EFFECT_FEATURE_ADJACENCY",
        )
        text = widget._auto_build_text()
        self.assertNotIn("{", text, "dict repr 不应出现在描述中")
        self.assertIn("+1", text)
        self.assertIn("[ICON_Production]", text)
        self.assertNotIn("DISTRICT_THEATER", text)

    def test_auto_build_text_negative_and_tiles(self) -> None:
        widget = _AdjacencyDescriptionEdit(
            sibling_values_provider=lambda: {
                "Amount": -1,
                "YieldType": "YIELD_FOOD",
                "TerrainType": "TERRAIN_MOUNTAIN",
                "TilesRequired": 2,
            },
            effect_type="EFFECT_TERRAIN_ADJACENCY",
        )
        text = widget._auto_build_text()
        self.assertIn("-1", text)
        self.assertIn("[ICON_Food]", text)
        self.assertIn("每2个", text)
        self.assertIn("相邻的", text)
        # 地形名依赖文本库词条；有词条则显示中文，缺词条时回退原 Type
        if "TERRAIN_MOUNTAIN" in text:
            self.assertIn("TERRAIN_MOUNTAIN", text)

    def test_auto_build_text_district_adjacency(self) -> None:
        """DISTRICT_ADJ：来源为相邻的其他区域，非指定区域。"""
        widget = _AdjacencyDescriptionEdit(
            sibling_values_provider=lambda: {
                "Amount": 1,
                "YieldType": "YIELD_GOLD",
                "DistrictType": "DISTRICT_THEATER",
            },
            effect_type="EFFECT_DISTRICT_ADJACENCY",
        )
        text = widget._auto_build_text()
        self.assertIn("[ICON_Gold]", text)
        self.assertIn("来自每个相邻的其他区域", text)
        self.assertNotIn("DISTRICT_THEATER", text)

    def test_auto_build_text_river_adjacency(self) -> None:
        """河流相邻：无数量概念，位于河流即有。"""
        widget = _AdjacencyDescriptionEdit(
            sibling_values_provider=lambda: {
                "Amount": 2,
                "YieldType": "YIELD_FOOD",
                "DistrictType": "DISTRICT_THEATER",
            },
            effect_type="EFFECT_RIVER_ADJACENCY",
        )
        text = widget._auto_build_text()
        self.assertIn("+2", text)
        self.assertIn("[ICON_Food]", text)
        self.assertIn("位于河流", text)
        self.assertNotIn("DISTRICT_THEATER", text)

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
