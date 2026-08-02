"""Unit tests for ArtDef reference parsing (From/{Base,DLC}/.artdef)."""
from __future__ import annotations

import unittest

from ModTools_5_4 import artdef_parser


class ArtdefParserTestCase(unittest.TestCase):
    def test_unit_names_list_is_populated(self) -> None:
        names = artdef_parser.list_unit_artdef_names()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("UNIT_") for name in names))

    def test_civilization_names_list_is_populated(self) -> None:
        names = artdef_parser.list_civilization_artdef_names()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("CIVILIZATION_") for name in names))

    def test_fetch_known_unit_entry(self) -> None:
        entry = artdef_parser.get_unit_entry_element("UNIT_SCOUT")
        self.assertIsNotNone(entry)
        name = entry.find("m_Name")
        self.assertIsNotNone(name)
        self.assertEqual(name.attrib.get("text"), "UNIT_SCOUT")

    def test_fetch_known_civilization_entry(self) -> None:
        entry = artdef_parser.get_civilization_entry_element("CIVILIZATION_AMERICA")
        self.assertIsNotNone(entry)

    def test_missing_entry_returns_none(self) -> None:
        self.assertIsNone(artdef_parser.get_unit_entry_element("UNIT_NOT_A_REAL_UNIT_XYZ"))


if __name__ == "__main__":
    unittest.main()
