"""Unit tests for the .CIV project file model (no GUI needed)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ModTools_5_4.project.civ_project import (
    CIV_FILE_EXTENSION,
    CIV_SECTION_ORDER,
    create_empty_project,
    load_civ_project,
    save_civ_project,
)


class CivProjectTestCase(unittest.TestCase):
    def test_create_empty_project_has_all_sections(self) -> None:
        project = create_empty_project("测试")
        self.assertEqual(project.project_name, "测试")
        self.assertEqual(list(project.sections.keys()), CIV_SECTION_ORDER)

    def test_direct_sections_are_dicts_groups_are_lists(self) -> None:
        project = create_empty_project()
        for section, value in project.sections.items():
            if section in {"基础信息", "美术", "文本", "修改器"}:
                self.assertIsInstance(value, dict, section)
            else:
                self.assertIsInstance(value, list, section)

    def test_roundtrip_save_and_load(self) -> None:
        project = create_empty_project("往返测试")
        project.sections["文明"].append({"name": "示例文明", "type": "CIVILIZATION_TEST"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proj.CIV"
            save_civ_project(path, project)
            loaded = load_civ_project(path)
        self.assertEqual(loaded.project_name, "往返测试")
        self.assertEqual(loaded.sections["文明"][0]["type"], "CIVILIZATION_TEST")

    def test_load_rejects_non_civ_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proj.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_civ_project(path)

    def test_load_rejects_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.CIV"
            path.write_text('{"hello": 1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_civ_project(path)

    def test_from_dict_normalizes_missing_sections(self) -> None:
        payload = {
            "meta": {"format": "CIV_PROJECT", "schema_version": "0.1.0", "project_name": "旧工程"},
            "workspace": {"文明": [{"name": "x"}]},
        }
        from ModTools_5_4.project.civ_project import CivProject

        loaded = CivProject.from_dict(payload)
        self.assertEqual(set(loaded.sections.keys()), set(CIV_SECTION_ORDER))
        self.assertIsInstance(loaded.sections["基础信息"], dict)
        self.assertIsInstance(loaded.sections["领袖"], list)
        self.assertEqual(loaded.sections["文明"][0]["name"], "x")


if __name__ == "__main__":
    unittest.main()
