"""Tests for the shared output manifest value object."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ModTools_5_4.project.output_manifest import (
    make_output_manifest,
    parent_folders,
    safe_relative_path,
)


class OutputManifestTestCase(unittest.TestCase):
    def test_manifest_summary_is_json_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo.civ6proj"
            manifest = make_output_manifest({"Data/X.sql": "SELECT 1;"}, ["Data"], path)
            summary = manifest.to_dict()
        self.assertTrue(summary["can_generate"])
        self.assertEqual(summary["file_count"], 1)
        self.assertEqual(summary["files"], ["Data/X.sql"])

    def test_safe_relative_path_matches_delete_rules(self) -> None:
        self.assertEqual(safe_relative_path(r"Data\\X.sql"), "Data/X.sql")
        self.assertEqual(safe_relative_path("./Data/X.sql"), "Data/X.sql")
        self.assertIsNone(safe_relative_path("../X.sql"))
        self.assertIsNone(safe_relative_path("C:/X.sql"))
        self.assertIsNone(safe_relative_path("/X.sql"))

    def test_parent_folders_returns_all_levels(self) -> None:
        self.assertEqual(parent_folders("A/B/C.txt"), {"A", "A/B"})
        self.assertEqual(parent_folders("C.txt"), set())


if __name__ == "__main__":
    unittest.main()
