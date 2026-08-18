"""能力实现搜索回归测试（2026-08-16）。

依赖真实游戏库/文本库：库不存在时 skip（CI/无游戏环境不报错）。
覆盖：三通道搜索、效果词扩展、对象详情（主表/副表/相邻加成）、
Modifier 嵌套展开（ATTACH/GRANT_ABILITY）。
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from ModTools_5_4.app.settings_store import load_settings  # noqa: E402
from ModTools_5_4.db.ability_search import (  # noqa: E402
    build_adjacency_description,
    fetch_object_detail,
    open_dbs,
    search_all,
)

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
        if candidate.exists():
            tdb = str(candidate)
        else:
            tdb = ""
    return gdb, tdb


@unittest.skipUnless(_db_paths() is not None, "无游戏数据库，跳过能力搜索测试")
class AbilitySearchTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gdb, cls.tdb = _db_paths() or ("", "")

    def setUp(self) -> None:
        self.conn_ctx = open_dbs(self.gdb, self.tdb)

    def tearDown(self) -> None:
        pass

    def _search(self, keyword: str, category=None):
        with self.conn_ctx as (gc, lc):
            return search_all(gc, lc, keyword, category=category)

    # ── 通道① 对象文本搜索 ──
    def test_chinese_object_search_finds_harbor(self) -> None:
        result = self._search("港口")
        types = {item["type"] for item in result["results"]}
        self.assertIn("DISTRICT_HARBOR", types, "中文'港口'应命中 DISTRICT_HARBOR")

    def test_english_type_search(self) -> None:
        result = self._search("DISTRICT_HARBOR")
        self.assertTrue(
            any(item["type"] == "DISTRICT_HARBOR" for item in result["results"]),
            "英文 Type 应命中 DISTRICT_HARBOR",
        )

    # ── 通道③ 效果词映射 → 通道② 能力搜索 ──
    def test_effect_keyword_expansion_hits_war_abilities(self) -> None:
        result = self._search("宣战")
        self.assertTrue(result["hint"], "中文效果词'宣战'应给出扩展提示")
        self.assertTrue(result["expansions"], "应附加英文关键词")
        # 能力命中（hit == "能力"）应存在
        self.assertTrue(
            any(item.get("hit") == "能力" for item in result["results"]),
            "效果词扩展后应命中能力反查结果",
        )

    def test_english_ability_search_reverse(self) -> None:
        result = self._search("WAR")
        self.assertTrue(result["results"], "WAR 应命中持有相关能力的对象")
        self.assertTrue(
            any(item.get("hit") in ("能力", "Type") for item in result["results"]),
        )

    # ── 对象详情 ──
    def test_district_detail_has_adjacency(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "district", "DISTRICT_HARBOR")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["name"], "港口")
        self.assertTrue(detail["main"]["values"], "主表应有非空列")
        adj_tables = [st for st in detail["sub_tables"] if st.get("kind") == "adjacency"]
        self.assertTrue(adj_tables, "港口应有相邻加成表")
        for st in adj_tables:
            for row in st["rows"]:
                self.assertTrue(row["description"], "相邻加成应有自动生成描述")
                self.assertTrue(row["sources"], "相邻加成应识别出条件来源")

    def test_adjacency_description_matches_editing_convention(self) -> None:
        with self.conn_ctx as (gc, lc):
            row = gc.execute("SELECT * FROM Adjacency_YieldChanges WHERE ID = 'Harbor_Gold'").fetchone()
            self.assertIsNotNone(row, "游戏库应有 Harbor_Gold 相邻加成")
            columns = [d[0] for d in gc.execute("SELECT * FROM Adjacency_YieldChanges LIMIT 0").description]
            desc = build_adjacency_description(gc, lc, dict(zip(columns, row)))
        self.assertIn("[ICON_Gold]", desc)
        self.assertIn("金币", desc)

    def test_policy_detail_has_modifiers(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "policy", "POLICY_INTERNATIONAL_SPACE_AGENCY")
        self.assertIsNotNone(detail)
        self.assertTrue(detail["modifier_groups"], "政策卡应有 Modifier")
        first_mod = detail["modifier_groups"][0]["modifiers"][0]
        self.assertTrue(first_mod["effect_type"], "Modifier 应解析出 EffectType")
        self.assertTrue(first_mod["args"], "Modifier 应有参数")

    # ── 嵌套展开 ──
    def test_ability_nested_expansion(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "unit_ability", "ABILITY_RELIGIOUS_IGNORE_TERRAIN_COST")
        self.assertIsNotNone(detail)
        mods = [m for g in detail["modifier_groups"] for m in g["modifiers"]]
        self.assertGreaterEqual(len(mods), 2, "GRANT_ABILITY 链应展开出 UnitAbilityModifiers 下全部 modifier")
        self.assertTrue(all(m["effect_type"] for m in mods))

    def test_trait_nested_attach_no_cycle(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "trait", "TRAIT_CIVILIZATION_PORTUGAL")
        self.assertIsNotNone(detail)
        self.assertTrue(detail["modifier_groups"], "葡萄牙特质应有 Modifier")
        self.assertTrue(detail["binders"], "特质应显示被哪些对象使用")

    def test_detail_unknown_object_returns_none(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "district", "DISTRICT_NOT_EXISTS_XYZ")
        self.assertIsNone(detail)

    # ── Modifier 标志（仅非默认）与 ModifierStrings ──
    def test_modifier_flags_only_non_default(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "building", "BUILDING_BARRACKS")
        self.assertIsNotNone(detail)
        mods = [m for g in detail["modifier_groups"] for m in g["modifiers"]]
        barracks_mod = next(
            (m for m in mods if m["modifier_id"] == "BARRACKS_TRAINED_UNIT_XP_MODIFIER"), None
        )
        self.assertIsNotNone(barracks_mod, "兵营的训练经验 modifier 应存在")
        self.assertIn("永久", barracks_mod["flags"], "Permanent=1 应显示为'永久'")
        # 默认值不显示：所有 flag 值必须来自非默认规则（白名单）
        allowed = {"永久", "仅一次", "仅新对象", "可重复"}
        for flag in barracks_mod["flags"]:
            self.assertTrue(
                flag in allowed or flag.startswith("所有者上限") or flag.startswith("主体上限"),
                f"意外标志: {flag}",
            )

    def test_modifier_strings_resolved_to_chinese(self) -> None:
        with self.conn_ctx as (gc, lc):
            detail = fetch_object_detail(gc, lc, "unit_ability", "ABILITY_RELIGIOUS_IGNORE_TERRAIN_COST")
        mods = [m for g in detail["modifier_groups"] for m in g["modifiers"]]
        terrain_mod = next((m for m in mods if m["modifier_id"] == "MOD_IGNORE_TERRAIN_COST"), None)
        self.assertIsNotNone(terrain_mod)
        self.assertTrue(terrain_mod["strings"], "该 modifier 应有 ModifierStrings")
        text = str(terrain_mod["strings"][0].get("text") or "")
        self.assertNotIn("LOC_", text, "ModifierStrings 文本应已解析为中文")
        self.assertTrue(any("\u4e00" <= ch <= "\u9fff" for ch in text), "应包含中文字符")


if __name__ == "__main__":
    unittest.main()
