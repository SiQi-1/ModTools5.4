# -*- coding: utf-8 -*-
"""外置技能名单（skills/EXTERNAL_SKILLS.md）接入与分发边界回归测试。

civ6-model-import 技能包（作者千寻瀑）只登记名单，不随仓库分发：
名单留在 skills/ 随 Git 与源码分享，包体与解压内容只在本机 Git 忽略的 local_skills/。
本测试不要求 local_skills/ 在本机存在（CI 与源码分享都没有该目录）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ModTools_5_4 import skills_search  # noqa: E402
from tools.share_source import forbidden  # noqa: E402

SKILLS = ROOT / "skills"
ROSTER = SKILLS / "EXTERNAL_SKILLS.md"


class ExternalSkillRosterTest(unittest.TestCase):
    """名单保留包名、作者、本机安装目录与发布边界。"""

    def test_roster_names_package_author_install_dir_and_boundary(self):
        self.assertTrue(ROSTER.is_file(), "缺少外置技能名单：%s" % ROSTER)
        text = ROSTER.read_text(encoding="utf-8")
        for needle in (
            "civ6-model-import",
            "千寻瀑",
            "local_skills/civ6-model-import",
            "不代替作者发布",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)

    def test_outline_reaches_roster(self):
        outline = (SKILLS / "SKILLS_OUTLINE.md").read_text(encoding="utf-8")
        self.assertIn("(EXTERNAL_SKILLS.md)", outline)
        self.assertIn("外置技能", outline)


class ExternalSkillRouteTest(unittest.TestCase):
    """必读映射与检索要指向名单，不能让能力看起来不存在。"""

    def test_reading_plan_hits_external_route_and_roster(self):
        plan = skills_search.reading_plan("civ6-model-import 模型导入")
        self.assertTrue(plan["matched"])
        self.assertIn("external_model_import", plan["topics"])
        self.assertIn("EXTERNAL_SKILLS.md", plan["required"])

    def test_route_keeps_package_aliases_and_reads_roster(self):
        catalog = json.loads((SKILLS / "catalog.json").read_text(encoding="utf-8"))
        routes = {route["id"]: route for route in catalog["routes"]}
        self.assertIn("external_model_import", routes)
        route = routes["external_model_import"]
        self.assertEqual(route["read"], ["EXTERNAL_SKILLS.md"])
        for alias in (
            "civ6-model-import", "模型导入", "领袖3D模型", "psk", "ueanim",
            "NexusBatch", "cn6", "BLP部署", "外置技能",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, route["aliases"])

    def test_search_ranks_roster_for_package_queries(self):
        for query in ("civ6-model-import 模型导入", "领袖3D模型 psk ueanim 导入"):
            with self.subTest(query=query):
                rels = [item["rel"] for item in skills_search.search_skills(query, limit=3)]
                self.assertIn("EXTERNAL_SKILLS.md", rels)


class ExternalSkillDistributionTest(unittest.TestCase):
    """包体不进 Git、不进源码分享；名单本身可分享。"""

    def test_gitignore_keeps_local_install_out_of_git(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()]
        self.assertIn("local_skills/", lines)

    def test_share_source_rejects_local_install_but_keeps_roster(self):
        self.assertTrue(forbidden("local_skills/civ6-model-import/SKILL.md"))
        self.assertTrue(forbidden("local_skills"))
        self.assertFalse(forbidden("skills/EXTERNAL_SKILLS.md"))

    def test_notices_record_package_and_author(self):
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("civ6-model-import.zip", notices)
        self.assertIn("千寻瀑", notices)

    def test_git_tracks_no_local_skills_or_package_files(self):
        if shutil.which("git") is None:
            self.skipTest("本机没有 git")
        try:
            top = subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, encoding="utf-8",
            )
        except OSError:
            self.skipTest("git 不可用")
        if top.returncode != 0 or not top.stdout.strip():
            self.skipTest("测试目录不在 Git 仓库中")
        if Path(top.stdout.strip()).resolve() != ROOT.resolve():
            self.skipTest("测试目录不是 Git 仓库根")
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True,
        )
        self.assertEqual(listed.returncode, 0,
                         listed.stderr.decode("utf-8", errors="replace"))
        tracked = [path for path in listed.stdout.decode("utf-8").split("\0") if path]
        local_paths = [
            path for path in tracked
            if "local_skills" in path.replace("\\", "/").lower().split("/")
        ]
        self.assertEqual(local_paths, [], "local_skills/ 内容不得被 Git 跟踪")
        package_paths = [path for path in tracked if "civ6-model-import" in path.lower()]
        self.assertEqual(package_paths, [], "外置技能包文件不得被 Git 跟踪")


if __name__ == "__main__":
    unittest.main()
