"""Regression tests for useful SQL conflict evidence, not first-column guesses."""
from __future__ import annotations

import unittest
from pathlib import Path

from modgen.custom_conflicts import check_conflicts
from modgen.sql_inspect import insert_rows, updated_tables


class SqlInspectionTest(unittest.TestCase):
    def check(self, generated: str, custom: str, *, generated_xml=False, scope="in_game"):
        generated_path = "Data/Generated.xml" if generated_xml else "Data/Generated.sql"
        payload = {"workspace": {}, "extensions": {"files": [
            {"path": "Data/Core.sql", "role": "database", "scope": scope}]}}
        preview = {"files": {generated_path: generated, "Data/Core.sql": custom},
                   "readonly_custom_paths": [], "actions": {"in_game_actions": [
                       {"type": "UpdateDatabase", "files": [generated_path]}]}}
        return check_conflicts(Path("unused.CIV"), payload=payload, manifest=preview)

    def test_multiline_multirow_quoted_semicolons_and_comments(self):
        sql = """-- INSERT INTO Types VALUES ('FALSE', 'K');
        INSERT INTO "Types" ("Type", Kind) VALUES
        ('FIRST', 'semi;colon'), ('O''Brien', 'K'), ('LAST', 'K');
        /* INSERT INTO Types VALUES ('IGNORED', 'K'); */
        """
        rows, skipped = insert_rows(sql)
        self.assertEqual([r[2][0] for r in rows], ["FIRST", "O'Brien", "LAST"])
        self.assertFalse(skipped)
        result = self.check("INSERT INTO Types (Type,Kind) VALUES ('LAST','K');", sql)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["pk"], "LAST")

    def test_composite_key_and_reordered_columns(self):
        generated = "INSERT INTO BuildingModifiers (BuildingType,ModifierId) VALUES ('B','M1');"
        other = "INSERT INTO BuildingModifiers (ModifierId,BuildingType) VALUES ('M2','B');"
        self.assertFalse(self.check(generated, other)["errors"])
        duplicate = "INSERT INTO BuildingModifiers (ModifierId,BuildingType) VALUES ('M1','B');"
        self.assertEqual(len(self.check(generated, duplicate)["errors"]), 1)

    def test_custom_schema_primary_key_is_not_first_column(self):
        sql = """CREATE TABLE Extra (Label TEXT, A TEXT, B INTEGER, PRIMARY KEY(A,B));
        INSERT INTO Extra VALUES ('X','ONE',1), ('X','ONE',2), ('Y','ONE',1);"""
        result = self.check("", sql)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["pk"], ["ONE", 1.0])

    def test_no_primary_key_table_allows_identical_values(self):
        sql = "CREATE TABLE Extra (Value TEXT); INSERT INTO Extra VALUES ('A'),('A');"
        result = self.check("", sql)
        self.assertFalse(result["errors"])
        self.assertFalse(result["warnings"])

    def test_unknown_key_and_select_report_coverage(self):
        result = self.check("", "INSERT INTO UnknownTable (X) VALUES ('A'),('A'); INSERT INTO Types (Type) SELECT Type FROM Other;")
        self.assertFalse(result["errors"])
        self.assertEqual(len(result["warnings"]), 2)

    def test_case_sensitive_values_and_separate_database_scopes(self):
        a = "INSERT INTO Types (Type) VALUES ('A');"
        self.assertFalse(self.check(a, "INSERT INTO Types (Type) VALUES ('a');")["errors"])
        self.assertFalse(self.check(a, a, scope="front")["errors"])

    def test_xml_generated_rows_and_sql_conflict(self):
        result = self.check('<GameInfo><Units><Row UnitType="UNIT_A" Name="X"/></Units></GameInfo>',
                            "INSERT INTO Units (Name,UnitType) VALUES ('Y','UNIT_A');", generated_xml=True)
        self.assertEqual(len(result["errors"]), 1)

    def test_trigger_body_is_not_treated_as_immediate_inserts(self):
        sql = """CREATE TRIGGER Later AFTER INSERT ON Extra BEGIN
          INSERT INTO Types (Type) VALUES ('A');
          INSERT INTO Types (Type) VALUES ('A');
        END;
        WITH entries AS (SELECT 'A') INSERT INTO Types SELECT * FROM entries;
        """
        result = self.check("INSERT INTO Types (Type) VALUES ('A');", sql)
        self.assertFalse(result["errors"], result)
        self.assertTrue(result["warnings"])

    def test_update_delete_ignores_strings_and_comments(self):
        sql = "SELECT 'UPDATE Fake SET X=1;'; -- DELETE FROM Nope;\nUPDATE \"Units\" SET Cost=2; DELETE FROM [Buildings];"
        self.assertEqual(updated_tables(sql), {"Units", "Buildings"})


if __name__ == "__main__":
    unittest.main()
