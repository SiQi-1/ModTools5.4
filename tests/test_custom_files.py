"""project/custom_files 单元测试：路径净化 + 动作分类 + 合并（GUI/modgen 单一实现）。"""
from __future__ import annotations

import unittest

from ModTools_5_4.project.custom_files import (
    classify_custom_path,
    looks_like_ui_context_xml,
    merge_action_entry,
    remove_action_files,
    sanitize_relative_path,
)


class SanitizeRelativePathTestCase(unittest.TestCase):
    def test_normal(self) -> None:
        self.assertEqual(sanitize_relative_path("Scripts/My.lua"), "Scripts/My.lua")
        self.assertEqual(sanitize_relative_path("Data\\Extra.sql"), "Data/Extra.sql")

    def test_rejects_absolute_and_drive(self) -> None:
        self.assertIsNone(sanitize_relative_path("/etc/passwd"))
        self.assertIsNone(sanitize_relative_path("C:/evil.sql"))

    def test_rejects_traversal(self) -> None:
        self.assertIsNone(sanitize_relative_path("../evil.sql"))
        self.assertIsNone(sanitize_relative_path("Data/../../evil.sql"))
        self.assertIsNone(sanitize_relative_path("a/./../b.sql"))

    def test_rejects_empty(self) -> None:
        self.assertIsNone(sanitize_relative_path(""))
        self.assertIsNone(sanitize_relative_path("/"))


class LooksLikeUiContextXmlTestCase(unittest.TestCase):
    def test_context_root(self) -> None:
        self.assertTrue(looks_like_ui_context_xml("<?xml version='1.0'?><Context></Context>"))
        self.assertTrue(looks_like_ui_context_xml("<Context xmlns='http://schemas.microsoft.com'></Context>"))

    def test_other_root_and_bad_xml(self) -> None:
        self.assertFalse(looks_like_ui_context_xml("<GameInfo></GameInfo>"))
        self.assertFalse(looks_like_ui_context_xml("not xml"))
        self.assertFalse(looks_like_ui_context_xml(""))


class ClassifyCustomPathTestCase(unittest.TestCase):
    def _specs(self, rel: str, *, peer: str = "", read_text=None) -> list[tuple[str, str, str, int]]:
        peers = {peer} if peer else set()

        def _peer_exists(path: str) -> bool:
            return path.lower() in {p.lower() for p in peers}

        return classify_custom_path(rel, peer_exists=_peer_exists, read_text=read_text)

    def test_data_sql(self) -> None:
        self.assertEqual(self._specs("Data/Extra.sql"), [("in_game", "UpdateDatabase", "UpdateDatabase", 10000)])

    def test_scripts_lua(self) -> None:
        self.assertEqual(
            self._specs("Scripts/My.lua"),
            [("in_game", "AddGameplayScripts", "AddGameplayScripts", 9500)],
        )

    def test_import_lua(self) -> None:
        self.assertEqual(self._specs("Import/Init.lua"), [("in_game", "ImportFiles", "ImportFiles", 9700)])

    def test_icons_both_scopes(self) -> None:
        self.assertEqual(
            self._specs("Icons/My_Icons.xml"),
            [
                ("front", "UpdateIcons", "UpdateIcons", 1000),
                ("in_game", "UpdateIcons", "UpdateIcons", 1000),
            ],
        )

    def test_text_both_scopes(self) -> None:
        self.assertEqual(
            self._specs("Text/My_Text.sql"),
            [
                ("front", "UpdateText", "UpdateText", 0),
                ("in_game", "UpdateText", "UpdateText", 0),
            ],
        )

    def test_ui_pair(self) -> None:
        read = {"UI/Panel.xml": "<Context></Context>"}
        self.assertEqual(
            self._specs("UI/Panel.xml", peer="UI/Panel.lua", read_text=lambda p: read.get(p, "")),
            [("in_game", "AddUserInterfaces", "AddUserInterfaces", 9600)],
        )
        self.assertEqual(
            self._specs("UI/Panel.lua", peer="UI/Panel.xml", read_text=lambda p: read.get(p, "")),
            [("in_game", "AddUserInterfaces", "AddUserInterfaces", 9600)],
        )

    def test_ui_xml_without_peer_falls_to_database(self) -> None:
        self.assertEqual(self._specs("UI/Panel.xml"), [("in_game", "UpdateDatabase", "UpdateDatabase", 10000)])

    def test_ui_lua_without_peer_unregistered(self) -> None:
        self.assertEqual(self._specs("UI/Panel.lua"), [])

    def test_ui_xml_not_context_falls_to_database(self) -> None:
        self.assertEqual(
            self._specs("UI/Panel.xml", peer="UI/Panel.lua", read_text=lambda _p: "<GameInfo></GameInfo>"),
            [("in_game", "UpdateDatabase", "UpdateDatabase", 10000)],
        )

    def test_images_unregistered(self) -> None:
        self.assertEqual(self._specs("IMG/icon.png"), [])
        self.assertEqual(self._specs("Textures/a.dds"), [])

    def test_traversal_unregistered(self) -> None:
        self.assertEqual(self._specs("../evil.sql"), [])


class MergeActionEntryTestCase(unittest.TestCase):
    def test_creates_entry(self) -> None:
        entries: list[dict] = []
        added = merge_action_entry(
            entries, action_type="UpdateDatabase", action_id="UpdateDatabase",
            files=["Data/A.sql"], load_order=9999, origin="custom",
        )
        self.assertEqual(added, 1)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["type"], "UpdateDatabase")
        self.assertEqual(entries[0]["files"], ["Data/A.sql"])
        self.assertEqual(entries[0]["file_origins"], {"Data/A.sql": "custom"})

    def test_dedup_files_and_reuses_entry(self) -> None:
        entries: list[dict] = []
        merge_action_entry(
            entries, action_type="UpdateDatabase", action_id="UpdateDatabase",
            files=["Data/A.sql"], load_order=9999,
        )
        added = merge_action_entry(
            entries, action_type="UpdateDatabase", action_id="UpdateDatabase",
            files=["Data/A.sql", "Data/B.sql"], load_order=100,  # 已存在条目不改 load_order
        )
        self.assertEqual(added, 1)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["load_order"], 9999)
        self.assertEqual(sorted(entries[0]["files"]), ["Data/A.sql", "Data/B.sql"])

    def test_invalid_paths_skipped(self) -> None:
        entries: list[dict] = []
        added = merge_action_entry(
            entries, action_type="UpdateDatabase", action_id="X",
            files=["../evil.sql", "Data/ok.sql"], load_order=0,
        )
        self.assertEqual(added, 1)
        self.assertEqual(entries[0]["files"], ["Data/ok.sql"])


class RemoveActionFilesTestCase(unittest.TestCase):
    def test_removes_from_entries(self) -> None:
        entries: list[dict] = [
            {"type": "UpdateDatabase", "id": "UpdateDatabase", "files": ["Data/A.sql", "Data/B.sql"],
             "load_order": 9999, "file_origins": {"Data/A.sql": "custom", "Data/B.sql": "custom"}},
        ]
        removed = remove_action_files(entries, "Data/A.sql")
        self.assertEqual(removed, 1)
        self.assertEqual(entries[0]["files"], ["Data/B.sql"])
        self.assertNotIn("Data/A.sql", entries[0]["file_origins"])

    def test_missing_returns_zero(self) -> None:
        entries: list[dict] = [{"type": "UpdateDatabase", "id": "X", "files": [], "load_order": 0}]
        self.assertEqual(remove_action_files(entries, "Data/nope.sql"), 0)


if __name__ == "__main__":
    unittest.main()
