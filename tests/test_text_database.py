"""Unit tests for the bundled text database (local_text_New.sqlite)."""
from __future__ import annotations

import unittest
from pathlib import Path

from ModTools_5_4.db.text_database import query_text_by_tag

REPO_ROOT = Path(__file__).resolve().parent.parent
TEXT_DB = REPO_ROOT / "local_text_New.sqlite"


@unittest.skipUnless(TEXT_DB.exists(), "local_text_New.sqlite not present in repo root")
class TextDatabaseTestCase(unittest.TestCase):
    def test_resolve_known_tag(self) -> None:
        text = query_text_by_tag(TEXT_DB, "LOC_CIVILIZATION_AMERICA_NAME")
        self.assertTrue(text and text != "未知", f"tag unresolved: {text!r}")

    def test_missing_tag_returns_tag_itself(self) -> None:
        text = query_text_by_tag(TEXT_DB, "LOC_TAG_THAT_DOES_NOT_EXIST_ZZZ")
        self.assertEqual(text, "LOC_TAG_THAT_DOES_NOT_EXIST_ZZZ")

    def test_nested_ref_resolution(self) -> None:
        text = query_text_by_tag(TEXT_DB, "LOC_CIVILIZATION_AMERICA_NAME", resolve_nested=True)
        self.assertNotIn("LOC_", text.upper() if text else "")


if __name__ == "__main__":
    unittest.main()
