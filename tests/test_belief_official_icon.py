"""Regression tests for belief official fixed icon support.

非万神殿信仰可启用"使用官方固定图标"：Icons.xml 直接引用官方图集
ICON_ATLAS_BELIEFS_PATHEON 的类别 Index（政策卡同款机制），不再生成
自定义图集，也不出现在美术页"未导入图片实体（可选别名）"表中。
万神殿信仰强制自定义图标；已导入自定义图片时以自定义图片为准。
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.ui.pages.art_workspace import (  # noqa: E402
    ArtWorkspacePanel,
    belief_official_icon_index,
    belief_uses_official_icon,
)

from sample_project import build_sample_project  # noqa: E402


def _fresh_state() -> dict[str, object]:
    return {
        "alias_map": {}, "source_map": {}, "need_map": {},
        "extra_xlp_flags": {}, "extra_artdef_flags": {},
        "civs": {}, "moments_map": {}, "leader_xlp_flags": {},
        "art_xml_workspace_config": {}, "art_xml_source_config": {},
        "art_xml_source_path": "",
    }


def _belief_entry(class_type: str, *, use_official: bool = True, icon_path: str = "") -> dict[str, object]:
    entry: dict[str, object] = {
        "name": "测试信仰",
        "abbr": "ABBR",
        "type": "BELIEF_TEST_ABBR",
        "table_name": "Beliefs",
        "table_data": {
            "Name": "测试信仰",
            "Description": "测试描述。",
            "BeliefClassType": class_type,
        },
        "icon_image_name": "ICON_BELIEF_TEST_ABBR",
        "images": {},
        "use_official_icon": use_official,
    }
    if icon_path:
        entry["images"] = {"icon": {"path": icon_path}}
    return entry


class BeliefOfficialIconIndexTestCase(unittest.TestCase):
    def test_class_index_mapping(self) -> None:
        self.assertEqual(belief_official_icon_index("BELIEF_CLASS_WORSHIP"), 22)
        self.assertEqual(belief_official_icon_index("BELIEF_CLASS_FOLLOWER"), 23)
        self.assertEqual(belief_official_icon_index("BELIEF_CLASS_FOUNDER"), 24)
        self.assertEqual(belief_official_icon_index("BELIEF_CLASS_ENHANCER"), 25)

    def test_pantheon_and_unknown_have_no_official_index(self) -> None:
        self.assertIsNone(belief_official_icon_index("BELIEF_CLASS_PANTHEON"))
        self.assertIsNone(belief_official_icon_index(""))
        self.assertIsNone(belief_official_icon_index(None))
        self.assertIsNone(belief_official_icon_index("BELIEF_CLASS_UNKNOWN"))

    def test_uses_official_icon_rules(self) -> None:
        follower = _belief_entry("BELIEF_CLASS_FOLLOWER")
        self.assertTrue(belief_uses_official_icon(follower))
        # 万神殿：即使勾选也不生效
        pantheon = _belief_entry("BELIEF_CLASS_PANTHEON")
        self.assertFalse(belief_uses_official_icon(pantheon))
        # 未勾选
        disabled = _belief_entry("BELIEF_CLASS_FOLLOWER", use_official=False)
        self.assertFalse(belief_uses_official_icon(disabled))
        # 已导入自定义图片：图片优先
        with_icon = _belief_entry("BELIEF_CLASS_FOLLOWER", icon_path="C:/fake/icon.png")
        self.assertFalse(belief_uses_official_icon(with_icon))


class BeliefOfficialIconIconsXmlTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.panel = ArtWorkspacePanel()

    def setUp(self) -> None:
        self.sections = build_sample_project().sections
        self.panel._state = _fresh_state()
        self.panel.refresh_from_sections(self.sections)

    def _icons_xml(self) -> str:
        return self.panel._build_icons_xml()

    def test_official_icon_mode_outputs_atlas_reference_only(self) -> None:
        self.sections["信仰"] = [_belief_entry("BELIEF_CLASS_FOLLOWER")]
        self.panel.refresh_from_sections(self.sections)
        xml = self._icons_xml()
        self.assertIn(
            'Name="ICON_BELIEF_TEST_ABBR" Atlas="ICON_ATLAS_BELIEFS_PATHEON" Index="23"',
            xml,
        )
        self.assertNotIn("ATLAS_ICON_BELIEF_TEST_ABBR", xml)

    def test_disabled_mode_outputs_custom_atlas(self) -> None:
        self.sections["信仰"] = [_belief_entry("BELIEF_CLASS_FOLLOWER", use_official=False)]
        self.panel.refresh_from_sections(self.sections)
        xml = self._icons_xml()
        self.assertIn("ATLAS_ICON_BELIEF_TEST_ABBR", xml)
        self.assertNotIn("ICON_ATLAS_BELIEFS_PATHEON", xml)

    def test_pantheon_never_uses_official_atlas(self) -> None:
        self.sections["信仰"] = [_belief_entry("BELIEF_CLASS_PANTHEON")]
        self.panel.refresh_from_sections(self.sections)
        xml = self._icons_xml()
        self.assertIn("ATLAS_ICON_BELIEF_TEST_ABBR", xml)
        self.assertNotIn("ICON_ATLAS_BELIEFS_PATHEON", xml)

    def test_imported_icon_wins_over_official(self) -> None:
        self.sections["信仰"] = [_belief_entry("BELIEF_CLASS_FOLLOWER", icon_path="C:/fake/icon.png")]
        self.panel.refresh_from_sections(self.sections)
        xml = self._icons_xml()
        self.assertIn("ATLAS_ICON_BELIEF_TEST_ABBR", xml)
        self.assertNotIn("ICON_ATLAS_BELIEFS_PATHEON", xml)

    def test_official_icon_entries_hidden_from_alias_table(self) -> None:
        self.sections["信仰"] = [
            _belief_entry("BELIEF_CLASS_FOLLOWER"),          # 官方图标 → 不出现在别名表
            _belief_entry("BELIEF_CLASS_PANTHEON", use_official=False),  # 万神殿 → 需要别名
        ]
        self.panel.refresh_from_sections(self.sections)
        belief_rows = [r for r in self.panel._alias_rows if r.entity == "belief"]
        self.assertEqual([r.type_name for r in belief_rows], ["BELIEF_TEST_ABBR"])


if __name__ == "__main__":
    unittest.main()
