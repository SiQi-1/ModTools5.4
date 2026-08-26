"""modgen search —— 效果/能力查询（AI 知识获取的内置途径）。

纯标准库实现，不依赖 GUI：在命令行直接"搜效果 → 看原版实现"，方法论内置：
不知道某个效果怎么做 → 先 search 找到游戏里现成的对象和 Modifier 实现 → 照抄，
而不是凭记忆断言"没有现成实现"。

数据源：
- 游戏库 DebugGameplay.sqlite（对象/绑定/Modifier 全链路）
- 可选文本库（中文关键词反查；不提供时中文关键词只能命中英文 Type）

路径解析顺序：--game-db/--text-db 参数 > 当前目录 settings.json > 游戏默认路径。
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

# ── 对象类型（轻量版，与 GUI 能力搜索对齐）────────────────────
OBJECT_TYPES: dict[str, dict[str, Any]] = {
    "civilization": {"label": "文明", "table": "Civilizations", "type_col": "CivilizationType", "name_col": "Name", "desc_col": "Description"},
    "leader": {"label": "领袖", "table": "Leaders", "type_col": "LeaderType", "name_col": "Name", "desc_col": None},
    "trait": {"label": "特质", "table": "Traits", "type_col": "TraitType", "name_col": "Name", "desc_col": "Description"},
    "district": {"label": "区域", "table": "Districts", "type_col": "DistrictType", "name_col": "Name", "desc_col": "Description"},
    "building": {"label": "建筑", "table": "Buildings", "type_col": "BuildingType", "name_col": "Name", "desc_col": "Description"},
    "unit": {"label": "单位", "table": "Units", "type_col": "UnitType", "name_col": "Name", "desc_col": "Description"},
    "improvement": {"label": "改良设施", "table": "Improvements", "type_col": "ImprovementType", "name_col": "Name", "desc_col": "Description"},
    "project": {"label": "项目", "table": "Projects", "type_col": "ProjectType", "name_col": "Name", "desc_col": "Description"},
    "policy": {"label": "政策卡", "table": "Policies", "type_col": "PolicyType", "name_col": "Name", "desc_col": "Description"},
    "governor": {"label": "总督", "table": "Governors", "type_col": "GovernorType", "name_col": "Name", "desc_col": "Description"},
    "governor_promotion": {"label": "总督晋升", "table": "GovernorPromotions", "type_col": "GovernorPromotionType", "name_col": "Name", "desc_col": "Description"},
    "great_person": {"label": "伟人", "table": "GreatPersonIndividuals", "type_col": "GreatPersonIndividualType", "name_col": "Name", "desc_col": None},
    "unit_ability": {"label": "单位能力", "table": "UnitAbilities", "type_col": "UnitAbilityType", "name_col": "Name", "desc_col": "Description"},
    "unit_promotion": {"label": "单位晋升", "table": "UnitPromotions", "type_col": "UnitPromotionType", "name_col": "Name", "desc_col": "Description"},
}
OBJECT_ORDER = list(OBJECT_TYPES.keys())

# 绑定表：(表, 对象列, Modifier 列, 类型 key)
BINDING_TABLES: list[tuple[str, str, str, str]] = [
    ("TraitModifiers", "TraitType", "ModifierId", "trait"),
    ("DistrictModifiers", "DistrictType", "ModifierId", "district"),
    ("BuildingModifiers", "BuildingType", "ModifierId", "building"),
    ("ImprovementModifiers", "ImprovementType", "ModifierID", "improvement"),
    ("ProjectCompletionModifiers", "ProjectType", "ModifierId", "project"),
    ("PolicyModifiers", "PolicyType", "ModifierId", "policy"),
    ("GovernorPromotionModifiers", "GovernorPromotionType", "ModifierId", "governor_promotion"),
    ("UnitAbilityModifiers", "UnitAbilityType", "ModifierId", "unit_ability"),
    ("UnitPromotionModifiers", "UnitPromotionType", "ModifierId", "unit_promotion"),
    ("GreatPersonIndividualActionModifiers", "GreatPersonIndividualType", "ModifierId", "great_person"),
    ("GreatPersonIndividualBirthModifiers", "GreatPersonIndividualType", "ModifierId", "great_person"),
]

# 中文效果词 → 英文概念（与 GUI 能力搜索对齐的常用子集）
EFFECT_KEYWORDS: dict[str, str] = {
    "宣战": "WAR", "战争": "WAR", "产能": "PRODUCTION", "生产力": "PRODUCTION",
    "信仰": "FAITH", "科技": "SCIENCE", "文化": "CULTURE", "金币": "GOLD",
    "食物": "FOOD", "宜居": "AMENITY", "住房": "HOUSING", "移动": "MOVEMENT",
    "战斗力": "STRENGTH", "旅游": "TOURISM", "伟人": "GREAT_PERSON",
    "区域": "DISTRICT", "建筑": "BUILDING", "单位": "UNIT", "改良": "IMPROVEMENT",
    "相邻": "ADJACEN", "城市": "CITY", "人口": "POPULATION", "时代": "ERA",
    "总督": "GOVERNOR", "海军": "NAVAL", "陆军": "LAND",
}


def default_game_db_path() -> Path:
    return Path.home() / "AppData" / "Local" / "Firaxis Games" / "Sid Meier's Civilization VI" / "Cache" / "DebugGameplay.sqlite"


def resolve_db_paths(
    game_db: str | None, text_db: str | None
) -> tuple[Path | None, Path | None]:
    """路径解析：参数 > settings.json（当前目录/开发目录）> 游戏默认路径。"""
    gdb = Path(game_db) if game_db else None
    tdb = Path(text_db) if text_db else None
    if gdb is None or tdb is None:
        for settings_path in (Path("settings.json"), Path("ModTools_5_4/data/settings.json")):
            if not settings_path.exists():
                continue
            try:
                payload = json.loads(settings_path.read_text(encoding="utf-8-sig"))
                if gdb is None and payload.get("game_db_path"):
                    gdb = Path(str(payload["game_db_path"]))
                if tdb is None and payload.get("active_text_db_path"):
                    tdb = Path(str(payload["active_text_db_path"]))
            except Exception:
                pass
            if gdb is not None and tdb is not None:
                break
    if gdb is None:
        gdb = default_game_db_path()
    if gdb is not None and not gdb.exists():
        gdb = None
    if tdb is not None and not tdb.exists():
        tdb = None
    return gdb, tdb


def _rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        cursor = conn.execute(sql, params)
        columns = [str(d[0]) for d in cursor.description or []]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def _resolve_loc(conn: Optional[sqlite3.Connection], tag: object) -> str:
    text = str(tag or "").strip()
    if not text or conn is None:
        return text
    try:
        row = conn.execute(
            "SELECT Text FROM LocalizedText WHERE Tag = ? AND lower(Language) = ? LIMIT 1",
            (text, "zh_hans_cn"),
        ).fetchone()
    except sqlite3.Error:
        return text
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()
    return text


def _clean(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.startswith("NO_"):
        return ""
    return text


def search_keyword(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    keyword: str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """三通道搜索（对象文本 / 能力层反查 / 效果词扩展），返回结果列表。"""
    kw = str(keyword or "").strip()
    if not kw:
        return []
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    kw_upper = kw.upper()
    is_ascii = all(ord(ch) < 128 for ch in kw)
    expansions = [kw_upper]
    if not is_ascii:
        expansions = [en for cn, en in EFFECT_KEYWORDS.items() if cn in kw] or [kw_upper]

    def add(category: str, obj_type: str, hit: str, summary: str) -> None:
        key = (category, obj_type)
        if key in seen:
            return
        seen.add(key)
        meta = OBJECT_TYPES[category]
        row = _rows(game_conn, f"SELECT * FROM {meta['table']} WHERE {meta['type_col']} = ?", (obj_type,))
        detail = row[0] if row else {}
        raw_name = str(detail.get(meta["name_col"]) or "") if meta["name_col"] else ""
        name = _resolve_loc(loc_conn, raw_name) if raw_name.strip().startswith("LOC_") else raw_name
        if not name:
            name = obj_type
        results.append({
            "category": category,
            "label": meta["label"],
            "name": name,
            "type": obj_type,
            "hit": hit,
            "summary": summary,
        })

    # 通道① 对象文本
    for key in OBJECT_ORDER:
        meta = OBJECT_TYPES[key]
        type_col = meta["type_col"]
        for row in _rows(game_conn, f"SELECT * FROM {meta['table']}"):
            type_value = _clean(row.get(type_col))
            if not type_value:
                continue
            if is_ascii:
                if kw_upper in type_value.upper():
                    add(key, type_value, "Type", type_value)
                else:
                    name_raw = str(row.get(meta["name_col"]) or "") if meta["name_col"] else ""
                    if kw_upper in name_raw.upper():
                        add(key, type_value, "Tag", name_raw)
            else:
                for col in (meta["name_col"], meta["desc_col"]):
                    raw = str(row.get(col) or "") if col else ""
                    if raw.strip().startswith("LOC_"):
                        resolved = _resolve_loc(loc_conn, raw)
                        if resolved != raw.strip() and kw in resolved:
                            add(key, type_value, "描述" if col == meta["desc_col"] else "名称", resolved)
                            break

    # 通道② 能力层反查
    hit_modifiers: set[str] = set()
    for exp in expansions:
        for table, id_col in (
            ("Modifiers", "ModifierId"),
            ("ModifierArguments", "ModifierId"),
        ):
            for row in _rows(game_conn, f"SELECT * FROM {table}"):
                matched = [
                    f"{col}={str(val or '')[:40]}"
                    for col, val in row.items()
                    if str(val or "") and exp in str(val).upper()
                ]
                mid = _clean(row.get(id_col))
                if matched and mid:
                    hit_modifiers.add(mid)
        for row in _rows(game_conn, "SELECT * FROM Requirements"):
            if exp in str(row.get("RequirementType") or "").upper():
                hit_modifiers.update(
                    _reqset_to_modifiers(game_conn, str(row.get("RequirementId") or ""))
                )
        for row in _rows(game_conn, "SELECT * FROM RequirementArguments"):
            if exp in str(row.get("Value") or "").upper():
                hit_modifiers.update(
                    _reqset_to_modifiers(game_conn, str(row.get("RequirementId") or ""))
                )

    summary_map: dict[str, str] = {}
    for mid in hit_modifiers:
        row = _rows(game_conn, "SELECT ModifierType FROM Modifiers WHERE ModifierId = ?", (mid,))
        summary_map[mid] = f"{mid} [{row[0]['ModifierType']}]" if row else mid
    for table, obj_col, mod_col, category in BINDING_TABLES:
        for row in _rows(game_conn, f"SELECT {obj_col}, {mod_col} FROM {table}"):
            mid = _clean(row.get(mod_col))
            obj_type = _clean(row.get(obj_col))
            if mid in hit_modifiers and obj_type:
                add(category, obj_type, "能力", summary_map.get(mid, mid))

    return results[:limit]


def _reqset_to_modifiers(game_conn: sqlite3.Connection, requirement_id: str) -> set[str]:
    """条件 → 使用它的 Modifier（经 RequirementSetRequirements → Modifiers）。"""
    out: set[str] = set()
    for row in _rows(game_conn, "SELECT RequirementSetId FROM RequirementSetRequirements WHERE RequirementId = ?", (requirement_id,)):
        rsid = _clean(row.get("RequirementSetId"))
        if not rsid:
            continue
        for mrow in _rows(
            game_conn,
            "SELECT ModifierId FROM Modifiers WHERE SubjectRequirementSetId = ? OR OwnerRequirementSetId = ?",
            (rsid, rsid),
        ):
            mid = _clean(mrow.get("ModifierId"))
            if mid:
                out.add(mid)
    return out


def object_modifier_summary(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    category: str,
    type_value: str,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """对象绑定的 Modifier 摘要（ModifierId/EffectType/参数/条件），供照抄实现。"""
    meta = OBJECT_TYPES.get(category)
    if not meta:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for table, obj_col, mod_col, _cat in BINDING_TABLES:
        for row in _rows(game_conn, f"SELECT {mod_col} FROM {table} WHERE {obj_col} = ?", (type_value,)):
            mid = _clean(row.get(mod_col))
            if not mid or mid in seen:
                continue
            seen.add(mid)
            mod = _rows(game_conn, "SELECT * FROM Modifiers WHERE ModifierId = ?", (mid,))
            if not mod:
                continue
            mod_row = mod[0]
            mod_type = str(mod_row.get("ModifierType") or "")
            dyn = _rows(game_conn, "SELECT * FROM DynamicModifiers WHERE ModifierType = ?", (mod_type,))
            effect = str(dyn[0].get("EffectType") or "") if dyn else ""
            args = [
                f"{r['Name']}={r['Value']}"
                for r in _rows(game_conn, "SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (mid,))
            ]
            reqsets = []
            for role in ("SubjectRequirementSetId", "OwnerRequirementSetId"):
                rsid = _clean(mod_row.get(role))
                if not rsid:
                    continue
                reqs = []
                for rr in _rows(game_conn, "SELECT RequirementId FROM RequirementSetRequirements WHERE RequirementSetId = ?", (rsid,)):
                    rid = _clean(rr.get("RequirementId"))
                    if not rid:
                        continue
                    req = _rows(game_conn, "SELECT RequirementType FROM Requirements WHERE RequirementId = ?", (rid,))
                    if req:
                        req_args = [
                            f"{r['Name']}={r['Value']}"
                            for r in _rows(game_conn, "SELECT Name, Value FROM RequirementArguments WHERE RequirementId = ?", (rid,))
                        ]
                        reqs.append(f"{rid} [{req[0]['RequirementType']}]" + (f" args={req_args}" if req_args else ""))
                reqsets.append(f"{role[:-2]}:{rsid}" + (f" → {'; '.join(reqs)}" if reqs else ""))
            out.append({
                "modifier_id": mid,
                "modifier_type": mod_type,
                "effect_type": effect,
                "args": args,
                "reqsets": reqsets,
            })
            if len(out) >= limit:
                return out
    return out
