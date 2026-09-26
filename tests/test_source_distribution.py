"""Regression coverage for source sharing and Git artifact boundaries."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.share_source import (
    REQUIRED, check_tracked, distributable, export_source, forbidden, tracked_files,
)


class SourceDistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Source test")
        self.git("config", "user.email", "source-test@example.invalid")
        self.write("README.md", "original")
        self.write("skills/example.md", "skill")
        self.write("modgen/example.py", "print('ok')")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            capture_output=True, text=True, encoding="utf-8",
        ).stdout

    def write(self, relative, content):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def test_artifacts_and_sidecars_case_insensitive(self):
        for path in ("old.ZIP", "app.ExE", "x.ZIP.sha256", "x.exe.sha256",
                     "tools/x.dll", "archive.tar.gz", "x.whl", "shares/x/readme.md",
                     ".venv/pyvenv.cfg", "tools/__pycache__/x.pyc", "settings.json",
                     "ModTools_5_4/data/settings.json"):
            with self.subTest(path=path):
                self.assertTrue(forbidden(path))
                self.assertTrue(check_tracked([*REQUIRED, path]))

    def test_runtime_data_sources_and_licenses_are_included(self):
        for path in ("local_text_New.sqlite", "ModTools_5_4/data/FontIcons.dds",
                     "skills/civ6-html-ui/scripts/render-textures.cjs",
                     "licenses/civ6-modding-skills.LICENSE", "tests/fixtures/example.json"):
            with self.subTest(path=path):
                self.assertTrue(distributable(path))
        self.assertFalse(distributable("private-notes.md"))
        self.assertFalse(distributable("tools/legacy_skill_builders/old.py"))
        self.assertTrue(distributable("tools/legacy_skill_builders/README.md"))
        self.assertFalse(distributable("ModTools_5_4/logs/.gitkeep"))

    def test_missing_required_sources_are_errors(self):
        self.assertEqual(check_tracked(sorted(REQUIRED)), [])
        self.assertIn("Missing tracked source: modgen/cli.py",
                      check_tracked(sorted(REQUIRED - {"modgen/cli.py"})))

    def test_export_uses_current_tracked_content_and_records_hashes(self):
        self.write("README.md", "updated")
        self.write("skills/private-note.md", "untracked")
        destination = Path(self.tmp.name) / "share"
        manifest = export_source(self.root, destination, tracked_files(self.root))
        self.assertEqual((destination / "README.md").read_text(), "updated")
        self.assertFalse((destination / "skills/private-note.md").exists())
        self.assertFalse((destination / ".git").exists())
        self.assertTrue(manifest["working_tree_dirty"])
        self.assertEqual(manifest["base_commit"], self.git("rev-parse", "HEAD").strip())
        self.assertEqual(json.loads((destination / "SOURCE_MANIFEST.json").read_text()),
                         manifest)
        for record in manifest["files"]:
            data = (destination / record["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
            self.assertEqual(len(data), record["size"])

    def test_clean_snapshot_and_new_staged_source(self):
        self.write("skills/new.md", "new staged source")
        self.git("add", "skills/new.md")
        self.git("commit", "-qm", "new source")
        destination = self.root / "shares" / "source"
        manifest = export_source(self.root, destination, tracked_files(self.root))
        self.assertFalse(manifest["working_tree_dirty"])
        self.assertEqual((destination / "skills/new.md").read_text(), "new staged source")

    def test_existing_and_overlapping_destinations_are_untouched(self):
        paths = tracked_files(self.root)
        for destination in (self.root, self.root.parent, self.root / "skills" / "share"):
            with self.subTest(destination=destination):
                with self.assertRaises(ValueError):
                    export_source(self.root, destination, paths)
        destination = Path(self.tmp.name) / "existing"
        destination.mkdir()
        sentinel = destination / "keep"
        sentinel.write_text("keep")
        with self.assertRaises(ValueError):
            export_source(self.root, destination, paths)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertFalse((self.root / "skills" / "share").exists())

    def test_missing_source_fails_before_output_creation(self):
        (self.root / "README.md").unlink()
        destination = Path(self.tmp.name) / "missing"
        with self.assertRaises(ValueError):
            export_source(self.root, destination, tracked_files(self.root))
        self.assertFalse(destination.exists())

    def test_parent_checkout_is_not_used_from_copied_folder(self):
        copied = self.root / "shares" / "copy"
        copied.mkdir(parents=True)
        with self.assertRaises(ValueError):
            tracked_files(copied)


if __name__ == "__main__":
    unittest.main()
