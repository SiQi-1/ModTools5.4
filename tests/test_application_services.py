"""Tests for the phase-two Qt-free application service seams."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ModTools_5_4.application import GenerationService, ProjectService
from ModTools_5_4.project.output_manifest import make_output_manifest


class FakeGenerationAdapter:
    def __init__(self) -> None:
        self.manifest_value = make_output_manifest({"Data/X.sql": "SELECT 1;"}, ["Data"], None)
        self.calls: list[tuple[str, object]] = []

    def output_manifest(self):
        self.calls.append(("manifest", None))
        return self.manifest_value

    def generate_all_output_files(self, *, overwrite_policy="ask"):
        self.calls.append(("all", overwrite_policy))
        return {"ok": True, "policy": overwrite_policy}

    def generate_single_output_file(self, relative_path, *, overwrite=None):
        self.calls.append(("file", (relative_path, overwrite)))
        return {"ok": True, "path": relative_path, "overwrite": overwrite}


class ProjectServiceTestCase(unittest.TestCase):
    def test_roundtrip_uses_shared_project_model(self) -> None:
        service = ProjectService()
        project = service.create("服务工程")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "service.CIV"
            service.save(path, project)
            loaded = service.load(path)
        self.assertEqual(loaded.project_name, "服务工程")
        self.assertIn("修改器", loaded.sections)


class GenerationServiceTestCase(unittest.TestCase):
    def test_delegates_without_qt_or_private_method_names(self) -> None:
        service = GenerationService()
        adapter = FakeGenerationAdapter()
        self.assertEqual(service.manifest(adapter).to_dict()["file_count"], 1)
        self.assertEqual(service.generate_all(adapter, overwrite_policy="all")["policy"], "all")
        result = service.generate_file(adapter, "Data/X.sql", overwrite=False)
        self.assertEqual(result["path"], "Data/X.sql")
        self.assertEqual(adapter.calls, [("manifest", None), ("all", "all"), ("file", ("Data/X.sql", False))])


if __name__ == "__main__":
    unittest.main()
