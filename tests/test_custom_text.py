"""Custom LOC declarations must survive saves and execute in SQL/XML output."""
from __future__ import annotations
import os
import sqlite3
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from ModTools_5_4.project.custom_text import validate_custom_text
from ModTools_5_4.project.civ_project import save_civ_project, load_civ_project
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage
from sample_project import build_sample_project


class CustomTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = WorkspacePage()
        self.addCleanup(self.page.close)
        self.page._project = build_sample_project()

    def test_sql_xml_roundtrip_and_persistence(self):
        content = "乌啾's <新闻> & {1}\n第二行 [ICON_Gold]"
        section = {"custom_entries": [{"tag": "LOC_CUSTOM_NEWS", "text": content,
                                      "group": "记者\n分组", "source": "test"}]}
        self.page._project.sections["文本"].update(section)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "text.CIV"
            save_civ_project(path, self.page._project)
            self.page._project = load_civ_project(path)
        self.assertEqual(self.page._project.sections["文本"]["custom_entries"], section["custom_entries"])
        sql = self.page._build_text_workspace_preview("sql")
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE LocalizedText(Language TEXT, Tag TEXT, Text TEXT, PRIMARY KEY(Language,Tag))")
            db.executescript(sql)
            self.assertEqual(db.execute("SELECT Text FROM LocalizedText WHERE Tag='LOC_CUSTOM_NEWS'").fetchone()[0], content)
        xml = ET.fromstring(self.page._build_text_workspace_preview("xml"))
        row = next(r for r in xml.iter("Row") if r.get("Tag") == "LOC_CUSTOM_NEWS")
        self.assertEqual(row.get("Text"), content)
        self.assertIn("-- 记者 分组", sql)

    def test_invalid_declarations(self):
        for entries in ({}, [None], [{"tag": "BAD", "text": "文本"}],
                        [{"tag": "LOC_TEST", "text": " "}],
                        [{"tag": "LOC_TEST", "text": "文本", "group": None}],
                        [{"tag": "LOC_TEST", "text": "一"}, {"tag": "LOC_TEST", "text": "二"}]):
            with self.subTest(entries=entries):
                self.assertTrue(validate_custom_text({"custom_entries": entries}))

    def test_generated_tag_collision_blocks_all_and_single_before_writing(self):
        self.page._project.sections["文本"]["custom_entries"] = [
            {"tag": "LOC_CIVILIZATION_SIQI_DEMO_NAME", "text": "冲突"}]
        for result in (self.page.generate_all_output_files(overwrite_policy="all"),
                       self.page._generate_single_output_file("Text/Test.sql", overwrite=True)):
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "custom_text_invalid")
            self.assertIn("LOC_CIVILIZATION_SIQI_DEMO_NAME", str(result["issues"]))

    def test_old_project_and_empty_list_identical(self):
        before = self.page._build_text_workspace_preview("sql")
        self.page._project.sections["文本"]["custom_entries"] = []
        self.assertEqual(before, self.page._build_text_workspace_preview("sql"))
        self.assertEqual(validate_custom_text(None), [])

if __name__ == "__main__":
    unittest.main()
