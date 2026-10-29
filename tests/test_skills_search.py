# -*- coding: utf-8 -*-
"""技能库检索引擎（ModTools_5_4/skills_search.py）回归测试。

覆盖：
1. `_` 前缀的开发产物不进索引。
2. 关键通用规则文档可被检索到。
3. 分层后的路径前缀权重（_kind）、reading_plan 的分级/字节/max_kb 告警与 30 KB 必读预算。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ModTools_5_4 import skills_search  # noqa: E402

BASIC_TASKS = {
    "新增一个单位": "reference/entities/unit.md",
    "新增文明": "reference/entities/civilization.md",
    "做一个建筑": "reference/entities/building.md",
    "改 UI 面板": "reference/art/ui-assets.md",
    "修改文本": "reference/config/text.md",
}


class DevArtifactFilterTestCase(unittest.TestCase):
    def test_underscore_prefixed_paths_are_dev_artifacts(self) -> None:
        for rel in (
            "reference/modifiers/_generate_final.py",
            "reference/modifiers/_modifier-city.md.effects.txt",
            "reference/modifiers/_trace_result3.txt",
            "some_dir/_sub/file.md",
            "__pycache__/x.py",
        ):
            self.assertTrue(skills_search._is_dev_artifact(rel), rel)

    def test_normal_paths_are_kept(self) -> None:
        for rel in (
            "reference/modifiers/techniques.md",
            "reference/modifiers/modifier-unit-combat.md",
            "guides/civ-pitfalls.md",
            "AGENTS.md",
        ):
            self.assertFalse(skills_search._is_dev_artifact(rel), rel)

    def test_windows_separator_handled(self) -> None:
        self.assertTrue(skills_search._is_dev_artifact(r"reference\modifiers\_query_db.py"))


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
        self.assertIn("reference/modifiers/techniques.md", self.docs)
        self.assertIn("guides/civ-pitfalls.md", self.docs)
        self.assertIn("reference/entities/naming.md", self.docs)

    def test_kind_uses_new_layer_prefixes(self) -> None:
        self.assertEqual(skills_search._kind("RULES.md"), "rule")
        self.assertEqual(skills_search._kind("reference/lua/code-style.md"), "rule")
        self.assertEqual(skills_search._kind("guides/INDEX.md"), "workflow")
        self.assertEqual(skills_search._kind("guides/modifiers.md"), "guide")
        self.assertEqual(skills_search._kind("reference/entities/unit.md"), "guide")
        self.assertEqual(skills_search._kind("reference/lua/lua-workshop-citypanel.md"), "example")
        self.assertEqual(skills_search._kind("reference/lua/lua-binary.md"), "reference")

    def test_modifier_strings_rule_is_searchable(self) -> None:
        """战斗力类必写 ModifierStrings 的通用规则必须能被检索到。"""
        results = skills_search.search_skills("ModifierStrings", root=self.root, limit=10)
        rels = [item.get("rel") for item in results]
        self.assertIn("reference/modifiers/techniques.md", rels,
                      "通用规则文档应出现在 ModifierStrings 的检索结果里：%s" % rels)

    def test_rule_states_placeholder_convention(self) -> None:
        text = self.docs.get("reference/modifiers/techniques.md", "")
        self.assertIn("{1_Amount}", text)
        self.assertIn("{Property}", text)
        self.assertIn("必写", text)


class ReadingPlanTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = skills_search.default_skills_root()
        if not cls.root.is_dir():
            raise unittest.SkipTest("skills/ 目录不存在")

    def test_five_basic_tasks_match_and_fit_budget(self) -> None:
        for query, expected in BASIC_TASKS.items():
            with self.subTest(query=query):
                plan = skills_search.reading_plan(query, root=self.root)
                self.assertTrue(plan["matched"], "基础任务应命中 catalog 路由")
                self.assertIn(expected, plan["required"], plan["required"])
                self.assertLessEqual(plan["must_kb"], 30.0, plan["items"])
                self.assertTrue(plan["budget"]["ok"])

    def test_plan_items_carry_level_bytes_and_sections(self) -> None:
        plan = skills_search.reading_plan("二进制上限", root=self.root)
        self.assertTrue(plan["items"])
        for item in plan["items"]:
            self.assertIn(item["level"], {"must", "optional"})
            self.assertIsInstance(item["bytes"], int)
            self.assertGreaterEqual(item["kb"], 0)
        section_items = [i for i in plan["items"] if i.get("section")]
        self.assertTrue(section_items, "catalog 应使用 section 级读取控制上下文")

    def test_unknown_task_keeps_rules_only(self) -> None:
        plan = skills_search.reading_plan("xyzzyquux", root=self.root)
        self.assertFalse(plan["matched"])
        self.assertEqual(plan["required"], ["RULES.md", "WORKFLOW.md"])
        self.assertLessEqual(plan["must_kb"], 30.0)


class PlanBudgetWarningTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, content: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_catalog(self, routes) -> None:
        self.put("RULES.md", "# 规则\n" + "规则 " * 200)
        self.put("WORKFLOW.md", "# 流程\n" + "流程 " * 200)
        self.put("catalog.json", json.dumps(
            {"version": 1, "always_read": ["RULES.md", "WORKFLOW.md"], "routes": routes},
            ensure_ascii=False))

    def test_route_max_kb_warning(self) -> None:
        self.put("big.md", "# 大参考\n" + "内容 " * 3000)
        self.write_catalog([{"id": "big", "level": "must", "max_kb": 1,
                             "aliases": ["大参考"], "read": ["big.md"]}])
        plan = skills_search.reading_plan("大参考", root=self.root)
        self.assertTrue(any("max_kb" in w for w in plan["warnings"]), plan["warnings"])

    def test_total_budget_demotes_extra_routes(self) -> None:
        self.put("a.md", "# 甲\n" + "甲 " * 5000)
        self.put("b.md", "# 乙\n" + "乙 " * 5000)
        self.write_catalog([
            {"id": "a", "level": "must", "max_kb": 13, "aliases": ["甲"], "read": ["a.md"]},
            {"id": "b", "level": "must", "max_kb": 13, "aliases": ["甲"], "read": ["b.md"]},
        ])
        plan = skills_search.reading_plan("甲", root=self.root)
        self.assertLessEqual(plan["must_kb"], 30.0)
        self.assertIn("b", plan["budget"]["demoted"])
        self.assertIn("b.md", plan["optional"])


if __name__ == "__main__":
    unittest.main()
