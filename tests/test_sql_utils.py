"""Tests for pure SQL output helpers."""
from __future__ import annotations

import unittest

from ModTools_5_4.project.sql_utils import sql_literal


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


if __name__ == "__main__":
    unittest.main()
