"""Unit tests for text DB import (XML/SQL files -> sqlite) and lookup."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ModTools_5_4.db.text_database import import_text_files, query_text_by_tag

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<GameData>
  <LocalizedText>
    <Row Tag="LOC_TEST_HELLO" Language="zh_Hans_CN" Text="你好世界"/>
    <Row Tag="LOC_TEST_SKIP" Language="en_US" Text="english only"/>
  </LocalizedText>
</GameData>
"""

SAMPLE_SQL = """-- test import
INSERT OR REPLACE INTO LocalizedText (Language, Tag, Text) VALUES ('zh_Hans_CN', 'LOC_TEST_SQL', '来自SQL');
"""


class TextImportTestCase(unittest.TestCase):
    def test_import_xml_and_sql_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "test.sqlite"
            xml_file = root / "text.xml"
            xml_file.write_text(SAMPLE_XML, encoding="utf-8")
            sql_file = root / "text.sql"
            sql_file.write_text(SAMPLE_SQL, encoding="utf-8")

            result = import_text_files(db, [xml_file, sql_file])
            self.assertEqual(result.inserted_count, 2)  # 1 zh XML + 1 SQL (en row skipped)
            self.assertEqual(result.parsed_file_count, 2)

            self.assertEqual(query_text_by_tag(db, "LOC_TEST_HELLO"), "你好世界")
            self.assertEqual(query_text_by_tag(db, "LOC_TEST_SQL"), "来自SQL")

    def test_reimport_updates_existing_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "test.sqlite"
            xml_file = root / "text.xml"
            xml_file.write_text(SAMPLE_XML, encoding="utf-8")

            import_text_files(db, [xml_file])
            result = import_text_files(db, [xml_file])
            self.assertEqual(result.updated_count, 1)  # only the zh_Hans_CN row re-imports
            self.assertEqual(result.inserted_count, 0)

    def test_loc_tag_only_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "test.sqlite"
            xml_file = root / "text.xml"
            xml_file.write_text(
                '<GameData><Row Tag="NOT_LOC_1" Language="zh_Hans_CN" Text="x"/>'
                '<Row Tag="LOC_KEEP_1" Language="zh_Hans_CN" Text="y"/></GameData>',
                encoding="utf-8",
            )
            result = import_text_files(db, [xml_file], loc_tag_only=True)
            self.assertEqual(result.inserted_count, 1)
            self.assertEqual(query_text_by_tag(db, "LOC_KEEP_1"), "y")
            self.assertEqual(query_text_by_tag(db, "NOT_LOC_1"), "NOT_LOC_1")


if __name__ == "__main__":
    unittest.main()
