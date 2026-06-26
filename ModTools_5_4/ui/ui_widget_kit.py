"""ModTools 5.4 UI 模板控件库。

用于 DEBUG 页的控件实例化、参数编辑与数据汇总。
所有选择类控件统一保存英文游戏标识，中文仅用于显示。

新增模板时请同步更新 `TEMPLATE_SPECS` 并在 `build_template_widget` 中注册。
"""
from __future__ import annotations

import sqlite3
import functools
import itertools
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

from contextlib import contextmanager

from PyQt6.QtCore import Qt, QEvent, QUrl, pyqtSignal, QSignalBlocker, QObject, QTimer
from PyQt6.QtGui import QColor, QBrush, QGuiApplication, QKeyEvent, QTextCharFormat, QTextCursor, QTextDocument, QTextImageFormat
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSpinBox,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QSpinBox,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QAbstractItemView,
    QHeaderView,
    QWidget,
    QGraphicsDropShadowEffect,
)

from .font_icon_popup import FontIconPopup
from .font_icons import DdsRgba32Atlas, FontIconRegistry, resolve_default_fonticons_dds_path


def _apply_drop_shadow(widget: QWidget, color: QColor | None = None, blur_radius: int = 8, offset_x: int = 0, offset_y: int = 2) -> None:
    """Apply a simple drop shadow effect to a widget.

    This is used to emulate the QSS `box-shadow` visual which Qt style sheets
    do not support. It's intentionally minimal and safe to call.
    """
    try:
        if color is None:
            color = QColor(80, 120, 180, 20)
        effect = QGraphicsDropShadowEffect(parent=widget)
        effect.setBlurRadius(blur_radius)
        effect.setOffset(offset_x, offset_y)
        effect.setColor(color)
        widget.setGraphicsEffect(effect)
    except Exception:
        LOGGER.exception("Failed to apply drop shadow")

from ..db.interface import get_chinese_text_for_tag
from ..db.paths import DEFAULT_GAME_DB


LOGGER = logging.getLogger(__name__)

# -------------------------------
# Workspace pinning support
# -------------------------------

_WORKSPACE_SECTIONS_PROVIDER: Callable[[], dict[str, object]] | None = None


def set_workspace_sections_provider(provider: Callable[[], dict[str, object]] | None) -> None:
    """Register a callable returning the active .CIV project's workspace sections."""

    global _WORKSPACE_SECTIONS_PROVIDER
    _WORKSPACE_SECTIONS_PROVIDER = provider


def _get_workspace_sections() -> dict[str, object]:
    provider = _WORKSPACE_SECTIONS_PROVIDER
    if provider is None:
        return {}
    try:
        sections = provider()
    except Exception:
        return {}
    return sections if isinstance(sections, dict) else {}


def _workspace_entries(section_name: str) -> list[dict[str, object]]:
    payload = _get_workspace_sections().get(section_name)
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _workspace_entry_type(entry: dict[str, object]) -> str:
    return str(entry.get("type") or "").strip()


def _workspace_entry_display_name(entry: dict[str, object]) -> str:
    for key in ("name", "Name"):
        text = str(entry.get(key) or "").strip()
        if text:
            return text
    table_data = entry.get("table_data")
    if isinstance(table_data, dict):
        text = str(table_data.get("Name") or "").strip()
        if text:
            return text
    return _workspace_entry_type(entry)


WORKSPACE_PIN_BG = "#fef9c3"  # pinned workspace entities
WORKSPACE_PIN_GROUP_LABEL = "工作区（置顶）"
WORKSPACE_GREATPERSON_NEW_BG = "#fde68a"
WORKSPACE_GREATPERSON_IMPORTED_BG = "#bfdbfe"

CHECKBOX_STYLE = (
    "QCheckBox {"
    "    spacing: 8px;"
    "    color: #334155;"
    "}"
    "QCheckBox::indicator {"
    "    width: 18px;"
    "    height: 18px;"
    "    border: 1px solid #9fb6dc;"
    "    border-radius: 4px;"
    "    background: #ffffff;"
    "}"
    "QCheckBox::indicator:hover {"
    "    border-color: #6f96d3;"
    "}"
    "QCheckBox::indicator:checked {"
    "    image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 10'><path d='M1.2 5.2 4.8 8.8 10.8 1.2' fill='none' stroke='%23000000' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>\");"
    "    border-color: #5f84bf;"
    "    background: #eaf2ff;"
    "}"
    "QCheckBox::indicator:checked:hover {"
    "    border-color: #4f72aa;"
    "}"
)

EXCLUDED_FEATURE_TYPES = {
    "FEATURE_BURNING_FOREST",
    "FEATURE_BURNT_FOREST",
    "FEATURE_BURNING_JUNGLE",
    "FEATURE_BURNT_JUNGLE",
}

RESOURCE_CLASS_LABELS = {
    "RESOURCECLASS_BONUS": "加成资源",
    "RESOURCECLASS_LUXURY": "奢侈资源",
    "RESOURCECLASS_STRATEGIC": "战略资源",
    "RESOURCECLASS_ARTIFACT": "文物",
}

RESOURCE_CLASS_ORDER = {
    "RESOURCECLASS_BONUS": 0,
    "RESOURCECLASS_LUXURY": 1,
    "RESOURCECLASS_STRATEGIC": 2,
}

ERA_GROUP_COLORS = (
    "#fef3c7",
    "#e0f2fe",
    "#ede9fe",
    "#dcfce7",
    "#fee2e2",
    "#fce7f3",
    "#e2e8f0",
    "#f5f5f5",
    "#fff7ed",
    "#f1f5f9",
)

PLUNDER_OPTIONS = (
    ("不可掠夺", "NO_PLUNDER"),
    ("掠夺文化", "PLUNDER_CULTURE"),
    ("掠夺信仰", "PLUNDER_FAITH"),
    ("掠夺金币", "PLUNDER_GOLD"),
    ("掠夺治疗", "PLUNDER_HEAL"),
    ("掠夺科技", "PLUNDER_SCIENCE"),
)

COST_PROGRESSION_OPTIONS = (
    ("随游戏进度", "COST_PROGRESSION_GAME_PROGRESS"),
    ("六折递增机制", "COST_PROGRESSION_NUM_UNDER_AVG_PLUS_TECH"),
    ("无递增", "NO_COST_PROGRESSION"),
    ("随数量递增", "COST_PROGRESSION_PREVIOUS_COPIES"),
)

DOMAIN_OPTIONS = (
    ("空军", "DOMAIN_AIR"),
    ("陆地", "DOMAIN_LAND"),
    ("海洋", "DOMAIN_SEA"),
)

FORMATION_CLASS_OPTIONS = (
    ("空中单位", "FORMATION_CLASS_AIR"),
    ("平民单位", "FORMATION_CLASS_CIVILIAN"),
    ("陆地军事单位", "FORMATION_CLASS_LAND_COMBAT"),
    ("海军单位", "FORMATION_CLASS_NAVAL"),
    ("支援单位", "FORMATION_CLASS_SUPPORT"),
)

YIELD_OPTIONS = (
    ("金币", "YIELD_GOLD"),
    ("生产力", "YIELD_PRODUCTION"),
    ("科技", "YIELD_SCIENCE"),
    ("文化", "YIELD_CULTURE"),
    ("信仰", "YIELD_FAITH"),
    ("食物", "YIELD_FOOD"),
)

ADVISOR_TYPE_OPTIONS = (
    ("ADVISOR_GENERIC", "通用"),
    ("ADVISOR_CONQUEST", "征服"),
    ("ADVISOR_CULTURE", "文化"),
    ("ADVISOR_RELIGIOUS", "宗教"),
    ("ADVISOR_TECHNOLOGY", "科技"),
)

RESOURCE_CLASS_OPTIONS = (
    ("RESOURCECLASS_BONUS", "加成资源"),
    ("RESOURCECLASS_LUXURY", "奢侈资源"),
    ("RESOURCECLASS_STRATEGIC", "战略资源"),
    ("RESOURCECLASS_ARTIFACT", "文物"),
)

YIELD_VALUE_TO_NAME = {value: label for label, value in YIELD_OPTIONS}


@contextmanager
def _block_signals(widget: QObject) -> Iterator[QObject]:
    blocker = QSignalBlocker(widget)
    try:
        yield widget
    finally:
        del blocker


YIELD_COLOR_MAP = {
    "YIELD_GOLD": "#fbbf24",
    "YIELD_PRODUCTION": "#9ca3af",
    "YIELD_SCIENCE": "#60a5fa",
    "YIELD_CULTURE": "#f472b6",
    "YIELD_FAITH": "#c4b5fd",
    "YIELD_FOOD": "#facc15",
}

YIELD_ICON_LABEL_MAP = {
    "YIELD_GOLD": ("[ICON_GOLD]", "金币"),
    "YIELD_PRODUCTION": ("[ICON_PRODUCTION]", "生产力"),
    "YIELD_SCIENCE": ("[ICON_SCIENCE]", "科技值"),
    "YIELD_CULTURE": ("[ICON_CULTURE]", "文化值"),
    "YIELD_FAITH": ("[ICON_FAITH]", "信仰值"),
    "YIELD_FOOD": ("[ICON_FOOD]", "食物"),
}

ADJACENCY_TYPE_INFO = {
    "OtherDistrictAdjacent": {"kind": "boolean", "label": "相邻其他区域"},
    "AdjacentSeaResource": {"kind": "boolean", "label": "相邻海洋资源"},
    "AdjacentRiver": {"kind": "boolean", "label": "相邻河流"},
    "AdjacentWonder": {"kind": "boolean", "label": "相邻人造奇观"},
    "AdjacentNaturalWonder": {"kind": "boolean", "label": "相邻自然奇观"},
    "AdjacentResource": {"kind": "boolean", "label": "相邻资源"},
    "Self": {"kind": "boolean", "label": "自带"},
    "AdjacentTerrain": {"kind": "terrain", "label": "相邻地形"},
    "AdjacentFeature": {"kind": "feature", "label": "相邻地貌"},
    "AdjacentImprovement": {"kind": "improvement", "label": "相邻改良设施"},
    "AdjacentDistrict": {"kind": "district", "label": "相邻区域"},
    "AdjacentResourceClass": {"kind": "resource_class", "label": "相邻资源类型"},
}

ADJACENCY_BOOLEAN_KEYS = tuple(
    key for key, meta in ADJACENCY_TYPE_INFO.items() if meta["kind"] == "boolean"
)

ADJACENCY_VALUE_KEYS = tuple(
    key for key, meta in ADJACENCY_TYPE_INFO.items() if meta["kind"] != "boolean"
)


ADJACENCY_VALUE_MAPPINGS = {
    "AdjacentTerrain": {"template": "terrain", "label": "选择地形", "value_key": "terrain_type"},
    "AdjacentFeature": {"template": "feature_all", "label": "选择地貌", "value_key": "feature_type"},
    "AdjacentImprovement": {"template": "improvement_search", "label": "选择改良设施", "value_key": "improvement_type"},
    "AdjacentDistrict": {"template": "district_search", "label": "选择区域", "value_key": "district_type"},
    "AdjacentResourceClass": {"template": "resource_class", "label": "选择资源类型", "value_key": "resource_class"},
}


@dataclass(slots=True)
class AdjacencySourceState:
    key: str
    kind: str
    value: Optional[str]


@dataclass(slots=True)
class AdjacencyYieldRecord:
    identifier: str
    description: Optional[str]
    yield_type: Optional[str]
    yield_change: int
    tiles_required: int
    prereq_tech: Optional[str]
    prereq_civic: Optional[str]
    obsolete_tech: Optional[str]
    obsolete_civic: Optional[str]
    requirement_set_id: Optional[str]
    requirement_fail_set_id: Optional[str]
    sources: List[AdjacencySourceState]
    raw: Dict[str, object]


def _normalize_text(value: object | None) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: object | None, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _fetch_table_columns(cursor: sqlite3.Cursor, table: str) -> List[str]:
    try:
        rows = cursor.execute(f"PRAGMA table_info('{table}')").fetchall()
    except sqlite3.Error:
        return []
    return [str(row[1]) for row in rows if len(row) > 1]


def _fetch_adjacency_rows(include_placeholder: bool = False) -> List[AdjacencyYieldRecord]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return []

    try:
        cursor = conn.cursor()
        available_columns = set(_fetch_table_columns(cursor, "Adjacency_YieldChanges"))
        base_columns = [
            "ID",
            "Description",
            "YieldType",
            "YieldChange",
            "TilesRequired",
            "PrereqTech",
            "PrereqCivic",
            "ObsoleteTech",
            "ObsoleteCivic",
            "RequirementSetId",
            "RequirementSetToFail",
        ]
        select_columns = [col for col in base_columns if col in available_columns]
        for key in ADJACENCY_TYPE_INFO:
            if key in available_columns:
                select_columns.append(key)

        if not select_columns:
            return []

        rows = cursor.execute(
            f"SELECT {', '.join(select_columns)} FROM Adjacency_YieldChanges"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    records: List[AdjacencyYieldRecord] = []
    for row in rows:
        data = {col: row[col] for col in select_columns}
        description = _normalize_text(data.get("Description"))
        if description == "Placeholder" and not include_placeholder:
            continue

        sources: List[AdjacencySourceState] = []
        for key, meta in ADJACENCY_TYPE_INFO.items():
            if key not in data:
                continue
            value = data.get(key)
            if meta["kind"] == "boolean":
                if _safe_int(value, 0):
                    sources.append(AdjacencySourceState(key=key, kind="boolean", value=None))
            else:
                text_value = _normalize_text(value)
                if text_value:
                    sources.append(AdjacencySourceState(key=key, kind=meta["kind"], value=text_value))

        record = AdjacencyYieldRecord(
            identifier=_normalize_text(data.get("ID")) or "",
            description=description,
            yield_type=_normalize_text(data.get("YieldType")),
            yield_change=_safe_int(data.get("YieldChange"), 0),
            tiles_required=_safe_int(data.get("TilesRequired"), 0),
            prereq_tech=_normalize_text(data.get("PrereqTech")),
            prereq_civic=_normalize_text(data.get("PrereqCivic")),
            obsolete_tech=_normalize_text(data.get("ObsoleteTech")),
            obsolete_civic=_normalize_text(data.get("ObsoleteCivic")),
            requirement_set_id=_normalize_text(data.get("RequirementSetId")),
            requirement_fail_set_id=_normalize_text(data.get("RequirementSetToFail")),
            sources=sources,
            raw=data,
        )
        records.append(record)

    return records


@dataclass(slots=True)
class AdjacencyDisplayItem:
    identifier: str
    yield_type: Optional[str]
    yield_change: int
    description: str
    source_summary: str
    tiles_required: int
    entry_type: str
    payload: Dict[str, object]


@dataclass(slots=True)
class AdjacencyAutoContext:
    prefix: str = ""
    district_infix: str = ""
    district_code: str = ""


ADJACENCY_TABLE_HEADERS = (
    "ID",
    "描述",
    "相邻类型",
)


class AdjacencyTableWidget(QTableWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        auto_height: bool = False,
        min_visible_rows: int = 5,
    ) -> None:
        super().__init__(0, len(ADJACENCY_TABLE_HEADERS), parent)
        self.setObjectName("adjacencyTable")
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setWordWrap(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(32)
        self.setHorizontalHeaderLabels(ADJACENCY_TABLE_HEADERS)
        self._enable_row_coloring = False
        self._auto_height = auto_height
        self._min_visible_rows = max(0, int(min_visible_rows))

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_table_height)

        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        if self._auto_height:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
            self._refresh_table_height()
        else:
            self._set_min_visible_rows(self._min_visible_rows)

    def _create_item(self, text: str, entry: Optional[AdjacencyDisplayItem] = None) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        if entry is not None:
            item.setData(Qt.ItemDataRole.UserRole, entry)
        return item

    def clear_entries(self) -> None:
        self.setRowCount(0)
        self._schedule_height_refresh()

    def append_entry(self, entry: AdjacencyDisplayItem) -> None:
        row_index = self.rowCount()
        self.insertRow(row_index)
        self._populate_row(row_index, entry)
        self._schedule_height_refresh()

    def extend_entries(self, entries: Sequence[AdjacencyDisplayItem]) -> None:
        if not entries:
            return
        self.setUpdatesEnabled(False)
        try:
            for entry in entries:
                row_index = self.rowCount()
                self.insertRow(row_index)
                self._populate_row(row_index, entry)
        finally:
            self.setUpdatesEnabled(True)
        self._schedule_height_refresh()

    def update_entry(self, row: int, entry: AdjacencyDisplayItem) -> None:
        if not (0 <= row < self.rowCount()):
            return
        self._populate_row(row, entry)
        self._schedule_height_refresh()

    def remove_selected_entries(self) -> List[AdjacencyDisplayItem]:
        removed: List[AdjacencyDisplayItem] = []
        selected_rows = sorted({index.row() for index in self.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            item = self.item(row, 0)
            entry = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if isinstance(entry, AdjacencyDisplayItem):
                removed.append(entry)
            self.removeRow(row)
        if selected_rows:
            self._schedule_height_refresh()
        return removed

    def iter_entries(self) -> List[AdjacencyDisplayItem]:
        results: List[AdjacencyDisplayItem] = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            entry = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if isinstance(entry, AdjacencyDisplayItem):
                results.append(entry)
        return results

    def _populate_row(self, row_index: int, entry: AdjacencyDisplayItem) -> None:
        id_item = self._create_item(entry.identifier, entry)
        desc_item = self._create_item(entry.description or "-")
        source_item = self._create_item(entry.source_summary or "-")

        self.setItem(row_index, 0, id_item)
        self.setItem(row_index, 1, desc_item)
        self.setItem(row_index, 2, source_item)
        self._apply_row_style(row_index, entry)

    def _set_min_visible_rows(self, rows: int) -> None:
        header = self.horizontalHeader()
        header_height = header.height() or header.defaultSectionSize()
        row_height = self.verticalHeader().defaultSectionSize()
        frame = self.frameWidth() * 2
        padding = 8
        total_height = header_height + row_height * rows + frame + padding
        self.setMinimumHeight(total_height)

    def _schedule_height_refresh(self) -> None:
        if not self._auto_height:
            return
        self._refresh_timer.start(0)

    def _refresh_table_height(self) -> None:
        if not self._auto_height:
            return

        # 让行高跟随 wordWrap/列宽变化
        self.resizeRowsToContents()

        header = self.horizontalHeader()
        header_height = header.height() or header.defaultSectionSize()
        frame = self.frameWidth() * 2
        padding = 8

        rows_height = sum(self.rowHeight(row) for row in range(self.rowCount()))
        if self.rowCount() < self._min_visible_rows:
            rows_height += (self._min_visible_rows - self.rowCount()) * self.verticalHeader().defaultSectionSize()

        hbar = self.horizontalScrollBar()
        hbar_height = hbar.sizeHint().height() if hbar.isVisible() else 0
        total_height = header_height + rows_height + frame + padding + hbar_height
        self.setFixedHeight(max(0, int(total_height)))

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._schedule_height_refresh()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._schedule_height_refresh()

    def set_row_coloring_enabled(self, enabled: bool) -> None:
        if self._enable_row_coloring == enabled:
            return
        self._enable_row_coloring = enabled
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            payload = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if isinstance(payload, AdjacencyDisplayItem):
                self._apply_row_style(row, payload)
            else:
                self._clear_row_background(row)

    def _clear_row_background(self, row_index: int) -> None:
        for column in range(self.columnCount()):
            item = self.item(row_index, column)
            if item is not None:
                item.setBackground(QBrush())

    def _apply_row_style(self, row_index: int, entry: AdjacencyDisplayItem) -> None:
        color_code = YIELD_COLOR_MAP.get(entry.yield_type or "")
        if self._enable_row_coloring and color_code:
            color = QColor(color_code)
            for column in range(self.columnCount()):
                item = self.item(row_index, column)
                if item is not None:
                    item.setBackground(color)
        else:
            self._clear_row_background(row_index)


@functools.lru_cache(maxsize=1)
def _terrain_name_map() -> Dict[str, str]:
    rows = _fetch_terrain_rows()
    return {terrain_type: _localize_tag(name) for terrain_type, name in rows}


@functools.lru_cache(maxsize=1)
def _feature_name_map() -> Dict[str, str]:
    rows = _fetch_feature_rows("", ())
    return {feature_type: _localize_tag(name) for feature_type, name, _natural, _impassable in rows}


@functools.lru_cache(maxsize=1)
def _improvement_name_map() -> Dict[str, str]:
    rows = _fetch_improvement_rows()
    return {imp_type: _localize_tag(name) for imp_type, name, _tech, _civic in rows}


@functools.lru_cache(maxsize=1)
def _district_name_map() -> Dict[str, str]:
    rows = _fetch_district_rows()
    return {district_type: _localize_tag(name_tag) for district_type, name_tag, _trait in rows}


@functools.lru_cache(maxsize=1)
def _technology_name_map() -> Dict[str, str]:
    rows = _fetch_technology_rows()
    return {tech_type: _localize_tag(name_tag) for tech_type, name_tag, _era in rows}


@functools.lru_cache(maxsize=1)
def _civic_name_map() -> Dict[str, str]:
    rows = _fetch_civic_rows()
    return {civic_type: _localize_tag(name_tag) for civic_type, name_tag, _era in rows}


def _resolve_named_value(kind: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if kind == "terrain":
        return _terrain_name_map().get(value, value)
    if kind == "feature":
        return _feature_name_map().get(value, value)
    if kind == "improvement":
        return _improvement_name_map().get(value, value)
    if kind == "district":
        return _district_name_map().get(value, value)
    if kind == "resource_class":
        return RESOURCE_CLASS_LABELS.get(value, value)
    return value


def _summarize_adjacency_sources(sources: Sequence[AdjacencySourceState]) -> str:
    if not sources:
        return ""
    parts: List[str] = []
    for source in sources:
        meta = ADJACENCY_TYPE_INFO.get(source.key, {})
        base_label = str(meta.get("label", source.key))
        if source.kind == "boolean":
            parts.append(base_label)
        else:
            detail = _resolve_named_value(source.kind, source.value)
            if detail:
                parts.append(f"{base_label}：{detail}")
            else:
                parts.append(base_label)
    return "；".join(parts)


_LOC_TOKEN_PATTERN = re.compile(r"\{LOC_([^}]+)\}")


def _replace_loc_tokens(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        candidate = token if token.startswith("LOC_") else f"LOC_{token}"
        localized = get_chinese_text_for_tag(candidate)
        return localized or match.group(0)

    return _LOC_TOKEN_PATTERN.sub(repl, text)


def _normalize_description_placeholders(text: str, yield_change: int) -> str:
    cleaned = _replace_loc_tokens(text)
    sign = "+" if yield_change > 0 else "-" if yield_change < 0 else ""
    abs_value = abs(int(yield_change))
    cleaned = re.sub(r"\+\{1_[nN]um\}", f"{sign}{abs_value}", cleaned)
    cleaned = re.sub(r"\+\{1_[aA]mount\}", f"{sign}{abs_value}", cleaned)
    cleaned = re.sub(r"\{1_[nN]um\}", str(int(yield_change)), cleaned)
    cleaned = re.sub(r"\{1_[aA]mount\}", str(int(yield_change)), cleaned)

    def plural_repl(match: re.Match[str]) -> str:
        inner = match.group(0)
        plural_match = re.search(r"plural\s*1\?([^;]+);\s*other\?([^;]+);", inner, re.IGNORECASE)
        if not plural_match:
            return ""
        one_text = plural_match.group(1).strip()
        other_text = plural_match.group(2).strip()
        return one_text if abs_value == 1 else other_text

    cleaned = re.sub(r"\{\s*1_(?:[nN]um|[aA]mount)\s*:\s*plural[^}]*\}", plural_repl, cleaned)
    cleaned = re.sub(r"\[ICON_[^\]]+\]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _localize_adjacency_description(record: AdjacencyYieldRecord) -> Optional[str]:
    tag = record.description
    if not tag:
        return None
    localized = get_chinese_text_for_tag(tag)
    if not localized and not tag.startswith("LOC_"):
        localized = get_chinese_text_for_tag(f"LOC_{tag}")
    if not localized:
        return None
    return _normalize_description_placeholders(localized, record.yield_change)


def _fallback_adjacency_description(record: AdjacencyYieldRecord, source_summary: str) -> str:
    yield_label = YIELD_VALUE_TO_NAME.get(record.yield_type or "", record.yield_type or "产出")
    change_prefix = "+" if record.yield_change > 0 else "-" if record.yield_change < 0 else ""
    base = f"{change_prefix}{abs(record.yield_change)}{yield_label}"
    if source_summary:
        return f"{base}（{source_summary}）"
    return base


def build_display_item_from_record(record: AdjacencyYieldRecord) -> AdjacencyDisplayItem:
    source_summary = _summarize_adjacency_sources(record.sources)
    description = _localize_adjacency_description(record)
    if not description:
        description = _fallback_adjacency_description(record, source_summary)
    payload = {
        "mode": "existing",
        "record": record,
    }
    return AdjacencyDisplayItem(
        identifier=record.identifier,
        yield_type=record.yield_type,
        yield_change=record.yield_change,
        description=description,
        source_summary=source_summary,
        tiles_required=record.tiles_required,
        entry_type="existing",
        payload=payload,
    )


def build_display_item_from_custom(data: Dict[str, object]) -> AdjacencyDisplayItem:
    yield_type = _normalize_text(data.get("yield_type"))
    yield_change = _safe_int(data.get("yield_change"), 0)
    tiles_required = _safe_int(data.get("tiles_required"), 0)
    source_type = _normalize_text(data.get("source_type")) or ""
    detail_value = _normalize_text(data.get("source_detail"))

    sources: List[AdjacencySourceState] = []
    meta = ADJACENCY_TYPE_INFO.get(source_type)
    if meta:
        if meta["kind"] == "boolean":
            sources.append(AdjacencySourceState(key=source_type, kind="boolean", value=None))
        else:
            sources.append(AdjacencySourceState(key=source_type, kind=meta["kind"], value=detail_value))

    source_summary = _summarize_adjacency_sources(sources)

    record = AdjacencyYieldRecord(
        identifier=_normalize_text(data.get("id")) or "",
        description=_normalize_text(data.get("description")),
        yield_type=yield_type,
        yield_change=yield_change,
        tiles_required=tiles_required,
        prereq_tech=_normalize_text(data.get("prereq_tech")),
        prereq_civic=_normalize_text(data.get("prereq_civic")),
        obsolete_tech=_normalize_text(data.get("obsolete_tech")),
        obsolete_civic=_normalize_text(data.get("obsolete_civic")),
        requirement_set_id=None,
        requirement_fail_set_id=None,
        sources=sources,
        raw=data,
    )

    description = record.description or _fallback_adjacency_description(record, source_summary)
    payload = {
        "mode": "custom",
        "data": data,
    }
    return AdjacencyDisplayItem(
        identifier=record.identifier,
        yield_type=record.yield_type,
        yield_change=record.yield_change,
        description=description,
        source_summary=source_summary,
        tiles_required=record.tiles_required,
        entry_type="custom",
        payload=payload,
    )


class AdjacencyExistingSelectorDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, include_placeholder: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择相邻加成")
        self.setModal(True)
        self.resize(960, 640)

        self._records = _fetch_adjacency_rows(include_placeholder)
        self._display_items = [build_display_item_from_record(record) for record in self._records]
        self._filtered_items: List[AdjacencyDisplayItem] = list(self._display_items)
        self._selected: List[AdjacencyDisplayItem] = []
        self._yield_sort_order = {
            yield_type: index
            for index, (_label, yield_type) in enumerate(YIELD_OPTIONS)
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel("产出筛选："))

        self._yield_checks: Dict[str, QCheckBox] = {}
        for label, yield_type in YIELD_OPTIONS:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._apply_filters)
            filter_row.addWidget(checkbox)
            self._yield_checks[yield_type] = checkbox

        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_row.addWidget(QLabel("搜索："))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("按ID、描述或来源搜索")
        self._search_edit.textChanged.connect(self._apply_filters)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        self._table = AdjacencyTableWidget(self)
        self._table.set_row_coloring_enabled(True)
        self._table.doubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filters()

    def _collect_selected_entries(self) -> List[AdjacencyDisplayItem]:
        selected_rows = sorted({index.row() for index in self._table.selectedIndexes()})
        entries: List[AdjacencyDisplayItem] = []
        for row in selected_rows:
            item = self._table.item(row, 0)
            if item is None:
                continue
            payload = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, AdjacencyDisplayItem):
                entries.append(payload)
        return entries

    def _handle_confirm(self) -> None:
        self._selected = self._collect_selected_entries()
        self.accept()

    def _handle_double_click(self, index) -> None:  # type: ignore[override]
        if not index.isValid():
            return
        self._selected = self._collect_selected_entries()
        if not self._selected:
            row = index.row()
            item = self._table.item(row, 0)
            entry = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if isinstance(entry, AdjacencyDisplayItem):
                self._selected = [entry]
        self.accept()

    def _apply_filters(self) -> None:
        active_yields = {
            yield_type
            for yield_type, checkbox in self._yield_checks.items()
            if checkbox.isChecked()
        }
        keyword = self._search_edit.text().strip().lower()
        filtered: List[AdjacencyDisplayItem] = []
        for item in self._display_items:
            if active_yields and item.yield_type not in active_yields:
                continue
            if keyword:
                components = [
                    (item.identifier or "").lower(),
                    (item.description or "").lower(),
                    (item.source_summary or "").lower(),
                ]
                haystack = "|".join(filter(None, components))
                if keyword not in haystack:
                    continue
            filtered.append(item)

        filtered.sort(key=self._sort_item_key)

        self._filtered_items = filtered
        self._table.clear_entries()
        self._table.extend_entries(self._filtered_items)

    def _sort_item_key(self, item: AdjacencyDisplayItem) -> tuple[int, str, str, int, str]:
        yield_type = item.yield_type or ""
        yield_rank = self._yield_sort_order.get(yield_type, len(self._yield_sort_order) + 1)
        yield_name = YIELD_VALUE_TO_NAME.get(yield_type, yield_type)
        return (
            yield_rank,
            yield_name,
            item.identifier or "",
            -int(item.yield_change),
            item.source_summary or "",
        )

    def selected_entries(self) -> List[AdjacencyDisplayItem]:
        return list(self._selected)


class AdjacencyCustomEntryDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        seed: Optional[Dict[str, object]] = None,
        auto_context: Optional[AdjacencyAutoContext] = None,
        fixed_description_placeholder: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("自定义相邻加成")
        self.setModal(True)
        self.resize(880, 720)

        self._context = auto_context or AdjacencyAutoContext()
        self._seed = seed or {}
        self._fixed_description_placeholder = bool(fixed_description_placeholder)
        self._result_item: Optional[AdjacencyDisplayItem] = None

        self._id_manual = False
        self._desc_manual = False
        self._current_source: Optional[str] = None
        self._detail_memory: Dict[str, Dict[str, object]] = {}

        self._technology_rows = _build_era_grouped_entries(_fetch_technology_rows())
        self._civic_rows = _build_era_grouped_entries(_fetch_civic_rows())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._build_basic_section(), 0)
        layout.addWidget(self._build_requirement_section(), 0)
        layout.addWidget(self._build_source_section(), 0)
        layout.addStretch(1)
        layout.addLayout(self._build_button_row())

        self._apply_seed_data()
        self._update_yield_hint()
        self._update_auto_fields(force=True)

    def _build_basic_section(self) -> QGroupBox:
        group = QGroupBox("基本信息", self)
        form = QFormLayout()
        form.setContentsMargins(10, 12, 10, 12)
        form.setSpacing(8)
        group.setLayout(form)

        self._id_edit = QLineEdit()
        self._id_edit.setPlaceholderText("自动生成或手动输入唯一ID")
        self._id_edit.textEdited.connect(self._mark_id_manual)
        id_row = QWidget()
        id_layout = QHBoxLayout(id_row)
        id_layout.setContentsMargins(0, 0, 0, 0)
        id_layout.setSpacing(6)
        id_layout.addWidget(self._id_edit, 1)
        self._id_auto_btn = QToolButton()
        self._id_auto_btn.setText("自动")
        self._id_auto_btn.setToolTip("根据当前配置重新生成ID")
        self._id_auto_btn.clicked.connect(self._reset_id_manual)
        id_layout.addWidget(self._id_auto_btn)
        form.addRow("ID：", id_row)

        self._desc_edit = QLineEdit()
        if self._fixed_description_placeholder:
            self._desc_edit.setPlaceholderText("固定占位符")
            self._desc_edit.setText("Placeholder")
            self._desc_edit.setReadOnly(True)
        else:
            self._desc_edit.setPlaceholderText("自动生成或手动输入描述")
            self._desc_edit.textEdited.connect(self._mark_desc_manual)
        desc_row = QWidget()
        desc_layout = QHBoxLayout(desc_row)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(6)
        desc_layout.addWidget(self._desc_edit, 1)
        self._desc_auto_btn = QToolButton()
        self._desc_auto_btn.setText("自动")
        if self._fixed_description_placeholder:
            self._desc_auto_btn.setToolTip("改良设施自定义相邻加成描述固定为 Placeholder")
            self._desc_auto_btn.setEnabled(False)
        else:
            self._desc_auto_btn.setToolTip("根据当前配置重新生成描述")
        self._desc_auto_btn.clicked.connect(self._reset_desc_manual)
        desc_layout.addWidget(self._desc_auto_btn)
        form.addRow("描述：", desc_row)

        self._yield_combo = QComboBox()
        for label, value in YIELD_OPTIONS:
            self._yield_combo.addItem(f"{label} | {value}", value)
        self._yield_combo.currentIndexChanged.connect(self._on_yield_changed)
        self._yield_hint_label = QLabel("")
        self._yield_hint_label.setStyleSheet("color: #6b7280;")
        yield_row = QWidget()
        yield_layout = QHBoxLayout(yield_row)
        yield_layout.setContentsMargins(0, 0, 0, 0)
        yield_layout.setSpacing(6)
        yield_layout.addWidget(self._yield_combo, 1)
        yield_layout.addWidget(self._yield_hint_label)
        form.addRow("产出类型：", yield_row)

        self._yield_spin = QSpinBox()
        self._yield_spin.setRange(-100, 100)
        self._yield_spin.setValue(1)
        self._yield_spin.valueChanged.connect(self._update_auto_fields)
        form.addRow("产出数值：", self._yield_spin)

        self._tiles_spin = QSpinBox()
        self._tiles_spin.setRange(0, 10)
        self._tiles_spin.setValue(1)
        form.addRow("需求地块：", self._tiles_spin)

        return group

    def _build_requirement_section(self) -> QGroupBox:
        group = QGroupBox("前置条件", self)
        form = QFormLayout()
        form.setContentsMargins(10, 12, 10, 12)
        form.setSpacing(8)
        group.setLayout(form)

        tech_widget, self._prereq_tech_state, self._prereq_tech_edit = self._create_requirement_selector(
            "科技",
            "前置科技",
            self._technology_rows,
        )
        form.addRow("前置科技：", tech_widget)

        civic_widget, self._prereq_civic_state, self._prereq_civic_edit = self._create_requirement_selector(
            "市政",
            "前置市政",
            self._civic_rows,
        )
        form.addRow("前置市政：", civic_widget)

        obsolete_tech_widget, self._obsolete_tech_state, self._obsolete_tech_edit = self._create_requirement_selector(
            "科技",
            "过时科技",
            self._technology_rows,
        )
        form.addRow("过时科技：", obsolete_tech_widget)

        obsolete_civic_widget, self._obsolete_civic_state, self._obsolete_civic_edit = self._create_requirement_selector(
            "市政",
            "过时市政",
            self._civic_rows,
        )
        form.addRow("过时市政：", obsolete_civic_widget)

        return group

    def _build_source_section(self) -> QGroupBox:
        group = QGroupBox("相邻来源", self)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)
        group.setLayout(layout)

        buttons_top = QHBoxLayout()
        buttons_top.setContentsMargins(0, 0, 0, 0)
        buttons_top.setSpacing(6)
        buttons_bottom = QHBoxLayout()
        buttons_bottom.setContentsMargins(0, 0, 0, 0)
        buttons_bottom.setSpacing(6)

        self._source_group_buttons = QButtonGroup(self)
        self._source_group_buttons.buttonClicked.connect(self._handle_source_clicked)
        self._source_buttons: Dict[str, QRadioButton] = {}

        for key, meta in ADJACENCY_TYPE_INFO.items():
            button = QRadioButton(meta["label"], group)
            button.setProperty("source_key", key)
            self._source_group_buttons.addButton(button)
            self._source_buttons[key] = button
            if meta["kind"] == "boolean":
                buttons_top.addWidget(button)
            else:
                buttons_bottom.addWidget(button)

        buttons_top.addStretch(1)
        buttons_bottom.addStretch(1)
        layout.addLayout(buttons_top)
        layout.addLayout(buttons_bottom)

        self._detail_stack = QStackedWidget(group)
        self._detail_pages: Dict[str, int] = {}
        self._detail_templates: Dict[str, BaseTemplateWidget] = {}

        for key in ADJACENCY_VALUE_KEYS:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(6)

            mapping = ADJACENCY_VALUE_MAPPINGS.get(key)
            template_widget: BaseTemplateWidget | None = None
            if mapping:
                template_widget = build_template_widget(mapping["template"])
                template_widget.setParent(page)
                label_setter = getattr(template_widget, "set_label_text", None)
                if callable(label_setter):
                    try:
                        label_setter(mapping["label"])
                    except TypeError:
                        pass
                template_widget.dataChanged.connect(lambda _=None, source_key=key: self._handle_detail_changed(source_key))
                page_layout.addWidget(template_widget)
                page_layout.addStretch(1)
                self._detail_templates[key] = template_widget
            else:
                notice = QLabel("此来源暂无可配置项")
                notice.setWordWrap(True)
                page_layout.addWidget(notice)
                page_layout.addStretch(1)

            index = self._detail_stack.addWidget(page)
            self._detail_pages[key] = index

        self._detail_stack.setVisible(False)
        layout.addWidget(self._detail_stack)

        return group

    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addStretch(1)
        confirm_btn = QPushButton("确定", self)
        confirm_btn.clicked.connect(self._handle_confirm)
        row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)
        return row

    def _create_requirement_selector(
        self,
        value_label: str,
        title_prefix: str,
        rows: Sequence[Tuple[str, str, str, str, int]],
    ) -> Tuple[QWidget, Dict[str, Optional[str]], QLineEdit]:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        line_edit = QLineEdit(container)
        line_edit.setPlaceholderText(f"点击选择{value_label}Type")
        line_edit.setReadOnly(True)
        layout.addWidget(line_edit, 1)

        select_button = QToolButton(container)
        select_button.setText("选择")
        layout.addWidget(select_button)

        clear_button = QToolButton(container)
        clear_button.setText("清除")
        layout.addWidget(clear_button)

        state: Dict[str, Optional[str]] = {"type": None, "display": None}

        def open_dialog() -> None:
            if not rows:
                QMessageBox.warning(self, "提示", f"未从数据库加载{value_label}数据")
                return
            dialog = _EraGroupedSelectionDialog(
                f"选择{value_label}",
                rows,
                ("时代", f"{value_label}名称", f"{value_label}Type"),
                self,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                result = dialog.selected_row()
                if result is not None:
                    state["type"] = result[3]
                    state["display"] = result[2]
                    line_edit.setText(result[2])
                    self._update_auto_fields()

        def clear_value() -> None:
            state["type"] = None
            state["display"] = None
            line_edit.clear()
            self._update_auto_fields()

        select_button.clicked.connect(open_dialog)
        clear_button.clicked.connect(clear_value)

        return container, state, line_edit

    def _handle_source_clicked(self, button) -> None:  # type: ignore[override]
        if button is None:
            return
        key = button.property("source_key")
        if not key:
            return
        key_str = str(key)
        previous = self._current_source
        if previous:
            template = self._detail_templates.get(previous)
            if template is not None:
                self._detail_memory[previous] = template.export_data()
        self._current_source = key_str
        if key_str in self._detail_pages:
            page_index = self._detail_pages[key_str]
            self._detail_stack.setCurrentIndex(page_index)
            self._detail_stack.setVisible(True)
            stored = self._detail_memory.get(key_str)
            if stored is not None:
                self._apply_template_data(key_str, stored)
            else:
                self._apply_template_data(key_str, {})
        else:
            self._detail_stack.setVisible(False)
        self._update_auto_fields()

    def _handle_detail_changed(self, source_key: str) -> None:
        template = self._detail_templates.get(source_key)
        if template is None:
            return
        self._detail_memory[source_key] = template.export_data()
        if self._current_source == source_key:
            self._update_auto_fields()

    def _apply_template_data(self, source_key: str, data: Dict[str, object]) -> None:
        template = self._detail_templates.get(source_key)
        if template is None:
            return
        mapping = ADJACENCY_VALUE_MAPPINGS.get(source_key)
        target_value: Optional[str] = None
        if mapping:
            value = data.get(mapping["value_key"])
            if not value and "value" in data:
                value = data.get("value")
            target_value = str(value) if value else None
        if isinstance(template, _DatasetComboTemplate):
            template.set_current_value(target_value)
        elif isinstance(template, _TypeSearchTemplate):
            normalized = template._normalize(target_value) if hasattr(template, "_normalize") else (target_value or "")
            template._selected_type = normalized or None
            display_text = str(data.get("display") or normalized or "")
            with _block_signals(template._line_edit):
                template._line_edit.setText(display_text)
        else:
            setter = getattr(template, "set_current_value", None)
            if callable(setter):
                setter(target_value)

    def _current_yield_type(self) -> Optional[str]:
        index = self._yield_combo.currentIndex()
        if index < 0:
            return None
        value = self._yield_combo.itemData(index)
        return str(value) if value else None

    def _get_source_detail_value(self, key: Optional[str] = None) -> Optional[str]:
        source_key = key or self._current_source
        if not source_key:
            return None
        mapping = ADJACENCY_VALUE_MAPPINGS.get(source_key)
        data: Dict[str, object] | None
        if mapping and source_key in self._detail_templates and self._current_source == source_key:
            data = self._detail_templates[source_key].export_data()
        else:
            stored = self._detail_memory.get(source_key)
            data = stored if isinstance(stored, dict) else None
        if not data:
            return None
        if mapping:
            value = data.get(mapping["value_key"]) or data.get("value")
            return str(value) if value else None
        value = data.get("value")
        return str(value) if value else None

    def _get_source_detail_label(self, key: Optional[str] = None) -> Optional[str]:
        source_key = key or self._current_source
        if not source_key:
            return None
        meta = ADJACENCY_TYPE_INFO.get(source_key)
        if not meta:
            return None
        detail_value = self._get_source_detail_value(source_key)
        return _resolve_named_value(meta.get("kind", ""), detail_value)

    def _mark_id_manual(self, _text: str) -> None:
        self._id_manual = True

    def _reset_id_manual(self) -> None:
        self._id_manual = False
        self._update_id(force=True)

    def _mark_desc_manual(self, _text: str) -> None:
        if self._fixed_description_placeholder:
            return
        self._desc_manual = True

    def _reset_desc_manual(self) -> None:
        if self._fixed_description_placeholder:
            self._desc_edit.blockSignals(True)
            self._desc_edit.setText("Placeholder")
            self._desc_edit.blockSignals(False)
            return
        self._desc_manual = False
        self._update_description(force=True)

    def _on_yield_changed(self, _index: int) -> None:
        self._update_yield_hint()
        self._update_auto_fields()

    def _update_yield_hint(self) -> None:
        yield_type = self._current_yield_type()
        if not yield_type:
            self._yield_hint_label.setText("")
            return
        label = YIELD_VALUE_TO_NAME.get(yield_type, yield_type)
        self._yield_hint_label.setText(label)

    def _update_auto_fields(self, force: bool = False) -> None:
        self._update_id(force=force)
        self._update_description(force=force)

    def _normalize_source_segment(self, source_key: str, detail_value: Optional[str]) -> Optional[str]:
        if source_key in ADJACENCY_BOOLEAN_KEYS:
            transformed = source_key.replace("Adjacent", "").replace("Other", "")
            return transformed or source_key
        if not detail_value:
            return None
        if source_key == "AdjacentResourceClass":
            return detail_value.replace("RESOURCECLASS_", "")
        # 修复：不要只取最后一个单词（如 MOUNTAIN），而是保留“首个下划线之后的全部内容”，
        # 例如 TERRAIN_SNOW_MOUNTAIN -> SNOW_MOUNTAIN，避免不同来源被压成同名 ID。
        text = detail_value.strip()
        head, sep, tail = text.partition("_")
        if sep and tail:
            return tail
        return head

    def _update_id(self, force: bool = False) -> None:
        if not force and self._id_manual:
            return
        parts: List[str] = []
        prefix = self._context.prefix.strip()
        if prefix:
            parts.append(prefix[:1].upper() + prefix[1:].lower())
        district_infix = self._context.district_infix.strip()
        if district_infix:
            parts.append(district_infix)
        district_code = self._context.district_code.strip()
        if district_code:
            parts.append(district_code)
        yield_type = self._current_yield_type()
        if yield_type:
            yield_segment = yield_type.replace("YIELD_", "").title().replace("_", "")
            parts.append(yield_segment)
        parts.append(str(self._yield_spin.value()))
        source_key = self._current_source
        detail_value = self._get_source_detail_value()
        if source_key:
            segment = self._normalize_source_segment(source_key, detail_value)
            if segment:
                if detail_value:
                    LOGGER.info(
                        "Adjacency auto-id source normalized: source=%s raw=%s segment=%s",
                        source_key,
                        detail_value,
                        segment,
                    )
                parts.append(segment)
        prereq_tech = self._prereq_tech_state.get("type")
        prereq_civic = self._prereq_civic_state.get("type")
        if prereq_tech:
            parts.append(prereq_tech.replace("TECH_", "").lower())
        elif prereq_civic:
            parts.append(prereq_civic.replace("CIVIC_", "").lower())
        generated = "_".join(filter(None, parts))
        self._id_edit.blockSignals(True)
        self._id_edit.setText(generated)
        self._id_edit.blockSignals(False)

    def _update_description(self, force: bool = False) -> None:
        if self._fixed_description_placeholder:
            self._desc_edit.blockSignals(True)
            self._desc_edit.setText("Placeholder")
            self._desc_edit.blockSignals(False)
            return
        if not force and self._desc_manual:
            return
        yield_type = self._current_yield_type()
        if not yield_type:
            return
        icon, yield_label = YIELD_ICON_LABEL_MAP.get(
            yield_type,
            ("", YIELD_VALUE_TO_NAME.get(yield_type, yield_type)),
        )
        main_part = f"+{{1_num}} {icon}{yield_label}".strip()
        components: List[str] = [main_part]

        source_key = self._current_source
        if source_key:
            if source_key == "Self":
                components.append("来自自身")
            else:
                source_meta = ADJACENCY_TYPE_INFO.get(source_key, {})
                base_label = str(source_meta.get("label", source_key))
                detail_label = self._get_source_detail_label()
                if detail_label:
                    if source_key in {"AdjacentDistrict", "AdjacentResourceClass"}:
                        components.append(f"来自相邻{detail_label}")
                    elif source_key in {"AdjacentTerrain", "AdjacentFeature", "AdjacentImprovement"}:
                        components.append(f"来自相邻{detail_label}单元格")
                    else:
                        components.append(f"来自{detail_label}")
                else:
                    components.append(f"来自{base_label}")

        prerequisites: List[str] = []
        prereq_tech = self._prereq_tech_state.get("type")
        prereq_civic = self._prereq_civic_state.get("type")
        if prereq_tech:
            tech_name = _technology_name_map().get(prereq_tech, prereq_tech)
            prerequisites.append(f"（需要{tech_name}）")
        elif prereq_civic:
            civic_name = _civic_name_map().get(prereq_civic, prereq_civic)
            prerequisites.append(f"（需要{civic_name}）")

        body_parts = [part for part in components if part and not part.startswith("（")]
        suffix = "".join(prerequisites)
        description = " ".join(body_parts) + suffix
        self._desc_edit.blockSignals(True)
        self._desc_edit.setText(description.strip())
        self._desc_edit.blockSignals(False)

    def _apply_seed_data(self) -> None:
        if not self._seed:
            if self._fixed_description_placeholder:
                self._desc_edit.setText("Placeholder")
            return
        identifier = _normalize_text(self._seed.get("id"))
        if identifier:
            self._id_edit.setText(identifier)
            self._id_manual = True
        if self._fixed_description_placeholder:
            self._desc_edit.setText("Placeholder")
        else:
            description = _normalize_text(self._seed.get("description"))
            if description:
                self._desc_edit.setText(description)
                self._desc_manual = True
        yield_type = _normalize_text(self._seed.get("yield_type"))
        if yield_type:
            index = self._yield_combo.findData(yield_type)
            if index != -1:
                self._yield_combo.setCurrentIndex(index)
        yield_change = self._seed.get("yield_change")
        if isinstance(yield_change, int):
            self._yield_spin.setValue(yield_change)
        tiles_required = self._seed.get("tiles_required")
        if isinstance(tiles_required, int):
            self._tiles_spin.setValue(tiles_required)

        prereq_tech = _normalize_text(self._seed.get("prereq_tech"))
        if prereq_tech:
            self._prereq_tech_state["type"] = prereq_tech
            self._prereq_tech_state["display"] = _technology_name_map().get(prereq_tech)
            self._prereq_tech_edit.setText(self._prereq_tech_state["display"] or prereq_tech)

        prereq_civic = _normalize_text(self._seed.get("prereq_civic"))
        if prereq_civic:
            self._prereq_civic_state["type"] = prereq_civic
            self._prereq_civic_state["display"] = _civic_name_map().get(prereq_civic)
            self._prereq_civic_edit.setText(self._prereq_civic_state["display"] or prereq_civic)

        obsolete_tech = _normalize_text(self._seed.get("obsolete_tech"))
        if obsolete_tech:
            self._obsolete_tech_state["type"] = obsolete_tech
            self._obsolete_tech_state["display"] = _technology_name_map().get(obsolete_tech)
            self._obsolete_tech_edit.setText(self._obsolete_tech_state["display"] or obsolete_tech)

        obsolete_civic = _normalize_text(self._seed.get("obsolete_civic"))
        if obsolete_civic:
            self._obsolete_civic_state["type"] = obsolete_civic
            self._obsolete_civic_state["display"] = _civic_name_map().get(obsolete_civic)
            self._obsolete_civic_edit.setText(self._obsolete_civic_state["display"] or obsolete_civic)

        source_type = _normalize_text(self._seed.get("source_type"))
        source_detail = _normalize_text(self._seed.get("source_detail"))
        if source_type and source_detail:
            mapping = ADJACENCY_VALUE_MAPPINGS.get(source_type)
            if mapping:
                detail_entry: Dict[str, object] = {
                    mapping["value_key"]: source_detail,
                    "value": source_detail,
                }
                source_meta = ADJACENCY_TYPE_INFO.get(source_type, {})
                detail_label = _resolve_named_value(source_meta.get("kind", ""), source_detail)
                if detail_label:
                    detail_entry["display"] = detail_label
                self._detail_memory[source_type] = detail_entry
        if source_type and source_type in self._source_buttons:
            button = self._source_buttons[source_type]
            button.setChecked(True)
            self._handle_source_clicked(button)

    def _collect_data(self) -> Optional[Dict[str, object]]:
        identifier = self._id_edit.text().strip()
        if not identifier:
            self._show_validation_error("ID不能为空")
            return None
        yield_type = self._current_yield_type()
        if not yield_type:
            self._show_validation_error("请选择产出类型")
            return None
        source_type = self._current_source
        if not source_type:
            self._show_validation_error("请选择相邻来源")
            return None
        detail_value = self._get_source_detail_value()
        if source_type in ADJACENCY_VALUE_KEYS and not detail_value:
            self._show_validation_error("请选择相邻来源的具体对象")
            return None
        data = {
            "id": identifier,
            "description": "Placeholder" if self._fixed_description_placeholder else self._desc_edit.text().strip(),
            "yield_type": yield_type,
            "yield_change": self._yield_spin.value(),
            "tiles_required": self._tiles_spin.value(),
            "prereq_tech": self._prereq_tech_state.get("type"),
            "prereq_civic": self._prereq_civic_state.get("type"),
            "obsolete_tech": self._obsolete_tech_state.get("type"),
            "obsolete_civic": self._obsolete_civic_state.get("type"),
            "source_type": source_type,
            "source_detail": detail_value,
        }
        return data

    def _handle_confirm(self) -> None:
        data = self._collect_data()
        if data is None:
            return
        self._result_item = build_display_item_from_custom(data)
        self.accept()

    def result_item(self) -> Optional[AdjacencyDisplayItem]:
        return self._result_item

    def _show_validation_error(self, message: str) -> None:
        QMessageBox.warning(self, "提示", message)


class AdjacencyEditorWidget(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        auto_context: Optional[AdjacencyAutoContext] = None,
        include_placeholder: bool = False,
        custom_description_placeholder: bool = False,
    ) -> None:
        super().__init__(parent)
        self._auto_context = auto_context or AdjacencyAutoContext()
        self._include_placeholder = include_placeholder
        self._custom_description_placeholder = custom_description_placeholder

        self._all_records = _fetch_adjacency_rows(include_placeholder)
        self._records_by_id = {record.identifier: record for record in self._all_records}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)

        self._add_existing_btn = QPushButton("添加已有", self)
        self._add_existing_btn.clicked.connect(self._handle_add_existing)
        button_row.addWidget(self._add_existing_btn)

        self._add_custom_btn = QPushButton("新增自定义", self)
        self._add_custom_btn.clicked.connect(self._handle_add_custom)
        button_row.addWidget(self._add_custom_btn)

        self._edit_custom_btn = QPushButton("编辑自定义", self)
        self._edit_custom_btn.clicked.connect(self._handle_edit_custom)
        self._edit_custom_btn.setEnabled(False)
        button_row.addWidget(self._edit_custom_btn)

        self._remove_btn = QPushButton("移除选中", self)
        self._remove_btn.clicked.connect(self._handle_remove_selected)
        self._remove_btn.setEnabled(False)
        button_row.addWidget(self._remove_btn)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        self._table = AdjacencyTableWidget(self, auto_height=True, min_visible_rows=0)
        self._table.itemSelectionChanged.connect(self._update_action_states)
        self._table.cellDoubleClicked.connect(self._handle_cell_double_click)
        layout.addWidget(self._table, 1)

    def _update_action_states(self) -> None:
        selected_entries = self._selected_entries()
        has_selection = bool(selected_entries)
        self._remove_btn.setEnabled(has_selection)
        self._edit_custom_btn.setEnabled(
            len(selected_entries) == 1 and selected_entries[0].entry_type == "custom"
        )

    def _selected_rows(self) -> List[int]:
        return sorted({index.row() for index in self._table.selectedIndexes()})

    def _selected_entries(self) -> List[AdjacencyDisplayItem]:
        entries: List[AdjacencyDisplayItem] = []
        for row in self._selected_rows():
            item = self._table.item(row, 0)
            if item is None:
                continue
            payload = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, AdjacencyDisplayItem):
                entries.append(payload)
        return entries

    def _handle_add_existing(self) -> None:
        dialog = AdjacencyExistingSelectorDialog(self, include_placeholder=self._include_placeholder)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_entries()
        existing_ids = {entry.identifier for entry in self._table.iter_entries() if entry.entry_type == "existing"}
        appended = False
        for entry in selected:
            if entry.identifier in existing_ids:
                continue
            self._table.append_entry(entry)
            appended = True
        if appended:
            self.dataChanged.emit()
            self._update_action_states()

    def _handle_add_custom(self) -> None:
        dialog = AdjacencyCustomEntryDialog(
            self,
            auto_context=self._auto_context,
            fixed_description_placeholder=self._custom_description_placeholder,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        item = dialog.result_item()
        if item is None:
            return
        self._table.append_entry(item)
        self.dataChanged.emit()
        self._update_action_states()

    def _handle_edit_custom(self) -> None:
        selected_rows = self._selected_rows()
        if len(selected_rows) != 1:
            return
        row = selected_rows[0]
        entry_item = self._table.item(row, 0)
        if entry_item is None:
            return
        entry = entry_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entry, AdjacencyDisplayItem) or entry.entry_type != "custom":
            return
        seed = self._extract_custom_seed(entry)
        dialog = AdjacencyCustomEntryDialog(
            self,
            seed=seed,
            auto_context=self._auto_context,
            fixed_description_placeholder=self._custom_description_placeholder,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.result_item()
        if updated is None:
            return
        self._table.update_entry(row, updated)
        self.dataChanged.emit()
        self._update_action_states()

    def _handle_remove_selected(self) -> None:
        removed = self._table.remove_selected_entries()
        if removed:
            self.dataChanged.emit()
        self._update_action_states()

    def _handle_cell_double_click(self, row: int, _column: int) -> None:
        item = self._table.item(row, 0)
        entry = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if isinstance(entry, AdjacencyDisplayItem) and entry.entry_type == "custom":
            self._handle_edit_custom()

    def set_payload(self, payload: Sequence[Dict[str, object]]) -> None:
        items: List[AdjacencyDisplayItem] = []
        for entry in payload:
            mode = entry.get("mode") or entry.get("type")
            if mode == "existing":
                identifier = _normalize_text(entry.get("id")) or _normalize_text(entry.get("identifier"))
                if not identifier:
                    continue
                record = self._get_record_by_id(identifier)
                if record is None:
                    continue
                items.append(build_display_item_from_record(record))
            elif mode == "custom":
                normalized = self._normalize_custom_payload(entry)
                items.append(build_display_item_from_custom(normalized))
        self._table.clear_entries()
        self._table.extend_entries(items)
        self._update_action_states()

    def export_payload(self) -> List[Dict[str, object]]:
        payload: List[Dict[str, object]] = []
        for entry in self._table.iter_entries():
            if entry.entry_type == "existing":
                record = entry.payload.get("record") if isinstance(entry.payload, dict) else None
                identifier = entry.identifier
                data = {"mode": "existing", "id": identifier}
                if isinstance(record, AdjacencyYieldRecord):
                    data.update(
                        {
                            "yield_type": record.yield_type,
                            "yield_change": record.yield_change,
                            "tiles_required": record.tiles_required,
                        }
                    )
                payload.append(data)
            else:
                data = {}
                raw = entry.payload.get("data") if isinstance(entry.payload, dict) else None
                if isinstance(raw, dict):
                    data.update(raw)
                data["mode"] = "custom"
                data.setdefault("id", entry.identifier)
                payload.append(data)
        return payload

    def _normalize_custom_payload(self, entry: Dict[str, object]) -> Dict[str, object]:
        result = {
            "id": entry.get("id"),
            "description": entry.get("description"),
            "yield_type": entry.get("yield_type"),
            "yield_change": entry.get("yield_change"),
            "tiles_required": entry.get("tiles_required"),
            "prereq_tech": entry.get("prereq_tech"),
            "prereq_civic": entry.get("prereq_civic"),
            "obsolete_tech": entry.get("obsolete_tech"),
            "obsolete_civic": entry.get("obsolete_civic"),
            "source_type": entry.get("source_type"),
            "source_detail": entry.get("source_detail"),
        }
        if self._custom_description_placeholder:
            result["description"] = "Placeholder"
        return result

    def _extract_custom_seed(self, entry: AdjacencyDisplayItem) -> Dict[str, object]:
        raw = entry.payload.get("data") if isinstance(entry.payload, dict) else None
        if isinstance(raw, dict):
            return dict(raw)
        return {
            "id": entry.identifier,
            "description": entry.description,
            "yield_type": entry.yield_type,
            "yield_change": entry.yield_change,
            "tiles_required": entry.tiles_required,
            "source_type": None,
            "source_detail": None,
        }

    def _refresh_record_cache(self) -> None:
        self._all_records = _fetch_adjacency_rows(self._include_placeholder)
        self._records_by_id = {record.identifier: record for record in self._all_records}

    def _get_record_by_id(self, identifier: str) -> Optional[AdjacencyYieldRecord]:
        record = self._records_by_id.get(identifier)
        if record is not None:
            return record
        self._refresh_record_cache()
        return self._records_by_id.get(identifier)

    def set_auto_context(self, context: AdjacencyAutoContext) -> None:
        self._auto_context = context


UNIT_CLASS_COLORS = (
    "#fde68a",
    "#bbf7d0",
    "#fee2e2",
    "#bfdbfe",
    "#f0abfc",
    "#fbcfe8",
    "#e5e7eb",
    "#c7d2fe",
    "#fed7aa",
    "#fef08a",
    "#bae6fd",
    "#ddd6fe",
    "#fecaca",
    "#dcfce7",
)


DISTRICT_PARENT_COLOR = "#e2e8f0"
DISTRICT_CHILD_COLOR = "#dbeafe"


def _localize_tag(tag: str) -> str:
    text = get_chinese_text_for_tag(tag) or ""
    return text.strip() or "未知"


def _fetch_feature_rows(where_clause: str, params: Sequence[object]) -> List[Tuple[str, str, int, int]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in EXCLUDED_FEATURE_TYPES)
        query = (
            "SELECT FeatureType, Name, IFNULL(NaturalWonder, 0), IFNULL(Impassable, 0) "
            "FROM Features "
            f"WHERE FeatureType NOT IN ({placeholders})"
            f"{where_clause}"
        )
        rows = cursor.execute(query, tuple(EXCLUDED_FEATURE_TYPES) + tuple(params)).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [
        (str(feature_type), str(name), int(natural), int(impassable))
        for feature_type, name, natural, impassable in rows
    ]


def _fetch_terrain_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT TerrainType, Name FROM Terrains").fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(terrain_type), str(name)) for terrain_type, name in rows]


def _fetch_era_rows() -> List[Tuple[str, str, int]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT EraType, Name, IFNULL(ChronologyIndex, 9999) FROM Eras"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [
        (str(era_type), str(name), int(index))
        for era_type, name, index in rows
    ]


def _fetch_resource_rows() -> List[Tuple[str, str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT ResourceType, Name, IFNULL(ResourceClassType, '') FROM Resources"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(res_type), str(name), str(class_type)) for res_type, name, class_type in rows]


def _fetch_district_rows() -> List[Tuple[str, str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT DistrictType, Name, IFNULL(TraitType, '') FROM Districts"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(district_type), str(name), str(trait_type)) for district_type, name, trait_type in rows]


def _fetch_district_replace_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT CivUniqueDistrictType, ReplacesDistrictType FROM DistrictReplaces"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(unique_type), str(replaces_type)) for unique_type, replaces_type in rows]


def _fetch_building_rows(include_wonders: bool) -> List[Tuple[str, str, int, int, str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT BuildingType, Name, IFNULL(Cost, 0), IFNULL(IsWonder, 0), "
            "IFNULL(TraitType, ''), IFNULL(PrereqDistrict, '') FROM Buildings"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    results: List[Tuple[str, str, int, int, str]] = []
    for building_type, name, cost, is_wonder, trait, prereq in rows:
        try:
            wonder_flag = int(is_wonder)
        except (TypeError, ValueError):
            wonder_flag = 0
        if not include_wonders and wonder_flag:
            continue
        try:
            cost_value = int(cost)
        except (TypeError, ValueError):
            cost_value = 0
        results.append((str(building_type), str(name), cost_value, wonder_flag, str(trait), str(prereq)))
    return results


def _fetch_unit_rows() -> List[Tuple[str, str, str, int, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT UnitType, Name, IFNULL(PromotionClass, ''), IFNULL(Cost, 0), IFNULL(TraitType, '') FROM Units"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    processed: List[Tuple[str, str, str, int, str]] = []
    for unit_type, name, promotion_class, cost, trait in rows:
        try:
            cost_value = int(cost)
        except (TypeError, ValueError):
            cost_value = 0
        processed.append((str(unit_type), str(name), str(promotion_class), cost_value, str(trait)))
    return processed


def _fetch_ability_class_tag_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT Tag FROM Tags WHERE Vocabulary = 'ABILITY_CLASS' ORDER BY Tag"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    parsed: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for (tag,) in rows:
        tag_text = str(tag or "").strip()
        if not tag_text:
            continue
        if tag_text in seen:
            continue
        seen.add(tag_text)
        parsed.append((tag_text, tag_text))
    return parsed


def _fetch_workspace_unit_ability_class_tag_rows() -> List[Tuple[str, str]]:
    parsed: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for entry in _workspace_entries("单位"):
        if not isinstance(entry, dict):
            continue
        subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
        bindings = (
            subtables.get("UnitAbilityBindings")
            if isinstance(subtables.get("UnitAbilityBindings"), list)
            else entry.get("unit_ability_bindings")
            if isinstance(entry.get("unit_ability_bindings"), list)
            else []
        )
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            tag_text = str(binding.get("Tag") or "").strip().upper()
            if not tag_text or tag_text in seen:
                continue
            seen.add(tag_text)
            parsed.append((tag_text, tag_text))
    return parsed


def _fetch_great_work_object_type_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT GreatWorkObjectType, IFNULL(Name, '') FROM GreatWorkObjectTypes ORDER BY GreatWorkObjectType"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    parsed: List[Tuple[str, str]] = []
    for object_type, name in rows:
        object_text = str(object_type or "").strip()
        if not object_text:
            continue
        localized = _localize_tag(str(name or ""))
        parsed.append((object_text, localized))
    return parsed


def _fetch_unit_ai_type_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT AiType FROM UnitAiTypes").fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    ai_type_cn_hints: Dict[str, str] = {
        "UNITAI_SETTLER": "开拓者/建城",
        "UNITAI_BUILDER": "建造者",
        "UNITAI_SCOUT": "侦察",
        "UNITAI_MELEE": "近战",
        "UNITAI_RANGED": "远程",
        "UNITAI_SIEGE": "攻城",
        "UNITAI_LIGHT_CAVALRY": "轻骑兵",
        "UNITAI_HEAVY_CAVALRY": "重骑兵",
        "UNITAI_SUPPORT": "支援",
        "UNITAI_COMBAT": "作战单位",
        "UNITAI_NAVAL_MELEE": "海军近战",
        "UNITAI_NAVAL_RANGED": "海军远程",
        "UNITAI_NAVAL_RAIDER": "海军突袭",
        "UNITAI_NAVAL_CARRIER": "航母",
        "UNITAI_AIR_FIGHTER": "战斗机",
        "UNITAI_AIR_BOMBER": "轰炸机",
        "UNITAI_SPY": "间谍",
        "UNITAI_RELIGIOUS": "宗教单位",
        "UNITAI_MISSIONARY": "传教士",
        "UNITAI_APOSTLE": "使徒",
        "UNITAI_INQUISITOR": "宗教裁判官",
        "UNITAI_TRADER": "商人",
        "UNITAI_GREAT_PERSON": "伟人",
        "UNITAI_ARCHAEOLOGIST": "考古学家",
        "UNITAI_MILITARY_ENGINEER": "军事工程师",
        "UNITAI_ROCK_BAND": "摇滚乐队",
        "UNITAI_AIRCRAFT_CARRIER": "航空母舰",
        "UNITAI_SPEC_OPS": "特种部队",
        "UNITAI_RANGER": "游骑兵",
        "UNITAI_FIELD_CANNON": "野战炮",
        "UNITAI_ANTI_AIR": "防空",
        "UNITAI_SUBMARINE": "潜艇",
        "UNITAI_DESTROYER": "驱逐舰",
        "UNITAI_BATTLESHIP": "战列舰",
        "UNITAI_FRIGATE": "护卫舰",
        "UNITTYPE_MELEE": "近战类型",
        "UNITTYPE_RANGED": "远程类型",
        "UNITTYPE_SIEGE": "攻城类型",
        "UNITTYPE_CAVALRY": "骑兵类型",
        "UNITTYPE_LIGHT_CAVALRY": "轻骑兵类型",
        "UNITTYPE_HEAVY_CAVALRY": "重骑兵类型",
        "UNITTYPE_SUPPORT": "支援类型",
        "UNITTYPE_RECON": "侦察类型",
        "UNITTYPE_LAND_COMBAT": "陆地作战类型",
        "UNITTYPE_NAVAL_MELEE": "海军近战类型",
        "UNITTYPE_NAVAL_RANGED": "海军远程类型",
        "UNITTYPE_NAVAL_RAIDER": "海军突袭类型",
        "UNITTYPE_AIR_FIGHTER": "战斗机类型",
        "UNITTYPE_AIR_BOMBER": "轰炸机类型",
        "UNITTYPE_RELIGIOUS": "宗教单位类型",
    }
    ai_token_cn = {
        "SETTLER": "开拓者",
        "BUILDER": "建造者",
        "SCOUT": "侦察",
        "MELEE": "近战",
        "RANGED": "远程",
        "SIEGE": "攻城",
        "LIGHT": "轻",
        "HEAVY": "重",
        "CAVALRY": "骑兵",
        "SUPPORT": "支援",
        "NAVAL": "海军",
        "RAIDER": "突袭",
        "CARRIER": "航母",
        "AIR": "空军",
        "FIGHTER": "战斗机",
        "BOMBER": "轰炸机",
        "SPY": "间谍",
        "RELIGIOUS": "宗教单位",
        "MISSIONARY": "传教士",
        "APOSTLE": "使徒",
        "INQUISITOR": "宗教裁判官",
        "TRADER": "商人",
        "GREAT": "大",
        "PERSON": "人物",
        "ARCHAEOLOGIST": "考古学家",
        "MILITARY": "军事",
        "ENGINEER": "工程师",
        "ROCK": "摇滚",
        "BAND": "乐队",
        "SUBMARINE": "潜艇",
        "DESTROYER": "驱逐舰",
        "BATTLESHIP": "战列舰",
        "FRIGATE": "护卫舰",
        "RANGER": "游骑兵",
        "FIELD": "野战",
        "CANNON": "炮",
        "ANTI": "防空",
        "AIRCRAFT": "航空",
        "SPEC": "特种",
        "OPS": "部队",
    }

    def _auto_cn_for_ai(ai_code: str) -> str:
        code = str(ai_code or "").strip().upper()
        if not code:
            return ""
        if code.startswith("UNITAI_"):
            code = code[7:]
        parts = [part for part in code.split("_") if part]
        merged: List[str] = []
        index = 0
        while index < len(parts):
            if index + 1 < len(parts):
                pair = f"{parts[index]}_{parts[index + 1]}"
                if pair == "GREAT_PERSON":
                    merged.append("伟人")
                    index += 2
                    continue
                if pair == "FIELD_CANNON":
                    merged.append("野战炮")
                    index += 2
                    continue
                if pair == "ROCK_BAND":
                    merged.append("摇滚乐队")
                    index += 2
                    continue
                if pair == "ANTI_AIR":
                    merged.append("防空")
                    index += 2
                    continue
                if pair == "SPEC_OPS":
                    merged.append("特种部队")
                    index += 2
                    continue
            merged.append(ai_token_cn.get(parts[index], parts[index]))
            index += 1
        text = "".join(merged).strip()
        if text:
            return text
        return ai_code

    output: List[Tuple[str, str]] = []
    for row in rows:
        ai_type = str((row[0] if row else "") or "").strip()
        if not ai_type:
            continue
        zh = ai_type_cn_hints.get(ai_type.upper()) or _auto_cn_for_ai(ai_type)
        output.append((ai_type, zh))
    output = sorted({item[0]: item for item in output}.values(), key=lambda item: item[0])
    return output


def _fetch_promotion_class_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        columns = _fetch_table_columns(cursor, "UnitPromotionClasses")
        if not columns:
            return []
        class_col = "PromotionClassType"
        if class_col not in columns and "UnitPromotionClassType" in columns:
            class_col = "UnitPromotionClassType"
        if class_col not in columns or "Name" not in columns:
            return []
        rows = cursor.execute(
            f"SELECT {class_col}, Name FROM UnitPromotionClasses"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(class_type), str(name)) for class_type, name in rows]


def _fetch_improvement_rows() -> List[Tuple[str, str, str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT ImprovementType, Name, IFNULL(PrereqTech, ''), IFNULL(PrereqCivic, '') FROM Improvements"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(imp_type), str(name), str(prereq_tech), str(prereq_civic)) for imp_type, name, prereq_tech, prereq_civic in rows]


def _build_district_hierarchy() -> List[Dict[str, object]]:
    pinned_entries: List[Dict[str, object]] = []
    pinned_types: set[str] = set()
    for entry in _workspace_entries("区域"):
        district_type = _workspace_entry_type(entry)
        if not district_type or district_type in pinned_types:
            continue
        pinned_types.add(district_type)
        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        pinned_entries.append(
            {
                "type": district_type,
                "name": _workspace_entry_display_name(entry),
                "indent": 0,
                "trait": str(table_data.get("TraitType") or "").strip(),
                "_workspace_pin": True,
            }
        )

    raw_rows = _fetch_district_rows()
    if not raw_rows:
        return pinned_entries
    info: Dict[str, Dict[str, object]] = {}
    base_types: List[str] = []
    trait_types: List[str] = []
    for district_type, name_tag, trait_type in raw_rows:
        localized = _localize_tag(name_tag)
        display_name = localized or name_tag
        trait = trait_type.strip() if trait_type else ""
        record = {
            "type": district_type,
            "name": display_name,
            "trait": trait,
        }
        info[district_type] = record
        if trait:
            trait_types.append(district_type)
        else:
            base_types.append(district_type)

    replacements = _fetch_district_replace_rows()
    children_map: Dict[str, List[str]] = {parent: [] for parent in base_types}
    handled_children: set[str] = set()
    for unique_type, replaces_type in replacements:
        if replaces_type in children_map and unique_type in info and unique_type in trait_types:
            children_map.setdefault(replaces_type, []).append(unique_type)
            handled_children.add(unique_type)

    for parent_type, child_list in children_map.items():
        child_list.sort(key=lambda c: str(info[c]["name"]))

    ordered: List[Dict[str, object]] = []
    seen: set[str] = set()
    for parent_type in sorted(base_types, key=lambda t: str(info[t]["name"])):
        ordered.append(
            {
                "type": parent_type,
                "name": info[parent_type]["name"],
                "indent": 0,
                "trait": info[parent_type]["trait"],
            }
        )
        seen.add(parent_type)
        for child_type in children_map.get(parent_type, []):
            ordered.append(
                {
                    "type": child_type,
                    "name": info[child_type]["name"],
                    "indent": 1,
                    "trait": info[child_type]["trait"],
                }
            )
            seen.add(child_type)

    remaining_trait = [t for t in trait_types if t not in seen]
    remaining_trait.sort(key=lambda t: str(info[t]["name"]))
    for district_type in remaining_trait:
        ordered.append(
            {
                "type": district_type,
                "name": info[district_type]["name"],
                "indent": 0,
                "trait": info[district_type]["trait"],
            }
        )
        seen.add(district_type)

    remaining_other = [t for t in info.keys() if t not in seen]
    remaining_other.sort(key=lambda t: str(info[t]["name"]))
    for district_type in remaining_other:
        ordered.append(
            {
                "type": district_type,
                "name": info[district_type]["name"],
                "indent": 0,
                "trait": info[district_type]["trait"],
            }
        )

    if pinned_types:
        ordered = [row for row in ordered if str(row.get("type") or "") not in pinned_types]
    return pinned_entries + ordered


def _build_building_entries(include_wonders: bool) -> List[Dict[str, object]]:
    district_lookup = _district_name_map()
    pinned_entries: List[Dict[str, object]] = []
    pinned_types: set[str] = set()

    def _field(entry: Dict[str, object], key: str, default: object = "") -> object:
        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        if key in table_data:
            return table_data.get(key)
        return entry.get(key, default)

    for entry in _workspace_entries("建筑"):
        building_type = _workspace_entry_type(entry) or str(_field(entry, "BuildingType") or "").strip()
        if not building_type or building_type in pinned_types:
            continue
        try:
            wonder_flag = int(_field(entry, "IsWonder", 0) or 0)
        except (TypeError, ValueError):
            wonder_flag = 0
        if not include_wonders and wonder_flag:
            continue
        # Workspace-created buildings are intentionally pinned to top regardless of prereq district.
        prereq_key = ""
        prereq_label = ""
        try:
            cost_value = int(_field(entry, "Cost", 0) or 0)
        except (TypeError, ValueError):
            cost_value = 0
        pinned_types.add(building_type)
        pinned_entries.append(
            {
                "type": building_type,
                "name": _workspace_entry_display_name(entry),
                "cost": cost_value,
                "is_wonder": bool(wonder_flag),
                "trait": str(_field(entry, "TraitType") or "").strip(),
                "prereq_district": prereq_key,
                "prereq_name": prereq_label,
                "_workspace_pin": True,
            }
        )

    raw_rows = _fetch_building_rows(include_wonders)
    entries: List[Dict[str, object]] = []
    for building_type, name_tag, cost_value, wonder_flag, trait_type, prereq_district in raw_rows:
        localized = _localize_tag(name_tag)
        display_name = localized or name_tag
        prereq_key = str(prereq_district or "").strip()
        prereq_label = district_lookup.get(prereq_key, prereq_key) if prereq_key else ""
        entries.append(
            {
                "type": building_type,
                "name": display_name,
                "cost": cost_value,
                "is_wonder": bool(wonder_flag),
                "trait": (trait_type or "").strip(),
                "prereq_district": prereq_key,
                "prereq_name": prereq_label,
            }
        )
    entries.sort(key=lambda entry: (entry["cost"], entry["name"], entry["type"]))
    if pinned_types:
        entries = [row for row in entries if str(row.get("type") or "") not in pinned_types]
    return pinned_entries + entries


def _building_group_label(entry: Dict[str, object]) -> str:
    prereq_key = str(entry.get("prereq_district") or "").strip()
    if not prereq_key:
        return "无区域"
    prereq_label = str(entry.get("prereq_name") or "").strip()
    if prereq_label and prereq_label != "未知":
        return prereq_label
    return prereq_key


def _generate_group_colors(keys: Sequence[str]) -> Dict[str, QColor]:
    color_map: Dict[str, QColor] = {}
    golden_ratio = 0.61803398875
    for idx, key in enumerate(keys):
        hue = (idx * golden_ratio) % 1.0
        color = QColor.fromHslF(hue, 0.35, 0.92)
        color_map[key] = color
    return color_map


def _building_group_color(label: str, group_colors: Dict[str, QColor]) -> QColor | None:
    if label == WORKSPACE_PIN_GROUP_LABEL:
        return QColor("#fde68a")
    if label == "奇观":
        return QColor("#fecaca")
    if label == "无区域":
        return QColor("#bfdbfe")
    color = group_colors.get(label)
    if color is not None:
        return color
    return QColor("#dbeafe")


def _build_promotion_class_lookup() -> Dict[str, Dict[str, object]]:
    lookup: Dict[str, Dict[str, object]] = {}
    for class_type, name_tag in _fetch_promotion_class_rows():
        localized = _localize_tag(name_tag)
        lookup[class_type] = {
            "type": class_type,
            "name": localized or name_tag,
        }
    return lookup


def _build_unit_entries() -> List[Dict[str, object]]:
    class_lookup = _build_promotion_class_lookup()

    pinned_entries: List[Dict[str, object]] = []
    pinned_types: set[str] = set()
    for entry in _workspace_entries("单位"):
        unit_type = _workspace_entry_type(entry)
        if not unit_type or unit_type in pinned_types:
            continue
        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        promotion_class = str(table_data.get("PromotionClass") or "").strip()
        promotion_info = class_lookup.get(promotion_class, {"name": promotion_class or "", "type": promotion_class})
        promotion_display = str(promotion_info.get("name") or "")
        if promotion_display == "未知":
            promotion_display = promotion_class
        try:
            cost_value = int(table_data.get("Cost") or 0)
        except (TypeError, ValueError):
            cost_value = 0
        pinned_types.add(unit_type)
        pinned_entries.append(
            {
                "type": unit_type,
                "name": _workspace_entry_display_name(entry),
                "promotion_class": promotion_class,
                "promotion_name": promotion_display,
                "cost": cost_value,
                "trait": str(table_data.get("TraitType") or "").strip(),
                "_workspace_pin": True,
            }
        )

    raw_rows = _fetch_unit_rows()
    entries: List[Dict[str, object]] = []
    for unit_type, name_tag, promotion_class, cost_value, trait_type in raw_rows:
        localized = _localize_tag(name_tag)
        display_name = localized or name_tag
        promotion_info = class_lookup.get(promotion_class, {"name": promotion_class or "", "type": promotion_class})
        promotion_display = promotion_info.get("name") or ""
        if promotion_display == "未知":
            promotion_display = promotion_class or ""
        entries.append(
            {
                "type": unit_type,
                "name": display_name,
                "promotion_class": promotion_class or "",
                "promotion_name": promotion_display,
                "cost": cost_value,
                "trait": (trait_type or "").strip(),
            }
        )
    entries.sort(
        key=lambda entry: (
            entry["promotion_class"],
            entry["cost"],
            entry["name"],
            entry["type"],
        )
    )
    if pinned_types:
        entries = [row for row in entries if str(row.get("type") or "") not in pinned_types]
    return pinned_entries + entries


def _build_improvement_entries() -> List[Dict[str, object]]:
    pinned_entries: List[Dict[str, object]] = []
    pinned_types: set[str] = set()
    for entry in _workspace_entries("改良设施"):
        imp_type = _workspace_entry_type(entry)
        if not imp_type or imp_type in pinned_types:
            continue
        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        pinned_types.add(imp_type)
        pinned_entries.append(
            {
                "type": imp_type,
                "name": _workspace_entry_display_name(entry),
                "prereq_tech": str(table_data.get("PrereqTech") or "").strip(),
                "prereq_civic": str(table_data.get("PrereqCivic") or "").strip(),
                "priority": 0,
                "order_value": -1,
                "order_label": "",
                "_workspace_pin": True,
            }
        )

    raw_rows = _fetch_improvement_rows()
    if not raw_rows:
        return pinned_entries

    tech_lookup = {entry[3]: (idx, entry[2]) for idx, entry in enumerate(_build_era_grouped_entries(_fetch_technology_rows()))}
    civic_lookup = {entry[3]: (idx, entry[2]) for idx, entry in enumerate(_build_era_grouped_entries(_fetch_civic_rows()))}

    entries: List[Dict[str, object]] = []
    for imp_type, name_tag, prereq_tech, prereq_civic in raw_rows:
        localized = _localize_tag(name_tag)
        display_name = localized or name_tag
        tech_key = prereq_tech.strip() if prereq_tech else ""
        civic_key = prereq_civic.strip() if prereq_civic else ""
        if tech_key and tech_key in tech_lookup:
            tech_order, tech_name = tech_lookup[tech_key]
        else:
            tech_order, tech_name = (9999, tech_key)
        if civic_key and civic_key in civic_lookup:
            civic_order, civic_name = civic_lookup[civic_key]
        else:
            civic_order, civic_name = (9999, civic_key)

        if tech_key:
            priority_group = 1
            order_value = tech_order
            order_label = tech_name or tech_key
        elif civic_key:
            priority_group = 2
            order_value = civic_order
            order_label = civic_name or civic_key
        else:
            priority_group = 0
            order_value = -1
            order_label = ""

        entries.append(
            {
                "type": imp_type,
                "name": display_name,
                "prereq_tech": tech_key,
                "prereq_civic": civic_key,
                "priority": priority_group,
                "order_value": order_value,
                "order_label": order_label,
            }
        )

    entries.sort(
        key=lambda entry: (
            entry["priority"],
            entry["order_value"],
            entry["order_label"],
            entry["name"],
            entry["type"],
        )
    )
    if pinned_types:
        entries = [row for row in entries if str(row.get("type") or "") not in pinned_types]
    return pinned_entries + entries


def _fetch_technology_rows() -> List[Tuple[str, str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT TechnologyType, Name, IFNULL(EraType, '') FROM Technologies"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(tech_type), str(name), str(era_type)) for tech_type, name, era_type in rows]


def _fetch_civic_rows() -> List[Tuple[str, str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT CivicType, Name, IFNULL(EraType, '') FROM Civics"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(civic_type), str(name), str(era_type)) for civic_type, name, era_type in rows]


def _fetch_great_person_class_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error:
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT GreatPersonClassType, Name FROM GreatPersonClasses "
            # "WHERE IFNULL(AvailableInTimeline, 0) = 1"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [(str(class_type), str(name)) for class_type, name in rows]


def _fetch_government_slot_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        LOGGER.warning("GovernmentSlots lookup skipped: game DB not found at %s", DEFAULT_GAME_DB)
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error as exc:
        LOGGER.warning("GovernmentSlots lookup failed to open DB: %s", exc)
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT GovernmentSlotType, IFNULL(Name, '') FROM GovernmentSlots ORDER BY GovernmentSlotType"
        ).fetchall()
    except sqlite3.Error as exc:
        LOGGER.warning("GovernmentSlots query failed: %s", exc)
        rows = []
    finally:
        conn.close()

    output: List[Tuple[str, str]] = []
    for slot_type, name_tag in rows:
        slot_text = str(slot_type or "").strip()
        if not slot_text:
            continue
        localized = _localize_tag(str(name_tag or ""))
        display = localized if localized and localized != "未知" else slot_text
        output.append((slot_text, display))
    LOGGER.info("Loaded %d GovernmentSlots options", len(output))
    return output


def _fetch_government_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        LOGGER.warning("Governments lookup skipped: game DB not found at %s", DEFAULT_GAME_DB)
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error as exc:
        LOGGER.warning("Governments lookup failed to open DB: %s", exc)
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT GovernmentType, IFNULL(Name, '') FROM Governments ORDER BY GovernmentType"
        ).fetchall()
    except sqlite3.Error as exc:
        LOGGER.warning("Governments query failed: %s", exc)
        rows = []
    finally:
        conn.close()

    output: List[Tuple[str, str]] = []
    for government_type, name_tag in rows:
        gov_text = str(government_type or "").strip()
        if not gov_text:
            continue
        localized = _localize_tag(str(name_tag or ""))
        display = localized if localized and localized != "未知" else gov_text
        output.append((gov_text, display))
    LOGGER.info("Loaded %d Government options", len(output))
    return output


def _fetch_belief_class_rows() -> List[Tuple[str, str]]:
    if not DEFAULT_GAME_DB.exists():
        LOGGER.warning("BeliefClasses lookup skipped: game DB not found at %s", DEFAULT_GAME_DB)
        return []
    try:
        conn = sqlite3.connect(str(DEFAULT_GAME_DB))
    except sqlite3.Error as exc:
        LOGGER.warning("BeliefClasses lookup failed to open DB: %s", exc)
        return []
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT BeliefClassType, IFNULL(Name, '') FROM BeliefClasses ORDER BY BeliefClassType"
        ).fetchall()
    except sqlite3.Error as exc:
        LOGGER.warning("BeliefClasses query failed: %s", exc)
        rows = []
    finally:
        conn.close()

    output: List[Tuple[str, str]] = []
    for class_type, name_tag in rows:
        class_text = str(class_type or "").strip()
        if not class_text:
            continue
        localized = _localize_tag(str(name_tag or ""))
        display = localized if localized and localized != "未知" else class_text
        output.append((class_text, display))
    LOGGER.info("Loaded %d BeliefClasses options", len(output))
    return output


def _build_era_lookup() -> Dict[str, Tuple[int, str]]:
    lookup: Dict[str, Tuple[int, str]] = {}
    for era_type, name, index in _fetch_era_rows():
        localized_name = _localize_tag(name)
        lookup[era_type] = (index, localized_name)
    return lookup


def _format_era_label(era_type: str, localized_name: str) -> str:
    if localized_name and localized_name != "未知":
        if era_type:
            return f"{localized_name} {era_type}"
        return localized_name
    return era_type or "未分类"


def _build_era_grouped_entries(
    raw_rows: Sequence[Tuple[str, str, str]]
) -> List[Tuple[str, str, str, str, int]]:
    era_lookup = _build_era_lookup()
    grouped: List[Tuple[str, str, str, str, int]] = []
    for value_type, name_tag, era_type in raw_rows:
        localized_name = _localize_tag(name_tag)
        order, localized_era = era_lookup.get(era_type, (9999, ""))
        era_label = _format_era_label(era_type, localized_era)
        grouped.append((era_type or "", era_label, localized_name, value_type, order))
    grouped.sort(key=lambda entry: (entry[4], entry[1], entry[2], entry[3]))
    return grouped


class BaseTemplateWidget(QWidget):
    """Base widget exposing consistent data access."""

    dataChanged = pyqtSignal()

    def __init__(self, display_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._display_name = display_name
        self.setProperty("templateWidget", "true")
        self._compact_mode_applied = False
        self._in_item_view_cached: bool | None = None

    def _ancestor_item_view(self) -> QAbstractItemView | None:
        widget = self.parentWidget()
        while widget is not None:
            if isinstance(widget, QAbstractItemView):
                return widget
            widget = widget.parentWidget()
        return None

    def _apply_table_compact_mode_if_needed(self) -> None:
        in_item_view = self._ancestor_item_view() is not None
        if self._in_item_view_cached is in_item_view:
            return
        self._in_item_view_cached = in_item_view

        if in_item_view:
            self.setProperty("templateInItemView", "true")
            if not self._compact_mode_applied:
                layout = self.layout()
                if layout is not None:
                    layout.setContentsMargins(2, 2, 2, 2)
                    layout.setSpacing(4)
                    if layout.count() > 0:
                        last_item = layout.itemAt(layout.count() - 1)
                        if last_item is not None and last_item.spacerItem() is not None:
                            layout.takeAt(layout.count() - 1)
                    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                self._compact_mode_applied = True
        else:
            self.setProperty("templateInItemView", "false")

        # re-polish to apply dynamic property based QSS.
        try:
            style = self.style()
            style.unpolish(self)
            style.polish(self)
        except Exception:
            pass
        self.update()

    def event(self, event) -> bool:
        if event.type() in (QEvent.Type.ParentChange, QEvent.Type.Show):
            self._apply_table_compact_mode_if_needed()
        return super().event(event)

    @property
    def display_name(self) -> str:
        return self._display_name

    def export_data(self) -> Dict[str, object]:  # pragma: no cover - UI helper
        raise NotImplementedError

    def summary_text(self) -> str:
        data = self.export_data()
        if not data:
            return "{}"
        formatted = ", ".join(f"{key}={value}" for key, value in data.items())
        return formatted


class NewlineTokenTextEdit(QPlainTextEdit):
    """多行文本输入框：导出时使用 [NEWLINE] 作为换行符。"""

    TOKEN = "[NEWLINE]"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        try:
            _apply_drop_shadow(self)
        except Exception:
            pass

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.insertPlainText(self.TOKEN)
            event.accept()
            return
        super().keyPressEvent(event)

    def insertFromMimeData(self, source) -> None:
        """确保粘贴/拖入的真实换行符也会被转换为 [NEWLINE]。"""

        try:
            if source is not None and source.hasText():
                text = source.text() or ""
                if text:
                    normalized = (
                        text.replace("\r\n", "\n")
                        .replace("\r", "\n")
                        .replace("\u2029", "\n")
                        .replace("\u2028", "\n")
                    )
                    self.insertPlainText(normalized.replace("\n", self.TOKEN))
                    return
        except Exception:
            LOGGER.exception("Failed to tokenize pasted text")

        super().insertFromMimeData(source)

    def export_tokenized_text(self) -> str:
        text = self.toPlainText()
        if not text:
            return ""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.replace("\n", self.TOKEN)

    def import_tokenized_text(self, value: object | None) -> None:
        raw = "" if value is None else str(value)
        normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
        self.setPlainText(normalized.replace("\n", self.TOKEN))


_FONT_ICON_REGISTRY: FontIconRegistry | None = None
_FONT_ICON_ATLASES: dict[str, DdsRgba32Atlas] = {}


def _get_font_icon_registry() -> FontIconRegistry:
    global _FONT_ICON_REGISTRY
    if _FONT_ICON_REGISTRY is None:
        _FONT_ICON_REGISTRY = FontIconRegistry.load_default()
    return _FONT_ICON_REGISTRY


def _get_font_icon_atlas(sheet_filename: str) -> DdsRgba32Atlas:
    key = str(sheet_filename or "").strip()
    atlas = _FONT_ICON_ATLASES.get(key)
    if atlas is not None:
        return atlas
    atlas = DdsRgba32Atlas(resolve_default_fonticons_dds_path(key))
    _FONT_ICON_ATLASES[key] = atlas
    return atlas


class IconTokenTextEdit(QTextEdit):
    """Text editor that displays Civ6 FontIcons as inline images.

    - UI shows icons (DDS slices) instead of raw tokens.
    - Export/preview uses token form: [ICON_Name]
    - Keeps existing newline token convention: [NEWLINE]
    """

    NEWLINE_TOKEN = "[NEWLINE]"

    _ICON_TOKEN_RE = re.compile(r"\[ICON_([^\]]+)\]")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptRichText(True)
        self.setUndoRedoEnabled(True)
        try:
            _apply_drop_shadow(self)
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Keep the existing tokenized newline behavior.
            self.insertPlainText(self.NEWLINE_TOKEN)
            event.accept()
            return
        super().keyPressEvent(event)

    def insertFromMimeData(self, source) -> None:
        """Normalize pasted text: real newlines -> [NEWLINE]."""

        try:
            if source is not None and source.hasText():
                text = source.text() or ""
                if text:
                    normalized = (
                        text.replace("\r\n", "\n")
                        .replace("\r", "\n")
                        .replace("\u2029", "\n")
                        .replace("\u2028", "\n")
                    )
                    self.insertPlainText(normalized.replace("\n", self.NEWLINE_TOKEN))
                    return
        except Exception:
            LOGGER.exception("Failed to tokenize pasted text")

        super().insertFromMimeData(source)

    def contextMenuEvent(self, event) -> None:
        # UX: right-click opens the icon picker popup at mouse position.
        registry = _get_font_icon_registry()
        if not registry.has_icons():
            super().contextMenuEvent(event)
            return

        try:
            cursor = self.cursorForPosition(event.pos())
            self.setTextCursor(cursor)
        except Exception:
            pass

        popup = FontIconPopup(registry=registry, parent=self)
        popup.iconPicked.connect(self._insert_icon_by_name)
        popup.adjustSize()

        global_pos = event.globalPos()
        screen = QGuiApplication.screenAt(global_pos)
        if screen is None:
            screen = self.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = int(global_pos.x())
            y = int(global_pos.y())
            w = int(popup.width())
            h = int(popup.height())

            # X: clamp within screen.
            if x + w > avail.right():
                x = int(avail.right() - w)
            if x < avail.left():
                x = int(avail.left())

            # Y: prefer below cursor; if not enough, show above.
            if y + h > avail.bottom():
                y = int(global_pos.y() - h)
            if y < avail.top():
                y = int(avail.top())

            popup.move(x, y)
        else:
            popup.move(global_pos)
        popup.show()

    def export_tokenized_text(self) -> str:
        doc = self.document()
        out: list[str] = []
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    fmt = frag.charFormat()
                    if fmt.isImageFormat():
                        img = fmt.toImageFormat()
                        name = self._icon_name_from_image(img)
                        if name:
                            out.append(f"[ICON_{name}]")
                        else:
                            out.append("")
                    else:
                        out.append(frag.text())
                it += 1
            block = block.next()
            if block.isValid():
                out.append("\n")

        text = "".join(out)
        if not text:
            return ""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.replace("\n", self.NEWLINE_TOKEN)

    def import_tokenized_text(self, value: object | None) -> None:
        raw = "" if value is None else str(value)
        normalized = raw.replace("\r\n", "\n").replace("\r", "\n")

        self.blockSignals(True)
        try:
            self.clear()
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.setTextCursor(cursor)

            # Split into tokens and literal text.
            pattern = re.compile(r"(\[ICON_[^\]]+\]|\[NEWLINE\])")
            parts = pattern.split(normalized)
            for part in parts:
                if not part:
                    continue
                if part == self.NEWLINE_TOKEN:
                    self.insertPlainText(self.NEWLINE_TOKEN)
                    continue
                match = self._ICON_TOKEN_RE.fullmatch(part)
                if match:
                    name = str(match.group(1) or "").strip()
                    if name:
                        self._insert_icon_by_name(name)
                    continue
                self.insertPlainText(part)
        finally:
            self.blockSignals(False)
            self.textChanged.emit()

    def _icon_name_from_image(self, img: QTextImageFormat) -> str:
        ref = str(img.name() or "").strip()
        if not ref:
            return ""
        if ref.startswith("civ6icon:"):
            return ref.split(":", 1)[1].lstrip("/")
        if ref.startswith("civ6icon://"):
            return ref.split("//", 1)[1]
        return ""

    def _insert_icon_by_name(self, icon_name: str) -> None:
        name = str(icon_name or "").strip()
        if not name:
            return

        registry = _get_font_icon_registry()
        sheet, idx = registry.resolve(name)
        if sheet is None or idx is None:
            # Fallback: insert token text.
            self.insertPlainText(f"[ICON_{name}]")
            return

        atlas = _get_font_icon_atlas(sheet.filename)
        pix = atlas.pixmap_for_index(icon_size=sheet.icon_size, cols=sheet.cols, index=idx, scale=1)
        if pix is None:
            self.insertPlainText(f"[ICON_{name}]")
            return

        image = pix.toImage()
        url = QUrl(f"civ6icon:{name}")
        self.document().addResource(QTextDocument.ResourceType.ImageResource, url, image)

        fmt = QTextImageFormat()
        fmt.setName(url.toString())
        fmt.setWidth(float(sheet.icon_size))
        fmt.setHeight(float(sheet.icon_size))
        fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignMiddle)
        self.textCursor().insertImage(fmt)


class TextInputTemplate(BaseTemplateWidget):
    """Accepts free-form strings, useful for notes or identifiers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("文本输入框", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("输入文本：")
        row.addWidget(self._label)

        self._line_edit = QLineEdit()
        self._line_edit.textChanged.connect(self.dataChanged)
        row.addWidget(self._line_edit, 1)
        layout.addLayout(row)
        layout.addStretch(1)

    def export_data(self) -> Dict[str, object]:
        return {"text": self._line_edit.text()}

    def summary_text(self) -> str:
        return self._line_edit.text() or "(空)"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def set_current_value(self, value: Optional[str]) -> None:
        self._line_edit.blockSignals(True)
        self._line_edit.setText("" if value is None else str(value))
        self._line_edit.blockSignals(False)
        self.dataChanged.emit()


class BinaryChoiceTemplate(BaseTemplateWidget):
    """Presents an exclusive yes/no switch rendered with check icons."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("二选一勾选按钮", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("二选一：")
        row.addWidget(self._label)

        choice_container = QWidget()
        choice_layout = QHBoxLayout(choice_container)
        choice_layout.setContentsMargins(0, 0, 0, 0)
        choice_layout.setSpacing(12)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._yes_checkbox = QCheckBox("是")
        self._no_checkbox = QCheckBox("否")
        self._yes_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self._no_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self._yes_checkbox.setChecked(True)
        self._button_group.addButton(self._yes_checkbox, 1)
        self._button_group.addButton(self._no_checkbox, 0)
        self._yes_checkbox.stateChanged.connect(self._on_state_changed)
        self._no_checkbox.stateChanged.connect(self._on_state_changed)

        choice_layout.addWidget(self._yes_checkbox)
        choice_layout.addWidget(self._no_checkbox)
        choice_layout.addStretch(1)

        row.addWidget(choice_container, 1)
        layout.addLayout(row)
        layout.addStretch(1)

    def export_data(self) -> Dict[str, object]:
        checked_id = self._button_group.checkedId()
        return {"selected": bool(checked_id)}

    def summary_text(self) -> str:
        checked_id = self._button_group.checkedId()
        if checked_id == -1:
            return "未选择"
        return "是" if checked_id == 1 else "否"

    def _on_state_changed(self) -> None:
        self.dataChanged.emit()

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class ChoiceTemplate(BaseTemplateWidget):
    """Collects a single option from a fixed four-value list."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("选择框", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("选择框：")
        row.addWidget(self._label)

        self._combo = QComboBox()
        for option in ("A", "B", "C", "D"):
            self._combo.addItem(option)
        self._combo.currentIndexChanged.connect(self.dataChanged)
        row.addWidget(self._combo, 1)
        layout.addLayout(row)
        layout.addStretch(1)

    def export_data(self) -> Dict[str, object]:
        return {"choice": self._combo.currentText()}

    def summary_text(self) -> str:
        return self._combo.currentText()

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class TourismSourceTemplate(BaseTemplateWidget):
    """Selector for Improvement_Tourism.TourismSource.

    固定枚举（内置）：
    - NO_TOURISMSOURCE（默认）
    - TOURISMSOURCE_CULTURE
    - TOURISMSOURCE_FAITH
    - TOURISMSOURCE_APPEAL
    - TOURISMSOURCE_FOOD
    - TOURISMSOURCE_GOLD
    - TOURISMSOURCE_PRODUCTION
    - TOURISMSOURCE_SCIENCE
    """

    DEFAULT_VALUE = "NO_TOURISMSOURCE"
    OPTIONS = (
        "NO_TOURISMSOURCE",
        "TOURISMSOURCE_CULTURE",
        "TOURISMSOURCE_FAITH",
        "TOURISMSOURCE_APPEAL",
        "TOURISMSOURCE_FOOD",
        "TOURISMSOURCE_GOLD",
        "TOURISMSOURCE_PRODUCTION",
        "TOURISMSOURCE_SCIENCE",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("TourismSource选择框", parent)
        self._label = QLabel("TourismSource：")
        self._combo = QComboBox()
        self._combo.setEditable(False)
        self._combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._combo.setMinimumContentsLength(14)
        with _block_signals(self._combo):
            for item in self.OPTIONS:
                self._combo.addItem(item, item)
            self._combo.setCurrentIndex(0)
        self._combo.currentIndexChanged.connect(self.dataChanged.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._label)
        row.addWidget(self._combo, 1)
        layout.addLayout(row)
        layout.addStretch(1)

    def export_data(self) -> Dict[str, object]:
        value = str(self._combo.currentData() or "").strip() or self.DEFAULT_VALUE
        return {"value": value, "display": value, "name": value, "text": value}

    def summary_text(self) -> str:
        value = str(self._combo.currentData() or "").strip() or self.DEFAULT_VALUE
        return value

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def set_current_value(self, value: Optional[str]) -> None:
        normalized = str(value or "").strip() or self.DEFAULT_VALUE
        with _block_signals(self._combo):
            idx = self._combo.findData(normalized)
            if idx != -1:
                self._combo.setCurrentIndex(idx)
            else:
                self._combo.setCurrentIndex(0 if self._combo.count() else -1)
        self.dataChanged.emit()


class IntegerSpinTemplate(BaseTemplateWidget):
    """Captures integer quantities via a spin box with arrow controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("整数输入框", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("数值：")
        row.addWidget(self._label)

        self._spin = QSpinBox()
        self._spin.setRange(-2147483648, 2147483647)
        self._spin.setValue(0)
        self._spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self._spin.valueChanged.connect(self.dataChanged.emit)
        row.addWidget(self._spin, 1)

        layout.addLayout(row)
        layout.addStretch(1)

    def export_data(self) -> Dict[str, object]:
        return {"value": self._spin.value()}

    def summary_text(self) -> str:
        return str(self._spin.value())

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class _DatasetComboTemplate(BaseTemplateWidget):
    """Shared combo-box behaviour for database-backed selectors."""

    def __init__(
        self,
        display_name: str,
        default_label: str,
        value_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(display_name, parent)
        self._value_key = value_key
        self._label = QLabel(f"{default_label}：")
        self._combo = QComboBox()
        self._options: List[Tuple[str, str]] = []
        self._placeholder = f"请选择{default_label}" if default_label else "请选择"
        self._combo.currentIndexChanged.connect(self.dataChanged.emit)
        self._build_layout()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._label)
        row.addWidget(self._combo, 1)

        layout.addLayout(row)
        layout.addStretch(1)

    def _populate_options(self, feature_rows: Sequence[Tuple[str, str]]) -> None:
        self._combo.clear()
        self._options = list(feature_rows)
        self._combo.addItem(self._placeholder, None)
        if not self._options:
            self._combo.setEnabled(False)
            return
        for display_name, feature_type in self._options:
            self._combo.addItem(f"{display_name} | {feature_type}", feature_type)
        self._combo.setEnabled(True)

    def _option_for_index(self, index: int) -> Tuple[str, str] | None:
        if index <= 0:
            return None
        real_index = index - 1
        if 0 <= real_index < len(self._options):
            return self._options[real_index]
        return None

    def export_data(self) -> Dict[str, object]:
        option = self._option_for_index(self._combo.currentIndex())
        if option is None:
            return {self._value_key: None, "display": "", "name": "", "value": None}
        display_name, feature_type = option
        return {
            self._value_key: feature_type,
            "display": display_name,
            "name": display_name,
            "value": feature_type,
        }

    def summary_text(self) -> str:
        option = self._option_for_index(self._combo.currentIndex())
        if option is None:
            return "未选择"
        return option[0]

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def set_current_value(self, value: Optional[str]) -> None:
        with _block_signals(self._combo):
            if value is None:
                self._combo.setCurrentIndex(0 if self._combo.count() else -1)
                return
            index = self._combo.findData(value)
            if index == -1:
                self._combo.setCurrentIndex(0 if self._combo.count() else -1)
            else:
                self._combo.setCurrentIndex(index)


class AbilityClassTagTemplate(BaseTemplateWidget):
    """Selector for Tags.Vocabulary='ABILITY_CLASS'."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("ABILITY_CLASS标签选择框", parent)
        self._label = QLabel("单位标签：")
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.currentTextChanged.connect(self.dataChanged.emit)
        self._options: List[Tuple[str, str]] = []
        self._placeholder = "可输入或选择 ABILITY_CLASS 标签"
        self._build_layout()
        self._populate_options(
            workspace_rows=_fetch_workspace_unit_ability_class_tag_rows(),
            db_rows=_fetch_ability_class_tag_rows(),
        )
        line_edit = self._combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(self._placeholder)

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._label)
        row.addWidget(self._combo, 1)
        layout.addLayout(row)
        layout.addStretch(1)

    def _normalize_value(self, value: object | None) -> str:
        return str(value or "").strip().upper()

    def _populate_options(
        self,
        workspace_rows: Sequence[Tuple[str, str]],
        db_rows: Sequence[Tuple[str, str]],
    ) -> None:
        merged: List[Tuple[str, str]] = []
        seen: set[str] = set()

        def _append_rows(rows: Sequence[Tuple[str, str]]) -> None:
            for tag_type, _name in rows:
                normalized = self._normalize_value(tag_type)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                merged.append((normalized, normalized))

        _append_rows(workspace_rows)
        _append_rows(sorted(db_rows, key=lambda item: str(item[0] or "")))
        self._options = merged

        with _block_signals(self._combo):
            self._combo.clear()
            for tag_type, _name in self._options:
                self._combo.addItem(tag_type, tag_type)

    def export_data(self) -> Dict[str, object]:
        current_data = self._combo.currentData()
        if current_data is None:
            current_data = self._combo.currentText()
        value = self._normalize_value(current_data)
        if not value:
            return {"tag": "", "value": "", "display": ""}
        return {"tag": value, "value": value, "display": value}

    def summary_text(self) -> str:
        current_data = self._combo.currentData()
        if current_data is None:
            current_data = self._combo.currentText()
        value = self._normalize_value(current_data)
        return value or "未选择"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def set_current_value(self, value: Optional[str]) -> None:
        normalized = self._normalize_value(value)
        with _block_signals(self._combo):
            index = self._combo.findData(normalized)
            if index != -1:
                self._combo.setCurrentIndex(index)
            else:
                self._combo.setEditText(normalized)
        self.dataChanged.emit()


class UnitAbilityTypeTemplate(BaseTemplateWidget):
    """Editable selector for UnitAbilityType with runtime option updates."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("UnitAbilityType选择框", parent)
        self._label = QLabel("UnitAbilityType：")
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._combo.setMinimumContentsLength(26)
        self._combo.currentTextChanged.connect(self.dataChanged.emit)
        self._options: List[Tuple[str, str]] = []
        self._placeholder = "可输入或选择 UnitAbilityType"
        self._build_layout()
        self.set_options([])

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._label)
        row.addWidget(self._combo, 1)
        layout.addLayout(row)
        layout.addStretch(1)

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def set_options(self, options: Sequence[Tuple[str, str]], *, preserve_text: bool = True) -> None:
        current_value = ""
        if preserve_text:
            current_value = str(self._combo.currentData() or "").strip()
            if not current_value:
                current_value = self._combo.currentText().strip()
                if "|" in current_value:
                    current_value = current_value.split("|", 1)[-1].strip()
        normalized: List[Tuple[str, str]] = []
        seen: set[str] = set()
        for display, value in options:
            clean_value = str(value or "").strip()
            if not clean_value or clean_value in seen:
                continue
            seen.add(clean_value)
            clean_display = str(display or "").strip() or clean_value
            normalized.append((clean_display, clean_value))
        self._options = normalized

        with _block_signals(self._combo):
            self._combo.clear()
            self._combo.addItem(self._placeholder, "")
            for display, value in self._options:
                self._combo.addItem(f"{display} | {value}", value)
            if current_value:
                index = self._combo.findData(current_value)
                if index >= 0:
                    self._combo.setCurrentIndex(index)
                else:
                    self._combo.setEditText(current_value)
            else:
                self._combo.setCurrentIndex(0)
        self.dataChanged.emit()

    def export_data(self) -> Dict[str, object]:
        # Export should always be the raw UnitAbilityType (English Type), not the display text.
        value = str(self._combo.currentData() or "").strip()
        if not value:
            value = self._combo.currentText().strip()
            if "|" in value:
                value = value.split("|", 1)[-1].strip()
        if not value:
            return {"ability_type": "", "value": "", "display": ""}
        matched = next((item for item in self._options if item[1] == value), None)
        display = matched[0] if matched is not None else value
        return {"ability_type": value, "value": value, "display": display}

    def summary_text(self) -> str:
        value = str(self._combo.currentData() or "").strip()
        if not value:
            value = self._combo.currentText().strip()
            if "|" in value:
                value = value.split("|", 1)[-1].strip()
        return value or "未选择"

    def set_current_value(self, value: Optional[str]) -> None:
        target = str(value or "").strip()
        if "|" in target:
            target = target.split("|", 1)[-1].strip()
        with _block_signals(self._combo):
            if not target:
                self._combo.setCurrentIndex(0 if self._combo.count() else -1)
            else:
                index = self._combo.findData(target)
                if index >= 0:
                    self._combo.setCurrentIndex(index)
                else:
                    self._combo.setEditText(target)
        self.dataChanged.emit()


class GreatWorkObjectTypeTemplate(_DatasetComboTemplate):
    """Selector for GreatWorkObjectTypes with localized display names."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("巨作类型选择框", "巨作类型", "great_work_object_type", parent)
        rows = _fetch_great_work_object_type_rows()
        options = sorted((name, object_type) for object_type, name in rows)
        self._populate_options(options)


class FeatureSelectorPassableTemplate(_DatasetComboTemplate):
    """Selects passable non-wonder features for placement rules."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("地貌（可通行）", "地貌", "feature_type", parent)
        rows = _fetch_feature_rows(
            " AND IFNULL(NaturalWonder, 0) = 0 AND IFNULL(Impassable, 0) = 0",
            (),
        )
        options = sorted(
            (
                _localize_tag(name),
                feature_type,
            )
            for feature_type, name, _natural, _impassable in rows
        )
        self._populate_options(options)


class FeatureSelectorAllTemplate(_DatasetComboTemplate):
    """Selects any feature with priority given to common, passable options."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("地貌（全部）", "地貌", "feature_type", parent)
        rows = _fetch_feature_rows("", ())

        def priority(entry: Tuple[str, str, int, int]) -> Tuple[int, str]:
            feature_type, _name, natural, impassable = entry
            score = 0
            if impassable:
                score += 1
            if natural:
                score += 2
            return (score, feature_type)

        sorted_rows = sorted(rows, key=priority)
        options = [
            (_localize_tag(name), feature_type)
            for feature_type, name, _natural, _impassable in sorted_rows
        ]
        self._populate_options(options)


class TerrainSelectorTemplate(_DatasetComboTemplate):
    """Presents a list of terrains sourced from Terrains."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("地形选择框", "地形", "terrain_type", parent)
        rows = _fetch_terrain_rows()
        options = sorted((
            _localize_tag(name),
            terrain_type,
        ) for terrain_type, name in rows)
        self._populate_options(options)


class EraSelectorTemplate(_DatasetComboTemplate):
    """Offers era selection sourced from Eras."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("时代选择框", "时代", "era_type", parent)
        rows = _fetch_era_rows()
        sorted_rows = sorted(
            rows,
            key=lambda entry: (entry[2], entry[0]),
        )
        options = [
            (_localize_tag(name), era_type)
            for era_type, name, _index in sorted_rows
        ]
        self._populate_options(options)


class _EraGroupedSelectionDialog(QDialog):
    """Dialog providing era-colored grouped selections."""

    def __init__(
        self,
        title: str,
        rows: Sequence[Tuple[str, str, str, str, int]],
        column_labels: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self.resize(780, 560)
        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Tuple[str, str, str, str, int] | None = None
        self._column_labels = list(column_labels)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤选项")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, len(self._column_labels))
        self._table.setHorizontalHeaderLabels(self._column_labels)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(160)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")
        self._adjust_column_widths()

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        current_row = self._table.currentRow()
        if 0 <= current_row < len(self._filtered):
            self._selected = self._filtered[current_row]
            self.accept()
        else:
            self.reject()

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        if not key:
            self._filtered = list(self._rows)
        else:
            self._filtered = [
                row
                for row in self._rows
                if key in row[0].lower()
                or key in row[1].lower()
                or key in row[2].lower()
                or key in row[3].lower()
            ]
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._filtered))
        for idx, (era_type, era_label, name, value, order) in enumerate(self._filtered):
            items = [era_label, name, value]
            color = QColor(ERA_GROUP_COLORS[order % len(ERA_GROUP_COLORS)])
            for column, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setBackground(color)
                self._table.setItem(idx, column, item)
        self._adjust_column_widths()

    def selected_row(self) -> Tuple[str, str, str, str, int] | None:
        return self._selected

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._adjust_column_widths()

    def _adjust_column_widths(self) -> None:
        viewport_width = self._table.viewport().width()
        if viewport_width <= 0:
            return
        base = viewport_width / 3.2
        era_width = int(base)
        name_width = int(base * 1.2)
        value_width = max(viewport_width - era_width - name_width, 0)
        self._table.setColumnWidth(0, era_width)
        if self._table.columnCount() > 1:
            self._table.setColumnWidth(1, name_width)
        if self._table.columnCount() > 2:
            self._table.setColumnWidth(2, value_width)


class TechnologySearchSelectorTemplate(BaseTemplateWidget):
    """Technology selector with era-grouped search dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("科技搜索选择框", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("科技：")
        row.addWidget(self._label)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("可直接输入或点击选择科技Type")
        self._line_edit.textChanged.connect(self._on_text_changed)
        row.addWidget(self._line_edit, 1)

        self._open_button = QToolButton()
        self._open_button.setText("…")
        self._open_button.clicked.connect(self._open_dialog)
        row.addWidget(self._open_button)

        layout.addLayout(row)
        layout.addStretch(1)

        self._selected_type: str | None = None
        self._selected_era: str | None = None
        self._tech_rows = _build_era_grouped_entries(_fetch_technology_rows())

    def _normalize(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized.upper()

    def _on_text_changed(self, _text: str) -> None:
        normalized = self._normalize(self._line_edit.text())
        if normalized is not None and self._line_edit.text() != normalized:
            self._line_edit.blockSignals(True)
            self._line_edit.setText(normalized)
            self._line_edit.blockSignals(False)
        self._selected_type = normalized
        self._selected_era = None
        self.dataChanged.emit()

    def _open_dialog(self) -> None:
        dialog = _EraGroupedSelectionDialog(
            "选择科技",
            self._tech_rows,
            ("时代", "科技名称", "TechnologyType"),
            self.window(),
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = dialog.selected_row()
            if row is not None:
                era_type, _era_label, name, tech_type, _order = row
                self._selected_type = self._normalize(tech_type)
                self._selected_era = era_type
                self._line_edit.blockSignals(True)
                self._line_edit.setText(self._selected_type or "")
                self._line_edit.blockSignals(False)
                self.dataChanged.emit()

    def export_data(self) -> Dict[str, object]:
        normalized = self._normalize(self._selected_type) or self._normalize(self._line_edit.text())
        self._selected_type = normalized
        return {
            "technology_type": normalized,
            "era_type": self._selected_era,
            "display": normalized or "",
        }

    def set_current_value(self, value: Optional[str]) -> None:
        normalized = self._normalize(value)
        self._selected_type = normalized
        self._selected_era = None
        self._line_edit.blockSignals(True)
        self._line_edit.setText(normalized or "")
        self._line_edit.blockSignals(False)
        self.dataChanged.emit()

    def summary_text(self) -> str:
        return self._line_edit.text().strip() or "未选择"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class CivicSearchSelectorTemplate(BaseTemplateWidget):
    """Civic selector with era-grouped search dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("市政搜索选择框", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("市政：")
        row.addWidget(self._label)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("可直接输入或点击选择市政Type")
        self._line_edit.textChanged.connect(self._on_text_changed)
        row.addWidget(self._line_edit, 1)

        self._open_button = QToolButton()
        self._open_button.setText("…")
        self._open_button.clicked.connect(self._open_dialog)
        row.addWidget(self._open_button)

        layout.addLayout(row)
        layout.addStretch(1)

        self._selected_type: str | None = None
        self._selected_era: str | None = None
        self._civic_rows = _build_era_grouped_entries(_fetch_civic_rows())

    def _normalize(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized.upper()

    def _on_text_changed(self, _text: str) -> None:
        normalized = self._normalize(self._line_edit.text())
        if normalized is not None and self._line_edit.text() != normalized:
            self._line_edit.blockSignals(True)
            self._line_edit.setText(normalized)
            self._line_edit.blockSignals(False)
        self._selected_type = normalized
        self._selected_era = None
        self.dataChanged.emit()

    def _open_dialog(self) -> None:
        dialog = _EraGroupedSelectionDialog(
            "选择市政",
            self._civic_rows,
            ("时代", "市政名称", "CivicType"),
            self.window(),
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = dialog.selected_row()
            if row is not None:
                era_type, _era_label, name, civic_type, _order = row
                self._selected_type = self._normalize(civic_type)
                self._selected_era = era_type
                self._line_edit.blockSignals(True)
                self._line_edit.setText(self._selected_type or "")
                self._line_edit.blockSignals(False)
                self.dataChanged.emit()

    def export_data(self) -> Dict[str, object]:
        normalized = self._normalize(self._selected_type) or self._normalize(self._line_edit.text())
        self._selected_type = normalized
        return {
            "civic_type": normalized,
            "era_type": self._selected_era,
            "display": normalized or "",
        }

    def set_current_value(self, value: Optional[str]) -> None:
        normalized = self._normalize(value)
        self._selected_type = normalized
        self._selected_era = None
        self._line_edit.blockSignals(True)
        self._line_edit.setText(normalized or "")
        self._line_edit.blockSignals(False)
        self.dataChanged.emit()

    def summary_text(self) -> str:
        return self._line_edit.text().strip() or "未选择"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class PlunderTypeSelectorTemplate(_DatasetComboTemplate):
    """Dropdown for plunder outcomes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("掠夺类型选择框", "掠夺类型", "plunder_type", parent)
        self._populate_options(PLUNDER_OPTIONS)


class CostProgressionTemplate(_DatasetComboTemplate):
    """Dropdown for cost progression models."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("成本递增模型选择框", "成本模型", "cost_progression_type", parent)
        self._populate_options(COST_PROGRESSION_OPTIONS)
        default = "NO_COST_PROGRESSION"
        for index, (_label, value) in enumerate(self._options):
            if value == default:
                self._combo.setCurrentIndex(index + 1)
                break


class DomainSelectorTemplate(_DatasetComboTemplate):
    """Dropdown for gameplay domains."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("领域选择框", "领域", "domain_type", parent)
        self._populate_options(DOMAIN_OPTIONS)


class FormationClassSelectorTemplate(_DatasetComboTemplate):
    """Dropdown for unit formation classes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("编队类型选择框", "编队类型", "formation_class", parent)
        self._populate_options(FORMATION_CLASS_OPTIONS)


class UnitPromotionClassSelectorTemplate(_DatasetComboTemplate):
    """Dropdown sourcing UnitPromotionClasses."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("单位晋升类型选择框", "晋升类型", "promotion_class", parent)
        rows = _fetch_promotion_class_rows()
        class_to_name: Dict[str, str] = {}
        for class_type, name_tag in rows:
            class_type_text = str(class_type or "").strip()
            if not class_type_text:
                continue
            localized = _localize_tag(name_tag)
            display_name = (localized or str(name_tag or "").strip() or class_type_text).strip()
            class_to_name[class_type_text] = display_name
        options = sorted(
            [(display_name, class_type) for class_type, display_name in class_to_name.items()],
            key=lambda item: item[0],
        )
        self._populate_options(options)


class YieldSelectorTemplate(_DatasetComboTemplate):
    """Dropdown for yield types."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("产出选择框", "产出", "yield_type", parent)
        self._populate_options(YIELD_OPTIONS)


class GreatPersonClassSelectorTemplate(_DatasetComboTemplate):
    """Dropdown sourcing timeline-available great person classes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("伟人类型选择框", "伟人类型", "great_person_class", parent)
        rows = _fetch_great_person_class_rows()
        db_display_map: Dict[str, str] = {}
        for class_type, name in rows:
            key = str(class_type or "").strip()
            if not key:
                continue
            localized = _localize_tag(str(name or ""))
            display = localized if localized and localized != "未知" else key
            db_display_map[key] = display

        workspace_entries = _workspace_entries("伟人")
        workspace_order: List[str] = []
        workspace_name_map: Dict[str, str] = {}
        for entry in workspace_entries:
            t = _workspace_entry_type(entry)
            if not t or t in workspace_name_map:
                continue
            workspace_order.append(t)
            workspace_name_map[t] = _workspace_entry_display_name(entry)

        db_types = set(db_display_map.keys())
        workspace_new = [t for t in workspace_order if t not in db_types]
        workspace_imported = [t for t in workspace_order if t in db_types]

        remaining_db = sorted(
            [(display, t) for t, display in db_display_map.items() if t not in set(workspace_imported)],
            key=lambda item: item[0],
        )

        colored: List[Tuple[str, str, str]] = []
        for t in workspace_new:
            display = workspace_name_map.get(t) or t
            colored.append((display, t, "workspace_new"))
        for t in workspace_imported:
            colored.append((db_display_map.get(t) or t, t, "workspace_imported"))
        for display, t in remaining_db:
            colored.append((display, t, "db"))

        self._populate_colored_options(colored)

    def _populate_colored_options(self, options: Sequence[Tuple[str, str, str]]) -> None:
        self._combo.clear()
        self._options = [(display, value) for display, value, _origin in options]
        self._combo.addItem(self._placeholder, None)
        if not self._options:
            self._combo.setEnabled(False)
            return

        self._combo.setEnabled(True)
        for display, value, origin in options:
            self._combo.addItem(f"{display} | {value}", value)
            index = self._combo.count() - 1
            if origin == "workspace_new":
                self._combo.setItemData(
                    index,
                    QBrush(QColor(WORKSPACE_GREATPERSON_NEW_BG)),
                    Qt.ItemDataRole.BackgroundRole,
                )
            elif origin == "workspace_imported":
                self._combo.setItemData(
                    index,
                    QBrush(QColor(WORKSPACE_GREATPERSON_IMPORTED_BG)),
                    Qt.ItemDataRole.BackgroundRole,
                )


class GovernmentSlotSelectorTemplate(_DatasetComboTemplate):
    """Dropdown sourcing GovernmentSlots.GovernmentSlotType."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("政策槽位选择框", "政策槽位", "government_slot_type", parent)
        rows = _fetch_government_slot_rows()
        options = [
            (display, slot_type)
            for slot_type, display in rows
        ]
        self._populate_options(options)


class GovernmentSelectorTemplate(_DatasetComboTemplate):
    """Dropdown sourcing Governments.GovernmentType."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("政体选择框", "政体", "government_type", parent)
        rows = _fetch_government_rows()
        options = [
            (display, government_type)
            for government_type, display in rows
        ]
        self._populate_options(options)


class BeliefClassSelectorTemplate(BaseTemplateWidget):
    """BeliefClassType 专用单选勾选组（3 行布局）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("信仰类别勾选组", parent)
        self._buttons: list[QCheckBox] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._label = QLabel("信仰类别：")
        root.addWidget(self._label)

        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        rows = _fetch_belief_class_rows()
        for idx, (belief_class_type, display_name) in enumerate(rows):
            checkbox = QCheckBox(display_name)
            checkbox.setToolTip(belief_class_type)
            self._button_group.addButton(checkbox, idx)
            checkbox.stateChanged.connect(lambda _v: self.dataChanged.emit())
            row = idx % 3
            col = idx // 3
            grid.addWidget(checkbox, row, col)
            self._buttons.append(checkbox)

        if self._buttons:
            self._buttons[0].setChecked(True)

        root.addWidget(holder)
        root.addStretch(1)

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def export_data(self) -> Dict[str, object]:
        for checkbox in self._buttons:
            if checkbox.isChecked():
                belief_class_type = checkbox.toolTip().strip()
                return {
                    "belief_class_type": belief_class_type,
                    "value": belief_class_type,
                    "display": checkbox.text(),
                }
        return {"belief_class_type": None, "value": None, "display": ""}

    def summary_text(self) -> str:
        for checkbox in self._buttons:
            if checkbox.isChecked():
                return checkbox.text()
        return "未选择"

    def set_current_value(self, value: Optional[str]) -> None:
        target = str(value or "").strip().upper()
        matched = False
        for checkbox in self._buttons:
            belief_class_type = checkbox.toolTip().strip().upper()
            should_check = bool(target) and belief_class_type == target
            checkbox.blockSignals(True)
            checkbox.setChecked(should_check)
            checkbox.blockSignals(False)
            if should_check:
                matched = True
        if not matched and self._buttons:
            self._buttons[0].blockSignals(True)
            self._buttons[0].setChecked(True)
            self._buttons[0].blockSignals(False)
        self.dataChanged.emit()


class AdvisorTypeSelectorTemplate(_DatasetComboTemplate):
    """Dropdown providing advisor types."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("顾问类型选择框", "顾问类型", "advisor_type", parent)
        options = [
            (label, value)
            for value, label in ADVISOR_TYPE_OPTIONS
        ]
        self._populate_options(options)
        default_value = "ADVISOR_GENERIC"
        for index, (_label, value) in enumerate(self._options):
            if value == default_value:
                self._combo.setCurrentIndex(index + 1)
                break

    def _current_option(self) -> Tuple[str, str] | None:
        option = self._option_for_index(self._combo.currentIndex())
        if option is None:
            return None
        return option

    def export_data(self) -> Dict[str, object]:
        option = self._current_option()
        if option is None:
            return {"advisor_type": None, "display": "", "value": None}
        _label, value = option
        return {"advisor_type": value, "display": value, "value": value}

    def summary_text(self) -> str:
        option = self._current_option()
        if option is None:
            return "未选择"
        _label, value = option
        return value or "未选择"


class ResourceClassSelectorTemplate(_DatasetComboTemplate):
    """Dropdown for resource class categories."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("资源类型选择框", "资源类型", "resource_class", parent)
        options = [
            (label, value)
            for value, label in RESOURCE_CLASS_OPTIONS
        ]
        self._populate_options(options)
        with _block_signals(self._combo):
            self._combo.setCurrentIndex(0)

    def _current_option(self) -> Tuple[str, str] | None:
        option = self._option_for_index(self._combo.currentIndex())
        if option is None:
            return None
        return option

    def export_data(self) -> Dict[str, object]:
        option = self._current_option()
        if option is None:
            return {"resource_class": None, "display": "", "value": None, "name": ""}
        _label, value = option
        return {"resource_class": value, "display": value, "value": value, "name": value}

    def summary_text(self) -> str:
        option = self._current_option()
        if option is None:
            return "未选择"
        _label, value = option
        return value or "未选择"


class _ResourceSearchDialog(QDialog):
    """Dialog presenting searchable resources in a table."""

    def __init__(self, rows: Sequence[Tuple[str, str, str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择资源")
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self.resize(780, 560)
        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Tuple[str, str, str, str] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤资源")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["资源名字", "ResourceType", "资源类别"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(160)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        self._confirm_btn = QPushButton("确定")
        self._confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(self._confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")
        self._adjust_column_widths()

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        current_row = self._table.currentRow()
        if 0 <= current_row < len(self._filtered):
            self._selected = self._filtered[current_row]
            self.accept()
        else:
            self.reject()

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        if not key:
            self._filtered = list(self._rows)
        else:
            self._filtered = [
                row
                for row in self._rows
                if key in row[0].lower()
                or key in row[1].lower()
                or key in row[2].lower()
                or key in row[3].lower()
            ]
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._filtered))
        for idx, (name, res_type, class_key, class_label) in enumerate(self._filtered):
            self._table.setItem(idx, 0, QTableWidgetItem(name))
            self._table.setItem(idx, 1, QTableWidgetItem(res_type))
            class_item = QTableWidgetItem(class_label or class_key or "其他")
            self._table.setItem(idx, 2, class_item)
        self._adjust_column_widths()

    def selected_row(self) -> Tuple[str, str, str, str] | None:
        return self._selected

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._adjust_column_widths()

    def _adjust_column_widths(self) -> None:
        viewport_width = self._table.viewport().width()
        if viewport_width <= 0:
            return
        base = viewport_width / 3.2
        name_width = int(base)
        type_width = int(base * 1.2)
        class_width = max(viewport_width - name_width - type_width, 0)
        self._table.setColumnWidth(0, name_width)
        self._table.setColumnWidth(1, type_width)
        self._table.setColumnWidth(2, class_width)


class ResourceSearchSelectorTemplate(BaseTemplateWidget):
    """Search-enabled resource selector suitable for large data sets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("资源搜索选择框", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel("资源：")
        row.addWidget(self._label)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("可直接输入或点击选择")
        self._line_edit.textChanged.connect(self._on_text_changed)
        row.addWidget(self._line_edit, 1)

        self._open_button = QToolButton()
        self._open_button.setText("…")
        self._open_button.clicked.connect(self._open_dialog)
        row.addWidget(self._open_button)

        layout.addLayout(row)
        layout.addStretch(1)

        self._selected_type: str | None = None
        resource_rows = _fetch_resource_rows()
        sorted_rows = sorted(
            (
                _localize_tag(name),
                res_type,
                class_key,
                RESOURCE_CLASS_LABELS.get(class_key, "其他"),
            )
            for res_type, name, class_key in resource_rows
        )
        sorted_rows.sort(
            key=lambda entry: (
                RESOURCE_CLASS_ORDER.get(entry[2], 3),
                entry[0],
            )
        )
        self._resource_rows = sorted_rows

    @staticmethod
    def _normalize_resource_type(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return normalized.upper()

    def _on_text_changed(self, _text: str) -> None:
        normalized = self._normalize_resource_type(self._line_edit.text())
        if normalized is None:
            self._selected_type = None
        else:
            if self._line_edit.text() != normalized:
                self._line_edit.blockSignals(True)
                self._line_edit.setText(normalized)
                self._line_edit.blockSignals(False)
            self._selected_type = normalized
        self.dataChanged.emit()

    def _open_dialog(self) -> None:
        dialog = _ResourceSearchDialog(self._resource_rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = dialog.selected_row()
            if row is not None:
                _name, res_type, _class_key, _class_label = row
                normalized_type = self._normalize_resource_type(res_type)
                self._selected_type = normalized_type
                self._line_edit.blockSignals(True)
                self._line_edit.setText(normalized_type or "")
                self._line_edit.blockSignals(False)
                self.dataChanged.emit()

    def export_data(self) -> Dict[str, object]:
        normalized = self._normalize_resource_type(self._selected_type)
        if normalized is None:
            normalized = self._normalize_resource_type(self._line_edit.text()) or ""
        self._selected_type = normalized or None
        return {"resource_type": self._selected_type, "display": normalized}

    def set_current_value(self, value: str | None) -> None:
        if value is None:
            self._selected_type = None
            self._line_edit.clear()
        else:
            normalized = self._normalize_resource_type(str(value))
            self._selected_type = normalized
            self._line_edit.blockSignals(True)
            self._line_edit.setText(normalized or "")
            self._line_edit.blockSignals(False)

    def summary_text(self) -> str:
        if self._selected_type:
            return self._selected_type
        normalized = self._normalize_resource_type(self._line_edit.text())
        return normalized or "未选择"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class _SimpleStringSearchDialog(QDialog):
    """通用字符串搜索弹窗（单列列表）。"""

    def __init__(
        self,
        rows: Sequence[str],
        *,
        title: str,
        placeholder: str,
        column_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(680, 500)
        self.resize(740, 560)
        self._rows = sorted({str(item).strip() for item in rows if str(item).strip()})
        self._filtered = list(self._rows)
        self._selected: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_row.addWidget(QLabel("搜索："))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(placeholder)
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, 1)
        self._table.setHorizontalHeaderLabels([column_label])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        if not key:
            self._filtered = list(self._rows)
        else:
            self._filtered = [item for item in self._rows if key in item.lower()]
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._filtered))
        for idx, value in enumerate(self._filtered):
            item = QTableWidgetItem(value)
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(idx, 0, item)

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def selected_value(self) -> str | None:
        return self._selected


class MomentTextureSearchTemplate(BaseTemplateWidget):
    """历史时刻数据库 Texture 搜索模板：可输入，也可弹窗搜索。"""

    def __init__(self, parent: QWidget | None = None, *, compact: bool = False) -> None:
        super().__init__("历史时刻Texture搜索选择框", parent)
        self._compact = bool(compact)
        self._label = QLabel("数据库Texture：")
        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("可输入或点击搜索数据库Texture")
        self._line_edit.textChanged.connect(self._on_text_changed)
        self._open_button = QToolButton()
        self._open_button.setText("…")
        self._open_button.clicked.connect(self._open_dialog)
        self._options: list[str] = []
        self._selected_value: str | None = None
        self._build_layout()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        if self._compact:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        else:
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6 if self._compact else 8)
        if not self._compact:
            row.addWidget(self._label)
        row.addWidget(self._line_edit, 1)
        row.addWidget(self._open_button)
        layout.addLayout(row)
        if not self._compact:
            layout.addStretch(1)

    @staticmethod
    def _normalize(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def set_options(self, options: Sequence[str], *, preserve_value: bool = True) -> None:
        current = self.current_value() if preserve_value else None
        self._options = sorted({str(item).strip() for item in options if str(item).strip()})
        if preserve_value:
            self.set_current_value(current)

    def _on_text_changed(self, _text: str) -> None:
        self._selected_value = self._normalize(self._line_edit.text())
        self.dataChanged.emit()

    def _open_dialog(self) -> None:
        dialog = _SimpleStringSearchDialog(
            self._options,
            title="选择数据库 Texture",
            placeholder="输入关键字过滤 Texture",
            column_label="Texture",
            parent=self.window(),
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected_value()
            if selected is not None:
                normalized = self._normalize(selected)
                self._selected_value = normalized
                self._line_edit.blockSignals(True)
                self._line_edit.setText(normalized or "")
                self._line_edit.blockSignals(False)
                self.dataChanged.emit()

    def current_value(self) -> str | None:
        return self._normalize(self._selected_value) or self._normalize(self._line_edit.text())

    def export_data(self) -> Dict[str, object]:
        value = self.current_value()
        return {
            "value": value or "",
            "display": value or "",
            "name": value or "",
            "db_texture": value or "",
        }

    def summary_text(self) -> str:
        return self.current_value() or "未选择"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)

    def set_current_value(self, value: Optional[str]) -> None:
        normalized = self._normalize(value)
        self._selected_value = normalized
        self._line_edit.blockSignals(True)
        self._line_edit.setText(normalized or "")
        self._line_edit.blockSignals(False)
        self.dataChanged.emit()


class _TypeSearchTemplate(BaseTemplateWidget):
    """Base class for selectors that yield a Type string."""

    def __init__(
        self,
        display_name: str,
        label_text: str,
        placeholder: str,
        type_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(display_name, parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._label = QLabel(f"{label_text}：")
        row.addWidget(self._label)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(placeholder)
        self._line_edit.textChanged.connect(self._on_text_changed)
        row.addWidget(self._line_edit, 1)

        self._open_button = QToolButton()
        self._open_button.setText("…")
        self._open_button.clicked.connect(self._open_dialog)
        row.addWidget(self._open_button)

        layout.addLayout(row)
        layout.addStretch(1)

        self._selected_type: str | None = None
        self._type_key = type_key

    def _normalize(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized.upper()

    def _on_text_changed(self, _text: str) -> None:
        normalized = self._normalize(self._line_edit.text())
        if normalized is None:
            self._selected_type = None
        else:
            if self._line_edit.text() != normalized:
                self._line_edit.blockSignals(True)
                self._line_edit.setText(normalized)
                self._line_edit.blockSignals(False)
            self._selected_type = normalized
        self.dataChanged.emit()

    def _select_from_dialog(self) -> str | None:
        raise NotImplementedError

    def _open_dialog(self) -> None:
        selected = self._select_from_dialog()
        if not selected:
            return
        normalized = self._normalize(selected)
        self._selected_type = normalized
        self._line_edit.blockSignals(True)
        self._line_edit.setText(normalized or "")
        self._line_edit.blockSignals(False)
        self.dataChanged.emit()

    def export_data(self) -> Dict[str, object]:
        normalized = self._normalize(self._selected_type) or self._normalize(self._line_edit.text())
        self._selected_type = normalized
        display_value = normalized or ""
        return {self._type_key: normalized, "display": display_value}

    def set_current_value(self, value: Optional[str]) -> None:
        normalized = self._normalize(value)
        self._selected_type = normalized
        self._line_edit.blockSignals(True)
        self._line_edit.setText(normalized or "")
        self._line_edit.blockSignals(False)
        self.dataChanged.emit()

    def summary_text(self) -> str:
        normalized = self._normalize(self._selected_type) or self._normalize(self._line_edit.text())
        return normalized or "未选择"

    def set_label_text(self, text: str) -> None:
        self._label.setText(text)


class ResourceStrategicTemplate(_DatasetComboTemplate):
    """Provides a compact selector limited to strategic resources."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("战略资源选择框", "战略资源", "resource_type", parent)
        rows = [
            (res_type, name, class_key)
            for res_type, name, class_key in _fetch_resource_rows()
            if class_key == "RESOURCECLASS_STRATEGIC"
        ]
        options = sorted(
            (
                _localize_tag(name),
                res_type,
            )
            for res_type, name, _class in rows
        )
        self._populate_options(options)

    def _current_option(self) -> Tuple[str, str] | None:
        return self._option_for_index(self._combo.currentIndex())

    def export_data(self) -> Dict[str, object]:
        option = self._current_option()
        if option is None:
            return {"resource_type": "", "display": ""}
        _label, value = option
        return {"resource_type": value, "display": value}

    def summary_text(self) -> str:
        option = self._current_option()
        if option is None:
            return "未选择"
        _label, value = option
        return value or "未选择"


class _DistrictSearchDialog(QDialog):
    """Dialog presenting districts with parent-child ordering."""

    def __init__(self, rows: Sequence[Dict[str, object]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择区域")
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self.resize(780, 560)

        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Dict[str, object] | None = None
        self._ignore_unknown = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤区域")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)
        self._ignore_unknown_toggle = QCheckBox("忽视未知")
        self._ignore_unknown_toggle.stateChanged.connect(self._handle_ignore_unknown_toggle)
        toggle_row.addWidget(self._ignore_unknown_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["区域", "DistrictType"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _emit_rows(self, rows: Sequence[Dict[str, object]]) -> None:
        self._table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            name = str(entry.get("name") or "")
            indent = int(entry.get("indent") or 0)
            indent_prefix = "    " * max(indent, 0)
            type_name = str(entry.get("type") or "")

            name_item = QTableWidgetItem(f"{indent_prefix}{name}")
            type_item = QTableWidgetItem(type_name)
            if bool(entry.get("_workspace_pin")):
                color = QColor(WORKSPACE_PIN_BG)
            else:
                color = QColor(DISTRICT_PARENT_COLOR if indent == 0 else DISTRICT_CHILD_COLOR)
            for item in (name_item, type_item):
                item.setData(Qt.ItemDataRole.UserRole, entry)
                item.setBackground(color)
            self._table.setItem(row_index, 0, name_item)
            self._table.setItem(row_index, 1, type_item)

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        filtered: List[Dict[str, object]] = []
        for entry in self._rows:
            if self._ignore_unknown and str(entry.get("name") or "").strip() == "未知":
                continue
            type_name = str(entry.get("type") or "").lower()
            name = str(entry.get("name") or "").lower()
            if not key or key in type_name or key in name:
                filtered.append(entry)
        self._filtered = filtered
        self._emit_rows(self._filtered)

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        current_row = self._table.currentRow()
        if 0 <= current_row < len(self._filtered):
            self._selected = self._filtered[current_row]
            self.accept()
        else:
            self.reject()

    def _handle_ignore_unknown_toggle(self, _state: int) -> None:
        self._ignore_unknown = self._ignore_unknown_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def selected_type(self) -> str | None:
        if self._selected is None:
            return None
        return str(self._selected.get("type") or "")


class DistrictSearchSelectorTemplate(_TypeSearchTemplate):
    """District selector with grouped civilization uniques."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "区域搜索选择框",
            "区域",
            "可直接输入或点击选择区域Type",
            "district_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = _build_district_hierarchy()
        if not rows:
            return None
        dialog = _DistrictSearchDialog(rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class DistrictSearchNoTraitSelectorTemplate(_TypeSearchTemplate):
    """District selector limited to entries without traits."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "区域搜索选择框（无Trait）",
            "区域",
            "可直接输入或点击选择区域Type",
            "district_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = [
            entry
            for entry in _build_district_hierarchy()
            if not (str(entry.get("trait") or "").strip())
        ]
        if not rows:
            return None
        dialog = _DistrictSearchDialog(rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class _BuildingSearchDialog(QDialog):
    """Dialog presenting building options sorted by production cost."""

    def __init__(self, rows: Sequence[Dict[str, object]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择建筑")
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self.resize(780, 560)

        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Dict[str, object] | None = None
        self._show_cost_one = False
        self._ignore_unknown = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤建筑")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)
        self._show_cost_toggle = QCheckBox("显示成本为1的建筑")
        self._show_cost_toggle.stateChanged.connect(self._handle_cost_toggle)
        toggle_row.addWidget(self._show_cost_toggle)
        self._ignore_unknown_toggle = QCheckBox("忽视未知")
        self._ignore_unknown_toggle.stateChanged.connect(self._handle_ignore_unknown_toggle)
        toggle_row.addWidget(self._ignore_unknown_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["建筑", "BuildingType"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _emit_rows(self, rows: Sequence[Dict[str, object]]) -> None:
        self._table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            name_item = QTableWidgetItem(str(entry.get("name") or ""))
            type_item = QTableWidgetItem(str(entry.get("type") or ""))
            if bool(entry.get("_workspace_pin")):
                color = QColor(WORKSPACE_PIN_BG)
                for item in (name_item, type_item):
                    item.setBackground(color)
            for item in (name_item, type_item):
                item.setData(Qt.ItemDataRole.UserRole, entry)
            self._table.setItem(row_index, 0, name_item)
            self._table.setItem(row_index, 1, type_item)

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        filtered: List[Dict[str, object]] = []
        for entry in self._rows:
            is_workspace_pin = bool(entry.get("_workspace_pin"))
            if not self._show_cost_one and int(entry.get("cost") or 0) == 1 and not is_workspace_pin:
                continue
            if self._ignore_unknown and str(entry.get("name") or "").strip() == "未知":
                continue
            type_name = str(entry.get("type") or "").lower()
            name = str(entry.get("name") or "").lower()
            if not key or key in type_name or key in name:
                filtered.append(entry)
        self._filtered = filtered
        self._emit_rows(self._filtered)

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        current_row = self._table.currentRow()
        if 0 <= current_row < len(self._filtered):
            self._selected = self._filtered[current_row]
            self.accept()
        else:
            self.reject()

    def _handle_cost_toggle(self, _state: int) -> None:
        self._show_cost_one = self._show_cost_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def _handle_ignore_unknown_toggle(self, _state: int) -> None:
        self._ignore_unknown = self._ignore_unknown_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def selected_type(self) -> str | None:
        if self._selected is None:
            return None
        return str(self._selected.get("type") or "")


class _BuildingSearchByDistrictDialog(QDialog):
    """Dialog presenting buildings grouped by PrereqDistrict."""

    def __init__(
        self,
        rows: Sequence[Dict[str, object]],
        parent: QWidget | None = None,
        *,
        include_wonders: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择建筑")
        self.setModal(True)
        self.setMinimumSize(760, 560)
        self.resize(820, 600)

        self._rows = list(rows)
        self._filtered = list(rows)
        self._visible_entries: List[Dict[str, object]] = []
        self._row_entry_map: List[Dict[str, object] | None] = []
        self._group_labels_in_view: List[str] = []
        self._collapsed_groups: set[str] = set()
        self._selected: Dict[str, object] | None = None
        self._show_cost_one = False
        self._ignore_unknown = False
        self._include_wonders = include_wonders
        self._expand_all_default = not include_wonders

        group_keys = self._group_key_sequence(self._rows)
        self._group_colors = _generate_group_colors(group_keys)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤建筑")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)
        self._show_cost_toggle = QCheckBox("显示成本为1的建筑")
        self._show_cost_toggle.stateChanged.connect(self._handle_cost_toggle)
        toggle_row.addWidget(self._show_cost_toggle)
        self._ignore_unknown_toggle = QCheckBox("忽视未知")
        self._ignore_unknown_toggle.stateChanged.connect(self._handle_ignore_unknown_toggle)
        toggle_row.addWidget(self._ignore_unknown_toggle)
        self._expand_all_toggle = QCheckBox("展开/折叠")
        self._expand_all_toggle.setChecked(self._expand_all_default)
        self._expand_all_toggle.stateChanged.connect(self._apply_expand_state)
        toggle_row.addWidget(self._expand_all_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["分组", "建筑", "BuildingType"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellClicked.connect(self._handle_cell_clicked)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _group_key_sequence(self, rows: Sequence[Dict[str, object]]) -> List[str]:
        labels = {self._group_label_for_entry(entry) for entry in rows}
        ordered = sorted([label for label in labels if label not in {"无区域", "奇观", WORKSPACE_PIN_GROUP_LABEL}])
        if "无区域" in labels:
            ordered.insert(0, "无区域")
        if "奇观" in labels:
            ordered.insert(1 if ordered and ordered[0] == "无区域" else 0, "奇观")
        if WORKSPACE_PIN_GROUP_LABEL in labels:
            ordered.insert(0, WORKSPACE_PIN_GROUP_LABEL)
        return ordered

    def _group_label_for_entry(self, entry: Dict[str, object]) -> str:
        if bool(entry.get("_workspace_pin")):
            return WORKSPACE_PIN_GROUP_LABEL
        if self._include_wonders and bool(entry.get("is_wonder")):
            return "奇观"
        return _building_group_label(entry)

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        filtered: List[Dict[str, object]] = []
        for entry in self._rows:
            is_workspace_pin = bool(entry.get("_workspace_pin"))
            if not self._show_cost_one and int(entry.get("cost") or 0) == 1 and not is_workspace_pin:
                continue
            if self._ignore_unknown and str(entry.get("name") or "").strip() == "未知":
                continue
            type_name = str(entry.get("type") or "").lower()
            name = str(entry.get("name") or "").lower()
            if not key or key in type_name or key in name:
                filtered.append(entry)
        self._filtered = filtered
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(0)
        self._visible_entries = []
        self._row_entry_map = []
        groups: Dict[str, List[Dict[str, object]]] = {}
        for entry in self._filtered:
            label = self._group_label_for_entry(entry)
            groups.setdefault(label, []).append(entry)

        ordered_labels = self._group_key_sequence(self._filtered)
        self._group_labels_in_view = ordered_labels
        self._collapsed_groups = {label for label in self._collapsed_groups if label in set(ordered_labels)}
        for label in ordered_labels:
            entries = groups.get(label, [])
            if not entries:
                continue
            color = _building_group_color(label, self._group_colors)
            header_row = self._table.rowCount()
            self._table.insertRow(header_row)
            expanded = label not in self._collapsed_groups
            group_item = QTableWidgetItem(("▼ " if expanded else "▶ ") + label)
            name_header = QTableWidgetItem("")
            type_header = QTableWidgetItem("")
            group_item.setData(Qt.ItemDataRole.UserRole, {"kind": "group", "label": label})
            for item in (group_item, name_header, type_header):
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setBackground(QBrush((color.darker(108) if color is not None else QColor("#bfdbfe"))))
                item.setForeground(QBrush(QColor("#0f172a")))
            self._table.setItem(header_row, 0, group_item)
            self._table.setItem(header_row, 1, name_header)
            self._table.setItem(header_row, 2, type_header)
            self._row_entry_map.append(None)

            if not expanded:
                continue

            for entry in entries:
                row_idx = self._table.rowCount()
                self._table.insertRow(row_idx)
                group_item = QTableWidgetItem(label)
                name_item = QTableWidgetItem(str(entry.get("name") or ""))
                type_item = QTableWidgetItem(str(entry.get("type") or ""))
                shade = color.lighter(108) if color is not None else QColor("#dbeafe")
                for item in (group_item, name_item, type_item):
                    item.setData(Qt.ItemDataRole.UserRole, entry)
                    item.setBackground(QBrush(shade))
                    item.setForeground(QBrush(QColor("#111827")))
                self._table.setItem(row_idx, 0, group_item)
                self._table.setItem(row_idx, 1, name_item)
                self._table.setItem(row_idx, 2, type_item)
                self._visible_entries.append(entry)
                self._row_entry_map.append(entry)

    def _apply_expand_state(self, _state: int | None = None) -> None:
        if self._expand_all_toggle.isChecked():
            self._collapsed_groups.clear()
        else:
            self._collapsed_groups = set(self._group_labels_in_view)
        self._populate_table()

    def _handle_cell_clicked(self, row: int, _column: int) -> None:
        if row < 0 or row >= self._table.rowCount():
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict) or payload.get("kind") != "group":
            return
        label = str(payload.get("label") or "")
        if not label:
            return
        if label in self._collapsed_groups:
            self._collapsed_groups.remove(label)
        else:
            self._collapsed_groups.add(label)
        if self._group_labels_in_view and len(self._collapsed_groups) == len(self._group_labels_in_view):
            self._expand_all_toggle.blockSignals(True)
            self._expand_all_toggle.setChecked(False)
            self._expand_all_toggle.blockSignals(False)
        elif not self._collapsed_groups:
            self._expand_all_toggle.blockSignals(True)
            self._expand_all_toggle.setChecked(True)
            self._expand_all_toggle.blockSignals(False)
        self._populate_table()

    def _handle_double_click(self, row: int, _column: int) -> None:
        if row < 0 or row >= self._table.rowCount():
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict) and payload.get("kind") == "group":
            self._handle_cell_clicked(row, _column)
            return
        if 0 <= row < len(self._row_entry_map):
            entry = self._row_entry_map[row]
            if isinstance(entry, dict):
                self._selected = entry
                self.accept()

    def _handle_confirm(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._row_entry_map):
            self.reject()
            return
        entry = self._row_entry_map[row]
        if not isinstance(entry, dict):
            self.reject()
            return
        self._selected = entry
        self.accept()

    def _handle_cost_toggle(self, _state: int) -> None:
        self._show_cost_one = self._show_cost_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def _handle_ignore_unknown_toggle(self, _state: int) -> None:
        self._ignore_unknown = self._ignore_unknown_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def selected_type(self) -> str | None:
        if self._selected is None:
            return None
        return str(self._selected.get("type") or "")


class _BuildingSearchSelectorBase(_TypeSearchTemplate):
    """Shared base for building selectors."""

    def __init__(
        self,
        display_name: str,
        include_wonders: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            display_name,
            "建筑",
            "可直接输入或点击选择建筑Type",
            "building_type",
            parent,
        )
        self._include_wonders = include_wonders

    def _select_from_dialog(self) -> str | None:
        rows = _build_building_entries(include_wonders=self._include_wonders)
        if not rows:
            return None
        dialog = _BuildingSearchByDistrictDialog(
            rows,
            self.window(),
            include_wonders=self._include_wonders,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class BuildingSearchSelectorTemplate(_BuildingSearchSelectorBase):
    """Building selector excluding wonders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("建筑搜索选择框", include_wonders=False, parent=parent)


class BuildingSearchAllSelectorTemplate(_BuildingSearchSelectorBase):
    """Building selector including wonders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("建筑搜索选择框（含奇观）", include_wonders=True, parent=parent)


class BuildingSearchNoTraitSelectorTemplate(_TypeSearchTemplate):
    """Building selector excluding wonders and trait-restricted entries."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "建筑搜索选择框（无Trait无奇观）",
            "建筑",
            "可直接输入或点击选择建筑Type",
            "building_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = [
            entry
            for entry in _build_building_entries(include_wonders=False)
            if not (str(entry.get("trait") or "").strip())
        ]
        if not rows:
            return None
        dialog = _BuildingSearchByDistrictDialog(rows, self.window(), include_wonders=False)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class _UnitSearchDialog(QDialog):
    """Dialog presenting units grouped by promotion class."""

    def __init__(self, rows: Sequence[Dict[str, object]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择单位")
        self.setModal(True)
        self.setMinimumSize(760, 560)
        self.resize(820, 600)

        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Dict[str, object] | None = None
        self._show_cost_one = False
        self._ignore_unknown = False

        class_sequence: List[str] = []
        for entry in self._rows:
            cls = str(entry.get("promotion_class") or "")
            if cls not in class_sequence:
                class_sequence.append(cls)
        self._class_colors = {
            cls: UNIT_CLASS_COLORS[index % len(UNIT_CLASS_COLORS)]
            for index, cls in enumerate(class_sequence)
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤单位")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)
        self._show_cost_toggle = QCheckBox("显示成本为1的单位")
        self._show_cost_toggle.stateChanged.connect(self._handle_cost_toggle)
        toggle_row.addWidget(self._show_cost_toggle)
        self._ignore_unknown_toggle = QCheckBox("忽视未知")
        self._ignore_unknown_toggle.stateChanged.connect(self._handle_ignore_unknown_toggle)
        toggle_row.addWidget(self._ignore_unknown_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["UnitType", "单位", "PromotionClass名称"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _handle_cost_toggle(self, _state: int) -> None:
        self._show_cost_one = self._show_cost_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def _handle_ignore_unknown_toggle(self, _state: int) -> None:
        self._ignore_unknown = self._ignore_unknown_toggle.isChecked()
        self._apply_filter(self._search_edit.text())

    def _emit_rows(self, rows: Sequence[Dict[str, object]]) -> None:
        self._table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            promotion_class = str(entry.get("promotion_class") or "")
            promotion_name = str(entry.get("promotion_name") or promotion_class)
            type_item = QTableWidgetItem(str(entry.get("type") or ""))
            name_item = QTableWidgetItem(str(entry.get("name") or ""))
            class_item = QTableWidgetItem(promotion_name)
            if bool(entry.get("_workspace_pin")):
                for item in (type_item, name_item, class_item):
                    item.setBackground(QColor(WORKSPACE_PIN_BG))
            else:
                color = self._class_colors.get(promotion_class)
                if color:
                    for item in (type_item, name_item, class_item):
                        item.setBackground(QColor(color))
            for item in (type_item, name_item, class_item):
                item.setData(Qt.ItemDataRole.UserRole, entry)
            self._table.setItem(row_index, 0, type_item)
            self._table.setItem(row_index, 1, name_item)
            self._table.setItem(row_index, 2, class_item)

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        filtered: List[Dict[str, object]] = []
        for entry in self._rows:
            if not self._show_cost_one and int(entry.get("cost") or 0) == 1:
                continue
            if self._ignore_unknown and str(entry.get("name") or "").strip() == "未知":
                continue
            type_name = str(entry.get("type") or "").lower()
            name = str(entry.get("name") or "").lower()
            promotion_name = str(entry.get("promotion_name") or "").lower()
            promotion_class = str(entry.get("promotion_class") or "").lower()
            if not key or key in type_name or key in name or key in promotion_name or key in promotion_class:
                filtered.append(entry)
        self._filtered = filtered
        self._emit_rows(self._filtered)

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        current_row = self._table.currentRow()
        if 0 <= current_row < len(self._filtered):
            self._selected = self._filtered[current_row]
            self.accept()
        else:
            self.reject()

    def selected_type(self) -> str | None:
        if self._selected is None:
            return None
        return str(self._selected.get("type") or "")


class UnitSearchSelectorTemplate(_TypeSearchTemplate):
    """Unit selector grouped by promotion class."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "单位搜索选择框",
            "单位",
            "可直接输入或点击选择单位Type",
            "unit_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = _build_unit_entries()
        if not rows:
            return None
        dialog = _UnitSearchDialog(rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class UnitSearchNoTraitSelectorTemplate(_TypeSearchTemplate):
    """Unit selector excluding trait-restricted entries."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "单位搜索选择框（无Trait）",
            "单位",
            "可直接输入或点击选择单位Type",
            "unit_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = [
            entry
            for entry in _build_unit_entries()
            if not (str(entry.get("trait") or "").strip())
        ]
        if not rows:
            return None
        dialog = _UnitSearchDialog(rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class _UnitAiTypeSearchDialog(QDialog):
    def __init__(self, rows: Sequence[Tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择单位AI类型")
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self.resize(780, 560)

        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Tuple[str, str] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_row.addWidget(QLabel("搜索："))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤 AiType")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["AiType", "中文说明"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        if not key:
            self._filtered = list(self._rows)
        else:
            self._filtered = [
                row
                for row in self._rows
                if key in row[0].lower() or key in row[1].lower()
            ]
        self._table.setRowCount(len(self._filtered))
        for idx, (ai_type, zh) in enumerate(self._filtered):
            self._table.setItem(idx, 0, QTableWidgetItem(ai_type))
            self._table.setItem(idx, 1, QTableWidgetItem(zh))

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()
        else:
            self.reject()

    def selected_type(self) -> str | None:
        if self._selected is None:
            return None
        return self._selected[0]


class UnitAiTypeSearchSelectorTemplate(_TypeSearchTemplate):
    """Unit AI type selector sourced from UnitAiTypes table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "单位AI类型搜索选择框",
            "单位AI类型",
            "可直接输入或点击选择 AiType",
            "ai_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = _fetch_unit_ai_type_rows()
        if not rows:
            return None
        dialog = _UnitAiTypeSearchDialog(rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


class _ImprovementSearchDialog(QDialog):
    """Dialog presenting improvements ordered by prerequisites."""

    def __init__(self, rows: Sequence[Dict[str, object]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择改良设施")
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self.resize(780, 560)

        self._rows = list(rows)
        self._filtered = list(rows)
        self._selected: Dict[str, object] | None = None
        self._ignore_unknown = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        search_label = QLabel("搜索：")
        search_row.addWidget(search_label)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤改良设施")
        self._search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search_edit, 1)
        layout.addLayout(search_row)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)
        self._ignore_unknown_toggle = QCheckBox("忽视未知")
        self._ignore_unknown_toggle.stateChanged.connect(self._handle_ignore_unknown_toggle)
        toggle_row.addWidget(self._ignore_unknown_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["改良设施", "ImprovementType"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._handle_double_click)
        layout.addWidget(self._table, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self._handle_confirm)
        button_row.addWidget(confirm_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

        self._apply_filter("")

    def _emit_rows(self, rows: Sequence[Dict[str, object]]) -> None:
        self._table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            name_item = QTableWidgetItem(str(entry.get("name") or ""))
            type_item = QTableWidgetItem(str(entry.get("type") or ""))
            if bool(entry.get("_workspace_pin")):
                color = QColor(WORKSPACE_PIN_BG)
                for item in (name_item, type_item):
                    item.setBackground(color)
            for item in (name_item, type_item):
                item.setData(Qt.ItemDataRole.UserRole, entry)
            self._table.setItem(row_index, 0, name_item)
            self._table.setItem(row_index, 1, type_item)

    def _apply_filter(self, keyword: str) -> None:
        key = keyword.strip().lower()
        filtered: List[Dict[str, object]] = []
        for entry in self._rows:
            if self._ignore_unknown and str(entry.get("name") or "").strip() == "未知":
                continue
            type_name = str(entry.get("type") or "").lower()
            name = str(entry.get("name") or "").lower()
            if not key or key in type_name or key in name:
                filtered.append(entry)
        self._filtered = filtered
        self._emit_rows(self._filtered)

    def _handle_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._filtered):
            self._selected = self._filtered[row]
            self.accept()

    def _handle_confirm(self) -> None:
        current_row = self._table.currentRow()
        if 0 <= current_row < len(self._filtered):
            self._selected = self._filtered[current_row]
            self.accept()
        else:
            self.reject()

    def selected_type(self) -> str | None:
        if self._selected is None:
            return None
        return str(self._selected.get("type") or "")

    def _handle_ignore_unknown_toggle(self, _state: int) -> None:
        self._ignore_unknown = self._ignore_unknown_toggle.isChecked()
        self._apply_filter(self._search_edit.text())


class ImprovementSearchSelectorTemplate(_TypeSearchTemplate):
    """Improvement selector ordered by prerequisite tech/civic."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "改良设施搜索选择框",
            "改良设施",
            "可直接输入或点击选择改良设施Type",
            "improvement_type",
            parent,
        )

    def _select_from_dialog(self) -> str | None:
        rows = _build_improvement_entries()
        if not rows:
            return None
        dialog = _ImprovementSearchDialog(rows, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type()
        return None


@dataclass(frozen=True)
class UITemplateSpec:
    key: str
    name: str
    factory: Callable[[], BaseTemplateWidget]


TEMPLATE_SPECS: tuple[UITemplateSpec, ...] = (
    # 基础输入
    UITemplateSpec("text", "文本输入框", TextInputTemplate),
    UITemplateSpec("binary", "二选一勾选按钮", BinaryChoiceTemplate),
    UITemplateSpec("choice", "选择框", ChoiceTemplate),
    UITemplateSpec("int_spin", "整数输入框", IntegerSpinTemplate),

    # 数据下拉选择
    UITemplateSpec("tourism_source", "TourismSource选择框", TourismSourceTemplate),
    UITemplateSpec("feature_passable", "地貌（可通行）", FeatureSelectorPassableTemplate),
    UITemplateSpec("feature_all", "地貌（全部）", FeatureSelectorAllTemplate),
    UITemplateSpec("terrain", "地形选择框", TerrainSelectorTemplate),
    UITemplateSpec("era", "时代选择框", EraSelectorTemplate),
    UITemplateSpec("resource_strategic", "战略资源选择框", ResourceStrategicTemplate),
    UITemplateSpec("plunder_type", "掠夺类型选择框", PlunderTypeSelectorTemplate),
    UITemplateSpec("cost_progression", "成本递增模型选择框", CostProgressionTemplate),
    UITemplateSpec("domain", "领域选择框", DomainSelectorTemplate),
    UITemplateSpec("formation_class", "编队类型选择框", FormationClassSelectorTemplate),
    UITemplateSpec("yield", "产出选择框", YieldSelectorTemplate),
    UITemplateSpec("unit_promotion_class", "单位晋升类型选择框", UnitPromotionClassSelectorTemplate),
    UITemplateSpec("great_person_class", "伟人类型选择框", GreatPersonClassSelectorTemplate),
    UITemplateSpec("government_slot", "政策槽位选择框", GovernmentSlotSelectorTemplate),
    UITemplateSpec("government_type", "政体选择框", GovernmentSelectorTemplate),
    UITemplateSpec("belief_class", "信仰类别勾选组", BeliefClassSelectorTemplate),
    UITemplateSpec("ability_class_tag", "ABILITY_CLASS标签选择框", AbilityClassTagTemplate),
    UITemplateSpec("unit_ability_type", "UnitAbilityType选择框", UnitAbilityTypeTemplate),
    UITemplateSpec("great_work_object_type", "巨作类型选择框", GreatWorkObjectTypeTemplate),
    UITemplateSpec("advisor_type", "顾问类型选择框", AdvisorTypeSelectorTemplate),
    UITemplateSpec("resource_class", "资源类型选择框", ResourceClassSelectorTemplate),

    # 搜索弹窗选择
    UITemplateSpec("resource_search", "资源搜索选择框", ResourceSearchSelectorTemplate),
    UITemplateSpec("district_search", "区域搜索选择框", DistrictSearchSelectorTemplate),
    UITemplateSpec("district_search_no_trait", "区域搜索选择框（无Trait）", DistrictSearchNoTraitSelectorTemplate),
    UITemplateSpec("building_search", "建筑搜索选择框", BuildingSearchSelectorTemplate),
    UITemplateSpec("building_search_all", "建筑搜索选择框（含奇观）", BuildingSearchAllSelectorTemplate),
    UITemplateSpec("building_search_no_trait", "建筑搜索选择框（无Trait无奇观）", BuildingSearchNoTraitSelectorTemplate),
    UITemplateSpec("unit_search", "单位搜索选择框", UnitSearchSelectorTemplate),
    UITemplateSpec("unit_search_no_trait", "单位搜索选择框（无Trait）", UnitSearchNoTraitSelectorTemplate),
    UITemplateSpec("unit_ai_type", "单位AI类型搜索选择框", UnitAiTypeSearchSelectorTemplate),
    UITemplateSpec("improvement_search", "改良设施搜索选择框", ImprovementSearchSelectorTemplate),
    UITemplateSpec("technology_search", "科技搜索选择框", TechnologySearchSelectorTemplate),
    UITemplateSpec("civic_search", "市政搜索选择框", CivicSearchSelectorTemplate),
    UITemplateSpec("moment_texture_search", "历史时刻Texture搜索选择框", MomentTextureSearchTemplate),
)


def build_template_widget(key: str) -> BaseTemplateWidget:
    for spec in TEMPLATE_SPECS:
        if spec.key == key:
            return spec.factory()
    raise KeyError(f"Unknown template key: {key}")
