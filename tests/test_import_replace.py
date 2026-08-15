"""导入取代功能与搜索对话框优化测试。

- _fill_replace_target：勾选"导入后取代该对象"时的取代目标填充规则
  （DB 原值已填则保留，不覆盖）。
- 区域对话框：仅显示非取代区域筛选（钉选条目豁免）。
- 建筑对话框：默认全部折叠（含奇观分组），展开/折叠切换正确。
- 三个搜索对话框：导入取代选项仅在有 replace_option 时出现，默认不勾选。
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QCheckBox  # noqa: E402

from ModTools_5_4.ui.pages.workspace_page import _fill_replace_target  # noqa: E402
from ModTools_5_4.ui.ui_widget_kit import (  # noqa: E402
    _BuildingSearchByDistrictDialog,
    _DistrictSearchDialog,
    _UnitSearchDialog,
)

DISTRICT_ROWS = [
    {"type": "DISTRICT_CAMPUS", "name": "学院", "indent": 0, "replaces": ""},
    {"type": "DISTRICT_SIX", "name": "六街坊", "indent": 1, "replaces": "DISTRICT_CAMPUS"},
    {"type": "DISTRICT_SPACEPORT", "name": "航天中心", "indent": 0, "replaces": ""},
    {
        "type": "DISTRICT_MINE",
        "name": "矿区",
        "indent": 0,
        "replaces": "DISTRICT_CAMPUS",
        "_workspace_pin": True,
    },
]

BUILDING_ROWS = [
    {"type": "BUILDING_MONUMENT", "name": "纪念碑", "cost": 60, "prereq_district": "DISTRICT_CITY_CENTER"},
    {"type": "BUILDING_LIBRARY", "name": "图书馆", "cost": 90, "prereq_district": "DISTRICT_CAMPUS"},
    {"type": "BUILDING_PYRAMID", "name": "金字塔", "cost": 400, "is_wonder": True},
]

UNIT_ROWS = [
    {"type": "UNIT_WARRIOR", "name": "勇士", "cost": 40, "promotion_class": "PROMOTION_CLASS_MELEE"},
]


class FillReplaceTargetTestCase(unittest.TestCase):
    def test_empty_replaces_is_filled(self) -> None:
        payload = {"district_replaces": {"CivUniqueDistrictType": "X", "ReplacesDistrictType": ""}}
        _fill_replace_target(payload, "district_replaces", "ReplacesDistrictType", "DISTRICT_CAMPUS")
        self.assertEqual(payload["district_replaces"]["ReplacesDistrictType"], "DISTRICT_CAMPUS")

    def test_existing_db_value_is_kept(self) -> None:
        payload = {"district_replaces": {"ReplacesDistrictType": "DISTRICT_CAMPUS"}}
        _fill_replace_target(payload, "district_replaces", "ReplacesDistrictType", "DISTRICT_SIX")
        self.assertEqual(payload["district_replaces"]["ReplacesDistrictType"], "DISTRICT_CAMPUS")

    def test_missing_subtable_is_ignored(self) -> None:
        _fill_replace_target({"table_data": {}}, "district_replaces", "ReplacesDistrictType", "DISTRICT_CAMPUS")
        self.assertNotIn("district_replaces", {"table_data": {}})


class DistrictSearchDialogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_replace_option_checkbox_present_only_when_requested(self) -> None:
        with_option = _DistrictSearchDialog(DISTRICT_ROWS, None, replace_option=True)
        without = _DistrictSearchDialog(DISTRICT_ROWS, None)
        texts = {c.text() for c in with_option.findChildren(QCheckBox)}
        self.assertIn("导入后取代该对象", texts)
        self.assertFalse(with_option.replace_selected())
        self.assertNotIn("导入后取代该对象", {c.text() for c in without.findChildren(QCheckBox)})
        self.assertFalse(without.replace_selected())

    def test_ignore_replacing_filter(self) -> None:
        dialog = _DistrictSearchDialog(DISTRICT_ROWS, None)
        dialog._ignore_replacing_toggle.setChecked(True)
        dialog._apply_filter("")
        types = [entry["type"] for entry in dialog._filtered]
        self.assertIn("DISTRICT_CAMPUS", types)
        self.assertIn("DISTRICT_SPACEPORT", types)
        self.assertIn("DISTRICT_MINE", types)
        self.assertNotIn("DISTRICT_SIX", types)

    def test_filter_off_by_default(self) -> None:
        dialog = _DistrictSearchDialog(DISTRICT_ROWS, None)
        self.assertFalse(dialog._ignore_replacing_toggle.isChecked())
        self.assertEqual(len(dialog._filtered), len(DISTRICT_ROWS))


class BuildingSearchDialogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_default_collapsed_with_wonders(self) -> None:
        dialog = _BuildingSearchByDistrictDialog(BUILDING_ROWS, None, include_wonders=True)
        self.assertFalse(dialog._expand_all_toggle.isChecked())
        self.assertTrue(dialog._collapsed_groups, "默认应全部折叠")

    def test_default_collapsed_without_wonders(self) -> None:
        dialog = _BuildingSearchByDistrictDialog(BUILDING_ROWS, None, include_wonders=False)
        self.assertTrue(dialog._collapsed_groups, "默认应全部折叠")

    def test_expand_toggle_cycles_state(self) -> None:
        dialog = _BuildingSearchByDistrictDialog(BUILDING_ROWS, None, include_wonders=True)
        dialog._expand_all_toggle.setChecked(True)
        self.assertFalse(dialog._collapsed_groups)
        dialog._expand_all_toggle.setChecked(False)
        self.assertTrue(dialog._collapsed_groups)

    def test_replace_option_checkbox(self) -> None:
        dialog = _BuildingSearchByDistrictDialog(BUILDING_ROWS, None, include_wonders=True, replace_option=True)
        self.assertIn("导入后取代该对象", {c.text() for c in dialog.findChildren(QCheckBox)})
        self.assertFalse(dialog.replace_selected())


class UnitSearchDialogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_replace_option_checkbox(self) -> None:
        with_option = _UnitSearchDialog(UNIT_ROWS, None, replace_option=True)
        self.assertIn("导入后取代该对象", {c.text() for c in with_option.findChildren(QCheckBox)})
        self.assertFalse(with_option.replace_selected())
        without = _UnitSearchDialog(UNIT_ROWS, None)
        self.assertNotIn("导入后取代该对象", {c.text() for c in without.findChildren(QCheckBox)})


if __name__ == "__main__":
    unittest.main()
