"""Home page for ModifiersTool."""
from __future__ import annotations

import copy
import json
import logging
import re
import sqlite3
from xml.dom import minidom
from xml.etree import ElementTree
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from PyQt6.QtCore import Qt, QTimer, QStringListModel
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QDoubleSpinBox,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..ui_widget_kit import BaseTemplateWidget, build_template_widget
from ...db.paths import DATA_DIR, DEFAULT_GAME_DB
from .base_page import BasePage


LOGGER = logging.getLogger(__name__)


class ReqsetComboBox(QComboBox):
    def __init__(self, name: str, on_popup: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._on_popup = on_popup

    def showPopup(self) -> None:
        try:
            self._on_popup(self._name)
        finally:
            super().showPopup()


class IntParamSpinBox(QDoubleSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDecimals(6)
        self.setSingleStep(1.0)

    def stepBy(self, steps: int) -> None:  # type: ignore[override]
        base = int(round(self.value()))
        self.setValue(base + steps)

    def textFromValue(self, value: float) -> str:  # type: ignore[override]
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"




# 表名 -> 类型字段 映射表（可扩展）
OWNER_TABLE_TYPE_MAP: Dict[str, str] = {
    "TraitModifiers": "TraitType",
    "BeliefModifiers": "BeliefType",
    "BuildingModifiers": "BuildingType",
    "CivicModifiers": "CivicType",
    "DistrictModifiers": "DistrictType",
    "GovernmentModifiers": "GovernmentType",
    "GreatPersonIndividualActionModifiers": "GreatPersonIndividualType",
    "GreatPersonIndividualBirthModifiers": "GreatPersonIndividualType",
    "GreatWorkModifiers": "GreatWorkType",
    "ImprovementModifiers": "ImprovementType",
    "PolicyModifiers": "PolicyType",
    "ProjectCompletionModifiers": "ProjectType",
    "TechnologyModifiers": "TechnologyType",
    "UnitAbilityModifiers": "UnitAbilityType",
    "UnitPromotionModifiers": "UnitPromotionType",
    "CommemorationModifiers": "CommemorationType",
    "ComplimentModifiers": "CommemorationType",
    "GovernorModifiers": "GovernorType",
    "GovernorPromotionModifiers": "GovernorPromotionType",
}

OWNER_TABLE_WITH_ATTACHMENT_TARGET = "GreatPersonIndividualActionModifiers"

TRAIT_SOURCE_PREFIX_LABELS: Dict[str, str] = {
    "civilization_trait:": "文明",
    "leader_trait:": "领袖",
    "district_trait:": "区域",
    "building_trait:": "建筑",
    "unit_trait:": "单位",
    "improvement_trait:": "改良设施",
    "governor_trait:": "总督",
}


BOOLEAN_PARAM_KEYS = {
    "Banned",
    "IsWonder",
    "CityStatesOnly",
    "CanPurchase",
    "HasBonus",
    "AlwaysLoyal",
    "Enable",
    "Enabled",
    "Domestic",
    "Ignore",
    "NoRemove",
    "Origin",
    "Destination",
    "SeeHidden",
    "CanSee",
    "Disable",
    "Intercontinental",
    "NoDamage",
}

INT_PARAM_KEYS = {
    "Amount",
    "ScalingFactor",
    "YieldChange",
    "Delta",
    "Range",
    "TilesRequired",
    "MaxDistance",
    "MinDistance",
    "MaximumAppeal",
    "MinimumAppeal",
    "PropertyMinimum",
    "MinimumAmount",
    "Percent",
    "MinScore",
}

TEMPLATE_PARAM_MAPPINGS: Dict[str, str] = {
    "YieldType": "yield",
    "YieldTypeToGrant": "yield",
    "YieldTypeToMirror": "yield",
    "DistrictType": "district_search",
    "BuildingType": "building_search_all",
    "BuildingTypeToReplace": "building_search_all",
    "UnitType": "unit_search",
    "ImprovementType": "improvement_search",
    "UnitDomain": "domain",
    "Domain": "domain",
    "FeatureType": "feature_all",
    "StartEra": "era",
    "EndEra": "era",
    "EarliestEra": "era",
    "LatestEra": "era",
    "MinimumEraType": "era",
    "EraType": "era",
    "EndEraType": "era",
    "StartEraType": "era",
    "ResourceType": "resource_search",
    "TerrainType": "terrain",
    "TechType": "technology_search",
    "TechnologyType": "technology_search",
    "CivicType": "civic_search",
    "GreatPersonClassType": "great_person_class",
    "ResourceClassType": "resource_class",
    "AbilityType": "unit_ability_type",
}


@dataclass
class OwnerRecord:
    table_name: str
    type_column: str
    type_name: str
    display_name: str = ""
    source_key: str = ""
    bound_modifier_ids: List[str] = field(default_factory=list)
    owner_bindings: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class UnitAbilityRecord:
    unit_ability_type: str
    name_zh: str = ""
    description_zh: str = ""
    inactive: bool = False
    show_float_text_when_earned: bool = False
    permanent: bool = True
    type_tags: List[str] = field(default_factory=list)


@dataclass
class ModifierTypeRecord:
    modifier_type: str
    effect_type: str | None
    collection_type: str | None


@dataclass
class ModifierRecord:
    modifier_id: str
    modifier_type: str
    comment: str = ""
    owner_reqset: str | None = None
    subject_reqset: str | None = None
    run_once: bool = False
    new_only: bool = False
    permanent: bool = False
    owner_stack_limit: int = 0
    subject_stack_limit: int = 0
    effect_type: str | None = None
    collection_type: str | None = None
    preview_text: str = ""
    parameters: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class RequirementSetRecord:
    requirement_set_id: str
    comment: str = ""
    logic: str = "ALL"
    bound_requirements: List[str] = field(default_factory=list)


@dataclass
class RequirementRecord:
    requirement_id: str
    comment: str = ""
    requirement_type: str = ""
    likeliness: int = 0
    impact: int = 0
    progress_weight: int = 1
    inverse: bool = False
    reverse: bool = False
    persistent: bool = False
    triggered: bool = False
    parameters: List[Dict[str, object]] = field(default_factory=list)


class SearchListDialog(QDialog):
    def __init__(self, title: str, options: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(560, 520)

        layout = QVBoxLayout(self)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入关键字过滤")
        layout.addWidget(self._search_edit)

        self._list = QListWidget()
        self._list.addItems(options)
        self._list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self._list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._all_options = list(options)
        self._search_edit.textChanged.connect(self._apply_filter)

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        self._list.clear()
        if not needle:
            self._list.addItems(self._all_options)
            return
        filtered = [opt for opt in self._all_options if needle in opt.lower()]
        self._list.addItems(filtered)

    def selected(self) -> str | None:
        item = self._list.currentItem()
        return item.text() if item else None


class ReqsetSearchDialog(QDialog):
    def __init__(
        self,
        title: str,
        rows: Sequence[tuple[str, str]],
        current_value: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 560)

        self._all_rows: List[tuple[str, str]] = list(rows)

        layout = QVBoxLayout(self)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("输入中文注释或条件集名字过滤")
        layout.addWidget(self._search_edit)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["中文注释", "条件集名字"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.itemDoubleClicked.connect(lambda _item: self.accept())
        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._search_edit.textChanged.connect(self._apply_filter)
        self._apply_filter("")
        self._select_by_value(current_value)

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        self._table.setRowCount(0)
        for comment, reqset_id in self._all_rows:
            comment_text = str(comment or "")
            id_text = str(reqset_id or "")
            if needle and needle not in comment_text.lower() and needle not in id_text.lower():
                continue
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(comment_text or ""))
            self._table.setItem(row, 1, QTableWidgetItem(id_text or "（空）"))

    def _select_by_value(self, value: str) -> None:
        target = str(value or "")
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 1)
            if item is None:
                continue
            text = item.text()
            normalized = "" if text == "（空）" else text
            if normalized == target:
                self._table.selectRow(row)
                break

    def selected(self) -> str | None:
        selected = self._table.selectionModel().selectedRows() if self._table.selectionModel() is not None else []
        if not selected:
            return None
        row = selected[0].row()
        item = self._table.item(row, 1)
        if item is None:
            return None
        text = item.text().strip()
        return "" if text == "（空）" else text


class TextPreviewDialog(QDialog):
    def __init__(self, title: str, content: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 560)
        self.setModal(True)

        layout = QVBoxLayout(self)
        text_area = QPlainTextEdit()
        text_area.setReadOnly(True)
        text_area.setPlainText(content)
        text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(text_area)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        layout.addWidget(close_box)


class UnitAbilityEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, prefix: str = "", infix: int = 0) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ability编辑")
        self.resize(860, 620)

        self._prefix = self._normalize_token(prefix)
        self._infix = max(0, int(infix or 0))

        self._short_name = QLineEdit()
        self._short_name.setPlaceholderText("输入简称，例如 U0023_S")
        self._short_name.textChanged.connect(self._refresh_ability_type)

        self._ability_type = QLineEdit()
        self._ability_type.setReadOnly(True)
        self._ability_type.setPlaceholderText("将根据简称自动生成")

        self._name_zh = QLineEdit()
        self._name_zh.setPlaceholderText("中文名称")

        self._description_zh = QPlainTextEdit()
        self._description_zh.setPlaceholderText("中文描述")
        self._description_zh.setFixedHeight(96)

        self._inactive_cb = QCheckBox("Inactive")
        self._show_float_cb = QCheckBox("ShowFloatTextWhenEarned")
        self._permanent_cb = QCheckBox("Permanent")
        self._permanent_cb.setChecked(True)

        self._type_tag_table = QTableWidget(0, 1)
        self._type_tag_table.setHorizontalHeaderLabels(["Tag（ABILITY_CLASS）"])
        self._type_tag_table.horizontalHeader().setStretchLastSection(True)
        self._type_tag_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._type_tag_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._type_tag_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._type_tag_table.setMinimumHeight(180)

        add_tag_btn = QPushButton("新增Tag")
        add_tag_btn.clicked.connect(self._handle_add_tag_row)
        del_tag_btn = QPushButton("删除Tag")
        del_tag_btn.clicked.connect(self._handle_delete_tag_row)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("简称", self._short_name)
        form.addRow("UnitAbilityType", self._ability_type)
        form.addRow("Name(zh)", self._name_zh)
        form.addRow("Description(zh)", self._description_zh)

        flags = QHBoxLayout()
        flags.addWidget(self._inactive_cb)
        flags.addWidget(self._show_float_cb)
        flags.addWidget(self._permanent_cb)
        flags.addStretch(1)

        tag_buttons = QHBoxLayout()
        tag_buttons.addWidget(add_tag_btn)
        tag_buttons.addWidget(del_tag_btn)
        tag_buttons.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(flags)
        layout.addWidget(QLabel("TypeTags（Type 固定为 UnitAbilityType）"))
        layout.addLayout(tag_buttons)
        layout.addWidget(self._type_tag_table, 1)
        layout.addWidget(buttons)

        self._saved_record: UnitAbilityRecord | None = None

    def set_record(self, record: UnitAbilityRecord) -> None:
        self._short_name.setText(self._extract_short_from_type(record.unit_ability_type))
        self._refresh_ability_type()
        self._name_zh.setText(record.name_zh)
        self._description_zh.setPlainText(record.description_zh)
        self._inactive_cb.setChecked(bool(record.inactive))
        self._show_float_cb.setChecked(bool(record.show_float_text_when_earned))
        self._permanent_cb.setChecked(bool(record.permanent))
        self._type_tag_table.setRowCount(0)
        for tag in record.type_tags:
            self._append_tag_row(str(tag or "").strip())

    @staticmethod
    def _normalize_token(value: object | None) -> str:
        text = str(value or "").strip().upper()
        return re.sub(r"[^A-Z0-9_]", "", text)

    def _extract_short_from_type(self, ability_type: str) -> str:
        clean = self._normalize_token(ability_type)
        if not clean:
            return ""
        if clean.startswith("ABILITY_"):
            clean = clean[len("ABILITY_"):]
        parts = [part for part in clean.split("_") if part]
        if not parts:
            return ""
        prefix_parts: list[str] = []
        if self._prefix:
            prefix_parts = [part for part in self._prefix.split("_") if part]
        if prefix_parts and parts[: len(prefix_parts)] == prefix_parts:
            parts = parts[len(prefix_parts):]
        if self._infix > 0 and parts and parts[0] == f"A{self._infix:04d}":
            parts = parts[1:]
        return "_".join(parts)

    def _refresh_ability_type(self) -> None:
        short = self._normalize_token(self._short_name.text())
        if short != self._short_name.text().strip().upper():
            self._short_name.blockSignals(True)
            self._short_name.setText(short)
            self._short_name.blockSignals(False)

        parts = ["ABILITY"]
        if self._prefix:
            parts.append(self._prefix)
        if self._infix > 0:
            parts.append(f"A{self._infix:04d}")
        if short:
            parts.append(short)
        self._ability_type.setText("_".join(parts) if len(parts) > 1 else "")

    def saved_record(self) -> UnitAbilityRecord | None:
        return self._saved_record

    def _handle_add_tag_row(self) -> None:
        self._append_tag_row("")

    def _append_tag_row(self, value: str) -> None:
        row = self._type_tag_table.rowCount()
        self._type_tag_table.insertRow(row)
        try:
            widget = build_template_widget("ability_class_tag")
        except KeyError:
            combo = QComboBox()
            combo.setEditable(True)
            widget = combo
        if isinstance(widget, BaseTemplateWidget):
            widget.set_current_value(value or None)
            combo = getattr(widget, "_combo", None)
            if isinstance(combo, QComboBox):
                combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
                combo.setMinimumContentsLength(36)
                combo.setMinimumWidth(420)
                view = combo.view()
                if view is not None:
                    view.setTextElideMode(Qt.TextElideMode.ElideNone)
                    view.setMinimumWidth(520)
        elif isinstance(widget, QComboBox):
            if value and widget.findText(value) < 0:
                widget.addItem(value)
            widget.setCurrentText(value)
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            widget.setMinimumContentsLength(36)
            widget.setMinimumWidth(420)
            view = widget.view()
            if view is not None:
                view.setTextElideMode(Qt.TextElideMode.ElideNone)
                view.setMinimumWidth(520)
        self._type_tag_table.setCellWidget(row, 0, widget)
        self._type_tag_table.setRowHeight(row, 42)

    def _handle_delete_tag_row(self) -> None:
        selected = self._type_tag_table.selectionModel().selectedRows()
        if not selected:
            return
        self._type_tag_table.removeRow(selected[0].row())

    def _collect_type_tags(self) -> List[str]:
        output: List[str] = []
        seen: set[str] = set()
        for row in range(self._type_tag_table.rowCount()):
            widget = self._type_tag_table.cellWidget(row, 0)
            value = ""
            if isinstance(widget, BaseTemplateWidget):
                payload = widget.export_data()
                if isinstance(payload, dict):
                    value = str(payload.get("tag") or payload.get("value") or "").strip()
            elif isinstance(widget, QComboBox):
                value = widget.currentText().strip()
            if not value or value in seen:
                continue
            seen.add(value)
            output.append(value)
        return output

    def _handle_accept(self) -> None:
        short_name = self._normalize_token(self._short_name.text())
        if not short_name:
            QMessageBox.warning(self, "提示", "请填写简称")
            return
        ability_type = self._ability_type.text().strip()
        if not ability_type:
            QMessageBox.warning(self, "提示", "未生成 UnitAbilityType，请检查简称")
            return
        self._saved_record = UnitAbilityRecord(
            unit_ability_type=ability_type,
            name_zh=self._name_zh.text().strip(),
            description_zh=self._description_zh.toPlainText().strip(),
            inactive=bool(self._inactive_cb.isChecked()),
            show_float_text_when_earned=bool(self._show_float_cb.isChecked()),
            permanent=bool(self._permanent_cb.isChecked()),
            type_tags=self._collect_type_tags(),
        )
        self.accept()


class HomePage(BasePage):
    page_id = "home"
    display_name = "首页"

    WIDE_LAYOUT_MIN_WIDTH = 1200
    LEFT_MIN_WIDTH = 300
    MIDDLE_MIN_WIDTH = 320
    RIGHT_MIN_WIDTH = 560

    def __init__(self) -> None:
        super().__init__()
        self._owners: List[OwnerRecord] = []
        self._unit_ability_records: List[UnitAbilityRecord] = []
        self._selected_owner_index: int = -1
        self._modifiers: List[ModifierRecord] = []
        self._current_modifier_index: int = -1
        self._modifier_editor_index: int = -1
        self._modifier_meta_index: Dict[str, ModifierTypeRecord] = {}
        self._effect_types: List[str] = []
        self._collection_types: List[str] = []
        self._effect_param_map: Dict[str, List[str]] = {}
        self._requirement_types: List[str] = []
        self._requirement_param_map: Dict[str, List[str]] = {}
        self._attachment_target_types: List[str] = []

        self._loading_modifier_editor = False
        self._loading_reqset_editor = False
        self._loading_requirement_editor = False

        self._requirement_sets: List[RequirementSetRecord] = []
        self._requirements: List[RequirementRecord] = []
        self._current_reqset_index: int = -1
        self._current_req_index: int = -1

        # Part 1 widgets
        self._owner_table_combo: QComboBox | None = None
        self._owner_type_label: QLabel | None = None
        self._owner_type_input: QLineEdit | None = None

        # Part 2 widgets
        self._owner_section_body: QWidget | None = None
        self._owner_tree: QTreeWidget | None = None
        self._owner_bind_table: QTableWidget | None = None
        self._owner_bind_add_btn: QPushButton | None = None
        self._owner_bind_del_btn: QPushButton | None = None
        self._owner_add_ability_btn: QPushButton | None = None
        self._owner_edit_ability_btn: QPushButton | None = None
        self._owner_attachment_container: QWidget | None = None
        self._owner_attachment_combo: QComboBox | None = None
        self._owner_delete_btn: QPushButton | None = None
        self._owner_toggle_btn: QPushButton | None = None
        self._owner_selected_label: QLabel | None = None
        self._owner_bind_compact_bar: QWidget | None = None
        self._owner_bind_compact_label: QLabel | None = None
        self._owner_bind_compact_add_btn: QPushButton | None = None
        self._owner_bind_compact_del_btn: QPushButton | None = None
        self._owner_bind_selected_row: int = -1
        self._loading_owner_attachment_editor = False

        # Part 3 widgets
        self._modifier_list: QTableWidget | None = None
        self._prefix_input: QLineEdit | None = None
        self._prefix2_input: QLineEdit | None = None
        self._modifier_id_input: QLineEdit | None = None
        self._comment_input: QLineEdit | None = None
        self._modifier_type_combo: QComboBox | None = None
        self._effect_type_combo: QComboBox | None = None
        self._collection_type_combo: QComboBox | None = None
        self._owner_reqset_input: QLineEdit | None = None
        self._subject_reqset_input: QLineEdit | None = None
        self._owner_reqset_combo: QComboBox | None = None
        self._subject_reqset_combo: QComboBox | None = None
        self._owner_reqset_menu: QMenu | None = None
        self._subject_reqset_menu: QMenu | None = None
        self._owner_reqset_btn: QToolButton | None = None
        self._subject_reqset_btn: QToolButton | None = None
        self._run_once_cb: QCheckBox | None = None
        self._new_only_cb: QCheckBox | None = None
        self._permanent_cb: QCheckBox | None = None
        self._owner_stack_spin: QSpinBox | None = None
        self._subject_stack_spin: QSpinBox | None = None
        self._param_table: QTableWidget | None = None
        self._param_add_btn: QPushButton | None = None
        self._param_del_btn: QPushButton | None = None
        self._modifier_preview_container: QWidget | None = None
        self._modifier_preview_text: QPlainTextEdit | None = None

        # Requirement section widgets
        self._reqset_list: QTableWidget | None = None
        self._req_list: QTableWidget | None = None
        self._reqset_id_input: QLineEdit | None = None
        self._reqset_comment_input: QLineEdit | None = None
        self._reqset_logic_all: QCheckBox | None = None
        self._reqset_logic_any: QCheckBox | None = None
        self._reqset_bind_list: QListWidget | None = None
        self._reqset_bind_add_btn: QPushButton | None = None
        self._reqset_bind_del_btn: QPushButton | None = None
        self._reqset_delete_btn: QPushButton | None = None
        self._reqset_toggle_btn: QPushButton | None = None
        self._reqset_section_body: QWidget | None = None

        self._req_id_input: QLineEdit | None = None
        self._req_comment_input: QLineEdit | None = None
        self._req_type_combo: QComboBox | None = None
        self._req_type_search_btn: QPushButton | None = None
        self._req_likeliness_spin: QSpinBox | None = None
        self._req_impact_spin: QSpinBox | None = None
        self._req_progress_spin: QSpinBox | None = None
        self._req_inverse_cb: QCheckBox | None = None
        self._req_reverse_cb: QCheckBox | None = None
        self._req_persistent_cb: QCheckBox | None = None
        self._req_triggered_cb: QCheckBox | None = None
        self._req_param_table: QTableWidget | None = None
        self._req_param_add_btn: QPushButton | None = None
        self._req_param_del_btn: QPushButton | None = None

        self._requirement_editor_container: QWidget | None = None
        self._requirement_editor_wide: QSplitter | None = None
        self._requirement_editor_narrow: QSplitter | None = None
        self._requirement_editor_midright: QSplitter | None = None
        self._requirement_editor_vertical: QSplitter | None = None
        self._requirement_editor_narrow_active = False
        self._requirement_left_panel: QWidget | None = None
        self._requirement_middle_panel: QWidget | None = None
        self._requirement_right_panel: QWidget | None = None

        self._modifier_editor_container: QWidget | None = None
        self._modifier_editor_wide: QSplitter | None = None
        self._modifier_editor_narrow: QSplitter | None = None
        self._modifier_editor_right_host: QWidget | None = None
        self._modifier_editor_vertical: QSplitter | None = None
        self._modifier_editor_midright: QSplitter | None = None
        self._modifier_editor_narrow_active = False
        self._modifier_left_panel: QWidget | None = None
        self._modifier_middle_panel: QWidget | None = None
        self._modifier_right_panel: QWidget | None = None
        self._scroll_area: QScrollArea | None = None
        self._scroll_content: QWidget | None = None

        self._reqset_model = QStringListModel(self)

        self._load_reference_data()
        self._build_ui()
        self._ensure_default_modifier()

    # -------------------- Data Loading --------------------
    def _load_reference_data(self) -> None:
        self._modifier_meta_index = self._load_modifier_meta_from_db()
        effect_types, collection_types, effect_param_map, requirement_types, requirement_param_map = self._load_effect_type_parameters()
        self._effect_types = effect_types
        self._collection_types = collection_types
        self._effect_param_map = effect_param_map
        self._requirement_types = requirement_types
        self._requirement_param_map = requirement_param_map
        self._attachment_target_types = self._load_attachment_target_types()

    def _load_attachment_target_types(self) -> List[str]:
        if not DEFAULT_GAME_DB.exists():
            return []
        try:
            conn = sqlite3.connect(str(DEFAULT_GAME_DB))
            conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return []
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT AttachmentTargetType
                FROM GreatPersonIndividualActionModifiers
                WHERE AttachmentTargetType IS NOT NULL
                  AND TRIM(AttachmentTargetType) <> ''
                ORDER BY AttachmentTargetType
                """
            ).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()
        values: List[str] = []
        for row in rows:
            text = str(row["AttachmentTargetType"] or "").strip()
            if text:
                values.append(text)
        return values

    def _load_modifier_meta_from_db(self) -> Dict[str, ModifierTypeRecord]:
        if not DEFAULT_GAME_DB.exists():
            return {}
        try:
            conn = sqlite3.connect(str(DEFAULT_GAME_DB))
            conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return {}
        try:
            rows = conn.execute(
                "SELECT ModifierType, EffectType, CollectionType FROM DynamicModifiers"
            ).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()
        result: Dict[str, ModifierTypeRecord] = {}
        for row in rows:
            modifier_type = row["ModifierType"]
            if not modifier_type:
                continue
            result[modifier_type] = ModifierTypeRecord(
                modifier_type=modifier_type,
                effect_type=row["EffectType"],
                collection_type=row["CollectionType"],
            )
        return result

    def _load_effect_type_parameters(
        self,
    ) -> tuple[List[str], List[str], Dict[str, List[str]], List[str], Dict[str, List[str]]]:
        json_path = DATA_DIR / "effect_type_parameters.json"
        if not json_path.exists():
            return [], [], {}, [], {}
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return [], [], {}, [], {}
        if isinstance(data, dict):
            raw_effects = data.get("effect_types", [])
            raw_collections = data.get("collection_types", [])
            raw_requirements = data.get("requirement_types", [])
        else:
            raw_effects = data
            raw_collections = []
            raw_requirements = []

        effect_param_map: Dict[str, List[str]] = {}
        if isinstance(raw_effects, list):
            for entry in raw_effects:
                if not isinstance(entry, dict):
                    continue
                effect_type = str(entry.get("effect_type", "")).strip()
                if not effect_type:
                    continue
                param_names = entry.get("parameter_names", [])
                if not isinstance(param_names, list):
                    param_names = []
                effect_param_map[effect_type] = [str(name) for name in param_names if name]

        requirement_param_map: Dict[str, List[str]] = {}
        if isinstance(raw_requirements, list):
            for entry in raw_requirements:
                if not isinstance(entry, dict):
                    continue
                req_type = str(entry.get("requirement_type", "")).strip()
                if not req_type:
                    continue
                param_names = entry.get("parameter_names", [])
                if not isinstance(param_names, list):
                    param_names = []
                requirement_param_map[req_type] = [str(name) for name in param_names if name]

        effect_types = sorted(
            {
                entry.get("effect_type", "")
                for entry in raw_effects
                if isinstance(entry, dict) and entry.get("effect_type")
            }
        )
        collection_types = sorted(
            {
                entry.get("collection_type", "")
                for entry in raw_effects
                if isinstance(entry, dict) and entry.get("collection_type")
            }
        )
        if raw_collections:
            collection_types = sorted({*collection_types, *[c for c in raw_collections if c]})
        requirement_types = sorted(requirement_param_map.keys())
        return effect_types, collection_types, effect_param_map, requirement_types, requirement_param_map

    # -------------------- UI Build --------------------
    def _build_ui(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        owner_bind_section = self._build_owner_bind_section()
        owner_manage_section = self._build_owner_manage_section()
        modifier_editor_section = self._build_modifier_editor_section()
        requirement_editor_section = self._build_requirement_editor_section()

        layout.addWidget(owner_bind_section)
        layout.addWidget(owner_manage_section)
        layout.addWidget(modifier_editor_section)
        layout.addWidget(requirement_editor_section, 1)

        scroll_area.setWidget(content)
        self._scroll_area = scroll_area
        self._scroll_content = content
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(scroll_area, 1)
        root_layout.addWidget(self._build_home_footer())
        self.setLayout(root_layout)
        QTimer.singleShot(0, self._sync_scroll_width)

    def _build_home_footer(self) -> QWidget:
        footer = QFrame()
        footer.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        save_btn = QPushButton("保存数据")
        save_btn.clicked.connect(self._handle_save_data)
        import_btn = QPushButton("导入数据")
        import_btn.clicked.connect(self._handle_import_data)
        layout.addWidget(save_btn)
        layout.addWidget(import_btn)

        layout.addStretch(1)

        sql_btn = QPushButton("SQL预览")
        sql_btn.clicked.connect(self._handle_sql_preview)
        xml_btn = QPushButton("XML预览")
        xml_btn.clicked.connect(self._handle_xml_preview)
        layout.addWidget(sql_btn)
        layout.addWidget(xml_btn)

        return footer

    def _ensure_default_modifier(self) -> None:
        if self._modifiers:
            return
        self._handle_add_modifier()
        self._set_modifier_editor_enabled(True)

    # -------------------- Part 1: Owner Binding --------------------
    def _build_owner_bind_section(self) -> QGroupBox:
        group = QGroupBox("所有者绑定")
        layout = QHBoxLayout()

        layout.addWidget(QLabel("表名"))
        table_combo = QComboBox()
        table_combo.addItems(sorted(OWNER_TABLE_TYPE_MAP.keys()))
        table_combo.currentTextChanged.connect(self._update_owner_type_label)
        self._owner_table_combo = table_combo
        layout.addWidget(table_combo)

        layout.addWidget(QLabel("类型"))
        type_label = QLabel("-")
        type_label.setObjectName("ownerTypeLabel")
        self._owner_type_label = type_label
        layout.addWidget(type_label)

        layout.addWidget(QLabel("类型名"))
        type_input = QLineEdit()
        type_input.setPlaceholderText("请输入英文类型名")
        self._owner_type_input = type_input
        layout.addWidget(type_input, 1)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._handle_add_owner)
        layout.addWidget(add_btn)

        add_ability_btn = QPushButton("新增Ability")
        add_ability_btn.clicked.connect(self._handle_add_unit_ability)
        self._owner_add_ability_btn = add_ability_btn
        layout.addWidget(add_ability_btn)

        layout.addStretch(1)
        group.setLayout(layout)

        self._update_owner_type_label(table_combo.currentText())
        return group

    def _update_owner_type_label(self, table_name: str) -> None:
        if self._owner_type_label is None:
            return
        type_name = OWNER_TABLE_TYPE_MAP.get(table_name, "")
        self._owner_type_label.setText(type_name or "-")
        self._update_ability_buttons_state()

    # -------------------- Part 2: Owner Management --------------------
    def _build_owner_manage_section(self) -> QWidget:
        container = QGroupBox("所有者对象管理")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("所有者对象"))

        selected_label = QLabel("未选择")
        selected_label.setStyleSheet("color: #64748b;")
        self._owner_selected_label = selected_label
        header.addWidget(selected_label)

        header.addStretch(1)
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._handle_add_owner)
        header.addWidget(add_btn)

        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self._handle_delete_owner)
        self._owner_delete_btn = delete_btn
        header.addWidget(delete_btn)

        toggle_btn = QPushButton("折叠")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(False)
        toggle_btn.clicked.connect(self._toggle_owner_section)
        self._owner_toggle_btn = toggle_btn
        header.addWidget(toggle_btn)

        edit_ability_btn = QPushButton("编辑Ability")
        edit_ability_btn.clicked.connect(self._handle_edit_selected_unit_ability)
        self._owner_edit_ability_btn = edit_ability_btn
        header.addWidget(edit_ability_btn)

        outer.addLayout(header)

        compact_bar = QWidget()
        compact_layout = QHBoxLayout(compact_bar)
        compact_layout.setContentsMargins(0, 0, 0, 0)
        compact_layout.setSpacing(8)
        compact_layout.addWidget(QLabel("当前 ModifierId"))
        compact_current_label = QLabel("（无）")
        compact_current_label.setStyleSheet("color: #64748b;")
        self._owner_bind_compact_label = compact_current_label
        compact_layout.addWidget(compact_current_label, 1)
        compact_add_btn = QPushButton("添加 ModifierId")
        compact_add_btn.clicked.connect(self._handle_bind_modifier)
        self._owner_bind_compact_add_btn = compact_add_btn
        compact_layout.addWidget(compact_add_btn)
        compact_del_btn = QPushButton("删除选中")
        compact_del_btn.clicked.connect(self._handle_unbind_modifier)
        self._owner_bind_compact_del_btn = compact_del_btn
        compact_layout.addWidget(compact_del_btn)
        compact_bar.setVisible(False)
        self._owner_bind_compact_bar = compact_bar
        outer.addWidget(compact_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        owner_tree = QTreeWidget()
        owner_tree.setHeaderHidden(True)
        owner_tree.itemSelectionChanged.connect(self._on_owner_selected)
        owner_tree.setMinimumWidth(320)
        self._owner_tree = owner_tree
        body_layout.addWidget(owner_tree, 2)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        button_row = QHBoxLayout()
        add_bind_btn = QPushButton("添加 ModifierId")
        add_bind_btn.clicked.connect(self._handle_bind_modifier)
        self._owner_bind_add_btn = add_bind_btn
        del_bind_btn = QPushButton("删除选中")
        del_bind_btn.clicked.connect(self._handle_unbind_modifier)
        self._owner_bind_del_btn = del_bind_btn
        button_row.addWidget(add_bind_btn)
        button_row.addWidget(del_bind_btn)
        button_row.addStretch(1)
        right_layout.addLayout(button_row)

        attachment_container = QWidget()
        attachment_row = QHBoxLayout(attachment_container)
        attachment_row.setContentsMargins(0, 0, 0, 0)
        attachment_row.setSpacing(6)
        attachment_row.addWidget(QLabel("AttachmentTargetType"))
        attachment_combo = QComboBox()
        attachment_combo.setEditable(True)
        attachment_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        attachment_combo.addItems(self._attachment_target_types)
        attachment_combo.currentTextChanged.connect(self._on_owner_attachment_target_changed)
        self._owner_attachment_combo = attachment_combo
        attachment_row.addWidget(attachment_combo, 1)
        self._owner_attachment_container = attachment_container
        attachment_container.setVisible(False)
        right_layout.addWidget(attachment_container)

        bind_table = QTableWidget(0, 1)
        bind_table.setHorizontalHeaderLabels(["绑定的 ModifierId"])
        bind_table.horizontalHeader().setStretchLastSection(True)
        bind_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        bind_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        bind_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        bind_table.itemSelectionChanged.connect(self._on_owner_bind_selection_changed)
        self._set_table_min_rows(bind_table, 7)
        self._owner_bind_table = bind_table
        right_layout.addWidget(bind_table, 1)

        body_layout.addWidget(right_panel, 3)
        outer.addWidget(body)

        self._owner_section_body = body
        self._refresh_owner_tree()
        self._update_owner_section_state()
        return container

    def _toggle_owner_section(self) -> None:
        if self._owner_section_body is None or self._owner_toggle_btn is None:
            return
        collapsed = self._owner_toggle_btn.isChecked()
        self._owner_section_body.setVisible(not collapsed)
        self._owner_toggle_btn.setText("展开" if collapsed else "折叠")
        if self._owner_delete_btn is not None:
            self._owner_delete_btn.setVisible(not collapsed)
        if self._owner_bind_compact_bar is not None:
            self._owner_bind_compact_bar.setVisible(collapsed)
        self._update_owner_section_state()

    def _update_owner_section_state(self) -> None:
        has_owner = bool(self._owners)
        if self._owner_toggle_btn is not None:
            self._owner_toggle_btn.setEnabled(has_owner)
            if not has_owner:
                self._owner_toggle_btn.setChecked(False)
                self._owner_toggle_btn.setText("折叠")
                if self._owner_section_body is not None:
                    self._owner_section_body.setVisible(True)
                if self._owner_bind_compact_bar is not None:
                    self._owner_bind_compact_bar.setVisible(False)
        if self._owner_bind_compact_bar is not None and self._owner_toggle_btn is not None and has_owner:
            self._owner_bind_compact_bar.setVisible(self._owner_toggle_btn.isChecked())
        self._update_owner_bind_buttons()
        self._update_owner_bind_compact_label()
        self._update_ability_buttons_state()

    def _update_ability_buttons_state(self) -> None:
        if self._owner_add_ability_btn is not None and self._owner_table_combo is not None:
            table_name = self._owner_table_combo.currentText().strip()
            self._owner_add_ability_btn.setVisible(table_name == "UnitAbilityModifiers")

        if self._owner_edit_ability_btn is not None:
            enabled = False
            if 0 <= self._selected_owner_index < len(self._owners):
                owner = self._owners[self._selected_owner_index]
                enabled = owner.table_name == "UnitAbilityModifiers" and bool(self._find_unit_ability_record(owner.type_name))
            self._owner_edit_ability_btn.setEnabled(enabled)

    # -------------------- Part 3: Modifier Editor --------------------
    def _build_modifier_editor_section(self) -> QGroupBox:
        group = QGroupBox("ModifierId 编辑")
        # 不使用固定最小高度，允许根据内容和布局自适应伸缩
        group.setMinimumHeight(0)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._modifier_editor_container = QWidget()
        self._modifier_editor_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._modifier_editor_container.setMinimumWidth(0)
        container_layout = QVBoxLayout(self._modifier_editor_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._modifier_left_panel = self._build_modifier_list_panel()
        self._modifier_middle_panel = self._build_modifier_detail_panel()
        self._modifier_right_panel = self._build_modifier_param_panel()

        self._modifier_left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._modifier_middle_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._modifier_right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._modifier_editor_wide = self._build_modifier_editor_wide()
        self._modifier_editor_narrow = self._build_modifier_editor_narrow()

        self._modifier_editor_wide.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._modifier_editor_narrow.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        container_layout.addWidget(self._modifier_editor_wide, 1)
        container_layout.addWidget(self._modifier_editor_narrow, 1)
        self._modifier_editor_narrow.hide()
        self._apply_modifier_editor_layout(use_narrow=False)
        QTimer.singleShot(0, self._force_modifier_editor_layout)


        layout.addWidget(self._modifier_editor_container)
        return group

    def _build_modifier_editor_wide(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        mid_right = QSplitter(Qt.Orientation.Vertical)
        mid_right.setStretchFactor(0, 3)
        mid_right.setStretchFactor(1, 2)
        self._modifier_editor_midright = mid_right
        return splitter

    def _build_modifier_editor_narrow(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.setStretchFactor(0, 1)
        vertical.setStretchFactor(1, 1)
        self._modifier_editor_vertical = vertical
        return splitter

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_scroll_width()
        self._update_modifier_editor_layout()
        self._update_requirement_editor_layout()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(0, self._force_modifier_editor_layout)
        QTimer.singleShot(0, self._force_requirement_editor_layout)
        QTimer.singleShot(0, self._sync_scroll_width)

    def _sync_scroll_width(self) -> None:
        if self._scroll_area is None or self._scroll_content is None:
            return
        viewport_width = self._scroll_area.viewport().width()
        if viewport_width > 0:
            self._scroll_content.setMinimumWidth(viewport_width)
        self._update_modifier_editor_layout()
        self._update_requirement_editor_layout()

    def _update_modifier_editor_layout(self) -> None:
        if self._modifier_editor_container is None or self._modifier_editor_wide is None or self._modifier_editor_narrow is None:
            return
        width = (
            self._scroll_area.viewport().width()
            if self._scroll_area is not None
            else (self._modifier_editor_container.width() or self.width())
        )
        use_narrow = width < self.WIDE_LAYOUT_MIN_WIDTH
        if use_narrow != self._modifier_editor_narrow_active:
            self._modifier_editor_narrow_active = use_narrow
            self._apply_modifier_editor_layout(use_narrow)
        self._apply_modifier_editor_sizes(use_narrow)

    def _force_modifier_editor_layout(self) -> None:
        if self._modifier_editor_container is None:
            return
        width = (
            self._scroll_area.viewport().width()
            if self._scroll_area is not None
            else (self._modifier_editor_container.width() or self.width())
        )
        use_narrow = width < self.WIDE_LAYOUT_MIN_WIDTH
        self._modifier_editor_narrow_active = not use_narrow
        self._apply_modifier_editor_layout(use_narrow)
        self._apply_modifier_editor_sizes(use_narrow)

    def _apply_modifier_editor_layout(self, use_narrow: bool) -> None:
        if (
            self._modifier_left_panel is None
            or self._modifier_middle_panel is None
            or self._modifier_right_panel is None
            or self._modifier_editor_wide is None
            or self._modifier_editor_narrow is None
            or self._modifier_editor_midright is None
            or self._modifier_editor_vertical is None
        ):
            return

        left = self._modifier_left_panel
        middle = self._modifier_middle_panel
        right = self._modifier_right_panel

        self._clear_splitter(self._modifier_editor_wide)
        self._clear_splitter(self._modifier_editor_narrow)
        self._clear_splitter(self._modifier_editor_midright)
        self._clear_splitter(self._modifier_editor_vertical)

        left.setParent(None)
        middle.setParent(None)
        right.setParent(None)

        if use_narrow:
            self._modifier_editor_wide.hide()
            self._modifier_editor_narrow.show()
            self._modifier_editor_narrow.addWidget(left)
            self._modifier_editor_narrow.addWidget(self._modifier_editor_vertical)
            self._modifier_editor_vertical.addWidget(middle)
            self._modifier_editor_vertical.addWidget(right)
            self._modifier_editor_narrow.setChildrenCollapsible(False)
            self._modifier_editor_vertical.setChildrenCollapsible(False)
        else:
            self._modifier_editor_narrow.hide()
            self._modifier_editor_wide.show()
            self._modifier_editor_wide.addWidget(left)
            self._modifier_editor_wide.addWidget(self._modifier_editor_midright)
            self._modifier_editor_midright.addWidget(middle)
            self._modifier_editor_midright.addWidget(right)
            self._modifier_editor_wide.setChildrenCollapsible(False)
            self._modifier_editor_midright.setChildrenCollapsible(False)

    def _apply_modifier_editor_sizes(self, use_narrow: bool) -> None:
        if not all([
            self._modifier_editor_container,
            self._modifier_editor_wide,
            self._modifier_editor_narrow,
            self._modifier_editor_midright,
            self._modifier_editor_vertical,
        ]):
            return

        total_width = (
            self._scroll_area.viewport().width()
            if self._scroll_area is not None
            else (self._modifier_editor_container.width() or self.width())
        )
        if total_width <= 0:
            return

        left_min = self.LEFT_MIN_WIDTH
        right_min = self.RIGHT_MIN_WIDTH

        if use_narrow:
            min_total = left_min + right_min
            total_width = max(total_width, min_total)
            left_width = max(left_min, int(total_width * 0.35))
            right_width = max(total_width - left_width, right_min)
            left_width = max(left_min, total_width - right_width)
        else:
            min_total = left_min + right_min
            total_width = max(total_width, min_total)
            extra = total_width - min_total
            weights = (4, 6)
            total_weight = sum(weights)
            left_width = left_min + int(extra * weights[0] / total_weight)
            right_width = total_width - left_width

        if use_narrow:
            self._modifier_editor_narrow.setStretchFactor(0, 3)
            self._modifier_editor_narrow.setStretchFactor(1, 7)
            self._modifier_editor_narrow.setSizes([left_width, right_width])
            total_height = self._modifier_editor_container.height() or self.height()
            if total_height > 0:
                upper_height = int(total_height * 0.5)
                self._modifier_editor_vertical.setSizes([upper_height, total_height - upper_height])
        else:
            self._modifier_editor_wide.setStretchFactor(0, 4)
            self._modifier_editor_wide.setStretchFactor(1, 6)
            self._modifier_editor_wide.setSizes([left_width, total_width - left_width])
            total_height = self._modifier_editor_container.height() or self.height()
            if total_height > 0:
                upper_height = int(total_height * 0.58)
                self._modifier_editor_midright.setSizes([upper_height, total_height - upper_height])

    def _update_requirement_editor_layout(self) -> None:
        if (
            self._requirement_editor_container is None
            or self._requirement_editor_wide is None
            or self._requirement_editor_narrow is None
        ):
            return
        width = (
            self._scroll_area.viewport().width()
            if self._scroll_area is not None
            else (self._requirement_editor_container.width() or self.width())
        )
        use_narrow = width < self.WIDE_LAYOUT_MIN_WIDTH
        if use_narrow != self._requirement_editor_narrow_active:
            self._requirement_editor_narrow_active = use_narrow
            self._apply_requirement_editor_layout(use_narrow)
        self._apply_requirement_editor_sizes(use_narrow)

    def _force_requirement_editor_layout(self) -> None:
        if self._requirement_editor_container is None:
            return
        width = (
            self._scroll_area.viewport().width()
            if self._scroll_area is not None
            else (self._requirement_editor_container.width() or self.width())
        )
        use_narrow = width < self.WIDE_LAYOUT_MIN_WIDTH
        self._requirement_editor_narrow_active = not use_narrow
        self._apply_requirement_editor_layout(use_narrow)
        self._apply_requirement_editor_sizes(use_narrow)

    def _apply_requirement_editor_layout(self, use_narrow: bool) -> None:
        if (
            self._requirement_left_panel is None
            or self._requirement_middle_panel is None
            or self._requirement_right_panel is None
            or self._requirement_editor_wide is None
            or self._requirement_editor_narrow is None
            or self._requirement_editor_midright is None
            or self._requirement_editor_vertical is None
        ):
            return

        left = self._requirement_left_panel
        middle = self._requirement_middle_panel
        right = self._requirement_right_panel

        self._clear_splitter(self._requirement_editor_wide)
        self._clear_splitter(self._requirement_editor_narrow)
        self._clear_splitter(self._requirement_editor_midright)
        self._clear_splitter(self._requirement_editor_vertical)

        left.setParent(None)
        middle.setParent(None)
        right.setParent(None)

        if use_narrow:
            self._requirement_editor_wide.hide()
            self._requirement_editor_narrow.show()
            self._requirement_editor_narrow.addWidget(left)
            self._requirement_editor_narrow.addWidget(self._requirement_editor_vertical)
            self._requirement_editor_vertical.addWidget(middle)
            self._requirement_editor_vertical.addWidget(right)
            self._requirement_editor_narrow.setChildrenCollapsible(False)
            self._requirement_editor_vertical.setChildrenCollapsible(False)
        else:
            self._requirement_editor_narrow.hide()
            self._requirement_editor_wide.show()
            self._requirement_editor_wide.addWidget(left)
            self._requirement_editor_wide.addWidget(self._requirement_editor_midright)
            self._requirement_editor_midright.addWidget(middle)
            self._requirement_editor_midright.addWidget(right)
            self._requirement_editor_wide.setChildrenCollapsible(False)
            self._requirement_editor_midright.setChildrenCollapsible(False)

    def _apply_requirement_editor_sizes(self, use_narrow: bool) -> None:
        if not all([
            self._requirement_editor_container,
            self._requirement_editor_wide,
            self._requirement_editor_narrow,
            self._requirement_editor_midright,
            self._requirement_editor_vertical,
        ]):
            return

        total_width = (
            self._scroll_area.viewport().width()
            if self._scroll_area is not None
            else (self._requirement_editor_container.width() or self.width())
        )
        if total_width <= 0:
            return

        left_min = self.LEFT_MIN_WIDTH
        right_min = self.RIGHT_MIN_WIDTH

        if use_narrow:
            min_total = left_min + right_min
            total_width = max(total_width, min_total)
            left_width = max(left_min, int(total_width * 0.35))
            right_width = max(total_width - left_width, right_min)
            left_width = max(left_min, total_width - right_width)
        else:
            min_total = left_min + right_min
            total_width = max(total_width, min_total)
            extra = total_width - min_total
            weights = (4, 6)
            total_weight = sum(weights)
            left_width = left_min + int(extra * weights[0] / total_weight)
            right_width = total_width - left_width

        if use_narrow:
            self._requirement_editor_narrow.setStretchFactor(0, 3)
            self._requirement_editor_narrow.setStretchFactor(1, 7)
            self._requirement_editor_narrow.setSizes([left_width, right_width])
            total_height = self._requirement_editor_container.height() or self.height()
            if total_height > 0:
                upper_height = int(total_height * 0.5)
                self._requirement_editor_vertical.setSizes([upper_height, total_height - upper_height])
        else:
            self._requirement_editor_wide.setStretchFactor(0, 4)
            self._requirement_editor_wide.setStretchFactor(1, 6)
            self._requirement_editor_wide.setSizes([left_width, total_width - left_width])
            total_height = self._requirement_editor_container.height() or self.height()
            if total_height > 0:
                upper_height = int(total_height * 0.58)
                self._requirement_editor_midright.setSizes([upper_height, total_height - upper_height])

    def _clear_splitter(self, splitter: QSplitter) -> None:
        while splitter.count():
            widget = splitter.widget(0)
            if widget is None:
                break
            widget.setParent(None)

    def _set_combo_text(self, combo: QComboBox, text: str) -> None:
        combo.blockSignals(True)
        if combo in (self._owner_reqset_input, self._subject_reqset_input):
            if combo.isEditable() and combo.lineEdit() is not None:
                combo.setCurrentIndex(-1)
                combo.lineEdit().setText(text or "")
            else:
                combo.setCurrentIndex(-1)
                combo.setEditText(text or "")
        else:
            if not text:
                combo.setCurrentIndex(-1)
                combo.setEditText("")
            else:
                combo.setEditText(text)
                combo.setCurrentText(text)
        combo.blockSignals(False)

    def _set_table_min_rows(self, table: QTableWidget, rows: int) -> None:
        if table is None or rows <= 0:
            return
        header_height = table.horizontalHeader().sizeHint().height()
        row_height = table.verticalHeader().defaultSectionSize()
        frame = table.frameWidth() * 2
        table.setMinimumHeight(header_height + row_height * rows + frame + 2)

    def _set_list_min_rows(self, list_widget: QListWidget, rows: int) -> None:
        if list_widget is None or rows <= 0:
            return
        row_height = list_widget.sizeHintForRow(0)
        if row_height <= 0:
            row_height = max(list_widget.fontMetrics().height() + 10, 24)
        frame = list_widget.frameWidth() * 2
        list_widget.setMinimumHeight(row_height * rows + frame + 2)

    def _get_selected_row(self, table: QTableWidget | None) -> int:
        if table is None:
            return -1
        if table.currentRow() is not None and table.currentRow() >= 0:
            return table.currentRow()
        if table.selectionModel() is None:
            return -1
        selected = table.selectionModel().selectedRows()
        return selected[0].row() if selected else -1

    # -------------------- Modifier List Panel --------------------
    def _build_modifier_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._handle_add_modifier)
        copy_btn = QPushButton("复制")
        copy_btn.clicked.connect(self._handle_duplicate_modifier)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._handle_delete_modifier)
        button_row.addWidget(add_btn)
        button_row.addWidget(copy_btn)
        button_row.addWidget(del_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["名称", "ModifierId"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(90)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.itemSelectionChanged.connect(self._on_modifier_selected)
        table.itemDoubleClicked.connect(self._on_modifier_row_double_clicked)
        table.currentCellChanged.connect(lambda *_args: self._on_modifier_selected())
        table.setMinimumWidth(self.LEFT_MIN_WIDTH)
        self._modifier_list = table
        layout.addWidget(table, 1)

        return panel

    # -------------------- Modifier Detail Panel --------------------
    def _build_modifier_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        def compact_button(text: str, width: int) -> QPushButton:
            button = QPushButton(text)
            button.setFixedHeight(20)
            button.setMinimumWidth(width)
            button.setMaximumWidth(width)
            button.setStyleSheet("font-size: 11px; padding: 0px 2px;")
            return button

        prefix_row = QHBoxLayout()
        prefix_row.addWidget(QLabel("前缀1"))
        self._prefix_input = QLineEdit()
        fm = self._prefix_input.fontMetrics()
        self._prefix_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._prefix_input.setPlaceholderText("可选前缀")
        prefix_row.addWidget(self._prefix_input, 1)
        prefix_row.addWidget(QLabel("前缀2"))
        self._prefix2_input = QLineEdit()
        fm = self._prefix2_input.fontMetrics()
        self._prefix2_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._prefix2_input.setPlaceholderText("可选前缀")
        prefix_row.addWidget(self._prefix2_input, 1)
        layout.addLayout(prefix_row)

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("ModifierId"))
        self._modifier_id_input = QLineEdit()
        fm = self._modifier_id_input.fontMetrics()
        self._modifier_id_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._modifier_id_input.textChanged.connect(self._update_modifier_list_label)
        self._modifier_id_input.textChanged.connect(lambda _t: self._on_modifier_editor_changed("modifier_id"))
        id_row.addWidget(self._modifier_id_input, 1)
        auto_btn = compact_button("自动补全", 64)
        auto_btn.clicked.connect(self._apply_modifier_id_default)
        id_row.addWidget(auto_btn)
        layout.addLayout(id_row)

        comment_row = QHBoxLayout()
        comment_row.addWidget(QLabel("中文注释"))
        self._comment_input = QLineEdit()
        fm = self._comment_input.fontMetrics()
        self._comment_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._comment_input.textChanged.connect(self._update_modifier_list_label)
        self._comment_input.textChanged.connect(lambda _t: self._on_modifier_editor_changed("comment"))
        comment_row.addWidget(self._comment_input, 1)
        layout.addLayout(comment_row)

        modtype_row = QHBoxLayout()
        modtype_btn = compact_button("搜索", 44)
        modtype_btn.clicked.connect(self._open_modifier_type_dialog)
        modtype_row.addWidget(modtype_btn)
        modtype_row.addWidget(QLabel("ModifierType"))
        self._modifier_type_combo = QComboBox()
        self._modifier_type_combo.setEditable(True)
        self._modifier_type_combo.addItems(sorted(self._modifier_meta_index.keys()))
        self._modifier_type_combo.currentTextChanged.connect(self._on_modifier_type_changed)
        self._modifier_type_combo.currentTextChanged.connect(lambda _t: self._on_modifier_editor_changed("modifier_type"))
        modtype_row.addWidget(self._modifier_type_combo, 1)
        layout.addLayout(modtype_row)

        effect_row = QHBoxLayout()
        effect_btn = compact_button("搜索", 44)
        effect_btn.clicked.connect(self._open_effect_type_dialog)
        effect_row.addWidget(effect_btn)
        effect_row.addWidget(QLabel("EffectType"))
        self._effect_type_combo = QComboBox()
        self._effect_type_combo.setEditable(True)
        self._effect_type_combo.addItems(self._effect_types)
        self._effect_type_combo.currentTextChanged.connect(self._on_effect_type_changed)
        self._effect_type_combo.currentTextChanged.connect(lambda _t: self._on_modifier_editor_changed("effect_type"))
        effect_row.addWidget(self._effect_type_combo, 1)
        layout.addLayout(effect_row)

        collection_row = QHBoxLayout()
        collection_row.addWidget(QLabel("CollectionType"))
        self._collection_type_combo = QComboBox()
        self._collection_type_combo.setEditable(True)
        self._collection_type_combo.addItems(self._collection_types)
        self._collection_type_combo.currentTextChanged.connect(lambda _t: self._on_modifier_editor_changed("collection_type"))
        collection_row.addWidget(self._collection_type_combo, 1)
        layout.addLayout(collection_row)

        owner_req_row = QHBoxLayout()
        owner_req_row.addWidget(QLabel("OwnerRequirementSetId"))
        owner_req_input = QLineEdit()
        fm = owner_req_input.fontMetrics()
        owner_req_input.setMinimumHeight(max(fm.height() + 12, 24))
        owner_req_input.setPlaceholderText("可手动输入或从下拉选择")
        owner_req_input.textChanged.connect(lambda _t: self._on_modifier_editor_changed("owner_reqset"))
        self._owner_reqset_input = owner_req_input
        owner_req_row.addWidget(owner_req_input, 1)
        owner_req_menu = QMenu(self)
        owner_req_btn = QToolButton()
        owner_req_btn.setText("搜索")
        owner_req_btn.setToolTip("搜索并选择条件集")
        owner_req_btn.clicked.connect(lambda: self._open_reqset_search_dialog("owner"))
        owner_req_btn.setFixedWidth(52)
        self._owner_reqset_menu = owner_req_menu
        self._owner_reqset_btn = owner_req_btn
        owner_req_row.addWidget(owner_req_btn)
        layout.addLayout(owner_req_row)

        subject_req_row = QHBoxLayout()
        subject_req_row.addWidget(QLabel("SubjectRequirementSetId"))
        subject_req_input = QLineEdit()
        fm = subject_req_input.fontMetrics()
        subject_req_input.setMinimumHeight(max(fm.height() + 12, 24))
        subject_req_input.setPlaceholderText("可手动输入或从下拉选择")
        subject_req_input.textChanged.connect(lambda _t: self._on_modifier_editor_changed("subject_reqset"))
        self._subject_reqset_input = subject_req_input
        subject_req_row.addWidget(subject_req_input, 1)
        subject_req_menu = QMenu(self)
        subject_req_btn = QToolButton()
        subject_req_btn.setText("搜索")
        subject_req_btn.setToolTip("搜索并选择条件集")
        subject_req_btn.clicked.connect(lambda: self._open_reqset_search_dialog("subject"))
        subject_req_btn.setFixedWidth(52)
        self._subject_reqset_menu = subject_req_menu
        self._subject_reqset_btn = subject_req_btn
        subject_req_row.addWidget(subject_req_btn)
        layout.addLayout(subject_req_row)

        flags_row = QHBoxLayout()
        self._run_once_cb = QCheckBox("RunOnce")
        self._new_only_cb = QCheckBox("NewOnly")
        self._permanent_cb = QCheckBox("Permanent")
        self._run_once_cb.stateChanged.connect(lambda _v: self._on_modifier_editor_changed("run_once"))
        self._new_only_cb.stateChanged.connect(lambda _v: self._on_modifier_editor_changed("new_only"))
        self._permanent_cb.stateChanged.connect(lambda _v: self._on_modifier_editor_changed("permanent"))
        flags_row.addWidget(self._run_once_cb)
        flags_row.addWidget(self._new_only_cb)
        flags_row.addWidget(self._permanent_cb)
        flags_row.addStretch(1)
        layout.addLayout(flags_row)

        stack_row = QHBoxLayout()
        stack_row.addWidget(QLabel("OwnerStackLimit"))
        self._owner_stack_spin = QSpinBox()
        self._owner_stack_spin.setRange(-999999, 999999)
        self._owner_stack_spin.valueChanged.connect(lambda _v: self._on_modifier_editor_changed("owner_stack_limit"))
        stack_row.addWidget(self._owner_stack_spin)
        stack_row.addWidget(QLabel("SubjectStackLimit"))
        self._subject_stack_spin = QSpinBox()
        self._subject_stack_spin.setRange(-999999, 999999)
        self._subject_stack_spin.valueChanged.connect(lambda _v: self._on_modifier_editor_changed("subject_stack_limit"))
        stack_row.addWidget(self._subject_stack_spin)
        stack_row.addStretch(1)
        layout.addLayout(stack_row)

        layout.addStretch(1)
        return panel

    # -------------------- Modifier Param Panel --------------------
    def _build_modifier_param_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_row = QHBoxLayout()
        add_btn = QPushButton("＋ 添加参数")
        add_btn.clicked.connect(lambda: self._append_param_row(""))
        self._param_add_btn = add_btn
        del_btn = QPushButton("－ 删除参数")
        del_btn.clicked.connect(self._remove_selected_param_rows)
        self._param_del_btn = del_btn
        button_row.addWidget(add_btn)
        button_row.addWidget(del_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["参数名字", "参数值"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(160)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setMinimumWidth(self.RIGHT_MIN_WIDTH)
        self._set_table_min_rows(table, 4)
        self._param_table = table
        layout.addWidget(table, 1)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)
        preview_layout.addWidget(QLabel("ModifierStrings.Text（Context 固定为 Preview）"))

        preview_text = QPlainTextEdit()
        preview_text.setPlaceholderText("填写：+{1_Amount} 来自XXX 或 +{Property}来自XXX")
        preview_text.setFixedHeight(80)
        preview_text.textChanged.connect(lambda: self._on_modifier_editor_changed("preview_text"))
        self._modifier_preview_text = preview_text
        preview_layout.addWidget(preview_text)

        preview_tip = QLabel("提示：仅在 EffectType = EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER 时生效。")
        preview_tip.setWordWrap(True)
        preview_tip.setStyleSheet("color: #64748b;")
        preview_layout.addWidget(preview_tip)

        preview_container.setVisible(False)
        self._modifier_preview_container = preview_container
        layout.addWidget(preview_container)
        return panel

    @staticmethod
    def _supports_modifier_preview_string(effect_type: str | None) -> bool:
        return str(effect_type or "").strip().upper() == "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER"

    def _sync_modifier_preview_editor_visibility(self) -> None:
        if self._modifier_preview_container is None:
            return
        effect_text = self._effect_type_combo.currentText().strip() if self._effect_type_combo is not None else ""
        self._modifier_preview_container.setVisible(self._supports_modifier_preview_string(effect_text))

    # -------------------- Part 4: Requirement Editor --------------------
    def _build_requirement_editor_section(self) -> QGroupBox:
        group = QGroupBox("条件集与条件")
        group.setMinimumHeight(0)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        reqset_group = QGroupBox("条件集对象")
        reqset_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        reqset_layout = QVBoxLayout(reqset_group)
        reqset_layout.setContentsMargins(6, 6, 6, 6)
        reqset_layout.addWidget(self._build_reqset_panel(), 1)
        layout.addWidget(reqset_group)

        req_group = QGroupBox("条件对象")
        req_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        req_layout = QVBoxLayout(req_group)
        req_layout.setContentsMargins(6, 6, 6, 6)

        self._requirement_editor_container = QWidget()
        self._requirement_editor_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_layout = QVBoxLayout(self._requirement_editor_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._requirement_left_panel = self._build_requirement_list_panel()
        self._requirement_middle_panel = self._build_requirement_detail_panel()
        self._requirement_right_panel = self._build_requirement_param_panel()

        self._requirement_left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._requirement_middle_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._requirement_right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._requirement_editor_wide = self._build_requirement_editor_wide()
        self._requirement_editor_narrow = self._build_requirement_editor_narrow()
        self._requirement_editor_wide.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._requirement_editor_narrow.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        container_layout.addWidget(self._requirement_editor_wide, 1)
        container_layout.addWidget(self._requirement_editor_narrow, 1)
        self._requirement_editor_narrow.hide()
        self._apply_requirement_editor_layout(use_narrow=False)
        QTimer.singleShot(0, self._force_requirement_editor_layout)

        req_layout.addWidget(self._requirement_editor_container, 1)
        layout.addWidget(req_group, 1)

        self._update_reqset_section_state()
        self._set_reqset_editor_enabled(False)
        self._set_requirement_editor_enabled(False)
        return group

    def _build_requirement_editor_wide(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        mid_right = QSplitter(Qt.Orientation.Vertical)
        mid_right.setStretchFactor(0, 3)
        mid_right.setStretchFactor(1, 2)
        self._requirement_editor_midright = mid_right
        return splitter

    def _build_requirement_editor_narrow(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.setStretchFactor(0, 1)
        vertical.setStretchFactor(1, 1)
        self._requirement_editor_vertical = vertical
        return splitter

    def _build_reqset_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("条件集对象"))
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._handle_add_reqset)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._handle_delete_reqset)
        self._reqset_delete_btn = del_btn
        toggle_btn = QPushButton("折叠")
        toggle_btn.setCheckable(True)
        toggle_btn.clicked.connect(self._toggle_reqset_section)
        self._reqset_toggle_btn = toggle_btn
        header_row.addWidget(add_btn)
        header_row.addWidget(del_btn)
        header_row.addStretch(1)
        header_row.addWidget(toggle_btn)
        layout.addLayout(header_row)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["名称", "RequirementSetId"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(90)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.itemSelectionChanged.connect(self._on_reqset_selected)
        table.currentCellChanged.connect(lambda *_args: self._on_reqset_selected())
        table.setMinimumWidth(self.LEFT_MIN_WIDTH)
        self._reqset_list = table
        left_layout.addWidget(table, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("RequirementSetId"))
        self._reqset_id_input = QLineEdit()
        fm = self._reqset_id_input.fontMetrics()
        self._reqset_id_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._reqset_id_input.textChanged.connect(self._update_reqset_list_label)
        self._reqset_id_input.textChanged.connect(lambda _t: self._on_reqset_editor_changed("requirement_set_id"))
        id_row.addWidget(self._reqset_id_input, 1)
        reqset_auto_btn = QPushButton("根据绑定条件补全")
        reqset_auto_btn.setFixedHeight(20)
        reqset_auto_btn.setMinimumWidth(120)
        reqset_auto_btn.setMaximumWidth(120)
        reqset_auto_btn.setStyleSheet("font-size: 11px; padding: 0px 2px;")
        reqset_auto_btn.clicked.connect(self._apply_reqset_id_from_bindings)
        id_row.addWidget(reqset_auto_btn)
        right_layout.addLayout(id_row)

        comment_row = QHBoxLayout()
        comment_row.addWidget(QLabel("中文注释"))
        self._reqset_comment_input = QLineEdit()
        fm = self._reqset_comment_input.fontMetrics()
        self._reqset_comment_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._reqset_comment_input.textChanged.connect(self._update_reqset_list_label)
        self._reqset_comment_input.textChanged.connect(lambda _t: self._on_reqset_editor_changed("comment"))
        comment_row.addWidget(self._reqset_comment_input, 1)
        right_layout.addLayout(comment_row)

        logic_row = QHBoxLayout()
        logic_row.addWidget(QLabel("逻辑"))
        self._reqset_logic_all = QCheckBox("ALL")
        self._reqset_logic_any = QCheckBox("ANY")
        self._reqset_logic_all.setChecked(True)
        self._reqset_logic_all.toggled.connect(lambda checked: self._sync_reqset_logic(checked, True))
        self._reqset_logic_any.toggled.connect(lambda checked: self._sync_reqset_logic(checked, False))
        self._reqset_logic_all.toggled.connect(lambda _v: self._on_reqset_editor_changed("logic"))
        self._reqset_logic_any.toggled.connect(lambda _v: self._on_reqset_editor_changed("logic"))
        logic_row.addWidget(self._reqset_logic_all)
        logic_row.addWidget(self._reqset_logic_any)
        logic_row.addStretch(1)
        right_layout.addLayout(logic_row)

        bind_row = QHBoxLayout()
        bind_row.addWidget(QLabel("绑定条件"))
        bind_add = QPushButton("绑定条件")
        bind_add.clicked.connect(self._bind_selected_requirement)
        self._reqset_bind_add_btn = bind_add
        bind_del = QPushButton("删除条件")
        bind_del.clicked.connect(self._unbind_selected_requirement)
        self._reqset_bind_del_btn = bind_del
        bind_row.addWidget(bind_add)
        bind_row.addWidget(bind_del)
        bind_row.addStretch(1)
        right_layout.addLayout(bind_row)

        bind_list = QListWidget()
        bind_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        bind_list.itemSelectionChanged.connect(self._update_reqset_bind_buttons)
        self._set_list_min_rows(bind_list, 7)
        self._reqset_bind_list = bind_list
        right_layout.addWidget(bind_list, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setChildrenCollapsible(False)

        body_layout.addWidget(splitter, 1)
        layout.addWidget(body, 1)
        self._reqset_section_body = body
        return panel

    def _build_requirement_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._handle_add_requirement)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._handle_delete_requirement)
        button_row.addWidget(add_btn)
        button_row.addWidget(del_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["名称", "RequirementId"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(90)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.itemSelectionChanged.connect(self._on_requirement_selected)
        table.currentCellChanged.connect(lambda *_args: self._on_requirement_selected())
        table.setMinimumWidth(self.LEFT_MIN_WIDTH)
        self._set_table_min_rows(table, 3)
        self._req_list = table
        layout.addWidget(table, 1)
        return panel

    def _build_requirement_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        def compact_button(text: str, width: int) -> QPushButton:
            button = QPushButton(text)
            button.setFixedHeight(20)
            button.setMinimumWidth(width)
            button.setMaximumWidth(width)
            button.setStyleSheet("font-size: 11px; padding: 0px 2px;")
            return button

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("RequirementId"))
        self._req_id_input = QLineEdit()
        fm = self._req_id_input.fontMetrics()
        self._req_id_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._req_id_input.textChanged.connect(self._update_requirement_list_label)
        self._req_id_input.textChanged.connect(lambda _t: self._on_requirement_editor_changed("requirement_id"))
        id_row.addWidget(self._req_id_input, 1)
        req_auto_btn = compact_button("自动补全", 64)
        req_auto_btn.clicked.connect(self._apply_requirement_id_default)
        id_row.addWidget(req_auto_btn)
        layout.addLayout(id_row)

        comment_row = QHBoxLayout()
        comment_row.addWidget(QLabel("中文注释"))
        self._req_comment_input = QLineEdit()
        fm = self._req_comment_input.fontMetrics()
        self._req_comment_input.setMinimumHeight(max(fm.height() + 12, 24))
        self._req_comment_input.textChanged.connect(self._update_requirement_list_label)
        self._req_comment_input.textChanged.connect(lambda _t: self._on_requirement_editor_changed("comment"))
        comment_row.addWidget(self._req_comment_input, 1)
        layout.addLayout(comment_row)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("RequirementType"))
        self._req_type_combo = QComboBox()
        self._req_type_combo.setEditable(True)
        self._req_type_combo.addItems(self._requirement_types)
        self._req_type_combo.currentTextChanged.connect(self._on_requirement_type_changed)
        self._req_type_combo.currentTextChanged.connect(lambda _t: self._on_requirement_editor_changed("requirement_type"))
        type_row.addWidget(self._req_type_combo, 1)
        search_btn = compact_button("搜索", 44)
        search_btn.clicked.connect(self._open_requirement_type_dialog)
        self._req_type_search_btn = search_btn
        type_row.addWidget(search_btn)
        layout.addLayout(type_row)

        num_row = QHBoxLayout()
        num_row.addWidget(QLabel("Likeliness"))
        self._req_likeliness_spin = QSpinBox()
        self._req_likeliness_spin.setRange(-999999, 999999)
        self._req_likeliness_spin.valueChanged.connect(lambda _v: self._on_requirement_editor_changed("likeliness"))
        num_row.addWidget(self._req_likeliness_spin)
        num_row.addWidget(QLabel("Impact"))
        self._req_impact_spin = QSpinBox()
        self._req_impact_spin.setRange(-999999, 999999)
        self._req_impact_spin.valueChanged.connect(lambda _v: self._on_requirement_editor_changed("impact"))
        num_row.addWidget(self._req_impact_spin)
        num_row.addWidget(QLabel("ProgressWeight"))
        self._req_progress_spin = QSpinBox()
        self._req_progress_spin.setRange(-999999, 999999)
        self._req_progress_spin.setValue(1)
        self._req_progress_spin.valueChanged.connect(lambda _v: self._on_requirement_editor_changed("progress_weight"))
        num_row.addWidget(self._req_progress_spin)
        num_row.addStretch(1)
        layout.addLayout(num_row)

        flags_row = QHBoxLayout()
        self._req_inverse_cb = QCheckBox("Inverse")
        self._req_reverse_cb = QCheckBox("Reverse")
        self._req_persistent_cb = QCheckBox("Persistent")
        self._req_triggered_cb = QCheckBox("Triggered")
        self._req_inverse_cb.stateChanged.connect(lambda _v: self._on_requirement_editor_changed("inverse"))
        self._req_reverse_cb.stateChanged.connect(lambda _v: self._on_requirement_editor_changed("reverse"))
        self._req_persistent_cb.stateChanged.connect(lambda _v: self._on_requirement_editor_changed("persistent"))
        self._req_triggered_cb.stateChanged.connect(lambda _v: self._on_requirement_editor_changed("triggered"))
        for cb in (
            self._req_inverse_cb,
            self._req_reverse_cb,
            self._req_persistent_cb,
            self._req_triggered_cb,
        ):
            flags_row.addWidget(cb)
        flags_row.addStretch(1)
        layout.addLayout(flags_row)

        layout.addStretch(1)
        return panel

    def _build_requirement_param_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_row = QHBoxLayout()
        add_btn = QPushButton("＋ 添加参数")
        add_btn.clicked.connect(lambda: self._append_req_param_row(""))
        self._req_param_add_btn = add_btn
        del_btn = QPushButton("－ 删除参数")
        del_btn.clicked.connect(self._remove_selected_req_param_rows)
        self._req_param_del_btn = del_btn
        button_row.addWidget(add_btn)
        button_row.addWidget(del_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["参数名字", "参数值"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(160)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setMinimumWidth(self.RIGHT_MIN_WIDTH)
        self._set_table_min_rows(table, 4)
        self._req_param_table = table
        layout.addWidget(table, 1)
        return panel

    # -------------------- Owner Handlers --------------------
    def _handle_add_owner(self) -> None:
        if self._owner_table_combo is None or self._owner_type_input is None:
            return
        table_name = self._owner_table_combo.currentText().strip()
        type_name = self._owner_type_input.text().strip()
        if not table_name:
            QMessageBox.warning(self, "提示", "请选择表名")
            return
        if not type_name:
            QMessageBox.warning(self, "提示", "请输入类型名")
            return
        for owner in self._owners:
            if owner.table_name == table_name and owner.type_name == type_name:
                QMessageBox.warning(self, "提示", "该所有者已存在")
                return
        type_column = OWNER_TABLE_TYPE_MAP.get(table_name, "")
        record = OwnerRecord(table_name=table_name, type_column=type_column, type_name=type_name, display_name=type_name)
        self._owners.append(record)
        self._owner_type_input.clear()
        self._refresh_owner_tree(select_index=len(self._owners) - 1)
        self._update_owner_section_state()

    def _handle_delete_owner(self) -> None:
        if self._selected_owner_index < 0 or self._selected_owner_index >= len(self._owners):
            return
        self._owners.pop(self._selected_owner_index)
        self._selected_owner_index = -1
        self._refresh_owner_tree()
        self._update_owner_section_state()

    def _refresh_owner_tree(self, select_index: int | None = None) -> None:
        if self._owner_tree is None:
            return
        self._owner_tree.clear()
        table_groups: Dict[str, QTreeWidgetItem] = {}
        for idx, owner in enumerate(self._owners):
            group = table_groups.get(owner.table_name)
            if group is None:
                group = QTreeWidgetItem([owner.table_name])
                group.setData(0, Qt.ItemDataRole.UserRole, None)
                table_groups[owner.table_name] = group
                self._owner_tree.addTopLevelItem(group)
            display_text = self._owner_display_text(owner)
            child = QTreeWidgetItem([display_text or owner.type_name])
            child.setToolTip(0, owner.type_name)
            child.setData(0, Qt.ItemDataRole.UserRole, idx)
            group.addChild(child)
        self._owner_tree.expandAll()
        if select_index is not None and 0 <= select_index < len(self._owners):
            self._select_owner_in_tree(select_index)
        else:
            self._selected_owner_index = -1
        self._update_owner_selected_label()
        self._refresh_owner_binding_table()

    def _select_owner_in_tree(self, index: int) -> None:
        if self._owner_tree is None:
            return
        root_count = self._owner_tree.topLevelItemCount()
        for i in range(root_count):
            parent = self._owner_tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.data(0, Qt.ItemDataRole.UserRole) == index:
                    self._owner_tree.setCurrentItem(child)
                    return

    def _on_owner_selected(self) -> None:
        if self._owner_tree is None:
            return
        item = self._owner_tree.currentItem()
        if item is None:
            self._selected_owner_index = -1
            self._refresh_owner_binding_table()
            return
        index = item.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            self._selected_owner_index = -1
        else:
            self._selected_owner_index = int(index)
        self._update_owner_selected_label()
        self._refresh_owner_binding_table()
        self._update_ability_buttons_state()

    def _find_unit_ability_record(self, ability_type: str) -> UnitAbilityRecord | None:
        clean_type = str(ability_type or "").strip()
        if not clean_type:
            return None
        for record in self._unit_ability_records:
            if record.unit_ability_type == clean_type:
                return record
        return None

    @staticmethod
    def _unit_ability_source_key(ability_type: str) -> str:
        return f"modifier_unit_ability:{str(ability_type or '').strip()}"

    def _upsert_unit_ability_record(self, record: UnitAbilityRecord) -> None:
        for index, existing in enumerate(self._unit_ability_records):
            if existing.unit_ability_type == record.unit_ability_type:
                self._unit_ability_records[index] = record
                return
        self._unit_ability_records.append(record)

    def _unit_ability_template_options(self) -> List[tuple[str, str]]:
        options: List[tuple[str, str]] = []
        for record in self._unit_ability_records:
            ability_type = str(record.unit_ability_type or "").strip()
            if not ability_type:
                continue
            label = str(record.name_zh or "").strip()
            display = f"{label}" if label else ability_type
            options.append((display, ability_type))
        options.sort(key=lambda item: item[1])
        return options

    def _refresh_ability_type_param_widgets(self) -> None:
        if self._param_table is None:
            return
        options = self._unit_ability_template_options()
        for row in range(self._param_table.rowCount()):
            name_widget = self._param_table.cellWidget(row, 0)
            if not isinstance(name_widget, QLineEdit):
                continue
            if name_widget.text().strip() != "AbilityType":
                continue
            value_widget = self._param_table.cellWidget(row, 1)
            if isinstance(value_widget, BaseTemplateWidget) and hasattr(value_widget, "set_options"):
                setter = getattr(value_widget, "set_options")
                try:
                    setter(options, preserve_text=True)
                except TypeError:
                    setter(options)

    def _workspace_prefix_infix(self) -> tuple[str, int]:
        sections: Dict[str, object] | None = None
        if callable(getattr(self, "_owner_sources_provider", None)):
            try:
                candidate = self._owner_sources_provider()
                if isinstance(candidate, dict):
                    sections = candidate
            except Exception:
                sections = None

        if not isinstance(sections, dict):
            return "", 0

        base_section = sections.get("基础信息")
        payload: Dict[str, object] | None = None
        if isinstance(base_section, dict):
            data = base_section.get("data")
            if isinstance(data, dict):
                payload = data
            else:
                payload = base_section

        if not isinstance(payload, dict):
            return "", 0

        shared = payload.get("shared_workspace_params")
        if not isinstance(shared, dict):
            shared = {}

        prefix = re.sub(r"[^A-Z0-9_]", "", str(shared.get("prefix") or "").strip().upper())
        try:
            infix = max(0, int(shared.get("infix", 0)))
        except (TypeError, ValueError):
            infix = 0
        return prefix, infix

    def _ensure_owner_for_unit_ability(self, ability_type: str, ability_name: str = "") -> None:
        clean_type = str(ability_type or "").strip()
        if not clean_type:
            return

        for index, owner in enumerate(self._owners):
            if owner.table_name == "UnitAbilityModifiers" and owner.type_name == clean_type:
                if ability_name.strip():
                    owner.display_name = ability_name.strip()
                if not owner.source_key:
                    owner.source_key = self._unit_ability_source_key(clean_type)
                self._refresh_owner_tree(select_index=index)
                return

        self._owners.append(
            OwnerRecord(
                table_name="UnitAbilityModifiers",
                type_column=OWNER_TABLE_TYPE_MAP.get("UnitAbilityModifiers", "UnitAbilityType"),
                type_name=clean_type,
                display_name=ability_name.strip() or clean_type,
                source_key=self._unit_ability_source_key(clean_type),
            )
        )
        self._refresh_owner_tree(select_index=len(self._owners) - 1)

    def _handle_add_unit_ability(self) -> None:
        if self._owner_table_combo is None:
            return
        if self._owner_table_combo.currentText().strip() != "UnitAbilityModifiers":
            QMessageBox.information(self, "提示", "仅在表名为 UnitAbilityModifiers 时可新增Ability。")
            return

        prefix, infix = self._workspace_prefix_infix()
        dialog = UnitAbilityEditorDialog(self, prefix=prefix, infix=infix)
        if self._owner_type_input is not None:
            seed_type = self._owner_type_input.text().strip()
            if seed_type:
                dialog.set_record(UnitAbilityRecord(unit_ability_type=seed_type))

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        saved = dialog.saved_record()
        if saved is None:
            return

        self._upsert_unit_ability_record(saved)
        self._ensure_owner_for_unit_ability(saved.unit_ability_type, saved.name_zh)
        if self._owner_type_input is not None:
            self._owner_type_input.setText(saved.unit_ability_type)
        self._refresh_ability_type_param_widgets()
        self._update_owner_section_state()

    def _handle_edit_selected_unit_ability(self) -> None:
        if not (0 <= self._selected_owner_index < len(self._owners)):
            QMessageBox.information(self, "提示", "请先选择一个 UnitAbilityModifiers 所有者。")
            return
        owner = self._owners[self._selected_owner_index]
        if owner.table_name != "UnitAbilityModifiers":
            QMessageBox.information(self, "提示", "当前所选所有者不是 UnitAbilityModifiers。")
            return

        existing = self._find_unit_ability_record(owner.type_name)
        if existing is None:
            QMessageBox.information(self, "提示", "该 Ability 不是在修改器页新增的，暂不支持回填编辑。")
            return

        prefix, infix = self._workspace_prefix_infix()
        dialog = UnitAbilityEditorDialog(self, prefix=prefix, infix=infix)
        dialog.set_record(existing)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        saved = dialog.saved_record()
        if saved is None:
            return

        old_type = existing.unit_ability_type
        self._upsert_unit_ability_record(saved)
        if old_type != saved.unit_ability_type:
            self._unit_ability_records = [
                row for row in self._unit_ability_records
                if row.unit_ability_type != old_type
            ]
            self._upsert_unit_ability_record(saved)
            owner.type_name = saved.unit_ability_type
            owner.source_key = self._unit_ability_source_key(saved.unit_ability_type)
        owner.display_name = saved.name_zh.strip() or saved.unit_ability_type
        self._refresh_owner_tree(select_index=self._selected_owner_index)
        self._refresh_ability_type_param_widgets()
        self._update_owner_section_state()

    def _on_owner_bind_selection_changed(self) -> None:
        if self._owner_bind_table is not None:
            selected = self._owner_bind_table.selectionModel().selectedRows()
            if selected:
                self._owner_bind_selected_row = selected[0].row()
            elif self._owner_bind_table.rowCount() == 0:
                self._owner_bind_selected_row = -1
        self._update_owner_bind_buttons()
        self._update_owner_bind_compact_label()
        self._update_owner_attachment_editor_state()

    @staticmethod
    def _is_attachment_target_owner(owner: OwnerRecord | None) -> bool:
        return bool(owner is not None and owner.table_name == OWNER_TABLE_WITH_ATTACHMENT_TARGET)

    def _owner_binding_rows(self, owner: OwnerRecord) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        seen: set[str] = set()

        raw_bindings = owner.owner_bindings if isinstance(owner.owner_bindings, list) else []
        for entry in raw_bindings:
            if not isinstance(entry, dict):
                continue
            modifier_id = str(entry.get("modifier_id") or "").strip()
            if not modifier_id or modifier_id in seen:
                continue
            rows.append(
                {
                    "modifier_id": modifier_id,
                    "attachment_target_type": str(entry.get("attachment_target_type") or "").strip(),
                }
            )
            seen.add(modifier_id)

        raw_ids = owner.bound_modifier_ids if isinstance(owner.bound_modifier_ids, list) else []
        for modifier_id in raw_ids:
            clean_id = str(modifier_id or "").strip()
            if not clean_id or clean_id in seen:
                continue
            rows.append({"modifier_id": clean_id, "attachment_target_type": ""})
            seen.add(clean_id)

        owner.owner_bindings = rows
        owner.bound_modifier_ids = [row["modifier_id"] for row in rows]
        return rows

    def _set_owner_binding_rows(self, owner: OwnerRecord, rows: List[Dict[str, str]]) -> None:
        normalized: List[Dict[str, str]] = []
        seen: set[str] = set()
        for entry in rows:
            if not isinstance(entry, dict):
                continue
            modifier_id = str(entry.get("modifier_id") or "").strip()
            if not modifier_id or modifier_id in seen:
                continue
            normalized.append(
                {
                    "modifier_id": modifier_id,
                    "attachment_target_type": str(entry.get("attachment_target_type") or "").strip(),
                }
            )
            seen.add(modifier_id)
        owner.owner_bindings = normalized
        owner.bound_modifier_ids = [row["modifier_id"] for row in normalized]

    def _update_owner_attachment_editor_state(self) -> None:
        if self._owner_attachment_container is None or self._owner_attachment_combo is None:
            return
        owner = self._owners[self._selected_owner_index] if 0 <= self._selected_owner_index < len(self._owners) else None
        enabled = self._is_attachment_target_owner(owner)
        self._owner_attachment_container.setVisible(enabled)
        if not enabled:
            return

        value = ""
        if owner is not None and self._owner_bind_table is not None:
            selected = self._owner_bind_table.selectionModel().selectedRows()
            if selected:
                row_index = selected[0].row()
                rows = self._owner_binding_rows(owner)
                if 0 <= row_index < len(rows):
                    value = rows[row_index].get("attachment_target_type", "")

        self._loading_owner_attachment_editor = True
        try:
            if value and self._owner_attachment_combo.findText(value) < 0:
                self._owner_attachment_combo.addItem(value)
            self._owner_attachment_combo.setCurrentText(value)
        finally:
            self._loading_owner_attachment_editor = False

    def _on_owner_attachment_target_changed(self, text: str) -> None:
        if self._loading_owner_attachment_editor:
            return
        if self._owner_bind_table is None:
            return
        if not (0 <= self._selected_owner_index < len(self._owners)):
            return
        owner = self._owners[self._selected_owner_index]
        if not self._is_attachment_target_owner(owner):
            return

        selected = self._owner_bind_table.selectionModel().selectedRows()
        if not selected:
            return
        row_index = selected[0].row()
        rows = self._owner_binding_rows(owner)
        if row_index < 0 or row_index >= len(rows):
            return
        rows[row_index]["attachment_target_type"] = text.strip()
        self._set_owner_binding_rows(owner, rows)
        item = self._owner_bind_table.item(row_index, 1)
        if item is not None:
            item.setText(text.strip())

    def _trait_owner_category(self, owner: OwnerRecord) -> str:
        if owner.table_name != "TraitModifiers":
            return ""

        clean_source = str(owner.source_key or "").strip().lower()
        for source_prefix, label in TRAIT_SOURCE_PREFIX_LABELS.items():
            if clean_source.startswith(source_prefix):
                return label

        trait_type = str(owner.type_name or "").strip().upper()
        if trait_type.startswith("TRAIT_CIVILIZATION_"):
            return "文明"
        if trait_type.startswith("TRAIT_LEADER_"):
            return "领袖"
        return ""

    def _owner_display_text(self, owner: OwnerRecord) -> str:
        base_text = owner.display_name.strip() if owner.display_name else owner.type_name
        category = self._trait_owner_category(owner)
        if category:
            return f"[{category}] {base_text}"
        return base_text

    def _update_owner_selected_label(self) -> None:
        if self._owner_selected_label is None:
            return
        if 0 <= self._selected_owner_index < len(self._owners):
            owner = self._owners[self._selected_owner_index]
            display_text = self._owner_display_text(owner)
            self._owner_selected_label.setText(f"{owner.table_name} · {display_text} ({owner.type_name})")
            if self._owner_delete_btn is not None:
                self._owner_delete_btn.setEnabled(True)
        else:
            self._owner_selected_label.setText("未选择")
            if self._owner_delete_btn is not None:
                self._owner_delete_btn.setEnabled(False)
        self._update_owner_bind_buttons()

    def _refresh_owner_binding_table(self) -> None:
        if self._owner_bind_table is None:
            return
        self._owner_bind_table.setRowCount(0)
        if not (0 <= self._selected_owner_index < len(self._owners)):
            self._owner_bind_selected_row = -1
            self._owner_bind_table.setColumnCount(1)
            self._owner_bind_table.setHorizontalHeaderLabels(["绑定的 ModifierId"])
            self._owner_bind_table.horizontalHeader().setStretchLastSection(True)
            self._update_owner_bind_compact_label()
            self._update_owner_attachment_editor_state()
            self._update_owner_bind_buttons()
            return
        owner = self._owners[self._selected_owner_index]
        is_special_owner = self._is_attachment_target_owner(owner)
        if is_special_owner:
            self._owner_bind_table.setColumnCount(2)
            self._owner_bind_table.setHorizontalHeaderLabels(["绑定的 ModifierId", "AttachmentTargetType"])
            header = self._owner_bind_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        else:
            self._owner_bind_table.setColumnCount(1)
            self._owner_bind_table.setHorizontalHeaderLabels(["绑定的 ModifierId"])
            self._owner_bind_table.horizontalHeader().setStretchLastSection(True)

        for row_data in self._owner_binding_rows(owner):
            row = self._owner_bind_table.rowCount()
            self._owner_bind_table.insertRow(row)
            self._owner_bind_table.setItem(row, 0, QTableWidgetItem(row_data.get("modifier_id", "")))
            if is_special_owner:
                self._owner_bind_table.setItem(row, 1, QTableWidgetItem(row_data.get("attachment_target_type", "")))
        if self._owner_bind_table.rowCount() > 0:
            target_row = self._owner_bind_selected_row
            if target_row < 0 or target_row >= self._owner_bind_table.rowCount():
                target_row = 0
            self._owner_bind_selected_row = target_row
            self._owner_bind_table.selectRow(target_row)
        else:
            self._owner_bind_selected_row = -1
        self._update_owner_bind_compact_label()
        self._update_owner_attachment_editor_state()
        self._update_owner_bind_buttons()

    def _update_owner_bind_compact_label(self) -> None:
        if self._owner_bind_compact_label is None:
            return
        if not (0 <= self._selected_owner_index < len(self._owners)):
            self._owner_bind_compact_label.setText("（无）")
            self._owner_bind_compact_label.setToolTip("")
            return
        owner = self._owners[self._selected_owner_index]
        rows = self._owner_binding_rows(owner)
        if not rows:
            self._owner_bind_selected_row = -1
            self._owner_bind_compact_label.setText("（无）")
            self._owner_bind_compact_label.setToolTip("")
            return
        if self._owner_bind_selected_row < 0 or self._owner_bind_selected_row >= len(rows):
            self._owner_bind_selected_row = 0
        current_id = str(rows[self._owner_bind_selected_row].get("modifier_id") or "").strip()
        self._owner_bind_compact_label.setText(current_id or "（无）")
        self._owner_bind_compact_label.setToolTip(current_id)

    def _update_owner_bind_buttons(self) -> None:
        has_owner = 0 <= self._selected_owner_index < len(self._owners)
        has_modifier = self._get_current_modifier_id() is not None
        if self._owner_bind_add_btn is not None:
            self._owner_bind_add_btn.setEnabled(has_owner and has_modifier)
        if self._owner_bind_compact_add_btn is not None:
            self._owner_bind_compact_add_btn.setEnabled(has_owner and has_modifier)
        has_selection = False
        if has_owner:
            owner = self._owners[self._selected_owner_index]
            rows = self._owner_binding_rows(owner)
            has_selection = 0 <= self._owner_bind_selected_row < len(rows)
        if self._owner_bind_del_btn is not None and self._owner_bind_table is not None:
            selected_rows = self._owner_bind_table.selectionModel().selectedRows()
            if selected_rows:
                has_selection = True
            self._owner_bind_del_btn.setEnabled(has_owner and has_selection)
        if self._owner_bind_compact_del_btn is not None:
            self._owner_bind_compact_del_btn.setEnabled(has_owner and has_selection)

    def _handle_bind_modifier(self) -> None:
        if not (0 <= self._selected_owner_index < len(self._owners)):
            return
        modifier_id = self._get_current_modifier_id()
        if not modifier_id:
            QMessageBox.warning(self, "提示", "请先选择一个 ModifierId")
            return
        owner = self._owners[self._selected_owner_index]
        rows = self._owner_binding_rows(owner)
        attachment_target_type = ""
        if self._is_attachment_target_owner(owner):
            attachment_target_type = self._owner_attachment_combo.currentText().strip() if self._owner_attachment_combo is not None else ""
            if not attachment_target_type:
                QMessageBox.warning(self, "提示", "请先填写 AttachmentTargetType")
                return

        existing_index = next((i for i, row in enumerate(rows) if row.get("modifier_id") == modifier_id), -1)
        if existing_index >= 0:
            if self._is_attachment_target_owner(owner):
                rows[existing_index]["attachment_target_type"] = attachment_target_type
                self._set_owner_binding_rows(owner, rows)
                self._owner_bind_selected_row = existing_index
                self._refresh_owner_binding_table()
                self._owner_bind_table.selectRow(existing_index)
                QMessageBox.information(self, "提示", "该 ModifierId 已绑定，AttachmentTargetType 已更新")
                return
            self._owner_bind_selected_row = existing_index
            self._refresh_owner_binding_table()
            QMessageBox.information(self, "提示", "该 ModifierId 已绑定")
            return

        rows.append(
            {
                "modifier_id": modifier_id,
                "attachment_target_type": attachment_target_type,
            }
        )
        self._set_owner_binding_rows(owner, rows)
        self._owner_bind_selected_row = len(rows) - 1
        self._refresh_owner_binding_table()
        if self._owner_bind_table.rowCount() > 0:
            self._owner_bind_table.selectRow(self._owner_bind_table.rowCount() - 1)

    def _handle_unbind_modifier(self) -> None:
        if self._owner_bind_table is None:
            return
        if not (0 <= self._selected_owner_index < len(self._owners)):
            return
        owner = self._owners[self._selected_owner_index]
        row = -1
        selected = self._owner_bind_table.selectionModel().selectedRows()
        if selected:
            row = selected[0].row()
        elif 0 <= self._owner_bind_selected_row < len(self._owner_binding_rows(owner)):
            row = self._owner_bind_selected_row
        if row < 0:
            return
        rows = self._owner_binding_rows(owner)
        if 0 <= row < len(rows):
            rows.pop(row)
            self._set_owner_binding_rows(owner, rows)
        if rows:
            self._owner_bind_selected_row = min(max(row - 1, 0), len(rows) - 1)
        else:
            self._owner_bind_selected_row = -1
        self._refresh_owner_binding_table()

    # -------------------- Modifier Handlers --------------------
    def _handle_add_modifier(self) -> None:
        self._persist_current_modifier()
        modifier_id = self._build_modifier_id_default()
        record = ModifierRecord(
            modifier_id=modifier_id,
            modifier_type="",
            comment="",
            run_once=False,
            new_only=False,
            permanent=False,
            owner_stack_limit=0,
            subject_stack_limit=0,
        )
        self._modifiers.append(record)
        self._append_modifier_row(record)
        self._select_modifier_row(len(self._modifiers) - 1)
        if self._modifier_id_input is not None:
            if not self._modifier_id_input.text().strip():
                self._modifier_id_input.setText(modifier_id)
        self._set_modifier_editor_enabled(True)

    def _handle_duplicate_modifier(self) -> None:
        self._persist_current_modifier()
        row = self._get_selected_row(self._modifier_list)
        if row < 0 or row >= len(self._modifiers):
            QMessageBox.warning(self, "提示", "请先选择一个 Modifier")
            return
        source = self._modifiers[row]
        new_id = self._generate_duplicate_modifier_id(source.modifier_id)
        record = ModifierRecord(
            modifier_id=new_id,
            modifier_type=source.modifier_type,
            comment=source.comment,
            owner_reqset=source.owner_reqset,
            subject_reqset=source.subject_reqset,
            run_once=source.run_once,
            new_only=source.new_only,
            permanent=source.permanent,
            owner_stack_limit=source.owner_stack_limit,
            subject_stack_limit=source.subject_stack_limit,
            effect_type=source.effect_type,
            collection_type=source.collection_type,
            parameters=copy.deepcopy(source.parameters),
        )
        self._modifiers.append(record)
        self._append_modifier_row(record)
        self._select_modifier_row(len(self._modifiers) - 1)
        self._set_modifier_editor_enabled(True)

    def _handle_delete_modifier(self) -> None:
        self._persist_current_modifier()
        row = self._current_modifier_index
        if row < 0 or row >= len(self._modifiers):
            return
        removed = self._modifiers.pop(row)
        self._remove_modifier_row(row)
        self._remove_modifier_bindings(removed.modifier_id)
        next_row = min(row, len(self._modifiers) - 1)
        if next_row >= 0:
            self._select_modifier_row(next_row)
        else:
            self._current_modifier_index = -1
            self._clear_modifier_editor()
            self._set_modifier_editor_enabled(False)

    def _append_modifier_row(self, record: ModifierRecord) -> None:
        if self._modifier_list is None:
            return
        row = self._modifier_list.rowCount()
        self._modifier_list.insertRow(row)
        name_item = QTableWidgetItem(self._modifier_display_text(record, row))
        id_item = QTableWidgetItem(record.modifier_id)
        self._modifier_list.setItem(row, 0, name_item)
        self._modifier_list.setItem(row, 1, id_item)

    def _remove_modifier_row(self, row: int) -> None:
        if self._modifier_list is None:
            return
        self._modifier_list.removeRow(row)
        for idx in range(self._modifier_list.rowCount()):
            record = self._modifiers[idx]
            self._modifier_list.item(idx, 0).setText(self._modifier_display_text(record, idx))

    def _select_modifier_row(self, row: int) -> None:
        if self._modifier_list is None:
            return
        if row < 0 or row >= self._modifier_list.rowCount():
            return
        self._modifier_list.selectRow(row)

    def _on_modifier_selected(self) -> None:
        if self._modifier_list is None:
            return
        row = self._get_selected_row(self._modifier_list)
        prev_index = self._modifier_editor_index
        if row == prev_index:
            return
        if 0 <= prev_index < len(self._modifiers):
            self._persist_modifier_by_index(prev_index)
        self._current_modifier_index = row
        if row < 0 or row >= len(self._modifiers):
            self._clear_modifier_editor()
            self._set_modifier_editor_enabled(False)
            return
        record = self._modifiers[row]
        self._load_modifier_into_editor(record)
        self._modifier_editor_index = row
        self._set_modifier_editor_enabled(True)
        self._update_owner_bind_buttons()

    def _on_modifier_row_double_clicked(self, item: QTableWidgetItem) -> None:
        if self._modifier_list is None:
            return
        row = item.row()
        if row < 0 or row >= len(self._modifiers):
            return
        self._select_modifier_row(row)
        if not (0 <= self._selected_owner_index < len(self._owners)):
            return
        owner = self._owners[self._selected_owner_index]
        modifier_id = str(self._modifiers[row].modifier_id or "").strip()
        if not modifier_id:
            return
        existed_before = any(entry.get("modifier_id") == modifier_id for entry in self._owner_binding_rows(owner))
        self._handle_bind_modifier()
        existed_after = any(entry.get("modifier_id") == modifier_id for entry in self._owner_binding_rows(owner))
        if (not existed_before) and existed_after:
            QApplication.beep()

    def _modifier_display_text(self, record: ModifierRecord, index: int) -> str:
        return record.comment.strip() or f"Modifier {index + 1}"

    def _load_modifier_into_editor(self, record: ModifierRecord) -> None:
        self._loading_modifier_editor = True
        try:
            if self._modifier_id_input:
                self._modifier_id_input.setText(record.modifier_id)
            if self._comment_input:
                self._comment_input.setText(record.comment)
            if self._modifier_type_combo:
                self._set_combo_text(self._modifier_type_combo, record.modifier_type)
            if self._effect_type_combo:
                self._set_combo_text(self._effect_type_combo, record.effect_type or "")
            if self._collection_type_combo:
                self._set_combo_text(self._collection_type_combo, record.collection_type or "")
            if self._owner_reqset_input:
                self._owner_reqset_input.setText(record.owner_reqset or "")
            if self._subject_reqset_input:
                self._subject_reqset_input.setText(record.subject_reqset or "")
            if self._run_once_cb:
                self._run_once_cb.setChecked(record.run_once)
            if self._new_only_cb:
                self._new_only_cb.setChecked(record.new_only)
            if self._permanent_cb:
                self._permanent_cb.setChecked(record.permanent)
            if self._owner_stack_spin:
                self._owner_stack_spin.setValue(record.owner_stack_limit)
            if self._subject_stack_spin:
                self._subject_stack_spin.setValue(record.subject_stack_limit)
            if self._modifier_preview_text:
                self._modifier_preview_text.setPlainText(record.preview_text or "")
            if record.parameters:
                self._load_param_table(record.parameters)
            else:
                self._refresh_parameters_from_effect(record.effect_type)
            self._sync_modifier_preview_editor_visibility()
        finally:
            self._loading_modifier_editor = False

    def _clear_modifier_editor(self) -> None:
        self._modifier_editor_index = -1
        if self._modifier_id_input:
            self._modifier_id_input.clear()
        if self._comment_input:
            self._comment_input.clear()
        if self._modifier_type_combo:
            self._modifier_type_combo.setCurrentText("")
        if self._effect_type_combo:
            self._effect_type_combo.setCurrentText("")
        if self._collection_type_combo:
            self._collection_type_combo.setCurrentText("")
        if self._owner_reqset_input:
            self._owner_reqset_input.clear()
        if self._subject_reqset_input:
            self._subject_reqset_input.clear()
        if self._run_once_cb:
            self._run_once_cb.setChecked(False)
        if self._new_only_cb:
            self._new_only_cb.setChecked(False)
        if self._permanent_cb:
            self._permanent_cb.setChecked(False)
        if self._owner_stack_spin:
            self._owner_stack_spin.setValue(0)
        if self._subject_stack_spin:
            self._subject_stack_spin.setValue(0)
        if self._modifier_preview_text:
            self._modifier_preview_text.setPlainText("")
        self._clear_param_table()
        self._sync_modifier_preview_editor_visibility()

    def _set_modifier_editor_enabled(self, enabled: bool) -> None:
        # 前缀输入保持可用
        for widget in (
            self._modifier_id_input,
            self._comment_input,
            self._modifier_type_combo,
            self._effect_type_combo,
            self._collection_type_combo,
            self._owner_reqset_input,
            self._subject_reqset_input,
            self._owner_reqset_btn,
            self._subject_reqset_btn,
            self._run_once_cb,
            self._new_only_cb,
            self._permanent_cb,
            self._owner_stack_spin,
            self._subject_stack_spin,
            self._param_table,
            self._param_add_btn,
            self._param_del_btn,
            self._modifier_preview_text,
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    def _persist_current_modifier(self) -> None:
        index = self._modifier_editor_index
        if index < 0 or index >= len(self._modifiers):
            return
        self._persist_modifier_by_index(index)

    def _persist_modifier_by_index(self, index: int) -> None:
        if index < 0 or index >= len(self._modifiers):
            return
        record = self._modifiers[index]
        if self._modifier_id_input:
            record.modifier_id = self._modifier_id_input.text().strip()
        if self._comment_input:
            record.comment = self._comment_input.text().strip()
        if self._modifier_type_combo:
            record.modifier_type = self._modifier_type_combo.currentText().strip()
        if self._effect_type_combo:
            record.effect_type = self._effect_type_combo.currentText().strip() or None
        if self._collection_type_combo:
            record.collection_type = self._collection_type_combo.currentText().strip() or None
        if self._owner_reqset_input:
            record.owner_reqset = self._owner_reqset_input.text().strip() or None
        if self._subject_reqset_input:
            record.subject_reqset = self._subject_reqset_input.text().strip() or None
        if self._run_once_cb:
            record.run_once = self._run_once_cb.isChecked()
        if self._new_only_cb:
            record.new_only = self._new_only_cb.isChecked()
        if self._permanent_cb:
            record.permanent = self._permanent_cb.isChecked()
        if self._owner_stack_spin:
            record.owner_stack_limit = self._owner_stack_spin.value()
        if self._subject_stack_spin:
            record.subject_stack_limit = self._subject_stack_spin.value()
        if self._modifier_preview_text:
            record.preview_text = self._modifier_preview_text.toPlainText().strip()
        record.parameters = self._collect_param_rows()
        if index == self._current_modifier_index:
            self._update_modifier_list_label()

    def _update_modifier_list_label(self) -> None:
        if self._loading_modifier_editor:
            return
        if self._modifier_list is None:
            return
        row = self._modifier_editor_index
        if row < 0 or row >= len(self._modifiers):
            return
        record = self._modifiers[row]
        record.comment = self._comment_input.text().strip() if self._comment_input else record.comment
        record.modifier_id = self._modifier_id_input.text().strip() if self._modifier_id_input else record.modifier_id
        self._modifier_list.item(row, 0).setText(self._modifier_display_text(record, row))
        self._modifier_list.item(row, 1).setText(record.modifier_id)

    def _remove_modifier_bindings(self, modifier_id: str) -> None:
        if not modifier_id:
            return
        for owner in self._owners:
            rows = self._owner_binding_rows(owner)
            filtered = [row for row in rows if row.get("modifier_id") != modifier_id]
            if len(filtered) != len(rows):
                self._set_owner_binding_rows(owner, filtered)
        self._refresh_owner_binding_table()

    def _get_current_modifier_id(self) -> str | None:
        if self._modifier_list is not None:
            row = self._get_selected_row(self._modifier_list)
            if 0 <= row < len(self._modifiers):
                return self._modifiers[row].modifier_id
        if self._current_modifier_index < 0 or self._current_modifier_index >= len(self._modifiers):
            return None
        if self._modifier_id_input is not None:
            current = self._modifier_id_input.text().strip()
            return current or self._modifiers[self._current_modifier_index].modifier_id
        return self._modifiers[self._current_modifier_index].modifier_id

    def _generate_duplicate_modifier_id(self, base_id: str) -> str:
        existing = {m.modifier_id for m in self._modifiers}
        counter = 1
        while True:
            candidate = f"{base_id}_{counter}"
            if candidate not in existing:
                return candidate
            counter += 1

    # -------------------- Requirement Set / Requirement Handlers --------------------
    def _handle_add_reqset(self) -> None:
        self._persist_current_reqset()
        new_id = self._generate_requirement_set_id()
        record = RequirementSetRecord(requirement_set_id=new_id, comment="")
        self._requirement_sets.append(record)
        self._append_reqset_row(record)
        self._select_reqset_row(len(self._requirement_sets) - 1)
        self._set_reqset_editor_enabled(True)
        self._refresh_reqset_options()
        self._update_reqset_section_state()

    def _handle_delete_reqset(self) -> None:
        self._persist_current_reqset()
        row = self._current_reqset_index
        if row < 0 or row >= len(self._requirement_sets):
            return
        self._requirement_sets.pop(row)
        if self._reqset_list is not None:
            self._reqset_list.removeRow(row)
        next_row = min(row, len(self._requirement_sets) - 1)
        if next_row >= 0:
            self._select_reqset_row(next_row)
        else:
            self._current_reqset_index = -1
            self._clear_reqset_editor()
            self._set_reqset_editor_enabled(False)
        self._refresh_reqset_options()
        self._update_reqset_section_state()

    def _handle_add_requirement(self) -> None:
        self._persist_current_requirement()
        new_id = self._generate_requirement_id()
        record = RequirementRecord(
            requirement_id=new_id,
            comment="",
            requirement_type=self._req_type_combo.currentText().strip() if self._req_type_combo else "",
            likeliness=self._req_likeliness_spin.value() if self._req_likeliness_spin else 0,
            impact=self._req_impact_spin.value() if self._req_impact_spin else 0,
            progress_weight=self._req_progress_spin.value() if self._req_progress_spin else 1,
            inverse=self._req_inverse_cb.isChecked() if self._req_inverse_cb else False,
            reverse=self._req_reverse_cb.isChecked() if self._req_reverse_cb else False,
            persistent=self._req_persistent_cb.isChecked() if self._req_persistent_cb else False,
            triggered=self._req_triggered_cb.isChecked() if self._req_triggered_cb else False,
        )
        self._requirements.append(record)
        self._append_requirement_row(record)
        self._select_requirement_row(len(self._requirements) - 1)
        self._set_requirement_editor_enabled(True)
        self._update_reqset_bind_buttons()

    def _handle_delete_requirement(self) -> None:
        self._persist_current_requirement()
        row = self._current_req_index
        if row < 0 or row >= len(self._requirements):
            return
        removed = self._requirements.pop(row)
        if self._req_list is not None:
            self._req_list.removeRow(row)
        for reqset in self._requirement_sets:
            if removed.requirement_id in reqset.bound_requirements:
                reqset.bound_requirements = [
                    rid for rid in reqset.bound_requirements if rid != removed.requirement_id
                ]
        self._refresh_reqset_bind_list()
        next_row = min(row, len(self._requirements) - 1)
        if next_row >= 0:
            self._select_requirement_row(next_row)
        else:
            self._current_req_index = -1
            self._clear_requirement_editor()
            self._set_requirement_editor_enabled(False)
        self._update_reqset_bind_buttons()

    def _append_reqset_row(self, record: RequirementSetRecord) -> None:
        if self._reqset_list is None:
            return
        row = self._reqset_list.rowCount()
        self._reqset_list.insertRow(row)
        name_item = QTableWidgetItem(self._reqset_display_text(record, row))
        id_item = QTableWidgetItem(record.requirement_set_id)
        self._reqset_list.setItem(row, 0, name_item)
        self._reqset_list.setItem(row, 1, id_item)

    def _append_requirement_row(self, record: RequirementRecord) -> None:
        if self._req_list is None:
            return
        row = self._req_list.rowCount()
        self._req_list.insertRow(row)
        name_item = QTableWidgetItem(self._requirement_display_text(record, row))
        id_item = QTableWidgetItem(record.requirement_id)
        self._req_list.setItem(row, 0, name_item)
        self._req_list.setItem(row, 1, id_item)

    def _select_reqset_row(self, row: int) -> None:
        if self._reqset_list is None:
            return
        if row < 0 or row >= self._reqset_list.rowCount():
            return
        self._reqset_list.selectRow(row)

    def _select_requirement_row(self, row: int) -> None:
        if self._req_list is None:
            return
        if row < 0 or row >= self._req_list.rowCount():
            return
        self._req_list.selectRow(row)

    def _on_reqset_selected(self) -> None:
        if self._reqset_list is None:
            return
        row = self._get_selected_row(self._reqset_list)
        if row == self._current_reqset_index:
            return
        self._persist_current_reqset()
        self._current_reqset_index = row
        if row < 0 or row >= len(self._requirement_sets):
            self._clear_reqset_editor()
            self._set_reqset_editor_enabled(False)
            self._update_reqset_section_state()
            return
        record = self._requirement_sets[row]
        self._load_reqset_into_editor(record)
        self._set_reqset_editor_enabled(True)
        self._update_reqset_section_state()

    def _on_requirement_selected(self) -> None:
        if self._req_list is None:
            return
        row = self._get_selected_row(self._req_list)
        self._persist_current_requirement()
        self._current_req_index = row
        if row < 0 or row >= len(self._requirements):
            self._clear_requirement_editor()
            self._set_requirement_editor_enabled(False)
            return
        record = self._requirements[row]
        self._load_requirement_into_editor(record)
        self._set_requirement_editor_enabled(True)
        self._update_reqset_bind_buttons()

    def _reqset_display_text(self, record: RequirementSetRecord, index: int) -> str:
        return record.comment.strip() or f"条件集{index + 1}"

    def _requirement_display_text(self, record: RequirementRecord, index: int) -> str:
        return record.comment.strip() or f"条件{index + 1}"

    def _load_reqset_into_editor(self, record: RequirementSetRecord) -> None:
        self._loading_reqset_editor = True
        try:
            if self._reqset_id_input:
                self._reqset_id_input.setText(record.requirement_set_id)
            if self._reqset_comment_input:
                self._reqset_comment_input.setText(record.comment)
            if self._reqset_logic_all:
                self._reqset_logic_all.setChecked(record.logic.upper() != "ANY")
            if self._reqset_logic_any:
                self._reqset_logic_any.setChecked(record.logic.upper() == "ANY")
            self._refresh_reqset_bind_list()
            # mark current editing record so helper can access it
            self._editing_reqset = record
        finally:
            self._loading_reqset_editor = False

    def _load_requirement_into_editor(self, record: RequirementRecord) -> None:
        self._loading_requirement_editor = True
        try:
            if self._req_id_input:
                self._req_id_input.setText(record.requirement_id)
            if self._req_comment_input:
                self._req_comment_input.setText(record.comment)
            if self._req_type_combo:
                self._set_combo_text(self._req_type_combo, record.requirement_type)
            if self._req_likeliness_spin:
                self._req_likeliness_spin.setValue(record.likeliness)
            if self._req_impact_spin:
                self._req_impact_spin.setValue(record.impact)
            if self._req_progress_spin:
                self._req_progress_spin.setValue(record.progress_weight)
            if self._req_inverse_cb:
                self._req_inverse_cb.setChecked(record.inverse)
            if self._req_reverse_cb:
                self._req_reverse_cb.setChecked(record.reverse)
            if self._req_persistent_cb:
                self._req_persistent_cb.setChecked(record.persistent)
            if self._req_triggered_cb:
                self._req_triggered_cb.setChecked(record.triggered)
            if record.parameters:
                self._refresh_requirement_parameters(record.requirement_type, preset=record.parameters)
            else:
                self._refresh_requirement_parameters(record.requirement_type)
        finally:
            self._loading_requirement_editor = False

    def _persist_current_reqset(self, refresh_list: bool = True) -> None:
        if self._current_reqset_index < 0 or self._current_reqset_index >= len(self._requirement_sets):
            return
        if not all([
            self._reqset_id_input,
            self._reqset_comment_input,
            self._reqset_logic_all,
            self._reqset_logic_any,
        ]):
            return
        record = self._requirement_sets[self._current_reqset_index]
        record.requirement_set_id = self._reqset_id_input.text().strip() or record.requirement_set_id
        record.comment = self._reqset_comment_input.text().strip()
        record.logic = "ANY" if self._reqset_logic_any.isChecked() else "ALL"
        if self._reqset_bind_list is not None:
            record.bound_requirements = [
                self._reqset_bind_list.item(i).text() for i in range(self._reqset_bind_list.count())
            ]
        if refresh_list:
            self._update_reqset_list_label()

    def _persist_current_requirement(self) -> None:
        if self._current_req_index < 0 or self._current_req_index >= len(self._requirements):
            return
        if not all([
            self._req_id_input,
            self._req_comment_input,
            self._req_type_combo,
            self._req_likeliness_spin,
            self._req_impact_spin,
            self._req_progress_spin,
            self._req_inverse_cb,
            self._req_reverse_cb,
            self._req_persistent_cb,
            self._req_triggered_cb,
        ]):
            return
        record = self._requirements[self._current_req_index]
        record.requirement_id = self._req_id_input.text().strip() or record.requirement_id
        record.comment = self._req_comment_input.text().strip()
        record.requirement_type = self._req_type_combo.currentText().strip()
        record.likeliness = self._req_likeliness_spin.value()
        record.impact = self._req_impact_spin.value()
        record.progress_weight = self._req_progress_spin.value()
        record.inverse = self._req_inverse_cb.isChecked()
        record.reverse = self._req_reverse_cb.isChecked()
        record.persistent = self._req_persistent_cb.isChecked()
        record.triggered = self._req_triggered_cb.isChecked()
        record.parameters = self._collect_req_param_rows()
        self._update_requirement_list_label()

    def _update_reqset_list_label(self) -> None:
        if self._reqset_list is None:
            return
        row = self._current_reqset_index
        if row < 0 or row >= len(self._requirement_sets):
            return
        record = self._requirement_sets[row]
        self._reqset_list.item(row, 0).setText(self._reqset_display_text(record, row))
        self._reqset_list.item(row, 1).setText(record.requirement_set_id)
        self._refresh_reqset_options()

    def _update_requirement_list_label(self) -> None:
        if self._req_list is None:
            return
        row = self._current_req_index
        if row < 0 or row >= len(self._requirements):
            return
        record = self._requirements[row]
        self._req_list.item(row, 0).setText(self._requirement_display_text(record, row))
        self._req_list.item(row, 1).setText(record.requirement_id)

    def _refresh_reqset_bind_list(self) -> None:
        if self._reqset_bind_list is None:
            return
        self._reqset_bind_list.clear()
        if not (0 <= self._current_reqset_index < len(self._requirement_sets)):
            self._update_reqset_bind_buttons()
            return
        record = self._requirement_sets[self._current_reqset_index]
        for req_id in record.bound_requirements:
            self._reqset_bind_list.addItem(req_id)
        self._update_reqset_bind_buttons()

    def _bind_selected_requirement(self) -> None:
        if not (0 <= self._current_reqset_index < len(self._requirement_sets)):
            return
        if self._req_list is None:
            return
        row = self._req_list.currentRow()
        if row < 0 or row >= len(self._requirements):
            return
        req_id = self._requirements[row].requirement_id
        record = self._requirement_sets[self._current_reqset_index]
        if req_id in record.bound_requirements:
            return
        record.bound_requirements.append(req_id)
        self._refresh_reqset_bind_list()

    def _unbind_selected_requirement(self) -> None:
        if self._reqset_bind_list is None:
            return
        row = self._reqset_bind_list.currentRow()
        if row < 0:
            return
        if not (0 <= self._current_reqset_index < len(self._requirement_sets)):
            return
        record = self._requirement_sets[self._current_reqset_index]
        if 0 <= row < len(record.bound_requirements):
            removed = record.bound_requirements.pop(row)
        self._refresh_reqset_bind_list()

    def _toggle_reqset_section(self) -> None:
        if self._reqset_section_body is None or self._reqset_toggle_btn is None:
            return
        collapsed = self._reqset_toggle_btn.isChecked()
        self._reqset_section_body.setVisible(not collapsed)
        self._reqset_toggle_btn.setText("展开" if collapsed else "折叠")
        if self._reqset_delete_btn is not None:
            self._reqset_delete_btn.setVisible(not collapsed)

    def _update_reqset_section_state(self) -> None:
        has_reqset = bool(self._requirement_sets)
        if self._reqset_toggle_btn is not None:
            self._reqset_toggle_btn.setEnabled(has_reqset)
            if not has_reqset:
                self._reqset_toggle_btn.setChecked(False)
                self._reqset_toggle_btn.setText("折叠")
                if self._reqset_section_body is not None:
                    self._reqset_section_body.setVisible(True)
        if self._reqset_delete_btn is not None:
            self._reqset_delete_btn.setEnabled(has_reqset and self._current_reqset_index >= 0)
        self._update_reqset_bind_buttons()

    def _update_reqset_bind_buttons(self) -> None:
        has_reqset = 0 <= self._current_reqset_index < len(self._requirement_sets)
        has_requirement = 0 <= self._current_req_index < len(self._requirements)
        if self._reqset_bind_add_btn is not None:
            self._reqset_bind_add_btn.setEnabled(has_reqset and has_requirement)
        if self._reqset_bind_del_btn is not None and self._reqset_bind_list is not None:
            has_selection = bool(self._reqset_bind_list.selectedItems())
            self._reqset_bind_del_btn.setEnabled(has_reqset and has_selection)

    def _set_reqset_editor_enabled(self, enabled: bool) -> None:
        for widget in (
            self._reqset_id_input,
            self._reqset_comment_input,
            self._reqset_logic_all,
            self._reqset_logic_any,
            self._reqset_bind_list,
            self._reqset_bind_add_btn,
            self._reqset_bind_del_btn,
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    def _set_requirement_editor_enabled(self, enabled: bool) -> None:
        for widget in (
            self._req_id_input,
            self._req_comment_input,
            self._req_type_combo,
            self._req_type_search_btn,
            self._req_likeliness_spin,
            self._req_impact_spin,
            self._req_progress_spin,
            self._req_inverse_cb,
            self._req_reverse_cb,
            self._req_persistent_cb,
            self._req_triggered_cb,
            self._req_param_table,
            self._req_param_add_btn,
            self._req_param_del_btn,
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    def _clear_reqset_editor(self) -> None:
        if self._reqset_id_input:
            self._reqset_id_input.clear()
        if self._reqset_comment_input:
            self._reqset_comment_input.clear()
        if self._reqset_logic_all:
            self._reqset_logic_all.setChecked(True)
        if self._reqset_logic_any:
            self._reqset_logic_any.setChecked(False)
        if self._reqset_bind_list:
            self._reqset_bind_list.clear()
        # clear editing marker
        self._editing_reqset = None

    def _clear_requirement_editor(self) -> None:
        if self._req_id_input:
            self._req_id_input.clear()
        if self._req_comment_input:
            self._req_comment_input.clear()
        if self._req_type_combo:
            self._req_type_combo.setCurrentText("")
        if self._req_likeliness_spin:
            self._req_likeliness_spin.setValue(0)
        if self._req_impact_spin:
            self._req_impact_spin.setValue(0)
        if self._req_progress_spin:
            self._req_progress_spin.setValue(1)
        if self._req_inverse_cb:
            self._req_inverse_cb.setChecked(False)
        if self._req_reverse_cb:
            self._req_reverse_cb.setChecked(False)
        if self._req_persistent_cb:
            self._req_persistent_cb.setChecked(False)
        if self._req_triggered_cb:
            self._req_triggered_cb.setChecked(False)
        self._clear_req_param_table()

    def _sync_reqset_logic(self, checked: bool, is_all: bool) -> None:
        if not checked:
            return
        if is_all and self._reqset_logic_any is not None:
            self._reqset_logic_any.blockSignals(True)
            self._reqset_logic_any.setChecked(False)
            self._reqset_logic_any.blockSignals(False)
        if (not is_all) and self._reqset_logic_all is not None:
            self._reqset_logic_all.blockSignals(True)
            self._reqset_logic_all.setChecked(False)
            self._reqset_logic_all.blockSignals(False)

    def _on_modifier_editor_changed(self, field: str) -> None:
        if self._loading_modifier_editor:
            return
        if self._modifier_editor_index < 0 or self._modifier_editor_index >= len(self._modifiers):
            return
        self._persist_current_modifier()

    def _log_reqset_combo_state(self, source: str) -> None:
        reqset_ids = [r.requirement_set_id for r in self._requirement_sets if r.requirement_set_id]
        owner_items: List[str] = []
        subject_items: List[str] = []
        owner_current = self._owner_reqset_input.text() if self._owner_reqset_input is not None else ""
        subject_current = self._subject_reqset_input.text() if self._subject_reqset_input is not None else ""
        owner_model_count = 0
        subject_model_count = 0
        if self._owner_reqset_menu is not None:
            owner_items = [action.text() for action in self._owner_reqset_menu.actions()]
            owner_model_count = len(owner_items)
        if self._subject_reqset_menu is not None:
            subject_items = [action.text() for action in self._subject_reqset_menu.actions()]
            subject_model_count = len(subject_items)
        LOGGER.info(
            "Reqset combo popup=%s | reqset_count=%s | reqset_ids=%s | model_rows=%s | owner_count=%s | owner_model_count=%s | owner_items=%s | owner_current=%s | subject_count=%s | subject_model_count=%s | subject_items=%s | subject_current=%s",
            source,
            len(reqset_ids),
            reqset_ids,
            self._reqset_model.rowCount(),
            len(owner_items),
            owner_model_count,
            owner_items,
            owner_current,
            len(subject_items),
            subject_model_count,
            subject_items,
            subject_current,
        )
        LOGGER.info(
            "Reqset combo models | owner_menu_id=%s subject_menu_id=%s shared_model_id=%s",
            id(self._owner_reqset_menu) if self._owner_reqset_menu is not None else None,
            id(self._subject_reqset_menu) if self._subject_reqset_menu is not None else None,
            id(self._reqset_model),
        )

    def _on_reqset_editor_changed(self, field: str) -> None:
        if self._loading_reqset_editor:
            return
        if self._current_reqset_index < 0 or self._current_reqset_index >= len(self._requirement_sets):
            return
        self._persist_current_reqset()

    def _on_requirement_editor_changed(self, field: str) -> None:
        if self._loading_requirement_editor:
            return
        if self._current_req_index < 0 or self._current_req_index >= len(self._requirements):
            return

    def _snapshot_modifier_editor(self) -> Dict[str, object]:
        owner_text = self._owner_reqset_input.text().strip() if self._owner_reqset_input else ""
        subject_text = self._subject_reqset_input.text().strip() if self._subject_reqset_input else ""
        return {
            "modifier_id": self._modifier_id_input.text().strip() if self._modifier_id_input else "",
            "comment": self._comment_input.text().strip() if self._comment_input else "",
            "modifier_type": self._modifier_type_combo.currentText().strip() if self._modifier_type_combo else "",
            "effect_type": self._effect_type_combo.currentText().strip() if self._effect_type_combo else "",
            "collection_type": self._collection_type_combo.currentText().strip() if self._collection_type_combo else "",
            "owner_reqset": owner_text.strip(),
            "subject_reqset": subject_text.strip(),
            "run_once": self._run_once_cb.isChecked() if self._run_once_cb else False,
            "new_only": self._new_only_cb.isChecked() if self._new_only_cb else False,
            "permanent": self._permanent_cb.isChecked() if self._permanent_cb else False,
            "owner_stack_limit": self._owner_stack_spin.value() if self._owner_stack_spin else 0,
            "subject_stack_limit": self._subject_stack_spin.value() if self._subject_stack_spin else 0,
            "preview_text": self._modifier_preview_text.toPlainText().strip() if self._modifier_preview_text else "",
            "parameters": self._collect_param_rows(),
        }

    def _snapshot_reqset_editor(self) -> Dict[str, object]:
        return {
            "requirement_set_id": self._reqset_id_input.text().strip() if self._reqset_id_input else "",
            "comment": self._reqset_comment_input.text().strip() if self._reqset_comment_input else "",
            "logic": "ANY" if (self._reqset_logic_any and self._reqset_logic_any.isChecked()) else "ALL",
            "bound_requirements": [
                self._reqset_bind_list.item(i).text()
                for i in range(self._reqset_bind_list.count())
            ] if self._reqset_bind_list else [],
        }

    def _snapshot_requirement_editor(self) -> Dict[str, object]:
        return {
            "requirement_id": self._req_id_input.text().strip() if self._req_id_input else "",
            "comment": self._req_comment_input.text().strip() if self._req_comment_input else "",
            "requirement_type": self._req_type_combo.currentText().strip() if self._req_type_combo else "",
            "likeliness": self._req_likeliness_spin.value() if self._req_likeliness_spin else 0,
            "impact": self._req_impact_spin.value() if self._req_impact_spin else 0,
            "progress_weight": self._req_progress_spin.value() if self._req_progress_spin else 0,
            "inverse": self._req_inverse_cb.isChecked() if self._req_inverse_cb else False,
            "reverse": self._req_reverse_cb.isChecked() if self._req_reverse_cb else False,
            "persistent": self._req_persistent_cb.isChecked() if self._req_persistent_cb else False,
            "triggered": self._req_triggered_cb.isChecked() if self._req_triggered_cb else False,
            "parameters": self._collect_req_param_rows(),
        }

    # -------------------- Modifier Type / Effect Type --------------------
    def _open_modifier_type_dialog(self) -> None:
        options = sorted(self._modifier_meta_index.keys())
        dialog = SearchListDialog("选择 ModifierType", options, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected()
            if selected and self._modifier_type_combo:
                self._modifier_type_combo.setCurrentText(selected)

    def _open_effect_type_dialog(self) -> None:
        dialog = SearchListDialog("选择 EffectType", self._effect_types, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected()
            if selected and self._effect_type_combo:
                self._effect_type_combo.setCurrentText(selected)

    def _on_modifier_type_changed(self, text: str) -> None:
        meta = self._modifier_meta_index.get(text)
        if meta and self._effect_type_combo and self._collection_type_combo:
            if meta.effect_type:
                self._effect_type_combo.setCurrentText(meta.effect_type)
            if meta.collection_type:
                self._collection_type_combo.setCurrentText(meta.collection_type)

    def _on_effect_type_changed(self, text: str) -> None:
        self._sync_modifier_preview_editor_visibility()
        if not text.strip():
            self._clear_param_table()
            return
        self._refresh_parameters_from_effect(text)

    def _on_requirement_type_changed(self, text: str) -> None:
        self._refresh_requirement_parameters(text)

    def _open_requirement_type_dialog(self) -> None:
        dialog = SearchListDialog("选择 RequirementType", self._requirement_types, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected()
            if selected and self._req_type_combo:
                self._req_type_combo.setCurrentText(selected)

    # -------------------- Requirement set options (placeholder) --------------------
    def _collect_reqset_picker_rows(self) -> List[tuple[str, str]]:
        item_ids = {
            str(r.requirement_set_id or "").strip()
            for r in self._requirement_sets
            if str(r.requirement_set_id or "").strip()
        }
        item_ids.update({
            str(m.owner_reqset or "").strip()
            for m in self._modifiers
            if str(m.owner_reqset or "").strip()
        })
        item_ids.update({
            str(m.subject_reqset or "").strip()
            for m in self._modifiers
            if str(m.subject_reqset or "").strip()
        })
        rows: List[tuple[str, str]] = [("", "")]
        for reqset_id in sorted(item_ids):
            comment = self._find_reqset_comment(reqset_id)
            rows.append((comment, reqset_id))
        rows[1:] = sorted(rows[1:], key=lambda entry: (entry[0] == "", entry[0], entry[1]))
        return rows

    def _open_reqset_search_dialog(self, target: str) -> None:
        self._refresh_reqset_options()
        rows = self._collect_reqset_picker_rows()
        if target == "owner":
            current = self._owner_reqset_input.text().strip() if self._owner_reqset_input else ""
            title = "选择 OwnerRequirementSetId"
        else:
            current = self._subject_reqset_input.text().strip() if self._subject_reqset_input else ""
            title = "选择 SubjectRequirementSetId"
        dialog = ReqsetSearchDialog(title, rows, current_value=current, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected()
        if selected is None:
            return
        if target == "owner":
            if self._owner_reqset_input is not None:
                self._owner_reqset_input.setText(selected)
        else:
            if self._subject_reqset_input is not None:
                self._subject_reqset_input.setText(selected)

    def _refresh_reqset_options(self, options: Sequence[str] | None = None) -> None:
        """更新条件集下拉选项。"""
        if self._owner_reqset_menu is None or self._subject_reqset_menu is None:
            LOGGER.warning(
                "Reqset refresh skipped: owner_combo=%s subject_combo=%s",
                "ready" if self._owner_reqset_menu is not None else "none",
                "ready" if self._subject_reqset_menu is not None else "none",
            )
            return
        if options is None:
            items_set = {r.requirement_set_id for r in self._requirement_sets if r.requirement_set_id}
            items_set.update({m.owner_reqset for m in self._modifiers if m.owner_reqset})
            items_set.update({m.subject_reqset for m in self._modifiers if m.subject_reqset})
            items = sorted(items_set)
        else:
            items = list(options)
        if "" not in items:
            items.insert(0, "")
        self._reqset_model.setStringList(items)
        LOGGER.info(
            "Reqset model updated | items=%s | model_rows=%s | model_id=%s",
            len(items),
            self._reqset_model.rowCount(),
            id(self._reqset_model),
        )
        self._owner_reqset_menu.clear()
        self._subject_reqset_menu.clear()
        for value in items:
            text = value or "（空）"
            owner_action = QAction(text, self)
            owner_action.triggered.connect(lambda _v=False, val=value: self._owner_reqset_input.setText(val))
            self._owner_reqset_menu.addAction(owner_action)
            subject_action = QAction(text, self)
            subject_action.triggered.connect(lambda _v=False, val=value: self._subject_reqset_input.setText(val))
            self._subject_reqset_menu.addAction(subject_action)
        owner_text = self._owner_reqset_input.text() if self._owner_reqset_input is not None else ""
        subject_text = self._subject_reqset_input.text() if self._subject_reqset_input is not None else ""
        LOGGER.info(
            "Reqset refresh inputs | owner_text=%s | subject_text=%s",
            owner_text,
            subject_text,
        )
        if items and self._reqset_model.rowCount() == 0:
            LOGGER.warning("Reqset model refresh still empty")

    # -------------------- Export / Import --------------------
    def export_home_data(self) -> Dict[str, object]:
        self._persist_current_modifier()
        self._persist_current_reqset(refresh_list=False)
        self._persist_current_requirement()

        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""

        owners = [
            {
                "table_name": owner.table_name,
                "type_column": owner.type_column,
                "type_name": owner.type_name,
                "display_name": owner.display_name,
                "source_key": owner.source_key,
                "bound_modifier_ids": list(owner.bound_modifier_ids),
                "owner_bindings": [
                    {
                        "modifier_id": str(row.get("modifier_id") or "").strip(),
                        "attachment_target_type": str(row.get("attachment_target_type") or "").strip(),
                    }
                    for row in self._owner_binding_rows(owner)
                ],
            }
            for owner in self._owners
        ]
        unit_abilities = [
            {
                "unit_ability_type": record.unit_ability_type,
                "name_zh": record.name_zh,
                "description_zh": record.description_zh,
                "inactive": bool(record.inactive),
                "show_float_text_when_earned": bool(record.show_float_text_when_earned),
                "permanent": bool(record.permanent),
                "type_tags": list(record.type_tags),
            }
            for record in self._unit_ability_records
            if str(record.unit_ability_type or "").strip()
        ]
        modifiers = [
            {
                "modifier_id": record.modifier_id,
                "modifier_type": record.modifier_type,
                "comment": record.comment,
                "owner_reqset": record.owner_reqset,
                "subject_reqset": record.subject_reqset,
                "run_once": record.run_once,
                "new_only": record.new_only,
                "permanent": record.permanent,
                "owner_stack_limit": record.owner_stack_limit,
                "subject_stack_limit": record.subject_stack_limit,
                "effect_type": record.effect_type,
                "collection_type": record.collection_type,
                "preview_text": record.preview_text,
                "parameters": list(record.parameters),
            }
            for record in self._modifiers
        ]
        reqsets = [
            {
                "requirement_set_id": record.requirement_set_id,
                "comment": record.comment,
                "logic": record.logic,
                "bound_requirements": list(record.bound_requirements),
            }
            for record in self._requirement_sets
        ]
        requirements = [
            {
                "requirement_id": record.requirement_id,
                "comment": record.comment,
                "requirement_type": record.requirement_type,
                "likeliness": record.likeliness,
                "impact": record.impact,
                "progress_weight": record.progress_weight,
                "inverse": record.inverse,
                "reverse": record.reverse,
                "persistent": record.persistent,
                "triggered": record.triggered,
                "parameters": list(record.parameters),
            }
            for record in self._requirements
        ]
        return {
            "prefix1": prefix1,
            "prefix2": prefix2,
            "owners": owners,
            "unit_abilities": unit_abilities,
            "modifiers": modifiers,
            "requirement_sets": reqsets,
            "requirements": requirements,
        }

    def _handle_save_data(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存数据",
            "modifiers_data.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        data = self.export_home_data()
        try:
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", f"无法保存数据：{exc}")
            return
        QMessageBox.information(self, "保存成功", "数据已保存为 JSON。")

    def _handle_import_data(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入数据",
            "",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.warning(self, "导入失败", f"无法读取数据：{exc}")
            return
        if not isinstance(payload, dict):
            QMessageBox.warning(self, "导入失败", "JSON格式不正确。")
            return
        self._apply_import_data(payload)
        QMessageBox.information(self, "导入成功", "数据已导入。")

    def _handle_sql_preview(self) -> None:
        self._persist_current_modifier()
        self._persist_current_reqset(refresh_list=False)
        self._persist_current_requirement()
        content = self._build_sql_preview_text()
        dialog = TextPreviewDialog("SQL 预览", content, self)
        dialog.exec()

    def _handle_xml_preview(self) -> None:
        self._persist_current_modifier()
        self._persist_current_reqset(refresh_list=False)
        self._persist_current_requirement()
        content = self._build_xml_preview_text()
        dialog = TextPreviewDialog("XML 预览", content, self)
        dialog.exec()

    def _sql_escape(self, text: str) -> str:
        return text.replace("'", "''")

    def _sql_text_or_null(self, value: str | None) -> str:
        if value is None:
            return "NULL"
        trimmed = str(value).strip()
        if not trimmed:
            return "NULL"
        return f"'{self._sql_escape(trimmed)}'"

    def _sql_text_or_empty(self, value: object) -> str:
        if value is None:
            return "''"
        text = str(value)
        return f"'{self._sql_escape(text)}'"

    def _param_to_sql(self, value: object) -> str:
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "false"}:
                return "1" if lowered == "true" else "0"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return self._format_number_sql(value)
        if isinstance(value, dict):
            for key in ("value", "id", "type", "unit_type", "display", "text", "name"):
                if key in value and value[key] not in (None, ""):
                    return self._param_to_sql(value[key])
            return "''"
        if value is None:
            return "''"
        return self._sql_text_or_empty(value)

    def _format_number_sql(self, value: float | int) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        try:
            num = float(value)
        except (TypeError, ValueError):
            return str(value)
        if num.is_integer():
            return str(int(num))
        return str(num)

    def _build_sql_preview_text(self) -> str:
        sections: List[str] = []

        # Owners
        owners_by_table: Dict[str, Dict[str, object]] = {}
        for owner in self._owners:
            rows = self._owner_binding_rows(owner)
            if not rows:
                continue
            type_column = owner.type_column or OWNER_TABLE_TYPE_MAP.get(owner.table_name, "")
            if not type_column:
                continue
            bucket = owners_by_table.setdefault(owner.table_name, {"type_column": type_column, "rows": []})
            bucket_rows = bucket.get("rows")
            if not isinstance(bucket_rows, list):
                continue
            for row_data in rows:
                modifier_id = str(row_data.get("modifier_id") or "").strip()
                if modifier_id:
                    bucket_rows.append(
                        (
                            owner.type_name,
                            modifier_id,
                            str(row_data.get("attachment_target_type") or "").strip(),
                        )
                    )

        for table_name, bucket in owners_by_table.items():
            rows = bucket.get("rows") if isinstance(bucket, dict) else None
            if not isinstance(rows, list) or not rows:
                continue
            type_column = str(bucket.get("type_column") or "") if isinstance(bucket, dict) else ""
            if not type_column:
                continue
            if table_name == OWNER_TABLE_WITH_ATTACHMENT_TARGET:
                lines = [f"INSERT INTO {table_name} ({type_column}, ModifierId, AttachmentTargetType) VALUES"]
            else:
                lines = [f"INSERT INTO {table_name} ({type_column}, ModifierId) VALUES"]
            for idx, row_tuple in enumerate(rows):
                type_name, modifier_id, attachment_target_type = row_tuple
                line_end = ";" if idx == len(rows) - 1 else ","
                if table_name == OWNER_TABLE_WITH_ATTACHMENT_TARGET:
                    attachment_sql = self._sql_text_or_null(attachment_target_type)
                    lines.append(
                        f"('{self._sql_escape(type_name)}', '{self._sql_escape(modifier_id)}', {attachment_sql}){line_end}"
                    )
                else:
                    lines.append(
                        f"('{self._sql_escape(type_name)}', '{self._sql_escape(modifier_id)}'){line_end}"
                    )
            sections.append("\n".join(lines))

        # Custom ModifierType definitions (Types / DynamicModifiers)
        custom_modifier_types: Dict[str, Dict[str, str | None]] = {}
        for record in self._modifiers:
            modifier_type = record.modifier_type.strip()
            if not modifier_type:
                continue
            if modifier_type in self._modifier_meta_index:
                continue
            current = custom_modifier_types.get(modifier_type)
            if current is None:
                custom_modifier_types[modifier_type] = {
                    "effect_type": record.effect_type,
                    "collection_type": record.collection_type,
                }
            else:
                if not current.get("effect_type") and record.effect_type:
                    current["effect_type"] = record.effect_type
                if not current.get("collection_type") and record.collection_type:
                    current["collection_type"] = record.collection_type

        if custom_modifier_types:
            type_lines = ["INSERT INTO Types (Type, Kind) VALUES"]
            type_keys = sorted(custom_modifier_types.keys())
            for idx, modifier_type in enumerate(type_keys):
                line_end = ";" if idx == len(type_keys) - 1 else ","
                type_lines.append(
                    f"('{self._sql_escape(modifier_type)}', 'KIND_MODIFIER'){line_end}"
                )
            sections.append("\n".join(type_lines))

            dyn_lines = ["INSERT INTO DynamicModifiers (ModifierType, EffectType, CollectionType) VALUES"]
            for idx, modifier_type in enumerate(type_keys):
                meta = custom_modifier_types.get(modifier_type, {})
                effect_text = self._sql_text_or_null(meta.get("effect_type"))
                collection_text = self._sql_text_or_null(meta.get("collection_type"))
                line_end = ";" if idx == len(type_keys) - 1 else ","
                dyn_lines.append(
                    f"('{self._sql_escape(modifier_type)}', {effect_text}, {collection_text}){line_end}"
                )
            sections.append("\n".join(dyn_lines))

        # Modifiers
        if self._modifiers:
            columns: List[tuple[str, str]] = [("ModifierId", "text"), ("ModifierType", "text")]
            if any(m.owner_reqset for m in self._modifiers):
                columns.append(("OwnerRequirementSetId", "text"))
            if any(m.subject_reqset for m in self._modifiers):
                columns.append(("SubjectRequirementSetId", "text"))
            if any(m.run_once for m in self._modifiers):
                columns.append(("RunOnce", "bool"))
            if any(m.new_only for m in self._modifiers):
                columns.append(("NewOnly", "bool"))
            if any(m.permanent for m in self._modifiers):
                columns.append(("Permanent", "bool"))
            if any(m.owner_stack_limit for m in self._modifiers):
                columns.append(("OwnerStackLimit", "int"))
            if any(m.subject_stack_limit for m in self._modifiers):
                columns.append(("SubjectStackLimit", "int"))

            col_names = ", ".join(col for col, _ in columns)
            lines = [f"INSERT INTO Modifiers({col_names}) VALUES"]
            for idx, record in enumerate(self._modifiers):
                values: List[str] = []
                for col, col_type in columns:
                    if col == "ModifierId":
                        values.append(self._sql_text_or_null(record.modifier_id))
                    elif col == "ModifierType":
                        values.append(self._sql_text_or_null(record.modifier_type))
                    elif col == "OwnerRequirementSetId":
                        values.append(self._sql_text_or_null(record.owner_reqset))
                    elif col == "SubjectRequirementSetId":
                        values.append(self._sql_text_or_null(record.subject_reqset))
                    elif col == "RunOnce":
                        values.append("1" if record.run_once else "0")
                    elif col == "NewOnly":
                        values.append("1" if record.new_only else "0")
                    elif col == "Permanent":
                        values.append("1" if record.permanent else "0")
                    elif col == "OwnerStackLimit":
                        values.append(str(record.owner_stack_limit or 0))
                    elif col == "SubjectStackLimit":
                        values.append(str(record.subject_stack_limit or 0))
                    else:
                        values.append("NULL")

                line_end = ";" if idx == len(self._modifiers) - 1 else ","
                line = f"({', '.join(values)}){line_end}"
                if record.comment:
                    line += f" -- {record.comment}"
                lines.append(line)
            sections.append("\n".join(lines))

        # ModifierArguments
        arg_lines: List[str] = []
        for record in self._modifiers:
            for param in record.parameters:
                name = str(param.get("name", "")).strip()
                if not name:
                    continue
                value = self._param_to_sql(param.get("value"))
                arg_lines.append(
                    f"('{self._sql_escape(record.modifier_id)}', '{self._sql_escape(name)}', {value})"
                )
        if arg_lines:
            lines = ["INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES"]
            for idx, line in enumerate(arg_lines):
                line_end = ";" if idx == len(arg_lines) - 1 else ","
                lines.append(f"{line}{line_end}")
            sections.append("\n".join(lines))
        else:
            sections.append("-- ModifierArguments 为空")

        modifier_strings_rows: List[str] = []
        for record in self._modifiers:
            if not self._supports_modifier_preview_string(record.effect_type):
                continue
            modifier_id = str(record.modifier_id or "").strip()
            preview_text = str(record.preview_text or "").strip()
            if not modifier_id or not preview_text:
                continue
            text_tag = f"LOC_{modifier_id}_PREVIEW"
            modifier_strings_rows.append(
                f"('{self._sql_escape(modifier_id)}', 'Preview', '{self._sql_escape(text_tag)}')"
            )

        if modifier_strings_rows:
            lines = ["INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES"]
            for idx, row in enumerate(modifier_strings_rows):
                line_end = ";" if idx == len(modifier_strings_rows) - 1 else ","
                lines.append(f"{row}{line_end}")
            sections.append("\n".join(lines))

        # RequirementSets
        reqset_lines: List[tuple[str, str]] = []
        reqset_req_lines: List[str] = []
        for record in self._requirement_sets:
            if not record.requirement_set_id:
                continue
            reqset_type = "REQUIREMENTSET_TEST_ANY" if record.logic.upper() == "ANY" else "REQUIREMENTSET_TEST_ALL"
            value_part = f"('{self._sql_escape(record.requirement_set_id)}', '{reqset_type}')"
            comment_part = f" -- {record.comment}" if record.comment else ""
            reqset_lines.append((value_part, comment_part))
            for req_id in record.bound_requirements:
                if not req_id:
                    continue
                reqset_req_lines.append(
                    f"('{self._sql_escape(record.requirement_set_id)}', '{self._sql_escape(req_id)}')"
                )

        if reqset_lines:
            lines = ["INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES"]
            for idx, (value_part, comment_part) in enumerate(reqset_lines):
                line_end = ";" if idx == len(reqset_lines) - 1 else ","
                lines.append(f"{value_part}{line_end}{comment_part}")
            sections.append("\n".join(lines))

        if reqset_req_lines:
            lines = ["INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES"]
            for idx, line in enumerate(reqset_req_lines):
                line_end = ";" if idx == len(reqset_req_lines) - 1 else ","
                lines.append(f"{line}{line_end}")
            sections.append("\n".join(lines))

        # Requirements
        if self._requirements:
            columns: List[tuple[str, str]] = [("RequirementId", "text"), ("RequirementType", "text")]
            if any(r.inverse for r in self._requirements):
                columns.append(("Inverse", "bool"))
            if any(r.reverse for r in self._requirements):
                columns.append(("Reverse", "bool"))
            if any(r.persistent for r in self._requirements):
                columns.append(("Persistent", "bool"))
            if any(r.triggered for r in self._requirements):
                columns.append(("Triggered", "bool"))
            if any(r.likeliness for r in self._requirements):
                columns.append(("Likeliness", "int"))
            if any(r.impact for r in self._requirements):
                columns.append(("Impact", "int"))
            if any(r.progress_weight != 1 for r in self._requirements):
                columns.append(("ProgressWeight", "int"))

            col_names = ", ".join(col for col, _ in columns)
            lines = [f"INSERT INTO Requirements ({col_names}) VALUES"]
            for idx, record in enumerate(self._requirements):
                values: List[str] = []
                for col, col_type in columns:
                    if col == "RequirementId":
                        values.append(self._sql_text_or_null(record.requirement_id))
                    elif col == "RequirementType":
                        values.append(self._sql_text_or_null(record.requirement_type))
                    elif col == "Inverse":
                        values.append("1" if record.inverse else "0")
                    elif col == "Reverse":
                        values.append("1" if record.reverse else "0")
                    elif col == "Persistent":
                        values.append("1" if record.persistent else "0")
                    elif col == "Triggered":
                        values.append("1" if record.triggered else "0")
                    elif col == "Likeliness":
                        values.append(str(record.likeliness or 0))
                    elif col == "Impact":
                        values.append(str(record.impact or 0))
                    elif col == "ProgressWeight":
                        values.append(str(record.progress_weight or 1))
                    else:
                        values.append("NULL")

                line_end = ";" if idx == len(self._requirements) - 1 else ","
                line = f"({', '.join(values)}){line_end}"
                if record.comment:
                    line += f" -- {record.comment}"
                lines.append(line)
            sections.append("\n".join(lines))

        # RequirementArguments
        req_arg_lines: List[str] = []
        for record in self._requirements:
            for param in record.parameters:
                name = str(param.get("name", "")).strip()
                if not name:
                    continue
                value = self._param_to_sql(param.get("value"))
                req_arg_lines.append(
                    f"('{self._sql_escape(record.requirement_id)}', '{self._sql_escape(name)}', {value})"
                )
        if req_arg_lines:
            lines = ["INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES"]
            for idx, line in enumerate(req_arg_lines):
                line_end = ";" if idx == len(req_arg_lines) - 1 else ","
                lines.append(f"{line}{line_end}")
            sections.append("\n".join(lines))
        else:
            sections.append("-- RequirementArguments 为空")

        return "\n\n".join([section for section in sections if section])

    def _build_xml_preview_text(self) -> str:
        def _bool_int(value: object) -> str:
            return "1" if bool(value) else "0"

        def _text(value: object | None) -> str:
            return "" if value is None else str(value)

        def _param_value_to_xml(value: object | None, param_name: str | None = None) -> str:
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "false"}:
                    return "True" if lowered == "true" else "False"
            if isinstance(value, bool):
                return "True" if value else "False"
            if isinstance(value, (int, float)):
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    return str(value)
                return str(int(num)) if num.is_integer() else str(num)
            if isinstance(value, dict):
                for key in ("value", "id", "type", "unit_type", "display", "text", "name"):
                    if key in value and value[key] not in (None, ""):
                        return _param_value_to_xml(value[key], param_name)
                return ""
            if value is None:
                return ""
            return str(value)

        def _param_value_to_xml_with_name(value: object | None, param_name: str) -> str:
            if param_name in BOOLEAN_PARAM_KEYS:
                if isinstance(value, str):
                    lowered = value.strip().lower()
                    if lowered in {"true", "false"}:
                        return "True" if lowered == "true" else "False"
                return "True" if bool(value) else "False"
            return _param_value_to_xml(value, param_name)

        root = ElementTree.Element("GameInfo")

        # Owners
        owners_by_table: Dict[str, Dict[str, object]] = {}
        for owner in self._owners:
            rows = self._owner_binding_rows(owner)
            if not rows:
                continue
            type_column = owner.type_column or OWNER_TABLE_TYPE_MAP.get(owner.table_name, "")
            if not type_column:
                continue
            bucket = owners_by_table.setdefault(owner.table_name, {"type_column": type_column, "rows": []})
            bucket_rows = bucket.get("rows")
            if not isinstance(bucket_rows, list):
                continue
            for row_data in rows:
                modifier_id = str(row_data.get("modifier_id") or "").strip()
                if modifier_id:
                    bucket_rows.append(
                        (
                            owner.type_name,
                            modifier_id,
                            str(row_data.get("attachment_target_type") or "").strip(),
                        )
                    )
        for table_name, bucket in owners_by_table.items():
            rows = bucket.get("rows") if isinstance(bucket, dict) else None
            if not isinstance(rows, list):
                continue
            type_column = str(bucket.get("type_column") or "") if isinstance(bucket, dict) else ""
            if not type_column:
                continue
            table_el = ElementTree.SubElement(root, table_name)
            for type_name, modifier_id, attachment_target_type in rows:
                row_el = ElementTree.SubElement(table_el, "Row")
                ElementTree.SubElement(row_el, type_column).text = _text(type_name)
                ElementTree.SubElement(row_el, "ModifierId").text = _text(modifier_id)
                if table_name == OWNER_TABLE_WITH_ATTACHMENT_TARGET:
                    ElementTree.SubElement(row_el, "AttachmentTargetType").text = _text(attachment_target_type)

        # Types / DynamicModifiers (custom)
        custom_modifier_types: Dict[str, Dict[str, str | None]] = {}
        for record in self._modifiers:
            modifier_type = record.modifier_type.strip()
            if not modifier_type:
                continue
            if modifier_type in self._modifier_meta_index:
                continue
            current = custom_modifier_types.get(modifier_type)
            if current is None:
                custom_modifier_types[modifier_type] = {
                    "effect_type": record.effect_type,
                    "collection_type": record.collection_type,
                }
            else:
                if not current.get("effect_type") and record.effect_type:
                    current["effect_type"] = record.effect_type
                if not current.get("collection_type") and record.collection_type:
                    current["collection_type"] = record.collection_type
        if custom_modifier_types:
            types_el = ElementTree.SubElement(root, "Types")
            dyn_el = ElementTree.SubElement(root, "DynamicModifiers")
            for modifier_type, meta in sorted(custom_modifier_types.items()):
                trow = ElementTree.SubElement(types_el, "Row")
                ElementTree.SubElement(trow, "Type").text = modifier_type
                ElementTree.SubElement(trow, "Kind").text = "KIND_MODIFIER"
                drow = ElementTree.SubElement(dyn_el, "Row")
                ElementTree.SubElement(drow, "ModifierType").text = modifier_type
                ElementTree.SubElement(drow, "EffectType").text = _text(meta.get("effect_type"))
                ElementTree.SubElement(drow, "CollectionType").text = _text(meta.get("collection_type"))

        # Modifiers
        mods_el = ElementTree.SubElement(root, "Modifiers")
        mod_columns: List[tuple[str, str]] = [("ModifierId", "text"), ("ModifierType", "text")]
        if any(m.owner_reqset for m in self._modifiers):
            mod_columns.append(("OwnerRequirementSetId", "text"))
        if any(m.subject_reqset for m in self._modifiers):
            mod_columns.append(("SubjectRequirementSetId", "text"))
        if any(m.run_once for m in self._modifiers):
            mod_columns.append(("RunOnce", "bool"))
        if any(m.new_only for m in self._modifiers):
            mod_columns.append(("NewOnly", "bool"))
        if any(m.permanent for m in self._modifiers):
            mod_columns.append(("Permanent", "bool"))
        if any(m.owner_stack_limit for m in self._modifiers):
            mod_columns.append(("OwnerStackLimit", "int"))
        if any(m.subject_stack_limit for m in self._modifiers):
            mod_columns.append(("SubjectStackLimit", "int"))

        for record in self._modifiers:
            row_el = ElementTree.SubElement(mods_el, "Row")
            for col, col_type in mod_columns:
                value: object | None
                if col == "ModifierId":
                    value = record.modifier_id
                elif col == "ModifierType":
                    value = record.modifier_type
                elif col == "OwnerRequirementSetId":
                    value = record.owner_reqset
                elif col == "SubjectRequirementSetId":
                    value = record.subject_reqset
                elif col == "RunOnce":
                    value = _bool_int(record.run_once)
                elif col == "NewOnly":
                    value = _bool_int(record.new_only)
                elif col == "Permanent":
                    value = _bool_int(record.permanent)
                elif col == "OwnerStackLimit":
                    value = record.owner_stack_limit
                elif col == "SubjectStackLimit":
                    value = record.subject_stack_limit
                else:
                    value = None
                if value in (None, ""):
                    continue
                ElementTree.SubElement(row_el, col).text = _text(value)

        # ModifierArguments
        args_el = ElementTree.SubElement(root, "ModifierArguments")
        for record in self._modifiers:
            for param in record.parameters:
                name = str(param.get("name", "")).strip()
                if not name:
                    continue
                row_el = ElementTree.SubElement(args_el, "Row")
                ElementTree.SubElement(row_el, "ModifierId").text = _text(record.modifier_id)
                ElementTree.SubElement(row_el, "Name").text = name
                ElementTree.SubElement(row_el, "Value").text = _param_value_to_xml_with_name(param.get("value"), name)

        modifier_strings_el = ElementTree.SubElement(root, "ModifierStrings")
        for record in self._modifiers:
            if not self._supports_modifier_preview_string(record.effect_type):
                continue
            modifier_id = str(record.modifier_id or "").strip()
            preview_text = str(record.preview_text or "").strip()
            if not modifier_id or not preview_text:
                continue
            row_el = ElementTree.SubElement(modifier_strings_el, "Row")
            ElementTree.SubElement(row_el, "ModifierId").text = modifier_id
            ElementTree.SubElement(row_el, "Context").text = "Preview"
            ElementTree.SubElement(row_el, "Text").text = f"LOC_{modifier_id}_PREVIEW"

        # RequirementSets
        reqsets_el = ElementTree.SubElement(root, "RequirementSets")
        rsr_el = ElementTree.SubElement(root, "RequirementSetRequirements")
        for record in self._requirement_sets:
            if not record.requirement_set_id:
                continue
            set_type = "REQUIREMENTSET_TEST_ANY" if record.logic.upper() == "ANY" else "REQUIREMENTSET_TEST_ALL"
            row_el = ElementTree.SubElement(reqsets_el, "Row")
            ElementTree.SubElement(row_el, "RequirementSetId").text = record.requirement_set_id
            ElementTree.SubElement(row_el, "RequirementSetType").text = set_type
            if record.bound_requirements:
                for req_id in record.bound_requirements:
                    bind_el = ElementTree.SubElement(rsr_el, "Row")
                    ElementTree.SubElement(bind_el, "RequirementSetId").text = record.requirement_set_id
                    ElementTree.SubElement(bind_el, "RequirementId").text = _text(req_id)

        # Requirements
        reqs_el = ElementTree.SubElement(root, "Requirements")
        req_cols: List[tuple[str, str]] = [("RequirementId", "text"), ("RequirementType", "text")]
        if any(r.inverse for r in self._requirements):
            req_cols.append(("Inverse", "bool"))
        if any(r.reverse for r in self._requirements):
            req_cols.append(("Reverse", "bool"))
        if any(r.persistent for r in self._requirements):
            req_cols.append(("Persistent", "bool"))
        if any(r.triggered for r in self._requirements):
            req_cols.append(("Triggered", "bool"))
        if any(r.likeliness for r in self._requirements):
            req_cols.append(("Likeliness", "int"))
        if any(r.impact for r in self._requirements):
            req_cols.append(("Impact", "int"))
        if any(r.progress_weight != 1 for r in self._requirements):
            req_cols.append(("ProgressWeight", "int"))
        for record in self._requirements:
            row_el = ElementTree.SubElement(reqs_el, "Row")
            for col, col_type in req_cols:
                value: object | None
                if col == "RequirementId":
                    value = record.requirement_id
                elif col == "RequirementType":
                    value = record.requirement_type
                elif col == "Inverse":
                    value = _bool_int(record.inverse)
                elif col == "Reverse":
                    value = _bool_int(record.reverse)
                elif col == "Persistent":
                    value = _bool_int(record.persistent)
                elif col == "Triggered":
                    value = _bool_int(record.triggered)
                elif col == "Likeliness":
                    value = record.likeliness
                elif col == "Impact":
                    value = record.impact
                elif col == "ProgressWeight":
                    value = record.progress_weight
                else:
                    value = None
                ElementTree.SubElement(row_el, col).text = _text(value)

        # RequirementArguments
        req_args_el = ElementTree.SubElement(root, "RequirementArguments")
        for record in self._requirements:
            for param in record.parameters:
                name = str(param.get("name", "")).strip()
                if not name:
                    continue
                row_el = ElementTree.SubElement(req_args_el, "Row")
                ElementTree.SubElement(row_el, "RequirementId").text = _text(record.requirement_id)
                ElementTree.SubElement(row_el, "Name").text = name
                ElementTree.SubElement(row_el, "Value").text = _param_value_to_xml_with_name(param.get("value"), name)

        raw = ElementTree.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(raw)
        return parsed.toprettyxml(indent="  ")

    def _apply_import_data(self, payload: Dict[str, object]) -> None:
        self._owners = []
        self._unit_ability_records = []
        self._modifiers = []
        self._requirement_sets = []
        self._requirements = []
        self._selected_owner_index = -1
        self._current_modifier_index = -1
        self._modifier_editor_index = -1
        self._current_reqset_index = -1
        self._current_req_index = -1

        prefix1 = str(payload.get("prefix1") or payload.get("prefix_1") or "")
        prefix2 = str(payload.get("prefix2") or payload.get("prefix_2") or "")
        if self._prefix_input is not None:
            self._prefix_input.setText(prefix1)
        if self._prefix2_input is not None:
            self._prefix2_input.setText(prefix2)

        owners_data = payload.get("owners", [])
        if isinstance(owners_data, list):
            for entry in owners_data:
                if not isinstance(entry, dict):
                    continue
                record = OwnerRecord(
                    table_name=str(entry.get("table_name", "")),
                    type_column=str(entry.get("type_column", "")),
                    type_name=str(entry.get("type_name", "")),
                    display_name=str(entry.get("display_name", "")),
                    source_key=str(entry.get("source_key", "")),
                    bound_modifier_ids=list(entry.get("bound_modifier_ids", []) or []),
                    owner_bindings=list(entry.get("owner_bindings", []) or []),
                )
                if record.table_name and record.type_name:
                    self._owner_binding_rows(record)
                    self._owners.append(record)

        unit_abilities_data = payload.get("unit_abilities", [])
        if isinstance(unit_abilities_data, list):
            for entry in unit_abilities_data:
                if not isinstance(entry, dict):
                    continue
                ability_type = str(entry.get("unit_ability_type") or "").strip()
                if not ability_type:
                    continue
                raw_tags = entry.get("type_tags")
                if not isinstance(raw_tags, list):
                    raw_tags = []
                self._upsert_unit_ability_record(
                    UnitAbilityRecord(
                        unit_ability_type=ability_type,
                        name_zh=str(entry.get("name_zh") or "").strip(),
                        description_zh=str(entry.get("description_zh") or "").strip(),
                        inactive=bool(entry.get("inactive", False)),
                        show_float_text_when_earned=bool(entry.get("show_float_text_when_earned", False)),
                        permanent=bool(entry.get("permanent", True)),
                        type_tags=[str(tag or "").strip() for tag in raw_tags if str(tag or "").strip()],
                    )
                )

        modifiers_data = payload.get("modifiers", [])
        if isinstance(modifiers_data, list):
            for entry in modifiers_data:
                if not isinstance(entry, dict):
                    continue
                record = ModifierRecord(
                    modifier_id=str(entry.get("modifier_id", "")),
                    modifier_type=str(entry.get("modifier_type", "")),
                    comment=str(entry.get("comment", "")),
                    owner_reqset=entry.get("owner_reqset") or None,
                    subject_reqset=entry.get("subject_reqset") or None,
                    run_once=bool(entry.get("run_once", False)),
                    new_only=bool(entry.get("new_only", False)),
                    permanent=bool(entry.get("permanent", False)),
                    owner_stack_limit=int(entry.get("owner_stack_limit", 0) or 0),
                    subject_stack_limit=int(entry.get("subject_stack_limit", 0) or 0),
                    effect_type=entry.get("effect_type") or None,
                    collection_type=entry.get("collection_type") or None,
                    preview_text=str(entry.get("preview_text", "") or ""),
                    parameters=list(entry.get("parameters", []) or []),
                )
                if record.modifier_id:
                    self._modifiers.append(record)

        reqset_data = payload.get("requirement_sets", [])
        if isinstance(reqset_data, list):
            for entry in reqset_data:
                if not isinstance(entry, dict):
                    continue
                record = RequirementSetRecord(
                    requirement_set_id=str(entry.get("requirement_set_id", "")),
                    comment=str(entry.get("comment", "")),
                    logic=str(entry.get("logic", "ALL")),
                    bound_requirements=list(entry.get("bound_requirements", []) or []),
                )
                if record.requirement_set_id:
                    self._requirement_sets.append(record)

        req_data = payload.get("requirements", [])
        if isinstance(req_data, list):
            for entry in req_data:
                if not isinstance(entry, dict):
                    continue
                record = RequirementRecord(
                    requirement_id=str(entry.get("requirement_id", "")),
                    comment=str(entry.get("comment", "")),
                    requirement_type=str(entry.get("requirement_type", "")),
                    likeliness=int(entry.get("likeliness", 0) or 0),
                    impact=int(entry.get("impact", 0) or 0),
                    progress_weight=int(entry.get("progress_weight", 1) or 1),
                    inverse=bool(entry.get("inverse", False)),
                    reverse=bool(entry.get("reverse", False)),
                    persistent=bool(entry.get("persistent", False)),
                    triggered=bool(entry.get("triggered", False)),
                    parameters=list(entry.get("parameters", []) or []),
                )
                if record.requirement_id:
                    self._requirements.append(record)

        if self._owner_tree is not None:
            self._refresh_owner_tree()
        self._update_owner_section_state()
        if self._modifier_list is not None:
            self._modifier_list.setRowCount(0)
            for record in self._modifiers:
                self._append_modifier_row(record)
        if self._reqset_list is not None:
            self._reqset_list.setRowCount(0)
            for record in self._requirement_sets:
                self._append_reqset_row(record)
        if self._req_list is not None:
            self._req_list.setRowCount(0)
            for record in self._requirements:
                self._append_requirement_row(record)

        if self._modifiers:
            self._select_modifier_row(0)
            self._on_modifier_selected()
        else:
            self._clear_modifier_editor()
            self._set_modifier_editor_enabled(False)
        if self._requirement_sets:
            self._select_reqset_row(0)
        else:
            self._clear_reqset_editor()
            self._set_reqset_editor_enabled(False)
        if self._requirements:
            self._select_requirement_row(0)
        else:
            self._clear_requirement_editor()
            self._set_requirement_editor_enabled(False)
        self._refresh_reqset_options()
        self._update_reqset_section_state()

    # -------------------- Param Table --------------------
    def _append_param_row(self, param_name: str) -> None:
        if self._param_table is None:
            return
        row = self._param_table.rowCount()
        self._param_table.insertRow(row)

        name_edit = QLineEdit(param_name)
        name_edit.textChanged.connect(lambda _t, r=row: self._refresh_param_value_widget(r))
        self._param_table.setCellWidget(row, 0, name_edit)

        value_widget = self._build_param_value_widget(param_name)
        self._param_table.setCellWidget(row, 1, value_widget)

        self._param_table.setItem(row, 0, QTableWidgetItem())
        self._param_table.setItem(row, 1, QTableWidgetItem())

    def _refresh_param_value_widget(self, row: int) -> None:
        if self._param_table is None:
            return
        name_widget = self._param_table.cellWidget(row, 0)
        if not isinstance(name_widget, QLineEdit):
            return
        old_widget = self._param_table.cellWidget(row, 1)
        old_value: object | None = None
        if isinstance(old_widget, QCheckBox):
            old_value = old_widget.isChecked()
        elif isinstance(old_widget, (QSpinBox, QDoubleSpinBox)):
            old_value = old_widget.value()
        elif isinstance(old_widget, QLineEdit):
            old_value = old_widget.text()
        elif isinstance(old_widget, BaseTemplateWidget):
            old_value = old_widget.export_data()
        param_name = name_widget.text().strip()
        value_widget = self._build_param_value_widget(param_name)
        self._param_table.setCellWidget(row, 1, value_widget)
        if old_value not in (None, ""):
            if isinstance(value_widget, QCheckBox):
                value_widget.setChecked(bool(old_value))
            elif isinstance(value_widget, (QSpinBox, QDoubleSpinBox)):
                try:
                    value_widget.setValue(float(old_value))
                except (TypeError, ValueError):
                    value_widget.setValue(0)
            elif isinstance(value_widget, QLineEdit):
                value_widget.setText(str(old_value))
            elif isinstance(value_widget, BaseTemplateWidget):
                self._apply_template_value(value_widget, old_value)

    def _build_param_value_widget(self, param_name: str) -> QWidget:
        key = param_name.strip()
        if key in BOOLEAN_PARAM_KEYS:
            cb = QCheckBox()
            cb.setChecked(False)
            return cb
        if key in INT_PARAM_KEYS:
            spin = IntParamSpinBox()
            spin.setRange(-999999, 999999)
            return spin
        template_key = TEMPLATE_PARAM_MAPPINGS.get(key)
        if template_key:
            try:
                widget = build_template_widget(template_key)
                if isinstance(widget, BaseTemplateWidget):
                    widget.setMinimumHeight(48)
                    if template_key == "unit_ability_type" and hasattr(widget, "set_options"):
                        setter = getattr(widget, "set_options")
                        try:
                            setter(self._unit_ability_template_options(), preserve_text=True)
                        except TypeError:
                            setter(self._unit_ability_template_options())
                return widget
            except KeyError:
                pass
        return QLineEdit()

    def _remove_selected_param_rows(self) -> None:
        if self._param_table is None:
            return
        selected = self._param_table.selectionModel().selectedRows()
        for index in sorted(selected, key=lambda idx: idx.row(), reverse=True):
            self._param_table.removeRow(index.row())

    def _collect_param_rows(self) -> List[Dict[str, object]]:
        if self._param_table is None:
            return []
        params: List[Dict[str, object]] = []
        for row in range(self._param_table.rowCount()):
            name_widget = self._param_table.cellWidget(row, 0)
            if not isinstance(name_widget, QLineEdit):
                continue
            name = name_widget.text().strip()
            if not name:
                continue
            value_widget = self._param_table.cellWidget(row, 1)
            value: object | None
            if isinstance(value_widget, QCheckBox):
                value = value_widget.isChecked()
            elif isinstance(value_widget, (QSpinBox, QDoubleSpinBox)):
                value = value_widget.value()
            elif isinstance(value_widget, QLineEdit):
                value = value_widget.text()
            elif isinstance(value_widget, BaseTemplateWidget):
                value = value_widget.export_data()
            else:
                value = None
            params.append({"name": name, "value": value})
        return params

    def _load_param_table(self, params: List[Dict[str, object]]) -> None:
        self._clear_param_table()
        if self._param_table is None:
            return
        for entry in params:
            name = str(entry.get("name", ""))
            self._append_param_row(name)
            self._set_param_value_for_last_row(entry.get("value"))

    def _refresh_parameters_from_effect(
        self,
        effect_type: str | None,
        preset: List[Dict[str, object]] | None = None,
    ) -> None:
        if self._param_table is None:
            return
        self._clear_param_table()
        if not effect_type:
            return
        if preset:
            self._load_param_table(preset)
            return
        param_names = self._effect_param_map.get(effect_type, [])
        for name in param_names:
            self._append_param_row(name)

    def _clear_param_table(self) -> None:
        if self._param_table is None:
            return
        self._param_table.setRowCount(0)

    def _set_param_value_for_last_row(self, value: object) -> None:
        if self._param_table is None:
            return
        row = self._param_table.rowCount() - 1
        if row < 0:
            return
        widget = self._param_table.cellWidget(row, 1)
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            try:
                widget.setValue(float(value))
            except (TypeError, ValueError):
                widget.setValue(0)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value or ""))
        elif isinstance(widget, BaseTemplateWidget):
            self._apply_template_value(widget, value)

    def _apply_template_value(self, widget: BaseTemplateWidget, value: object) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            if hasattr(widget, "set_payload"):
                getattr(widget, "set_payload")(value)
                return
            setter = getattr(widget, "set_current_value", None)
            if setter is not None:
                target = None
                if "value" in value and value.get("value") not in (None, ""):
                    target = value.get("value")
                else:
                    type_key = getattr(widget, "_type_key", None)
                    if isinstance(type_key, str) and value.get(type_key) not in (None, ""):
                        target = value.get(type_key)
                    else:
                        for key, entry in value.items():
                            if key.endswith("_type") and entry not in (None, ""):
                                target = entry
                                break
                        if target is None and value.get("display") not in (None, ""):
                            target = value.get("display")
                setter(target)
                return
            line_edit = getattr(widget, "_line_edit", None)
            if isinstance(line_edit, QLineEdit):
                display = value.get("display") if isinstance(value.get("display"), str) else None
                if display:
                    line_edit.setText(display)
                else:
                    for key, entry in value.items():
                        if key.endswith("_type") and isinstance(entry, str):
                            line_edit.setText(entry)
                            break
            if hasattr(widget, "_selected_type"):
                for key, entry in value.items():
                    if key.endswith("_type") and entry not in (None, ""):
                        setattr(widget, "_selected_type", entry)
                        break
            if hasattr(widget, "_selected_era") and value.get("era_type") not in (None, ""):
                setattr(widget, "_selected_era", value.get("era_type"))
            return
        if hasattr(widget, "set_current_value"):
            getattr(widget, "set_current_value")(value)

    # -------------------- Requirement Param Table --------------------
    def _append_req_param_row(self, param_name: str) -> None:
        if self._req_param_table is None:
            return
        row = self._req_param_table.rowCount()
        self._req_param_table.insertRow(row)

        name_edit = QLineEdit(param_name)
        self._req_param_table.setCellWidget(row, 0, name_edit)

        value_widget = self._build_param_value_widget(param_name)
        self._req_param_table.setCellWidget(row, 1, value_widget)

        self._req_param_table.setItem(row, 0, QTableWidgetItem())
        self._req_param_table.setItem(row, 1, QTableWidgetItem())

    def _remove_selected_req_param_rows(self) -> None:
        if self._req_param_table is None:
            return
        selected = self._req_param_table.selectionModel().selectedRows()
        for index in sorted(selected, key=lambda idx: idx.row(), reverse=True):
            self._req_param_table.removeRow(index.row())

    def _collect_req_param_rows(self) -> List[Dict[str, object]]:
        if self._req_param_table is None:
            return []
        params: List[Dict[str, object]] = []
        for row in range(self._req_param_table.rowCount()):
            name_widget = self._req_param_table.cellWidget(row, 0)
            if not isinstance(name_widget, QLineEdit):
                continue
            name = name_widget.text().strip()
            if not name:
                continue
            value_widget = self._req_param_table.cellWidget(row, 1)
            value: object | None
            if isinstance(value_widget, QCheckBox):
                value = value_widget.isChecked()
            elif isinstance(value_widget, (QSpinBox, QDoubleSpinBox)):
                value = value_widget.value()
            elif isinstance(value_widget, QLineEdit):
                value = value_widget.text()
            elif isinstance(value_widget, BaseTemplateWidget):
                value = value_widget.export_data()
            else:
                value = None
            params.append({"name": name, "value": value})
        return params

    def _set_req_param_value_for_last_row(self, value: object) -> None:
        if self._req_param_table is None:
            return
        row = self._req_param_table.rowCount() - 1
        if row < 0:
            return
        widget = self._req_param_table.cellWidget(row, 1)
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            try:
                widget.setValue(float(value))
            except (TypeError, ValueError):
                widget.setValue(0)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value or ""))
        elif isinstance(widget, BaseTemplateWidget):
            self._apply_template_value(widget, value)

    def _clear_req_param_table(self) -> None:
        if self._req_param_table is None:
            return
        self._req_param_table.setRowCount(0)

    def _refresh_requirement_parameters(
        self,
        req_type: str | None,
        preset: List[Dict[str, object]] | None = None,
    ) -> None:
        if self._req_param_table is None:
            return
        self._clear_req_param_table()
        if not req_type:
            return
        if preset:
            for entry in preset:
                name = str(entry.get("name", ""))
                self._append_req_param_row(name)
                self._set_req_param_value_for_last_row(entry.get("value"))
            return
        param_names = self._requirement_param_map.get(req_type, [])
        for name in param_names:
            self._append_req_param_row(name)

    # -------------------- ModifierId Default --------------------
    def _build_modifier_id_default(self) -> str:
        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""
        parts = ["MODIFIER"]
        if prefix1:
            parts.append(prefix1)
        if prefix2:
            parts.append(prefix2)
        base = "_".join(parts)
        return f"{base}_"

    def _build_modifier_id_auto(self) -> str:
        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""
        modifier_type = self._modifier_type_combo.currentText().strip() if self._modifier_type_combo else ""
        type_fragment = self._extract_modifier_type_fragment(modifier_type)
        param_fragment = self._extract_first_param_fragment()
        reqset_fragment = self._extract_modifier_reqset_fragment(prefix1, prefix2)
        parts = ["MODIFIER"]
        if prefix1:
            parts.append(prefix1)
        if prefix2:
            parts.append(prefix2)
        if type_fragment:
            parts.append(type_fragment)
        if param_fragment:
            parts.append(param_fragment)
        if reqset_fragment:
            parts.append(reqset_fragment)
        return "_".join(parts)

    def _apply_modifier_id_default(self) -> None:
        if self._modifier_id_input is None:
            return
        self._modifier_id_input.setText(self._build_modifier_id_auto())
        if self._comment_input is not None:
            self._comment_input.setText(self._build_modifier_comment_auto())

    def _build_modifier_comment_auto(self) -> str:
        reqset_comment = self._resolve_modifier_reqset_comment()
        param_comment = self._build_param_comment_from_rows(self._collect_param_rows())
        return self._join_comment_parts(reqset_comment, param_comment)

    def _resolve_modifier_reqset_comment(self) -> str:
        owner_id = self._owner_reqset_input.text().strip() if self._owner_reqset_input else ""
        subject_id = self._subject_reqset_input.text().strip() if self._subject_reqset_input else ""
        comments: List[str] = []
        for reqset_id in (owner_id, subject_id):
            if not reqset_id:
                continue
            comment = self._find_reqset_comment(reqset_id)
            if comment and comment not in comments:
                comments.append(comment)
        return " ".join(comments)

    def _find_reqset_comment(self, reqset_id: str) -> str:
        target = str(reqset_id or "").strip()
        if not target:
            return ""
        for record in self._requirement_sets:
            rid = str(getattr(record, "requirement_set_id", "") or "").strip()
            if rid == target:
                return str(getattr(record, "comment", "") or "").strip()
        return ""

    def _extract_modifier_reqset_fragment(self, prefix1: str, prefix2: str) -> str:
        owner_id = self._owner_reqset_input.text().strip() if self._owner_reqset_input else ""
        subject_id = self._subject_reqset_input.text().strip() if self._subject_reqset_input else ""
        reqset_id = owner_id or subject_id
        if not reqset_id:
            return ""
        return self._reqset_suffix_fragment(reqset_id, prefix1, prefix2)

    def _extract_modifier_type_fragment(self, modifier_type: str) -> str:
        if not modifier_type:
            return ""
        text = modifier_type.strip().upper()
        if "ADJUST_" in text:
            return text.split("ADJUST_", 1)[1].strip("_")
        if "GRANT_" in text:
            return text.split("GRANT_", 1)[1].strip("_")
        return text.strip("_")

    def _extract_first_param_fragment(self) -> str:
        params = self._collect_param_rows()
        for param in params:
            name = str(param.get("name", "")).strip()
            if not name or name.lower() == "description":
                continue
            value = param.get("value")
            if self._is_text_param(name, value):
                return self._param_to_fragment(name, value)
        for param in params:
            name = str(param.get("name", "")).strip()
            if not name or name.lower() == "description":
                continue
            value = param.get("value")
            return self._param_to_fragment(name, value)
        return ""

    def _is_text_param(self, name: str, value: object | None) -> bool:
        raw = self._extract_param_value(value)
        if isinstance(raw, bool):
            return True
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return False
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return False
            return re.fullmatch(r"-?\d+(\.\d+)?", text) is None
        return False

    def _param_to_fragment(self, name: str, value: object | None) -> str:
        name_upper = name.strip().upper()
        raw = self._extract_param_value(value)
        if isinstance(raw, str):
            text = raw.strip()
            text_up = text.upper()
            lowered = text.lower()
            if lowered in {"true", "false"}:
                return name_upper if lowered == "true" else f"NO_{name_upper}"
            if re.fullmatch(r"-?\d+(\.\d+)?", text):
                return self._normalize_numeric_text(text)
            if "_" in text_up:
                # whitelist prefixes that should keep everything after the first token
                whitelist = ("TERRAIN", "FEATURE", "TECHNOLOGY", "CIVIC", "RESOURCE")
                for p in whitelist:
                    if text_up.startswith(p + "_"):
                        return text_up.split("_", 1)[1]
                # special case for UNIT_*..._1 -> keep last two segments (e.g., XXX_1)
                if text_up.startswith("UNIT_"):
                    parts = [p for p in text_up.split("_") if p != ""]
                    if parts and parts[-1].isdigit() and len(parts) >= 2:
                        return f"{parts[-2]}_{parts[-1]}"
                return self._last_non_numeric_segment(text_up)
            return text_up
        if isinstance(raw, bool):
            return name_upper if raw else f"NO_{name_upper}"
        if isinstance(raw, (int, float)):
            return self._normalize_numeric_text(f"{raw:.6f}")
        return name_upper

    def _normalize_numeric_text(self, text: str) -> str:
        cleaned = text.strip()
        match = re.fullmatch(r"(-?\d+)(?:\.(\d+))?", cleaned)
        if not match:
            return cleaned
        int_part = match.group(1)
        dec_part = match.group(2)
        if not dec_part:
            return int_part
        dec_part = dec_part.rstrip("0")
        if not dec_part:
            return int_part
        return f"{int_part}{dec_part}"

    def _signed_amount_text(self, value: object | None) -> str:
        raw = self._extract_param_value(value)
        if isinstance(raw, bool) or raw is None:
            return ""
        try:
            number = float(str(raw).strip())
        except (TypeError, ValueError):
            return ""
        normalized = self._normalize_numeric_text(str(number))
        if not normalized:
            return ""
        if normalized.startswith("-"):
            return normalized
        return f"+{normalized}"

    def _display_text_from_value(self, value: object | None) -> str:
        if isinstance(value, dict):
            display = value.get("display")
            if isinstance(display, str) and display.strip():
                return display.strip()
        raw = self._extract_param_value(value)
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return ""
            if re.fullmatch(r"-?\d+(\.\d+)?", text):
                return ""
            return text
        return ""

    def _parameter_desc_text(self, name: str, value: object | None) -> str:
        display = self._display_text_from_value(value)
        if display:
            return display
        return self._humanize_param_name(name)

    def _humanize_param_name(self, name: str) -> str:
        text = str(name or "").strip()
        if not text:
            return ""
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", text)
        if not parts:
            return text
        return " ".join(parts)

    def _build_param_comment_from_rows(self, rows: List[Dict[str, object]]) -> str:
        amount_text = ""
        desc_text = ""
        for param in rows:
            name = str(param.get("name", "") or "").strip()
            if not name:
                continue
            value = param.get("value")
            if name.lower() == "amount":
                amount_text = self._signed_amount_text(value)
                continue
            if not desc_text:
                desc_text = self._parameter_desc_text(name, value)
        if not desc_text:
            desc_text = "参数"
        if amount_text:
            return f"{amount_text} {desc_text}".strip()
        return desc_text

    def _join_comment_parts(self, left: str, right: str) -> str:
        parts = [str(left or "").strip(), str(right or "").strip()]
        return " ".join(part for part in parts if part)

    def _reqset_suffix_fragment(self, reqset_id: str, prefix1: str, prefix2: str) -> str:
        text = str(reqset_id or "").strip().upper()
        if not text:
            return ""
        if text.startswith("REQSET_"):
            text = text[7:]
        parts = [p for p in text.split("_") if p]
        idx = 0
        p1 = str(prefix1 or "").strip().upper()
        p2 = str(prefix2 or "").strip().upper()
        if p1 and idx < len(parts) and parts[idx] == p1:
            idx += 1
        if p2 and idx < len(parts) and parts[idx] == p2:
            idx += 1
        remain = parts[idx:] if idx < len(parts) else parts
        if remain:
            return "_".join(remain)
        return self._last_non_numeric_segment(text)

    def _extract_param_value(self, value: object | None) -> object | None:
        if isinstance(value, dict):
            for key in ("value", "id", "type", "unit_type", "display", "text", "name"):
                if key in value and value[key] not in (None, ""):
                    return value[key]
            return None
        return value

    def _last_non_numeric_segment(self, text: str) -> str:
        """Return the last underscore-separated segment that is not purely numeric.

        If all segments are numeric, return the last segment. Result is upper-cased.
        """
        if not text:
            return ""
        parts = [p for p in str(text).split("_") if p != ""]
        if not parts:
            return str(text).upper()
        for seg in reversed(parts):
            if re.fullmatch(r"\d+", seg) is None:
                return seg.upper()
        return parts[-1].upper()

    def _single_binding_fragment(self, rid: str, prefix1: str, prefix2: str) -> str:
        """For a single bound requirement, return the full suffix after prefixes.

        Example: REQ_SIQI_C0032_PLOT_ADJACENT_TO_RIVER with prefix1=SIQI, prefix2=C0032
        -> PLOT_ADJACENT_TO_RIVER
        """
        if not rid:
            return ""
        text = str(rid).strip().upper()
        if text.startswith("REQ_"):
            text = text[4:]
        parts = [p for p in text.split("_") if p != ""]
        if not parts:
            return text
        idx = 0
        p1 = (prefix1 or "").strip().upper()
        p2 = (prefix2 or "").strip().upper()
        if p1 and idx < len(parts) and parts[idx] == p1:
            idx += 1
            if p2 and idx < len(parts) and parts[idx] == p2:
                idx += 1
        # remaining parts form the desired suffix
        if idx < len(parts):
            return "_".join(parts[idx:])
        # fallback to last-non-numeric segment
        return self._last_non_numeric_segment(text)

    def _build_reqset_id_default(self) -> str:
        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""
        parts = ["REQSET"]
        if prefix1:
            parts.append(prefix1)
        if prefix2:
            parts.append(prefix2)
        return f"{'_'.join(parts)}_"

    def _build_requirement_id_default(self) -> str:
        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""
        parts = ["REQ"]
        if prefix1:
            parts.append(prefix1)
        if prefix2:
            parts.append(prefix2)
        return f"{'_'.join(parts)}_"

    def _build_requirement_id_auto(self) -> str:
        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""
        req_type = self._req_type_combo.currentText().strip() if self._req_type_combo else ""
        type_fragment = self._extract_requirement_type_fragment(req_type)
        param_fragment = self._extract_first_req_param_fragment()
        parts = ["REQ"]
        if prefix1:
            parts.append(prefix1)
        if prefix2:
            parts.append(prefix2)
        if type_fragment:
            parts.append(type_fragment)
        if param_fragment:
            parts.append(param_fragment)
        return "_".join(parts)

    def _apply_requirement_id_default(self) -> None:
        if self._req_id_input is None:
            return
        self._req_id_input.setText(self._build_requirement_id_auto())
        if self._req_comment_input is not None:
            self._req_comment_input.setText(self._build_requirement_comment_auto())

    def _build_requirement_comment_auto(self) -> str:
        return self._build_param_comment_from_rows(self._collect_req_param_rows())

    def _extract_requirement_type_fragment(self, requirement_type: str) -> str:
        if not requirement_type:
            return ""
        text = requirement_type.strip().upper()
        if "REQUIREMENT_" in text:
            return text.split("REQUIREMENT_", 1)[1].strip("_")
        return text.strip("_")

    def _extract_first_req_param_fragment(self) -> str:
        params = self._collect_req_param_rows()
        for param in params:
            name = str(param.get("name", "")).strip()
            if not name or name.lower() == "description":
                continue
            value = param.get("value")
            if self._is_text_param(name, value):
                return self._param_to_fragment(name, value)
        for param in params:
            name = str(param.get("name", "")).strip()
            if not name or name.lower() == "description":
                continue
            value = param.get("value")
            return self._param_to_fragment(name, value)
        return ""

    def _generate_requirement_set_id(self) -> str:
        base = self._build_reqset_id_default()
        candidate = base
        existing = {r.requirement_set_id for r in self._requirement_sets}
        counter = 1
        while candidate in existing:
            counter += 1
            candidate = f"{base}_{counter}"
        return candidate

    def _generate_requirement_id(self) -> str:
        base = self._build_requirement_id_default()
        candidate = base
        existing = {r.requirement_id for r in self._requirements}
        counter = 1
        while candidate in existing:
            counter += 1
            candidate = f"{base}_{counter}"
        return candidate

    def _apply_reqset_id_from_bindings(self) -> None:
        record = getattr(self, "_editing_reqset", None)
        if record is None:
            return
        bound = getattr(record, "bound_requirements", []) or []
        if not bound:
            return
        # determine joiner based on logic: ALL -> _AND_ , ANY -> _OR_
        logic = str(getattr(record, "logic", "ALL") or "ALL").upper()
        joiner = "_AND_" if logic == "ALL" else "_OR_"
        # include prefix1/prefix2 like other auto-builders
        prefix1 = self._prefix_input.text().strip() if self._prefix_input else ""
        prefix2 = self._prefix2_input.text().strip() if self._prefix2_input else ""
        fragments: list[str] = []
        for b in bound:
            # bound requirement may be an object or string id
            rid = getattr(b, "requirement_id", None) or getattr(b, "id", None) or str(b)
            fragments.append(str(rid))

        parts = ["REQSET"]
        if prefix1:
            parts.append(prefix1)
        if prefix2:
            parts.append(prefix2)

        if len(fragments) == 1:
            # single binding: use full suffix after REQ_ and prefixes
            single_frag = self._single_binding_fragment(fragments[0], prefix1, prefix2)
            parts.append(single_frag)
        else:
            # multi-binding: use short fragments (last non-numeric segment)
            short_frags: list[str] = []
            for raw in fragments:
                frag = self._param_to_fragment("", raw)
                if frag:
                    short_frags.append(frag)
            parts.append(joiner.join(short_frags))

        candidate = "_".join(parts)
        # avoid duplicates: if candidate exists, append incremental suffix _2, _3 ...
        existing = {r.requirement_set_id for r in getattr(self, "_requirement_sets", [])}
        base = candidate
        counter = 2
        while candidate in existing:
            candidate = f"{base}_{counter}"
            counter += 1
        # set generated id
        if self._reqset_id_input is not None:
            self._reqset_id_input.setText(candidate)

        # --- generate Chinese comment from bound requirements ---
        # collect comments for each bound requirement id (skip empty)
        comments: list[str] = []
        all_reqs = getattr(self, "_requirements", []) or []
        for raw_rid in fragments:
            rid = str(raw_rid)
            # try to find matching RequirementRecord
            rec = next((r for r in all_reqs if getattr(r, "requirement_id", None) == rid), None)
            if rec is not None:
                txt = (getattr(rec, "comment", "") or "").strip()
                if txt:
                    comments.append(txt)
            # if not found, skip

        if comments:
            if len(comments) == 1:
                combined = comments[0]
            else:
                sep = "且" if logic == "ALL" else "或"
                combined = sep.join(comments)
        else:
            combined = ""

        if self._reqset_comment_input is not None:
            self._reqset_comment_input.setText(combined)


class ModifierWorkspacePanel(HomePage):
    """ModifiersTool 逻辑迁移层，负责与 .CIV 工程交换数据。"""

    def __init__(
        self,
        save_to_project_callback: Callable[[Dict[str, object]], None] | None = None,
        load_from_project_callback: Callable[[], Dict[str, object] | None] | None = None,
        owner_sources_provider: Callable[[], Dict[str, object] | None] | None = None,
    ) -> None:
        self._save_to_project_callback = save_to_project_callback
        self._load_from_project_callback = load_from_project_callback
        self._owner_sources_provider = owner_sources_provider
        super().__init__()
        self.setObjectName("modifierWorkspacePanel")
        self.setProperty("workspacePanel", "true")

    def export_project_payload(self) -> Dict[str, object]:
        return self.export_home_data()

    def import_project_payload(self, payload: Dict[str, object] | None) -> None:
        safe_payload = payload if isinstance(payload, dict) else {}
        self._apply_import_data(safe_payload)
        self.sync_owners_from_sections()

    @staticmethod
    def _owner_key(table_name: str, type_name: str) -> str:
        return f"{str(table_name).strip()}::{str(type_name).strip()}"

    @staticmethod
    def _resolve_entry_name(entry: Dict[str, object], index: int) -> str:
        name = str(entry.get("name") or "").strip()
        if name:
            return name
        fallback = str(entry.get("Name") or "").strip()
        if fallback:
            return fallback
        type_name = str(entry.get("type") or "").strip()
        if type_name:
            return type_name
        return f"对象{index + 1}"

    @staticmethod
    def _leader_trait_type(leader_type: str, index: int) -> str:
        base = str(leader_type or "").strip()
        if not base:
            return f"TRAIT_LEADER_CUSTOM_{index + 1}"
        short_type = base[7:] if base.startswith("LEADER_") else base
        return f"TRAIT_LEADER_{short_type}" if short_type else f"TRAIT_LEADER_CUSTOM_{index + 1}"

    @staticmethod
    def _governor_promotion_type(governor_type: str, level: int, col: int) -> str:
        if level == 0:
            return f"{governor_type}_PROMOTION_BASE"
        letter = {0: "L", 1: "M", 2: "R"}.get(col, "M")
        return f"{governor_type}_PROMOTION_{letter}{level}"

    def _merge_owner_bindings(self, target: OwnerRecord, source: OwnerRecord) -> None:
        target_rows = self._owner_binding_rows(target)
        source_rows = self._owner_binding_rows(source)
        merged_map: Dict[str, Dict[str, str]] = {
            row.get("modifier_id", ""): {
                "modifier_id": row.get("modifier_id", ""),
                "attachment_target_type": row.get("attachment_target_type", ""),
            }
            for row in target_rows
            if row.get("modifier_id", "")
        }
        for row in source_rows:
            modifier_id = row.get("modifier_id", "")
            if not modifier_id:
                continue
            existing = merged_map.get(modifier_id)
            if existing is None:
                merged_map[modifier_id] = {
                    "modifier_id": modifier_id,
                    "attachment_target_type": row.get("attachment_target_type", ""),
                }
                continue
            if not existing.get("attachment_target_type") and row.get("attachment_target_type"):
                existing["attachment_target_type"] = row.get("attachment_target_type", "")

        self._set_owner_binding_rows(target, list(merged_map.values()))

    def _build_owner_candidates_from_sections(self, sections: Dict[str, object]) -> Dict[str, OwnerRecord]:
        candidates: Dict[str, OwnerRecord] = {}

        def add_candidate(
            table_name: str,
            type_column: str,
            type_name: object,
            display_name: object = "",
            source_key: object = "",
        ) -> None:
            clean_type = str(type_name or "").strip()
            if not clean_type:
                return
            key = self._owner_key(table_name, clean_type)
            clean_display = str(display_name or "").strip() or clean_type
            clean_source = str(source_key or "").strip()
            existing = candidates.get(key)
            if existing is None:
                candidates[key] = OwnerRecord(
                    table_name=table_name,
                    type_column=type_column,
                    type_name=clean_type,
                    display_name=clean_display,
                    source_key=clean_source,
                )
                return
            if (
                (not existing.display_name or existing.display_name == existing.type_name)
                and clean_display
                and clean_display != clean_type
            ):
                existing.display_name = clean_display
            if not existing.source_key and clean_source:
                existing.source_key = clean_source

        def iter_entries(section_name: str) -> List[Dict[str, object]]:
            rows = sections.get(section_name)
            if not isinstance(rows, list):
                return []
            return [row for row in rows if isinstance(row, dict)]

        for ability in self._unit_ability_records:
            ability_type = str(ability.unit_ability_type or "").strip()
            if not ability_type:
                continue
            display = str(ability.name_zh or "").strip() or ability_type
            add_candidate(
                "UnitAbilityModifiers",
                "UnitAbilityType",
                ability_type,
                display,
                source_key=self._unit_ability_source_key(ability_type),
            )

        for index, entry in enumerate(iter_entries("文明")):
            civ_type = str(entry.get("type") or "").strip()
            civ_name = self._resolve_entry_name(entry, index)
            if civ_type:
                add_candidate("TraitModifiers", "TraitType", f"TRAIT_{civ_type}", f"{civ_name} Trait", source_key=f"civilization_trait:{index}")

        for index, entry in enumerate(iter_entries("领袖")):
            leader_type = str(entry.get("type") or "").strip()
            leader_name = self._resolve_entry_name(entry, index)
            add_candidate(
                "TraitModifiers",
                "TraitType",
                self._leader_trait_type(leader_type, index),
                f"{leader_name} Trait",
                source_key=f"leader_trait:{index}",
            )

        for index, entry in enumerate(iter_entries("区域")):
            district_type = str(entry.get("type") or "").strip()
            district_name = self._resolve_entry_name(entry, index)
            add_candidate("DistrictModifiers", "DistrictType", district_type, district_name, source_key=f"district:{index}")

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            trait_type = str(table_data.get("TraitType") or "").strip()
            add_candidate("TraitModifiers", "TraitType", trait_type, f"{district_name} Trait", source_key=f"district_trait:{index}")

        for index, entry in enumerate(iter_entries("建筑")):
            building_type = str(entry.get("type") or "").strip()
            building_name = self._resolve_entry_name(entry, index)
            add_candidate("BuildingModifiers", "BuildingType", building_type, building_name, source_key=f"building:{index}")

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            trait_type = str(table_data.get("TraitType") or "").strip()
            add_candidate("TraitModifiers", "TraitType", trait_type, f"{building_name} Trait", source_key=f"building_trait:{index}")

        for index, entry in enumerate(iter_entries("单位")):
            unit_name = self._resolve_entry_name(entry, index)
            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
            unit_abilities = subtables.get("UnitAbilityBindings") if isinstance(subtables.get("UnitAbilityBindings"), list) else entry.get("unit_ability_bindings") if isinstance(entry.get("unit_ability_bindings"), list) else []
            for ability_index, ability in enumerate(unit_abilities):
                if not isinstance(ability, dict):
                    continue
                ability_type = str(ability.get("UnitAbilityType") or "").strip()
                ability_name = str(ability.get("AbilityName") or "").strip() or f"{unit_name} Ability"
                add_candidate(
                    "UnitAbilityModifiers",
                    "UnitAbilityType",
                    ability_type,
                    ability_name,
                    source_key=f"unit_ability:{index}:{ability_index}",
                )

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            trait_type = str(table_data.get("TraitType") or "").strip()
            add_candidate("TraitModifiers", "TraitType", trait_type, f"{unit_name} Trait", source_key=f"unit_trait:{index}")

        for class_index, entry in enumerate(iter_entries("伟人")):
            class_name = self._resolve_entry_name(entry, class_index)
            individuals = entry.get("individuals") if isinstance(entry.get("individuals"), list) else []
            for individual_index, individual in enumerate(individuals):
                if not isinstance(individual, dict):
                    continue
                mode = str(individual.get("mode") or "activation").strip().lower()
                is_greatwork_mode = mode == "greatwork"
                individual_type = str(individual.get("GreatPersonIndividualType") or "").strip()
                individual_name = str(individual.get("Name") or "").strip() or f"{class_name} 个体{individual_index + 1}"
                if not is_greatwork_mode:
                    add_candidate(
                        "GreatPersonIndividualActionModifiers",
                        "GreatPersonIndividualType",
                        individual_type,
                        individual_name,
                        source_key=f"great_person_individual_action:{class_index}:{individual_index}",
                    )
                add_candidate(
                    "GreatPersonIndividualBirthModifiers",
                    "GreatPersonIndividualType",
                    individual_type,
                    individual_name,
                    source_key=f"great_person_individual_birth:{class_index}:{individual_index}",
                )

                great_works = individual.get("great_works") if isinstance(individual.get("great_works"), list) else []
                for great_work_index, great_work in enumerate(great_works):
                    if not isinstance(great_work, dict):
                        continue
                    great_work_type = str(great_work.get("GreatWorkType") or "").strip()
                    great_work_name = str(great_work.get("Name") or "").strip() or f"{individual_name} 巨作{great_work_index + 1}"
                    add_candidate(
                        "GreatWorkModifiers",
                        "GreatWorkType",
                        great_work_type,
                        great_work_name,
                        source_key=f"great_work:{class_index}:{individual_index}:{great_work_index}",
                    )

        for index, entry in enumerate(iter_entries("改良设施")):
            improvement_type = str(entry.get("type") or "").strip()
            improvement_name = self._resolve_entry_name(entry, index)
            add_candidate("ImprovementModifiers", "ImprovementType", improvement_type, improvement_name, source_key=f"improvement:{index}")

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            trait_type = str(table_data.get("TraitType") or "").strip()
            add_candidate("TraitModifiers", "TraitType", trait_type, f"{improvement_name} Trait", source_key=f"improvement_trait:{index}")

        for index, entry in enumerate(iter_entries("项目")):
            project_type = str(entry.get("type") or entry.get("ProjectType") or "").strip()
            project_name = self._resolve_entry_name(entry, index)
            add_candidate("ProjectCompletionModifiers", "ProjectType", project_type, project_name, source_key=f"project:{index}")

        for index, entry in enumerate(iter_entries("政策卡")):
            policy_type = str(entry.get("type") or "").strip()
            policy_name = self._resolve_entry_name(entry, index)
            add_candidate("PolicyModifiers", "PolicyType", policy_type, policy_name, source_key=f"policy:{index}")

        for index, entry in enumerate(iter_entries("信仰")):
            belief_type = str(entry.get("type") or "").strip()
            belief_name = self._resolve_entry_name(entry, index)
            add_candidate("BeliefModifiers", "BeliefType", belief_type, belief_name, source_key=f"belief:{index}")

        for index, entry in enumerate(iter_entries("总督")):
            governor_type = str(entry.get("GovernorType") or entry.get("type") or "").strip()
            governor_name = self._resolve_entry_name(entry, index)
            add_candidate("GovernorModifiers", "GovernorType", governor_type, governor_name, source_key=f"governor:{index}")

            trait_type = str(entry.get("TraitType") or "").strip()
            add_candidate("TraitModifiers", "TraitType", trait_type, f"{governor_name} Trait", source_key=f"governor_trait:{index}")

            if governor_type:
                promotions = entry.get("promotions") if isinstance(entry.get("promotions"), dict) else {}
                base_payload = promotions.get("base") if isinstance(promotions.get("base"), dict) else {}
                base_name = str(base_payload.get("name") or "").strip() or f"{governor_name} 基础晋升"
                add_candidate(
                    "GovernorPromotionModifiers",
                    "GovernorPromotionType",
                    self._governor_promotion_type(governor_type, 0, 1),
                    base_name,
                    source_key=f"governor_promotion:{index}:0:1",
                )

                tiers = promotions.get("tiers") if isinstance(promotions.get("tiers"), list) else []
                for level in range(1, 4):
                    row_data = tiers[level - 1] if level - 1 < len(tiers) and isinstance(tiers[level - 1], list) else []
                    for col in range(3):
                        node = row_data[col] if col < len(row_data) and isinstance(row_data[col], dict) else {}
                        if not bool(node.get("enabled", False)):
                            continue
                        promotion_name = str(node.get("name") or "").strip() or f"{governor_name} 晋升{level}-{col + 1}"
                        add_candidate(
                            "GovernorPromotionModifiers",
                            "GovernorPromotionType",
                            self._governor_promotion_type(governor_type, level, col),
                            promotion_name,
                            source_key=f"governor_promotion:{index}:{level}:{col}",
                        )

        LOGGER.debug("Owner candidates rebuilt from sections: total=%d", len(candidates))
        return candidates

    def sync_owners_from_sections(self, sections: Dict[str, object] | None = None) -> None:
        source_sections = sections
        if source_sections is None and callable(getattr(self, "_owner_sources_provider", None)):
            source_sections = self._owner_sources_provider()
        if not isinstance(source_sections, dict):
            return

        current_selected_key: str | None = None
        if 0 <= self._selected_owner_index < len(self._owners):
            selected_owner = self._owners[self._selected_owner_index]
            current_selected_key = self._owner_key(selected_owner.table_name, selected_owner.type_name)

        existing_by_key = {
            self._owner_key(owner.table_name, owner.type_name): owner
            for owner in self._owners
        }
        existing_by_source = {
            owner.source_key: owner
            for owner in self._owners
            if owner.source_key
        }
        candidates = self._build_owner_candidates_from_sections(source_sections)

        changed = False
        for key, candidate in candidates.items():
            existing = existing_by_key.get(key)
            if existing is None:
                source_owner: OwnerRecord | None = None
                if candidate.source_key:
                    source_owner = existing_by_source.get(candidate.source_key)
                if source_owner is None and candidate.table_name == "UnitAbilityModifiers":
                    legacy_candidates = [
                        owner
                        for owner in self._owners
                        if owner.table_name == candidate.table_name and not owner.source_key
                    ]
                    if candidate.display_name:
                        matched = [owner for owner in legacy_candidates if owner.display_name.strip() == candidate.display_name.strip()]
                        if len(matched) == 1:
                            source_owner = matched[0]
                    if source_owner is None and len(legacy_candidates) == 1:
                        source_owner = legacy_candidates[0]
                if source_owner is not None and source_owner.table_name == candidate.table_name:
                    target = existing_by_key.get(key)
                    if target is not None and target is not source_owner:
                        self._merge_owner_bindings(target, source_owner)
                        if candidate.display_name:
                            target.display_name = candidate.display_name
                        if candidate.source_key and not target.source_key:
                            target.source_key = candidate.source_key
                        if source_owner in self._owners:
                            self._owners.remove(source_owner)
                        changed = True
                        existing_by_key[key] = target
                        if candidate.source_key:
                            existing_by_source[candidate.source_key] = target
                        continue

                    old_key = self._owner_key(source_owner.table_name, source_owner.type_name)
                    source_owner.table_name = candidate.table_name
                    source_owner.type_column = candidate.type_column
                    source_owner.type_name = candidate.type_name
                    if candidate.display_name:
                        source_owner.display_name = candidate.display_name
                    if candidate.source_key:
                        source_owner.source_key = candidate.source_key
                    changed = True
                    existing_by_key.pop(old_key, None)
                    existing_by_key[key] = source_owner
                    if candidate.source_key:
                        existing_by_source[candidate.source_key] = source_owner
                    continue

                self._owners.append(
                    OwnerRecord(
                        table_name=candidate.table_name,
                        type_column=candidate.type_column,
                        type_name=candidate.type_name,
                        display_name=candidate.display_name,
                        source_key=candidate.source_key,
                        bound_modifier_ids=[],
                    )
                )
                changed = True
                existing_by_key[key] = self._owners[-1]
                if candidate.source_key:
                    existing_by_source[candidate.source_key] = self._owners[-1]
                continue

            if not existing.type_column and candidate.type_column:
                existing.type_column = candidate.type_column
                changed = True
            new_display = candidate.display_name.strip() if candidate.display_name else ""
            if new_display and new_display != (existing.display_name or "").strip():
                existing.display_name = new_display
                changed = True
            if candidate.source_key and candidate.source_key != existing.source_key:
                existing.source_key = candidate.source_key
                changed = True

        if not changed:
            LOGGER.debug("Owner sync skipped: no changes detected.")
            return

        reselect_index: int | None = None
        if current_selected_key is not None:
            for index, owner in enumerate(self._owners):
                if self._owner_key(owner.table_name, owner.type_name) == current_selected_key:
                    reselect_index = index
                    break

        self._refresh_owner_tree(select_index=reselect_index)
        self._update_owner_section_state()
        LOGGER.info("Owner sync applied: owners=%d selected=%s", len(self._owners), str(reselect_index))

    def generate_sql_preview_text(self) -> str:
        self._persist_current_modifier()
        self._persist_current_reqset(refresh_list=False)
        self._persist_current_requirement()
        return self._build_sql_preview_text()

    def generate_xml_preview_text(self) -> str:
        self._persist_current_modifier()
        self._persist_current_reqset(refresh_list=False)
        self._persist_current_requirement()
        return self._build_xml_preview_text()

    def _build_home_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(0)
        footer.setVisible(False)
        return footer

    def _handle_save_data(self) -> None:
        if self._save_to_project_callback is None:
            super()._handle_save_data()
            return
        try:
            payload = self.export_project_payload()
            self._save_to_project_callback(payload)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", f"无法保存到当前工程：{exc}")
            return
        QMessageBox.information(self, "保存成功", "修改器数据已写入当前 .CIV 工程。")

    def _handle_import_data(self) -> None:
        if self._load_from_project_callback is None:
            super()._handle_import_data()
            return
        try:
            payload = self._load_from_project_callback()
            self.import_project_payload(payload)
        except Exception as exc:
            QMessageBox.warning(self, "导入失败", f"无法从当前工程读取：{exc}")
            return
        QMessageBox.information(self, "导入成功", "已从当前 .CIV 工程载入修改器数据。")
