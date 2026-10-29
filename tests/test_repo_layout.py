"""Repository layout and documentation guards (2026-10 restructure)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import doc_lint  # noqa: E402

ROOT_FILE_WHITELIST = {
    ".gitattributes", ".gitignore", "AGENTS.md", "CLAUDE.md", "LICENSE",
    "ModTools5.4.py", "README.md", "THIRD_PARTY_NOTICES.md",
    "local_text_New.sqlite", "requirements.txt",
}
ROOT_DIR_WHITELIST = {
    ".github", "docs", "licenses", "modgen", "ModTools_5_4", "skills", "tests", "tools",
}
LOCAL_DISK_DIRS = {
    "workspace", "workspace/mods", "local_notes", "local_skills", "local_db_queries",
    "refs", "build", "dist", "release", "shares", "_scripts", "work",
    "project_reports", "review_notes",
}


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


class RootLayoutTest(unittest.TestCase):
    def test_root_files_are_whitelisted(self) -> None:
        for path in tracked():
            if "/" not in path:
                self.assertIn(path, ROOT_FILE_WHITELIST, f"unexpected tracked root file: {path}")

    def test_only_whitelisted_top_level_directories_are_tracked(self) -> None:
        tops = {p.split("/", 1)[0] for p in tracked() if "/" in p}
        self.assertEqual(tops - ROOT_DIR_WHITELIST, set())

    def test_local_workspace_is_not_tracked(self) -> None:
        for path in tracked():
            top = path.split("/", 1)[0]
            self.assertNotIn(top, LOCAL_DISK_DIRS, f"local path tracked: {path}")

    def test_root_markdown_budget(self) -> None:
        root_md = [p for p in tracked() if "/" not in p and p.endswith(".md")]
        self.assertLessEqual(len(root_md), 4, root_md)
        self.assertLessEqual((ROOT / "README.md").stat().st_size, 8 * 1024)
        self.assertLessEqual((ROOT / "AGENTS.md").stat().st_size, 8 * 1024)

    def test_gitignore_covers_workspace(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/workspace/", text)


class DocsTest(unittest.TestCase):
    def test_doc_lint_has_no_errors(self) -> None:
        report = doc_lint.lint()
        self.assertTrue(report["ok"], json.dumps(report["errors"][:10], ensure_ascii=False, indent=1))

    def test_no_local_absolute_paths(self) -> None:
        report = doc_lint.lint()
        offenders = [w for w in report["warnings"] if w["code"] == "local-path"]
        self.assertEqual(offenders, [], json.dumps(offenders[:10], ensure_ascii=False, indent=1))

    def test_core_entrypoints_exist(self) -> None:
        for rel in ("docs/README.md", "docs/dev/architecture.md", "docs/dev/roadmap.md",
                    "skills/RULES.md", "skills/WORKFLOW.md", "skills/catalog.json",
                    "skills/SKILLS_OUTLINE.md", "modgen/AGENTS.md", "modgen/docs/cli-reference.md"):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_catalog_read_targets_exist(self) -> None:
        catalog = json.loads((ROOT / "skills" / "catalog.json").read_text(encoding="utf-8"))
        missing = []
        for rel in catalog.get("always_read", []):
            if not (ROOT / "skills" / rel).is_file():
                missing.append(rel)
        for route in catalog.get("routes", []):
            for rel in route.get("read", []):
                if isinstance(rel, str) and not (ROOT / "skills" / rel).is_file():
                    missing.append(f"{route.get('id')}:{rel}")
        self.assertEqual(missing, [])


class ShareBoundaryTest(unittest.TestCase):
    def test_share_source_check_passes(self) -> None:
        result = subprocess.run([sys.executable, "-S", str(ROOT / "tools" / "share_source.py"), "--check"],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
