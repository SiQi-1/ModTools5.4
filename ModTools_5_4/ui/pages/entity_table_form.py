"""通用主表编辑器（Schema 驱动）。

用于将 SQL 主表定义转为可配置 UI：
- 基础信息区（含简称/Type/中文名称描述/联动参数）
- 数值区（三列）
- 布尔区（三列）

说明：
- 字段映射优先使用 TEMPLATE_MAPPING 指定的 ui_widget_kit 模板。
- 未命中映射的 TEXT 字段默认使用英文输入框。
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import sqlite3
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..ui_widget_kit import BaseTemplateWidget, IconTokenTextEdit, NewlineTokenTextEdit, build_template_widget
from ..ui_widget_kit import AdjacencyAutoContext, AdjacencyEditorWidget
from ...app.settings_store import load_settings
from ...db.interface import resolve_chinese_text_or_unknown
from ...db.paths import DEFAULT_GAME_DB


BASIC_WITH_ICON_ROWS_LIMIT = 8
BASIC_ROWS_PER_COLUMN_LIMIT = 8
LOGGER = logging.getLogger(__name__)


# 必填字段规则（便于后续增减）：
# - required: 是否必填
# - default: 为空时可自动填充的默认值（若无则为 None/缺省）
#
# 注意：对于“无合适默认值”的必填字段，校验与弹窗在生成阶段处理。
REQUIRED_MAIN_TABLE_FIELD_RULES: dict[str, dict[str, dict[str, object]]] = {
    "Districts": {
        "MilitaryDomain": {"required": True, "default": "NO_DOMAIN"},
    },
    "Units": {
        "FormationClass": {"required": True},
    }
}

# 对改良设施主表的必填规则：PlunderType 必须非空，默认 NO_PLUNDER
REQUIRED_MAIN_TABLE_FIELD_RULES.setdefault("Improvements", {})
REQUIRED_MAIN_TABLE_FIELD_RULES["Improvements"]["PlunderType"] = {"required": True, "default": "NO_PLUNDER"}


def _apply_required_rules(table_name: str, fields: list[TableFieldSpec]) -> None:
    rules = REQUIRED_MAIN_TABLE_FIELD_RULES.get(str(table_name or ""), {})
    if not rules:
        return
    for field in fields:
        rule = rules.get(field.key)
        if not isinstance(rule, dict):
            continue
        if bool(rule.get("required")):
            field.required = True
        if field.default in (None, "") and "default" in rule:
            field.default = rule.get("default")


BUILDING_TABLE_EXPLANATIONS: dict[str, dict[str, object]] = {
    "Buildings_XP2": {
        "table": "建筑扩展参数（供电、防灾、海平面与功能开关）。",
        "params": {
            "BuildingType": "当前建筑完整 Type",
            "RequiredPower": "运行所需电力",
            "ResourceTypeConvertedToPower": "可转换为电力的战略资源",
            "PreventsFloods": "是否防洪",
            "PreventsDrought": "是否防旱",
            "BlocksCoastalFlooding": "是否阻挡海岸洪水",
            "CostMultiplierPerTile": "每地块成本倍率",
            "CostMultiplierPerSeaLevel": "每级海平面成本倍率",
            "Bridge": "是否桥梁",
            "CanalWonder": "是否运河奇观",
            "EntertainmentBonusWithPower": "通电后额外宜居度",
            "NuclearReactor": "是否核反应堆建筑",
            "Pillage": "是否可被劫掠",
        },
    },
    "BuildingReplaces": {
        "table": "文明专属建筑替代关系。",
        "params": {
            "CivUniqueBuildingType": "文明专属建筑 Type",
            "ReplacesBuildingType": "被替代的基础建筑（无Trait无奇观）",
        },
    },
    "BuildingPrereqs": {
        "table": "额外前置建筑链。",
        "params": {
            "Building": "当前建筑 Type",
            "PrereqBuilding": "前置建筑",
        },
    },
    "Building_CitizenYieldChanges": {
        "table": "市民在该建筑工作时获得的产出修正。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "YieldType": "产出类型",
            "YieldChange": "产出改变量",
        },
    },
    "Building_GreatPersonPoints": {
        "table": "每回合伟人点。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "GreatPersonClassType": "伟人类别",
            "PointsPerTurn": "每回合点数",
        },
    },
    "Building_RequiredFeatures": {
        "table": "建造所需地貌限制。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "FeatureType": "必须满足的地貌",
        },
    },
    "Building_TourismBombs_XP2": {
        "table": "旅游业绩炸弹数值设置。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "TourismBombValue": "旅游业绩炸弹强度",
        },
    },
    "Building_ResourceCosts": {
        "table": "资源消耗。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "ResourceType": "资源类型（战略资源）",
            "StartProductionCost": "初始生产消耗",
            "PerTurnMaintenanceCost": "每回合维护消耗",
        },
    },
    "Building_ValidFeatures": {
        "table": "可放置地貌白名单。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "FeatureType": "允许放置的地貌",
        },
    },
    "Building_ValidTerrains": {
        "table": "可放置地形白名单。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "TerrainType": "允许放置的地形",
        },
    },
    "Building_YieldChanges": {
        "table": "建筑基础产出。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "YieldType": "产出类型",
            "YieldChange": "产出值",
        },
    },
    "Building_YieldChangesBonusWithPower": {
        "table": "通电后额外产出。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "YieldType": "通电产出类型",
            "YieldChange": "通电产出增量",
        },
    },
    "Building_YieldDistrictCopies": {
        "table": "区域相邻加成复制/替换映射。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "OldYieldType": "原产出类型",
            "NewYieldType": "替换后产出类型",
        },
    },
    "Building_YieldsPerEra": {
        "table": "随时代增长的产出。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "YieldType": "时代成长产出类型",
            "YieldChange": "每时代增加值",
        },
    },
    "BuildingConditions": {
        "table": "建筑条件：由效果解锁开关。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "UnlocksFromEffect": "是否通过效果解锁",
        },
    },
    "Building_BuildChargeProductions": {
        "table": "建造次数转生产比例。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "UnitType": "单位类型",
            "PercentProductionPerCharge": "每次建造转化百分比",
        },
    },
    "Building_GreatWorks": {
        "table": "巨作槽位。",
        "params": {
            "BuildingType": "当前建筑 Type",
            "GreatWorkSlotType": "巨作槽位类型",
            "NumSlots": "槽位数量",
            "ThemingUniquePerson": "主题化要求不同作者",
            "ThemingSameObjectType": "主题化要求相同巨作类型",
            "ThemingUniqueCivs": "主题化要求不同文明",
            "ThemingSameEras": "主题化要求同一时代",
            "ThemingYieldMultiplier": "主题化产出倍率",
            "ThemingTourismMultiplier": "主题化旅游倍率",
            "NonUniquePersonYield": "非唯一作者产出补偿",
            "NonUniquePersonTourism": "非唯一作者旅游补偿",
            "ThemingBonusDescription": "主题化描述文本",
        },
    },
}


POLICY_TABLE_EXPLANATIONS: dict[str, dict[str, object]] = {
    "Policies": {
        "table": "政策卡主表。",
        "params": {
            "PolicyType": "政策卡完整 Type",
            "Name": "政策卡名称",
            "Description": "政策卡描述",
            "PrereqCivic": "前置市政",
            "PrereqTech": "前置科技",
            "GovernmentSlotType": "政策槽位类型",
            "RequiresGovernmentUnlock": "是否要求通过政体解锁",
            "ExplicitUnlock": "是否显式解锁",
        },
    },
    "Policies_XP1": {
        "table": "政策卡时代/黄金黑暗时代限制。",
        "params": {
            "PolicyType": "政策卡完整 Type",
            "MinimumGameEra": "最早可用时代",
            "MaximumGameEra": "最晚可用时代",
            "RequiresDarkAge": "仅黑暗时代可用",
            "RequiresGoldenAge": "仅黄金时代可用",
        },
    },
    "Policy_GovernmentExclusives_XP2": {
        "table": "政策卡政体独占限制。",
        "params": {
            "PolicyType": "政策卡完整 Type",
            "GovernmentType": "限定政体",
        },
    },
}


PROJECT_TABLE_EXPLANATIONS: dict[str, dict[str, object]] = {
    "Projects": {
        "table": "项目主表。",
        "params": {
            "ProjectType": "项目完整 Type",
            "Name": "项目名称",
            "ShortName": "项目短名",
            "Description": "项目描述",
            "PopupText": "弹窗文本",
            "Cost": "基础成本",
            "CostProgressionModel": "成本递增模型",
            "CostProgressionParam1": "成本递增参数",
            "PrereqTech": "前置科技",
            "PrereqCivic": "前置市政",
            "PrereqDistrict": "前置区域",
            "RequiredBuilding": "需要建筑",
            "VisualBuildingType": "展示建筑",
            "SpaceRace": "是否太空竞赛项目",
            "OuterDefenseRepair": "是否修复外城防",
            "MaxPlayerInstances": "每玩家最大完成数",
            "AmenitiesWhileActive": "进行中提供的宜居度",
            "PrereqResource": "前置资源",
            "AdvisorType": "顾问类型",
            "WMD": "是否大规模杀伤相关",
            "UnlocksFromEffect": "是否通过效果解锁",
        },
    },
    "Projects_MODE": {
        "table": "项目模式扩展。PrereqImprovement 参数当前基本未使用。",
        "params": {
            "ProjectType": "当前项目 Type",
            "PrereqImprovement": "前置改良设施（未使用参数）",
            "ResourceType": "资源类型",
        },
    },
    "Projects_XP1": {
        "table": "风云变幻扩展。",
        "params": {
            "ProjectType": "当前项目 Type",
            "IdentityPerCitizenChange": "每市民忠诚度压力变化",
            "UnlocksFromEffect": "是否通过效果解锁",
        },
    },
    "Projects_XP2": {
        "table": "迭起兴衰扩展。",
        "params": {
            "ProjectType": "当前项目 Type",
            "RequiredPowerWhileActive": "进行中所需电力",
            "ReligiousPressureModifier": "宗教压力修正值",
            "UnlocksFromEffect": "是否通过效果解锁",
            "RequiredBuilding": "要求前置建筑",
            "CreateBuilding": "完成时创建建筑",
            "FullyPoweredWhileActive": "进行中是否满电",
            "MaxSimultaneousInstances": "最多同时进行数",
        },
    },
    "Project_BuildingCosts": {
        "table": "项目额外建筑消耗。",
        "params": {
            "ProjectType": "当前项目 Type",
            "ConsumedBuildingType": "消耗的建筑类型",
        },
    },
    "Project_GreatPersonPoints": {
        "table": "项目伟人点奖励。",
        "params": {
            "ProjectType": "当前项目 Type",
            "GreatPersonClassType": "伟人类别",
            "Points": "点数",
            "PointProgressionModel": "点数递增模型",
            "PointProgressionParam1": "点数递增参数",
        },
    },
    "Project_ResourceCosts": {
        "table": "项目资源消耗。",
        "params": {
            "ProjectType": "当前项目 Type",
            "ResourceType": "资源类型",
            "StartProductionCost": "初始生产消耗",
        },
    },
    "Project_YieldConversions": {
        "table": "项目产能转换。",
        "params": {
            "ProjectType": "当前项目 Type",
            "YieldType": "转换产出类型",
            "PercentOfProductionRate": "生产力转换百分比",
        },
    },
    "ProjectPrereqs": {
        "table": "项目前置项目链。",
        "params": {
            "ProjectType": "当前项目 Type",
            "PrereqProjectType": "前置项目 Type",
            "MinimumPlayerInstances": "玩家最小实例数",
        },
    },
}


BELIEF_TABLE_EXPLANATIONS: dict[str, dict[str, object]] = {
    "Beliefs": {
        "table": "信仰主表。",
        "params": {
            "BeliefType": "信仰完整 Type",
            "Name": "信仰名称",
            "Description": "信仰描述",
            "BeliefClassType": "信仰类别",
        },
    },
}


def _safe_text(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def _sanitize_english_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "", value or "")


def _first_non_empty(data: dict[str, object]) -> str:
    for value in data.values():
        text = _safe_text(value)
        if text:
            return text
    return ""


def _pick_non_empty_by_keys(data: dict[str, object], keys: list[str]) -> str:
    for key in keys:
        text = _safe_text(data.get(key))
        if text:
            return text
    return ""


def _building_param_zh(table_name: str, param: str) -> str:
    table_info = BUILDING_TABLE_EXPLANATIONS.get(table_name, {})
    params = table_info.get("params") if isinstance(table_info.get("params"), dict) else {}
    return str(params.get(param) or "")


def _policy_param_zh(table_name: str, param: str) -> str:
    table_info = POLICY_TABLE_EXPLANATIONS.get(table_name, {})
    params = table_info.get("params") if isinstance(table_info.get("params"), dict) else {}
    return str(params.get(param) or "")


def _project_param_zh(table_name: str, param: str) -> str:
    table_info = PROJECT_TABLE_EXPLANATIONS.get(table_name, {})
    params = table_info.get("params") if isinstance(table_info.get("params"), dict) else {}
    return str(params.get(param) or "")


def _belief_param_zh(table_name: str, param: str) -> str:
    table_info = BELIEF_TABLE_EXPLANATIONS.get(table_name, {})
    params = table_info.get("params") if isinstance(table_info.get("params"), dict) else {}
    return str(params.get(param) or "")


def _param_display_text(*, zh_text: str, fallback_key: str) -> str:
    zh = _safe_text(zh_text)
    return zh if zh else fallback_key


def _attach_hover_param_tooltip(widget: QWidget, param_name: str) -> None:
    if isinstance(widget, (QCheckBox, QSpinBox, QDoubleSpinBox)):
        widget.setToolTip(_safe_text(param_name))


def _normalize_checkbox_caption(widget: QWidget) -> None:
    if isinstance(widget, QCheckBox):
        widget.setText("")


def _building_table_hint(table_name: str) -> str:
    table_info = BUILDING_TABLE_EXPLANATIONS.get(table_name, {})
    table_desc = str(table_info.get("table") or "")
    # 仅保留表级别说明：逐参数中文解释会与下方参数行中文标签重复。
    return table_desc


def _policy_table_hint(table_name: str) -> str:
    table_info = POLICY_TABLE_EXPLANATIONS.get(table_name, {})
    table_desc = str(table_info.get("table") or "")
    # 仅保留表级别说明：逐参数中文解释会与下方参数行中文标签重复。
    return table_desc


def _project_table_hint(table_name: str) -> str:
    table_info = PROJECT_TABLE_EXPLANATIONS.get(table_name, {})
    table_desc = str(table_info.get("table") or "")
    # 仅保留表级别说明：逐参数中文解释会与下方参数行中文标签重复。
    return table_desc


def _belief_table_hint(table_name: str) -> str:
    table_info = BELIEF_TABLE_EXPLANATIONS.get(table_name, {})
    table_desc = str(table_info.get("table") or "")
    # 仅保留表级别说明：逐参数中文解释会与下方参数行中文标签重复。
    return table_desc


def _sql_escape(value: object | None) -> str:
    return str(value or "").replace("'", "''")


def _sql_literal(value: object | None) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".15g")
    return f"'{_sql_escape(value)}'"


def _greatwork_slot_short(slot_type: str) -> str:
    slot = _safe_text(slot_type).upper()
    if slot.startswith("GREATWORKSLOT_"):
        short = slot[len("GREATWORKSLOT_") :]
        return short or slot
    return slot


def _fit_column_widths(base_widths: list[int], available: int, preferred_min: int = 60) -> list[int]:
    if not base_widths:
        return []
    if available <= 0:
        return [1 for _ in base_widths]

    count = len(base_widths)
    adaptive_min = max(1, min(preferred_min, available // count if count > 0 else preferred_min))
    base_sum = sum(base_widths)
    if base_sum <= 0:
        avg = max(adaptive_min, available // count if count > 0 else available)
        widths = [avg for _ in base_widths]
    else:
        widths = [max(adaptive_min, int(available * width / base_sum)) for width in base_widths]

    total = sum(widths)
    if total < available:
        idx = len(widths) - 1
        remaining = available - total
        while remaining > 0 and widths:
            widths[idx] += 1
            remaining -= 1
            idx = (idx - 1) % len(widths)
        return widths

    if total > available:
        overflow = total - available
        idx = len(widths) - 1
        while overflow > 0 and widths:
            if widths[idx] > adaptive_min:
                widths[idx] -= 1
                overflow -= 1
            idx = (idx - 1) % len(widths)
            if idx == len(widths) - 1 and all(item <= adaptive_min for item in widths):
                break

    total_after = sum(widths)
    if total_after > available:
        overflow = total_after - available
        idx = len(widths) - 1
        while overflow > 0 and widths:
            if widths[idx] > 1:
                widths[idx] -= 1
                overflow -= 1
            idx = (idx - 1) % len(widths)
            if idx == len(widths) - 1 and all(item <= 1 for item in widths):
                break

    total_after = sum(widths)
    if total_after < available:
        idx = len(widths) - 1
        remaining = available - total_after
        while remaining > 0 and widths:
            widths[idx] += 1
            remaining -= 1
            idx = (idx - 1) % len(widths)

    return widths


def _active_game_db_path() -> Path:
    settings = load_settings()
    configured = _safe_text(getattr(settings, "game_db_path", ""))
    if configured and Path(configured).exists():
        return Path(configured)
    return DEFAULT_GAME_DB


def _fetch_project_rows_for_selector() -> list[tuple[str, str]]:
    db_path = _active_game_db_path()
    if not db_path.exists():
        LOGGER.warning("ProjectPrereq selector skipped: game DB not found at %s", db_path)
        return []
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as exc:
        LOGGER.warning("ProjectPrereq selector failed to open DB: %s", exc)
        return []
    try:
        rows = conn.execute(
            "SELECT ProjectType, IFNULL(Name, '') FROM Projects ORDER BY ProjectType"
        ).fetchall()
    except sqlite3.Error as exc:
        LOGGER.warning("ProjectPrereq selector query failed: %s", exc)
        rows = []
    finally:
        conn.close()

    output: list[tuple[str, str]] = []
    for project_type, name_tag in rows:
        project_text = _safe_text(project_type)
        if not project_text:
            continue
        localized = resolve_chinese_text_or_unknown(_safe_text(name_tag)) if _safe_text(name_tag) else ""
        display = localized if localized and localized != "未知" else project_text
        output.append((project_text, display))
    LOGGER.info("Loaded %d project options for ProjectPrereq selector", len(output))
    return output


def _suggest_upgrade_from_replaces(replaces_unit_type: str) -> str:
    base_type = _safe_text(replaces_unit_type)
    if not base_type:
        return ""
    db_path = _active_game_db_path()
    if not db_path.exists():
        return ""
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return ""
    try:
        row = conn.execute(
            "SELECT UpgradeUnit FROM UnitUpgrades WHERE Unit = ? LIMIT 1",
            (base_type,),
        ).fetchone()
        if not row:
            return ""
        return _safe_text(row[0])
    except sqlite3.Error:
        return ""
    finally:
        conn.close()


FIXED_UNIT_CLASS_TAGS: list[tuple[str, str]] = [
    ("CLASS_LANDCIVILIAN", "陆地平民"),
    ("CLASS_RECON", "侦察"),
    ("CLASS_BUILDER", "建造者"),
    ("CLASS_MELEE", "近战"),
    ("CLASS_RANGED", "远程"),
    ("CLASS_SIEGE", "攻城"),
    ("CLASS_HEAVY_CAVALRY", "重骑兵"),
    ("CLASS_LIGHT_CAVALRY", "轻骑兵"),
    ("CLASS_ANTI_CAVALRY", "反骑兵"),
    ("CLASS_NAVAL_MELEE", "海军近战"),
    ("CLASS_NAVAL_RANGED", "海军远程"),
    ("CLASS_NAVAL_RAIDER", "海军袭击者"),
    ("CLASS_NAVAL_CARRIER", "海军航母"),
    ("CLASS_TRADER", "商人"),
    ("CLASS_RELIGIOUS", "宗教单位"),
    ("CLASS_AIRCRAFT", "飞机"),
    ("CLASS_AIR_BOMBER", "空中轰炸机"),
    ("CLASS_AIR_FIGHTER", "空中战斗机"),
    ("CLASS_ARCHAEOLOGIST", "考古学家"),
    ("CLASS_SPY", "间谍"),
    ("CLASS_ANTI_AIR", "防空单位"),
    ("CLASS_MOBILE_RANGED", "机动远程单位"),
    ("CLASS_SUPPORT", "支援单位"),
]


def _infer_class_tag(unit_type: str) -> str:
    normalized = _sanitize_english_token(_safe_text(unit_type).upper())
    return f"CLASS_{normalized}" if normalized else ""


def _fetch_unit_typetag_candidates(excluded: set[str] | None = None) -> list[str]:
    excluded_set = {item for item in (excluded or set()) if _safe_text(item)}
    db_path = _active_game_db_path()
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute("SELECT DISTINCT Tag FROM TypeTags WHERE Type LIKE 'UNIT_%'").fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    fixed = {code for code, _ in FIXED_UNIT_CLASS_TAGS}
    output: list[str] = []
    for row in rows:
        tag = _safe_text((row[0] if row else ""))
        if not tag:
            continue
        if tag in fixed:
            continue
        if tag in excluded_set:
            continue
        output.append(tag)
    return sorted(set(output))


def _fetch_dynamic_modifier_types() -> list[str]:
    db_path = _active_game_db_path()
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute("SELECT DISTINCT ModifierType FROM DynamicModifiers").fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    items = [_safe_text((row[0] if row else "")) for row in rows]
    return sorted({item for item in items if item})


class _CompactDoubleSpinBox(QDoubleSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setDecimals(6)
        self.setSingleStep(1.0)

    def textFromValue(self, value: float) -> str:  # type: ignore[override]
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"


@dataclass(slots=True)
class TableFieldSpec:
    key: str
    label: str
    field_type: str  # text/int/real/bool/template
    section: str  # basic/number/bool
    default: object = ""
    template_key: str | None = None
    chinese_input: bool = False
    english_only: bool = False
    linked_group: str | None = None
    tokenized_multiline: bool = False
    required: bool = False


@dataclass(slots=True)
class LinkedGroupSpec:
    group_id: str
    label: str
    first_key: str
    second_key: str


@dataclass(slots=True)
class MainTableSchema:
    table_name: str
    head: str
    midfix_code: str
    abbr_key: str
    type_key: str
    name_key: str
    description_key: str
    icon_size: tuple[int, int]
    fields: list[TableFieldSpec]
    linked_groups: list[LinkedGroupSpec]
    has_images: bool = True
    portrait_suffix: str | None = None
    top_basic_visual_limit: int = BASIC_WITH_ICON_ROWS_LIMIT


class _TraitTypeToggleWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._checkbox = QCheckBox("启用TraitType")
        self._value = QLineEdit()
        self._value.setReadOnly(True)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._checkbox)
        layout.addWidget(self._value, 1)
        self.setLayout(layout)

        self._checkbox.stateChanged.connect(lambda _v: self.changed.emit())

    def set_trait_type(self, value: str) -> None:
        self._value.setText(_safe_text(value))

    def set_checked(self, checked: bool) -> None:
        self._checkbox.setChecked(bool(checked))

    def is_checked(self) -> bool:
        return self._checkbox.isChecked()


DISTRICT_TEMPLATE_MAPPING: dict[str, str] = {
    "PrereqTech": "technology_search",
    "PrereqCivic": "civic_search",
    "PlunderType": "plunder_type",
    "MilitaryDomain": "domain",
    "CostProgressionModel": "cost_progression",
    "AdvisorType": "advisor_type",
}


BUILDING_TEMPLATE_MAPPING: dict[str, str] = {
    "PrereqTech": "technology_search",
    "PrereqCivic": "civic_search",
    "PrereqDistrict": "district_search",
    "AdjacentDistrict": "district_search",
    "AdjacentResource": "resource_search",
    "PurchaseYield": "yield",
    "ObsoleteEra": "era",
    "AdvisorType": "advisor_type",
    "AdjacentImprovement": "improvement_search",
    "CityAdjacentTerrain": "terrain",
}


UNIT_TEMPLATE_MAPPING: dict[str, str] = {
    "Domain": "domain",
    "FormationClass": "formation_class",
    "CostProgressionModel": "cost_progression",
    "PromotionClass": "unit_promotion_class",
    "PrereqTech": "technology_search",
    "PrereqCivic": "civic_search",
    "PrereqDistrict": "district_search",
    "StrategicResource": "resource_strategic",
    "PurchaseYield": "yield",
    "ObsoleteTech": "technology_search",
    "ObsoleteCivic": "civic_search",
    "MandatoryObsoleteTech": "technology_search",
    "MandatoryObsoleteCivic": "civic_search",
    "AdvisorType": "advisor_type",
}


IMPROVEMENT_TEMPLATE_MAPPING: dict[str, str] = {
    "PrereqTech": "technology_search",
    "PrereqCivic": "civic_search",
    "PlunderType": "plunder_type",
    "YieldFromAppeal": "yield",
    "Domain": "domain",
    "ImprovementOnRemove": "improvement_search",
}


POLICY_TEMPLATE_MAPPING: dict[str, str] = {
    "PrereqTech": "technology_search",
    "PrereqCivic": "civic_search",
    "GovernmentSlotType": "government_slot",
}


PROJECT_TEMPLATE_MAPPING: dict[str, str] = {
    "CostProgressionModel": "cost_progression",
    "PrereqTech": "technology_search",
    "PrereqCivic": "civic_search",
    "PrereqDistrict": "district_search",
    "RequiredBuilding": "building_search_no_trait",
    "VisualBuildingType": "building_search_all",
    "PrereqResource": "resource_search",
    "AdvisorType": "advisor_type",
}


BELIEF_TEMPLATE_MAPPING: dict[str, str] = {
    "BeliefClassType": "belief_class",
}

def build_agendas_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "议程名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "议程描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
    ]

    return MainTableSchema(
        table_name="Agendas",
        head="AGENDA",
        midfix_code="A",
        abbr_key="abbr",
        type_key="AgendaType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=[],
        has_images=False,
        top_basic_visual_limit=16,
    )


def build_districts_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "区域名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "区域描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("PrereqTech", "前置科技", "template", "basic", "", template_key=DISTRICT_TEMPLATE_MAPPING["PrereqTech"]),
        TableFieldSpec("PrereqCivic", "前置市政", "template", "basic", "", template_key=DISTRICT_TEMPLATE_MAPPING["PrereqCivic"]),
        TableFieldSpec("TraitType", "TraitType", "trait_toggle", "basic", 0),
        TableFieldSpec("AdvisorType", "顾问类型", "template", "basic", "", template_key=DISTRICT_TEMPLATE_MAPPING["AdvisorType"]),

        TableFieldSpec("PlunderType", "掠夺类型", "template", "basic", "NO_PLUNDER", template_key=DISTRICT_TEMPLATE_MAPPING["PlunderType"], linked_group="plunder"),
        TableFieldSpec("PlunderAmount", "掠夺数值", "int", "basic", 0, linked_group="plunder"),
        TableFieldSpec("CostProgressionModel", "成本递增模型", "template", "basic", "NO_COST_PROGRESSION", template_key=DISTRICT_TEMPLATE_MAPPING["CostProgressionModel"], linked_group="cost_progression"),
        TableFieldSpec("CostProgressionParam1", "成本递增参数", "int", "basic", 0, linked_group="cost_progression"),
        TableFieldSpec("MilitaryDomain", "军事领域", "template", "basic", "NO_DOMAIN", template_key=DISTRICT_TEMPLATE_MAPPING["MilitaryDomain"]),

        TableFieldSpec("Cost", "建造成本", "int", "number", 1),
        TableFieldSpec("HitPoints", "耐久值", "int", "number", 0),
        TableFieldSpec("Appeal", "魅力", "int", "number", 0),
        TableFieldSpec("Housing", "住房", "int", "number", 0),
        TableFieldSpec("Entertainment", "宜居度", "int", "number", 0),
        TableFieldSpec("Maintenance", "维护费", "int", "number", 0),
        TableFieldSpec("AirSlots", "空军槽位", "int", "number", 0),
        TableFieldSpec("CitizenSlots", "市民槽位", "int", "number", 0),
        TableFieldSpec("TravelTime", "修复回合", "int", "number", -1),
        TableFieldSpec("CityStrengthModifier", "城市防御修正", "int", "number", 0),
        TableFieldSpec("MaxPerPlayer", "每玩家上限", "real", "number", -1.0),

        TableFieldSpec("Coast", "允许沿海", "bool", "bool", 0),
        TableFieldSpec("RequiresPlacement", "需要地块放置", "bool", "bool", 0),
        TableFieldSpec("RequiresPopulation", "需要人口", "bool", "bool", 1),
        TableFieldSpec("NoAdjacentCity", "不可邻接城市中心", "bool", "bool", 0),
        TableFieldSpec("CityCenter", "作为城市中心", "bool", "bool", 0),
        TableFieldSpec("Aqueduct", "视为引水渠", "bool", "bool", 0),
        TableFieldSpec("InternalOnly", "仅内部可建", "bool", "bool", 0),
        TableFieldSpec("ZOC", "提供控制区", "bool", "bool", 0),
        TableFieldSpec("FreeEmbark", "提供免费登船", "bool", "bool", 0),
        TableFieldSpec("CaptureRemovesBuildings", "被占领移除建筑", "bool", "bool", 0),
        TableFieldSpec("CaptureRemovesCityDefenses", "被占领移除城防", "bool", "bool", 0),
        TableFieldSpec("TradeEmbark", "商路可登船", "bool", "bool", 0),
        TableFieldSpec("OnePerCity", "每城限一", "bool", "bool", 1),
        TableFieldSpec("AllowsHolyCity", "允许圣城", "bool", "bool", 0),
        TableFieldSpec("AdjacentToLand", "必须邻接陆地", "bool", "bool", 0),
        TableFieldSpec("CanAttack", "可进行攻击", "bool", "bool", 0),
        TableFieldSpec("CaptureRemovesDistrict", "被占领移除区域", "bool", "bool", 0),
    ]

    _apply_required_rules("Districts", fields)

    linked_groups = [
        LinkedGroupSpec("plunder", "掠夺联动参数", "PlunderType", "PlunderAmount"),
        LinkedGroupSpec("cost_progression", "成本递增联动参数", "CostProgressionModel", "CostProgressionParam1"),
    ]

    return MainTableSchema(
        table_name="Districts",
        head="DISTRICT",
        midfix_code="D",
        abbr_key="abbr",
        type_key="DistrictType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=linked_groups,
    )


def build_buildings_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "建筑名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "建筑描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("Quote", "名言（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("QuoteAudio", "名言音频（英文）", "text", "basic", "", english_only=True),
        TableFieldSpec("PrereqTech", "前置科技", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["PrereqTech"]),
        TableFieldSpec("PrereqCivic", "前置市政", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["PrereqCivic"]),
        TableFieldSpec("PrereqDistrict", "前置区域", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["PrereqDistrict"]),
        TableFieldSpec("AdjacentDistrict", "邻接区域", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["AdjacentDistrict"]),
        TableFieldSpec("AdjacentResource", "邻接资源", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["AdjacentResource"]),
        TableFieldSpec("PurchaseYield", "购买产出类型", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["PurchaseYield"]),
        TableFieldSpec("ObsoleteEra", "过时时代", "template", "basic", "NO_ERA", template_key=BUILDING_TEMPLATE_MAPPING["ObsoleteEra"]),
        TableFieldSpec("AdvisorType", "顾问类型", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["AdvisorType"]),
        TableFieldSpec("AdjacentImprovement", "邻接改良设施", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["AdjacentImprovement"]),
        TableFieldSpec("CityAdjacentTerrain", "城市邻接地形", "template", "basic", "", template_key=BUILDING_TEMPLATE_MAPPING["CityAdjacentTerrain"]),
        TableFieldSpec("TraitType", "TraitType", "trait_toggle", "basic", 0),
        TableFieldSpec("GovernmentTierRequirement", "政体等级需求（英文）", "text", "basic", "", english_only=True),

        TableFieldSpec("Cost", "建造成本", "int", "number", 1),
        TableFieldSpec("MaxPlayerInstances", "每玩家上限", "int", "number", -1),
        TableFieldSpec("MaxWorldInstances", "全世界上限", "int", "number", -1),
        TableFieldSpec("OuterDefenseHitPoints", "外城防耐久", "int", "number", 0),
        TableFieldSpec("Housing", "住房", "int", "number", 0),
        TableFieldSpec("Entertainment", "宜居度", "int", "number", 0),
        TableFieldSpec("Maintenance", "维护费", "int", "number", 0),
        TableFieldSpec("OuterDefenseStrength", "外城防强度", "int", "number", 0),
        TableFieldSpec("CitizenSlots", "市民槽位", "int", "number", 0),
        TableFieldSpec("RegionalRange", "区域范围", "int", "number", 0),
        TableFieldSpec("GrantFortification", "驻防加成", "int", "number", 0),
        TableFieldSpec("DefenseModifier", "防御修正", "int", "number", 0),

        TableFieldSpec("Capital", "首都限定", "bool", "bool", 0),
        TableFieldSpec("RequiresPlacement", "需要地块放置", "bool", "bool", 0),
        TableFieldSpec("RequiresRiver", "需要河流", "bool", "bool", 0),
        TableFieldSpec("Coast", "允许沿海", "bool", "bool", 0),
        TableFieldSpec("EnabledByReligion", "宗教启用", "bool", "bool", 0),
        TableFieldSpec("AllowsHolyCity", "允许圣城", "bool", "bool", 0),
        TableFieldSpec("MustPurchase", "必须购买", "bool", "bool", 0),
        TableFieldSpec("IsWonder", "是否奇观", "bool", "bool", 0),
        TableFieldSpec("MustBeLake", "必须湖泊", "bool", "bool", 0),
        TableFieldSpec("MustNotBeLake", "不能湖泊", "bool", "bool", 0),
        TableFieldSpec("AdjacentToMountain", "必须邻山", "bool", "bool", 0),
        TableFieldSpec("RequiresReligion", "需要宗教", "bool", "bool", 0),
        TableFieldSpec("InternalOnly", "仅内部可建", "bool", "bool", 0),
        TableFieldSpec("RequiresAdjacentRiver", "必须邻接河流", "bool", "bool", 0),
        TableFieldSpec("MustBeAdjacentLand", "必须邻接陆地", "bool", "bool", 0),
        TableFieldSpec("AdjacentCapital", "必须邻接首都", "bool", "bool", 0),
        TableFieldSpec("UnlocksGovernmentPolicy", "解锁政体政策", "bool", "bool", 0),
    ]

    return MainTableSchema(
        table_name="Buildings",
        head="BUILDING",
        midfix_code="B",
        abbr_key="abbr",
        type_key="BuildingType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=[],
    )


def build_units_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "单位名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "单位描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("Domain", "领域", "template", "basic", "DOMAIN_LAND", template_key=UNIT_TEMPLATE_MAPPING["Domain"]),
        TableFieldSpec("FormationClass", "编队类型", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["FormationClass"]),
        TableFieldSpec("CostProgressionModel", "成本递增模型", "template", "basic", "NO_COST_PROGRESSION", template_key=UNIT_TEMPLATE_MAPPING["CostProgressionModel"]),
        TableFieldSpec("CostProgressionParam1", "成本递增参数", "int", "basic", 0),
        TableFieldSpec("PromotionClass", "晋升类型", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["PromotionClass"]),
        TableFieldSpec("PrereqTech", "前置科技", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["PrereqTech"]),
        TableFieldSpec("PrereqCivic", "前置市政", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["PrereqCivic"]),
        TableFieldSpec("PrereqDistrict", "前置区域", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["PrereqDistrict"]),
        TableFieldSpec("StrategicResource", "战略资源", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["StrategicResource"]),
        TableFieldSpec("PurchaseYield", "购买产出", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["PurchaseYield"]),
        TableFieldSpec("PseudoYieldType", "伪产出类型（英文）", "text", "basic", "", english_only=True),
        TableFieldSpec("ObsoleteTech", "过时科技", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["ObsoleteTech"]),
        TableFieldSpec("ObsoleteCivic", "过时市政", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["ObsoleteCivic"]),
        TableFieldSpec("MandatoryObsoleteTech", "强制过时科技", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["MandatoryObsoleteTech"]),
        TableFieldSpec("MandatoryObsoleteCivic", "强制过时市政", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["MandatoryObsoleteCivic"]),
        TableFieldSpec("AdvisorType", "顾问类型", "template", "basic", "", template_key=UNIT_TEMPLATE_MAPPING["AdvisorType"]),
        TableFieldSpec("LeaderType", "限定领袖（英文）", "text", "basic", "", english_only=True),
        TableFieldSpec("Flavor", "Flavor（英文）", "text", "basic", "", english_only=True),
        TableFieldSpec("TraitType", "TraitType", "trait_toggle", "basic", 0),

        TableFieldSpec("BaseSightRange", "基础视野", "int", "number", 2),
        TableFieldSpec("BaseMoves", "基础移动力", "int", "number", 2),
        TableFieldSpec("Combat", "近战战斗力", "int", "number", 0),
        TableFieldSpec("RangedCombat", "远程战斗力", "int", "number", 0),
        TableFieldSpec("Range", "射程", "int", "number", 0),
        TableFieldSpec("Bombard", "轰炸战斗力", "int", "number", 0),
        TableFieldSpec("Cost", "建造成本", "int", "number", 1),
        TableFieldSpec("PopulationCost", "人口成本", "int", "number", 0),
        TableFieldSpec("BuildCharges", "建造次数", "int", "number", 0),
        TableFieldSpec("ReligiousStrength", "宗教强度", "int", "number", 0),
        TableFieldSpec("ReligionEvictPercent", "宗教驱逐比例", "int", "number", 0),
        TableFieldSpec("SpreadCharges", "传播次数", "int", "number", 0),
        TableFieldSpec("ReligiousHealCharges", "宗教治疗次数", "int", "number", 0),
        TableFieldSpec("InitialLevel", "初始等级", "int", "number", 1),
        TableFieldSpec("NumRandomChoices", "随机晋升数", "int", "number", 0),
        TableFieldSpec("PrereqPopulation", "人口前置需求", "int", "number", 0),
        TableFieldSpec("Maintenance", "维护费", "int", "number", 0),
        TableFieldSpec("AirSlots", "空军槽位", "int", "number", 0),
        TableFieldSpec("AntiAirCombat", "防空战斗力", "int", "number", 0),
        TableFieldSpec("ParkCharges", "公园次数", "int", "number", 0),
        TableFieldSpec("DisasterCharges", "灾害次数", "int", "number", 0),

        TableFieldSpec("FoundCity", "可建城", "bool", "bool", 0),
        TableFieldSpec("FoundReligion", "可建宗教", "bool", "bool", 0),
        TableFieldSpec("MakeTradeRoute", "可建商路", "bool", "bool", 0),
        TableFieldSpec("EvangelizeBelief", "可传教", "bool", "bool", 0),
        TableFieldSpec("LaunchInquisition", "可发起审判", "bool", "bool", 0),
        TableFieldSpec("RequiresInquisition", "需要可审判", "bool", "bool", 0),
        TableFieldSpec("ExtractsArtifacts", "可发掘文物", "bool", "bool", 0),
        TableFieldSpec("CanCapture", "可俘虏", "bool", "bool", 1),
        TableFieldSpec("CanRetreatWhenCaptured", "被俘可撤退", "bool", "bool", 0),
        TableFieldSpec("AllowBarbarians", "蛮族可用", "bool", "bool", 0),
        TableFieldSpec("CanTrain", "可训练", "bool", "bool", 1),
        TableFieldSpec("MustPurchase", "必须购买", "bool", "bool", 0),
        TableFieldSpec("Stackable", "可堆叠", "bool", "bool", 0),
        TableFieldSpec("CanTargetAir", "可攻击空中", "bool", "bool", 0),
        TableFieldSpec("ZoneOfControl", "控制区", "bool", "bool", 0),
        TableFieldSpec("Spy", "间谍单位", "bool", "bool", 0),
        TableFieldSpec("WMDCapable", "可携带核武", "bool", "bool", 0),
        TableFieldSpec("IgnoreMoves", "IgnoreMoves", "bool", "bool", 0),
        TableFieldSpec("TeamVisibility", "团队共享视野", "bool", "bool", 0),
        TableFieldSpec("EnabledByReligion", "宗教启用", "bool", "bool", 0),
        TableFieldSpec("TrackReligion", "TrackReligion", "bool", "bool", 0),
        TableFieldSpec("UseMaxMeleeTrainedStrength", "使用最高近战训练力", "bool", "bool", 0),
        TableFieldSpec("ImmediatelyName", "立即命名", "bool", "bool", 0),
        TableFieldSpec("CanEarnExperience", "可获得经验", "bool", "bool", 1),
    ]

    _apply_required_rules("Units", fields)

    return MainTableSchema(
        table_name="Units",
        head="UNIT",
        midfix_code="U",
        abbr_key="abbr",
        type_key="UnitType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=[],
        portrait_suffix="_PORTRAIT",
        top_basic_visual_limit=16,
    )


def build_improvements_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "改良设施名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "改良设施描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("PrereqTech", "前置科技", "template", "basic", "", template_key=IMPROVEMENT_TEMPLATE_MAPPING["PrereqTech"]),
        TableFieldSpec("PrereqCivic", "前置市政", "template", "basic", "", template_key=IMPROVEMENT_TEMPLATE_MAPPING["PrereqCivic"]),
        TableFieldSpec("PlunderType", "掠夺类型", "template", "basic", "NO_PLUNDER", template_key=IMPROVEMENT_TEMPLATE_MAPPING["PlunderType"], linked_group="plunder"),
        TableFieldSpec("PlunderAmount", "掠夺数值", "int", "basic", 0, linked_group="plunder"),
        TableFieldSpec("TraitType", "TraitType", "trait_toggle", "basic", 0),
        TableFieldSpec("YieldFromAppeal", "魅力产出", "template", "basic", "", template_key=IMPROVEMENT_TEMPLATE_MAPPING["YieldFromAppeal"]),
        TableFieldSpec("Domain", "领域", "template", "basic", "DOMAIN_LAND", template_key=IMPROVEMENT_TEMPLATE_MAPPING["Domain"]),
        TableFieldSpec("ImprovementOnRemove", "移除后改良设施", "template", "basic", "", template_key=IMPROVEMENT_TEMPLATE_MAPPING["ImprovementOnRemove"]),

        TableFieldSpec("DispersalGold", "拆除后获得金币", "int", "number", 0),
        TableFieldSpec("Housing", "住房", "int", "number", 0),
        TableFieldSpec("TilesRequired", "需求地块数", "int", "number", 1),
        TableFieldSpec("AirSlots", "空军槽位", "int", "number", 0),
        TableFieldSpec("DefenseModifier", "防御修正值", "int", "number", 0),
        TableFieldSpec("GrantFortification", "驻防加成", "int", "number", 0),
        TableFieldSpec("MinimumAppeal", "最低魅力需求", "int", "number", 0),
        TableFieldSpec("WeaponSlots", "核武器发射槽位", "int", "number", 0),
        TableFieldSpec("ReligiousUnitHealRate", "ReligiousUnitHealRate", "int", "number", 0),
        TableFieldSpec("Appeal", "相邻地块魅力加成", "int", "number", 0),
        TableFieldSpec("YieldFromAppealPercent", "魅力产出百分比", "int", "number", 100),
        TableFieldSpec("ValidAdjacentTerrainAmount", "需要相邻指定地形数量", "int", "number", 0),
        TableFieldSpec("MovementChange", "移动力变化", "int", "number", 0),
        TableFieldSpec("TilesPerGoody", "TilesPerGoody", "int", "number", 0),
        TableFieldSpec("GoodyRange", "GoodyRange", "int", "number", 0),

        TableFieldSpec("BarbarianCamp", "蛮族营地", "bool", "bool", 0),
        TableFieldSpec("Buildable", "可建造", "bool", "bool", 0),
        TableFieldSpec("RemoveOnEntry", "进入后移除", "bool", "bool", 0),
        TableFieldSpec("Goody", "部落村庄", "bool", "bool", 0),
        TableFieldSpec("SameAdjacentValid", "允许相邻", "bool", "bool", 1),
        TableFieldSpec("RequiresRiver", "需求河流", "bool", "bool", 0),
        TableFieldSpec("EnforceTerrain", "EnforceTerrain", "bool", "bool", 0),
        TableFieldSpec("BuildInLine", "线性建造", "bool", "bool", 0),
        TableFieldSpec("CanBuildOutsideTerritory", "可在境外建造", "bool", "bool", 0),
        TableFieldSpec("BuildOnFrontier", "边境建造", "bool", "bool", 0),
        TableFieldSpec("Coast", "沿海", "bool", "bool", 0),
        TableFieldSpec("OnePerCity", "每城唯一", "bool", "bool", 0),
        TableFieldSpec("AdjacentSeaResource", "邻接海洋资源", "bool", "bool", 0),
        TableFieldSpec("RequiresAdjacentBonusOrLuxury", "需求邻接加成或奢侈", "bool", "bool", 0),
        TableFieldSpec("Workable", "可工作", "bool", "bool", 1),
        TableFieldSpec("GoodyNotify", "GoodyNotify", "bool", "bool", 1),
        TableFieldSpec("NoAdjacentSpecialtyDistrict", "不可邻接专业区域", "bool", "bool", 0),
        TableFieldSpec("RequiresAdjacentLuxury", "需求邻接奢侈", "bool", "bool", 0),
        TableFieldSpec("AdjacentToLand", "邻接陆地", "bool", "bool", 0),
        TableFieldSpec("Removable", "可移除", "bool", "bool", 1),
        TableFieldSpec("OnlyOpenBorders", "仅开放边界", "bool", "bool", 0),
        TableFieldSpec("Capturable", "可占领", "bool", "bool", 1),
    ]

    linked_groups = [
        LinkedGroupSpec("plunder", "掠夺参数", "PlunderType", "PlunderAmount"),
    ]

    # 应用全局必填规则（如 Improvements.PlunderType -> required, default）
    _apply_required_rules("Improvements", fields)

    return MainTableSchema(
        table_name="Improvements",
        head="IMPROVEMENT",
        midfix_code="I",
        abbr_key="abbr",
        type_key="ImprovementType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=linked_groups,
    )


def build_policies_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "政策卡名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "政策卡描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("PrereqCivic", "前置市政", "template", "basic", "", template_key=POLICY_TEMPLATE_MAPPING["PrereqCivic"]),
        TableFieldSpec("PrereqTech", "前置科技", "template", "basic", "", template_key=POLICY_TEMPLATE_MAPPING["PrereqTech"]),
        TableFieldSpec("GovernmentSlotType", "政策槽位", "template", "basic", "SLOT_WILDCARD", template_key=POLICY_TEMPLATE_MAPPING["GovernmentSlotType"]),
        TableFieldSpec("RequiresGovernmentUnlock", "需要政体解锁", "bool", "bool", 0),
        TableFieldSpec("ExplicitUnlock", "显式解锁", "bool", "bool", 0),
    ]

    return MainTableSchema(
        table_name="Policies",
        head="POLICY",
        midfix_code="P",
        abbr_key="abbr",
        type_key="PolicyType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=[],
        has_images=False,
        top_basic_visual_limit=16,
    )


def build_projects_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "项目名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("ShortName", "项目短名（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "项目描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("PopupText", "弹窗文本（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("PrereqTech", "前置科技", "template", "basic", "", template_key=PROJECT_TEMPLATE_MAPPING["PrereqTech"]),
        TableFieldSpec("PrereqCivic", "前置市政", "template", "basic", "", template_key=PROJECT_TEMPLATE_MAPPING["PrereqCivic"]),
        TableFieldSpec("PrereqDistrict", "前置区域", "template", "basic", "", template_key=PROJECT_TEMPLATE_MAPPING["PrereqDistrict"]),
        TableFieldSpec("RequiredBuilding", "需要建筑", "template", "basic", "", template_key=PROJECT_TEMPLATE_MAPPING["RequiredBuilding"]),
        TableFieldSpec("VisualBuildingType", "展示建筑", "template", "basic", "", template_key=PROJECT_TEMPLATE_MAPPING["VisualBuildingType"]),
        TableFieldSpec("CostProgressionModel", "成本递增模型", "template", "basic", "NO_PROGRESSION_MODEL", template_key=PROJECT_TEMPLATE_MAPPING["CostProgressionModel"], linked_group="cost_progression"),
        TableFieldSpec("CostProgressionParam1", "成本递增参数", "int", "basic", 0, linked_group="cost_progression"),
        TableFieldSpec("PrereqResource", "前置资源", "template", "basic", "", template_key=PROJECT_TEMPLATE_MAPPING["PrereqResource"]),
        TableFieldSpec("AdvisorType", "顾问类型", "template", "basic", "ADVISOR_GENERIC", template_key=PROJECT_TEMPLATE_MAPPING["AdvisorType"]),

        TableFieldSpec("Cost", "基础成本", "int", "number", 1),
        TableFieldSpec("MaxPlayerInstances", "每玩家上限", "int", "number", -1),
        TableFieldSpec("AmenitiesWhileActive", "进行中宜居度", "int", "number", 0),

        TableFieldSpec("SpaceRace", "太空竞赛项目", "bool", "bool", 0),
        TableFieldSpec("OuterDefenseRepair", "修复外城防", "bool", "bool", 0),
        TableFieldSpec("WMD", "WMD项目", "bool", "bool", 0),
        TableFieldSpec("UnlocksFromEffect", "效果解锁", "bool", "bool", 0),
    ]

    linked_groups = [
        LinkedGroupSpec("cost_progression", "成本递增联动参数", "CostProgressionModel", "CostProgressionParam1"),
    ]

    return MainTableSchema(
        table_name="Projects",
        head="PROJECT",
        midfix_code="P",
        abbr_key="abbr",
        type_key="ProjectType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=linked_groups,
        has_images=True,
        top_basic_visual_limit=16,
    )


def build_beliefs_main_schema() -> MainTableSchema:
    fields: list[TableFieldSpec] = [
        TableFieldSpec("Name", "信仰名字（中文）", "text", "basic", "", chinese_input=True),
        TableFieldSpec("Description", "信仰描述（中文）", "text", "basic", "", chinese_input=True, tokenized_multiline=True),
        TableFieldSpec("BeliefClassType", "信仰类别", "template", "basic", "", template_key=BELIEF_TEMPLATE_MAPPING["BeliefClassType"]),
    ]

    return MainTableSchema(
        table_name="Beliefs",
        head="BELIEF",
        midfix_code="B",
        abbr_key="abbr",
        type_key="BeliefType",
        name_key="Name",
        description_key="Description",
        icon_size=(256, 256),
        fields=fields,
        linked_groups=[],
        has_images=False,
        top_basic_visual_limit=16,
    )


class MainTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        schema: MainTableSchema,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._schema = schema
        self._shared_params_provider = shared_params_provider
        self._type_builder = type_builder
        self._image_widget_factory = image_widget_factory

        self._entry_name_fallback = ""
        self._internal_updating = False

        self._abbr_edit = QLineEdit()
        self._abbr_edit.setPlaceholderText("仅英文/数字/下划线")
        self._type_label = QLabel(self._schema.head)
        self._type_label.setObjectName("pageInfoLabel")
        self._icon_name = QLineEdit()
        self._icon_name.setReadOnly(True)
        self._icon_widget: QWidget | None = None
        if self._schema.has_images:
            self._icon_widget = image_widget_factory(self._schema.icon_size, True)
        self._portrait_name: QLineEdit | None = None
        self._portrait_widget: QWidget | None = None
        if self._schema.has_images and self._schema.portrait_suffix:
            self._portrait_name = QLineEdit()
            self._portrait_name.setReadOnly(True)
            self._portrait_widget = image_widget_factory(self._schema.icon_size, True)

        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, TableFieldSpec] = {item.key: item for item in self._schema.fields}

        self._build_ui()
        self._bind_events()
        self._refresh_type_labels()

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)

        basic_group = QGroupBox(f"{self._schema.table_name} 基础信息")
        basic_layout = QVBoxLayout()

        top_row = QHBoxLayout()
        top_entries: list[tuple[object, QWidget]] = [
            ("简称", self._abbr_edit),
            ("完整Type", self._type_label),
        ]

        basic_fields = [f for f in self._schema.fields if f.section == "basic" and f.linked_group is None]
        basic_entries: list[tuple[object, QWidget]] = []
        for field in basic_fields:
            widget = self._create_widget(field)
            self._field_widgets[field.key] = widget
            basic_entries.append((self._build_field_label(field), widget))

        visual_limit = max(1, int(self._schema.top_basic_visual_limit or BASIC_WITH_ICON_ROWS_LIMIT))
        first_entries: list[tuple[object, QWidget]] = []
        used_visual_units = 0
        for label_text, widget in basic_entries:
            unit_cost = 3 if isinstance(widget, (NewlineTokenTextEdit, IconTokenTextEdit)) else 1
            if first_entries and used_visual_units + unit_cost > visual_limit:
                break
            first_entries.append((label_text, widget))
            used_visual_units += unit_cost

        first_count = len(first_entries)
        remain_entries: list[tuple[object, QWidget]] = list(basic_entries[first_count:])

        top_entries.extend(first_entries)
        left_holder = QWidget()
        left_holder_layout = QVBoxLayout()
        left_holder_layout.setContentsMargins(0, 0, 0, 0)
        left_holder_layout.addWidget(self._build_form_widget(top_entries), 1)
        left_holder.setLayout(left_holder_layout)

        top_row.addWidget(left_holder, 1)
        if self._schema.has_images and self._icon_widget is not None:
            right_holder = QWidget()
            right_layout = QVBoxLayout()
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            right_layout.addWidget(self._icon_name)
            right_layout.addWidget(self._icon_widget)
            if self._portrait_name is not None and self._portrait_widget is not None:
                right_layout.addWidget(self._portrait_name)
                right_layout.addWidget(self._portrait_widget)
            right_layout.addStretch(1)
            right_holder.setLayout(right_layout)
            right_holder.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            top_row.addWidget(right_holder, 0)
        basic_layout.addLayout(top_row)

        if remain_entries:
            self._append_balanced_basic_rows(
                basic_layout,
                remain_entries,
                max_rows_per_column=BASIC_ROWS_PER_COLUMN_LIMIT,
            )

        for group in self._schema.linked_groups:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{group.label}"), 0)
            first_widget = self._field_widgets.get(group.first_key)
            if first_widget is None:
                first_spec = self._field_specs[group.first_key]
                first_widget = self._create_widget(first_spec)
                self._field_widgets[group.first_key] = first_widget
            second_widget = self._field_widgets.get(group.second_key)
            if second_widget is None:
                second_spec = self._field_specs[group.second_key]
                second_widget = self._create_widget(second_spec)
                self._field_widgets[group.second_key] = second_widget
            first_spec = self._field_specs[group.first_key]
            second_spec = self._field_specs[group.second_key]
            row.addWidget(self._build_field_label(first_spec, with_colon=True), 0)
            row.addWidget(first_widget, 1)
            row.addWidget(self._build_field_label(second_spec, with_colon=True), 0)
            row.addWidget(second_widget, 1)
            basic_layout.addLayout(row)

        basic_group.setLayout(basic_layout)
        root.addWidget(basic_group)

        number_fields = [f for f in self._schema.fields if f.section == "number"]
        if number_fields:
            number_group = QGroupBox("数值参数")
            number_layout = QGridLayout()
            for index, field in enumerate(number_fields):
                cell = QWidget()
                cell_layout = QHBoxLayout()
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.addWidget(self._build_field_label(field, with_colon=True), 0)
                widget = self._create_widget(field)
                self._field_widgets[field.key] = widget
                cell_layout.addWidget(widget, 1)
                cell.setLayout(cell_layout)
                row = index // 3
                col = index % 3
                number_layout.addWidget(cell, row, col)
            number_group.setLayout(number_layout)
            root.addWidget(number_group)

        bool_fields = [f for f in self._schema.fields if f.section == "bool"]
        if bool_fields:
            bool_group = QGroupBox("布尔参数")
            bool_layout = QGridLayout()
            for index, field in enumerate(bool_fields):
                widget = self._create_widget(field)
                self._field_widgets[field.key] = widget
                row = index // 3
                col = index % 3
                bool_layout.addWidget(widget, row, col)
            bool_group.setLayout(bool_layout)
            root.addWidget(bool_group)

        root.addStretch(1)
        self.setLayout(root)

    def _append_balanced_basic_rows(
        self,
        target_layout: QVBoxLayout,
        entries: list[tuple[object, QWidget]],
        *,
        max_rows_per_column: int,
    ) -> None:
        if not entries:
            return

        block_capacity = max_rows_per_column * 2
        start = 0
        while start < len(entries):
            block = entries[start : start + block_capacity]
            start += block_capacity

            if len(block) <= max_rows_per_column:
                split_at = max(1, (len(block) + 1) // 2)
            else:
                split_at = min(max_rows_per_column, len(block))
            left_entries = block[:split_at]
            right_entries = block[split_at:]

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)

            row.addWidget(self._build_form_widget(left_entries), 1)
            row.addWidget(self._build_form_widget(right_entries), 1)

            target_layout.addLayout(row)

    def _build_form_widget(self, entries: list[tuple[object, QWidget]]) -> QWidget:
        holder = QWidget()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        for label, widget in entries:
            if isinstance(label, QWidget):
                form.addRow(label, widget)
            else:
                form.addRow(str(label), widget)
        holder.setLayout(form)
        return holder

    def _build_field_label(self, field: TableFieldSpec, *, with_colon: bool = False) -> QLabel:
        base = str(field.label or "")
        suffix = ":" if with_colon else ""
        if field.required:
            label = QLabel(f"{base}<span style='color:#dc2626'>*</span>{suffix}")
            label.setTextFormat(Qt.TextFormat.RichText)
            return label
        return QLabel(f"{base}{suffix}")

    def _create_widget(self, field: TableFieldSpec) -> QWidget:
        if field.field_type == "trait_toggle":
            return _TraitTypeToggleWidget()

        if field.field_type == "bool":
            checkbox = QCheckBox(field.label)
            checkbox.setChecked(bool(int(field.default or 0)))
            _attach_hover_param_tooltip(checkbox, field.key)
            return checkbox

        if field.field_type == "int":
            spin = QSpinBox()
            if field.key == "Cost":
                spin.setRange(1, 999999)
                try:
                    spin.setValue(max(1, int(field.default or 1)))
                except (TypeError, ValueError):
                    spin.setValue(1)
            else:
                spin.setRange(-999999, 999999)
                spin.setValue(int(field.default or 0))
            _attach_hover_param_tooltip(spin, field.key)
            return spin

        if field.field_type == "real":
            spin = _CompactDoubleSpinBox()
            spin.setRange(-999999.0, 999999.0)
            spin.setValue(float(field.default or 0.0))
            _attach_hover_param_tooltip(spin, field.key)
            return spin

        if field.field_type == "template" and field.template_key:
            widget = build_template_widget(field.template_key)
            if hasattr(widget, "set_label_text"):
                widget.set_label_text("")
            return widget

        if field.field_type == "text" and field.tokenized_multiline:
            text_edit = IconTokenTextEdit()
            text_edit.setPlaceholderText("输入文本（右键插入图标；回车写入 [NEWLINE]）")
            text_edit.setFixedHeight(88)
            if field.default is not None and str(field.default) != "":
                text_edit.import_tokenized_text(field.default)
            return text_edit

        line = QLineEdit()
        if field.default is not None and str(field.default) != "":
            line.setText(str(field.default))
        if field.chinese_input:
            line.setPlaceholderText("输入中文")
        elif field.english_only:
            line.setPlaceholderText("仅英文/数字/下划线")
        else:
            line.setPlaceholderText("输入文本")
        return line

    def _bind_events(self) -> None:
        self._abbr_edit.textChanged.connect(self._handle_abbr_changed)
        for key, widget in self._field_widgets.items():
            field = self._field_specs[key]
            if isinstance(widget, QLineEdit):
                if field.english_only and not field.chinese_input:
                    widget.textChanged.connect(lambda _v, wk=widget: self._sanitize_line_edit(wk))
                widget.textChanged.connect(lambda _v: self._emit_data_changed())
            elif isinstance(widget, (NewlineTokenTextEdit, IconTokenTextEdit)):
                widget.textChanged.connect(lambda: self._emit_data_changed())
            elif isinstance(widget, QSpinBox):
                widget.valueChanged.connect(lambda _v: self._emit_data_changed())
            elif isinstance(widget, QDoubleSpinBox):
                widget.valueChanged.connect(lambda _v: self._emit_data_changed())
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(lambda _v: self._emit_data_changed())
            elif isinstance(widget, _TraitTypeToggleWidget):
                widget.changed.connect(self._emit_data_changed)
            elif isinstance(widget, BaseTemplateWidget):
                widget.dataChanged.connect(self._emit_data_changed)

        if self._icon_widget is not None and hasattr(self._icon_widget, "dataChanged"):
            self._icon_widget.dataChanged.connect(self._emit_data_changed)
        if self._portrait_widget is not None and hasattr(self._portrait_widget, "dataChanged"):
            self._portrait_widget.dataChanged.connect(self._emit_data_changed)

    def _sanitize_line_edit(self, line_edit: QLineEdit) -> None:
        text = line_edit.text()
        cleaned = _sanitize_english_token(text)
        if cleaned == text:
            return
        cursor = line_edit.cursorPosition()
        line_edit.blockSignals(True)
        line_edit.setText(cleaned)
        line_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
        line_edit.blockSignals(False)

    def _handle_abbr_changed(self, text: str) -> None:
        cleaned = _sanitize_english_token(text).upper()
        if cleaned != text:
            cursor = self._abbr_edit.cursorPosition()
            self._abbr_edit.blockSignals(True)
            self._abbr_edit.setText(cleaned)
            self._abbr_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._abbr_edit.blockSignals(False)
        self._refresh_type_labels()
        self._emit_data_changed()

    def _refresh_type_labels(self) -> None:
        shared = self._shared_params_provider()
        type_text = self._type_builder(shared, self._schema.head, self._schema.midfix_code, self._abbr_edit.text())
        self._type_label.setText(type_text)
        if self._schema.has_images:
            self._icon_name.setText(f"ICON_{type_text}" if type_text else "")
        else:
            self._icon_name.setText("")
        if self._portrait_name is not None and self._schema.portrait_suffix:
            self._portrait_name.setText(f"ICON_{type_text}{self._schema.portrait_suffix}" if type_text else "")
        trait_widget = self._field_widgets.get("TraitType")
        if isinstance(trait_widget, _TraitTypeToggleWidget):
            trait_widget.set_trait_type(f"TRAIT_{type_text}" if type_text else "")

    def _set_field_value(self, key: str, value: object) -> None:
        widget = self._field_widgets.get(key)
        if widget is None:
            return
        if isinstance(widget, QLineEdit):
            widget.setText(_safe_text(value))
        elif isinstance(widget, (NewlineTokenTextEdit, IconTokenTextEdit)):
            widget.import_tokenized_text(value)
        elif isinstance(widget, QSpinBox):
            try:
                number = int(value if value is not None else 0)
                if key == "Cost":
                    number = max(1, number)
                widget.setValue(number)
            except (TypeError, ValueError):
                widget.setValue(1 if key == "Cost" else 0)
        elif isinstance(widget, QDoubleSpinBox):
            try:
                widget.setValue(float(value if value is not None else 0.0))
            except (TypeError, ValueError):
                widget.setValue(0.0)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(int(value or 0)))
        elif isinstance(widget, _TraitTypeToggleWidget):
            if isinstance(value, str):
                widget.set_checked(bool(_safe_text(value)))
            else:
                try:
                    widget.set_checked(bool(int(value or 0)))
                except (TypeError, ValueError):
                    widget.set_checked(False)
        elif isinstance(widget, BaseTemplateWidget):
            if hasattr(widget, "set_current_value"):
                resolved: str | None
                if isinstance(value, dict):
                    preferred_keys: list[str] = []
                    if key == "PrereqTech":
                        preferred_keys = [
                            "technology_type",
                            "TechnologyType",
                            "prereq_tech",
                            "PrereqTech",
                            "value",
                            "Value",
                            "type",
                            "Type",
                            "display",
                            "Display",
                            "name",
                            "Name",
                        ]
                    elif key == "PrereqCivic":
                        preferred_keys = [
                            "civic_type",
                            "CivicType",
                            "prereq_civic",
                            "PrereqCivic",
                            "value",
                            "Value",
                            "type",
                            "Type",
                            "display",
                            "Display",
                            "name",
                            "Name",
                        ]
                    else:
                        preferred_keys = ["value", "type", "display", "name"]

                    resolved = ""
                    for preferred_key in preferred_keys:
                        candidate = _safe_text(value.get(preferred_key))
                        if candidate:
                            resolved = candidate
                            break
                    if not resolved:
                        resolved = _first_non_empty(value)
                    widget.set_current_value(resolved or None)
                else:
                    widget.set_current_value(_safe_text(value) or None)

    def _get_field_value(self, key: str) -> object:
        widget = self._field_widgets.get(key)
        if widget is None:
            return ""
        if isinstance(widget, QLineEdit):
            return _safe_text(widget.text())
        if isinstance(widget, (NewlineTokenTextEdit, IconTokenTextEdit)):
            return widget.export_tokenized_text()
        if isinstance(widget, QSpinBox):
            value = int(widget.value())
            if key == "Cost":
                return max(1, value)
            return value
        if isinstance(widget, QDoubleSpinBox):
            return float(widget.value())
        if isinstance(widget, QCheckBox):
            return 1 if widget.isChecked() else 0
        if isinstance(widget, _TraitTypeToggleWidget):
            current_type = _safe_text(self._type_label.text())
            return f"TRAIT_{current_type}" if widget.is_checked() and current_type else ""
        if isinstance(widget, BaseTemplateWidget):
            payload = widget.export_data()
            if key == "PrereqTech":
                value = _pick_non_empty_by_keys(
                    payload,
                    [
                        "technology_type",
                        "TechnologyType",
                        "prereq_tech",
                        "PrereqTech",
                        "value",
                        "Value",
                        "type",
                        "Type",
                    ],
                )
                return value or _first_non_empty(payload)
            if key == "PrereqCivic":
                value = _pick_non_empty_by_keys(
                    payload,
                    [
                        "civic_type",
                        "CivicType",
                        "prereq_civic",
                        "PrereqCivic",
                        "value",
                        "Value",
                        "type",
                        "Type",
                    ],
                )
                return value or _first_non_empty(payload)
            return _first_non_empty(payload)
        return ""

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._internal_updating = True
        self._entry_name_fallback = fallback_name

        self._abbr_edit.setText(_safe_text(entry.get(self._schema.abbr_key)))

        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        if not table_data:
            table_data = {key: entry.get(key) for key in self._field_specs.keys()}

        for key, spec in self._field_specs.items():
            value = table_data.get(key)
            if value is None:
                value = spec.default
            self._set_field_value(key, value)

        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        icon_payload = images.get("icon")
        if self._icon_widget is not None and hasattr(self._icon_widget, "set_state"):
            self._icon_widget.set_state(icon_payload)
        if self._portrait_widget is not None and hasattr(self._portrait_widget, "set_state"):
            self._portrait_widget.set_state(images.get("portrait"))

        self._refresh_type_labels()
        self._internal_updating = False

    def export_entry(self) -> dict[str, object]:
        data: dict[str, object] = {}
        for key in self._field_specs.keys():
            data[key] = self._get_field_value(key)

        display_name = _safe_text(data.get(self._schema.name_key)) or self._entry_name_fallback

        images_payload = {}
        if self._icon_widget is not None and hasattr(self._icon_widget, "export_state"):
            images_payload["icon"] = self._icon_widget.export_state()
        if self._portrait_widget is not None and hasattr(self._portrait_widget, "export_state"):
            images_payload["portrait"] = self._portrait_widget.export_state()

        payload = {
            "name": display_name,
            self._schema.abbr_key: _safe_text(self._abbr_edit.text()),
            "type": _safe_text(self._type_label.text()),
            self._schema.type_key: _safe_text(self._type_label.text()),
            "table_name": self._schema.table_name,
            "table_data": data,
            self._schema.name_key: _safe_text(data.get(self._schema.name_key)),
            self._schema.description_key: _safe_text(data.get(self._schema.description_key)),
            "icon_image_name": _safe_text(self._icon_name.text()),
            "portrait_image_name": _safe_text(self._portrait_name.text()) if self._portrait_name is not None else "",
            "images": images_payload,
        }
        return payload

    def export_main_table_row(self) -> dict[str, object]:
        """导出当前主表单行为列值字典（用于生成 SQL/XML）。"""
        row: dict[str, object] = {
            self._schema.type_key: _safe_text(self._type_label.text()),
        }
        for key in self._field_specs.keys():
            row[key] = self._get_field_value(key)
        # 如果字段为空且在 schema 中标记为 required，则使用 TableFieldSpec.default 作为导出值。
        for key, spec in self._field_specs.items():
            if getattr(spec, "required", False):
                val = row.get(key)
                if val is None or (isinstance(val, str) and val == ""):
                    # 仅在默认值明确存在时覆盖（允许默认为 0 或其他假值）
                    if getattr(spec, "default", None) is not None:
                        row[key] = spec.default
        return row

    def current_type(self) -> str:
        return _safe_text(self._type_label.text())

    def current_abbr(self) -> str:
        return _safe_text(self._abbr_edit.text())

    def shared_params(self) -> dict[str, object]:
        params = self._shared_params_provider()
        return params if isinstance(params, dict) else {}

    def build_main_table_insert_sql(self) -> str:
        """导出当前主表的单行 INSERT SQL。"""
        row = self.export_main_table_row()
        columns = [self._schema.type_key, *self._field_specs.keys()]
        values_sql = ", ".join(_sql_literal(row.get(col)) for col in columns)
        return (
            f"INSERT INTO {self._schema.table_name} ({', '.join(columns)}) VALUES\n"
            f"({values_sql});"
        )

    def _emit_data_changed(self) -> None:
        if self._internal_updating:
            return
        self._refresh_type_labels()
        self.dataChanged.emit()


class DistrictXP2SubTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._district_type = ""
        self._district_type_display = QLineEdit()
        self._district_type_display.setReadOnly(True)

        self._one_per_river = QCheckBox("OnePerRiver")
        self._prevents_floods = QCheckBox("PreventsFloods")
        self._prevents_drought = QCheckBox("PreventsDrought")
        self._canal = QCheckBox("Canal")
        self._attack_range = QSpinBox()
        self._attack_range.setRange(-999999, 999999)
        self._attack_range.setValue(0)
        _attach_hover_param_tooltip(self._attack_range, "AttackRange")
        for checkbox, param in (
            (self._one_per_river, "OnePerRiver"),
            (self._prevents_floods, "PreventsFloods"),
            (self._prevents_drought, "PreventsDrought"),
            (self._canal, "Canal"),
        ):
            _normalize_checkbox_caption(checkbox)
            _attach_hover_param_tooltip(checkbox, param)

        group = QGroupBox("Districts_XP2")
        group_layout = QVBoxLayout()
        tip = QLabel("XP2的参数")
        tip.setWordWrap(True)
        group_layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def _field_cell(label: str, widget: QWidget) -> QWidget:
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(110)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return container

        grid.addWidget(_field_cell("DistrictType", self._district_type_display), 0, 0)
        grid.addWidget(_field_cell("AttackRange", self._attack_range), 0, 1)
        grid.addWidget(_field_cell("OnePerRiver", self._one_per_river), 1, 0)
        grid.addWidget(_field_cell("PreventsFloods", self._prevents_floods), 1, 1)
        grid.addWidget(_field_cell("PreventsDrought", self._prevents_drought), 2, 0)
        grid.addWidget(_field_cell("Canal", self._canal), 2, 1)
        group_layout.addLayout(grid)
        group.setLayout(group_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)
        self.setLayout(layout)

        for cb in (self._one_per_river, self._prevents_floods, self._prevents_drought, self._canal):
            cb.stateChanged.connect(lambda _v: self.dataChanged.emit())
        self._attack_range.valueChanged.connect(lambda _v: self.dataChanged.emit())

    def set_district_type(self, district_type: str) -> None:
        self._district_type = _safe_text(district_type)
        self._district_type_display.setText(self._district_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        self._one_per_river.setChecked(bool(int(payload.get("OnePerRiver", 0) or 0)))
        self._prevents_floods.setChecked(bool(int(payload.get("PreventsFloods", 0) or 0)))
        self._prevents_drought.setChecked(bool(int(payload.get("PreventsDrought", 0) or 0)))
        self._canal.setChecked(bool(int(payload.get("Canal", 0) or 0)))
        try:
            self._attack_range.setValue(int(payload.get("AttackRange", 0) or 0))
        except (TypeError, ValueError):
            self._attack_range.setValue(0)

    def export_payload(self) -> dict[str, object]:
        return {
            "DistrictType": self._district_type,
            "OnePerRiver": 1 if self._one_per_river.isChecked() else 0,
            "PreventsFloods": 1 if self._prevents_floods.isChecked() else 0,
            "PreventsDrought": 1 if self._prevents_drought.isChecked() else 0,
            "Canal": 1 if self._canal.isChecked() else 0,
            "AttackRange": int(self._attack_range.value()),
        }


@dataclass(slots=True)
class _DistrictRowColumnSpec:
    key: str
    label: str
    kind: str  # template/int/real
    template_key: str | None = None


class _DistrictRowsTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, *, table_name: str, hint_text: str, columns: list[_DistrictRowColumnSpec]) -> None:
        super().__init__()
        self._district_type = ""
        self._columns = columns
        self._base_column_widths: list[int] = []

        group = QGroupBox(table_name)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(8, 6, 8, 6)
        group_layout.setSpacing(8)

        tip = QLabel(hint_text)
        tip.setWordWrap(True)
        group_layout.addWidget(tip)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("DistrictType"))
        self._district_type_display = QLineEdit()
        self._district_type_display.setReadOnly(True)
        top_row.addWidget(self._district_type_display, 1)
        self._add_button = QPushButton("＋ 添加行")
        self._add_button.clicked.connect(self._add_row)
        top_row.addWidget(self._add_button)
        group_layout.addLayout(top_row)

        self._table = QTableWidget(0, len(self._columns) + 1)
        headers = [item.label for item in self._columns] + ["操作"]
        self._table.setHorizontalHeaderLabels(headers)
        header = self._table.horizontalHeader()
        for col in range(len(self._columns)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(len(self._columns), QHeaderView.ResizeMode.Fixed)
        header.setMinimumSectionSize(72)
        self._table.setColumnWidth(len(self._columns), 56)
        self._init_header_width_policy(headers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        group_layout.addWidget(self._table, 1)
        group.setLayout(group_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)
        self.setLayout(layout)
        QTimer.singleShot(0, self._apply_proportional_column_widths)

    def _init_header_width_policy(self, headers: list[str]) -> None:
        metrics = QFontMetrics(self._table.horizontalHeader().font())
        self._base_column_widths = []
        for col, text in enumerate(headers[:-1]):
            header_width = metrics.horizontalAdvance(text) + 34
            base_width = 220 if col == 0 else 150
            width = max(base_width, header_width)
            self._base_column_widths.append(width)
        self._table.setMinimumWidth(0)
        self._apply_proportional_column_widths()

    def _apply_proportional_column_widths(self) -> None:
        if not self._base_column_widths:
            return
        op_col = len(self._columns)
        op_width = 56
        self._table.setColumnWidth(op_col, op_width)

        available = max(0, self._table.viewport().width() - op_width - 2)
        if available <= 0:
            return
        scaled = _fit_column_widths(self._base_column_widths, available, preferred_min=60)

        for col, width in enumerate(scaled):
            self._table.setColumnWidth(col, width)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_proportional_column_widths()

    def set_district_type(self, district_type: str) -> None:
        self._district_type = _safe_text(district_type)
        self._district_type_display.setText(self._district_type)

    def _create_cell_widget(self, spec: _DistrictRowColumnSpec, seed: dict[str, object] | None) -> QWidget:
        if spec.kind == "template" and spec.template_key:
            widget = build_template_widget(spec.template_key)
            if hasattr(widget, "set_label_text"):
                widget.set_label_text("")
            if seed and hasattr(widget, "set_current_value"):
                widget.set_current_value(_safe_text(seed.get(spec.key)) or None)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            widget.setMinimumWidth(220)
            return widget

        if spec.kind == "real":
            spin = _CompactDoubleSpinBox()
            spin.setRange(-999999.0, 999999.0)
            try:
                spin.setValue(float((seed or {}).get(spec.key, 0.0) or 0.0))
            except (TypeError, ValueError):
                spin.setValue(0.0)
            _attach_hover_param_tooltip(spin, spec.key)
            return spin

        spin = QSpinBox()
        spin.setRange(-999999, 999999)
        try:
            spin.setValue(int((seed or {}).get(spec.key, 0) or 0))
        except (TypeError, ValueError):
            spin.setValue(0)
        _attach_hover_param_tooltip(spin, spec.key)
        return spin

    def _add_row(self, seed: dict[str, object] | None = None) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, spec in enumerate(self._columns):
            cell_widget = self._create_cell_widget(spec, seed)
            self._table.setCellWidget(row, col, cell_widget)
            if isinstance(cell_widget, BaseTemplateWidget):
                cell_widget.dataChanged.connect(self.dataChanged.emit)
            elif isinstance(cell_widget, QSpinBox):
                cell_widget.valueChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(cell_widget, QDoubleSpinBox):
                cell_widget.valueChanged.connect(lambda _v: self.dataChanged.emit())

        del_btn = QPushButton("删")
        small_font = QFont(del_btn.font())
        small_font.setPointSize(max(8, small_font.pointSize() - 1))
        del_btn.setFont(small_font)
        del_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        del_btn.clicked.connect(lambda: self._remove_row_by_button(del_btn))

        self._table.setCellWidget(row, len(self._columns), del_btn)
        self._refresh_table_height()
        self.dataChanged.emit()

    def _remove_row_by_button(self, button: QPushButton) -> None:
        op_col = len(self._columns)
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, op_col) is button:
                self._table.removeRow(row)
                self._refresh_table_height()
                self.dataChanged.emit()
                return

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        self._table.setRowCount(0)
        for row in payload:
            if isinstance(row, dict):
                self._add_row(row)
        self._refresh_table_height()

    def _refresh_table_height(self) -> None:
        self._table.resizeRowsToContents()
        header_h = self._table.horizontalHeader().height()
        frame_h = self._table.frameWidth() * 2
        rows_h = 0
        for row in range(self._table.rowCount()):
            rows_h += self._table.rowHeight(row)
        min_rows = 1
        if self._table.rowCount() < min_rows:
            rows_h += self._table.verticalHeader().defaultSectionSize() * (min_rows - self._table.rowCount())
        self._table.setFixedHeight(header_h + rows_h + frame_h + 2)

    def export_payload(self) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for row in range(self._table.rowCount()):
            row_payload: dict[str, object] = {"DistrictType": self._district_type}
            skip_row = False
            for col, spec in enumerate(self._columns):
                widget = self._table.cellWidget(row, col)
                if isinstance(widget, BaseTemplateWidget):
                    value = _safe_text(_first_non_empty(widget.export_data()))
                elif isinstance(widget, QDoubleSpinBox):
                    value = float(widget.value())
                elif isinstance(widget, QSpinBox):
                    value = int(widget.value())
                else:
                    value = ""
                if col == 0 and _safe_text(value) == "":
                    skip_row = True
                row_payload[spec.key] = value
            if not skip_row:
                output.append(row_payload)
        return output


class DistrictReplacesSubTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._district_type = ""
        self._district_type_display = QLineEdit()
        self._district_type_display.setReadOnly(True)
        self._replaces_widget = build_template_widget("district_search_no_trait")
        if hasattr(self._replaces_widget, "set_label_text"):
            self._replaces_widget.set_label_text("")

        group = QGroupBox("DistrictReplaces")
        group_layout = QVBoxLayout()
        tip = QLabel("取代区域：设置该文明专属区域替代的区域")
        tip.setWordWrap(True)
        group_layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def _field_cell(label: str, widget: QWidget) -> QWidget:
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(140)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return container

        grid.addWidget(_field_cell("CivUniqueDistrictType", self._district_type_display), 0, 0)
        grid.addWidget(_field_cell("ReplacesDistrictType", self._replaces_widget), 0, 1)
        group_layout.addLayout(grid)
        group.setLayout(group_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)
        self.setLayout(layout)

        if hasattr(self._replaces_widget, "dataChanged"):
            self._replaces_widget.dataChanged.connect(self.dataChanged.emit)

    def set_district_type(self, district_type: str) -> None:
        self._district_type = _safe_text(district_type)
        self._district_type_display.setText(self._district_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        if hasattr(self._replaces_widget, "set_current_value"):
            self._replaces_widget.set_current_value(_safe_text(payload.get("ReplacesDistrictType")) or None)

    def export_payload(self) -> dict[str, object]:
        replaces_type = ""
        if isinstance(self._replaces_widget, BaseTemplateWidget):
            replaces_type = _safe_text(_first_non_empty(self._replaces_widget.export_data()))
        return {
            "CivUniqueDistrictType": self._district_type,
            "ReplacesDistrictType": replaces_type,
        }


class DistrictCompositeEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._loading = False
        self._shared_params_provider = shared_params_provider

        self._main_editor = MainTableEditor(
            schema=build_districts_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )
        self._xp2_editor = DistrictXP2SubTableEditor()
        self._gp_editor = _DistrictRowsTableEditor(
            table_name="District_GreatPersonPoints",
            hint_text="伟人点：为该区域配置每回合提供的伟人类型与点数。",
            columns=[
                _DistrictRowColumnSpec("GreatPersonClassType", "GreatPersonClassType", "template", "great_person_class"),
                _DistrictRowColumnSpec("PointsPerTurn", "PointsPerTurn", "int"),
            ],
        )
        self._citizen_yield_editor = _DistrictRowsTableEditor(
            table_name="District_CitizenYieldChanges",
            hint_text="公民产出：配置公民在该区域工作时的额外产出类型与数值。",
            columns=[
                _DistrictRowColumnSpec("YieldType", "YieldType", "template", "yield"),
                _DistrictRowColumnSpec("YieldChange", "YieldChange", "int"),
            ],
        )
        self._required_features_editor = _DistrictRowsTableEditor(
            table_name="District_RequiredFeatures",
            hint_text="地貌限制：仅允许在指定地貌上建造该区域。",
            columns=[
                _DistrictRowColumnSpec("FeatureType", "FeatureType", "template", "feature_all"),
            ],
        )
        self._trade_route_yields_editor = _DistrictRowsTableEditor(
            table_name="District_TradeRouteYields",
            hint_text="贸易路线产出：配置该区域作为起点/国内终点/国际终点时提供的额外产出。",
            columns=[
                _DistrictRowColumnSpec("YieldType", "YieldType", "template", "yield"),
                _DistrictRowColumnSpec("YieldChangeAsOrigin", "YieldChangeAsOrigin", "real"),
                _DistrictRowColumnSpec("YieldChangeAsDomesticDestination", "YieldChangeAsDomesticDestination", "real"),
                _DistrictRowColumnSpec("YieldChangeAsInternationalDestination", "YieldChangeAsInternationalDestination", "real"),
            ],
        )
        self._valid_terrains_editor = _DistrictRowsTableEditor(
            table_name="District_ValidTerrains",
            hint_text="地形限制：仅允许在指定地形上建造该区域。",
            columns=[
                _DistrictRowColumnSpec("TerrainType", "TerrainType", "template", "terrain"),
            ],
        )
        self._replaces_editor = DistrictReplacesSubTableEditor()
        self._adjacency_editor = AdjacencyEditorWidget(
            auto_context=AdjacencyAutoContext(),
            include_placeholder=False,
        )

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        self._xp2_editor.dataChanged.connect(self._emit_data_changed)
        self._gp_editor.dataChanged.connect(self._emit_data_changed)
        self._citizen_yield_editor.dataChanged.connect(self._emit_data_changed)
        self._required_features_editor.dataChanged.connect(self._emit_data_changed)
        self._trade_route_yields_editor.dataChanged.connect(self._emit_data_changed)
        self._valid_terrains_editor.dataChanged.connect(self._emit_data_changed)
        self._replaces_editor.dataChanged.connect(self._emit_data_changed)
        self._adjacency_editor.dataChanged.connect(self._emit_data_changed)

        def _top_cell(widget: QWidget) -> QWidget:
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(0)
            holder_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)
            holder_layout.addStretch(1)
            return holder

        def _pair_row(left: QWidget, right: QWidget) -> QWidget:
            row_holder = QWidget()
            row_layout = QHBoxLayout(row_holder)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(_top_cell(left), 1)
            row_layout.addWidget(_top_cell(right), 1)
            return row_holder

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)
        layout.addWidget(_pair_row(self._xp2_editor, self._replaces_editor))
        layout.addWidget(_pair_row(self._gp_editor, self._citizen_yield_editor))
        layout.addWidget(self._trade_route_yields_editor)
        layout.addWidget(_pair_row(self._required_features_editor, self._valid_terrains_editor))
        layout.addWidget(self._adjacency_editor)
        self.setLayout(layout)

    def _build_adjacency_context(self) -> AdjacencyAutoContext:
        shared = self._shared_params_provider() if callable(self._shared_params_provider) else {}
        prefix = _safe_text(shared.get("prefix")).upper()
        district_code = self._main_editor.current_abbr().upper()
        district_infix = ""
        try:
            infix = max(0, int(shared.get("infix", 0)))
            if infix > 0:
                district_infix = f"D{infix:04d}"
        except (TypeError, ValueError):
            district_infix = ""
        return AdjacencyAutoContext(prefix=prefix, district_code=district_code, district_infix=district_infix)

    def _sync_district_type(self) -> None:
        district_type = self._main_editor.current_type()
        self._xp2_editor.set_district_type(district_type)
        self._gp_editor.set_district_type(district_type)
        self._citizen_yield_editor.set_district_type(district_type)
        self._required_features_editor.set_district_type(district_type)
        self._trade_route_yields_editor.set_district_type(district_type)
        self._valid_terrains_editor.set_district_type(district_type)
        self._replaces_editor.set_district_type(district_type)
        self._adjacency_editor.set_auto_context(self._build_adjacency_context())

    def _handle_main_changed(self) -> None:
        self._sync_district_type()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_district_type()

        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
        xp2_payload = subtables.get("Districts_XP2") if isinstance(subtables.get("Districts_XP2"), dict) else None
        if xp2_payload is None:
            xp2_payload = entry.get("districts_xp2") if isinstance(entry.get("districts_xp2"), dict) else {}
        self._xp2_editor.set_payload(xp2_payload if isinstance(xp2_payload, dict) else {})

        gp_payload = subtables.get("District_GreatPersonPoints") if isinstance(subtables.get("District_GreatPersonPoints"), list) else None
        if gp_payload is None:
            gp_payload = entry.get("district_great_person_points") if isinstance(entry.get("district_great_person_points"), list) else []
        self._gp_editor.set_payload(gp_payload if isinstance(gp_payload, list) else [])

        citizen_payload = subtables.get("District_CitizenYieldChanges") if isinstance(subtables.get("District_CitizenYieldChanges"), list) else None
        if citizen_payload is None:
            citizen_payload = entry.get("district_citizen_yield_changes") if isinstance(entry.get("district_citizen_yield_changes"), list) else []
        self._citizen_yield_editor.set_payload(citizen_payload if isinstance(citizen_payload, list) else [])

        feature_payload = subtables.get("District_RequiredFeatures") if isinstance(subtables.get("District_RequiredFeatures"), list) else None
        if feature_payload is None:
            feature_payload = entry.get("district_required_features") if isinstance(entry.get("district_required_features"), list) else []
        self._required_features_editor.set_payload(feature_payload if isinstance(feature_payload, list) else [])

        trade_payload = subtables.get("District_TradeRouteYields") if isinstance(subtables.get("District_TradeRouteYields"), list) else None
        if trade_payload is None:
            trade_payload = entry.get("district_trade_route_yields") if isinstance(entry.get("district_trade_route_yields"), list) else []
        self._trade_route_yields_editor.set_payload(trade_payload if isinstance(trade_payload, list) else [])

        terrain_payload = subtables.get("District_ValidTerrains") if isinstance(subtables.get("District_ValidTerrains"), list) else None
        if terrain_payload is None:
            terrain_payload = entry.get("district_valid_terrains") if isinstance(entry.get("district_valid_terrains"), list) else []
        self._valid_terrains_editor.set_payload(terrain_payload if isinstance(terrain_payload, list) else [])

        replaces_payload = subtables.get("DistrictReplaces") if isinstance(subtables.get("DistrictReplaces"), dict) else None
        if replaces_payload is None:
            replaces_payload = entry.get("district_replaces") if isinstance(entry.get("district_replaces"), dict) else {}
        self._replaces_editor.set_payload(replaces_payload if isinstance(replaces_payload, dict) else {})

        adjacency_payload = subtables.get("District_Adjacencies") if isinstance(subtables.get("District_Adjacencies"), list) else None
        if adjacency_payload is None:
            adjacency_payload = entry.get("adjacencies") if isinstance(entry.get("adjacencies"), list) else []
        self._adjacency_editor.set_payload(adjacency_payload if isinstance(adjacency_payload, list) else [])

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()
        xp2 = self._xp2_editor.export_payload()
        gp_rows = self._gp_editor.export_payload()
        citizen_rows = self._citizen_yield_editor.export_payload()
        feature_rows = self._required_features_editor.export_payload()
        trade_rows = self._trade_route_yields_editor.export_payload()
        terrain_rows = self._valid_terrains_editor.export_payload()
        replaces_row = self._replaces_editor.export_payload()
        adjacency_rows = self._adjacency_editor.export_payload()
        payload["districts_xp2"] = xp2
        payload["district_great_person_points"] = gp_rows
        payload["district_citizen_yield_changes"] = citizen_rows
        payload["district_required_features"] = feature_rows
        payload["district_trade_route_yields"] = trade_rows
        payload["district_valid_terrains"] = terrain_rows
        payload["district_replaces"] = replaces_row
        payload["adjacencies"] = adjacency_rows
        payload["subtables"] = {
            "Districts_XP2": xp2,
            "District_GreatPersonPoints": gp_rows,
            "District_CitizenYieldChanges": citizen_rows,
            "District_RequiredFeatures": feature_rows,
            "District_TradeRouteYields": trade_rows,
            "District_ValidTerrains": terrain_rows,
            "DistrictReplaces": replaces_row,
            "District_Adjacencies": adjacency_rows,
        }
        return payload

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class BuildingsXP2SubTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._building_type = ""
        self._building_type_display = QLineEdit()
        self._building_type_display.setReadOnly(True)

        self._required_power = QSpinBox()
        self._required_power.setRange(0, 999999)
        self._resource_type_to_power = build_template_widget("resource_strategic")
        if hasattr(self._resource_type_to_power, "set_label_text"):
            self._resource_type_to_power.set_label_text("")

        self._prevents_floods = QCheckBox("PreventsFloods")
        self._prevents_drought = QCheckBox("PreventsDrought")
        self._blocks_coastal_flooding = QCheckBox("BlocksCoastalFlooding")
        self._bridge = QCheckBox("Bridge")
        self._canal_wonder = QCheckBox("CanalWonder")
        self._nuclear_reactor = QCheckBox("NuclearReactor")
        self._pillage = QCheckBox("Pillage")
        self._pillage.setChecked(True)

        self._cost_mul_tile = QSpinBox()
        self._cost_mul_tile.setRange(0, 999999)
        self._cost_mul_sea = QSpinBox()
        self._cost_mul_sea.setRange(0, 999999)
        self._ent_bonus_with_power = QSpinBox()
        self._ent_bonus_with_power.setRange(0, 999999)
        _attach_hover_param_tooltip(self._required_power, "RequiredPower")
        _attach_hover_param_tooltip(self._cost_mul_tile, "CostMultiplierPerTile")
        _attach_hover_param_tooltip(self._cost_mul_sea, "CostMultiplierPerSeaLevel")
        _attach_hover_param_tooltip(self._ent_bonus_with_power, "EntertainmentBonusWithPower")
        for checkbox, param in (
            (self._prevents_floods, "PreventsFloods"),
            (self._prevents_drought, "PreventsDrought"),
            (self._blocks_coastal_flooding, "BlocksCoastalFlooding"),
            (self._bridge, "Bridge"),
            (self._canal_wonder, "CanalWonder"),
            (self._nuclear_reactor, "NuclearReactor"),
            (self._pillage, "Pillage"),
        ):
            _normalize_checkbox_caption(checkbox)
            _attach_hover_param_tooltip(checkbox, param)

        group = QGroupBox("Buildings_XP2")
        layout = QVBoxLayout(group)
        tip = QLabel(_building_table_hint("Buildings_XP2"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(120)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "BuildingType"), fallback_key="BuildingType"), self._building_type_display), 0, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "RequiredPower"), fallback_key="RequiredPower"), self._required_power), 0, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "ResourceTypeConvertedToPower"), fallback_key="ResourceTypeConvertedToPower"), self._resource_type_to_power), 1, 0, 1, 2)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "CostMultiplierPerTile"), fallback_key="CostMultiplierPerTile"), self._cost_mul_tile), 2, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "CostMultiplierPerSeaLevel"), fallback_key="CostMultiplierPerSeaLevel"), self._cost_mul_sea), 2, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "EntertainmentBonusWithPower"), fallback_key="EntertainmentBonusWithPower"), self._ent_bonus_with_power), 3, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "PreventsFloods"), fallback_key="PreventsFloods"), self._prevents_floods), 4, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "PreventsDrought"), fallback_key="PreventsDrought"), self._prevents_drought), 4, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "BlocksCoastalFlooding"), fallback_key="BlocksCoastalFlooding"), self._blocks_coastal_flooding), 5, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "Bridge"), fallback_key="Bridge"), self._bridge), 5, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "CanalWonder"), fallback_key="CanalWonder"), self._canal_wonder), 6, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "NuclearReactor"), fallback_key="NuclearReactor"), self._nuclear_reactor), 6, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("Buildings_XP2", "Pillage"), fallback_key="Pillage"), self._pillage), 7, 0)

        layout.addLayout(grid)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        for cb in (
            self._prevents_floods,
            self._prevents_drought,
            self._blocks_coastal_flooding,
            self._bridge,
            self._canal_wonder,
            self._nuclear_reactor,
            self._pillage,
        ):
            cb.stateChanged.connect(lambda _v: self.dataChanged.emit())
        self._required_power.valueChanged.connect(lambda _v: self.dataChanged.emit())
        self._cost_mul_tile.valueChanged.connect(lambda _v: self.dataChanged.emit())
        self._cost_mul_sea.valueChanged.connect(lambda _v: self.dataChanged.emit())
        self._ent_bonus_with_power.valueChanged.connect(lambda _v: self.dataChanged.emit())
        if hasattr(self._resource_type_to_power, "dataChanged"):
            self._resource_type_to_power.dataChanged.connect(self.dataChanged.emit)

    def set_building_type(self, building_type: str) -> None:
        self._building_type = _safe_text(building_type)
        self._building_type_display.setText(self._building_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        self._required_power.setValue(int(payload.get("RequiredPower", 0) or 0))
        if hasattr(self._resource_type_to_power, "set_current_value"):
            self._resource_type_to_power.set_current_value(_safe_text(payload.get("ResourceTypeConvertedToPower")) or None)
        self._prevents_floods.setChecked(bool(int(payload.get("PreventsFloods", 0) or 0)))
        self._prevents_drought.setChecked(bool(int(payload.get("PreventsDrought", 0) or 0)))
        self._blocks_coastal_flooding.setChecked(bool(int(payload.get("BlocksCoastalFlooding", 0) or 0)))
        self._cost_mul_tile.setValue(int(payload.get("CostMultiplierPerTile", 0) or 0))
        self._cost_mul_sea.setValue(int(payload.get("CostMultiplierPerSeaLevel", 0) or 0))
        self._bridge.setChecked(bool(int(payload.get("Bridge", 0) or 0)))
        self._canal_wonder.setChecked(bool(int(payload.get("CanalWonder", 0) or 0)))
        self._ent_bonus_with_power.setValue(int(payload.get("EntertainmentBonusWithPower", 0) or 0))
        self._nuclear_reactor.setChecked(bool(int(payload.get("NuclearReactor", 0) or 0)))
        self._pillage.setChecked(bool(int(payload.get("Pillage", 1) or 1)))

    def export_payload(self) -> dict[str, object]:
        resource_type = ""
        if isinstance(self._resource_type_to_power, BaseTemplateWidget):
            resource_type = _safe_text(_first_non_empty(self._resource_type_to_power.export_data()))
        return {
            "BuildingType": self._building_type,
            "RequiredPower": int(self._required_power.value()),
            "ResourceTypeConvertedToPower": resource_type,
            "PreventsFloods": 1 if self._prevents_floods.isChecked() else 0,
            "PreventsDrought": 1 if self._prevents_drought.isChecked() else 0,
            "BlocksCoastalFlooding": 1 if self._blocks_coastal_flooding.isChecked() else 0,
            "CostMultiplierPerTile": int(self._cost_mul_tile.value()),
            "CostMultiplierPerSeaLevel": int(self._cost_mul_sea.value()),
            "Bridge": 1 if self._bridge.isChecked() else 0,
            "CanalWonder": 1 if self._canal_wonder.isChecked() else 0,
            "EntertainmentBonusWithPower": int(self._ent_bonus_with_power.value()),
            "NuclearReactor": 1 if self._nuclear_reactor.isChecked() else 0,
            "Pillage": 1 if self._pillage.isChecked() else 0,
        }


@dataclass(slots=True)
class _BuildingRowColumnSpec:
    key: str
    label: str
    kind: str  # template/int/real/bool/text
    template_key: str | None = None


class _BuildingRowsTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, *, table_name: str, hint_text: str, columns: list[_BuildingRowColumnSpec]) -> None:
        super().__init__()
        self._building_type = ""
        self._columns = columns
        self._base_column_widths: list[int] = []

        group = QGroupBox(table_name)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(8, 6, 8, 6)
        group_layout.setSpacing(8)
        tip = QLabel(hint_text)
        tip.setWordWrap(True)
        group_layout.addWidget(tip)

        top = QHBoxLayout()
        top.addWidget(QLabel("BuildingType"))
        self._building_type_display = QLineEdit()
        self._building_type_display.setReadOnly(True)
        top.addWidget(self._building_type_display, 1)
        self._add_btn = QPushButton("＋ 添加行")
        self._add_btn.clicked.connect(self._add_row)
        top.addWidget(self._add_btn)
        group_layout.addLayout(top)

        self._table = QTableWidget(0, len(self._columns) + 1)
        self._table.setHorizontalHeaderLabels([item.label for item in self._columns] + ["Action"])
        header = self._table.horizontalHeader()
        for col in range(len(self._columns)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(len(self._columns), QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(len(self._columns), 56)
        header.setMinimumSectionSize(72)
        self._init_header_width_policy([item.label for item in self._columns])
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        group_layout.addWidget(self._table)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)
        QTimer.singleShot(0, self._apply_proportional_column_widths)

    def _init_header_width_policy(self, headers: list[str]) -> None:
        metrics = QFontMetrics(self._table.horizontalHeader().font())
        self._base_column_widths = []
        for col, text in enumerate(headers):
            header_width = metrics.horizontalAdvance(text) + 34
            base_width = 200 if col == 0 else 150
            self._base_column_widths.append(max(base_width, header_width))
        self._apply_proportional_column_widths()

    def _apply_proportional_column_widths(self) -> None:
        if not self._base_column_widths:
            return
        op_col = len(self._columns)
        op_width = 56
        self._table.setColumnWidth(op_col, op_width)

        available = max(0, self._table.viewport().width() - op_width - 2)
        if available <= 0:
            return
        scaled = _fit_column_widths(self._base_column_widths, available, preferred_min=60)

        for col, width in enumerate(scaled):
            self._table.setColumnWidth(col, width)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_proportional_column_widths()

    def set_building_type(self, building_type: str) -> None:
        self._building_type = _safe_text(building_type)
        self._building_type_display.setText(self._building_type)

    def _create_cell_widget(self, spec: _BuildingRowColumnSpec, seed: dict[str, object] | None) -> QWidget:
        if spec.kind == "template" and spec.template_key:
            widget = build_template_widget(spec.template_key)
            if hasattr(widget, "set_label_text"):
                widget.set_label_text("")
            if seed and hasattr(widget, "set_current_value"):
                widget.set_current_value(_safe_text(seed.get(spec.key)) or None)
            return widget
        if spec.kind == "real":
            spin = _CompactDoubleSpinBox()
            spin.setRange(-999999.0, 999999.0)
            spin.setValue(float((seed or {}).get(spec.key, 0.0) or 0.0))
            _attach_hover_param_tooltip(spin, spec.key)
            return spin
        if spec.kind == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(int((seed or {}).get(spec.key, 0) or 0)))
            _normalize_checkbox_caption(cb)
            _attach_hover_param_tooltip(cb, spec.key)
            return cb
        if spec.kind == "text":
            edit = QLineEdit()
            edit.setText(_safe_text((seed or {}).get(spec.key)))
            return edit
        spin = QSpinBox()
        spin.setRange(-999999, 999999)
        spin.setValue(int((seed or {}).get(spec.key, 0) or 0))
        _attach_hover_param_tooltip(spin, spec.key)
        return spin

    def _add_row(self, seed: dict[str, object] | None = None) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, spec in enumerate(self._columns):
            widget = self._create_cell_widget(spec, seed)
            self._table.setCellWidget(row, col, widget)
            if isinstance(widget, BaseTemplateWidget):
                widget.dataChanged.connect(self.dataChanged.emit)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _t: self.dataChanged.emit())

        btn = QPushButton("删")
        btn.clicked.connect(lambda: self._remove_row(btn))
        self._table.setCellWidget(row, len(self._columns), btn)
        self._refresh_table_height()
        self.dataChanged.emit()

    def _remove_row(self, button: QPushButton) -> None:
        op_col = len(self._columns)
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, op_col) is button:
                self._table.removeRow(row)
                self._refresh_table_height()
                self.dataChanged.emit()
                return

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        self._table.setRowCount(0)
        for row in payload:
            if isinstance(row, dict):
                self._add_row(row)
        self._refresh_table_height()

    def _refresh_table_height(self) -> None:
        self._table.resizeRowsToContents()
        header_h = self._table.horizontalHeader().height()
        frame_h = self._table.frameWidth() * 2
        rows_h = sum(self._table.rowHeight(r) for r in range(self._table.rowCount()))
        min_rows = 1
        if self._table.rowCount() < min_rows:
            rows_h += self._table.verticalHeader().defaultSectionSize() * (min_rows - self._table.rowCount())
        self._table.setFixedHeight(header_h + rows_h + frame_h + 2)

    def export_payload(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in range(self._table.rowCount()):
            payload: dict[str, object] = {"BuildingType": self._building_type}
            empty_first = False
            for col, spec in enumerate(self._columns):
                widget = self._table.cellWidget(row, col)
                value: object = ""
                if isinstance(widget, BaseTemplateWidget):
                    value = _safe_text(_first_non_empty(widget.export_data()))
                elif isinstance(widget, QSpinBox):
                    value = int(widget.value())
                elif isinstance(widget, QDoubleSpinBox):
                    value = float(widget.value())
                elif isinstance(widget, QCheckBox):
                    value = 1 if widget.isChecked() else 0
                elif isinstance(widget, QLineEdit):
                    value = _safe_text(widget.text())
                if col == 0 and _safe_text(value) == "":
                    empty_first = True
                payload[spec.key] = value
            if not empty_first:
                rows.append(payload)
        return rows


class BuildingReplacesSubTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._building_type = ""
        self._building_type_display = QLineEdit()
        self._building_type_display.setReadOnly(True)
        self._replaces_widget = build_template_widget("building_search_no_trait")
        if hasattr(self._replaces_widget, "set_label_text"):
            self._replaces_widget.set_label_text("")

        group = QGroupBox("BuildingReplaces")
        layout = QVBoxLayout(group)
        tip = QLabel(_building_table_hint("BuildingReplaces"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()
        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(120)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("BuildingReplaces", "CivUniqueBuildingType"), fallback_key="CivUniqueBuildingType"), self._building_type_display), 0, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("BuildingReplaces", "ReplacesBuildingType"), fallback_key="ReplacesBuildingType"), self._replaces_widget), 0, 1)
        layout.addLayout(grid)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        if hasattr(self._replaces_widget, "dataChanged"):
            self._replaces_widget.dataChanged.connect(self.dataChanged.emit)

    def set_building_type(self, building_type: str) -> None:
        self._building_type = _safe_text(building_type)
        self._building_type_display.setText(self._building_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        if hasattr(self._replaces_widget, "set_current_value"):
            self._replaces_widget.set_current_value(_safe_text(payload.get("ReplacesBuildingType")) or None)

    def export_payload(self) -> dict[str, object]:
        replaces_type = ""
        if isinstance(self._replaces_widget, BaseTemplateWidget):
            replaces_type = _safe_text(_first_non_empty(self._replaces_widget.export_data()))
        return {
            "CivUniqueBuildingType": self._building_type,
            "ReplacesBuildingType": replaces_type,
        }


class BuildingConditionsSingleEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._building_type = ""
        self._building_type_display = QLineEdit()
        self._building_type_display.setReadOnly(True)
        self._unlocks_from_effect = QCheckBox("UnlocksFromEffect")
        _normalize_checkbox_caption(self._unlocks_from_effect)
        _attach_hover_param_tooltip(self._unlocks_from_effect, "UnlocksFromEffect")

        group = QGroupBox("BuildingConditions")
        layout = QVBoxLayout(group)
        tip = QLabel(_building_table_hint("BuildingConditions"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(180)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("BuildingConditions", "BuildingType"), fallback_key="BuildingType"), self._building_type_display), 0, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_building_param_zh("BuildingConditions", "UnlocksFromEffect"), fallback_key="UnlocksFromEffect"), self._unlocks_from_effect), 0, 1)
        layout.addLayout(grid)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        self._unlocks_from_effect.stateChanged.connect(lambda _v: self.dataChanged.emit())

    def set_building_type(self, building_type: str) -> None:
        self._building_type = _safe_text(building_type)
        self._building_type_display.setText(self._building_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        self._unlocks_from_effect.setChecked(bool(int(payload.get("UnlocksFromEffect", 0) or 0)))

    def export_payload(self) -> dict[str, object]:
        return {
            "BuildingType": self._building_type,
            "UnlocksFromEffect": 1 if self._unlocks_from_effect.isChecked() else 0,
        }


class BuildingGreatWorksEditor(QWidget):
    dataChanged = pyqtSignal()

    _SLOTS = [
        "GREATWORKSLOT_WRITING",
        "GREATWORKSLOT_ART",
        "GREATWORKSLOT_MUSIC",
        "GREATWORKSLOT_ARTIFACT",
        "GREATWORKSLOT_RELIC",
        "GREATWORKSLOT_CATHEDRAL",
        "GREATWORKSLOT_PALACE",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._building_type = ""

        group = QGroupBox("Building_GreatWorks")
        group_layout = QVBoxLayout(group)
        tip = QLabel(_building_table_hint("Building_GreatWorks"))
        tip.setWordWrap(True)
        group_layout.addWidget(tip)

        top = QHBoxLayout()
        top.addWidget(QLabel("BuildingType"))
        self._building_type_display = QLineEdit()
        self._building_type_display.setReadOnly(True)
        top.addWidget(self._building_type_display, 1)
        self._add_btn = QPushButton("＋ 添加槽位")
        self._add_btn.clicked.connect(self._add_row)
        top.addWidget(self._add_btn)
        group_layout.addLayout(top)

        self._rows_holder = QVBoxLayout()
        self._rows_holder.setContentsMargins(0, 0, 0, 0)
        self._rows_holder.setSpacing(8)
        group_layout.addLayout(self._rows_holder)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        self._rows: list[dict[str, object]] = []

    def set_building_type(self, building_type: str) -> None:
        self._building_type = _safe_text(building_type)
        self._building_type_display.setText(self._building_type)

    def _make_hint_text(self, slot: str, yield_mul: int, tourism_mul: int, uniq_person: bool, same_obj: bool, uniq_civs: bool, same_eras: bool) -> str:
        actor = "创作者"
        obj_name = "巨作"
        if slot in {"GREATWORKSLOT_ART", "GREATWORKSLOT_CATHEDRAL"}:
            actor, obj_name = "艺术家", "作品"
        elif slot == "GREATWORKSLOT_WRITING":
            actor, obj_name = "作家", "著作"
        elif slot == "GREATWORKSLOT_MUSIC":
            actor, obj_name = "音乐家", "音乐作品"
        elif slot == "GREATWORKSLOT_ARTIFACT":
            actor, obj_name = "", "文物"
        elif slot == "GREATWORKSLOT_RELIC":
            actor, obj_name = "", "遗物"

        origin_parts: list[str] = []
        if actor:
            origin_parts.append(f"不同{actor}" if uniq_person else actor)
        if uniq_civs:
            origin_parts.append("不同文明")

        qualifier_parts: list[str] = []
        if same_eras:
            qualifier_parts.append("相同时代")
        if same_obj:
            qualifier_parts.append("相同类型")

        mul_parts: list[str] = []
        if yield_mul == tourism_mul and yield_mul >= 2:
            mul_parts.append("主题加成翻倍" if yield_mul == 2 else f"主题加成翻{yield_mul}倍")
        else:
            if yield_mul >= 2:
                mul_parts.append("主题产出翻倍" if yield_mul == 2 else f"主题产出翻{yield_mul}倍")
            if tourism_mul >= 2:
                mul_parts.append("主题旅游翻倍" if tourism_mul == 2 else f"主题旅游翻{tourism_mul}倍")
        if not mul_parts:
            return "当前未设置有效主题倍率。"

        target = ("".join(qualifier_parts) + "的" if qualifier_parts else "") + obj_name
        origin = "来自" + "".join(origin_parts) if origin_parts else ""
        body = origin + target if origin else target
        return f"当展示{body}时，{'，'.join(mul_parts)}。"

    def _add_row(self, seed: dict[str, object] | None = None) -> None:
        card = QGroupBox("槽位条目")
        card_layout = QVBoxLayout(card)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("GreatWorkSlotType（槽位类型）"))
        slot_combo = QComboBox()
        slot_combo.setEditable(True)
        slot_combo.addItems(self._SLOTS)
        slot_combo.setCurrentText(_safe_text((seed or {}).get("GreatWorkSlotType")) or self._SLOTS[0])
        row1.addWidget(slot_combo, 1)
        row1.addWidget(QLabel("NumSlots（槽位数量）"))
        num_slots = QSpinBox()
        num_slots.setRange(1, 20)
        num_slots.setValue(int((seed or {}).get("NumSlots", 1) or 1))
        row1.addWidget(num_slots)
        delete_btn = QPushButton("删除")
        row1.addWidget(delete_btn)
        card_layout.addLayout(row1)

        row2 = QHBoxLayout()
        unique_person = QCheckBox(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingUniquePerson"), fallback_key="ThemingUniquePerson"))
        unique_person.setChecked(bool(int((seed or {}).get("ThemingUniquePerson", 0) or 0)))
        same_object = QCheckBox(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingSameObjectType"), fallback_key="ThemingSameObjectType"))
        same_object.setChecked(bool(int((seed or {}).get("ThemingSameObjectType", 0) or 0)))
        unique_civs = QCheckBox(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingUniqueCivs"), fallback_key="ThemingUniqueCivs"))
        unique_civs.setChecked(bool(int((seed or {}).get("ThemingUniqueCivs", 0) or 0)))
        same_eras = QCheckBox(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingSameEras"), fallback_key="ThemingSameEras"))
        same_eras.setChecked(bool(int((seed or {}).get("ThemingSameEras", 0) or 0)))
        _attach_hover_param_tooltip(unique_person, "ThemingUniquePerson")
        _attach_hover_param_tooltip(same_object, "ThemingSameObjectType")
        _attach_hover_param_tooltip(unique_civs, "ThemingUniqueCivs")
        _attach_hover_param_tooltip(same_eras, "ThemingSameEras")
        row2.addWidget(unique_person)
        row2.addWidget(same_object)
        row2.addWidget(unique_civs)
        row2.addWidget(same_eras)
        card_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingYieldMultiplier"), fallback_key="ThemingYieldMultiplier")))
        yield_mul = QSpinBox()
        yield_mul.setRange(0, 999)
        yield_mul.setValue(int((seed or {}).get("ThemingYieldMultiplier", 0) or 0))
        _attach_hover_param_tooltip(yield_mul, "ThemingYieldMultiplier")
        row3.addWidget(yield_mul)
        row3.addWidget(QLabel(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingTourismMultiplier"), fallback_key="ThemingTourismMultiplier")))
        tourism_mul = QSpinBox()
        tourism_mul.setRange(0, 999)
        tourism_mul.setValue(int((seed or {}).get("ThemingTourismMultiplier", 0) or 0))
        _attach_hover_param_tooltip(tourism_mul, "ThemingTourismMultiplier")
        row3.addWidget(tourism_mul)
        row3.addWidget(QLabel(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "NonUniquePersonYield"), fallback_key="NonUniquePersonYield")))
        non_unique_yield = QSpinBox()
        non_unique_yield.setRange(0, 999)
        non_unique_yield.setValue(int((seed or {}).get("NonUniquePersonYield", 0) or 0))
        _attach_hover_param_tooltip(non_unique_yield, "NonUniquePersonYield")
        row3.addWidget(non_unique_yield)
        row3.addWidget(QLabel(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "NonUniquePersonTourism"), fallback_key="NonUniquePersonTourism")))
        non_unique_tour = QSpinBox()
        non_unique_tour.setRange(0, 999)
        non_unique_tour.setValue(int((seed or {}).get("NonUniquePersonTourism", 0) or 0))
        _attach_hover_param_tooltip(non_unique_tour, "NonUniquePersonTourism")
        row3.addWidget(non_unique_tour)
        card_layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel(_param_display_text(zh_text=_building_param_zh("Building_GreatWorks", "ThemingBonusDescription"), fallback_key="ThemingBonusDescription")))
        desc_edit = QLineEdit()
        desc_edit.setText(_safe_text((seed or {}).get("ThemingBonusDescriptionText") or (seed or {}).get("ThemingBonusDescription")))
        row4.addWidget(desc_edit, 1)
        fill_btn = QPushButton("自动填入")
        row4.addWidget(fill_btn)
        card_layout.addLayout(row4)

        hint = QLabel("参考：")
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        item = {
            "card": card,
            "slot": slot_combo,
            "num": num_slots,
            "u_person": unique_person,
            "s_obj": same_object,
            "u_civs": unique_civs,
            "s_eras": same_eras,
            "yield_mul": yield_mul,
            "tour_mul": tourism_mul,
            "nu_yield": non_unique_yield,
            "nu_tour": non_unique_tour,
            "desc": desc_edit,
            "hint": hint,
        }

        def _update_hint() -> None:
            hint.setText(
                "参考："
                + self._make_hint_text(
                    slot_combo.currentText().strip(),
                    int(yield_mul.value()),
                    int(tourism_mul.value()),
                    unique_person.isChecked(),
                    same_object.isChecked(),
                    unique_civs.isChecked(),
                    same_eras.isChecked(),
                )
            )

        def _remove() -> None:
            self._rows = [entry for entry in self._rows if entry is not item]
            card.setParent(None)
            card.deleteLater()
            self.dataChanged.emit()

        def _fill_desc() -> None:
            desc_edit.setText(hint.text().replace("参考：", "", 1).strip())

        delete_btn.clicked.connect(_remove)
        fill_btn.clicked.connect(_fill_desc)
        slot_combo.currentTextChanged.connect(lambda _t: (_update_hint(), self.dataChanged.emit()))
        desc_edit.textChanged.connect(lambda _t: self.dataChanged.emit())
        for widget in (num_slots, yield_mul, tourism_mul, non_unique_yield, non_unique_tour):
            widget.valueChanged.connect(lambda _v: (_update_hint(), self.dataChanged.emit()))
        for widget in (unique_person, same_object, unique_civs, same_eras):
            widget.stateChanged.connect(lambda _v: (_update_hint(), self.dataChanged.emit()))

        _update_hint()
        self._rows.append(item)
        self._rows_holder.addWidget(card)
        self.dataChanged.emit()

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        for row in list(self._rows):
            card = row.get("card")
            if isinstance(card, QWidget):
                card.setParent(None)
                card.deleteLater()
        self._rows = []
        for row in payload:
            if isinstance(row, dict):
                self._add_row(row)

    def export_payload(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        seen_slots: set[str] = set()
        for row in self._rows:
            slot_combo = row.get("slot")
            if not isinstance(slot_combo, QComboBox):
                continue
            slot = _safe_text(slot_combo.currentText()).upper()
            if not slot or slot in seen_slots:
                continue
            seen_slots.add(slot)

            num_widget = row.get("num")
            u_person = row.get("u_person")
            s_obj = row.get("s_obj")
            u_civs = row.get("u_civs")
            s_eras = row.get("s_eras")
            y_mul = row.get("yield_mul")
            t_mul = row.get("tour_mul")
            nu_y = row.get("nu_yield")
            nu_t = row.get("nu_tour")
            desc = row.get("desc")
            desc_text = _safe_text(desc.text()) if isinstance(desc, QLineEdit) else ""
            theming_loc = f"LOC_{self._building_type}_{_greatwork_slot_short(slot)}_THEMING" if desc_text else ""

            rows.append(
                {
                    "BuildingType": self._building_type,
                    "GreatWorkSlotType": slot,
                    "NumSlots": int(num_widget.value()) if isinstance(num_widget, QSpinBox) else 1,
                    "ThemingUniquePerson": 1 if isinstance(u_person, QCheckBox) and u_person.isChecked() else 0,
                    "ThemingSameObjectType": 1 if isinstance(s_obj, QCheckBox) and s_obj.isChecked() else 0,
                    "ThemingUniqueCivs": 1 if isinstance(u_civs, QCheckBox) and u_civs.isChecked() else 0,
                    "ThemingSameEras": 1 if isinstance(s_eras, QCheckBox) and s_eras.isChecked() else 0,
                    "ThemingYieldMultiplier": int(y_mul.value()) if isinstance(y_mul, QSpinBox) else 0,
                    "ThemingTourismMultiplier": int(t_mul.value()) if isinstance(t_mul, QSpinBox) else 0,
                    "NonUniquePersonYield": int(nu_y.value()) if isinstance(nu_y, QSpinBox) else 0,
                    "NonUniquePersonTourism": int(nu_t.value()) if isinstance(nu_t, QSpinBox) else 0,
                    "ThemingBonusDescription": theming_loc,
                    "ThemingBonusDescriptionText": desc_text,
                }
            )
        return rows


class BuildingCompositeEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._loading = False

        self._main_editor = MainTableEditor(
            schema=build_buildings_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )

        self._xp2_editor = BuildingsXP2SubTableEditor()
        self._replaces_editor = BuildingReplacesSubTableEditor()
        self._prereqs_editor = _BuildingRowsTableEditor(
            table_name="BuildingPrereqs",
            hint_text=_building_table_hint("BuildingPrereqs"),
            columns=[_BuildingRowColumnSpec("PrereqBuilding", "PrereqBuilding", "template", "building_search_all")],
        )
        self._citizen_yield_editor = _BuildingRowsTableEditor(
            table_name="Building_CitizenYieldChanges",
            hint_text=_building_table_hint("Building_CitizenYieldChanges"),
            columns=[
                _BuildingRowColumnSpec("YieldType", "YieldType", "template", "yield"),
                _BuildingRowColumnSpec("YieldChange", "YieldChange", "int"),
            ],
        )
        self._gp_editor = _BuildingRowsTableEditor(
            table_name="Building_GreatPersonPoints",
            hint_text=_building_table_hint("Building_GreatPersonPoints"),
            columns=[
                _BuildingRowColumnSpec("GreatPersonClassType", "GreatPersonClassType", "template", "great_person_class"),
                _BuildingRowColumnSpec("PointsPerTurn", "PointsPerTurn", "int"),
            ],
        )
        self._required_features_editor = _BuildingRowsTableEditor(
            table_name="Building_RequiredFeatures",
            hint_text=_building_table_hint("Building_RequiredFeatures"),
            columns=[_BuildingRowColumnSpec("FeatureType", "FeatureType", "template", "feature_all")],
        )
        self._tourism_bombs_editor = _BuildingRowsTableEditor(
            table_name="Building_TourismBombs_XP2",
            hint_text=_building_table_hint("Building_TourismBombs_XP2"),
            columns=[_BuildingRowColumnSpec("TourismBombValue", "TourismBombValue", "int")],
        )
        self._resource_costs_editor = _BuildingRowsTableEditor(
            table_name="Building_ResourceCosts",
            hint_text=_building_table_hint("Building_ResourceCosts"),
            columns=[
                _BuildingRowColumnSpec("ResourceType", "ResourceType", "template", "resource_strategic"),
                _BuildingRowColumnSpec("StartProductionCost", "StartProductionCost", "int"),
                _BuildingRowColumnSpec("PerTurnMaintenanceCost", "PerTurnMaintenanceCost", "int"),
            ],
        )
        self._valid_features_editor = _BuildingRowsTableEditor(
            table_name="Building_ValidFeatures",
            hint_text=_building_table_hint("Building_ValidFeatures"),
            columns=[_BuildingRowColumnSpec("FeatureType", "FeatureType", "template", "feature_all")],
        )
        self._valid_terrains_editor = _BuildingRowsTableEditor(
            table_name="Building_ValidTerrains",
            hint_text=_building_table_hint("Building_ValidTerrains"),
            columns=[_BuildingRowColumnSpec("TerrainType", "TerrainType", "template", "terrain")],
        )
        self._yield_changes_editor = _BuildingRowsTableEditor(
            table_name="Building_YieldChanges",
            hint_text=_building_table_hint("Building_YieldChanges"),
            columns=[
                _BuildingRowColumnSpec("YieldType", "YieldType", "template", "yield"),
                _BuildingRowColumnSpec("YieldChange", "YieldChange", "int"),
            ],
        )
        self._yield_power_editor = _BuildingRowsTableEditor(
            table_name="Building_YieldChangesBonusWithPower",
            hint_text=_building_table_hint("Building_YieldChangesBonusWithPower"),
            columns=[
                _BuildingRowColumnSpec("YieldType", "YieldType", "template", "yield"),
                _BuildingRowColumnSpec("YieldChange", "YieldChange", "int"),
            ],
        )
        self._yield_district_copies_editor = _BuildingRowsTableEditor(
            table_name="Building_YieldDistrictCopies",
            hint_text=_building_table_hint("Building_YieldDistrictCopies"),
            columns=[
                _BuildingRowColumnSpec("OldYieldType", "OldYieldType", "template", "yield"),
                _BuildingRowColumnSpec("NewYieldType", "NewYieldType", "template", "yield"),
            ],
        )
        self._yields_per_era_editor = _BuildingRowsTableEditor(
            table_name="Building_YieldsPerEra",
            hint_text=_building_table_hint("Building_YieldsPerEra"),
            columns=[
                _BuildingRowColumnSpec("YieldType", "YieldType", "template", "yield"),
                _BuildingRowColumnSpec("YieldChange", "YieldChange", "int"),
            ],
        )
        self._conditions_editor = BuildingConditionsSingleEditor()
        self._build_charge_prod_editor = _BuildingRowsTableEditor(
            table_name="Building_BuildChargeProductions",
            hint_text=_building_table_hint("Building_BuildChargeProductions"),
            columns=[
                _BuildingRowColumnSpec("UnitType", "UnitType", "template", "unit_search"),
                _BuildingRowColumnSpec("PercentProductionPerCharge", "PercentProductionPerCharge", "int"),
            ],
        )
        self._greatworks_editor = BuildingGreatWorksEditor()

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        for editor in (
            self._xp2_editor,
            self._replaces_editor,
            self._prereqs_editor,
            self._citizen_yield_editor,
            self._gp_editor,
            self._required_features_editor,
            self._tourism_bombs_editor,
            self._resource_costs_editor,
            self._valid_features_editor,
            self._valid_terrains_editor,
            self._yield_changes_editor,
            self._yield_power_editor,
            self._yield_district_copies_editor,
            self._yields_per_era_editor,
            self._conditions_editor,
            self._build_charge_prod_editor,
            self._greatworks_editor,
        ):
            editor.dataChanged.connect(self._emit_data_changed)

        def _top_cell(widget: QWidget) -> QWidget:
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(0)
            holder_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)
            holder_layout.addStretch(1)
            return holder

        def _pair_row(left: QWidget, right: QWidget) -> QWidget:
            row_holder = QWidget()
            row_layout = QHBoxLayout(row_holder)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(_top_cell(left), 1)
            row_layout.addWidget(_top_cell(right), 1)
            return row_holder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)
        layout.addWidget(self._xp2_editor)
        layout.addWidget(_pair_row(self._replaces_editor, self._prereqs_editor))
        layout.addWidget(_pair_row(self._resource_costs_editor, self._yield_changes_editor))
        layout.addWidget(_pair_row(self._yield_power_editor, self._citizen_yield_editor))
        layout.addWidget(_pair_row(self._yields_per_era_editor, self._gp_editor))
        layout.addWidget(_pair_row(self._tourism_bombs_editor, self._required_features_editor))
        layout.addWidget(_pair_row(self._valid_features_editor, self._valid_terrains_editor))
        layout.addWidget(_pair_row(self._conditions_editor, self._yield_district_copies_editor))
        layout.addWidget(self._build_charge_prod_editor)
        layout.addWidget(self._greatworks_editor)

    def _sync_building_type(self) -> None:
        building_type = self._main_editor.current_type()
        self._xp2_editor.set_building_type(building_type)
        self._replaces_editor.set_building_type(building_type)
        self._prereqs_editor.set_building_type(building_type)
        self._citizen_yield_editor.set_building_type(building_type)
        self._gp_editor.set_building_type(building_type)
        self._required_features_editor.set_building_type(building_type)
        self._tourism_bombs_editor.set_building_type(building_type)
        self._resource_costs_editor.set_building_type(building_type)
        self._valid_features_editor.set_building_type(building_type)
        self._valid_terrains_editor.set_building_type(building_type)
        self._yield_changes_editor.set_building_type(building_type)
        self._yield_power_editor.set_building_type(building_type)
        self._yield_district_copies_editor.set_building_type(building_type)
        self._yields_per_era_editor.set_building_type(building_type)
        self._conditions_editor.set_building_type(building_type)
        self._build_charge_prod_editor.set_building_type(building_type)
        self._greatworks_editor.set_building_type(building_type)

    def _handle_main_changed(self) -> None:
        self._sync_building_type()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_building_type()

        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

        self._xp2_editor.set_payload(subtables.get("Buildings_XP2") if isinstance(subtables.get("Buildings_XP2"), dict) else entry.get("buildings_xp2") if isinstance(entry.get("buildings_xp2"), dict) else {})
        self._replaces_editor.set_payload(subtables.get("BuildingReplaces") if isinstance(subtables.get("BuildingReplaces"), dict) else entry.get("building_replaces") if isinstance(entry.get("building_replaces"), dict) else {})
        self._prereqs_editor.set_payload(subtables.get("BuildingPrereqs") if isinstance(subtables.get("BuildingPrereqs"), list) else entry.get("building_prereqs") if isinstance(entry.get("building_prereqs"), list) else [])
        self._citizen_yield_editor.set_payload(subtables.get("Building_CitizenYieldChanges") if isinstance(subtables.get("Building_CitizenYieldChanges"), list) else entry.get("building_citizen_yield_changes") if isinstance(entry.get("building_citizen_yield_changes"), list) else [])
        self._gp_editor.set_payload(subtables.get("Building_GreatPersonPoints") if isinstance(subtables.get("Building_GreatPersonPoints"), list) else entry.get("building_great_person_points") if isinstance(entry.get("building_great_person_points"), list) else [])
        self._required_features_editor.set_payload(subtables.get("Building_RequiredFeatures") if isinstance(subtables.get("Building_RequiredFeatures"), list) else entry.get("building_required_features") if isinstance(entry.get("building_required_features"), list) else [])
        self._tourism_bombs_editor.set_payload(subtables.get("Building_TourismBombs_XP2") if isinstance(subtables.get("Building_TourismBombs_XP2"), list) else entry.get("building_tourism_bombs_xp2") if isinstance(entry.get("building_tourism_bombs_xp2"), list) else [])
        self._resource_costs_editor.set_payload(subtables.get("Building_ResourceCosts") if isinstance(subtables.get("Building_ResourceCosts"), list) else entry.get("building_resource_costs") if isinstance(entry.get("building_resource_costs"), list) else [])
        self._valid_features_editor.set_payload(subtables.get("Building_ValidFeatures") if isinstance(subtables.get("Building_ValidFeatures"), list) else entry.get("building_valid_features") if isinstance(entry.get("building_valid_features"), list) else [])
        self._valid_terrains_editor.set_payload(subtables.get("Building_ValidTerrains") if isinstance(subtables.get("Building_ValidTerrains"), list) else entry.get("building_valid_terrains") if isinstance(entry.get("building_valid_terrains"), list) else [])
        self._yield_changes_editor.set_payload(subtables.get("Building_YieldChanges") if isinstance(subtables.get("Building_YieldChanges"), list) else entry.get("building_yield_changes") if isinstance(entry.get("building_yield_changes"), list) else [])
        self._yield_power_editor.set_payload(subtables.get("Building_YieldChangesBonusWithPower") if isinstance(subtables.get("Building_YieldChangesBonusWithPower"), list) else entry.get("building_yield_changes_bonus_with_power") if isinstance(entry.get("building_yield_changes_bonus_with_power"), list) else [])
        self._yield_district_copies_editor.set_payload(subtables.get("Building_YieldDistrictCopies") if isinstance(subtables.get("Building_YieldDistrictCopies"), list) else entry.get("building_yield_district_copies") if isinstance(entry.get("building_yield_district_copies"), list) else [])
        self._yields_per_era_editor.set_payload(subtables.get("Building_YieldsPerEra") if isinstance(subtables.get("Building_YieldsPerEra"), list) else entry.get("building_yields_per_era") if isinstance(entry.get("building_yields_per_era"), list) else [])
        conditions_payload = subtables.get("BuildingConditions")
        if isinstance(conditions_payload, list):
            conditions_payload = conditions_payload[0] if conditions_payload else {}
        if not isinstance(conditions_payload, dict):
            conditions_payload = entry.get("building_conditions") if isinstance(entry.get("building_conditions"), dict) else {}
        self._conditions_editor.set_payload(conditions_payload if isinstance(conditions_payload, dict) else {})
        self._build_charge_prod_editor.set_payload(subtables.get("Building_BuildChargeProductions") if isinstance(subtables.get("Building_BuildChargeProductions"), list) else entry.get("building_build_charge_productions") if isinstance(entry.get("building_build_charge_productions"), list) else [])
        self._greatworks_editor.set_payload(subtables.get("Building_GreatWorks") if isinstance(subtables.get("Building_GreatWorks"), list) else entry.get("building_greatworks") if isinstance(entry.get("building_greatworks"), list) else [])

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()
        buildings_xp2 = self._xp2_editor.export_payload()
        building_replaces = self._replaces_editor.export_payload()
        building_prereqs = self._prereqs_editor.export_payload()
        citizen = self._citizen_yield_editor.export_payload()
        gpp = self._gp_editor.export_payload()
        req_features = self._required_features_editor.export_payload()
        tourism_bombs = self._tourism_bombs_editor.export_payload()
        resource_costs = self._resource_costs_editor.export_payload()
        valid_features = self._valid_features_editor.export_payload()
        valid_terrains = self._valid_terrains_editor.export_payload()
        yield_changes = self._yield_changes_editor.export_payload()
        yield_power = self._yield_power_editor.export_payload()
        yield_district_copies = self._yield_district_copies_editor.export_payload()
        yields_per_era = self._yields_per_era_editor.export_payload()
        conditions = self._conditions_editor.export_payload()
        build_charge = self._build_charge_prod_editor.export_payload()
        greatworks = self._greatworks_editor.export_payload()

        payload.update(
            {
                "buildings_xp2": buildings_xp2,
                "building_replaces": building_replaces,
                "building_prereqs": building_prereqs,
                "building_citizen_yield_changes": citizen,
                "building_great_person_points": gpp,
                "building_required_features": req_features,
                "building_tourism_bombs_xp2": tourism_bombs,
                "building_resource_costs": resource_costs,
                "building_valid_features": valid_features,
                "building_valid_terrains": valid_terrains,
                "building_yield_changes": yield_changes,
                "building_yield_changes_bonus_with_power": yield_power,
                "building_yield_district_copies": yield_district_copies,
                "building_yields_per_era": yields_per_era,
                "building_conditions": conditions,
                "building_build_charge_productions": build_charge,
                "building_greatworks": greatworks,
                "subtables": {
                    "Buildings_XP2": buildings_xp2,
                    "BuildingReplaces": building_replaces,
                    "BuildingPrereqs": building_prereqs,
                    "Building_CitizenYieldChanges": citizen,
                    "Building_GreatPersonPoints": gpp,
                    "Building_RequiredFeatures": req_features,
                    "Building_TourismBombs_XP2": tourism_bombs,
                    "Building_ResourceCosts": resource_costs,
                    "Building_ValidFeatures": valid_features,
                    "Building_ValidTerrains": valid_terrains,
                    "Building_YieldChanges": yield_changes,
                    "Building_YieldChangesBonusWithPower": yield_power,
                    "Building_YieldDistrictCopies": yield_district_copies,
                    "Building_YieldsPerEra": yields_per_era,
                    "BuildingConditions": conditions,
                    "Building_BuildChargeProductions": build_charge,
                    "Building_GreatWorks": greatworks,
                },
            }
        )
        return payload

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


@dataclass(slots=True)
class _UnitColumnSpec:
    key: str
    label: str
    kind: str  # template/int/real/bool/text
    template_key: str | None = None


class _UnitRowsTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, *, table_name: str, hint_text: str, owner_key: str, columns: list[_UnitColumnSpec]) -> None:
        super().__init__()
        self._unit_type = ""
        self._owner_key = owner_key
        self._columns = columns
        self._base_column_widths: list[int] = []

        group = QGroupBox(table_name)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(8, 6, 8, 6)
        group_layout.setSpacing(8)
        tip = QLabel(hint_text)
        tip.setWordWrap(True)
        group_layout.addWidget(tip)

        top = QHBoxLayout()
        self._top_layout = top
        top.addWidget(QLabel(owner_key))
        self._unit_type_display = QLineEdit()
        self._unit_type_display.setReadOnly(True)
        top.addWidget(self._unit_type_display, 1)
        self._add_btn = QPushButton("＋ 添加行")
        self._add_btn.clicked.connect(self._add_row)
        top.addWidget(self._add_btn)
        group_layout.addLayout(top)

        self._table = QTableWidget(0, len(self._columns) + 1)
        self._table.setHorizontalHeaderLabels([item.label for item in self._columns] + ["Action"])
        header = self._table.horizontalHeader()
        for col in range(len(self._columns)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(len(self._columns), QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(len(self._columns), 56)
        header.setMinimumSectionSize(72)
        self._init_header_width_policy([item.label for item in self._columns])
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        group_layout.addWidget(self._table)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)
        QTimer.singleShot(0, self._apply_proportional_column_widths)

    def _register_top_action_button(self, button: QPushButton) -> None:
        insert_index = max(0, self._top_layout.count() - 1)
        self._top_layout.insertWidget(insert_index, button)

    def _init_header_width_policy(self, headers: list[str]) -> None:
        metrics = QFontMetrics(self._table.horizontalHeader().font())
        self._base_column_widths = []
        for col, text in enumerate(headers):
            header_width = metrics.horizontalAdvance(text) + 34
            base_width = 190 if col == 0 else 140
            self._base_column_widths.append(max(base_width, header_width))
        self._apply_proportional_column_widths()

    def _apply_proportional_column_widths(self) -> None:
        if not self._base_column_widths:
            return
        op_col = len(self._columns)
        op_width = 56
        self._table.setColumnWidth(op_col, op_width)
        available = max(0, self._table.viewport().width() - op_width - 2)
        if available <= 0:
            return
        scaled = _fit_column_widths(self._base_column_widths, available, preferred_min=60)
        for col, width in enumerate(scaled):
            self._table.setColumnWidth(col, width)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_proportional_column_widths()

    def set_unit_type(self, unit_type: str) -> None:
        self._unit_type = _safe_text(unit_type)
        self._unit_type_display.setText(self._unit_type)

    def _create_cell_widget(self, spec: _UnitColumnSpec, seed: dict[str, object] | None) -> QWidget:
        if spec.kind == "template" and spec.template_key:
            widget = build_template_widget(spec.template_key)
            if hasattr(widget, "set_label_text"):
                widget.set_label_text("")
            if seed and hasattr(widget, "set_current_value"):
                widget.set_current_value(_safe_text(seed.get(spec.key)) or None)
            return widget
        if spec.kind == "real":
            spin = _CompactDoubleSpinBox()
            spin.setRange(-999999.0, 999999.0)
            spin.setValue(float((seed or {}).get(spec.key, 0.0) or 0.0))
            _attach_hover_param_tooltip(spin, spec.key)
            return spin
        if spec.kind == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(int((seed or {}).get(spec.key, 0) or 0)))
            _normalize_checkbox_caption(cb)
            _attach_hover_param_tooltip(cb, spec.key)
            return cb
        if spec.kind == "text":
            edit = QLineEdit()
            edit.setText(_safe_text((seed or {}).get(spec.key)))
            return edit
        spin = QSpinBox()
        spin.setRange(-999999, 999999)
        spin.setValue(int((seed or {}).get(spec.key, 0) or 0))
        _attach_hover_param_tooltip(spin, spec.key)
        return spin

    def _add_row(self, seed: dict[str, object] | None = None) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, spec in enumerate(self._columns):
            widget = self._create_cell_widget(spec, seed)
            self._table.setCellWidget(row, col, widget)
            if isinstance(widget, BaseTemplateWidget):
                widget.dataChanged.connect(self.dataChanged.emit)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _t: self.dataChanged.emit())
        btn = QPushButton("删")
        btn.clicked.connect(lambda: self._remove_row(btn))
        self._table.setCellWidget(row, len(self._columns), btn)
        self._refresh_table_height()
        self.dataChanged.emit()

    def _remove_row(self, button: QPushButton) -> None:
        op_col = len(self._columns)
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, op_col) is button:
                self._table.removeRow(row)
                self._refresh_table_height()
                self.dataChanged.emit()
                return

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        self._table.setRowCount(0)
        for row in payload:
            if isinstance(row, dict):
                self._add_row(row)
        self._refresh_table_height()

    def _refresh_table_height(self) -> None:
        self._table.resizeRowsToContents()
        header_h = self._table.horizontalHeader().height()
        frame_h = self._table.frameWidth() * 2
        rows_h = sum(self._table.rowHeight(r) for r in range(self._table.rowCount()))
        if self._table.rowCount() == 0:
            rows_h += self._table.verticalHeader().defaultSectionSize()
        self._table.setFixedHeight(header_h + rows_h + frame_h + 2)

    def export_payload(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in range(self._table.rowCount()):
            payload: dict[str, object] = {self._owner_key: self._unit_type}
            empty_first = False
            for col, spec in enumerate(self._columns):
                widget = self._table.cellWidget(row, col)
                value: object = ""
                if isinstance(widget, BaseTemplateWidget):
                    value = _safe_text(_first_non_empty(widget.export_data()))
                elif isinstance(widget, QSpinBox):
                    value = int(widget.value())
                elif isinstance(widget, QDoubleSpinBox):
                    value = float(widget.value())
                elif isinstance(widget, QCheckBox):
                    value = 1 if widget.isChecked() else 0
                elif isinstance(widget, QLineEdit):
                    value = _safe_text(widget.text())
                if col == 0 and _safe_text(value) == "":
                    empty_first = True
                payload[spec.key] = value
            if not empty_first:
                rows.append(payload)
        return rows


class _UnitSingleRowEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, *, table_name: str, hint_text: str, owner_key: str, columns: list[_UnitColumnSpec]) -> None:
        super().__init__()
        self._owner_key = owner_key
        self._unit_type = ""
        self._widgets: dict[str, QWidget] = {}

        group = QGroupBox(table_name)
        layout = QVBoxLayout(group)
        tip = QLabel(hint_text)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self._owner_display = QLineEdit()
        self._owner_display.setReadOnly(True)

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(180)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        current_row = 0
        grid.addWidget(_cell(owner_key, self._owner_display), current_row, 0, 1, 2)
        current_row += 1

        pending_half_row: QWidget | None = None

        for spec in columns:
            widget: QWidget
            if spec.kind == "template" and spec.template_key:
                widget = build_template_widget(spec.template_key)
                if hasattr(widget, "set_label_text"):
                    widget.set_label_text("")
            elif spec.kind == "real":
                widget = _CompactDoubleSpinBox()
                widget.setRange(-999999.0, 999999.0)
                _attach_hover_param_tooltip(widget, spec.key)
            elif spec.kind == "bool":
                widget = QCheckBox()
                _normalize_checkbox_caption(widget)
                _attach_hover_param_tooltip(widget, spec.key)
            elif spec.kind == "text":
                widget = QLineEdit()
            else:
                widget = QSpinBox()
                widget.setRange(-999999, 999999)
                _attach_hover_param_tooltip(widget, spec.key)
            self._widgets[spec.key] = widget

            cell_widget = _cell(spec.label, widget)
            if spec.kind == "template":
                if pending_half_row is not None:
                    grid.addWidget(pending_half_row, current_row, 0)
                    current_row += 1
                    pending_half_row = None
                grid.addWidget(cell_widget, current_row, 0, 1, 2)
                current_row += 1
            else:
                if pending_half_row is None:
                    pending_half_row = cell_widget
                else:
                    grid.addWidget(pending_half_row, current_row, 0)
                    grid.addWidget(cell_widget, current_row, 1)
                    current_row += 1
                    pending_half_row = None

            if isinstance(widget, BaseTemplateWidget):
                widget.dataChanged.connect(self.dataChanged.emit)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(lambda _v: self.dataChanged.emit())
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _v: self.dataChanged.emit())

        if pending_half_row is not None:
            grid.addWidget(pending_half_row, current_row, 0)

        layout.addLayout(grid)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

    def set_unit_type(self, unit_type: str) -> None:
        self._unit_type = _safe_text(unit_type)
        self._owner_display.setText(self._unit_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        for key, widget in self._widgets.items():
            value = payload.get(key)
            if isinstance(widget, BaseTemplateWidget) and hasattr(widget, "set_current_value"):
                widget.set_current_value(_safe_text(value) or None)
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value or 0))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value or 0.0))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(int(value or 0)))
            elif isinstance(widget, QLineEdit):
                widget.setText(_safe_text(value))

    def export_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {self._owner_key: self._unit_type}
        for key, widget in self._widgets.items():
            if isinstance(widget, BaseTemplateWidget):
                payload[key] = _safe_text(_first_non_empty(widget.export_data()))
            elif isinstance(widget, QSpinBox):
                payload[key] = int(widget.value())
            elif isinstance(widget, QDoubleSpinBox):
                payload[key] = float(widget.value())
            elif isinstance(widget, QCheckBox):
                payload[key] = 1 if widget.isChecked() else 0
            elif isinstance(widget, QLineEdit):
                payload[key] = _safe_text(widget.text())
        return payload


class UnitReplacesSingleEditor(_UnitSingleRowEditor):
    replacesChanged = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__(
            table_name="UnitReplaces",
            hint_text="特色单位替代关系。",
            owner_key="CivUniqueUnitType",
            columns=[_UnitColumnSpec("ReplacesUnitType", "ReplacesUnitType", "template", "unit_search_no_trait")],
        )
        widget = self._widgets.get("ReplacesUnitType")
        if isinstance(widget, BaseTemplateWidget):
            widget.dataChanged.connect(self._emit_replaces)

    def _emit_replaces(self) -> None:
        widget = self._widgets.get("ReplacesUnitType")
        value = _safe_text(_first_non_empty(widget.export_data())) if isinstance(widget, BaseTemplateWidget) else ""
        self.replacesChanged.emit(value)

    def set_payload(self, payload: dict[str, object]) -> None:
        super().set_payload(payload)
        value = _safe_text(payload.get("ReplacesUnitType"))
        self.replacesChanged.emit(value)


class UnitUpgradesSingleEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._unit_type = ""
        self._suggest_value = ""
        self._unit_display = QLineEdit()
        self._unit_display.setReadOnly(True)
        self._upgrade_widget = build_template_widget("unit_search")
        if hasattr(self._upgrade_widget, "set_label_text"):
            self._upgrade_widget.set_label_text("")
        self._suggest_label = QLabel("建议值是取代单位的升级单位")
        self._fill_btn = QPushButton("填充建议")
        self._fill_btn.clicked.connect(self._fill_suggested)

        group = QGroupBox("UnitUpgrades")
        layout = QVBoxLayout(group)
        tip = QLabel("升级关系。")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(180)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell("Unit", self._unit_display), 0, 0)
        grid.addWidget(_cell("UpgradeUnit", self._upgrade_widget), 0, 1)

        suggest_row = QHBoxLayout()
        suggest_row.addWidget(self._fill_btn)
        suggest_row.addWidget(self._suggest_label, 1)
        suggest_row.addStretch(1)

        layout.addLayout(grid)
        layout.addLayout(suggest_row)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        if hasattr(self._upgrade_widget, "dataChanged"):
            self._upgrade_widget.dataChanged.connect(self.dataChanged.emit)

    def set_unit_type(self, unit_type: str) -> None:
        self._unit_type = _safe_text(unit_type)
        self._unit_display.setText(self._unit_type)

    def set_replaces_type(self, replaces_type: str) -> None:
        self._suggest_value = _suggest_upgrade_from_replaces(replaces_type)
        self._suggest_label.setText(f"建议值：{self._suggest_value or '（无）'}")

    def _fill_suggested(self) -> None:
        if not self._suggest_value:
            return
        if hasattr(self._upgrade_widget, "set_current_value"):
            self._upgrade_widget.set_current_value(self._suggest_value)
        self.dataChanged.emit()

    def set_payload(self, payload: dict[str, object]) -> None:
        if hasattr(self._upgrade_widget, "set_current_value"):
            self._upgrade_widget.set_current_value(_safe_text(payload.get("UpgradeUnit")) or None)

    def export_payload(self) -> dict[str, object]:
        value = ""
        if isinstance(self._upgrade_widget, BaseTemplateWidget):
            value = _safe_text(_first_non_empty(self._upgrade_widget.export_data()))
        return {"Unit": self._unit_type, "UpgradeUnit": value}


class UnitsXP2SingleEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._unit_type = ""
        self._unit_display = QLineEdit()
        self._unit_display.setReadOnly(True)

        self._resource_maintenance_amount = QSpinBox(); self._resource_maintenance_amount.setRange(0, 999999)
        self._resource_cost = QSpinBox(); self._resource_cost.setRange(0, 999999)
        self._resource_maintenance_type = build_template_widget("resource_strategic")
        if hasattr(self._resource_maintenance_type, "set_label_text"):
            self._resource_maintenance_type.set_label_text("")
        self._tourism_bomb = QSpinBox(); self._tourism_bomb.setRange(0, 999999)

        self._can_earn_experience = QCheckBox(); _normalize_checkbox_caption(self._can_earn_experience)
        self._tourism_bomb_possible = QCheckBox(); _normalize_checkbox_caption(self._tourism_bomb_possible)
        self._can_form_military = QCheckBox(); _normalize_checkbox_caption(self._can_form_military)
        self._major_civ_only = QCheckBox(); _normalize_checkbox_caption(self._major_civ_only)
        self._can_cause_disasters = QCheckBox(); _normalize_checkbox_caption(self._can_cause_disasters)
        self._can_sacrifice_units = QCheckBox(); _normalize_checkbox_caption(self._can_sacrifice_units)

        for widget, key in (
            (self._resource_maintenance_amount, "ResourceMaintenanceAmount"),
            (self._resource_cost, "ResourceCost"),
            (self._tourism_bomb, "TourismBomb"),
            (self._can_earn_experience, "CanEarnExperience"),
            (self._tourism_bomb_possible, "TourismBombPossible"),
            (self._can_form_military, "CanFormMilitaryFormation"),
            (self._major_civ_only, "MajorCivOnly"),
            (self._can_cause_disasters, "CanCauseDisasters"),
            (self._can_sacrifice_units, "CanSacrificeUnits"),
        ):
            _attach_hover_param_tooltip(widget, key)

        group = QGroupBox("Units_XP2")
        layout = QVBoxLayout(group)
        tip = QLabel("单位 XP2 扩展参数。")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        grid = QGridLayout()

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget(); row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0); row.setSpacing(6)
            title = QLabel(label); title.setMinimumWidth(190)
            row.addWidget(title); row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell("UnitType", self._unit_display), 0, 0)
        grid.addWidget(_cell("ResourceMaintenanceAmount", self._resource_maintenance_amount), 0, 1)
        grid.addWidget(_cell("ResourceCost", self._resource_cost), 1, 0)
        grid.addWidget(_cell("ResourceMaintenanceType", self._resource_maintenance_type), 1, 1)
        grid.addWidget(_cell("TourismBomb", self._tourism_bomb), 2, 0)
        grid.addWidget(_cell("CanEarnExperience", self._can_earn_experience), 2, 1)
        grid.addWidget(_cell("TourismBombPossible", self._tourism_bomb_possible), 3, 0)
        grid.addWidget(_cell("CanFormMilitaryFormation", self._can_form_military), 3, 1)
        grid.addWidget(_cell("MajorCivOnly", self._major_civ_only), 4, 0)
        grid.addWidget(_cell("CanCauseDisasters", self._can_cause_disasters), 4, 1)
        grid.addWidget(_cell("CanSacrificeUnits", self._can_sacrifice_units), 5, 0)
        layout.addLayout(grid)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        for widget in (self._resource_maintenance_amount, self._resource_cost, self._tourism_bomb):
            widget.valueChanged.connect(lambda _v: self.dataChanged.emit())
        for widget in (
            self._can_earn_experience,
            self._tourism_bomb_possible,
            self._can_form_military,
            self._major_civ_only,
            self._can_cause_disasters,
            self._can_sacrifice_units,
        ):
            widget.stateChanged.connect(lambda _v: self.dataChanged.emit())
        if hasattr(self._resource_maintenance_type, "dataChanged"):
            self._resource_maintenance_type.dataChanged.connect(self.dataChanged.emit)

    def set_unit_type(self, unit_type: str) -> None:
        self._unit_type = _safe_text(unit_type)
        self._unit_display.setText(self._unit_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        self._resource_maintenance_amount.setValue(int(payload.get("ResourceMaintenanceAmount", 0) or 0))
        self._resource_cost.setValue(int(payload.get("ResourceCost", 0) or 0))
        if hasattr(self._resource_maintenance_type, "set_current_value"):
            self._resource_maintenance_type.set_current_value(_safe_text(payload.get("ResourceMaintenanceType")) or None)
        self._tourism_bomb.setValue(int(payload.get("TourismBomb", 0) or 0))
        self._can_earn_experience.setChecked(bool(int(payload.get("CanEarnExperience", 1) or 1)))
        self._tourism_bomb_possible.setChecked(bool(int(payload.get("TourismBombPossible", 0) or 0)))
        self._can_form_military.setChecked(bool(int(payload.get("CanFormMilitaryFormation", 1) or 1)))
        self._major_civ_only.setChecked(bool(int(payload.get("MajorCivOnly", 0) or 0)))
        self._can_cause_disasters.setChecked(bool(int(payload.get("CanCauseDisasters", 0) or 0)))
        self._can_sacrifice_units.setChecked(bool(int(payload.get("CanSacrificeUnits", 0) or 0)))

    def export_payload(self) -> dict[str, object]:
        resource_type = ""
        if isinstance(self._resource_maintenance_type, BaseTemplateWidget):
            resource_type = _safe_text(_first_non_empty(self._resource_maintenance_type.export_data()))
        return {
            "UnitType": self._unit_type,
            "ResourceMaintenanceAmount": int(self._resource_maintenance_amount.value()),
            "ResourceCost": int(self._resource_cost.value()),
            "ResourceMaintenanceType": resource_type,
            "TourismBomb": int(self._tourism_bomb.value()),
            "CanEarnExperience": 1 if self._can_earn_experience.isChecked() else 0,
            "TourismBombPossible": 1 if self._tourism_bomb_possible.isChecked() else 0,
            "CanFormMilitaryFormation": 1 if self._can_form_military.isChecked() else 0,
            "MajorCivOnly": 1 if self._major_civ_only.isChecked() else 0,
            "CanCauseDisasters": 1 if self._can_cause_disasters.isChecked() else 0,
            "CanSacrificeUnits": 1 if self._can_sacrifice_units.isChecked() else 0,
        }


class _UnitTagPickerDialog(QDialog):
    def __init__(self, candidates: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择 Tag")
        self.setModal(True)
        self.resize(640, 480)
        self._candidates = list(candidates)

        layout = QVBoxLayout(self)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("搜索"))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("输入关键字过滤 Tag")
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit, 1)
        layout.addLayout(filter_row)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        layout.addWidget(self._list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._apply_filter("")

    def _apply_filter(self, keyword: str) -> None:
        key = _safe_text(keyword).lower()
        self._list.clear()
        for tag in self._candidates:
            if key and key not in tag.lower():
                continue
            self._list.addItem(QListWidgetItem(tag))

    def selected_tags(self) -> list[str]:
        return [_safe_text(item.text()) for item in self._list.selectedItems() if _safe_text(item.text())]


class UnitTypeTagsEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._unit_type = ""
        self._fixed_checks: dict[str, QCheckBox] = {}
        self._custom_tags: list[str] = []

        group = QGroupBox("TypeTags")
        layout = QVBoxLayout(group)
        tip = QLabel("单位 TypeTags 独立区域")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        top = QHBoxLayout()
        top.addWidget(QLabel("Type"))
        self._unit_display = QLineEdit()
        self._unit_display.setReadOnly(True)
        top.addWidget(self._unit_display, 1)
        layout.addLayout(top)

        fixed_box = QGroupBox("固定单位类别 Tag")
        fixed_grid = QGridLayout(fixed_box)
        for index, (tag_code, zh) in enumerate(FIXED_UNIT_CLASS_TAGS):
            checkbox = QCheckBox(f"{tag_code}（{zh}）")
            checkbox.stateChanged.connect(lambda _v: self.dataChanged.emit())
            self._fixed_checks[tag_code] = checkbox
            fixed_grid.addWidget(checkbox, index // 4, index % 4)
        layout.addWidget(fixed_box)

        custom_box = QGroupBox("数据库的其他 Tag")
        custom_layout = QVBoxLayout(custom_box)
        buttons = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_custom_tags)
        remove_btn = QPushButton("移除选中")
        remove_btn.clicked.connect(self._remove_selected_custom_tags)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_custom_tags)
        buttons.addWidget(add_btn)
        buttons.addWidget(remove_btn)
        buttons.addWidget(clear_btn)
        buttons.addStretch(1)
        custom_layout.addLayout(buttons)
        self._custom_list = QListWidget()
        self._custom_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        custom_layout.addWidget(self._custom_list, 1)
        layout.addWidget(custom_box)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

    def set_unit_type(self, unit_type: str) -> None:
        self._unit_type = _safe_text(unit_type)
        self._unit_display.setText(self._unit_type)

    def _add_custom_tags(self) -> None:
        excluded = set(self._custom_tags)
        excluded.update(self._fixed_checks.keys())
        candidates = _fetch_unit_typetag_candidates(excluded)
        if not candidates:
            QMessageBox.information(self, "TypeTags", "未找到可添加的自定义 Tag。")
            return
        dialog = _UnitTagPickerDialog(candidates, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_tags()
        changed = False
        for tag in selected:
            if tag and tag not in self._custom_tags:
                self._custom_tags.append(tag)
                changed = True
        if changed:
            self._refresh_custom_list()
            self.dataChanged.emit()

    def _remove_selected_custom_tags(self) -> None:
        selected = {_safe_text(item.text()) for item in self._custom_list.selectedItems()}
        if not selected:
            return
        self._custom_tags = [tag for tag in self._custom_tags if tag not in selected]
        self._refresh_custom_list()
        self.dataChanged.emit()

    def _clear_custom_tags(self) -> None:
        if not self._custom_tags:
            return
        self._custom_tags = []
        self._refresh_custom_list()
        self.dataChanged.emit()

    def _refresh_custom_list(self) -> None:
        self._custom_list.clear()
        for tag in sorted(set(self._custom_tags)):
            self._custom_list.addItem(QListWidgetItem(tag))

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        for checkbox in self._fixed_checks.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
        self._custom_tags = []
        selected_tags: list[str] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            tag = _safe_text(row.get("Tag"))
            if tag:
                selected_tags.append(tag)
        for tag in selected_tags:
            checkbox = self._fixed_checks.get(tag)
            if checkbox is not None:
                checkbox.blockSignals(True)
                checkbox.setChecked(True)
                checkbox.blockSignals(False)
            elif tag not in self._custom_tags:
                self._custom_tags.append(tag)
        self._refresh_custom_list()

    def export_payload(self) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for tag_code, checkbox in self._fixed_checks.items():
            if checkbox.isChecked():
                output.append({"Type": self._unit_type, "Tag": tag_code})
        for tag in sorted(set(self._custom_tags)):
            output.append({"Type": self._unit_type, "Tag": tag})
        return output


class UnitAbilityBindingsEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._unit_type = ""
        self._last_auto_ability_type = ""
        self._last_auto_tag = ""

        group = QGroupBox("单位 Ability")
        layout = QVBoxLayout(group)
        tip = QLabel("单位能力区，勾选表示是否启用。")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("UnitType"))
        self._unit_display = QLineEdit()
        self._unit_display.setReadOnly(True)
        row1.addWidget(self._unit_display, 1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("UnitAbilityType"))
        self._ability_type = QLineEdit()
        self._ability_type.setPlaceholderText("例如 ABILITY_UNIT_SIQI_U0023_S")
        row2.addWidget(self._ability_type, 1)
        row2.addWidget(QLabel("Tag"))
        self._tag = QLineEdit()
        self._tag.setPlaceholderText("例如 CLASS_SIQI_U0023_S")
        row2.addWidget(self._tag, 1)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("AbilityName(zh)"))
        self._ability_name = QLineEdit()
        row3.addWidget(self._ability_name, 1)
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("AbilityDescription(zh)"))
        self._ability_description = QLineEdit()
        row4.addWidget(self._ability_description, 1)
        layout.addLayout(row4)

        row5 = QHBoxLayout()
        self._enabled = QCheckBox("需要 Ability")
        row5.addWidget(self._enabled)
        row5.addStretch(1)
        layout.addLayout(row5)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        for widget in (self._ability_type, self._tag, self._ability_name, self._ability_description):
            widget.textChanged.connect(lambda _t: self.dataChanged.emit())
        self._enabled.stateChanged.connect(lambda _v: self.dataChanged.emit())

    def _update_defaults(self) -> None:
        inferred_tag = _infer_class_tag(self._unit_type)
        current_tag = _safe_text(self._tag.text())
        if inferred_tag and (not current_tag or current_tag == self._last_auto_tag):
            self._tag.setText(inferred_tag)
            self._last_auto_tag = inferred_tag
        if self._unit_type:
            inferred_ability_type = f"ABILITY_{self._unit_type}"
            current_ability_type = _safe_text(self._ability_type.text())
            if not current_ability_type or current_ability_type == self._last_auto_ability_type:
                self._ability_type.setText(inferred_ability_type)
                self._last_auto_ability_type = inferred_ability_type

    def set_unit_type(self, unit_type: str) -> None:
        self._unit_type = _safe_text(unit_type)
        self._unit_display.setText(self._unit_type)
        self._update_defaults()

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        if not payload:
            self._enabled.setChecked(False)
            self._ability_type.setText("")
            self._tag.setText("")
            self._ability_name.setText("")
            self._ability_description.setText("")
            self._update_defaults()
            return
        first = payload[0] if isinstance(payload[0], dict) else {}
        self._ability_type.setText(_safe_text(first.get("UnitAbilityType")))
        self._tag.setText(_safe_text(first.get("Tag")))
        self._ability_name.setText(_safe_text(first.get("AbilityName")))
        self._ability_description.setText(_safe_text(first.get("AbilityDescription")))
        self._enabled.setChecked(bool(int(first.get("Enabled", 1) or 1)))
        self._update_defaults()

    def export_payload(self) -> list[dict[str, object]]:
        enabled = self._enabled.isChecked()
        ability_type = f"ABILITY_{self._unit_type}" if self._unit_type else _safe_text(self._ability_type.text())
        tag = _infer_class_tag(self._unit_type) if self._unit_type else _safe_text(self._tag.text())
        ability_name = _safe_text(self._ability_name.text())
        ability_desc = _safe_text(self._ability_description.text())
        if not enabled:
            return []
        if not ability_type:
            return []
        return [
            {
                "UnitType": self._unit_type,
                "UnitAbilityType": ability_type,
                "Tag": tag,
                "AbilityName": ability_name,
                "AbilityDescription": ability_desc,
                "Enabled": 1,
            }
        ]


class UnitCompositeEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._loading = False

        self._main_editor = MainTableEditor(
            schema=build_units_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )

        self._mode_editor = _UnitSingleRowEditor(
            table_name="Units_MODE",
            hint_text="单位模式参数。",
            owner_key="UnitType",
            columns=[_UnitColumnSpec("ActionCharges", "ActionCharges", "int")],
        )
        self._presentation_editor = _UnitSingleRowEditor(
            table_name="Units_Presentation",
            hint_text="单位显示参数。",
            owner_key="UnitType",
            columns=[_UnitColumnSpec("UIFlagOffset", "UIFlagOffset", "int")],
        )
        self._xp2_editor = UnitsXP2SingleEditor()
        self._replaces_editor = UnitReplacesSingleEditor()
        self._upgrades_editor = UnitUpgradesSingleEditor()
        self._captures_editor = _UnitSingleRowEditor(
            table_name="UnitCaptures",
            hint_text="捕获后转换单位。",
            owner_key="CapturedUnitType",
            columns=[_UnitColumnSpec("BecomesUnitType", "BecomesUnitType", "template", "unit_search")],
        )
        self._retreats_editor = _UnitRowsTableEditor(
            table_name="UnitRetreats_XP1",
            hint_text="撤退规则。",
            owner_key="UnitType",
            columns=[
                _UnitColumnSpec("UnitRetreatType", "UnitRetreatType", "text"),
                _UnitColumnSpec("BuildingType", "BuildingType", "template", "building_search_all"),
                _UnitColumnSpec("ImprovementType", "ImprovementType", "template", "improvement_search"),
            ],
        )
        self._building_prereqs_editor = _UnitRowsTableEditor(
            table_name="Unit_BuildingPrereqs",
            hint_text="单位建筑前置。",
            owner_key="Unit",
            columns=[
                _UnitColumnSpec("PrereqBuilding", "PrereqBuilding", "template", "building_search_all"),
                _UnitColumnSpec("NumSupported", "NumSupported", "int"),
            ],
        )
        self._ai_infos_editor = _UnitRowsTableEditor(
            table_name="UnitAiInfos",
            hint_text="单位AI类型。",
            owner_key="UnitType",
            columns=[_UnitColumnSpec("AiType", "AiType", "template", "unit_ai_type")],
        )
        self._type_tags_editor = UnitTypeTagsEditor()
        self._ability_bindings_editor = UnitAbilityBindingsEditor()

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        for editor in (
            self._mode_editor,
            self._presentation_editor,
            self._xp2_editor,
            self._replaces_editor,
            self._upgrades_editor,
            self._captures_editor,
            self._retreats_editor,
            self._building_prereqs_editor,
            self._ai_infos_editor,
            self._type_tags_editor,
            self._ability_bindings_editor,
        ):
            editor.dataChanged.connect(self._emit_data_changed)

        self._replaces_editor.replacesChanged.connect(self._upgrades_editor.set_replaces_type)

        def _top_cell(widget: QWidget) -> QWidget:
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(0)
            holder_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)
            holder_layout.addStretch(1)
            return holder

        def _pair_row(left: QWidget, right: QWidget) -> QWidget:
            row_holder = QWidget()
            row_layout = QHBoxLayout(row_holder)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(_top_cell(left), 1)
            row_layout.addWidget(_top_cell(right), 1)
            return row_holder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)
        layout.addWidget(self._xp2_editor)
        layout.addWidget(_pair_row(self._mode_editor, self._presentation_editor))
        layout.addWidget(_pair_row(self._replaces_editor, self._upgrades_editor))
        layout.addWidget(self._captures_editor)
        layout.addWidget(_pair_row(self._retreats_editor, self._building_prereqs_editor))
        layout.addWidget(self._type_tags_editor)
        layout.addWidget(self._ai_infos_editor)
        layout.addWidget(self._ability_bindings_editor)

    def _sync_unit_type(self) -> None:
        unit_type = self._main_editor.current_type()
        self._mode_editor.set_unit_type(unit_type)
        self._presentation_editor.set_unit_type(unit_type)
        self._xp2_editor.set_unit_type(unit_type)
        self._replaces_editor.set_unit_type(unit_type)
        self._upgrades_editor.set_unit_type(unit_type)
        self._captures_editor.set_unit_type(unit_type)
        self._retreats_editor.set_unit_type(unit_type)
        self._building_prereqs_editor.set_unit_type(unit_type)
        self._ai_infos_editor.set_unit_type(unit_type)
        self._type_tags_editor.set_unit_type(unit_type)
        self._ability_bindings_editor.set_unit_type(unit_type)

    def _handle_main_changed(self) -> None:
        self._sync_unit_type()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_unit_type()
        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

        self._mode_editor.set_payload(subtables.get("Units_MODE") if isinstance(subtables.get("Units_MODE"), dict) else entry.get("units_mode") if isinstance(entry.get("units_mode"), dict) else {})
        self._presentation_editor.set_payload(subtables.get("Units_Presentation") if isinstance(subtables.get("Units_Presentation"), dict) else entry.get("units_presentation") if isinstance(entry.get("units_presentation"), dict) else {})
        self._xp2_editor.set_payload(subtables.get("Units_XP2") if isinstance(subtables.get("Units_XP2"), dict) else entry.get("units_xp2") if isinstance(entry.get("units_xp2"), dict) else {})
        self._replaces_editor.set_payload(subtables.get("UnitReplaces") if isinstance(subtables.get("UnitReplaces"), dict) else entry.get("unit_replaces") if isinstance(entry.get("unit_replaces"), dict) else {})
        self._upgrades_editor.set_payload(subtables.get("UnitUpgrades") if isinstance(subtables.get("UnitUpgrades"), dict) else entry.get("unit_upgrades") if isinstance(entry.get("unit_upgrades"), dict) else {})
        self._captures_editor.set_payload(subtables.get("UnitCaptures") if isinstance(subtables.get("UnitCaptures"), dict) else entry.get("unit_captures") if isinstance(entry.get("unit_captures"), dict) else {})
        self._retreats_editor.set_payload(subtables.get("UnitRetreats_XP1") if isinstance(subtables.get("UnitRetreats_XP1"), list) else entry.get("unit_retreats_xp1") if isinstance(entry.get("unit_retreats_xp1"), list) else [])
        self._building_prereqs_editor.set_payload(subtables.get("Unit_BuildingPrereqs") if isinstance(subtables.get("Unit_BuildingPrereqs"), list) else entry.get("unit_building_prereqs") if isinstance(entry.get("unit_building_prereqs"), list) else [])
        self._ai_infos_editor.set_payload(subtables.get("UnitAiInfos") if isinstance(subtables.get("UnitAiInfos"), list) else entry.get("unit_ai_infos") if isinstance(entry.get("unit_ai_infos"), list) else [])
        self._type_tags_editor.set_payload(subtables.get("TypeTags") if isinstance(subtables.get("TypeTags"), list) else entry.get("type_tags") if isinstance(entry.get("type_tags"), list) else [])
        self._ability_bindings_editor.set_payload(subtables.get("UnitAbilityBindings") if isinstance(subtables.get("UnitAbilityBindings"), list) else entry.get("unit_ability_bindings") if isinstance(entry.get("unit_ability_bindings"), list) else [])

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()
        units_mode = self._mode_editor.export_payload()
        units_presentation = self._presentation_editor.export_payload()
        units_xp2 = self._xp2_editor.export_payload()
        unit_replaces = self._replaces_editor.export_payload()
        unit_upgrades = self._upgrades_editor.export_payload()
        unit_captures = self._captures_editor.export_payload()
        unit_retreats_xp1 = self._retreats_editor.export_payload()
        unit_building_prereqs = self._building_prereqs_editor.export_payload()
        unit_ai_infos = self._ai_infos_editor.export_payload()
        type_tags = self._type_tags_editor.export_payload()
        unit_ability_bindings = self._ability_bindings_editor.export_payload()

        payload.update(
            {
                "units_mode": units_mode,
                "units_presentation": units_presentation,
                "units_xp2": units_xp2,
                "unit_replaces": unit_replaces,
                "unit_upgrades": unit_upgrades,
                "unit_captures": unit_captures,
                "unit_retreats_xp1": unit_retreats_xp1,
                "unit_building_prereqs": unit_building_prereqs,
                "unit_ai_infos": unit_ai_infos,
                "type_tags": type_tags,
                "unit_ability_bindings": unit_ability_bindings,
                "subtables": {
                    "Units_MODE": units_mode,
                    "Units_Presentation": units_presentation,
                    "Units_XP2": units_xp2,
                    "UnitReplaces": unit_replaces,
                    "UnitUpgrades": unit_upgrades,
                    "UnitCaptures": unit_captures,
                    "UnitRetreats_XP1": unit_retreats_xp1,
                    "Unit_BuildingPrereqs": unit_building_prereqs,
                    "UnitAiInfos": unit_ai_infos,
                    "TypeTags": type_tags,
                    "UnitAbilityBindings": unit_ability_bindings,
                },
            }
        )
        return payload

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class ImprovementYieldsOutsideTerritoriesEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._improvement_type = ""
        self._improvement_display = QLineEdit()
        self._improvement_display.setReadOnly(True)
        self._enabled = QCheckBox("启用 Improvement_YieldsOutsideTerritories")
        _normalize_checkbox_caption(self._enabled)

        group = QGroupBox("Improvement_YieldsOutsideTerritories")
        layout = QVBoxLayout(group)
        tip = QLabel("该表无参数；勾选后仅输出 ImprovementType 一行。")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(220)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell("ImprovementType", self._improvement_display), 0, 0)
        grid.addWidget(_cell("Enabled", self._enabled), 0, 1)
        layout.addLayout(grid)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        self._enabled.stateChanged.connect(lambda _v: self.dataChanged.emit())

    def set_improvement_type(self, improvement_type: str) -> None:
        self._improvement_type = _safe_text(improvement_type)
        self._improvement_display.setText(self._improvement_type)

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        self._enabled.setChecked(bool(payload))

    def export_payload(self) -> list[dict[str, object]]:
        if not self._enabled.isChecked() or not self._improvement_type:
            return []
        return [{"ImprovementType": self._improvement_type}]


class ImprovementBonusYieldChangesEditor(_UnitRowsTableEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Improvement_BonusYieldChanges",
            hint_text="加成产出变化。ID 固定为 {完整Type}_{序数}。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("YieldType", "YieldType", "template", "yield"),
                _UnitColumnSpec("BonusYieldChange", "BonusYieldChange", "int"),
                _UnitColumnSpec("PrereqTech", "PrereqTech", "template", "technology_search"),
                _UnitColumnSpec("PrereqCivic", "PrereqCivic", "template", "civic_search"),
            ],
        )

    def set_improvement_type(self, improvement_type: str) -> None:
        self.set_unit_type(improvement_type)

    def export_payload(self) -> list[dict[str, object]]:
        rows = super().export_payload()
        output: list[dict[str, object]] = []
        for index, row in enumerate(rows, start=1):
            cloned = dict(row)
            improvement_type = _safe_text(cloned.get("ImprovementType"))
            if improvement_type:
                cloned["Id"] = f"{improvement_type}_{index}"
            output.append(cloned)
        return output


class ImprovementYieldChangesFixedEditor(_UnitRowsTableEditor):
    _DEFAULT_YIELDS = [
        "YIELD_GOLD",
        "YIELD_PRODUCTION",
        "YIELD_SCIENCE",
        "YIELD_CULTURE",
        "YIELD_FAITH",
        "YIELD_FOOD",
    ]

    def __init__(self) -> None:
        super().__init__(
            table_name="Improvement_YieldChanges",
            hint_text="默认包含 6 种产出，初始值为 0。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("YieldType", "YieldType", "template", "yield"),
                _UnitColumnSpec("YieldChange", "YieldChange", "int"),
            ],
        )

    def set_improvement_type(self, improvement_type: str) -> None:
        self.set_unit_type(improvement_type)

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        if payload:
            super().set_payload(payload)
            return
        defaults = [
            {
                "ImprovementType": self._unit_type,
                "YieldType": yield_type,
                "YieldChange": 0,
            }
            for yield_type in self._DEFAULT_YIELDS
        ]
        super().set_payload(defaults)


class ImprovementValidBuildUnitsEditor(_UnitRowsTableEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Improvement_ValidBuildUnits",
            hint_text="可建造单位。默认自带一行 UNIT_BUILDER。",
            owner_key="ImprovementType",
            columns=[_UnitColumnSpec("UnitType", "UnitType", "template", "unit_search")],
        )

    def set_improvement_type(self, improvement_type: str) -> None:
        self.set_unit_type(improvement_type)

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        if payload:
            super().set_payload(payload)
            return
        super().set_payload([{"ImprovementType": self._unit_type, "UnitType": "UNIT_BUILDER"}])

    def export_payload(self) -> list[dict[str, object]]:
        rows = super().export_payload()
        if rows:
            return rows
        if self._unit_type:
            return [{"ImprovementType": self._unit_type, "UnitType": "UNIT_BUILDER"}]
        return []


class ImprovementValidTerrainsEditor(_UnitRowsTableEditor):
    _FALLBACK_LAND_TERRAINS = [
        "TERRAIN_GRASS",
        "TERRAIN_PLAINS",
        "TERRAIN_DESERT",
        "TERRAIN_TUNDRA",
        "TERRAIN_SNOW",
    ]

    def __init__(self) -> None:
        super().__init__(
            table_name="Improvement_ValidTerrains",
            hint_text="需要地形。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("TerrainType", "TerrainType", "template", "terrain"),
                _UnitColumnSpec("PrereqTech", "PrereqTech", "template", "technology_search"),
                _UnitColumnSpec("PrereqCivic", "PrereqCivic", "template", "civic_search"),
            ],
        )
        self._add_land_btn = QPushButton("一键添加所有陆地")
        self._add_land_btn.clicked.connect(self._add_all_land_terrains)
        self._register_top_action_button(self._add_land_btn)

    @staticmethod
    def _load_land_terrain_types() -> list[str]:
        db_path = _active_game_db_path()
        if not db_path.exists():
            return list(ImprovementValidTerrainsEditor._FALLBACK_LAND_TERRAINS)
        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return list(ImprovementValidTerrainsEditor._FALLBACK_LAND_TERRAINS)

        rows: list[tuple[object, ...]] = []
        try:
            try:
                rows = conn.execute(
                    "SELECT TerrainType FROM Terrains WHERE IFNULL(CAST(Water AS INTEGER), 0) = 0 ORDER BY TerrainType"
                ).fetchall()
            except sqlite3.Error:
                rows = conn.execute("SELECT TerrainType FROM Terrains ORDER BY TerrainType").fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()

        terrain_types: list[str] = []
        for row in rows:
            terrain_type = _safe_text(row[0] if row else "")
            if not terrain_type:
                continue
            if terrain_type in {"TERRAIN_COAST", "TERRAIN_OCEAN"}:
                continue
            if "MOUNTAIN" in terrain_type.upper():
                continue
            terrain_types.append(terrain_type)

        if not terrain_types:
            return list(ImprovementValidTerrainsEditor._FALLBACK_LAND_TERRAINS)
        return sorted(set(terrain_types))

    def _existing_terrain_types(self) -> set[str]:
        values: set[str] = set()
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, 0)
            if isinstance(widget, BaseTemplateWidget):
                value = _safe_text(_first_non_empty(widget.export_data()))
                if value:
                    values.add(value)
        return values

    def _add_all_land_terrains(self) -> None:
        if not self._unit_type:
            QMessageBox.information(self, "提示", "请先填写改良设施 Type，再添加地形。")
            return

        existing = self._existing_terrain_types()
        added = 0
        for terrain_type in self._load_land_terrain_types():
            if terrain_type in existing:
                continue
            self._add_row(
                {
                    self._owner_key: self._unit_type,
                    "TerrainType": terrain_type,
                    "PrereqTech": "",
                    "PrereqCivic": "",
                }
            )
            existing.add(terrain_type)
            added += 1

        if added == 0:
            QMessageBox.information(self, "提示", "陆地地形已全部存在，无需重复添加。")


class ImprovementCompositeEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._loading = False

        self._main_editor = MainTableEditor(
            schema=build_improvements_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )

        self._mode_editor = _UnitSingleRowEditor(
            table_name="Improvements_MODE",
            hint_text="垄断公司模式参数。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("Industry", "Industry", "bool"),
                _UnitColumnSpec("Corporation", "Corporation", "bool"),
            ],
        )
        self._xp2_editor = _UnitSingleRowEditor(
            table_name="Improvements_XP2",
            hint_text="资料片XP2参数。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("AllowImpassableMovement", "AllowImpassableMovement", "bool"),
                _UnitColumnSpec("BuildOnAdjacentPlot", "BuildOnAdjacentPlot", "bool"),
                _UnitColumnSpec("PreventsDrought", "PreventsDrought", "bool"),
                _UnitColumnSpec("DisasterResistant", "DisasterResistant", "bool"),
            ],
        )
        self._tourism_editor = _UnitSingleRowEditor(
            table_name="Improvement_Tourism",
            hint_text="旅游业绩参数。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("TourismSource", "TourismSource", "template", "tourism_source"),
                _UnitColumnSpec("PrereqCivic", "PrereqCivic", "template", "civic_search"),
                _UnitColumnSpec("PrereqTech", "PrereqTech", "template", "technology_search"),
                _UnitColumnSpec("ScalingFactor", "ScalingFactor", "int"),
            ],
        )
        self._outside_territories_editor = ImprovementYieldsOutsideTerritoriesEditor()

        self._bonus_yield_editor = ImprovementBonusYieldChangesEditor()
        self._yield_changes_editor = ImprovementYieldChangesFixedEditor()
        self._invalid_adj_feature_editor = _UnitRowsTableEditor(
            table_name="Improvement_InvalidAdjacentFeatures",
            hint_text="排除相邻地貌。",
            owner_key="ImprovementType",
            columns=[_UnitColumnSpec("FeatureType", "FeatureType", "template", "feature_all")],
        )
        self._valid_adj_resource_editor = _UnitRowsTableEditor(
            table_name="Improvement_ValidAdjacentResources",
            hint_text="需要相邻资源。",
            owner_key="ImprovementType",
            columns=[_UnitColumnSpec("ResourceType", "ResourceType", "template", "resource_search")],
        )
        self._valid_adj_terrain_editor = _UnitRowsTableEditor(
            table_name="Improvement_ValidAdjacentTerrains",
            hint_text="需要相邻地形。",
            owner_key="ImprovementType",
            columns=[_UnitColumnSpec("TerrainType", "TerrainType", "template", "terrain")],
        )
        self._valid_build_units_editor = ImprovementValidBuildUnitsEditor()
        self._valid_features_editor = _UnitRowsTableEditor(
            table_name="Improvement_ValidFeatures",
            hint_text="需要地貌。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("FeatureType", "FeatureType", "template", "feature_all"),
                _UnitColumnSpec("PrereqTech", "PrereqTech", "template", "technology_search"),
                _UnitColumnSpec("PrereqCivic", "PrereqCivic", "template", "civic_search"),
            ],
        )
        self._valid_resources_editor = _UnitRowsTableEditor(
            table_name="Improvement_ValidResources",
            hint_text="需要资源。",
            owner_key="ImprovementType",
            columns=[
                _UnitColumnSpec("ResourceType", "ResourceType", "template", "resource_search"),
                _UnitColumnSpec("MustRemoveFeature", "MustRemoveFeature", "bool"),
            ],
        )
        self._valid_terrains_editor = ImprovementValidTerrainsEditor()

        self._adjacency_editor = AdjacencyEditorWidget(
            auto_context=AdjacencyAutoContext(),
            include_placeholder=True,
            custom_description_placeholder=True,
            parent=self,
        )

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        for editor in (
            self._mode_editor,
            self._xp2_editor,
            self._tourism_editor,
            self._outside_territories_editor,
            self._bonus_yield_editor,
            self._yield_changes_editor,
            self._invalid_adj_feature_editor,
            self._valid_adj_resource_editor,
            self._valid_adj_terrain_editor,
            self._valid_build_units_editor,
            self._valid_features_editor,
            self._valid_resources_editor,
            self._valid_terrains_editor,
            self._adjacency_editor,
        ):
            editor.dataChanged.connect(self._emit_data_changed)

        def _top_cell(widget: QWidget) -> QWidget:
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(0)
            holder_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)
            holder_layout.addStretch(1)
            return holder

        def _pair_row(left: QWidget, right: QWidget) -> QWidget:
            row_holder = QWidget()
            row_layout = QHBoxLayout(row_holder)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(_top_cell(left), 1)
            row_layout.addWidget(_top_cell(right), 1)
            return row_holder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)
        layout.addWidget(_pair_row(self._mode_editor, self._xp2_editor))
        layout.addWidget(_pair_row(self._tourism_editor, self._outside_territories_editor))
        layout.addWidget(_pair_row(self._bonus_yield_editor, self._yield_changes_editor))
        layout.addWidget(_pair_row(self._invalid_adj_feature_editor, self._valid_adj_resource_editor))
        layout.addWidget(_pair_row(self._valid_adj_terrain_editor, self._valid_build_units_editor))
        layout.addWidget(_pair_row(self._valid_features_editor, self._valid_resources_editor))
        layout.addWidget(self._valid_terrains_editor)
        layout.addWidget(self._adjacency_editor)

    def _build_adjacency_context(self) -> AdjacencyAutoContext:
        shared = self._main_editor.shared_params()
        prefix = _safe_text(shared.get("prefix") if isinstance(shared, dict) else "")
        infix = 0
        if isinstance(shared, dict):
            try:
                infix = int(shared.get("infix", 0) or 0)
            except (TypeError, ValueError):
                infix = 0
        improvement_type = self._main_editor.current_type()
        code = improvement_type
        if code.startswith("IMPROVEMENT_"):
            code = code[len("IMPROVEMENT_") :]
        code = _sanitize_english_token(code)
        infix_text = f"{infix:03d}" if infix > 0 else ""
        return AdjacencyAutoContext(prefix=prefix, district_infix=infix_text, district_code=code)

    def _sync_improvement_type(self) -> None:
        improvement_type = self._main_editor.current_type()
        self._mode_editor.set_unit_type(improvement_type)
        self._xp2_editor.set_unit_type(improvement_type)
        self._tourism_editor.set_unit_type(improvement_type)
        self._outside_territories_editor.set_improvement_type(improvement_type)
        self._bonus_yield_editor.set_improvement_type(improvement_type)
        self._yield_changes_editor.set_improvement_type(improvement_type)
        self._invalid_adj_feature_editor.set_unit_type(improvement_type)
        self._valid_adj_resource_editor.set_unit_type(improvement_type)
        self._valid_adj_terrain_editor.set_unit_type(improvement_type)
        self._valid_build_units_editor.set_improvement_type(improvement_type)
        self._valid_features_editor.set_unit_type(improvement_type)
        self._valid_resources_editor.set_unit_type(improvement_type)
        self._valid_terrains_editor.set_unit_type(improvement_type)
        self._adjacency_editor.set_auto_context(self._build_adjacency_context())

    def _handle_main_changed(self) -> None:
        self._sync_improvement_type()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_improvement_type()
        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

        self._mode_editor.set_payload(subtables.get("Improvements_MODE") if isinstance(subtables.get("Improvements_MODE"), dict) else entry.get("improvements_mode") if isinstance(entry.get("improvements_mode"), dict) else {})
        self._xp2_editor.set_payload(subtables.get("Improvements_XP2") if isinstance(subtables.get("Improvements_XP2"), dict) else entry.get("improvements_xp2") if isinstance(entry.get("improvements_xp2"), dict) else {})
        self._tourism_editor.set_payload(subtables.get("Improvement_Tourism") if isinstance(subtables.get("Improvement_Tourism"), dict) else entry.get("improvement_tourism") if isinstance(entry.get("improvement_tourism"), dict) else {})
        self._outside_territories_editor.set_payload(subtables.get("Improvement_YieldsOutsideTerritories") if isinstance(subtables.get("Improvement_YieldsOutsideTerritories"), list) else entry.get("improvement_yields_outside_territories") if isinstance(entry.get("improvement_yields_outside_territories"), list) else [])
        self._bonus_yield_editor.set_payload(subtables.get("Improvement_BonusYieldChanges") if isinstance(subtables.get("Improvement_BonusYieldChanges"), list) else entry.get("improvement_bonus_yield_changes") if isinstance(entry.get("improvement_bonus_yield_changes"), list) else [])
        self._yield_changes_editor.set_payload(subtables.get("Improvement_YieldChanges") if isinstance(subtables.get("Improvement_YieldChanges"), list) else entry.get("improvement_yield_changes") if isinstance(entry.get("improvement_yield_changes"), list) else [])
        self._invalid_adj_feature_editor.set_payload(subtables.get("Improvement_InvalidAdjacentFeatures") if isinstance(subtables.get("Improvement_InvalidAdjacentFeatures"), list) else entry.get("improvement_invalid_adjacent_features") if isinstance(entry.get("improvement_invalid_adjacent_features"), list) else [])
        self._valid_adj_resource_editor.set_payload(subtables.get("Improvement_ValidAdjacentResources") if isinstance(subtables.get("Improvement_ValidAdjacentResources"), list) else entry.get("improvement_valid_adjacent_resources") if isinstance(entry.get("improvement_valid_adjacent_resources"), list) else [])
        self._valid_adj_terrain_editor.set_payload(subtables.get("Improvement_ValidAdjacentTerrains") if isinstance(subtables.get("Improvement_ValidAdjacentTerrains"), list) else entry.get("improvement_valid_adjacent_terrains") if isinstance(entry.get("improvement_valid_adjacent_terrains"), list) else [])
        self._valid_build_units_editor.set_payload(subtables.get("Improvement_ValidBuildUnits") if isinstance(subtables.get("Improvement_ValidBuildUnits"), list) else entry.get("improvement_valid_build_units") if isinstance(entry.get("improvement_valid_build_units"), list) else [])
        self._valid_features_editor.set_payload(subtables.get("Improvement_ValidFeatures") if isinstance(subtables.get("Improvement_ValidFeatures"), list) else entry.get("improvement_valid_features") if isinstance(entry.get("improvement_valid_features"), list) else [])
        self._valid_resources_editor.set_payload(subtables.get("Improvement_ValidResources") if isinstance(subtables.get("Improvement_ValidResources"), list) else entry.get("improvement_valid_resources") if isinstance(entry.get("improvement_valid_resources"), list) else [])
        self._valid_terrains_editor.set_payload(subtables.get("Improvement_ValidTerrains") if isinstance(subtables.get("Improvement_ValidTerrains"), list) else entry.get("improvement_valid_terrains") if isinstance(entry.get("improvement_valid_terrains"), list) else [])

        adjacency_payload = subtables.get("Improvement_Adjacencies") if isinstance(subtables.get("Improvement_Adjacencies"), list) else None
        if adjacency_payload is None:
            adjacency_payload = entry.get("improvement_adjacencies") if isinstance(entry.get("improvement_adjacencies"), list) else []
        self._adjacency_editor.set_payload(adjacency_payload)

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()
        improvements_mode = self._mode_editor.export_payload()
        improvements_xp2 = self._xp2_editor.export_payload()
        improvement_tourism = self._tourism_editor.export_payload()
        improvement_yields_outside_territories = self._outside_territories_editor.export_payload()
        improvement_bonus_yield_changes = self._bonus_yield_editor.export_payload()
        improvement_yield_changes = self._yield_changes_editor.export_payload()
        improvement_invalid_adjacent_features = self._invalid_adj_feature_editor.export_payload()
        improvement_valid_adjacent_resources = self._valid_adj_resource_editor.export_payload()
        improvement_valid_adjacent_terrains = self._valid_adj_terrain_editor.export_payload()
        improvement_valid_build_units = self._valid_build_units_editor.export_payload()
        improvement_valid_features = self._valid_features_editor.export_payload()
        improvement_valid_resources = self._valid_resources_editor.export_payload()
        improvement_valid_terrains = self._valid_terrains_editor.export_payload()
        improvement_adjacencies = self._adjacency_editor.export_payload()

        payload.update(
            {
                "improvements_mode": improvements_mode,
                "improvements_xp2": improvements_xp2,
                "improvement_tourism": improvement_tourism,
                "improvement_yields_outside_territories": improvement_yields_outside_territories,
                "improvement_bonus_yield_changes": improvement_bonus_yield_changes,
                "improvement_yield_changes": improvement_yield_changes,
                "improvement_invalid_adjacent_features": improvement_invalid_adjacent_features,
                "improvement_valid_adjacent_resources": improvement_valid_adjacent_resources,
                "improvement_valid_adjacent_terrains": improvement_valid_adjacent_terrains,
                "improvement_valid_build_units": improvement_valid_build_units,
                "improvement_valid_features": improvement_valid_features,
                "improvement_valid_resources": improvement_valid_resources,
                "improvement_valid_terrains": improvement_valid_terrains,
                "improvement_adjacencies": improvement_adjacencies,
                "subtables": {
                    "Improvements_MODE": improvements_mode,
                    "Improvements_XP2": improvements_xp2,
                    "Improvement_Tourism": improvement_tourism,
                    "Improvement_YieldsOutsideTerritories": improvement_yields_outside_territories,
                    "Improvement_BonusYieldChanges": improvement_bonus_yield_changes,
                    "Improvement_YieldChanges": improvement_yield_changes,
                    "Improvement_InvalidAdjacentFeatures": improvement_invalid_adjacent_features,
                    "Improvement_ValidAdjacentResources": improvement_valid_adjacent_resources,
                    "Improvement_ValidAdjacentTerrains": improvement_valid_adjacent_terrains,
                    "Improvement_ValidBuildUnits": improvement_valid_build_units,
                    "Improvement_ValidFeatures": improvement_valid_features,
                    "Improvement_ValidResources": improvement_valid_resources,
                    "Improvement_ValidTerrains": improvement_valid_terrains,
                    "Improvement_Adjacencies": improvement_adjacencies,
                },
            }
        )
        return payload

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class ProjectPrereqSelectorTemplate(BaseTemplateWidget):
    """前置项目选择：合并数据库项目与工作区新建项目。"""

    def __init__(self, workspace_projects_provider: Callable[[], list[tuple[str, str]]], parent: QWidget | None = None) -> None:
        super().__init__("项目前置选择框", parent)
        self._workspace_projects_provider = workspace_projects_provider
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self.dataChanged.emit)
        self._placeholder = "请选择前置项目"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._combo)

        self.refresh_options()

    def refresh_options(self, preferred_value: str | None = None) -> None:
        current = _safe_text(preferred_value) or _safe_text(self._combo.currentData())
        workspace_rows = self._workspace_projects_provider() if callable(self._workspace_projects_provider) else []
        db_rows = _fetch_project_rows_for_selector()

        seen: set[str] = set()
        workspace_normalized: list[tuple[str, str]] = []
        for project_type, name in workspace_rows:
            project_text = _safe_text(project_type)
            if not project_text or project_text in seen:
                continue
            seen.add(project_text)
            workspace_normalized.append((project_text, _safe_text(name) or project_text))

        db_normalized: list[tuple[str, str]] = []
        for project_type, display in db_rows:
            project_text = _safe_text(project_type)
            if not project_text or project_text in seen:
                continue
            seen.add(project_text)
            db_normalized.append((project_text, _safe_text(display) or project_text))

        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(self._placeholder, None)

        workspace_color: QColor = self.palette().color(QPalette.ColorRole.Link)
        for project_type, display in workspace_normalized:
            label = f"【工作区】{display} | {project_type}"
            self._combo.addItem(label, project_type)
            idx = self._combo.count() - 1
            self._combo.setItemData(idx, workspace_color, Qt.ItemDataRole.ForegroundRole)
            self._combo.setItemData(idx, "workspace", Qt.ItemDataRole.UserRole)

        for project_type, display in db_normalized:
            label = f"{display} | {project_type}"
            self._combo.addItem(label, project_type)
            idx = self._combo.count() - 1
            self._combo.setItemData(idx, "database", Qt.ItemDataRole.UserRole)

        if current:
            match_index = self._combo.findData(current)
            if match_index >= 0:
                self._combo.setCurrentIndex(match_index)
            else:
                self._combo.setCurrentIndex(0 if self._combo.count() else -1)
        else:
            self._combo.setCurrentIndex(0 if self._combo.count() else -1)
        self._combo.setEnabled(self._combo.count() > 1)
        self._combo.blockSignals(False)

    def export_data(self) -> dict[str, object]:
        project_type = _safe_text(self._combo.currentData())
        source = _safe_text(self._combo.currentData(Qt.ItemDataRole.UserRole))
        return {
            "project_type": project_type,
            "value": project_type,
            "source": source,
        }

    def set_current_value(self, value: str | None) -> None:
        self.refresh_options(value)


class ProjectsModeSingleEditor(_UnitSingleRowEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Projects_MODE",
            hint_text=_project_table_hint("Projects_MODE"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("PrereqImprovement", _param_display_text(zh_text=_project_param_zh("Projects_MODE", "PrereqImprovement"), fallback_key="PrereqImprovement"), "template", "improvement_search"),
                _UnitColumnSpec("ResourceType", _param_display_text(zh_text=_project_param_zh("Projects_MODE", "ResourceType"), fallback_key="ResourceType"), "template", "resource_search"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectsXP1SingleEditor(_UnitSingleRowEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Projects_XP1",
            hint_text=_project_table_hint("Projects_XP1"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("IdentityPerCitizenChange", _param_display_text(zh_text=_project_param_zh("Projects_XP1", "IdentityPerCitizenChange"), fallback_key="IdentityPerCitizenChange"), "real"),
                _UnitColumnSpec("UnlocksFromEffect", _param_display_text(zh_text=_project_param_zh("Projects_XP1", "UnlocksFromEffect"), fallback_key="UnlocksFromEffect"), "bool"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectsXP2SingleEditor(_UnitSingleRowEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Projects_XP2",
            hint_text=_project_table_hint("Projects_XP2"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("RequiredPowerWhileActive", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "RequiredPowerWhileActive"), fallback_key="RequiredPowerWhileActive"), "int"),
                _UnitColumnSpec("ReligiousPressureModifier", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "ReligiousPressureModifier"), fallback_key="ReligiousPressureModifier"), "int"),
                _UnitColumnSpec("UnlocksFromEffect", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "UnlocksFromEffect"), fallback_key="UnlocksFromEffect"), "bool"),
                _UnitColumnSpec("RequiredBuilding", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "RequiredBuilding"), fallback_key="RequiredBuilding"), "template", "building_search_no_trait"),
                _UnitColumnSpec("CreateBuilding", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "CreateBuilding"), fallback_key="CreateBuilding"), "template", "building_search_no_trait"),
                _UnitColumnSpec("FullyPoweredWhileActive", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "FullyPoweredWhileActive"), fallback_key="FullyPoweredWhileActive"), "bool"),
                _UnitColumnSpec("MaxSimultaneousInstances", _param_display_text(zh_text=_project_param_zh("Projects_XP2", "MaxSimultaneousInstances"), fallback_key="MaxSimultaneousInstances"), "int"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectBuildingCostsEditor(_UnitRowsTableEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Project_BuildingCosts",
            hint_text=_project_table_hint("Project_BuildingCosts"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("ConsumedBuildingType", _param_display_text(zh_text=_project_param_zh("Project_BuildingCosts", "ConsumedBuildingType"), fallback_key="ConsumedBuildingType"), "template", "building_search_no_trait"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectGreatPersonPointsEditor(_UnitRowsTableEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Project_GreatPersonPoints",
            hint_text=_project_table_hint("Project_GreatPersonPoints"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("GreatPersonClassType", _param_display_text(zh_text=_project_param_zh("Project_GreatPersonPoints", "GreatPersonClassType"), fallback_key="GreatPersonClassType"), "template", "great_person_class"),
                _UnitColumnSpec("Points", _param_display_text(zh_text=_project_param_zh("Project_GreatPersonPoints", "Points"), fallback_key="Points"), "int"),
                _UnitColumnSpec("PointProgressionModel", _param_display_text(zh_text=_project_param_zh("Project_GreatPersonPoints", "PointProgressionModel"), fallback_key="PointProgressionModel"), "template", "cost_progression"),
                _UnitColumnSpec("PointProgressionParam1", _param_display_text(zh_text=_project_param_zh("Project_GreatPersonPoints", "PointProgressionParam1"), fallback_key="PointProgressionParam1"), "int"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectResourceCostsEditor(_UnitRowsTableEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Project_ResourceCosts",
            hint_text=_project_table_hint("Project_ResourceCosts"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("ResourceType", _param_display_text(zh_text=_project_param_zh("Project_ResourceCosts", "ResourceType"), fallback_key="ResourceType"), "template", "resource_search"),
                _UnitColumnSpec("StartProductionCost", _param_display_text(zh_text=_project_param_zh("Project_ResourceCosts", "StartProductionCost"), fallback_key="StartProductionCost"), "int"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectYieldConversionsEditor(_UnitRowsTableEditor):
    def __init__(self) -> None:
        super().__init__(
            table_name="Project_YieldConversions",
            hint_text=_project_table_hint("Project_YieldConversions"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("YieldType", _param_display_text(zh_text=_project_param_zh("Project_YieldConversions", "YieldType"), fallback_key="YieldType"), "template", "yield"),
                _UnitColumnSpec("PercentOfProductionRate", _param_display_text(zh_text=_project_param_zh("Project_YieldConversions", "PercentOfProductionRate"), fallback_key="PercentOfProductionRate"), "int"),
            ],
        )

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)


class ProjectPrereqsEditor(_UnitRowsTableEditor):
    def __init__(self, *, workspace_projects_provider: Callable[[str], list[tuple[str, str]]]) -> None:
        self._workspace_projects_provider = workspace_projects_provider
        super().__init__(
            table_name="ProjectPrereqs",
            hint_text=_project_table_hint("ProjectPrereqs"),
            owner_key="ProjectType",
            columns=[
                _UnitColumnSpec("PrereqProjectType", _param_display_text(zh_text=_project_param_zh("ProjectPrereqs", "PrereqProjectType"), fallback_key="PrereqProjectType"), "template", "project_prereq_selector"),
                _UnitColumnSpec("MinimumPlayerInstances", _param_display_text(zh_text=_project_param_zh("ProjectPrereqs", "MinimumPlayerInstances"), fallback_key="MinimumPlayerInstances"), "int"),
            ],
        )

    def _create_cell_widget(self, spec: _UnitColumnSpec, seed: dict[str, object] | None) -> QWidget:
        if spec.key == "PrereqProjectType":
            widget = ProjectPrereqSelectorTemplate(
                workspace_projects_provider=lambda: self._workspace_projects_provider(self._unit_type)
            )
            if seed:
                widget.set_current_value(_safe_text(seed.get(spec.key)) or None)
            return widget
        return super()._create_cell_widget(spec, seed)

    def set_project_type(self, project_type: str) -> None:
        self.set_unit_type(project_type)
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, 0)
            if isinstance(widget, ProjectPrereqSelectorTemplate):
                current = _safe_text(widget.export_data().get("project_type"))
                widget.refresh_options(current)


class ProjectCompositeEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
        project_entries_provider: Callable[[], list[dict[str, object]]],
    ) -> None:
        super().__init__()
        self._loading = False
        self._project_entries_provider = project_entries_provider

        self._main_editor = MainTableEditor(
            schema=build_projects_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )
        self._mode_editor = ProjectsModeSingleEditor()
        self._xp1_editor = ProjectsXP1SingleEditor()
        self._xp2_editor = ProjectsXP2SingleEditor()
        self._building_costs_editor = ProjectBuildingCostsEditor()
        self._great_person_points_editor = ProjectGreatPersonPointsEditor()
        self._resource_costs_editor = ProjectResourceCostsEditor()
        self._yield_conversions_editor = ProjectYieldConversionsEditor()
        self._prereqs_editor = ProjectPrereqsEditor(workspace_projects_provider=self._workspace_projects)

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        self._mode_editor.dataChanged.connect(self._emit_data_changed)
        self._xp1_editor.dataChanged.connect(self._emit_data_changed)
        self._xp2_editor.dataChanged.connect(self._emit_data_changed)
        self._building_costs_editor.dataChanged.connect(self._emit_data_changed)
        self._great_person_points_editor.dataChanged.connect(self._emit_data_changed)
        self._resource_costs_editor.dataChanged.connect(self._emit_data_changed)
        self._yield_conversions_editor.dataChanged.connect(self._emit_data_changed)
        self._prereqs_editor.dataChanged.connect(self._emit_data_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)
        layout.addWidget(self._mode_editor)
        layout.addWidget(self._xp1_editor)
        layout.addWidget(self._xp2_editor)

        multi_holder = QWidget()
        multi_layout = QGridLayout(multi_holder)
        multi_layout.setContentsMargins(0, 0, 0, 0)
        multi_layout.setHorizontalSpacing(10)
        multi_layout.setVerticalSpacing(10)
        multi_layout.addWidget(self._building_costs_editor, 0, 0)
        multi_layout.addWidget(self._great_person_points_editor, 0, 1)
        multi_layout.addWidget(self._resource_costs_editor, 1, 0)
        multi_layout.addWidget(self._yield_conversions_editor, 1, 1)
        multi_layout.addWidget(self._prereqs_editor, 2, 0)
        multi_layout.setColumnStretch(0, 1)
        multi_layout.setColumnStretch(1, 1)

        layout.addWidget(multi_holder)

    def _workspace_projects(self, current_project_type: str) -> list[tuple[str, str]]:
        entries = self._project_entries_provider() if callable(self._project_entries_provider) else []
        output: list[tuple[str, str]] = []
        seen: set[str] = set()
        current = _safe_text(current_project_type)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            project_type = _safe_text(entry.get("type"))
            if not project_type or project_type == current or project_type in seen:
                continue
            seen.add(project_type)
            display_name = _safe_text(entry.get("name")) or project_type
            output.append((project_type, display_name))
        LOGGER.info("Loaded %d workspace project options for current project %s", len(output), current or "<empty>")
        return output

    def _sync_project_type(self) -> None:
        project_type = self._main_editor.current_type()
        self._mode_editor.set_project_type(project_type)
        self._xp1_editor.set_project_type(project_type)
        self._xp2_editor.set_project_type(project_type)
        self._building_costs_editor.set_project_type(project_type)
        self._great_person_points_editor.set_project_type(project_type)
        self._resource_costs_editor.set_project_type(project_type)
        self._yield_conversions_editor.set_project_type(project_type)
        self._prereqs_editor.set_project_type(project_type)

    def _handle_main_changed(self) -> None:
        self._sync_project_type()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_project_type()

        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

        mode_payload = subtables.get("Projects_MODE") if isinstance(subtables.get("Projects_MODE"), dict) else entry.get("projects_mode") if isinstance(entry.get("projects_mode"), dict) else {}
        self._mode_editor.set_payload(mode_payload if isinstance(mode_payload, dict) else {})

        xp1_payload = subtables.get("Projects_XP1") if isinstance(subtables.get("Projects_XP1"), dict) else entry.get("projects_xp1") if isinstance(entry.get("projects_xp1"), dict) else {}
        self._xp1_editor.set_payload(xp1_payload if isinstance(xp1_payload, dict) else {})

        xp2_payload = subtables.get("Projects_XP2") if isinstance(subtables.get("Projects_XP2"), dict) else entry.get("projects_xp2") if isinstance(entry.get("projects_xp2"), dict) else {}
        self._xp2_editor.set_payload(xp2_payload if isinstance(xp2_payload, dict) else {})

        building_costs = subtables.get("Project_BuildingCosts") if isinstance(subtables.get("Project_BuildingCosts"), list) else entry.get("project_building_costs") if isinstance(entry.get("project_building_costs"), list) else []
        self._building_costs_editor.set_payload(building_costs if isinstance(building_costs, list) else [])

        great_person_points = subtables.get("Project_GreatPersonPoints") if isinstance(subtables.get("Project_GreatPersonPoints"), list) else entry.get("project_great_person_points") if isinstance(entry.get("project_great_person_points"), list) else []
        self._great_person_points_editor.set_payload(great_person_points if isinstance(great_person_points, list) else [])

        resource_costs = subtables.get("Project_ResourceCosts") if isinstance(subtables.get("Project_ResourceCosts"), list) else entry.get("project_resource_costs") if isinstance(entry.get("project_resource_costs"), list) else []
        self._resource_costs_editor.set_payload(resource_costs if isinstance(resource_costs, list) else [])

        yield_conversions = subtables.get("Project_YieldConversions") if isinstance(subtables.get("Project_YieldConversions"), list) else entry.get("project_yield_conversions") if isinstance(entry.get("project_yield_conversions"), list) else []
        self._yield_conversions_editor.set_payload(yield_conversions if isinstance(yield_conversions, list) else [])

        prereqs = subtables.get("ProjectPrereqs") if isinstance(subtables.get("ProjectPrereqs"), list) else entry.get("project_prereqs") if isinstance(entry.get("project_prereqs"), list) else []
        self._prereqs_editor.set_payload(prereqs if isinstance(prereqs, list) else [])

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()
        projects_mode = self._mode_editor.export_payload()
        projects_xp1 = self._xp1_editor.export_payload()
        projects_xp2 = self._xp2_editor.export_payload()
        project_building_costs = self._building_costs_editor.export_payload()
        project_great_person_points = self._great_person_points_editor.export_payload()
        project_resource_costs = self._resource_costs_editor.export_payload()
        project_yield_conversions = self._yield_conversions_editor.export_payload()
        project_prereqs = self._prereqs_editor.export_payload()
        payload.update(
            {
                "projects_mode": projects_mode,
                "projects_xp1": projects_xp1,
                "projects_xp2": projects_xp2,
                "project_building_costs": project_building_costs,
                "project_great_person_points": project_great_person_points,
                "project_resource_costs": project_resource_costs,
                "project_yield_conversions": project_yield_conversions,
                "project_prereqs": project_prereqs,
                "subtables": {
                    "Projects_MODE": projects_mode,
                    "Projects_XP1": projects_xp1,
                    "Projects_XP2": projects_xp2,
                    "Project_BuildingCosts": project_building_costs,
                    "Project_GreatPersonPoints": project_great_person_points,
                    "Project_ResourceCosts": project_resource_costs,
                    "Project_YieldConversions": project_yield_conversions,
                    "ProjectPrereqs": project_prereqs,
                },
            }
        )
        return payload

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class BeliefCompositeEditor(QWidget):
    dataChanged = pyqtSignal()
    duplicateRequested = pyqtSignal(dict)

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._loading = False

        self._main_editor = MainTableEditor(
            schema=build_beliefs_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )
        self._duplicate_button = QPushButton("复制该信仰")
        self._duplicate_button.clicked.connect(self._request_duplicate)

        self._main_editor.dataChanged.connect(self._emit_data_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)

        actions = QHBoxLayout()
        actions.addWidget(self._duplicate_button)
        actions.addStretch(1)
        layout.addLayout(actions)

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._loading = False

    def export_entry(self) -> dict[str, object]:
        return self._main_editor.export_entry()

    def _request_duplicate(self) -> None:
        payload = self.export_entry()
        self.duplicateRequested.emit(payload)

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class _ReqSetSearchDialog(QDialog):
    """搜索 SubjectRequirementSetId：数据库模式 / 自建模式，三列显示，双击选中。"""

    reqsetSelected = pyqtSignal(str, object)  # reqset_id, imported_args (dict) or None for self-built

    def __init__(
        self,
        text_search_provider: Callable[[str], str],
        custom_reqset_provider: Callable[[], list[dict[str, object]]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择 SubjectRequirementSetId")
        self.resize(780, 520)

        self._text_search_provider = text_search_provider
        self._custom_reqset_provider = custom_reqset_provider
        self._db_rows: list[tuple[str, str, str, dict[str, object]]] = []  # (rsid, desc_text, stmt_text, args)
        self._custom_rows: list[dict[str, object]] = []
        self._mode = "db"  # "db" or "custom"

        layout = QVBoxLayout(self)

        # Search bar
        search_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索条件集ID…")
        self._search_edit.textChanged.connect(self._on_search)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        # Mode toggles
        toggle_row = QHBoxLayout()
        self._db_check = QCheckBox("仅数据库")
        self._db_check.setChecked(True)
        self._db_check.toggled.connect(self._on_mode_changed)
        toggle_row.addWidget(self._db_check)
        self._custom_check = QCheckBox("仅自建")
        self._custom_check.toggled.connect(self._on_mode_changed)
        toggle_row.addWidget(self._custom_check)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["条件集ID", "描述文本", "台词文本"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self._on_select)
        btn_row.addWidget(select_btn)
        layout.addLayout(btn_row)

        # Load data
        self._load_db_data()
        self._load_custom_data()
        self._populate_table()

    def _load_db_data(self) -> None:
        from ...app.settings_store import load_settings
        settings = load_settings()
        gdb = settings.game_db_path
        if not gdb or not Path(gdb).exists():
            return
        try:
            conn = sqlite3.connect(str(gdb))
            # For each unique SubjectRequirementSetId, get the first Modifier's description/statement
            rows = conn.execute(
                "SELECT m.SubjectRequirementSetId, m.ModifierId FROM Modifiers m "
                "WHERE m.ModifierType = 'MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER' "
                "AND m.SubjectRequirementSetId IS NOT NULL "
                "ORDER BY m.SubjectRequirementSetId"
            ).fetchall()
            # Group by SubjectRequirementSetId, keep first ModifierId
            seen: set[str] = set()
            first_mod: dict[str, str] = {}
            for rsid, mod_id in rows:
                rs = str(rsid)
                if rs not in seen:
                    seen.add(rs)
                    first_mod[rs] = str(mod_id)

            # Get arguments for each first modifier
            for rsid, mod_id in first_mod.items():
                args_rows = conn.execute(
                    "SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (mod_id,)
                ).fetchall()
                args: dict[str, object] = {}
                desc_tag = ""
                stmt_tag = ""
                for name, value in args_rows:
                    n = str(name)
                    v = str(value or "")
                    args[n] = v
                    if n == "SimpleModifierDescription":
                        desc_tag = v
                    elif n == "StatementKey":
                        stmt_tag = v
                desc_text = self._text_search_provider(desc_tag) if desc_tag else ""
                stmt_text = self._text_search_provider(stmt_tag) if stmt_tag else ""
                self._db_rows.append((rsid, desc_text, stmt_text, args))
            conn.close()
        except sqlite3.Error:
            pass

    def _load_custom_data(self) -> None:
        self._custom_rows = self._custom_reqset_provider() if callable(self._custom_reqset_provider) else []

    def _on_mode_changed(self) -> None:
        if self._db_check.isChecked() and self._custom_check.isChecked():
            # Both checked — not allowed, reset
            if self._mode == "custom":
                self._custom_check.setChecked(False)
                self._mode = "db"
            else:
                self._db_check.setChecked(False)
                self._mode = "custom"
        elif self._db_check.isChecked():
            self._mode = "db"
        elif self._custom_check.isChecked():
            self._mode = "custom"
        else:
            # Neither checked — keep current
            if self._mode == "db":
                self._db_check.setChecked(True)
            else:
                self._custom_check.setChecked(True)
        self._populate_table()

    def _on_search(self, _text: str) -> None:
        self._populate_table()

    def _populate_table(self) -> None:
        keyword = self._search_edit.text().strip().lower()
        self._table.setRowCount(0)

        if self._mode == "db":
            self._table.setHorizontalHeaderLabels(["条件集ID", "描述文本", "台词文本"])
            rows_to_show = self._db_rows
        else:
            self._table.setHorizontalHeaderLabels(["条件集ID", "条件集注释", "条件注释"])
            rows_to_show = []  # type: ignore[assignment]

        if self._mode == "db":
            for rsid, desc_text, stmt_text, _args in self._db_rows:
                if keyword and keyword not in rsid.lower() and keyword not in desc_text:
                    continue
                r = self._table.rowCount()
                self._table.insertRow(r)
                self._table.setItem(r, 0, QTableWidgetItem(rsid))
                self._table.setItem(r, 1, QTableWidgetItem(desc_text))
                self._table.setItem(r, 2, QTableWidgetItem(stmt_text))
                self._table.item(r, 0).setData(Qt.ItemDataRole.UserRole, rsid)
        else:
            for entry in self._custom_rows:
                if not isinstance(entry, dict):
                    continue
                rsid = str(entry.get("requirement_set_id") or entry.get("RequirementSetId") or "").strip()
                if not rsid:
                    continue
                if keyword and keyword not in rsid.lower():
                    continue
                comment = str(entry.get("comment") or "")
                # Requirement comments: comma-joined
                reqs = entry.get("bound_requirements") or entry.get("requirements") or []
                req_comments: list[str] = []
                if isinstance(reqs, list):
                    for req in reqs:
                        if isinstance(req, dict):
                            rc = str(req.get("comment") or "")
                            if rc:
                                req_comments.append(rc)
                req_comment_str = ", ".join(req_comments) if req_comments else ""
                r = self._table.rowCount()
                self._table.insertRow(r)
                self._table.setItem(r, 0, QTableWidgetItem(rsid))
                self._table.setItem(r, 1, QTableWidgetItem(comment))
                self._table.setItem(r, 2, QTableWidgetItem(req_comment_str))
                self._table.item(r, 0).setData(Qt.ItemDataRole.UserRole, rsid)

    def _on_double_click(self, row: int, _col: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        rsid = item.data(Qt.ItemDataRole.UserRole)
        if not rsid:
            return
        if self._mode == "db":
            # Find the args for this rsid
            for _rsid, _desc, _stmt, args in self._db_rows:
                if _rsid == rsid:
                    self.reqsetSelected.emit(str(rsid), dict(args))
                    break
        else:
            self.reqsetSelected.emit(str(rsid), None)
        self.accept()

    def _on_select(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._on_double_click(row, 0)


class AgendaModifierEditor(QWidget):
    """单个议程 Modifier 编辑器（无外框，由列表容器管理删除）。"""

    dataChanged = pyqtSignal()

    def __init__(
        self,
        text_search_provider: Callable[[str], str],
        custom_reqset_provider: Callable[[], list[dict[str, object]]],
    ) -> None:
        super().__init__()
        self._loading = False
        self._agenda_type = ""
        self._prefix = ""
        self._leader_name = ""
        self._text_search_provider = text_search_provider
        self._custom_reqset_provider = custom_reqset_provider
        self._imported_desc_ref = ""
        self._imported_stmt_ref = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # SubjectRequirementSetId — button + display
        rs_row = QHBoxLayout()
        rs_row.addWidget(QLabel("SubjectRequirementSetId"))
        self._reqset_display = QLineEdit()
        self._reqset_display.setReadOnly(True)
        self._reqset_display.setPlaceholderText("点击右侧按钮选择条件集…")
        rs_row.addWidget(self._reqset_display, 1)
        self._select_reqset_btn = QPushButton("选择条件集")
        self._select_reqset_btn.clicked.connect(self._open_search_dialog)
        rs_row.addWidget(self._select_reqset_btn)
        layout.addLayout(rs_row)

        # ModifierId + auto-name button
        mod_id_row = QHBoxLayout()
        mod_id_row.addWidget(QLabel("ModifierId"))
        self._modifier_id_edit = QLineEdit()
        self._modifier_id_edit.textChanged.connect(self._on_modifier_id_changed)
        mod_id_row.addWidget(self._modifier_id_edit, 1)
        self._auto_name_btn = QPushButton("自动命名")
        self._auto_name_btn.clicked.connect(self._auto_name)
        mod_id_row.addWidget(self._auto_name_btn)
        layout.addLayout(mod_id_row)

        # Numeric args grid
        num_grid = QGridLayout()
        num_grid.setHorizontalSpacing(8)

        num_grid.addWidget(QLabel("InitialValue"), 0, 0)
        self._initial_value = QSpinBox()
        self._initial_value.setRange(-999, 999)
        self._initial_value.setValue(0)
        self._initial_value.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._initial_value, 0, 1)

        num_grid.addWidget(QLabel("MaxValue"), 0, 2)
        self._max_value = QSpinBox()
        self._max_value.setRange(-999, 999)
        self._max_value.setSpecialValueText("无限制")
        self._max_value.setValue(0)
        self._max_value.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._max_value, 0, 3)

        num_grid.addWidget(QLabel("IncrementTurns"), 1, 0)
        self._increment_turns = QSpinBox()
        self._increment_turns.setRange(0, 999)
        self._increment_turns.setValue(0)
        self._increment_turns.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._increment_turns, 1, 1)

        num_grid.addWidget(QLabel("IncrementValue"), 1, 2)
        self._increment_value = QSpinBox()
        self._increment_value.setRange(-999, 999)
        self._increment_value.setValue(0)
        self._increment_value.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._increment_value, 1, 3)

        num_grid.addWidget(QLabel("ReductionTurns"), 2, 0)
        self._reduction_turns = QSpinBox()
        self._reduction_turns.setRange(0, 999)
        self._reduction_turns.setValue(0)
        self._reduction_turns.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._reduction_turns, 2, 1)

        num_grid.addWidget(QLabel("ReductionValue"), 2, 2)
        self._reduction_value = QSpinBox()
        self._reduction_value.setRange(-999, 999)
        self._reduction_value.setValue(0)
        self._reduction_value.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._reduction_value, 2, 3)

        num_grid.addWidget(QLabel("MessageThrottle"), 3, 0)
        self._message_throttle = QSpinBox()
        self._message_throttle.setRange(0, 999)
        self._message_throttle.setValue(20)
        self._message_throttle.valueChanged.connect(lambda _: self._notify_change())
        num_grid.addWidget(self._message_throttle, 3, 1)
        layout.addLayout(num_grid)

        # HiddenAgenda checkbox
        self._hidden_agenda = QCheckBox("HiddenAgenda（隐藏议程，触发后可见）")
        self._hidden_agenda.toggled.connect(self._on_hidden_toggled)
        layout.addWidget(self._hidden_agenda)

        # SimpleModifierDescription: Chinese text + auto LOC tag + reference
        layout.addWidget(QLabel("SimpleModifierDescription（中文描述）"))
        self._simple_desc_text = QLineEdit()
        self._simple_desc_text.setPlaceholderText("输入中文描述…")
        self._simple_desc_text.textChanged.connect(lambda _: self._notify_change())
        layout.addWidget(self._simple_desc_text)
        loc_row1 = QHBoxLayout()
        loc_row1.addWidget(QLabel("LOC Tag:"))
        self._simple_desc_loc = QLineEdit()
        self._simple_desc_loc.setReadOnly(True)
        loc_row1.addWidget(self._simple_desc_loc, 1)
        layout.addLayout(loc_row1)
        self._simple_desc_ref = QLabel("")
        self._simple_desc_ref.setObjectName("pageInfoLabel")
        self._simple_desc_ref.setWordWrap(True)
        layout.addWidget(self._simple_desc_ref)

        # StatementKey: Chinese text + auto LOC tag + reference
        self._stmt_group = QVBoxLayout()
        stmt_label = QLabel("StatementKey 台词（中文文本）")
        self._stmt_group.addWidget(stmt_label)
        self._statement_text = QLineEdit()
        self._statement_text.setPlaceholderText("输入外交台词…")
        self._statement_text.textChanged.connect(lambda _: self._notify_change())
        self._stmt_group.addWidget(self._statement_text)
        loc_row2 = QHBoxLayout()
        loc_row2.addWidget(QLabel("LOC Tag:"))
        self._statement_loc = QLineEdit()
        self._statement_loc.setReadOnly(True)
        loc_row2.addWidget(self._statement_loc, 1)
        self._stmt_group.addLayout(loc_row2)
        self._statement_ref = QLabel("")
        self._statement_ref.setObjectName("pageInfoLabel")
        self._statement_ref.setWordWrap(True)
        self._stmt_group.addWidget(self._statement_ref)
        layout.addLayout(self._stmt_group)

        layout.addStretch(1)

    # ── help text ──────────────────────────────────────────────────────

    def display_name(self) -> str:
        mod_id = self._modifier_id_edit.text().strip()
        if mod_id:
            return mod_id
        rsid = self._reqset_display.text().strip()
        return rsid or "新 Modifier"

    # ── naming helpers ─────────────────────────────────────────────────

    def _reqset_short(self) -> str:
        txt = self._reqset_display.text().strip()
        if not txt:
            return ""
        for prefix in ("PLAYER_", "PLAYERS_", "AGENDA_REQUIRE_", "STANDARD_DIPLOMATIC_"):
            if txt.startswith(prefix):
                return txt[len(prefix):]
        return txt

    def _gen_modifier_id(self) -> str:
        short = self._reqset_short()
        if not self._prefix or not short:
            return ""
        return f"MODIFIER_{self._prefix}_{short}"

    def _gen_simple_desc_loc(self) -> str:
        mod_id = self._modifier_id_edit.text().strip()
        return f"LOC_{mod_id}_DESCRIPTION" if mod_id else ""

    def _gen_statement_loc(self) -> str:
        mod_id = self._modifier_id_edit.text().strip()
        return f"LOC_{mod_id}_STATEMENT" if mod_id else ""

    def _auto_name(self) -> None:
        mod_id = self._gen_modifier_id()
        if mod_id:
            self._modifier_id_edit.setText(mod_id)
        self._sync_loc_tags()

    def _on_modifier_id_changed(self, _text: str) -> None:
        self._sync_loc_tags()
        self._notify_change()

    def _sync_loc_tags(self) -> None:
        self._simple_desc_loc.setText(self._gen_simple_desc_loc())
        self._statement_loc.setText(self._gen_statement_loc())
        self._update_ref_texts()

    # ── search dialog ─────────────────────────────────────────────────

    def _open_search_dialog(self) -> None:
        dlg = _ReqSetSearchDialog(
            text_search_provider=self._text_search_provider,
            custom_reqset_provider=self._custom_reqset_provider,
            parent=self,
        )
        dlg.reqsetSelected.connect(self._on_reqset_selected)
        dlg.exec()

    def _on_reqset_selected(self, rsid: str, imported_args: object) -> None:
        self._reqset_display.setText(rsid)
        if isinstance(imported_args, dict):
            self._loading = True
            args = dict(imported_args)
            def _set_int(spin: QSpinBox, key: str, default: int = 0) -> None:
                try:
                    spin.setValue(int(args.get(key, default)))
                except (TypeError, ValueError):
                    spin.setValue(default)
            _set_int(self._initial_value, "InitialValue", 0)
            _set_int(self._max_value, "MaxValue", 0)
            _set_int(self._increment_turns, "IncrementTurns", 0)
            _set_int(self._increment_value, "IncrementValue", 0)
            _set_int(self._reduction_turns, "ReductionTurns", 0)
            _set_int(self._reduction_value, "ReductionValue", 0)
            _set_int(self._message_throttle, "MessageThrottle", 20)
            self._hidden_agenda.setChecked(args.get("HiddenAgenda", "0") == "1")
            # Save imported game LOC tag texts as reference
            imported_desc_tag = str(args.get("SimpleModifierDescription") or "")
            imported_stmt_tag = str(args.get("StatementKey") or "")
            self._imported_desc_ref = self._text_search_provider(imported_desc_tag) if imported_desc_tag and callable(self._text_search_provider) else ""
            self._imported_stmt_ref = self._text_search_provider(imported_stmt_tag) if imported_stmt_tag and callable(self._text_search_provider) else ""
            self._loading = False
        if not self._modifier_id_edit.text().strip():
            self._auto_name()
        self._notify_change()

    # ── data load / save ──────────────────────────────────────────────

    def set_context(self, agenda_type: str, prefix: str, abbr: str, leader_name: str) -> None:
        self._agenda_type = _safe_text(agenda_type)
        self._prefix = _safe_text(prefix)
        self._leader_name = leader_name

    def set_payload(self, payload: dict[str, object]) -> None:
        self._loading = True
        self._modifier_id_edit.setText(str(payload.get("ModifierId") or ""))
        self._reqset_display.setText(str(payload.get("SubjectRequirementSetId") or ""))

        args = payload.get("Arguments")
        args_dict: dict[str, object] = dict(args) if isinstance(args, dict) else {}

        def _int_from(key: str, default: int = 0) -> int:
            try: return int(args_dict.get(key, default))
            except (TypeError, ValueError): return default

        self._initial_value.setValue(_int_from("InitialValue", 0))
        self._max_value.setValue(_int_from("MaxValue", 0))
        self._increment_turns.setValue(_int_from("IncrementTurns", 0))
        self._increment_value.setValue(_int_from("IncrementValue", 0))
        self._reduction_turns.setValue(_int_from("ReductionTurns", 0))
        self._reduction_value.setValue(_int_from("ReductionValue", 0))
        self._message_throttle.setValue(_int_from("MessageThrottle", 20))
        self._hidden_agenda.setChecked(_int_from("HiddenAgenda", 0) != 0)
        self._simple_desc_text.setText(str(args_dict.get("SimpleModifierText", "")))
        self._statement_text.setText(str(args_dict.get("StatementText", "")))
        self._imported_desc_ref = str(args_dict.get("_ImportedDescRef", ""))
        self._imported_stmt_ref = str(args_dict.get("_ImportedStmtRef", ""))
        self._sync_loc_tags()
        self._loading = False

    def export_payload(self) -> dict[str, object]:
        args: dict[str, str] = {}
        def _add_int(key: str, spin: QSpinBox, skip_zero: bool = True) -> None:
            val = spin.value()
            if not skip_zero or val != 0:
                args[key] = str(val)
        _add_int("InitialValue", self._initial_value, skip_zero=False)
        _add_int("MaxValue", self._max_value)
        _add_int("IncrementTurns", self._increment_turns)
        _add_int("IncrementValue", self._increment_value)
        _add_int("ReductionTurns", self._reduction_turns)
        _add_int("ReductionValue", self._reduction_value)
        _add_int("MessageThrottle", self._message_throttle)
        if self._hidden_agenda.isChecked():
            args["HiddenAgenda"] = "1"

        simple_loc = self._simple_desc_loc.text().strip()
        stmt_loc = self._statement_loc.text().strip()
        if simple_loc:
            args["SimpleModifierDescription"] = simple_loc
        if stmt_loc:
            args["StatementKey"] = stmt_loc
        simple_text = self._simple_desc_text.text().strip()
        stmt_text = self._statement_text.text().strip()
        if simple_text:
            args["SimpleModifierText"] = simple_text
        if stmt_text:
            args["StatementText"] = stmt_text
        if self._imported_desc_ref:
            args["_ImportedDescRef"] = self._imported_desc_ref
        if self._imported_stmt_ref:
            args["_ImportedStmtRef"] = self._imported_stmt_ref

        return {
            "ModifierId": self._modifier_id_edit.text().strip(),
            "ModifierType": "MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER",
            "SubjectRequirementSetId": self._reqset_display.text().strip(),
            "Arguments": args,
        }

    # ── visibility / reference ────────────────────────────────────────

    def _on_hidden_toggled(self, checked: bool) -> None:
        for i in range(self._stmt_group.count()):
            w = self._stmt_group.itemAt(i).widget()
            if w is not None:
                w.setVisible(not checked)
        self._update_ref_texts()
        self._notify_change()

    def _update_ref_texts(self) -> None:
        if getattr(self, '_imported_desc_ref', ''):
            self._simple_desc_ref.setText(f"参考（游戏原文）: {self._imported_desc_ref}")
        else:
            self._simple_desc_ref.setText("")

        if getattr(self, '_imported_stmt_ref', ''):
            self._statement_ref.setText(f"参考（游戏原文）: {self._imported_stmt_ref}")
        else:
            self._statement_ref.setText("")

    def _notify_change(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class AgendaModifierListEditor(QWidget):
    """左列 Modifier 列表 + 右侧编辑区，支持增删切换。"""

    dataChanged = pyqtSignal()

    def __init__(
        self,
        text_search_provider: Callable[[str], str],
        custom_reqset_provider: Callable[[], list[dict[str, object]]],
    ) -> None:
        super().__init__()
        self._loading = False
        self._agenda_type = ""
        self._prefix = ""
        self._abbr = ""
        self._leader_name = ""
        self._text_search_provider = text_search_provider
        self._custom_reqset_provider = custom_reqset_provider
        self._editors: list[AgendaModifierEditor] = []

        group = QGroupBox("议程 Modifier")
        outer = QVBoxLayout(group)

        # Splitter: left list | right editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._modifier_list = QListWidget()
        self._modifier_list.currentRowChanged.connect(self._on_list_selection_changed)
        left_layout.addWidget(self._modifier_list, 1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("＋ 添加")
        add_btn.clicked.connect(self._add_modifier)
        btn_row.addWidget(add_btn)
        self._remove_btn = QPushButton("✕ 删除")
        self._remove_btn.clicked.connect(self._remove_selected)
        self._remove_btn.setEnabled(False)
        btn_row.addWidget(self._remove_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # Right panel — QStackedWidget of editors
        self._editor_stack = QStackedWidget()
        self._editor_stack.addWidget(QLabel("请添加或选择一个 Modifier"))
        splitter.addWidget(self._editor_stack)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 520])

        outer.addWidget(splitter)
        self.setLayout(outer)

    def set_context(self, agenda_type: str, prefix: str, abbr: str, leader_name: str) -> None:
        self._agenda_type = _safe_text(agenda_type)
        self._prefix = _safe_text(prefix)
        self._abbr = _safe_text(abbr)
        self._leader_name = leader_name
        for e in self._editors:
            e.set_context(agenda_type, prefix, abbr, leader_name)

    def set_payload(self, modifiers: list[dict[str, object]]) -> None:
        self._loading = True
        self._clear_all()
        for mod in modifiers:
            if isinstance(mod, dict):
                self._add_modifier_widget(mod)
        if self._editors:
            self._modifier_list.setCurrentRow(0)
        self._loading = False

    def export_payload(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for e in self._editors:
            payload = e.export_payload()
            if payload.get("ModifierId") or payload.get("SubjectRequirementSetId"):
                result.append(payload)
        return result

    def _add_modifier(self) -> None:
        self._add_modifier_widget({})
        self._modifier_list.setCurrentRow(len(self._editors) - 1)

    def _add_modifier_widget(self, payload: dict[str, object]) -> None:
        e = AgendaModifierEditor(
            text_search_provider=self._text_search_provider,
            custom_reqset_provider=self._custom_reqset_provider,
        )
        e.set_context(self._agenda_type, self._prefix, self._abbr, getattr(self, '_leader_name', ''))
        e.set_payload(payload)
        e.dataChanged.connect(self._emit_data_changed)
        self._editors.append(e)

        idx = self._editor_stack.addWidget(e)  # add after placeholder
        item = QListWidgetItem(e.display_name())
        item.setData(Qt.ItemDataRole.UserRole, idx)
        self._modifier_list.addItem(item)

    def _on_list_selection_changed(self, row: int) -> None:
        self._remove_btn.setEnabled(row >= 0)
        if 0 <= row < len(self._editors):
            item = self._modifier_list.item(row)
            stack_idx = item.data(Qt.ItemDataRole.UserRole) if item else -1
            if stack_idx >= 0 and stack_idx < self._editor_stack.count():
                self._editor_stack.setCurrentIndex(stack_idx)
        else:
            self._editor_stack.setCurrentIndex(0)  # placeholder

    def _remove_selected(self) -> None:
        row = self._modifier_list.currentRow()
        if row < 0 or row >= len(self._editors):
            return
        self._modifier_list.takeItem(row)
        editor = self._editors.pop(row)
        self._editor_stack.removeWidget(editor)
        editor.deleteLater()
        # Update data indices for remaining items
        for r in range(self._modifier_list.count()):
            item = self._modifier_list.item(r)
            if item and self._editor_stack.count() > r + 1:
                item.setData(Qt.ItemDataRole.UserRole, r + 1)
        self._emit_data_changed()

    def _clear_all(self) -> None:
        self._modifier_list.clear()
        for e in self._editors:
            self._editor_stack.removeWidget(e)
            e.deleteLater()
        self._editors.clear()
        self._editor_stack.setCurrentIndex(0)

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        # Refresh list item names
        for r, e in enumerate(self._editors):
            item = self._modifier_list.item(r)
            if item:
                item.setText(e.display_name())
        self.dataChanged.emit()


def _agenda_table_hint(table: str) -> str:
    hints: dict[str, str] = {
        "HistoricalAgendas": "绑定该议程所属领袖。每个领袖建议只绑一个议程。",
        "AgendaTraits": "自动生成 TraitType = TRAIT_{AgendaType}，始终输出。",
        "ExclusiveAgendas": "可选：与随机议程互斥。AgendaTwo 候选来自游戏库 RandomAgendas。",
        "AiLists": "AI 偏好组。System 决定偏好类型，ListType 可自动生成或手填。",
        "AgendaModifiers": "议程外交效果 Modifier (MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER)。选择 SubjectRequirementSetId 以从数据库导入官方模版。ModifierString(Preview) 自动生成。",
    }
    return hints.get(table, "")


class _LeaderDropdown(QWidget):
    """下拉选择当前工程中的领袖。"""

    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(lambda _: self.changed.emit())

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("LeaderType"))
        layout.addWidget(self._combo, 1)
        self.setLayout(layout)

    def set_leader_list(self, leaders: list[tuple[str, str]]) -> None:
        current = self._combo.currentData()
        self._combo.blockSignals(True)
        self._combo.clear()
        for leader_type, display_name in leaders:
            self._combo.addItem(display_name, leader_type)
        if current:
            idx = self._combo.findData(current)
            if idx >= 0:
                self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)

    def current_leader_type(self) -> str:
        return str(self._combo.currentData() or "")

    def set_current_leader_type(self, leader_type: str) -> None:
        idx = self._combo.findData(leader_type)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

    def add_leader_if_missing(self, leader_type: str, display_name: str) -> None:
        idx = self._combo.findData(leader_type)
        if idx < 0:
            self._combo.addItem(display_name, leader_type)


class HistoricalAgendasEditor(QWidget):
    """领袖绑定 + 外交告别语（LOC Tag 自动生成，只读）。"""

    dataChanged = pyqtSignal()

    def __init__(
        self,
        leader_entries_provider: Callable[[], list[dict[str, str]]],
        text_search_provider: Callable[[str], str],
    ) -> None:
        super().__init__()
        self._loading = False
        self._leader_dropdown = _LeaderDropdown()
        self._leader_dropdown.changed.connect(self._on_leader_changed)

        self._leader_entries_provider = leader_entries_provider
        self._text_search_provider = text_search_provider

        group = QGroupBox("HistoricalAgendas（领袖绑定）")
        layout = QVBoxLayout(group)
        tip = QLabel(_agenda_table_hint("HistoricalAgendas"))
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addWidget(self._leader_dropdown)

        # Exit Kudo
        layout.addWidget(QLabel("赞许告别语（中文）"))
        self._exit_kudo_text = QLineEdit()
        self._exit_kudo_text.setPlaceholderText("输入中文告别语（赞许）…")
        self._exit_kudo_text.textChanged.connect(lambda _: self.dataChanged.emit())
        layout.addWidget(self._exit_kudo_text)

        kudo_tag_row = QHBoxLayout()
        kudo_tag_row.addWidget(QLabel("LOC Tag（自动）"))
        self._exit_kudo_tag = QLineEdit()
        self._exit_kudo_tag.setReadOnly(True)
        kudo_tag_row.addWidget(self._exit_kudo_tag, 1)
        layout.addLayout(kudo_tag_row)

        self._exit_kudo_ref = QLabel("")
        self._exit_kudo_ref.setObjectName("pageInfoLabel")
        self._exit_kudo_ref.setWordWrap(True)
        layout.addWidget(self._exit_kudo_ref)

        # Exit Warning
        layout.addWidget(QLabel("警告告别语（中文）"))
        self._exit_warn_text = QLineEdit()
        self._exit_warn_text.setPlaceholderText("输入中文告别语（警告）…")
        self._exit_warn_text.textChanged.connect(lambda _: self.dataChanged.emit())
        layout.addWidget(self._exit_warn_text)

        warn_tag_row = QHBoxLayout()
        warn_tag_row.addWidget(QLabel("LOC Tag（自动）"))
        self._exit_warn_tag = QLineEdit()
        self._exit_warn_tag.setReadOnly(True)
        warn_tag_row.addWidget(self._exit_warn_tag, 1)
        layout.addLayout(warn_tag_row)

        self._exit_warn_ref = QLabel("")
        self._exit_warn_ref.setObjectName("pageInfoLabel")
        self._exit_warn_ref.setWordWrap(True)
        layout.addWidget(self._exit_warn_ref)

        self.setLayout(layout)

    def _leader_name(self) -> str:
        """Extract leader name from LeaderType: 'LEADER_SIQI_MORTIS' -> 'SIQI_MORTIS'"""
        lt = self._leader_dropdown.current_leader_type()
        if lt.startswith("LEADER_"):
            return lt[len("LEADER_"):]
        return lt

    def _gen_exit_kudo_tag(self) -> str:
        name = self._leader_name()
        return f"LOC_DIPLO_KUDO_EXIT_LEADER_{name}_ANY" if name else ""

    def _gen_exit_warn_tag(self) -> str:
        name = self._leader_name()
        return f"LOC_DIPLO_WARNING_EXIT_LEADER_{name}_ANY" if name else ""

    def _on_leader_changed(self) -> None:
        self._sync_loc_tags()
        self._update_exit_refs()
        self.dataChanged.emit()

    def _sync_loc_tags(self) -> None:
        self._exit_kudo_tag.setText(self._gen_exit_kudo_tag())
        self._exit_warn_tag.setText(self._gen_exit_warn_tag())

    def refresh_leader_list(self) -> None:
        entries = self._leader_entries_provider() if callable(self._leader_entries_provider) else []
        leaders: list[tuple[str, str]] = []
        for entry in entries:
            if isinstance(entry, dict):
                lt = str(entry.get("type") or "").strip()
                if lt:
                    name = str(entry.get("name") or "").strip() or lt
                    leaders.append((lt, f"{lt}（{name}）"))
        self._leader_dropdown.set_leader_list(leaders)

    def current_leader_type(self) -> str:
        return self._leader_dropdown.current_leader_type()

    def set_entry(self, payload: dict[str, object]) -> None:
        self._loading = True
        self.refresh_leader_list()
        leader_type = str(payload.get("LeaderType") or "").strip()
        if leader_type:
            self._leader_dropdown.add_leader_if_missing(leader_type, leader_type)
        self._leader_dropdown.set_current_leader_type(leader_type)
        self._sync_loc_tags()

        self._exit_kudo_text.setText(str(payload.get("ExitKudoText") or ""))
        self._exit_warn_text.setText(str(payload.get("ExitWarnText") or ""))
        self._update_exit_refs()
        self._loading = False

    def export_payload(self) -> dict[str, object]:
        result: dict[str, object] = {
            "LeaderType": self._leader_dropdown.current_leader_type(),
        }
        kudo_text = self._exit_kudo_text.text().strip()
        warn_text = self._exit_warn_text.text().strip()
        kudo_tag = self._gen_exit_kudo_tag()
        warn_tag = self._gen_exit_warn_tag()
        if kudo_text and kudo_tag:
            result["ExitKudoStatementKey"] = kudo_tag
            result["ExitKudoText"] = kudo_text
        if warn_text and warn_tag:
            result["ExitWarningStatementKey"] = warn_tag
            result["ExitWarnText"] = warn_text
        return result

    def _update_exit_refs(self) -> None:
        kudo_fallback = self._text_search_provider("LOC_DIPLO_KUDO_EXIT_ANY_ANY") if callable(self._text_search_provider) else ""
        warn_fallback = self._text_search_provider("LOC_DIPLO_WARNING_EXIT_ANY_ANY") if callable(self._text_search_provider) else ""
        self._exit_kudo_ref.setText(f"参考保底: {kudo_fallback}" if kudo_fallback else "")
        self._exit_warn_ref.setText(f"参考保底: {warn_fallback}" if warn_fallback else "")


class ExclusiveAgendasEditor(QWidget):
    """ExclusiveAgendas 可选副表 — 多行，AgendaTwo 从 RandomAgendas 选择。"""

    dataChanged = pyqtSignal()

    def __init__(self, random_agendas_provider: Callable[[], list[tuple[str, str]]]) -> None:
        super().__init__()
        self._agenda_type = ""
        self._loading = False
        self._random_agendas: list[tuple[str, str]] = []
        self._rows: list[dict[str, str]] = []
        self._random_agendas_provider = random_agendas_provider

        group = QGroupBox("ExclusiveAgendas（互斥议程，可选）")
        layout = QVBoxLayout(group)
        tip = QLabel(_agenda_table_hint("ExclusiveAgendas"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        top_row = QHBoxLayout()
        self._agenda_type_display = QLineEdit()
        self._agenda_type_display.setReadOnly(True)
        top_row.addWidget(QLabel("AgendaOne"))
        top_row.addWidget(self._agenda_type_display, 1)
        self._add_button = QPushButton("＋ 添加互斥")
        self._add_button.clicked.connect(self._add_row)
        top_row.addWidget(self._add_button)
        layout.addLayout(top_row)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["AgendaTwo（随机议程）", "操作"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 56)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        self.setLayout(layout)

    def set_agenda_type(self, agenda_type: str) -> None:
        self._agenda_type = _safe_text(agenda_type)
        self._agenda_type_display.setText(self._agenda_type)

    def set_payload(self, rows: list[dict[str, object]]) -> None:
        self._loading = True
        self._random_agendas = self._random_agendas_provider() if callable(self._random_agendas_provider) else []
        self._rows = []
        self._table.setRowCount(0)
        for entry in rows:
            if isinstance(entry, dict):
                agenda_two = _safe_text(entry.get("AgendaTwo"))
                self._rows.append({"AgendaTwo": agenda_two})
                self._append_table_row(agenda_two)
        self._loading = False

    def export_payload(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for data in self._rows:
            agenda_two = _safe_text(data.get("AgendaTwo"))
            if agenda_two:
                result.append({
                    "AgendaOne": self._agenda_type,
                    "AgendaTwo": agenda_two,
                })
        return result

    def _add_row(self) -> None:
        idx = self._table.rowCount()
        self._table.insertRow(idx)
        combo = QComboBox()
        combo.addItem("", "")
        for ra_type, ra_display in self._random_agendas:
            combo.addItem(ra_display, ra_type)
        combo.setEditable(True)
        combo.currentTextChanged.connect(lambda text, r=idx: self._on_row_text(r, text))
        self._table.setCellWidget(idx, 0, combo)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(32, 26)
        del_btn.clicked.connect(lambda *_a, r=idx: self._delete_row(r))
        self._table.setCellWidget(idx, 1, del_btn)

        self._rows.append({"AgendaTwo": ""})
        self._notify_change()

    def _append_table_row(self, agenda_two: str) -> None:
        idx = self._table.rowCount()
        self._table.insertRow(idx)
        combo = QComboBox()
        combo.addItem("", "")
        for ra_type, ra_display in self._random_agendas:
            combo.addItem(ra_display, ra_type)
        combo.setEditable(True)
        # Try to find by data (type) first, fall back to text match
        found_idx = combo.findData(agenda_two)
        if found_idx >= 0:
            combo.setCurrentIndex(found_idx)
        elif agenda_two:
            combo.setCurrentText(agenda_two)
        combo.currentTextChanged.connect(lambda text, r=idx: self._on_row_text(r, text))
        self._table.setCellWidget(idx, 0, combo)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(32, 26)
        del_btn.clicked.connect(lambda *_a, r=idx: self._delete_row(r))
        self._table.setCellWidget(idx, 1, del_btn)

    def _delete_row(self, row: int) -> None:
        if 0 <= row < len(self._rows):
            self._rows.pop(row)
        self._table.removeRow(row)
        self._notify_change()

    def _on_row_text(self, row: int, _text: str) -> None:
        if 0 <= row < len(self._rows):
            widget = self._table.cellWidget(row, 0)
            if isinstance(widget, QComboBox):
                data = widget.currentData()
                self._rows[row]["AgendaTwo"] = str(data or widget.currentText() or "").strip()
            self._notify_change()

    def _notify_change(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class _AiFavoredItemRow:
    """单行 AiFavoredItems 数据。"""
    def __init__(self, item: str = "", favored: bool = True, value: int = 0,
                 string_val: str = "", min_diff: str = "", max_diff: str = "",
                 tooltip: str = ""):
        self.item = item
        self.favored = favored
        self.value = value
        self.string_val = string_val
        self.min_diff = min_diff
        self.max_diff = max_diff
        self.tooltip = tooltip


class _AiFavoredItemsTable(QWidget):
    """AiFavoredItems 多行表编辑器，含高级字段折叠。"""

    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._loading = False
        self._rows: list[_AiFavoredItemRow] = []
        self._show_advanced = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("AiFavoredItems"))
        hdr.addStretch(1)
        self._add_btn = QPushButton("＋ 添加行")
        self._add_btn.clicked.connect(self._add_row)
        hdr.addWidget(self._add_btn)
        layout.addLayout(hdr)

        # Table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Item", "Favored", "Value", "操作"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 60)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 60)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 40)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(30)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        # Advanced toggle
        self._adv_toggle = QPushButton("展开高级字段 ▼")
        self._adv_toggle.setCheckable(True)
        self._adv_toggle.toggled.connect(self._on_advanced_toggled)
        layout.addWidget(self._adv_toggle)

        # Advanced fields — hidden by default, shown as extra columns in a second table (simpler: just add extra text edits per row)
        # Instead of complex column toggling, we'll use per-row hidden widgets shown/hidden by toggle

        self._rebuild_table()

    def _on_advanced_toggled(self, checked: bool) -> None:
        self._show_advanced = checked
        self._adv_toggle.setText("收起高级字段 ▲" if checked else "展开高级字段 ▼")
        self._rebuild_table()

    def set_loading(self, loading: bool) -> None:
        self._loading = loading

    def set_payload(self, rows: list[dict[str, object]]) -> None:
        self._loading = True
        self._rows.clear()
        for entry in rows:
            if isinstance(entry, dict):
                self._rows.append(_AiFavoredItemRow(
                    item=str(entry.get("Item") or ""),
                    favored=bool(int(entry.get("Favored", 1))),
                    value=int(entry.get("Value", 0)),
                    string_val=str(entry.get("StringVal") or ""),
                    min_diff=str(entry.get("MinDifficulty") or ""),
                    max_diff=str(entry.get("MaxDifficulty") or ""),
                    tooltip=str(entry.get("TooltipString") or ""),
                ))
        self._rebuild_table()
        self._loading = False

    def export_payload(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for row in self._rows:
            if not row.item.strip():
                continue
            entry: dict[str, object] = {
                "Item": row.item,
                "Favored": 1 if row.favored else 0,
                "Value": row.value,
            }
            if row.string_val:
                entry["StringVal"] = row.string_val
            if row.min_diff:
                entry["MinDifficulty"] = row.min_diff
            if row.max_diff:
                entry["MaxDifficulty"] = row.max_diff
            if row.tooltip:
                entry["TooltipString"] = row.tooltip
            result.append(entry)
        return result

    def _add_row(self) -> None:
        self._rows.append(_AiFavoredItemRow())
        self._rebuild_table()
        self._notify_change()

    def _delete_row(self, idx: int) -> None:
        if 0 <= idx < len(self._rows):
            self._rows.pop(idx)
        self._rebuild_table()
        self._notify_change()

    def _rebuild_table(self) -> None:
        self._table.setRowCount(0)
        col_count = 8 if self._show_advanced else 4
        self._table.setColumnCount(col_count)
        if self._show_advanced:
            self._table.setHorizontalHeaderLabels(
                ["Item", "Favored", "Value", "StrVal", "MinDiff", "MaxDiff", "Tooltip", "操作"])
            for c in range(3, 8):
                self._table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
            self._table.setColumnWidth(7, 40)
        else:
            self._table.setHorizontalHeaderLabels(["Item", "Favored", "Value", "操作"])
            self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(3, 40)

        for _row_idx, data in enumerate(self._rows):
            r = self._table.rowCount()
            self._table.insertRow(r)

            item_edit = QLineEdit(data.item)
            item_edit.setPlaceholderText("如 DIPLOACTION_DECLARE_FRIENDSHIP")
            item_edit.textChanged.connect(lambda text, i=r: self._on_cell_changed(i, 0, text))
            self._table.setCellWidget(r, 0, item_edit)

            fav_cb = QCheckBox()
            fav_cb.setChecked(data.favored)
            fav_cb.toggled.connect(lambda checked, i=r: self._on_cell_changed(i, 1, checked))
            fav_w = QWidget()
            fav_l = QHBoxLayout(fav_w)
            fav_l.setContentsMargins(4, 0, 4, 0)
            fav_l.addWidget(fav_cb)
            self._table.setCellWidget(r, 1, fav_w)

            val_spin = QSpinBox()
            val_spin.setRange(-9999, 9999)
            val_spin.setValue(data.value)
            val_spin.valueChanged.connect(lambda v, i=r: self._on_cell_changed(i, 2, v))
            self._table.setCellWidget(r, 2, val_spin)

            if self._show_advanced:
                sv_edit = QLineEdit(data.string_val)
                sv_edit.setPlaceholderText("StringVal")
                sv_edit.textChanged.connect(lambda text, i=r: self._on_cell_changed(i, 3, text))
                self._table.setCellWidget(r, 3, sv_edit)

                md_min = QLineEdit(data.min_diff)
                md_min.setPlaceholderText("MinDifficulty")
                md_min.textChanged.connect(lambda text, i=r: self._on_cell_changed(i, 4, text))
                self._table.setCellWidget(r, 4, md_min)

                md_max = QLineEdit(data.max_diff)
                md_max.setPlaceholderText("MaxDifficulty")
                md_max.textChanged.connect(lambda text, i=r: self._on_cell_changed(i, 5, text))
                self._table.setCellWidget(r, 5, md_max)

                tt_edit = QLineEdit(data.tooltip)
                tt_edit.setPlaceholderText("TooltipString")
                tt_edit.textChanged.connect(lambda text, i=r: self._on_cell_changed(i, 6, text))
                self._table.setCellWidget(r, 6, tt_edit)

                del_col = 7
            else:
                del_col = 3

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 26)
            del_btn.clicked.connect(lambda *_a, i=r: self._delete_row(i))
            self._table.setCellWidget(r, del_col, del_btn)

    def _on_cell_changed(self, row_idx: int, col: int, value: object) -> None:
        if row_idx >= len(self._rows):
            return
        d = self._rows[row_idx]
        if col == 0:
            d.item = str(value or "")
        elif col == 1:
            d.favored = bool(value)
        elif col == 2:
            d.value = int(value)
        elif col == 3 and self._show_advanced:
            d.string_val = str(value or "")
        elif col == 4 and self._show_advanced:
            d.min_diff = str(value or "")
        elif col == 5 and self._show_advanced:
            d.max_diff = str(value or "")
        elif col == 6 and self._show_advanced:
            d.tooltip = str(value or "")
        self._notify_change()

    def _notify_change(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class AiListsEditor(QWidget):
    """左列偏好组列表 + 右侧编辑区。"""

    dataChanged = pyqtSignal()

    def __init__(self, ai_list_types_provider: Callable[[], list[str]], prefix_provider: Callable[[], str]) -> None:
        super().__init__()
        self._agenda_type = ""
        self._leader_type = ""
        self._abbr = ""
        self._loading = False
        self._groups: list[dict[str, object]] = []
        self._system_options: list[str] = []
        self._ai_list_types_provider = ai_list_types_provider
        self._prefix_provider = prefix_provider
        self._editors: list[_AiFavoredItemsTable] = []

        group = QGroupBox("AI 偏好 (AiLists + AiFavoredItems)")
        outer = QVBoxLayout(group)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel — group list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._group_list = QListWidget()
        self._group_list.currentRowChanged.connect(self._on_group_selected)
        left_layout.addWidget(self._group_list, 1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("＋ 新增偏好组")
        add_btn.clicked.connect(self._add_group)
        btn_row.addWidget(add_btn)
        self._remove_btn = QPushButton("✕ 删除")
        self._remove_btn.clicked.connect(self._remove_selected)
        self._remove_btn.setEnabled(False)
        btn_row.addWidget(self._remove_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # Right panel — editor stack
        self._editor_stack = QStackedWidget()
        self._editor_stack.addWidget(QLabel("请添加或选择一个 AI 偏好组"))
        self._system_combos: list[QComboBox] = []
        self._list_type_edits: list[QLineEdit] = []

        splitter.addWidget(self._editor_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 520])

        outer.addWidget(splitter)
        self.setLayout(outer)

    def _auto_list_type(self, system: str) -> str:
        if not system:
            return ""
        prefix = self._prefix_provider() if callable(self._prefix_provider) else ""
        abbr = self._abbr
        parts = [prefix, abbr, system] if prefix else [abbr, system]
        return "".join(p for p in parts if p)

    def set_context(self, agenda_type: str, leader_type: str, abbr: str) -> None:
        self._agenda_type = _safe_text(agenda_type)
        self._leader_type = _safe_text(leader_type)
        self._abbr = _safe_text(abbr)
        self._system_options = self._ai_list_types_provider() if callable(self._ai_list_types_provider) else []

    def set_payload(self, groups: list[dict[str, object]]) -> None:
        self._loading = True
        self._clear_all()
        if isinstance(groups, list):
            for grp in groups:
                if isinstance(grp, dict):
                    self._add_group_widget(grp)
        if self._editors:
            self._group_list.setCurrentRow(0)
        self._loading = False

    def export_payload(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for i in range(self._group_list.count()):
            system_combo = self._system_combos[i]
            list_type_edit = self._list_type_edits[i]
            items_table = self._editors[i]
            system = system_combo.currentText().strip()
            list_type = list_type_edit.text().strip() or list_type_edit.placeholderText() or self._auto_list_type(system)
            fav_items = items_table.export_payload()
            if system or list_type or fav_items:
                result.append({
                    "LeaderType": self._leader_type,
                    "AgendaType": self._agenda_type,
                    "ListType": list_type,
                    "System": system,
                    "AiFavoredItems": fav_items,
                })
        return result

    def _on_group_selected(self, row: int) -> None:
        self._remove_btn.setEnabled(row >= 0)
        if 0 <= row < self._editor_stack.count() - 1:
            self._editor_stack.setCurrentIndex(row + 1)  # +1 for placeholder

    def _add_group(self) -> None:
        self._add_group_widget({})
        self._group_list.setCurrentRow(self._group_list.count() - 1)

    def _add_group_widget(self, grp_data: dict[str, object]) -> None:
        system = _safe_text(grp_data.get("System", ""))
        list_type = _safe_text(grp_data.get("ListType", ""))
        fav_items_payload = grp_data.get("AiFavoredItems")
        fav_list = list(fav_items_payload) if isinstance(fav_items_payload, list) else []

        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        # Row: System + ListType
        top = QHBoxLayout()
        top.addWidget(QLabel("System"))
        sys_combo = QComboBox()
        sys_combo.setEditable(True)
        sys_combo.addItem("", "")
        for opt in self._system_options:
            sys_combo.addItem(opt, opt)
        if system:
            sys_combo.setCurrentText(system)
        sys_combo.currentTextChanged.connect(self._emit_data_changed)
        top.addWidget(sys_combo, 1)
        self._system_combos.append(sys_combo)

        top.addWidget(QLabel("ListType"))
        lt_edit = QLineEdit()
        lt_edit.setPlaceholderText(self._auto_list_type(system) or "自动生成")
        if list_type:
            lt_edit.setText(list_type)
        lt_edit.textChanged.connect(lambda _: self._emit_data_changed())
        top.addWidget(lt_edit, 1)
        self._list_type_edits.append(lt_edit)

        page_layout.addLayout(top)

        # AiFavoredItems table
        items_table = _AiFavoredItemsTable()
        items_table.set_payload(fav_list)
        items_table.dataChanged.connect(self._emit_data_changed)
        self._editors.append(items_table)
        page_layout.addWidget(items_table, 1)

        # Stack index
        stack_idx = self._editor_stack.addWidget(page)
        item = QListWidgetItem(list_type or system or f"偏好组 {self._group_list.count() + 1}")
        item.setData(Qt.ItemDataRole.UserRole, stack_idx)
        self._group_list.addItem(item)

    def _remove_selected(self) -> None:
        row = self._group_list.currentRow()
        if row < 0 or row >= len(self._editors):
            return
        self._group_list.takeItem(row)
        page = self._editor_stack.widget(row + 1)  # +1 for placeholder
        self._editor_stack.removeWidget(page)
        page.deleteLater()
        self._system_combos.pop(row)
        self._list_type_edits.pop(row)
        self._editors.pop(row)
        # Re-index remaining items
        for r in range(self._group_list.count()):
            item = self._group_list.item(r)
            if item and r + 1 < self._editor_stack.count():
                item.setData(Qt.ItemDataRole.UserRole, r + 1)
        self._emit_data_changed()

    def _clear_all(self) -> None:
        self._group_list.clear()
        for i in range(self._editor_stack.count() - 1, 0, -1):
            w = self._editor_stack.widget(i)
            self._editor_stack.removeWidget(w)
            w.deleteLater()
        self._system_combos.clear()
        self._list_type_edits.clear()
        self._editors.clear()

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        # Refresh list names
        for r in range(self._group_list.count()):
            item = self._group_list.item(r)
            if item is None:
                continue
            lt = self._list_type_edits[r].text().strip()
            sys = self._system_combos[r].currentText().strip()
            name = lt or sys or f"偏好组 {r + 1}"
            item.setText(name)
        self.dataChanged.emit()


class AgendaCompositeEditor(QWidget):
    """议程复合编辑器 —— 议程表 + Modifier + AI偏好。"""

    dataChanged = pyqtSignal()

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
        leader_entries_provider: Callable[[], list[dict[str, str]]],
        random_agendas_provider: Callable[[], list[tuple[str, str]]],
        ai_list_types_provider: Callable[[], list[str]],
        custom_reqset_provider: Callable[[], list[dict[str, object]]],
        text_search_provider: Callable[[str], str],
    ) -> None:
        super().__init__()
        self._loading = False
        self._leader_entries_provider = leader_entries_provider

        self._main_editor = MainTableEditor(
            schema=build_agendas_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )
        self._historical_editor = HistoricalAgendasEditor(
            leader_entries_provider,
            text_search_provider,
        )
        self._exclusive_editor = ExclusiveAgendasEditor(random_agendas_provider)
        self._modifier_editor = AgendaModifierListEditor(
            text_search_provider=text_search_provider,
            custom_reqset_provider=custom_reqset_provider,
        )
        self._ai_lists_editor = AiListsEditor(
            ai_list_types_provider=ai_list_types_provider,
            prefix_provider=lambda: str(shared_params_provider().get("prefix", "")),
        )

        self._trait_display = QLineEdit()
        self._trait_display.setReadOnly(True)

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        self._historical_editor.dataChanged.connect(self._emit_data_changed)
        self._exclusive_editor.dataChanged.connect(self._emit_data_changed)
        self._modifier_editor.dataChanged.connect(self._emit_data_changed)
        self._ai_lists_editor.dataChanged.connect(self._emit_data_changed)

        # 议程相关表区域
        agenda_section = QGroupBox("议程相关表")
        agenda_layout = QVBoxLayout(agenda_section)
        agenda_layout.addWidget(self._main_editor)

        trait_row = QHBoxLayout()
        trait_row.addWidget(QLabel("TraitType（自动生成）"))
        trait_row.addWidget(self._trait_display, 1)
        agenda_layout.addLayout(trait_row)
        agenda_layout.addWidget(self._historical_editor)
        agenda_layout.addWidget(self._exclusive_editor)

        # AI 偏好区域
        ai_section = QGroupBox("AI 偏好相关表")
        ai_layout = QVBoxLayout(ai_section)
        ai_layout.addWidget(self._ai_lists_editor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(agenda_section)
        layout.addWidget(self._modifier_editor)
        layout.addWidget(ai_section)

    def _sync_agenda_context(self) -> None:
        agenda_type = self._main_editor.current_type()
        leader_type = self._historical_editor.current_leader_type()
        abbr = _safe_text(self._main_editor._abbr_edit.text())
        prefix = _safe_text(self._main_editor._shared_params_provider().get("prefix", ""))
        self._trait_display.setText(f"TRAIT_{agenda_type}" if agenda_type else "")
        self._exclusive_editor.set_agenda_type(agenda_type)
        leader_name = leader_type[len("LEADER_"):] if leader_type.startswith("LEADER_") else leader_type
        self._modifier_editor.set_context(agenda_type, prefix, abbr, leader_name)
        self._ai_lists_editor.set_context(agenda_type, leader_type, abbr)

    def _handle_main_changed(self) -> None:
        self._sync_agenda_context()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_agenda_context()

        # HistoricalAgendas
        historical = entry.get("historical_agendas")
        historical_dict = dict(historical) if isinstance(historical, dict) else {}
        self._historical_editor.set_entry(historical_dict)

        # Sub tables
        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

        # ExclusiveAgendas
        exclusive_payload = subtables.get("ExclusiveAgendas") if isinstance(subtables.get("ExclusiveAgendas"), list) else []
        self._exclusive_editor.set_payload(exclusive_payload if isinstance(exclusive_payload, list) else [])

        # AgendaModifiers
        modifiers_payload = subtables.get("AgendaModifiers") if isinstance(subtables.get("AgendaModifiers"), list) else []
        self._modifier_editor.set_payload(modifiers_payload if isinstance(modifiers_payload, list) else [])

        # AiLists
        ai_lists_payload = subtables.get("AiLists") if isinstance(subtables.get("AiLists"), list) else []
        self._ai_lists_editor.set_payload(ai_lists_payload if isinstance(ai_lists_payload, list) else [])

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()

        historical_payload = self._historical_editor.export_payload()
        leader_type = str(historical_payload.get("LeaderType") or "")
        if leader_type:
            historical_payload["AgendaType"] = self._main_editor.current_type()
            payload["historical_agendas"] = historical_payload
        else:
            payload.pop("historical_agendas", None)

        subtables = payload.get("subtables") if isinstance(payload.get("subtables"), dict) else {}
        if not isinstance(subtables, dict):
            subtables = {}

        exclusive = self._exclusive_editor.export_payload()
        if exclusive:
            subtables["ExclusiveAgendas"] = exclusive
        else:
            subtables.pop("ExclusiveAgendas", None)

        modifiers = self._modifier_editor.export_payload()
        if modifiers:
            subtables["AgendaModifiers"] = modifiers
        else:
            subtables.pop("AgendaModifiers", None)

        ai_lists = self._ai_lists_editor.export_payload()
        if ai_lists:
            subtables["AiLists"] = ai_lists
        else:
            subtables.pop("AiLists", None)

        if subtables:
            payload["subtables"] = subtables
        else:
            payload.pop("subtables", None)
        return payload

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class PolicyXP1SubTableEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._policy_type = ""
        self._policy_type_display = QLineEdit()
        self._policy_type_display.setReadOnly(True)

        self._minimum_era_widget = build_template_widget("era")
        if hasattr(self._minimum_era_widget, "set_label_text"):
            self._minimum_era_widget.set_label_text("")
        self._maximum_era_widget = build_template_widget("era")
        if hasattr(self._maximum_era_widget, "set_label_text"):
            self._maximum_era_widget.set_label_text("")

        self._requires_dark_age = QCheckBox("RequiresDarkAge")
        self._requires_golden_age = QCheckBox("RequiresGoldenAge")
        _normalize_checkbox_caption(self._requires_dark_age)
        _normalize_checkbox_caption(self._requires_golden_age)
        _attach_hover_param_tooltip(self._requires_dark_age, "RequiresDarkAge")
        _attach_hover_param_tooltip(self._requires_golden_age, "RequiresGoldenAge")

        group = QGroupBox("Policies_XP1")
        layout = QVBoxLayout(group)
        tip = QLabel(_policy_table_hint("Policies_XP1"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(180)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policies_XP1", "PolicyType"), fallback_key="PolicyType"), self._policy_type_display), 0, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policies_XP1", "MinimumGameEra"), fallback_key="MinimumGameEra"), self._minimum_era_widget), 0, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policies_XP1", "MaximumGameEra"), fallback_key="MaximumGameEra"), self._maximum_era_widget), 1, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policies_XP1", "RequiresDarkAge"), fallback_key="RequiresDarkAge"), self._requires_dark_age), 1, 1)
        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policies_XP1", "RequiresGoldenAge"), fallback_key="RequiresGoldenAge"), self._requires_golden_age), 2, 0)
        layout.addLayout(grid)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        self._requires_dark_age.stateChanged.connect(lambda _v: self.dataChanged.emit())
        self._requires_golden_age.stateChanged.connect(lambda _v: self.dataChanged.emit())
        if hasattr(self._minimum_era_widget, "dataChanged"):
            self._minimum_era_widget.dataChanged.connect(self.dataChanged.emit)
        if hasattr(self._maximum_era_widget, "dataChanged"):
            self._maximum_era_widget.dataChanged.connect(self.dataChanged.emit)

    def set_policy_type(self, policy_type: str) -> None:
        self._policy_type = _safe_text(policy_type)
        self._policy_type_display.setText(self._policy_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        if hasattr(self._minimum_era_widget, "set_current_value"):
            self._minimum_era_widget.set_current_value(_safe_text(payload.get("MinimumGameEra")) or None)
        if hasattr(self._maximum_era_widget, "set_current_value"):
            self._maximum_era_widget.set_current_value(_safe_text(payload.get("MaximumGameEra")) or None)
        self._requires_dark_age.setChecked(bool(int(payload.get("RequiresDarkAge", 0) or 0)))
        self._requires_golden_age.setChecked(bool(int(payload.get("RequiresGoldenAge", 0) or 0)))

    def export_payload(self) -> dict[str, object]:
        minimum_era = ""
        if isinstance(self._minimum_era_widget, BaseTemplateWidget):
            minimum_era = _safe_text(_first_non_empty(self._minimum_era_widget.export_data()))
        maximum_era = ""
        if isinstance(self._maximum_era_widget, BaseTemplateWidget):
            maximum_era = _safe_text(_first_non_empty(self._maximum_era_widget.export_data()))
        return {
            "PolicyType": self._policy_type,
            "MinimumGameEra": minimum_era,
            "MaximumGameEra": maximum_era,
            "RequiresDarkAge": 1 if self._requires_dark_age.isChecked() else 0,
            "RequiresGoldenAge": 1 if self._requires_golden_age.isChecked() else 0,
        }


class PolicyGovernmentExclusiveEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._policy_type = ""
        self._policy_type_display = QLineEdit()
        self._policy_type_display.setReadOnly(True)

        self._government_type_widget = build_template_widget("government_type")
        if hasattr(self._government_type_widget, "set_label_text"):
            self._government_type_widget.set_label_text("")

        group = QGroupBox("Policy_GovernmentExclusives_XP2")
        layout = QVBoxLayout(group)
        tip = QLabel(_policy_table_hint("Policy_GovernmentExclusives_XP2"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def _cell(label: str, widget: QWidget) -> QWidget:
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            title = QLabel(label)
            title.setMinimumWidth(120)
            row.addWidget(title)
            row.addWidget(widget, 1)
            return holder

        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policy_GovernmentExclusives_XP2", "PolicyType"), fallback_key="PolicyType"), self._policy_type_display), 0, 0)
        grid.addWidget(_cell(_param_display_text(zh_text=_policy_param_zh("Policy_GovernmentExclusives_XP2", "GovernmentType"), fallback_key="GovernmentType"), self._government_type_widget), 0, 1)
        layout.addLayout(grid)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        if hasattr(self._government_type_widget, "dataChanged"):
            self._government_type_widget.dataChanged.connect(self.dataChanged.emit)

    def set_policy_type(self, policy_type: str) -> None:
        self._policy_type = _safe_text(policy_type)
        self._policy_type_display.setText(self._policy_type)

    def set_payload(self, payload: dict[str, object]) -> None:
        if hasattr(self._government_type_widget, "set_current_value"):
            self._government_type_widget.set_current_value(_safe_text(payload.get("GovernmentType")) or None)

    def export_payload(self) -> dict[str, object]:
        government_type = ""
        if isinstance(self._government_type_widget, BaseTemplateWidget):
            government_type = _safe_text(_first_non_empty(self._government_type_widget.export_data()))
        return {
            "PolicyType": self._policy_type,
            "GovernmentType": government_type,
        }


class PolicyCompositeEditor(QWidget):
    dataChanged = pyqtSignal()
    duplicateRequested = pyqtSignal(dict)

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        type_builder: Callable[[dict[str, object], str, str, object | None], str],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._loading = False

        self._main_editor = MainTableEditor(
            schema=build_policies_main_schema(),
            shared_params_provider=shared_params_provider,
            type_builder=type_builder,
            image_widget_factory=image_widget_factory,
        )
        self._xp1_editor = PolicyXP1SubTableEditor()
        self._exclusive_editor = PolicyGovernmentExclusiveEditor()

        self._duplicate_button = QPushButton("复制该政策卡")
        self._duplicate_button.clicked.connect(self._request_duplicate)

        self._main_editor.dataChanged.connect(self._handle_main_changed)
        self._xp1_editor.dataChanged.connect(self._emit_data_changed)
        self._exclusive_editor.dataChanged.connect(self._emit_data_changed)

        def _top_cell(widget: QWidget) -> QWidget:
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(0)
            holder_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)
            holder_layout.addStretch(1)
            return holder

        actions = QHBoxLayout()
        actions.addWidget(self._duplicate_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._main_editor)
        layout.addLayout(actions)
        layout.addWidget(self._xp1_editor)
        layout.addWidget(self._exclusive_editor)

    def _sync_policy_type(self) -> None:
        policy_type = self._main_editor.current_type()
        self._xp1_editor.set_policy_type(policy_type)
        self._exclusive_editor.set_policy_type(policy_type)

    def _handle_main_changed(self) -> None:
        self._sync_policy_type()
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._loading = True
        self._main_editor.set_entry(entry, fallback_name)
        self._sync_policy_type()
        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

        xp1_payload = subtables.get("Policies_XP1") if isinstance(subtables.get("Policies_XP1"), dict) else entry.get("policies_xp1") if isinstance(entry.get("policies_xp1"), dict) else {}
        self._xp1_editor.set_payload(xp1_payload if isinstance(xp1_payload, dict) else {})

        exclusive_payload = subtables.get("Policy_GovernmentExclusives_XP2") if isinstance(subtables.get("Policy_GovernmentExclusives_XP2"), dict) else entry.get("policy_government_exclusive") if isinstance(entry.get("policy_government_exclusive"), dict) else {}
        self._exclusive_editor.set_payload(exclusive_payload if isinstance(exclusive_payload, dict) else {})

        self._loading = False

    def export_entry(self) -> dict[str, object]:
        payload = self._main_editor.export_entry()
        xp1 = self._xp1_editor.export_payload()
        exclusive = self._exclusive_editor.export_payload()
        payload.update(
            {
                "policies_xp1": xp1,
                "policy_government_exclusive": exclusive,
                "subtables": {
                    "Policies_XP1": xp1,
                    "Policy_GovernmentExclusives_XP2": exclusive,
                },
            }
        )
        return payload

    def _request_duplicate(self) -> None:
        payload = self.export_entry()
        self.duplicateRequested.emit(payload)

    def _emit_data_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()
