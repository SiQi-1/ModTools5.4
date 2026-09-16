"""Belief extraction regression: legacy output, executable SQL and no Qt."""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

from ModTools_5_4.project.sql_builders import build_belief_sql_pair

FIXTURE = Path(__file__).parent / "fixtures" / "belief_sql_legacy.json"
TEST_SCHEMA = """
CREATE TABLE Types (Type TEXT PRIMARY KEY, Kind TEXT NOT NULL);
CREATE TABLE Beliefs (
    BeliefType TEXT PRIMARY KEY, Name TEXT, Description TEXT,
    BeliefClassType TEXT NOT NULL
);
CREATE TABLE LocalizedText (Language TEXT, Tag TEXT, Text TEXT, PRIMARY KEY(Language, Tag));
"""


class BeliefSqlBuilderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]

    def test_exact_legacy_output_and_input_immutability(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["name"]):
                entries = deepcopy(case["entries"])
                expected = (case["data_sql"], case["text_sql"])
                self.assertEqual(build_belief_sql_pair(entries), expected)
                self.assertEqual(entries, case["entries"])

    def test_all_cases_execute_as_sqlite(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["name"]), closing(sqlite3.connect(":memory:")) as conn:
                conn.executescript(TEST_SCHEMA)
                data_sql, text_sql = build_belief_sql_pair(case["entries"])
                conn.executescript(data_sql)
                conn.executescript(text_sql)
                count = conn.execute("SELECT count(*) FROM Beliefs").fetchone()[0]
                self.assertEqual(conn.execute("SELECT count(*) FROM Types").fetchone()[0], count)
                self.assertEqual(conn.execute("SELECT count(*) FROM LocalizedText").fetchone()[0], count * 2)

    def test_builder_runs_without_site_packages_or_gui_imports(self) -> None:
        code = """
import sys
from ModTools_5_4.project.sql_builders import build_belief_sql_pair
sql, text = build_belief_sql_pair([{'type': 'BELIEF_STANDALONE'}])
assert 'BELIEF_STANDALONE' in sql and 'LOC_BELIEF_STANDALONE_NAME' in text
assert not any(name.startswith(('PyQt6', 'PIL', 'ModTools_5_4.ui')) for name in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-S", "-c", code], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
