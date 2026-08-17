"""能力实现搜索查询层（纯函数，无 UI，可单测）。

数据源（连接由调用方提供）：
- 游戏库 DebugGameplay.sqlite：对象/绑定/Modifier 全链路
- 文本库 local_text_New.sqlite：LOC tag → 中文

功能：
1. 对象搜索（通道①）：名字/描述（中文经文本库，英文 Type/Tag）
2. 能力搜索（通道②）：ModifierId/Type/EffectType/参数/RequirementType/条件参数 LIKE → 反向找绑定对象
3. 效果词映射（通道③）：中文效果词 → 英文概念，自动附加能力搜索
4. 对象详情：主表（仅非空列）+ 副表（动态发现，相邻加成专门结构化渲染）
   + 能力树（Modifier 全链路，ATTACH/GRANT_ABILITY 嵌套递归展开，防环限深）

约定（AGENT.md 对齐）：
- 空值/NO_* 视为"无"，不展示
- 相邻加成布尔条件列 0/1；值列 NO_ 前缀为无值标记
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional
import re
import sqlite3

# ── 产出图标/中文名 ────────────────────────────────────────────
YIELD_ICON_MAP: dict[str, str] = {
    "YIELD_GOLD": "[ICON_Gold]",
    "YIELD_PRODUCTION": "[ICON_Production]",
    "YIELD_SCIENCE": "[ICON_Science]",
    "YIELD_CULTURE": "[ICON_Culture]",
    "YIELD_FAITH": "[ICON_Faith]",
    "YIELD_FOOD": "[ICON_Food]",
}
YIELD_CN_MAP: dict[str, str] = {
    "YIELD_GOLD": "金币",
    "YIELD_PRODUCTION": "生产力",
    "YIELD_SCIENCE": "科技值",
    "YIELD_CULTURE": "文化值",
    "YIELD_FAITH": "信仰值",
    "YIELD_FOOD": "食物",
    "YIELD_TOURISM": "旅游业绩",
    "YIELD_HOUSING": "住房",
    "YIELD_AMENITY": "宜居度",
    "YIELD_GREAT_PERSON_POINT": "伟人点",
}

# ── 相邻加成 ──────────────────────────────────────────────────
ADJACENCY_BOOLEAN_KEYS = (
    "OtherDistrictAdjacent", "AdjacentSeaResource", "AdjacentRiver",
    "AdjacentWonder", "AdjacentNaturalWonder", "AdjacentResource", "Self",
)
ADJACENCY_VALUE_KEYS = (
    "AdjacentTerrain", "AdjacentFeature", "AdjacentImprovement",
    "AdjacentDistrict", "AdjacentResourceClass",
)
# 值列 → 查中文名的（游戏库表, 类型列, 名称列）
_ADJACENCY_VALUE_TABLE = {
    "AdjacentTerrain": ("Terrains", "TerrainType", "Name"),
    "AdjacentFeature": ("Features", "FeatureType", "Name"),
    "AdjacentImprovement": ("Improvements", "ImprovementType", "Name"),
    "AdjacentDistrict": ("Districts", "DistrictType", "Name"),
    "AdjacentResourceClass": ("ResourceClasses", "ResourceClassType", "Name"),
}
# 布尔条件 → 中文描述（不带"相邻"前缀，由描述模板统一拼"来自每N个相邻的"）
ADJACENCY_BOOLEAN_CN: dict[str, str] = {
    "OtherDistrictAdjacent": "其他区域",
    "AdjacentSeaResource": "海洋资源",
    "AdjacentRiver": "河流",
    "AdjacentWonder": "人造奇观",
    "AdjacentNaturalWonder": "自然奇观",
    "AdjacentResource": "资源",
    "Self": "自身",
}

# ── 中文效果词 → 英文概念（通道③）─────────────────────────────
EFFECT_KEYWORD_MAP: dict[str, str] = {
    "宣战": "WAR", "战争": "WAR", "和平": "WAR",
    "产能": "PRODUCTION", "生产力": "PRODUCTION",
    "信仰": "FAITH", "科技": "SCIENCE", "科技值": "SCIENCE",
    "文化": "CULTURE", "文化值": "CULTURE", "金币": "GOLD", "金钱": "GOLD",
    "食物": "FOOD", "宜居": "AMENITY", "住房": "HOUSING",
    "移动": "MOVEMENT", "移动力": "MOVEMENT", "战斗力": "STRENGTH",
    "旅游": "TOURISM", "伟人": "GREAT_PERSON", "人口": "POPULATION",
    "区域": "DISTRICT", "建筑": "BUILDING", "单位": "UNIT",
    "改良": "IMPROVEMENT", "项目": "PROJECT", "政策": "POLICY",
    "相邻": "ADJACEN", "城市": "CITY", "蛮族": "BARBARIAN",
    "宗教": "RELIGION", "遗物": "RELIC", "贸易": "TRADE",
    "时代": "ERA", "黄金时代": "GOLDEN_AGE", "黑暗时代": "DARK_AGE",
    "总督": "GOVERNOR", "间谍": "SPY", "使徒": "APOSTLE",
    "海军": "NAVAL", "陆军": "LAND", "空袭": "AIR",
}


@contextmanager
def open_dbs(game_db_path: str, text_db_path: str) -> Iterator[tuple[sqlite3.Connection, sqlite3.Connection]]:
    """同时打开游戏库与文本库（自动关闭）。文本库路径为空时 loc_conn 为 None。"""
    game_conn = sqlite3.connect(str(game_db_path))
    try:
        loc_conn = None
        if text_db_path:
            try:
                loc_conn = sqlite3.connect(str(text_db_path))
            except sqlite3.Error:
                loc_conn = None
        try:
            yield game_conn, loc_conn
        finally:
            if loc_conn is not None:
                loc_conn.close()
    finally:
        game_conn.close()


def resolve_loc(loc_conn: Optional[sqlite3.Connection], tag: object, lang: str = "zh_Hans_CN") -> str:
    """LOC tag → 中文；失败返回原 tag。"""
    text = str(tag or "").strip()
    if not text or loc_conn is None:
        return text
    try:
        row = loc_conn.execute(
            "SELECT Text FROM LocalizedText WHERE Tag = ? AND lower(Language) = ? LIMIT 1",
            (text, lang.lower()),
        ).fetchone()
    except sqlite3.Error:
        return text
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()
    return text


# ── 对象类型注册表 ────────────────────────────────────────────
# binding_sources:
#   direct:      绑定表 (obj_col → mod_col)
#   via_trait:   经对象自身 TraitType 列 → TraitModifiers
#   via_table:   经中间表 (via_obj_col → trait_col) → TraitModifiers
#   governor_promotion: GovernorPromotions(GovernorType) → GovernorPromotionModifiers
#   gp_action/birth:    GreatPersonIndividuals → GreatPersonIndividual*Modifiers
OBJECT_TYPES: dict[str, dict[str, Any]] = {
    "civilization": {
        "label": "文明",
        "table": "Civilizations",
        "type_col": "CivilizationType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "CivilizationTraits→TraitModifiers", "kind": "via_table",
             "via_table": "CivilizationTraits", "via_obj_col": "CivilizationType", "trait_col": "TraitType"},
        ],
    },
    "leader": {
        "label": "领袖",
        "table": "Leaders",
        "type_col": "LeaderType",
        "name_col": "Name",
        "desc_col": None,
        "binding_sources": [
            {"label": "LeaderTraits→TraitModifiers", "kind": "via_table",
             "via_table": "LeaderTraits", "via_obj_col": "LeaderType", "trait_col": "TraitType"},
        ],
    },
    "trait": {
        "label": "特质",
        "table": "Traits",
        "type_col": "TraitType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "TraitModifiers", "kind": "direct",
             "table": "TraitModifiers", "obj_col": "TraitType", "mod_col": "ModifierId"},
        ],
        "show_binders": True,
    },
    "district": {
        "label": "区域",
        "table": "Districts",
        "type_col": "DistrictType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "DistrictModifiers", "kind": "direct",
             "table": "DistrictModifiers", "obj_col": "DistrictType", "mod_col": "ModifierId"},
            {"label": "TraitType→TraitModifiers", "kind": "via_trait", "trait_col": "TraitType"},
        ],
    },
    "building": {
        "label": "建筑",
        "table": "Buildings",
        "type_col": "BuildingType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "BuildingModifiers", "kind": "direct",
             "table": "BuildingModifiers", "obj_col": "BuildingType", "mod_col": "ModifierId"},
            {"label": "TraitType→TraitModifiers", "kind": "via_trait", "trait_col": "TraitType"},
        ],
    },
    "unit": {
        "label": "单位",
        "table": "Units",
        "type_col": "UnitType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "TraitType→TraitModifiers", "kind": "via_trait", "trait_col": "TraitType"},
        ],
    },
    "improvement": {
        "label": "改良设施",
        "table": "Improvements",
        "type_col": "ImprovementType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "ImprovementModifiers", "kind": "direct",
             "table": "ImprovementModifiers", "obj_col": "ImprovementType", "mod_col": "ModifierID"},
            {"label": "TraitType→TraitModifiers", "kind": "via_trait", "trait_col": "TraitType"},
        ],
    },
    "project": {
        "label": "项目",
        "table": "Projects",
        "type_col": "ProjectType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "ProjectCompletionModifiers", "kind": "direct",
             "table": "ProjectCompletionModifiers", "obj_col": "ProjectType", "mod_col": "ModifierId"},
        ],
    },
    "policy": {
        "label": "政策卡",
        "table": "Policies",
        "type_col": "PolicyType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "PolicyModifiers", "kind": "direct",
             "table": "PolicyModifiers", "obj_col": "PolicyType", "mod_col": "ModifierId"},
        ],
    },
    "governor": {
        "label": "总督",
        "table": "Governors",
        "type_col": "GovernorType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "GovernorModifiers", "kind": "direct",
             "table": "GovernorModifiers", "obj_col": "GovernorType", "mod_col": "ModifierId"},
            {"label": "GovernorPromotions→GovernorPromotionModifiers", "kind": "governor_promotion"},
        ],
    },
    "governor_promotion": {
        "label": "总督晋升",
        "table": "GovernorPromotions",
        "type_col": "GovernorPromotionType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "GovernorPromotionModifiers", "kind": "direct",
             "table": "GovernorPromotionModifiers", "obj_col": "GovernorPromotionType", "mod_col": "ModifierId"},
        ],
    },
    "great_person": {
        "label": "伟人",
        "table": "GreatPersonIndividuals",
        "type_col": "GreatPersonIndividualType",
        "name_col": "Name",
        "desc_col": None,
        "binding_sources": [
            {"label": "GreatPersonIndividualActionModifiers", "kind": "gp_action"},
            {"label": "GreatPersonIndividualBirthModifiers", "kind": "gp_birth"},
        ],
    },
    "unit_ability": {
        "label": "单位能力",
        "table": "UnitAbilities",
        "type_col": "UnitAbilityType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "UnitAbilityModifiers", "kind": "direct",
             "table": "UnitAbilityModifiers", "obj_col": "UnitAbilityType", "mod_col": "ModifierId"},
        ],
    },
    "unit_promotion": {
        "label": "单位晋升",
        "table": "UnitPromotions",
        "type_col": "UnitPromotionType",
        "name_col": "Name",
        "desc_col": "Description",
        "binding_sources": [
            {"label": "UnitPromotionModifiers", "kind": "direct",
             "table": "UnitPromotionModifiers", "obj_col": "UnitPromotionType", "mod_col": "ModifierId"},
        ],
    },
}

OBJECT_TYPE_ORDER: list[str] = [
    "civilization", "leader", "trait", "district", "building", "unit",
    "improvement", "project", "policy", "governor", "governor_promotion",
    "great_person", "unit_ability", "unit_promotion",
]

OBJECT_CATEGORY_LABELS: dict[str, str] = {key: meta["label"] for key, meta in OBJECT_TYPES.items()}


def _clean_type_value(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.startswith("NO_"):
        return ""
    return text


def _fetch_row_dict(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> Optional[dict[str, Any]]:
    try:
        cursor = conn.execute(sql, params)
        columns = [str(d[0]) for d in cursor.description or []]
        row = cursor.fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return dict(zip(columns, row))


def _fetch_all_row_dicts(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    try:
        cursor = conn.execute(sql, params)
        columns = [str(d[0]) for d in cursor.description or []]
        rows = cursor.fetchall()
    except sqlite3.Error:
        return []
    return [dict(zip(columns, row)) for row in rows]


def _object_display_name(meta: dict[str, Any], row: dict[str, Any], loc_conn: Optional[sqlite3.Connection]) -> str:
    name_col = meta.get("name_col")
    raw = str(row.get(name_col) or "").strip() if name_col else ""
    if raw:
        resolved = resolve_loc(loc_conn, raw)
        if resolved and resolved != raw:
            return resolved
        return raw
    # 兜底：Name 缺失时尝试 LOC_{Type}_NAME
    type_value = str(row.get(meta["type_col"]) or "")
    fallback = resolve_loc(loc_conn, f"LOC_{type_value}_NAME")
    if fallback and fallback != f"LOC_{type_value}_NAME":
        return fallback
    return type_value


# ── 通道①：对象文本搜索 ───────────────────────────────────────
def search_objects(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    keyword: str,
    category: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """按名字/描述/Type 搜索对象。返回 [{category, label, name, type, hit, summary}]。"""
    kw = str(keyword or "").strip()
    if not kw:
        return []
    results: list[dict[str, Any]] = []
    kw_upper = kw.upper()
    is_ascii = all(ord(ch) < 128 for ch in kw)

    for key in OBJECT_TYPE_ORDER:
        if category and key != category:
            continue
        meta = OBJECT_TYPES[key]
        type_col = meta["type_col"]
        name_col = meta.get("name_col")
        desc_col = meta.get("desc_col")
        try:
            rows = _fetch_all_row_dicts(game_conn, f"SELECT * FROM {meta['table']}", ())
        except sqlite3.Error:
            continue
        for row in rows:
            type_value = _clean_type_value(row.get(type_col))
            if not type_value:
                continue
            hit: Optional[str] = None
            summary = ""
            if is_ascii:
                if kw_upper in type_value.upper():
                    hit = "Type"
                    summary = type_value
                else:
                    name_raw = str(row.get(name_col) or "") if name_col else ""
                    if kw_upper in name_raw.upper():
                        hit = "Tag"
                        summary = name_raw
            else:
                name_raw = str(row.get(name_col) or "") if name_col else ""
                desc_raw = str(row.get(desc_col) or "") if desc_col else ""
                for tag_raw, kind in ((name_raw, "名称"), (desc_raw, "描述")):
                    if not tag_raw or not tag_raw.strip().startswith("LOC_"):
                        continue
                    resolved = resolve_loc(loc_conn, tag_raw)
                    if resolved != tag_raw and kw in resolved:
                        hit = kind
                        summary = resolved
                        break
            if hit:
                name = _object_display_name(meta, row, loc_conn)
                results.append({
                    "category": key,
                    "label": meta["label"],
                    "name": name,
                    "type": type_value,
                    "hit": hit,
                    "summary": summary or name,
                })
    return results[:limit]


# ── 通道②：能力层搜索 ─────────────────────────────────────────
_MODIFIER_TABLES = (
    ("Modifiers", "ModifierId"),
    ("ModifierArguments", "ModifierId"),
    ("ModifierStrings", "ModifierId"),
)
_CONDITION_TABLES = (
    ("Requirements", "RequirementId"),
    ("RequirementArguments", "RequirementId"),
)
_BINDING_TABLES: list[tuple[str, str, str]] = [
    # (绑定表, 对象列, 类型 key)
    ("TraitModifiers", "TraitType", "trait"),
    ("DistrictModifiers", "DistrictType", "district"),
    ("BuildingModifiers", "BuildingType", "building"),
    ("ImprovementModifiers", "ImprovementType", "improvement"),
    ("ProjectCompletionModifiers", "ProjectType", "project"),
    ("PolicyModifiers", "PolicyType", "policy"),
    ("GovernorModifiers", "GovernorType", "governor"),
    ("GovernorPromotionModifiers", "GovernorPromotionType", "governor_promotion"),
    ("UnitAbilityModifiers", "UnitAbilityType", "unit_ability"),
    ("UnitPromotionModifiers", "UnitPromotionType", "unit_promotion"),
    ("GreatPersonIndividualActionModifiers", "GreatPersonIndividualType", "great_person"),
    ("GreatPersonIndividualBirthModifiers", "GreatPersonIndividualType", "great_person"),
]


def search_by_modifier_keyword(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    keyword: str,
    category: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """按 Modifier/条件关键词搜索，反向找绑定对象。返回与 search_objects 同构。"""
    kw = str(keyword or "").strip()
    if not kw:
        return []
    kw_upper = kw.upper()
    hit_modifier_ids: set[str] = set()
    hit_requirement_ids: set[str] = set()
    hit_summary: dict[str, str] = {}

    for table, id_col in _MODIFIER_TABLES:
        for row in _fetch_all_row_dicts(
            game_conn,
            f"SELECT * FROM {table}",
            (),
        ):
            matched: list[str] = []
            for col, val in row.items():
                text = str(val or "")
                if kw_upper in text.upper():
                    matched.append(f"{col}={text[:40]}")
            if matched:
                mid = str(row.get(id_col) or "").strip()
                if mid:
                    hit_modifier_ids.add(mid)
                    hit_summary.setdefault(mid, " | ".join(matched[:2]))

    for table, id_col in _CONDITION_TABLES:
        for row in _fetch_all_row_dicts(game_conn, f"SELECT * FROM {table}", ()):
            matched = [
                f"{col}={str(val or '')[:40]}"
                for col, val in row.items()
                if str(val or "") and kw_upper in str(val).upper()
            ]
            if matched:
                rid = str(row.get(id_col) or "").strip()
                if rid:
                    hit_requirement_ids.add(rid)
                    hit_summary.setdefault(rid, " | ".join(matched[:2]))

    if not hit_modifier_ids and not hit_requirement_ids:
        return []

    # 条件 → 使用它的 modifier（经 RequirementSetRequirements → Modifiers）
    condition_to_modifiers: dict[str, set[str]] = {}
    if hit_requirement_ids:
        for row in _fetch_all_row_dicts(game_conn, "SELECT * FROM RequirementSetRequirements", ()):
            rid = str(row.get("RequirementId") or "").strip()
            if rid in hit_requirement_ids:
                rsid = str(row.get("RequirementSetId") or "").strip()
                for mrow in _fetch_all_row_dicts(
                    game_conn,
                    "SELECT ModifierId, SubjectRequirementSetId, OwnerRequirementSetId FROM Modifiers",
                    (),
                ):
                    if rsid in (str(mrow.get("SubjectRequirementSetId") or ""), str(mrow.get("OwnerRequirementSetId") or "")):
                        mid = str(mrow.get("ModifierId") or "").strip()
                        if mid:
                            hit_modifier_ids.add(mid)
                            hit_summary.setdefault(mid, hit_summary.get(rid, ""))

    if not hit_modifier_ids:
        return []

    # 反向：绑定表 → 对象
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for binding_table, obj_col, category_key in _BINDING_TABLES:
        if category and category_key != category:
            continue
        if binding_table == "ImprovementModifiers":
            mod_col = "ModifierID"
        else:
            mod_col = "ModifierId"
        for row in _fetch_all_row_dicts(
            game_conn,
            f"SELECT {obj_col}, {mod_col} FROM {binding_table}",
            (),
        ):
            mid = str(row.get(mod_col) or "").strip()
            if mid not in hit_modifier_ids:
                continue
            obj_type = _clean_type_value(row.get(obj_col))
            if not obj_type:
                continue
            key = (category_key, obj_type)
            if key in seen:
                continue
            seen.add(key)
            meta = OBJECT_TYPES[category_key]
            detail = _fetch_row_dict(game_conn, f"SELECT * FROM {meta['table']} WHERE {meta['type_col']} = ?", (obj_type,))
            name = _object_display_name(meta, detail or {}, loc_conn) if detail else obj_type
            results.append({
                "category": category_key,
                "label": meta["label"],
                "name": name,
                "type": obj_type,
                "hit": "能力",
                "summary": hit_summary.get(mid, mid),
            })
    return results[:limit]


# ── 通道③：效果词映射 ─────────────────────────────────────────
def effect_keyword_expansion(keyword: str) -> tuple[list[str], str]:
    """中文效果词 → 附加英文关键词列表 + 提示文本。"""
    kw = str(keyword or "").strip()
    if not kw or all(ord(ch) < 128 for ch in kw):
        return [], ""
    extra: list[str] = []
    for cn, en in EFFECT_KEYWORD_MAP.items():
        if cn in kw:
            extra.append(en)
    if not extra:
        return [], ""
    hint = "已按效果词扩展搜索：" + "、".join(f"“{kw}”→{e}" for e in extra)
    return extra, hint


def search_all(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    keyword: str,
    category: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """三通道合并。返回 {"results": [...], "hint": 提示, "expansions": [英文词]}。"""
    results = search_objects(game_conn, loc_conn, keyword, category=category, limit=limit)
    extra, hint = effect_keyword_expansion(keyword)
    extra_hits: list[dict[str, Any]] = []
    if extra:
        for en in extra:
            extra_hits.extend(
                search_by_modifier_keyword(game_conn, loc_conn, en, category=category, limit=limit)
            )
    else:
        extra_hits = search_by_modifier_keyword(game_conn, loc_conn, keyword, category=category, limit=limit)

    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for item in results + extra_hits:
        key = (item["category"], item["type"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return {"results": merged[:limit], "hint": hint, "expansions": extra}


# ── 对象详情 ───────────────────────────────────────────────────
def _list_sub_tables(conn: sqlite3.Connection, type_col: str) -> list[str]:
    """动态发现含 type_col 列的表（对象副表候选）。"""
    tables: list[str] = []
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    except sqlite3.Error:
        return []
    for (name,) in rows:
        try:
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{name}")').fetchall()]
        except sqlite3.Error:
            continue
        if type_col in cols:
            tables.append(name)
    return tables


def _row_non_empty(row: dict[str, Any]) -> dict[str, Any]:
    """过滤 NULL/空串/NO_* 值。"""
    return {
        k: v
        for k, v in row.items()
        if v is not None and str(v).strip() and not str(v).strip().startswith("NO_")
    }


def _adjacency_sources(row: dict[str, Any]) -> list[tuple[str, str | None]]:
    """识别相邻加成行的条件来源。"""
    sources: list[tuple[str, str | None]] = []
    for key in ADJACENCY_BOOLEAN_KEYS:
        val = row.get(key)
        if str(val or "").strip() == "1":
            sources.append((key, None))
    for key in ADJACENCY_VALUE_KEYS:
        val = _clean_type_value(row.get(key))
        if val:
            sources.append((key, val))
    return sources


def _resolve_source_cn(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    source_key: str,
    source_value: str | None,
) -> str:
    if source_value is None:
        return ADJACENCY_BOOLEAN_CN.get(source_key, source_key)
    table_info = _ADJACENCY_VALUE_TABLE.get(source_key)
    if not table_info:
        return source_value
    table, type_col, name_col = table_info
    row = _fetch_row_dict(game_conn, f"SELECT {name_col} FROM {table} WHERE {type_col} = ?", (source_value,))
    if not row:
        return source_value
    resolved = resolve_loc(loc_conn, row.get(name_col))
    return resolved if resolved and resolved != str(row.get(name_col) or "") else source_value


def build_adjacency_description(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    row: dict[str, Any],
) -> str:
    """自动生成相邻加成描述（参考编辑窗口同款逻辑，数值直填版）。

    格式：+2[ICON_Gold]金币 来自每2个相邻的{来源}（需要{科技}）
    """
    try:
        amount = int(row.get("YieldChange") or 0)
    except (TypeError, ValueError):
        amount = 0
    yield_type = str(row.get("YieldType") or "").strip()
    try:
        tiles = max(1, int(row.get("TilesRequired") or 1))
    except (TypeError, ValueError):
        tiles = 1

    sign = "+" if amount > 0 else "-" if amount < 0 else ""
    icon = YIELD_ICON_MAP.get(yield_type, "")
    cn = YIELD_CN_MAP.get(yield_type, yield_type)
    main = f"{sign}{abs(amount)}{icon}{cn}"

    sources = _adjacency_sources(row)
    quantifier = "每个" if tiles <= 1 else f"每{tiles}个"
    source_text = ""
    if sources:
        specials = [s for s in sources if s[0] in ("AdjacentRiver", "Self")]
        regulars = [s for s in sources if s[0] not in ("AdjacentRiver", "Self")]
        parts: list[str] = []
        for key, _value in specials:
            parts.append("位于河流" if key == "AdjacentRiver" else "来自自身")
        if regulars:
            details = [_resolve_source_cn(game_conn, loc_conn, key, value) for key, value in regulars]
            parts.append(f"来自{quantifier}相邻的{'、'.join(details)}")
        source_text = "、".join(parts)

    description = main
    if source_text:
        description = f"{description} {source_text}"

    prereq = _clean_type_value(row.get("PrereqTech")) or _clean_type_value(row.get("PrereqCivic"))
    if prereq:
        prereq_row = _fetch_row_dict(
            game_conn,
            f"SELECT Name FROM {( 'Technologies' if str(prereq).startswith('TECH_') else 'Civics' )} WHERE {'TechnologyType' if str(prereq).startswith('TECH_') else 'CivicType'} = ?",
            (prereq,),
        )
        if prereq_row:
            prereq_name = resolve_loc(loc_conn, prereq_row.get("Name")) or prereq
            description = f"{description}（需要{prereq_name}）"
    return description


def _fetch_adjacency_detail(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    yield_change_id: str,
) -> dict[str, Any]:
    row = _fetch_row_dict(
        game_conn,
        "SELECT * FROM Adjacency_YieldChanges WHERE ID = ?",
        (yield_change_id,),
    ) or {}
    sources = _adjacency_sources(row)
    desc_tag = str(row.get("Description") or "").strip()
    original = resolve_loc(loc_conn, desc_tag) if desc_tag else ""
    return {
        "id": yield_change_id,
        "description": build_adjacency_description(game_conn, loc_conn, row),
        "original_description": original,
        "yield_type": str(row.get("YieldType") or ""),
        "yield_change": row.get("YieldChange"),
        "tiles_required": row.get("TilesRequired"),
        "sources": [
            {"key": key, "value": value, "cn": _resolve_source_cn(game_conn, loc_conn, key, value)}
            for key, value in sources
        ],
        "prereq": _clean_type_value(row.get("PrereqTech")) or _clean_type_value(row.get("PrereqCivic")),
        "raw": _row_non_empty(row),
    }


def _fetch_sub_tables(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    meta: dict[str, Any],
    type_value: str,
) -> list[dict[str, Any]]:
    """副表（含相邻加成专门处理）。"""
    type_col = meta["type_col"]
    main_table = meta["table"]
    sub_tables: list[dict[str, Any]] = []
    for table in _list_sub_tables(game_conn, type_col):
        if table == main_table:
            continue
        rows = _fetch_all_row_dicts(game_conn, f"SELECT * FROM {table} WHERE {type_col} = ?", (type_value,))
        if not rows:
            continue
        if table in ("District_Adjacencies", "Improvement_Adjacencies"):
            entries = []
            for r in rows:
                yid = _clean_type_value(r.get("YieldChangeId"))
                if not yid:
                    continue
                entries.append(_fetch_adjacency_detail(game_conn, loc_conn, yid))
            if entries:
                sub_tables.append({"table": table, "kind": "adjacency", "rows": entries})
        else:
            sub_tables.append({"table": table, "kind": "plain", "rows": [_row_non_empty(r) for r in rows[:50]]})
    return sub_tables


# ── Modifier 树（嵌套展开）────────────────────────────────────
_ATTACH_RE = re.compile(r"ATTACH_MODIFIER")
_GRANT_ABILITY_RE = re.compile(r"GRANT_ABILITY")
MAX_NEST_DEPTH = 8


def _expand_modifier(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    modifier_id: str,
    visited: set[str],
    depth: int,
) -> Optional[dict[str, Any]]:
    if depth > MAX_NEST_DEPTH or modifier_id in visited:
        return None
    visited.add(modifier_id)

    mod_row = _fetch_row_dict(game_conn, "SELECT * FROM Modifiers WHERE ModifierId = ?", (modifier_id,))
    if not mod_row:
        return None
    modifier_type = str(mod_row.get("ModifierType") or "").strip()
    dyn = _fetch_row_dict(game_conn, "SELECT * FROM DynamicModifiers WHERE ModifierType = ?", (modifier_type,))
    effect_type = str(dyn.get("EffectType") or "") if dyn else ""
    collection_type = str(dyn.get("CollectionType") or "") if dyn else ""

    args = [
        {"name": str(r.get("Name") or ""), "value": r.get("Value")}
        for r in _fetch_all_row_dicts(
            game_conn, "SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (modifier_id,)
        )
        if str(r.get("Name") or "")
    ]

    reqsets: list[dict[str, Any]] = []
    for role in ("SubjectRequirementSetId", "OwnerRequirementSetId"):
        rsid = str(mod_row.get(role) or "").strip()
        if not rsid:
            continue
        reqsets.append(_expand_reqset(game_conn, loc_conn, role, rsid))

    strings = [
        {"context": str(r.get("Context") or ""), "text": r.get("Text")}
        for r in _fetch_all_row_dicts(
            game_conn, "SELECT Context, Text FROM ModifierStrings WHERE ModifierId = ?", (modifier_id,)
        )
    ]

    node: dict[str, Any] = {
        "modifier_id": modifier_id,
        "modifier_type": modifier_type,
        "effect_type": effect_type,
        "collection_type": collection_type,
        "run_once": mod_row.get("RunOnce"),
        "permanent": mod_row.get("Permanent"),
        "args": args,
        "reqsets": reqsets,
        "strings": strings,
        "nested": [],
        "nested_kind": None,
    }

    # ATTACH：参数 ModifierId → 被挂载者
    is_attach = bool(_ATTACH_RE.search(modifier_type)) or effect_type == "EFFECT_ATTACH_MODIFIER"
    for arg in args:
        if arg["name"] == "ModifierId" and arg["value"]:
            target = str(arg["value"]).strip()
            if target and is_attach:
                child = _expand_modifier(game_conn, loc_conn, target, visited, depth + 1)
                if child:
                    node["nested"].append(child)
                    node["nested_kind"] = "attach"

    # GRANT_ABILITY：AbilityType → UnitAbilities → UnitAbilityModifiers
    is_grant = bool(_GRANT_ABILITY_RE.search(modifier_type)) or effect_type == "EFFECT_GRANT_ABILITY"
    for arg in args:
        if arg["name"] == "AbilityType" and arg["value"]:
            ability_type = str(arg["value"]).strip()
            if not ability_type:
                continue
            ability_row = _fetch_row_dict(
                game_conn, "SELECT * FROM UnitAbilities WHERE UnitAbilityType = ?", (ability_type,)
            )
            ability_cn = ""
            if ability_row:
                ability_cn = resolve_loc(loc_conn, ability_row.get("Name"))
            for br in _fetch_all_row_dicts(
                game_conn, "SELECT ModifierId FROM UnitAbilityModifiers WHERE UnitAbilityType = ?", (ability_type,)
            ):
                child = _expand_modifier(game_conn, loc_conn, str(br.get("ModifierId") or ""), visited, depth + 1)
                if child:
                    node["nested"].append(child)
            if node["nested"]:
                node["nested_kind"] = "ability"
                node["ability_type"] = ability_type
                node["ability_name"] = ability_cn or ability_type
    return node


def _expand_reqset(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    role: str,
    reqset_id: str,
) -> dict[str, Any]:
    rs_row = _fetch_row_dict(
        game_conn, "SELECT * FROM RequirementSets WHERE RequirementSetId = ?", (reqset_id,)
    )
    requirements: list[dict[str, Any]] = []
    for rr in _fetch_all_row_dicts(
        game_conn,
        "SELECT * FROM RequirementSetRequirements WHERE RequirementSetId = ?",
        (reqset_id,),
    ):
        rid = str(rr.get("RequirementId") or "").strip()
        if not rid:
            continue
        if rid.startswith("REQSET_"):
            # 嵌套条件集
            requirements.append({
                "requirement_id": rid,
                "requirement_type": "REQSET（嵌套）",
                "inverse": 0,
                "args": [],
                "nested_reqset": _expand_reqset(game_conn, loc_conn, role, rid),
            })
            continue
        req_row = _fetch_row_dict(game_conn, "SELECT * FROM Requirements WHERE RequirementId = ?", (rid,))
        if not req_row:
            continue
        req_args = [
            {"name": str(r.get("Name") or ""), "value": r.get("Value")}
            for r in _fetch_all_row_dicts(
                game_conn, "SELECT Name, Value FROM RequirementArguments WHERE RequirementId = ?", (rid,)
            )
            if str(r.get("Name") or "")
        ]
        requirements.append({
            "requirement_id": rid,
            "requirement_type": str(req_row.get("RequirementType") or ""),
            "inverse": req_row.get("Inverse"),
            "triggered": req_row.get("Triggered"),
            "args": req_args,
            "nested_reqset": None,
        })
    return {
        "role": "Subject" if role.startswith("Subject") else "Owner",
        "id": reqset_id,
        "type": str(rs_row.get("RequirementSetType") or "") if rs_row else "",
        "requirements": requirements,
    }


def _collect_binding_modifier_ids(
    game_conn: sqlite3.Connection,
    meta: dict[str, Any],
    type_value: str,
) -> list[tuple[str, str]]:
    """返回 [(来源标签, ModifierId), ...]（按绑定源）。"""
    out: list[tuple[str, str]] = []
    for source in meta.get("binding_sources", []):
        kind = source["kind"]
        label = str(source.get("label") or kind)
        try:
            if kind == "direct":
                rows = _fetch_all_row_dicts(
                    game_conn,
                    f"SELECT {source['mod_col']} FROM {source['table']} WHERE {source['obj_col']} = ?",
                    (type_value,),
                )
                for r in rows:
                    mid = str(r.get(source["mod_col"]) or "").strip()
                    if mid:
                        out.append((label, mid))
            elif kind == "via_trait":
                trait_type = _clean_type_value(
                    _fetch_row_dict(
                        game_conn, f"SELECT {source['trait_col']} FROM {meta['table']} WHERE {meta['type_col']} = ?",
                        (type_value,),
                    ).get(source["trait_col"])
                    if _fetch_row_dict(
                        game_conn, f"SELECT {source['trait_col']} FROM {meta['table']} WHERE {meta['type_col']} = ?",
                        (type_value,),
                    )
                    else None
                )
                if trait_type:
                    label = f"{source.get('label', 'TraitType→TraitModifiers')}（{trait_type}）"
                    for r in _fetch_all_row_dicts(
                        game_conn, "SELECT ModifierId FROM TraitModifiers WHERE TraitType = ?", (trait_type,)
                    ):
                        mid = str(r.get("ModifierId") or "").strip()
                        if mid:
                            out.append((label, mid))
            elif kind == "via_table":
                for r in _fetch_all_row_dicts(
                    game_conn,
                    f"SELECT {source['trait_col']} FROM {source['via_table']} WHERE {source['via_obj_col']} = ?",
                    (type_value,),
                ):
                    trait_type = _clean_type_value(r.get(source["trait_col"]))
                    if not trait_type:
                        continue
                    trait_row = _fetch_row_dict(game_conn, "SELECT Name FROM Traits WHERE TraitType = ?", (trait_type,))
                    trait_cn = resolve_loc(loc_conn, trait_row.get("Name")) if trait_row else trait_type
                    label = f"{source.get('label', 'TraitModifiers')}（{trait_cn}）"
                    for mr in _fetch_all_row_dicts(
                        game_conn, "SELECT ModifierId FROM TraitModifiers WHERE TraitType = ?", (trait_type,)
                    ):
                        mid = str(mr.get("ModifierId") or "").strip()
                        if mid:
                            out.append((label, mid))
            elif kind == "governor_promotion":
                for r in _fetch_all_row_dicts(
                    game_conn, "SELECT GovernorPromotionType FROM GovernorPromotions WHERE GovernorType = ?",
                    (type_value,),
                ):
                    gp_type = _clean_type_value(r.get("GovernorPromotionType"))
                    if not gp_type:
                        continue
                    for mr in _fetch_all_row_dicts(
                        game_conn, "SELECT ModifierId FROM GovernorPromotionModifiers WHERE GovernorPromotionType = ?",
                        (gp_type,),
                    ):
                        mid = str(mr.get("ModifierId") or "").strip()
                        if mid:
                            out.append((f"GovernorPromotions（{gp_type}）", mid))
            elif kind == "gp_action":
                for mr in _fetch_all_row_dicts(
                    game_conn,
                    "SELECT ModifierId FROM GreatPersonIndividualActionModifiers WHERE GreatPersonIndividualType = ?",
                    (type_value,),
                ):
                    mid = str(mr.get("ModifierId") or "").strip()
                    if mid:
                        out.append((label, mid))
            elif kind == "gp_birth":
                for mr in _fetch_all_row_dicts(
                    game_conn,
                    "SELECT ModifierId FROM GreatPersonIndividualBirthModifiers WHERE GreatPersonIndividualType = ?",
                    (type_value,),
                ):
                    mid = str(mr.get("ModifierId") or "").strip()
                    if mid:
                        out.append((label, mid))
        except sqlite3.Error:
            continue
    return out


def fetch_object_detail(
    game_conn: sqlite3.Connection,
    loc_conn: Optional[sqlite3.Connection],
    category: str,
    type_value: str,
) -> Optional[dict[str, Any]]:
    """对象详情：主表（仅非空列）+ 副表 + 能力树（按来源分组）。"""
    meta = OBJECT_TYPES.get(category)
    if not meta:
        return None
    main_row = _fetch_row_dict(
        game_conn, f"SELECT * FROM {meta['table']} WHERE {meta['type_col']} = ?", (type_value,)
    )
    if not main_row:
        return None

    name = _object_display_name(meta, main_row, loc_conn)

    main_values = _row_non_empty(main_row)
    # 主表 LOC tag 值解析为中文（如 Name/Description）
    if loc_conn is not None:
        for key, value in list(main_values.items()):
            if isinstance(value, str) and value.strip().startswith("LOC_"):
                resolved = resolve_loc(loc_conn, value)
                if resolved != value.strip():
                    main_values[key] = resolved

    detail: dict[str, Any] = {
        "category": category,
        "label": meta["label"],
        "type": type_value,
        "name": name,
        "main": {
            "table": meta["table"],
            "values": main_values,
        },
        "sub_tables": _fetch_sub_tables(game_conn, loc_conn, meta, type_value),
        "binders": [],
        "modifier_groups": [],
    }

    # 特质挂载者（trait 类型显示"被谁使用"）
    if meta.get("show_binders"):
        binders: list[str] = []
        for table, obj_col, label in (
            ("CivilizationTraits", "CivilizationType", "文明"),
            ("LeaderTraits", "LeaderType", "领袖"),
        ):
            for r in _fetch_all_row_dicts(game_conn, f"SELECT {obj_col} FROM {table} WHERE TraitType = ?", (type_value,)):
                obj_type = _clean_type_value(r.get(obj_col))
                if not obj_type:
                    continue
                if label == "文明":
                    b_row = _fetch_row_dict(game_conn, "SELECT Name FROM Civilizations WHERE CivilizationType = ?", (obj_type,))
                else:
                    b_row = _fetch_row_dict(game_conn, "SELECT Name FROM Leaders WHERE LeaderType = ?", (obj_type,))
                cn = resolve_loc(loc_conn, b_row.get("Name")) if b_row else obj_type
                binders.append(f"{label}：{cn}（{obj_type}）")
        detail["binders"] = binders

    # 能力树
    bindings = _collect_binding_modifier_ids(game_conn, meta, type_value)
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for label, mid in bindings:
        if label not in grouped:
            grouped[label] = []
            order.append(label)
        grouped[label].append(mid)
    visited: set[str] = set()
    for label in order:
        nodes = []
        for mid in grouped[label]:
            node = _expand_modifier(game_conn, loc_conn, mid, visited, 0)
            if node:
                nodes.append(node)
        if nodes:
            detail["modifier_groups"].append({"source": label, "modifiers": nodes})
    return detail
