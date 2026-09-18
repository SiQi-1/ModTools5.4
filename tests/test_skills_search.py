# -*- coding: utf-8 -*-
"""技能库检索引擎（ModTools_5_4/skills_search.py）回归测试。

覆盖两件事：
1. `_` 前缀的开发产物（生成脚本/查询脚本/中间数据）不进索引——否则它们会把真正该读的
   知识文档挤出结果前列（每个脚本里同一个术语出现几十次）。
2. 关键通用规则文档可被检索到（防止"知识写进去了但检索不到"）。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ModTools_5_4 import skills_search  # noqa: E402


class DevArtifactFilterTestCase(unittest.TestCase):
    def test_underscore_prefixed_paths_are_dev_artifacts(self) -> None:
        for rel in (
            "07-techniques/modifiers/_generate_final.py",
            "07-techniques/modifiers/_modifier-city.md.effects.txt",
            "07-techniques/modifiers/_trace_result3.txt",
            "some_dir/_sub/file.md",
            "__pycache__/x.py",
        ):
            self.assertTrue(skills_search._is_dev_artifact(rel), rel)

    def test_normal_paths_are_kept(self) -> None:
        for rel in (
            "07-techniques/modifier-techniques.md",
            "07-techniques/modifiers/modifier-unit-combat.md",
            "05-modtools-civ/civ-pitfalls.md",
            "AGENTS.md",
        ):
            self.assertFalse(skills_search._is_dev_artifact(rel), rel)

    def test_windows_separator_handled(self) -> None:
        self.assertTrue(skills_search._is_dev_artifact(r"07-techniques\modifiers\_query_db.py"))


class SkillsIndexTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = skills_search.default_skills_root()
        if not cls.root.is_dir():
            raise unittest.SkipTest("skills/ 目录不存在")
        cls.docs = {doc["rel"]: doc["text"] for doc in skills_search.build_index(cls.root)}

    def test_index_skips_dev_artifacts(self) -> None:
        leaked = [rel for rel in self.docs if skills_search._is_dev_artifact(rel)]
        self.assertEqual(leaked, [], "开发产物不应进索引")

    def test_index_keeps_knowledge_docs(self) -> None:
        self.assertIn("07-techniques/modifier-techniques.md", self.docs)
        self.assertIn("05-modtools-civ/civ-pitfalls.md", self.docs)

    def test_modifier_strings_rule_is_searchable(self) -> None:
        """战斗力类必写 ModifierStrings 的通用规则必须能被检索到。"""
        results = skills_search.search_skills("ModifierStrings", root=self.root, limit=10)
        rels = [item.get("rel") for item in results]
        self.assertIn("07-techniques/modifier-techniques.md", rels,
                      "通用规则文档应出现在 ModifierStrings 的检索结果里：%s" % rels)

    def test_rule_states_placeholder_convention(self) -> None:
        text = self.docs.get("07-techniques/modifier-techniques.md", "")
        self.assertIn("{1_Amount}", text)
        self.assertIn("{Property}", text)
        # 该章节点名"必写"，避免又变成"按需"的软提示
        self.assertIn("必写", text)


if __name__ == "__main__":
    unittest.main()
