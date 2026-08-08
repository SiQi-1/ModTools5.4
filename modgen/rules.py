"""命名与结构规则（纯函数，与 ModTools GUI 的规则保持一致）。

命名规则来源：
- ModTools_5_4/ui/pages/group_workspace.py:_build_entity_type
- ModTools_5_4/ui/pages/great_people_editor.py:_build_type
- 知识库 skills/06-naming.md（核对一致）
"""
from __future__ import annotations

import re
from typing import Any

# 各分类 Type 命名参数（head / midfix 与 GUI 的 build_*_main_schema 一致）
SECTION_TYPE_RULES: dict[str, dict[str, str]] = {
    "文明": {"head": "CIVILIZATION", "midfix": "C"},
    "领袖": {"head": "LEADER", "midfix": "L"},
    "区域": {"head": "DISTRICT", "midfix": "D"},
    "建筑": {"head": "BUILDING", "midfix": "B"},
    "单位": {"head": "UNIT", "midfix": "U"},
    "改良设施": {"head": "IMPROVEMENT", "midfix": "I"},
    "总督": {"head": "GOVERNOR", "midfix": "G"},
    "伟人": {"head": "GREAT_PERSON_CLASS", "midfix": "G"},
    "政策卡": {"head": "POLICY", "midfix": "P"},
    "项目": {"head": "PROJECT", "midfix": "P"},
    "信仰": {"head": "BELIEF", "midfix": "B"},
    "议程": {"head": "AGENDA", "midfix": "A"},
    "单位晋升": {"head": "PROMOTION_CLASS", "midfix": "P"},
}

# 条目主表类型键（entry 里主表的 type_key）
SECTION_TYPE_KEYS: dict[str, str] = {
    "文明": "type",
    "领袖": "type",
    "区域": "type",
    "建筑": "type",
    "单位": "type",
    "改良设施": "type",
    "总督": "type",
    "伟人": "type",
    "政策卡": "type",
    "项目": "type",
    "信仰": "type",
    "议程": "type",
    "单位晋升": "type",
}

# 各分类主表 type 后缀（用于 table_data 里的类型键，如 Districts 表用 DistrictType 列）
SECTION_DB_TYPE_KEY: dict[str, str] = {
    "文明": "CivilizationType",
    "领袖": "LeaderType",
    "区域": "DistrictType",
    "建筑": "BuildingType",
    "单位": "UnitType",
    "改良设施": "ImprovementType",
    "总督": "GovernorType",
    "伟人": "GreatPersonClassType",
    "政策卡": "PolicyType",
    "项目": "ProjectType",
    "信仰": "BeliefType",
    "议程": "AgendaType",
    "单位晋升": "PromotionClassType",
}

# 各分类条目对应的主表名（用于 table_name / subtables 约定）
SECTION_TABLE_NAME: dict[str, str] = {
    "文明": "Civilizations",
    "领袖": "Leaders",
    "区域": "Districts",
    "建筑": "Buildings",
    "单位": "Units",
    "改良设施": "Improvements",
    "总督": "Governors",
    "伟人": "GreatPersonClasses",
    "政策卡": "Policies",
    "项目": "Projects",
    "信仰": "Beliefs",
    "议程": "Agendas",
    "单位晋升": "UnitPromotionClasses",
}

# 有效分类（与 CIV_SECTION_ORDER 的内容分类一致，不含直接工作区）
CONTENT_SECTIONS: tuple[str, ...] = (
    "文明", "领袖", "区域", "建筑", "单位", "单位晋升", "改良设施",
    "总督", "伟人", "政策卡", "项目", "信仰", "议程",
)

# 各分类条目必填基础键（总督用 code 生成 Type；议程/伟人/晋升树无顶层 abbr）
SECTION_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "文明": ("abbr", "name"),
    "领袖": ("abbr", "name"),
    "区域": ("abbr", "name"),
    "建筑": ("abbr", "name"),
    "单位": ("abbr", "name"),
    "改良设施": ("abbr", "name"),
    "政策卡": ("abbr", "name"),
    "项目": ("abbr", "name"),
    "信仰": ("abbr", "name"),
    "总督": ("code", "name"),
    "伟人": ("name",),
    "议程": ("name",),
    "单位晋升": ("name", "type"),
}


def sanitize_short_token(value: object | None) -> str:
    """清洗简称：仅保留字母数字下划线并转大写（与 GUI 一致）。"""
    raw = str(value or "").strip()
    if not raw:
        return ""
    return re.sub(r"[^A-Za-z0-9_]", "", raw).upper()


def build_entity_type(
    prefix: str,
    infix: int,
    *,
    head: str,
    midfix_code: str,
    short_name: object | None,
) -> str:
    """生成完整 Type：{HEAD}_{前缀}_{中缀代码}{中缀:04d}_{简称}（与 GUI 一致）。"""
    prefix_text = str(prefix or "").strip().upper()
    try:
        infix_int = max(0, int(infix))
    except (TypeError, ValueError):
        infix_int = 0
    short = sanitize_short_token(short_name)

    parts = [head]
    if prefix_text:
        parts.append(prefix_text)
    if infix_int > 0:
        parts.append(f"{midfix_code}{infix_int:04d}")
    if short:
        parts.append(short)
    return "_".join(parts)


def loc_name_tag(entity_type: str) -> str:
    """实体 Name 的 LOC tag 约定。"""
    return f"LOC_{entity_type}_NAME"


def loc_description_tag(entity_type: str) -> str:
    """实体 Description 的 LOC tag 约定。"""
    return f"LOC_{entity_type}_DESCRIPTION"


def loc_tag_for(entity_type: str, suffix: str) -> str:
    """按约定生成 LOC tag：LOC_{TYPE}_{SUFFIX}。"""
    return f"LOC_{entity_type}_{suffix}"


def entry_display_name(entry: dict[str, Any]) -> str:
    """条目的显示名（name 优先，回退 Name/type）。"""
    for key in ("name", "Name"):
        text = str(entry.get(key) or "").strip()
        if text:
            return text
    return str(entry.get("type") or "未命名").strip()


def entry_type(entry: dict[str, Any]) -> str:
    """条目主表类型（type 键）。"""
    return str(entry.get("type") or "").strip()


def requires_type_key(section: str) -> bool:
    """该分类的条目是否必须携带主表类型键。"""
    return section not in {"单位晋升"}
