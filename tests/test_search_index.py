"""BM25 检索层（db.search_index）回归测试。

依赖真实游戏库/文本库的用例在库缺失时 skip（CI/无游戏环境不报错）。
"""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from ModTools_5_4.app.settings_store import load_settings
from ModTools_5_4.db import search_index
from ModTools_5_4.db.loc_text import LOC_REF_PATTERN

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def _db_paths() -> tuple[str, str] | None:
    settings = load_settings()
    gdb = str(settings.game_db_path or "")
    if not gdb or not Path(gdb).exists():
        alt = Path.home() / "AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
        if alt.exists():
            gdb = str(alt)
        else:
            return None
    tdb = str(settings.active_text_db_path or "")
    if not tdb or not Path(tdb).exists():
        candidate = _WORKSPACE_ROOT / "local_text_New.sqlite"
        tdb = str(candidate) if candidate.exists() else ""
    return gdb, tdb


class TokenizeTestCase(unittest.TestCase):
    def test_chinese_bigram(self) -> None:
        tokens = search_index.tokenize("贸易路线")
        self.assertIn("贸易", tokens)
        self.assertIn("易路", tokens)
        self.assertIn("路线", tokens)

    def test_domain_terms(self) -> None:
        tokens = search_index.tokenize("通往你城市的贸易路线加产出")
        self.assertIn("术语:TRADE_ROUTE", tokens)
        self.assertIn("术语:YIELD", tokens)
        self.assertIn("术语:CITY", tokens)

    def test_english_type_split(self) -> None:
        tokens = search_index.tokenize("MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD")
        self.assertIn("modifier", tokens)
        self.assertIn("trade", tokens)
        self.assertIn("route", tokens)
        self.assertIn("yield", tokens)

    def test_markup_stripped(self) -> None:
        cleaned = search_index.strip_markup("+2[ICON_Gold]金币[NEWLINE]下一行")
        self.assertNotIn("[ICON_Gold]", cleaned)
        self.assertNotIn("[NEWLINE]", cleaned)
        self.assertIn("金币", cleaned)

    def test_empty(self) -> None:
        self.assertEqual(search_index.tokenize(""), [])


@unittest.skipUnless(_db_paths() is not None, "无游戏数据库，跳过检索索引测试")
class SearchIndexTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gdb, cls.tdb = _db_paths() or ("", "")
        cls.game_conn = sqlite3.connect(cls.gdb)
        cls.loc_conn = sqlite3.connect(cls.tdb) if cls.tdb else None
        from ModTools_5_4.db.ability_search import OBJECT_TYPES

        cls.object_types = OBJECT_TYPES

    @classmethod
    def tearDownClass(cls) -> None:
        cls.game_conn.close()
        if cls.loc_conn is not None:
            cls.loc_conn.close()

    def _index(self) -> search_index.SearchIndex:
        return search_index.get_index(self.game_conn, self.loc_conn, self.object_types)

    def _search(self, query: str, limit: int = 200) -> list[dict]:
        index = self._index()
        boost = " ".join(search_index.iter_matched_terms(query))
        return index.search(
            query,
            limit=limit,
            boost_query=boost,
            boost_weight=search_index.EXPANSION_BOOST_WEIGHT,
        )

    def test_index_built_with_corpus(self) -> None:
        index = self._index()
        self.assertGreater(index.document_count, 5000, "语料应包含对象+效果+条件文档")
        self.assertGreater(index.term_count, 3000)

    def test_index_cached_by_mtime(self) -> None:
        first = search_index.get_index(self.game_conn, self.loc_conn, self.object_types)
        second = search_index.get_index(self.game_conn, self.loc_conn, self.object_types)
        self.assertIs(first, second, "同一数据库（mtime 未变）应复用索引")

    def test_no_unresolved_loc_refs_in_corpus(self) -> None:
        """语料应经嵌套解析——不得残留 {LOC_...} 引用（否则中文永远匹配不到）。"""
        index = self._index()
        leftovers = 0
        for document in index._data.documents:  # noqa: SLF001 - 测试内部结构
            if LOC_REF_PATTERN.search(document.text):
                leftovers += 1
        self.assertEqual(leftovers, 0, f"{leftovers} 条语料残留未解析 LOC 引用")

    def test_chinese_name_search(self) -> None:
        results = self._search("农场")
        types = {item["type"] for item in results}
        self.assertIn("IMPROVEMENT_FARM", types)

    def test_english_type_search(self) -> None:
        results = self._search("DISTRICT_HARBOR")
        self.assertTrue(results)
        self.assertEqual(results[0]["type"], "DISTRICT_HARBOR", "精确 Type 查询应排第一")

    def test_natural_language_trade_route_query(self) -> None:
        """用户测试用例：通往你城市的贸易路线加产出 —— 应召回贸易路线产出实现。

        修复前该查询经"整句子串 + 46 词字典"只得到 CITY/TRADE 噪声（200 条无关结果）。
        """
        results = self._search("通往你城市的贸易路线加产出", limit=30)
        self.assertTrue(results)
        top_types = [item["type"] for item in results[:10]]
        # 期望：前排出现"贸易路线 + 产出/金币"类实现（伟人/政策/特质/建筑任一）
        joined = " ".join(top_types)
        self.assertTrue(
            ("GREAT_PERSON" in joined) or ("POLICY" in joined) or ("MINOR_CIV" in joined),
            f"前 10 应有贸易路线相关实现，实际：{top_types}",
        )
        # 至少一条命中摘要里同时出现"贸易路线"与产出词（金币/信仰/产出等）
        summaries = " ".join(str(item["summary"]) for item in results[:10])
        self.assertIn("贸易路线", summaries)

    def test_relevance_sorted_descending(self) -> None:
        results = self._search("贸易路线")
        scores = [item["score"] for item in results]
        self.assertEqual(scores, sorted(scores, reverse=True), "结果必须按分数降序")

    def test_category_filter(self) -> None:
        results = self._search("贸易路线", limit=200)
        filtered = self._index().search(
            "贸易路线", category="policy", limit=50,
            boost_query=" ".join(search_index.iter_matched_terms("贸易路线")),
        )
        self.assertTrue(filtered)
        self.assertTrue(all(item["category"] == "policy" for item in filtered))
        self.assertLessEqual(len(filtered), len(results))

    def test_technology_and_civic_registered(self) -> None:
        """科技/市政已进入检索语料：绑定表存在，索引能反查到对象。"""
        from ModTools_5_4.db.ability_search import OBJECT_TYPES

        self.assertIn("technology", OBJECT_TYPES)
        self.assertIn("civic", OBJECT_TYPES)
        self.assertEqual(OBJECT_TYPES["technology"]["table"], "Technologies")
        self.assertEqual(OBJECT_TYPES["civic"]["table"], "Civics")

        for table, obj_col, category in (
            ("TechnologyModifiers", "TechnologyType", "technology"),
            ("CivicModifiers", "CivicType", "civic"),
        ):
            with self.subTest(table=table):
                row = self.game_conn.execute(
                    f"SELECT {obj_col}, ModifierId FROM {table} LIMIT 1"
                ).fetchone()
                if row is None:
                    self.skipTest(f"游戏库无 {table} 数据")
                obj_type, modifier_id = str(row[0] or ""), str(row[1] or "")
                results = self._search(modifier_id)
                categories = {str(item.get("category")) for item in results}
                self.assertIn(category, categories, f"{modifier_id} 应反查到 {category} 对象")
                self.assertIn(obj_type, {str(item.get("type")) for item in results})

    def test_technology_category_filter_via_search_all(self) -> None:
        from ModTools_5_4.db import ability_search

        row = self.game_conn.execute(
            "SELECT ModifierId FROM TechnologyModifiers LIMIT 1"
        ).fetchone()
        if row is None:
            self.skipTest("游戏库无 TechnologyModifiers 数据")
        modifier_id = str(row[0] or "")
        res = ability_search.search_all(
            self.game_conn, self.loc_conn, modifier_id, category="technology", limit=20
        )
        self.assertTrue(res["results"], "科技效果应能按分类过滤检索")
        self.assertTrue(all(str(item.get("category")) == "technology" for item in res["results"]))

    def test_technology_object_detail_includes_modifiers(self) -> None:
        """科技详情（能力树）应列出 TechnologyModifiers 绑定的 Modifier。"""
        from ModTools_5_4.db import ability_search

        row = self.game_conn.execute(
            "SELECT TechnologyType, ModifierId FROM TechnologyModifiers LIMIT 1"
        ).fetchone()
        if row is None:
            self.skipTest("游戏库无 TechnologyModifiers 数据")
        tech_type, modifier_id = str(row[0] or ""), str(row[1] or "")
        detail = ability_search.fetch_object_detail(self.game_conn, self.loc_conn, "technology", tech_type)
        self.assertIsNotNone(detail, f"科技 {tech_type} 详情应存在")
        collected = {
            mid
            for group in (detail or {}).get("modifier_groups", [])
            for node in group.get("modifiers", [])
            for mid in [str(node.get("modifier_id") or "")]
        }
        self.assertIn(modifier_id, collected, "能力树应包含 TechnologyModifiers 绑定的 Modifier")


if __name__ == "__main__":
    unittest.main()
