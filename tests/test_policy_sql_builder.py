"""Policy extraction regression: legacy output, executable SQL and no Qt."""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

from ModTools_5_4.project.sql_builders import build_policy_sql_pair


FIXTURE = Path(__file__).parent / "fixtures" / "policy_sql_legacy.json"
TEST_SCHEMA = """
CREATE TABLE Types (Type TEXT PRIMARY KEY, Kind TEXT NOT NULL);
CREATE TABLE Policies (
    PolicyType TEXT PRIMARY KEY, Name TEXT, Description TEXT,
    PrereqCivic TEXT, PrereqTech TEXT, GovernmentSlotType TEXT NOT NULL,
    RequiresGovernmentUnlock INTEGER NOT NULL, ExplicitUnlock INTEGER NOT NULL
);
CREATE TABLE Policies_XP1 (
    PolicyType TEXT PRIMARY KEY, MinimumGameEra TEXT, MaximumGameEra TEXT,
    RequiresDarkAge INTEGER, RequiresGoldenAge INTEGER
);
CREATE TABLE Policy_GovernmentExclusives_XP2 (PolicyType TEXT, GovernmentType TEXT);
CREATE TABLE LocalizedText (Language TEXT, Tag TEXT, Text TEXT, PRIMARY KEY(Language, Tag));
"""


class PolicySqlBuilderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]

    def test_exact_legacy_output_without_mutating_input(self) -> None:
        # Captured from WorkspacePage at 47ed84d before the builder was moved.
        for case in self.cases:
            with self.subTest(case=case["name"]):
                entries = deepcopy(case["entries"])
                expected = (case["data_sql"], case["text_sql"])
                self.assertEqual(build_policy_sql_pair(entries), expected)
                self.assertEqual(entries, case["entries"])
                self.assertEqual(build_policy_sql_pair(entries), expected)

    def test_all_legacy_cases_execute_as_sqlite(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["name"]), closing(sqlite3.connect(":memory:")) as conn:
                conn.executescript(TEST_SCHEMA)
                data_sql, text_sql = build_policy_sql_pair(case["entries"])
                conn.executescript(data_sql)
                conn.executescript(text_sql)
                count = conn.execute("SELECT count(*) FROM Policies").fetchone()[0]
                self.assertEqual(conn.execute("SELECT count(*) FROM Types").fetchone()[0], count)
                self.assertEqual(conn.execute("SELECT count(*) FROM LocalizedText").fetchone()[0], count * 2)

    def test_database_preserves_text_defaults_and_subtables(self) -> None:
        cases = {case["name"]: case for case in self.cases}
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.executescript(TEST_SCHEMA)
            for name in ("all_fields", "legacy_subtables", "null_blank_and_invalid_numbers"):
                data_sql, text_sql = build_policy_sql_pair(cases[name]["entries"])
                conn.executescript(data_sql)
                conn.executescript(text_sql)
            self.assertEqual(
                conn.execute("SELECT Text FROM LocalizedText WHERE Tag = 'LOC_POLICY_COMPLETE_NAME'").fetchone(),
                ("匠人的 O'Brien",),
            )
            self.assertEqual(
                conn.execute("SELECT PrereqCivic, PrereqTech, GovernmentSlotType, RequiresGovernmentUnlock, ExplicitUnlock FROM Policies WHERE PolicyType = 'POLICY_NULLS'").fetchone(),
                (None, None, "SLOT_WILDCARD", 0, 0),
            )
            self.assertEqual(
                conn.execute("SELECT MinimumGameEra, MaximumGameEra, RequiresDarkAge, RequiresGoldenAge FROM Policies_XP1 WHERE PolicyType = 'POLICY_LEGACY'").fetchone(),
                (None, "ERA_RENAISSANCE", 0, 1),
            )
            self.assertEqual(
                conn.execute("SELECT GovernmentType FROM Policy_GovernmentExclusives_XP2 WHERE PolicyType = 'POLICY_COMPLETE'").fetchone(),
                ("GOVERNMENT_DEMOCRACY",),
            )

    def test_builder_runs_without_site_packages_or_gui_imports(self) -> None:
        code = """
import sys
from ModTools_5_4.project.sql_builders import build_policy_sql_pair
sql, text = build_policy_sql_pair([{'type': 'POLICY_STANDALONE'}])
assert 'POLICY_STANDALONE' in sql and 'LOC_POLICY_STANDALONE_NAME' in text
assert not any(name.startswith(('PyQt6', 'PIL', 'ModTools_5_4.ui')) for name in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-S", "-c", code], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
