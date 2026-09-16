"""Tests for the Qt-free project schema boundary."""
from __future__ import annotations

import unittest

from ModTools_5_4.project.schema import (
    CIV_SECTION_ORDER,
    normalize_workspace,
    parse_project_payload,
    project_envelope,
)


class ProjectSchemaTestCase(unittest.TestCase):
    def test_normalize_missing_and_wrong_section_shapes(self) -> None:
        normalized = normalize_workspace({"基础信息": [], "文明": {"bad": True}})
        self.assertEqual(list(normalized), CIV_SECTION_ORDER)
        self.assertEqual(normalized["基础信息"], {})
        self.assertEqual(normalized["文明"], [])

    def test_parse_requires_meta_and_workspace(self) -> None:
        with self.assertRaisesRegex(ValueError, "meta"):
            parse_project_payload({"workspace": {}})
        with self.assertRaisesRegex(ValueError, "workspace"):
            parse_project_payload({"meta": {}})

    def test_parse_preserves_project_name_and_normalizes(self) -> None:
        name, workspace = parse_project_payload(
            {"meta": {"project_name": "  示例  "}, "workspace": {"文明": []}}
        )
        self.assertEqual(name, "示例")
        self.assertIsInstance(workspace["基础信息"], dict)
        self.assertIsInstance(workspace["文明"], list)

    def test_envelope_keeps_schema_version(self) -> None:
        payload = project_envelope("示例", normalize_workspace({}))
        self.assertEqual(payload["meta"]["schema_version"], "0.1.0")
        self.assertEqual(payload["meta"]["format"], "CIV_PROJECT")


if __name__ == "__main__":
    unittest.main()
