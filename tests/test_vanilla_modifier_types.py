# -*- coding: utf-8 -*-
"""原版 ModifierType 快照与自定义类型注册判定（Qt-free）。"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ModTools_5_4.project import vanilla_modifier_types as vmt  # noqa: E402


class SnapshotFileTests(unittest.TestCase):
    def test_snapshot_file_exists_and_parses(self) -> None:
        self.assertTrue(vmt.SNAPSHOT_PATH.is_file(), "缺少原版快照文件：%s" % vmt.SNAPSHOT_PATH)
        snapshot = vmt.load_vanilla_modifier_types()
        self.assertGreater(len(snapshot), 500, "原版快照条数异常偏少")
        self.assertTrue(vmt.snapshot_available())

    def test_snapshot_contains_known_vanilla_types(self) -> None:
        snapshot = vmt.load_vanilla_modifier_types()
        for name in (
            "MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT",
            "MODIFIER_PLAYER_DISTRICTS_ADJUST_TOURISM_CHANGE",
            "MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH",
            "MODIFIER_PLAYER_UNITS_GRANT_ABILITY",
        ):
            self.assertIn(name, snapshot, "%s 应属原版类型" % name)
            self.assertTrue(snapshot[name]["effect_type"].startswith("EFFECT_"))

    def test_snapshot_excludes_mod_added_types(self) -> None:
        """本机运行库里的 Mod 自定义类型不得出现在原版快照中。"""
        snapshot = vmt.load_vanilla_modifier_types()
        for name in (
            "MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY",
            "MODIFIER_SIQI0046_PLAYER_UNITS_ADJUST_PROPERTY",
            "MODIFIER_SIQI_0054_L9_IMPROVEMENTS_ATTACH_MODIFIER",
        ):
            self.assertNotIn(name, snapshot, "%s 是 Mod 新增类型，不应算原版" % name)


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = {
            "MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT": {"collection_type": "COLLECTION_PLAYER_CITIES",
                                                     "effect_type": "EFFECT_ADJUST_CITY_EXTRA_DISTRICTS"},
        }

    def test_auto_uses_snapshot(self) -> None:
        self.assertFalse(vmt.resolve_needs_registration(
            "MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", "", snapshot=self.snapshot))
        self.assertTrue(vmt.resolve_needs_registration(
            "MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY", "", snapshot=self.snapshot))

    def test_auto_ignores_legacy_live_db(self) -> None:
        """关键回归：本机库里“有”不再被当成原版“有”。"""
        live = {"MODIFIER_SIQI0046_PLAYER_UNITS_ADJUST_PROPERTY"}
        self.assertTrue(vmt.resolve_needs_registration(
            "MODIFIER_SIQI0046_PLAYER_UNITS_ADJUST_PROPERTY", "",
            snapshot=self.snapshot, legacy_known_types=live, prefixes=("SIQI",)))

    def test_force_new_overrides_snapshot(self) -> None:
        self.assertTrue(vmt.resolve_needs_registration(
            "MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", "new", snapshot=self.snapshot))

    def test_force_vanilla_overrides_snapshot(self) -> None:
        self.assertFalse(vmt.resolve_needs_registration(
            "MODIFIER_WHATEVER", "vanilla", snapshot=self.snapshot))

    def test_fallback_when_snapshot_missing(self) -> None:
        self.assertTrue(vmt.resolve_needs_registration(
            "MODIFIER_BRAND_NEW", "", snapshot={}, legacy_known_types=set(), prefixes=("SIQI",)))
        self.assertFalse(vmt.resolve_needs_registration(
            "MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", "", snapshot={},
            legacy_known_types={"MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT"}, prefixes=("SIQI",)))

    def test_legacy_prefix_match_accepts_both_naming_styles(self) -> None:
        """旧实现认不出 MODIFIER_SIQI0055_X（无下划线），这里按分段匹配修掉。"""
        for name in ("MODIFIER_SIQI_0055_X", "MODIFIER_SIQI0055_X"):
            self.assertTrue(vmt.resolve_needs_registration(
                name, "", snapshot={}, legacy_known_types={name}, prefixes=("SIQI",)),
                "%s 应被识别为本工程命名" % name)
        self.assertFalse(vmt.resolve_needs_registration(
            "MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", "", snapshot={},
            legacy_known_types={"MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT"}, prefixes=("SIQI",)))


class DescribeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = {"MODIFIER_VANILLA_X": {}}

    def test_verdicts(self) -> None:
        cases = [
            ("MODIFIER_VANILLA_X", "", "vanilla"),
            ("MODIFIER_CUSTOM_X", "", "new"),
            ("MODIFIER_CUSTOM_X", "new", "forced_new"),
            ("MODIFIER_VANILLA_X", "vanilla", "forced_vanilla"),
            ("", "", "unknown"),
        ]
        for name, source, expected in cases:
            self.assertEqual(
                vmt.describe_modifier_type(name, source, snapshot=self.snapshot), expected,
                "describe(%r, %r)" % (name, source))

    def test_legacy_verdict_without_snapshot(self) -> None:
        self.assertEqual(vmt.describe_modifier_type("MODIFIER_X", "", snapshot={}), "legacy")


class RealProjectTests(unittest.TestCase):
    """本项目 0055 的两个自建类型必须判定为“需要注册”。"""

    def test_siqi0055_custom_types_need_registration(self) -> None:
        civ = ROOT / "55.CIV"
        if not civ.is_file():
            self.skipTest("55.CIV 不在仓库中")
        data = json.loads(civ.read_text(encoding="utf-8"))
        modifiers = data["workspace"]["修改器"]["data"]["modifiers"]
        custom = {
            str(m.get("modifier_type") or "")
            for m in modifiers
            if vmt.resolve_needs_registration(str(m.get("modifier_type") or ""),
                                              str(m.get("modifier_type_source") or ""))
        }
        self.assertIn("MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY", custom)
        self.assertIn("MODIFIER_SIQI0055_PLAYER_DISTRICTS_ATTACH_MODIFIER", custom)
        # 原版类型不得被误判为需要注册
        self.assertNotIn("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", custom)
        self.assertNotIn("MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER", custom)


class ModifierPageIntegrationTests(unittest.TestCase):
    """GUI 侧接线：HomePage 的判定与三态控件（offscreen）。"""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        from ModTools_5_4.ui.pages.modifier_workspace import HomePage, ModifierRecord

        self.page = HomePage()
        self.record_cls = ModifierRecord

    def _record(self, modifier_type: str, source: str = ""):
        return self.record_cls(modifier_id="MODIFIER_SIQI_0055_T",
                               modifier_type=modifier_type,
                               effect_type="EFFECT_ADJUST_UNIT_PROPERTY",
                               collection_type="COLLECTION_PLAYER_UNITS",
                               modifier_type_source=source)

    def test_page_loaded_snapshot(self) -> None:
        self.assertTrue(self.page._vanilla_modifier_types, "页面未加载原版快照")
        self.assertIn("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", self.page._modifier_meta_index)

    def test_needs_registration_matches_snapshot(self) -> None:
        self.assertFalse(self.page._needs_type_registration(
            self._record("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT")))
        self.assertTrue(self.page._needs_type_registration(
            self._record("MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY")))

    def test_override_beats_snapshot(self) -> None:
        self.assertFalse(self.page._needs_type_registration(
            self._record("MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY", "vanilla")))
        self.assertTrue(self.page._needs_type_registration(
            self._record("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT", "new")))

    def test_custom_type_map_uses_single_source(self) -> None:
        self.page._modifiers = [
            self._record("MODIFIER_PLAYER_CITIES_EXTRA_DISTRICT"),
            self._record("MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY"),
        ]
        collected = self.page._custom_modifier_type_map()
        self.assertEqual(list(collected.keys()), ["MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY"])
        self.assertEqual(collected["MODIFIER_SIQI0055_PLAYER_UNITS_ADJUST_PROPERTY"]["effect_type"],
                         "EFFECT_ADJUST_UNIT_PROPERTY")

    def test_source_combo_exists_with_three_states(self) -> None:
        combo = getattr(self.page, "_modifier_type_source_combo", None)
        self.assertIsNotNone(combo, "缺少「类型来源」三态控件")
        self.assertEqual([combo.itemData(i) for i in range(combo.count())], ["", "new", "vanilla"])


if __name__ == "__main__":
    unittest.main()
