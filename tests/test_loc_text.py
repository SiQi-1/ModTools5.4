"""LOC 文本解析（db.loc_text 单一实现）回归测试。"""
from __future__ import annotations

import sqlite3
import unittest

from ModTools_5_4.db.loc_text import (
    LOC_REF_PATTERN,
    contains_ref,
    looks_like_tag,
    make_sqlite_fetcher,
    resolve_tag,
    resolve_tag_or_original,
    resolve_text,
)


def _fetch_from(mapping: dict[str, str]):
    def fetch(tag: str) -> str | None:
        return mapping.get(tag)

    return fetch


class ResolveTextTestCase(unittest.TestCase):
    def test_single_level_reference(self) -> None:
        fetch = _fetch_from({"LOC_A": "苹果"})
        self.assertEqual(resolve_text(fetch, "{LOC_A}"), "苹果")
        self.assertEqual(resolve_text(fetch, "值：{LOC_A}！"), "值：苹果！")

    def test_nested_reference_chain(self) -> None:
        """A → B → C 三层引用应全部展开（历史 bug：能力搜索只解析一层）。"""
        fetch = _fetch_from({"LOC_A": "{LOC_B}", "LOC_B": "{LOC_C}", "LOC_C": "深层文本"})
        self.assertEqual(resolve_text(fetch, "{LOC_A}"), "深层文本")
        self.assertEqual(resolve_tag(fetch, "LOC_A"), "深层文本")

    def test_missing_reference_kept(self) -> None:
        fetch = _fetch_from({"LOC_A": "值：{LOC_MISSING}。"})
        self.assertEqual(resolve_text(fetch, "{LOC_A}"), "值：{LOC_MISSING}。")

    def test_cycle_does_not_hang(self) -> None:
        """互相引用不得死循环，未解析部分保留原样。"""
        fetch = _fetch_from({"LOC_A": "{LOC_B}", "LOC_B": "{LOC_A}"})
        result = resolve_text(fetch, "{LOC_A}")
        self.assertIn("LOC_", result)  # 无法完全解析，但必须返回

    def test_self_reference(self) -> None:
        fetch = _fetch_from({"LOC_A": "前缀{LOC_A}后缀"})
        result = resolve_text(fetch, "{LOC_A}")
        self.assertIn("前缀", result)
        self.assertIn("后缀", result)

    def test_numeric_placeholders_preserved(self) -> None:
        """{1_Amount} 等数值占位符不是 LOC 引用，必须原样保留。"""
        fetch = _fetch_from({"LOC_A": "获得{1_Amount}[ICON_Gold]金币"})
        self.assertEqual(resolve_text(fetch, "{LOC_A}"), "获得{1_Amount}[ICON_Gold]金币")

    def test_depth_limit(self) -> None:
        """超深引用链在 max_depth 内停止（不无限展开）。"""
        mapping = {f"LOC_L{i}": f"{{LOC_L{i + 1}}}" for i in range(30)}
        mapping["LOC_L30"] = "终点"
        fetch = _fetch_from(mapping)
        result = resolve_text(fetch, "{LOC_L0}", max_depth=4)
        self.assertIn("LOC_", result)
        self.assertNotIn("终点", result)

    def test_tag_or_original_semantics(self) -> None:
        fetch = _fetch_from({"LOC_A": "中文"})
        self.assertEqual(resolve_tag_or_original(fetch, "LOC_A"), "中文")
        self.assertEqual(resolve_tag_or_original(fetch, "LOC_NOPE"), "LOC_NOPE")
        self.assertIsNone(resolve_tag(fetch, "LOC_NOPE"))

    def test_strip_reference_newlines(self) -> None:
        fetch = _fetch_from({"LOC_A": "第一行\n第二行"})
        self.assertEqual(resolve_text(fetch, "{LOC_A}"), "第一行\n第二行")
        self.assertEqual(
            resolve_text(fetch, "{LOC_A}", strip_reference_newlines=True), "第一行第二行"
        )

    def test_helpers(self) -> None:
        self.assertTrue(looks_like_tag("LOC_X_NAME"))
        self.assertTrue(looks_like_tag("loc_x_name"))
        self.assertFalse(looks_like_tag("普通文本"))
        self.assertTrue(contains_ref("前缀{LOC_X}"))
        self.assertFalse(contains_ref("普通文本"))
        self.assertEqual(LOC_REF_PATTERN.findall("{LOC_A} 和 { LOC_B }"), ["LOC_A", "LOC_B"])


class SqliteFetcherTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE LocalizedText (Tag TEXT, Language TEXT, Text TEXT)")
        self.conn.executemany(
            "INSERT INTO LocalizedText VALUES (?, ?, ?)",
            [
                ("LOC_A", "zh_Hans_CN", "甲"),
                ("LOC_B", "zh_Hans_CN", "{LOC_A}乙"),
                ("LOC_EN_ONLY", "en_US", "english only"),
            ],
        )
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()

    def test_fetch_and_nested(self) -> None:
        fetch = make_sqlite_fetcher(self.conn)
        self.assertEqual(fetch("LOC_A"), "甲")
        self.assertEqual(resolve_tag(fetch, "LOC_B"), "甲乙")

    def test_language_fallback(self) -> None:
        fetch = make_sqlite_fetcher(self.conn, language="zh_Hans_CN", fallback_any_language=True)
        self.assertEqual(fetch("LOC_EN_ONLY"), "english only")
        strict = make_sqlite_fetcher(self.conn, language="zh_Hans_CN", fallback_any_language=False)
        self.assertIsNone(strict("LOC_EN_ONLY"))

    def test_missing_tag(self) -> None:
        fetch = make_sqlite_fetcher(self.conn)
        self.assertIsNone(fetch("LOC_NOT_EXIST"))


if __name__ == "__main__":
    unittest.main()
