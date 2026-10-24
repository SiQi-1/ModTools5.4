"""Tests for pure SQL output helpers."""
from __future__ import annotations

import unittest

from ModTools_5_4.project.sql_utils import build_sparse_insert_blocks, sql_literal, sql_value_present, sparse_row


class SqlUtilsTestCase(unittest.TestCase):
    def test_null_boolean_and_numbers(self) -> None:
        self.assertEqual(sql_literal(None, lambda value: value), "NULL")
        self.assertEqual(sql_literal(True, lambda value: value), "1")
        self.assertEqual(sql_literal(False, lambda value: value), "0")
        self.assertEqual(sql_literal(12, lambda value: value), "12")
        self.assertEqual(sql_literal(1.25, lambda value: value), "1.25")

    def test_empty_and_none_text_are_null(self) -> None:
        escape = lambda value: value.replace("'", "''")
        self.assertEqual(sql_literal("", escape), "NULL")
        self.assertEqual(sql_literal("  ", escape), "NULL")
        self.assertEqual(sql_literal("None", escape), "NULL")

    def test_strings_use_injected_escape_policy(self) -> None:
        escape = lambda value: value.replace("'", "''")
        self.assertEqual(sql_literal("O'Brien", escape), "'O''Brien'")

    def test_sparse_row_keeps_required_columns_and_real_zero(self) -> None:
        columns, values = sparse_row(
            {"Type": "X", "Name": "LOC_X_NAME", "Description": None, "Optional": "", "Flag": 0},
            ["Type", "Name", "Description", "Optional", "Flag"],
            keep_columns=("Type", "Name", "Description"),
        )
        self.assertEqual(columns, ["Type", "Name", "Description", "Flag"])
        self.assertEqual(values, ["X", "LOC_X_NAME", None, 0])
        self.assertTrue(sql_value_present(0))
        self.assertTrue(sql_value_present(False))
        self.assertFalse(sql_value_present(""))
        self.assertFalse(sql_value_present("NULL"))

    def test_sparse_insert_groups_rows_by_column_signature(self) -> None:
        sql = build_sparse_insert_blocks(
            "Units",
            "Units",
            [
                {"UnitType": "UNIT_A", "Name": "LOC_A", "FormationClass": "FORMATION_CLASS_CIVILIAN"},
                {"UnitType": "UNIT_B", "Name": "LOC_B", "Domain": "DOMAIN_LAND"},
            ],
            ["UnitType", "Name", "Domain", "FormationClass"],
            keep_columns=("UnitType", "Name"),
        )
        self.assertEqual(sql.count("INSERT INTO Units"), 2)
        self.assertNotIn("NULL", sql)
        self.assertIn("(UnitType, Name, FormationClass)", sql)
        self.assertIn("(UnitType, Name, Domain)", sql)


if __name__ == "__main__":
    unittest.main()
