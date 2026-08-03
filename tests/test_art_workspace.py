"""Regression tests for art workspace orphan-state handling.

Ensures deleted/renamed objects never show up as "（已丢失对象）" rows in the
美术 workspace, while state carrying real config (music/cultures/artdef
sources) is preserved.
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel  # noqa: E402

from sample_project import build_sample_project  # noqa: E402


def _fresh_state() -> dict[str, object]:
    return {
        "alias_map": {}, "source_map": {}, "need_map": {},
        "extra_xlp_flags": {}, "extra_artdef_flags": {},
        "civs": {}, "moments_map": {}, "leader_xlp_flags": {},
        "art_xml_workspace_config": {}, "art_xml_source_config": {},
        "art_xml_source_path": "",
    }


class ArtWorkspaceOrphanTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.panel = ArtWorkspacePanel()

    def setUp(self) -> None:
        self.sections = build_sample_project().sections
        self.panel._state = _fresh_state()
        self.panel.refresh_from_sections(self.sections)

    def _civ_table_types(self) -> list[str]:
        return [
            self.panel._civ_table.item(r, 0).text()
            for r in range(self.panel._civ_table.rowCount())
            if self.panel._civ_table.item(r, 0)
        ]

    def _source_table_keys(self) -> list[str]:
        return [
            f"{self.panel._source_table.item(r, 0).text()}:{self.panel._source_table.item(r, 1).text()}"
            for r in range(self.panel._source_table.rowCount())
            if self.panel._source_table.item(r, 0) and self.panel._source_table.item(r, 1)
        ]

    def test_matching_sections_show_no_lost_rows(self) -> None:
        self.assertEqual(self._civ_table_types(), ["CIVILIZATION_SIQI_DEMO"])
        self.assertNotIn("已丢失对象", str(self._civ_table_types()))
        self.assertIn("district:DISTRICT_SIQI_DEMO", self._source_table_keys())

    def test_deleted_civ_never_shown_and_empty_ghost_pruned(self) -> None:
        self.sections["文明"] = []
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(self._civ_table_types(), [])
        self.assertEqual(self.panel._state_civ_art_map(), {})

    def test_configured_ghost_hidden_but_preserved(self) -> None:
        self.sections["文明"] = []
        self.panel._state["civs"]["CIVILIZATION_GHOST_CFG"] = {
            "need": True, "music_source": "", "cultures": {}
        }
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(self._civ_table_types(), [])
        self.assertIn("CIVILIZATION_GHOST_CFG", self.panel._state_civ_art_map())

    def test_deleted_district_source_orphan_pruned_when_empty(self) -> None:
        self.sections["区域"] = []
        self.panel._state["need_map"] = {"district:DISTRICT_GHOST": False}
        self.panel._state["source_map"] = {"district:DISTRICT_GHOST": ""}
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(self.panel._state_need_map(), {})
        self.assertEqual(self.panel._state_source_map(), {})
        self.assertNotIn("district:DISTRICT_GHOST", self._source_table_keys())

    def test_deleted_district_source_orphan_with_need_kept(self) -> None:
        self.sections["区域"] = []
        self.panel._state["need_map"] = {"district:DISTRICT_GHOST": True}
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(self.panel._state_need_map(), {"district:DISTRICT_GHOST": True})
        self.assertNotIn("district:DISTRICT_GHOST", self._source_table_keys())

    def test_renamed_civ_old_state_pruned(self) -> None:
        self.sections["文明"][0]["type"] = "CIVILIZATION_SIQI_DEMO_NEW"
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(
            self._civ_table_types(),
            ["CIVILIZATION_SIQI_DEMO_NEW"],
            "renamed civ must not leave a ghost row behind",
        )
        self.assertEqual(list(self.panel._state_civ_art_map().keys()), ["CIVILIZATION_SIQI_DEMO_NEW"])


if __name__ == "__main__":
    unittest.main()
