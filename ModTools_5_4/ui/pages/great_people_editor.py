from __future__ import annotations

from copy import deepcopy
import sqlite3
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QHeaderView,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...app.settings_store import load_settings
from ...db.paths import DEFAULT_GAME_DB
from ..ui_widget_kit import BaseTemplateWidget, IconTokenTextEdit, NewlineTokenTextEdit, build_template_widget


def _safe_text(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def _sanitize_short_token(value: object | None) -> str:
    raw = _safe_text(value)
    if not raw:
        return ""
    cleaned = []
    for ch in raw:
        if ch.isalnum() or ch == "_":
            cleaned.append(ch)
    return "".join(cleaned).upper()


def _build_type(shared: dict[str, object], head: str, midfix_code: str, short_name: object | None) -> str:
    prefix = _safe_text(shared.get("prefix")).upper()
    try:
        infix = max(0, int(shared.get("infix", 0)))
    except (TypeError, ValueError):
        infix = 0
    short = _sanitize_short_token(short_name)

    parts = [head]
    if prefix:
        parts.append(prefix)
    if infix > 0:
        parts.append(f"{midfix_code}{infix:04d}")
    if short:
        parts.append(short)
    return "_".join(parts)


def _active_db_path() -> Path:
    configured = Path(str(load_settings().game_db_path or "")).expanduser()
    if configured.exists():
        return configured
    return DEFAULT_GAME_DB


def _query_distinct_values(table_name: str, column_name: str) -> list[str]:
    db_path = _active_db_path()
    if not db_path.exists():
        return []

    sql = (
        f"SELECT DISTINCT {column_name} "
        f"FROM {table_name} "
        f"WHERE {column_name} IS NOT NULL AND TRIM({column_name}) <> '' "
        f"ORDER BY {column_name}"
    )
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(sql)
        values = [str(row[0] or "").strip() for row in cursor.fetchall()]
        deduped: list[str] = []
        seen: set[str] = set()
        for item in values:
            if not item:
                continue
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped
    except sqlite3.Error:
        return []
    finally:
        conn.close()


class _ValueSearchDialog(QDialog):
    def __init__(self, title: str, values: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(620, 420)
        self._all_values = list(values)
        self._selected = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("输入关键字过滤选项")
        root.addWidget(self._search)

        self._table = QTableWidget(0, 1)
        self._table.setHorizontalHeaderLabels(["参数候选值"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._accept_current)
        root.addWidget(self._table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._search.textChanged.connect(self._refresh)
        self._refresh("")

    def _refresh(self, keyword: str) -> None:
        key = keyword.strip().lower()
        rows = [item for item in self._all_values if not key or key in item.lower()]
        self._table.setRowCount(len(rows))
        for idx, value in enumerate(rows):
            self._table.setItem(idx, 0, QTableWidgetItem(value))

    def _accept_current(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            self.reject()
            return
        item = self._table.item(row, 0)
        self._selected = "" if item is None else _safe_text(item.text())
        if not self._selected:
            self.reject()
            return
        self.accept()

    def selected_value(self) -> str:
        return self._selected


class DistinctValueEditableTemplate(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, table_name: str, column_name: str, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._table_name = table_name
        self._column_name = column_name

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._combo.setPlaceholderText(placeholder)
        row.addWidget(self._combo, 1)

        self._search_btn = QToolButton()
        self._search_btn.setText("…")
        row.addWidget(self._search_btn)

        self._reload_options()
        self._combo.currentIndexChanged.connect(self.dataChanged.emit)
        self._combo.editTextChanged.connect(lambda *_args: self.dataChanged.emit())
        self._search_btn.clicked.connect(self._open_search)

    def _reload_options(self) -> None:
        values = _query_distinct_values(self._table_name, self._column_name)
        current = self.value()
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("")
        for item in values:
            self._combo.addItem(item)
        self._combo.setCurrentText(current)
        self._combo.blockSignals(False)

    def _open_search(self) -> None:
        values = _query_distinct_values(self._table_name, self._column_name)
        dialog = _ValueSearchDialog(f"选择 {self._column_name}", values, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        selected = dialog.selected_value()
        if not selected:
            return
        self.set_value(selected)
        self.dataChanged.emit()

    def value(self) -> str:
        return _safe_text(self._combo.currentText())

    def set_value(self, value: object | None) -> None:
        self._combo.setCurrentText(_safe_text(value))

    def set_read_only(self, read_only: bool) -> None:
        self._combo.setEnabled(not read_only)
        self._search_btn.setEnabled(not read_only)


class GreatPersonIndividualEditor(QWidget):
    dataChanged = pyqtSignal()

    _ERA_OPTIONS = [
        "ERA_ANCIENT",
        "ERA_CLASSICAL",
        "ERA_MEDIEVAL",
        "ERA_RENAISSANCE",
        "ERA_INDUSTRIAL",
        "ERA_MODERN",
        "ERA_ATOMIC",
        "ERA_INFORMATION",
        "ERA_FUTURE",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._internal_updating = False
        self._class_type_provider: Callable[[], str] | None = None

        self._activation_radio = QRadioButton("激活类伟人")
        self._greatwork_radio = QRadioButton("巨作类伟人")
        self._activation_radio.setChecked(True)
        self._kind_group = QButtonGroup(self)
        self._kind_group.setExclusive(True)
        self._kind_group.addButton(self._activation_radio)
        self._kind_group.addButton(self._greatwork_radio)

        self._abbr_edit = QLineEdit()
        self._abbr_edit.setPlaceholderText("个体简称")
        self._type_label = QLabel("")
        self._type_label.setObjectName("pageInfoLabel")

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("伟人个体名称（中文）")
        self._class_type_label = QLabel("")
        self._class_type_label.setObjectName("pageInfoLabel")

        self._era_combo = QComboBox()
        self._era_combo.addItems(self._ERA_OPTIONS)
        self._action_charges_spin = QSpinBox()
        self._action_charges_spin.setRange(0, 99)
        self._action_charges_spin.setValue(1)
        self._gender_combo = QComboBox()
        self._gender_combo.addItems(["M", "F"])
        self._area_highlight_radius = QSpinBox()
        self._area_highlight_radius.setRange(-1, 9999)
        self._area_highlight_radius.setValue(0)

        self._bool_fields: dict[str, QCheckBox] = {}
        self._number_fields: dict[str, QSpinBox] = {}
        self._text_template_fields: dict[str, BaseTemplateWidget] = {}
        self._text_template_value_keys: dict[str, str] = {}
        self._greatworks: list[dict[str, object]] = []
        self._current_greatwork_index = -1
        self._build_active_fields()

        self._active_panel = QWidget()
        active_root = QVBoxLayout(self._active_panel)
        active_root.setContentsMargins(0, 0, 0, 0)
        active_root.setSpacing(8)
        active_root.addWidget(self._build_two_col_group("激活参数 - 布尔条件", self._bool_fields, mode="bool"))
        active_root.addWidget(self._build_two_col_group("激活参数 - 数值条件", self._number_fields, mode="number"))
        active_root.addWidget(self._build_single_col_group("激活参数 - 文本条件", self._text_template_fields))

        self._greatwork_add_btn = QPushButton("添加巨作")
        self._greatwork_list = QListWidget()
        self._greatwork_abbr_edit = QLineEdit()
        self._greatwork_abbr_edit.setPlaceholderText("巨作简称")
        self._greatwork_type_label = QLabel("")
        self._greatwork_type_label.setObjectName("pageInfoLabel")
        self._greatwork_name_edit = QLineEdit()
        self._greatwork_name_edit.setPlaceholderText("巨作名称（中文）")
        self._greatwork_object_widget = build_template_widget("great_work_object_type")
        self._greatwork_audio_widget = DistinctValueEditableTemplate("GreatWorks", "Audio", "选择 Audio")
        self._greatwork_image_widget = DistinctValueEditableTemplate("GreatWorks", "Image", "选择 Image")
        self._greatwork_quote_edit = QLineEdit()
        self._greatwork_quote_edit.setPlaceholderText("Quote 输入中文")
        self._greatwork_tourism_spin = QSpinBox()
        self._greatwork_tourism_spin.setRange(0, 9999)
        self._greatwork_tourism_spin.setValue(1)
        self._greatwork_era_combo = QComboBox()
        self._greatwork_era_combo.addItem("")
        self._greatwork_era_combo.addItems(self._ERA_OPTIONS)
        self._greatwork_yield_table = QTableWidget(0, 2)
        self._greatwork_yield_table.setHorizontalHeaderLabels(["YieldType", "YieldChange"])
        yield_header = self._greatwork_yield_table.horizontalHeader()
        yield_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        yield_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        yield_header.setStretchLastSection(False)
        self._greatwork_add_yield_btn = QPushButton("新增产出行")
        self._greatwork_remove_yield_btn = QPushButton("删除产出行")
        self._greatwork_editor_box = self._build_greatwork_editor_box()

        self._greatwork_panel = QWidget()
        greatwork_root = QVBoxLayout(self._greatwork_panel)
        greatwork_root.setContentsMargins(0, 0, 0, 0)
        greatwork_root.setSpacing(8)

        greatwork_btn_row = QHBoxLayout()
        greatwork_btn_row.setContentsMargins(0, 0, 0, 0)
        greatwork_btn_row.setSpacing(6)
        greatwork_btn_row.addWidget(self._greatwork_add_btn)
        greatwork_btn_row.addStretch(1)
        greatwork_root.addLayout(greatwork_btn_row)

        greatwork_content = QHBoxLayout()
        greatwork_content.setContentsMargins(0, 0, 0, 0)
        greatwork_content.setSpacing(8)
        greatwork_content.addWidget(self._greatwork_list, 0)
        greatwork_content.addWidget(self._greatwork_editor_box, 1)
        greatwork_root.addLayout(greatwork_content)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._active_panel)
        self._stack.addWidget(self._greatwork_panel)

        common_group = QGroupBox("GreatPersonIndividuals 通用参数")
        common_form = QFormLayout()
        self._add_form_row(common_form, "简称", "abbr", self._abbr_edit)
        self._add_form_row(common_form, "个体类型", "GreatPersonIndividualType", self._type_label)
        self._add_form_row(common_form, "伟人名字", "Name", self._name_edit)
        self._add_form_row(common_form, "所属伟人类型", "GreatPersonClassType", self._class_type_label)
        self._add_form_row(common_form, "出现时代", "EraType", self._era_combo)
        self._add_form_row(common_form, "可用次数", "ActionCharges", self._action_charges_spin)
        self._add_form_row(common_form, "性别", "Gender", self._gender_combo)
        self._add_form_row(common_form, "高亮半径", "AreaHighlightRadius", self._area_highlight_radius)
        common_group.setLayout(common_form)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self._activation_radio)
        mode_row.addWidget(self._greatwork_radio)
        mode_row.addStretch(1)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        root.addLayout(mode_row)
        root.addWidget(common_group)
        root.addWidget(self._stack)
        root.addStretch(1)
        self.setLayout(root)

        self._activation_radio.toggled.connect(self._handle_mode_changed)
        self._greatwork_radio.toggled.connect(self._handle_mode_changed)
        self._abbr_edit.textChanged.connect(self._handle_abbr_changed)
        self._name_edit.textChanged.connect(lambda *_args: self._emit_data_changed())
        self._era_combo.currentIndexChanged.connect(lambda *_args: self._emit_data_changed())
        self._action_charges_spin.valueChanged.connect(lambda *_args: self._emit_data_changed())
        self._gender_combo.currentIndexChanged.connect(lambda *_args: self._emit_data_changed())
        self._area_highlight_radius.valueChanged.connect(lambda *_args: self._emit_data_changed())

        self._greatwork_add_btn.clicked.connect(self._handle_add_greatwork)
        self._greatwork_list.currentRowChanged.connect(self._handle_greatwork_selection_changed)
        self._greatwork_abbr_edit.textChanged.connect(self._handle_greatwork_abbr_changed)
        self._greatwork_name_edit.textChanged.connect(lambda *_args: self._handle_greatwork_field_changed())
        self._greatwork_object_widget.dataChanged.connect(self._handle_greatwork_field_changed)
        self._greatwork_audio_widget.dataChanged.connect(self._handle_greatwork_field_changed)
        self._greatwork_image_widget.dataChanged.connect(self._handle_greatwork_field_changed)
        self._greatwork_quote_edit.textChanged.connect(lambda *_args: self._handle_greatwork_field_changed())
        self._greatwork_tourism_spin.valueChanged.connect(lambda *_args: self._handle_greatwork_field_changed())
        self._greatwork_era_combo.currentIndexChanged.connect(lambda *_args: self._handle_greatwork_field_changed())
        self._greatwork_add_yield_btn.clicked.connect(self._handle_add_yield_row)
        self._greatwork_remove_yield_btn.clicked.connect(self._handle_remove_yield_row)

        for widget in self._bool_fields.values():
            widget.toggled.connect(lambda *_args: self._emit_data_changed())
        for widget in self._number_fields.values():
            widget.valueChanged.connect(lambda *_args: self._emit_data_changed())
        for widget in self._text_template_fields.values():
            widget.dataChanged.connect(self._emit_data_changed)

        self._handle_mode_changed()
        self._refresh_type_label()
        self._set_greatwork_editor_enabled(False)

    @staticmethod
    def _field_desc_map() -> dict[str, str]:
        return {
            "ActionRequiresOwnedTile": "需要位于己方地块",
            "ActionRequiresUnownedTile": "需要位于无主地块",
            "ActionRequiresAdjacentMountain": "需要相邻山脉",
            "ActionRequiresAdjacentOwnedTile": "需要相邻己方地块",
            "ActionRequiresAdjacentBarbarianUnit": "需要相邻蛮族单位",
            "ActionRequiresOnOrAdjacentNaturalWonder": "需要位于或相邻自然奇观",
            "ActionRequiresIncompleteWonder": "需要目标奇观未完工",
            "ActionRequiresIncompleteSpaceRaceProject": "需要未完成太空竞赛项目",
            "ActionRequiresVisibleLuxury": "需要可见奢侈资源",
            "ActionRequiresNoMilitaryUnit": "需要无军事单位",
            "ActionRequiresPlayerRelicSlot": "需要玩家存在可用遗物槽位",
            "ActionEffectTileHighlighting": "行动触发地块高亮",
            "ActionRequiresEnemyTerritory": "需要敌方领土",
            "ActionRequiresCityStateTerritory": "需要城邦领土",
            "ActionRequiresNonHostileTerritory": "需要非敌对领土",
            "ActionRequiresSuzerainTerritory": "需要宗主国领土",
            "ActionRequiresUnitCanGainExperience": "目标单位可获得经验",
            "ActionRequiresOnOrAdjacentFeatureType": "要求地貌类型",
            "ActionRequiresMilitaryUnitDomain": "要求军事单位领域",
            "ActionRequiresUnitMilitaryFormation": "要求单位编队类型",
            "ActionRequiresNearbyUnitWithTagA": "附近要求单位标签A",
            "ActionRequiresNearbyUnitWithTagB": "附近要求单位标签B",
            "ActionRequiresCityGreatWorkObjectType": "城市需存在巨作类型",
            "ActionRequiresCompletedDistrictType": "要求已完成区域类型",
            "ActionRequiresMissingBuildingType": "要求缺失建筑类型",
            "ActionNameTextOverride": "行动名称文本Tag（默认 LOC_GREATPERSON_ACTION_NAME_RETIRE）",
            "ActionEffectTextOverride": "行动效果文本（输入中文，SQL自动转LOC）",
            "BirthNameTextOverride": "诞生名称文本Tag（输入LOC tag）",
            "BirthEffectTextOverride": "诞生效果文本Tag（输入LOC tag）",
            "ActionRequiresLandMilitaryUnitWithinXTiles": "范围内有陆军单位",
            "ActionRequiresEnemyMilitaryUnitWithinXTiles": "范围内有敌军单位",
            "ActionRequiresGoldCost": "行动金币花费",
        }

    def _build_active_fields(self) -> None:
        bool_keys = [
            "ActionRequiresOwnedTile",
            "ActionRequiresUnownedTile",
            "ActionRequiresAdjacentMountain",
            "ActionRequiresAdjacentOwnedTile",
            "ActionRequiresAdjacentBarbarianUnit",
            "ActionRequiresOnOrAdjacentNaturalWonder",
            "ActionRequiresIncompleteWonder",
            "ActionRequiresIncompleteSpaceRaceProject",
            "ActionRequiresVisibleLuxury",
            "ActionRequiresNoMilitaryUnit",
            "ActionRequiresPlayerRelicSlot",
            "ActionEffectTileHighlighting",
            "ActionRequiresEnemyTerritory",
            "ActionRequiresCityStateTerritory",
            "ActionRequiresNonHostileTerritory",
            "ActionRequiresSuzerainTerritory",
            "ActionRequiresUnitCanGainExperience",
        ]
        for key in bool_keys:
            check = QCheckBox()
            check.setChecked(key in {"ActionRequiresOwnedTile", "ActionEffectTileHighlighting"})
            self._bool_fields[key] = check

        text_templates: dict[str, tuple[str, str]] = {
            "ActionRequiresOnOrAdjacentFeatureType": ("feature_all", "feature_type"),
            "ActionRequiresMilitaryUnitDomain": ("domain", "domain_type"),
            "ActionRequiresUnitMilitaryFormation": ("formation_class", "formation_class"),
            "ActionRequiresNearbyUnitWithTagA": ("ability_class_tag", "tag"),
            "ActionRequiresNearbyUnitWithTagB": ("ability_class_tag", "tag"),
            "ActionRequiresCityGreatWorkObjectType": ("great_work_object_type", "great_work_object_type"),
            "ActionRequiresCompletedDistrictType": ("district_search", "district_type"),
            "ActionRequiresMissingBuildingType": ("building_search_all", "building_type"),
            "ActionNameTextOverride": ("text", "text"),
            "ActionEffectTextOverride": ("text", "text"),
            "BirthNameTextOverride": ("text", "text"),
            "BirthEffectTextOverride": ("text", "text"),
        }
        for key, (template_key, value_key) in text_templates.items():
            widget = build_template_widget(template_key)
            if hasattr(widget, "set_label_text"):
                try:
                    getattr(widget, "set_label_text")("")
                except TypeError:
                    pass
            self._text_template_fields[key] = widget
            self._text_template_value_keys[key] = value_key

        int_keys = [
            "ActionRequiresLandMilitaryUnitWithinXTiles",
            "ActionRequiresEnemyMilitaryUnitWithinXTiles",
            "ActionRequiresGoldCost",
        ]
        for key in int_keys:
            spin = QSpinBox()
            spin.setRange(-1, 9999)
            spin.setValue(0)
            self._number_fields[key] = spin

    def _add_form_row(self, form: QFormLayout, zh_label: str, english_key: str, widget: QWidget) -> None:
        label = QLabel(zh_label)
        label.setToolTip(english_key)
        widget.setToolTip(english_key)
        form.addRow(label, widget)

    def _build_two_col_group(self, title: str, fields: dict[str, QWidget], mode: str) -> QGroupBox:
        group = QGroupBox(title)
        grid = QGridLayout()
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        desc_map = self._field_desc_map()
        keys = list(fields.keys())
        pairs = [keys[i : i + 2] for i in range(0, len(keys), 2)]
        row_index = 0
        for pair in pairs:
            for col_index, key in enumerate(pair):
                label = QLabel(desc_map.get(key, "参数"))
                widget = fields[key]
                label.setToolTip(key)
                widget.setToolTip(key)
                base_col = col_index * 2
                grid.addWidget(label, row_index, base_col)
                grid.addWidget(widget, row_index, base_col + 1)
                if mode == "bool" and isinstance(widget, QCheckBox):
                    widget.setText("启用")
            row_index += 1

        group.setLayout(grid)
        return group

    def _build_single_col_group(self, title: str, fields: dict[str, QWidget]) -> QGroupBox:
        group = QGroupBox(title)
        layout = QFormLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        desc_map = self._field_desc_map()
        for key, widget in fields.items():
            label = QLabel(desc_map.get(key, "参数"))
            label.setToolTip(key)
            widget.setToolTip(key)
            layout.addRow(label, widget)

        group.setLayout(layout)
        return group

    def _build_greatwork_editor_box(self) -> QGroupBox:
        group = QGroupBox("巨作编辑区")
        root = QVBoxLayout(group)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        form = QFormLayout()
        self._add_form_row(form, "简称", "abbr", self._greatwork_abbr_edit)
        self._add_form_row(form, "巨作类型ID", "GreatWorkType", self._greatwork_type_label)
        self._add_form_row(form, "巨作对象", "GreatWorkObjectType", self._greatwork_object_widget)
        self._add_form_row(form, "巨作名称", "Name", self._greatwork_name_edit)
        self._add_form_row(form, "Audio", "Audio", self._greatwork_audio_widget)
        self._add_form_row(form, "Image", "Image", self._greatwork_image_widget)
        self._add_form_row(form, "Quote（中文）", "Quote", self._greatwork_quote_edit)
        self._add_form_row(form, "旅游业绩", "Tourism", self._greatwork_tourism_spin)
        self._add_form_row(form, "时代", "EraType", self._greatwork_era_combo)
        root.addLayout(form)

        yield_title = QLabel("GreatWork_YieldChanges")
        yield_title.setObjectName("pageInfoLabel")
        root.addWidget(yield_title)
        root.addWidget(self._greatwork_yield_table)

        yield_btn_row = QHBoxLayout()
        yield_btn_row.setContentsMargins(0, 0, 0, 0)
        yield_btn_row.setSpacing(6)
        yield_btn_row.addWidget(self._greatwork_add_yield_btn)
        yield_btn_row.addWidget(self._greatwork_remove_yield_btn)
        yield_btn_row.addStretch(1)
        root.addLayout(yield_btn_row)
        return group

    @staticmethod
    def _yield_type_options() -> list[tuple[str, str]]:
        return [
            ("金币", "YIELD_GOLD"),
            ("生产力", "YIELD_PRODUCTION"),
            ("科技", "YIELD_SCIENCE"),
            ("文化", "YIELD_CULTURE"),
            ("信仰", "YIELD_FAITH"),
            ("食物", "YIELD_FOOD"),
        ]

    def _create_yield_type_combo(self, selected: str | None = None) -> QComboBox:
        combo = QComboBox()
        for label, value in self._yield_type_options():
            combo.addItem(f"{label} | {value}", value)
        index = combo.findData(_safe_text(selected))
        combo.setCurrentIndex(0 if index < 0 else index)
        combo.currentIndexChanged.connect(lambda *_args: self._handle_greatwork_field_changed())
        return combo

    def _create_yield_change_spin(self, value: int = 0) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(-9999, 9999)
        spin.setValue(int(value))
        spin.valueChanged.connect(lambda *_args: self._handle_greatwork_field_changed())
        return spin

    def _clear_yield_rows(self) -> None:
        self._greatwork_yield_table.setRowCount(0)

    def _append_yield_row(self, yield_type: str = "YIELD_CULTURE", yield_change: int = 0) -> None:
        row = self._greatwork_yield_table.rowCount()
        self._greatwork_yield_table.insertRow(row)
        self._greatwork_yield_table.setCellWidget(row, 0, self._create_yield_type_combo(yield_type))
        self._greatwork_yield_table.setCellWidget(row, 1, self._create_yield_change_spin(yield_change))

    def _collect_yield_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in range(self._greatwork_yield_table.rowCount()):
            yield_combo = self._greatwork_yield_table.cellWidget(row, 0)
            change_spin = self._greatwork_yield_table.cellWidget(row, 1)
            if not isinstance(yield_combo, QComboBox) or not isinstance(change_spin, QSpinBox):
                continue
            yield_type = _safe_text(yield_combo.currentData())
            if not yield_type:
                continue
            rows.append(
                {
                    "YieldType": yield_type,
                    "YieldChange": int(change_spin.value()),
                }
            )
        return rows

    def _refresh_greatwork_type_label(self) -> None:
        short = _sanitize_short_token(self._greatwork_abbr_edit.text())
        self._greatwork_type_label.setText(f"GREATWORK_{short}" if short else "")

    def _resolve_greatwork_item_title(self, payload: dict[str, object], index: int) -> str:
        name = _safe_text(payload.get("Name"))
        if name:
            return name
        gw_type = _safe_text(payload.get("GreatWorkType"))
        if gw_type:
            return gw_type
        return "未命名巨作" if index < 0 else f"未命名巨作 {index + 1}"

    def _set_greatwork_editor_enabled(self, enabled: bool) -> None:
        for widget in (
            self._greatwork_abbr_edit,
            self._greatwork_object_widget,
            self._greatwork_name_edit,
            self._greatwork_audio_widget,
            self._greatwork_image_widget,
            self._greatwork_quote_edit,
            self._greatwork_tourism_spin,
            self._greatwork_era_combo,
            self._greatwork_yield_table,
            self._greatwork_add_yield_btn,
            self._greatwork_remove_yield_btn,
        ):
            widget.setEnabled(enabled)

    def _set_greatwork_payload(self, payload: dict[str, object]) -> None:
        self._greatwork_abbr_edit.setText(_safe_text(payload.get("abbr")))
        self._refresh_greatwork_type_label()
        self._set_template_value(self._greatwork_object_widget, payload.get("GreatWorkObjectType"))
        self._greatwork_name_edit.setText(_safe_text(payload.get("Name")))
        self._greatwork_audio_widget.set_value(payload.get("Audio"))
        self._greatwork_image_widget.set_value(payload.get("Image"))
        self._greatwork_quote_edit.setText(_safe_text(payload.get("Quote")))
        self._greatwork_tourism_spin.setValue(int(payload.get("Tourism", 1) or 1))
        era_value = _safe_text(payload.get("EraType"))
        era_index = self._greatwork_era_combo.findText(era_value)
        self._greatwork_era_combo.setCurrentIndex(0 if era_index < 0 else era_index)

        self._clear_yield_rows()
        yield_changes = payload.get("yield_changes") if isinstance(payload.get("yield_changes"), list) else []
        if yield_changes:
            for row in yield_changes:
                if not isinstance(row, dict):
                    continue
                self._append_yield_row(
                    _safe_text(row.get("YieldType") or "YIELD_CULTURE"),
                    int(row.get("YieldChange", 0) or 0),
                )
        else:
            self._append_yield_row("YIELD_CULTURE", 0)

    def _export_current_greatwork_payload(self) -> dict[str, object]:
        return {
            "abbr": _safe_text(self._greatwork_abbr_edit.text()),
            "GreatWorkType": _safe_text(self._greatwork_type_label.text()),
            "GreatWorkObjectType": self._export_template_value(self._greatwork_object_widget, "great_work_object_type"),
            "Name": _safe_text(self._greatwork_name_edit.text()),
            "Audio": self._greatwork_audio_widget.value(),
            "Image": self._greatwork_image_widget.value(),
            "Quote": _safe_text(self._greatwork_quote_edit.text()),
            "Tourism": int(self._greatwork_tourism_spin.value()),
            "EraType": _safe_text(self._greatwork_era_combo.currentText()),
            "yield_changes": self._collect_yield_rows(),
        }

    def _handle_add_greatwork(self) -> None:
        base_payload = {
            "abbr": "",
            "GreatWorkType": "",
            "GreatWorkObjectType": "",
            "Name": "",
            "Audio": "",
            "Image": "",
            "Quote": "",
            "Tourism": 1,
            "EraType": "",
            "yield_changes": [{"YieldType": "YIELD_CULTURE", "YieldChange": 0}],
        }
        self._greatworks.append(base_payload)
        self._greatwork_list.addItem(QListWidgetItem(self._resolve_greatwork_item_title(base_payload, len(self._greatworks) - 1)))
        self._greatwork_list.setCurrentRow(len(self._greatworks) - 1)
        self._emit_data_changed()

    def _handle_greatwork_selection_changed(self, row: int) -> None:
        self._current_greatwork_index = row
        if row < 0 or row >= len(self._greatworks):
            self._set_greatwork_editor_enabled(False)
            self._set_greatwork_payload({})
            return
        self._set_greatwork_editor_enabled(self._greatwork_radio.isChecked())
        self._set_greatwork_payload(self._greatworks[row])

    def _handle_greatwork_abbr_changed(self, text: str) -> None:
        cleaned = _sanitize_short_token(text)
        if cleaned != text:
            cursor = self._greatwork_abbr_edit.cursorPosition()
            self._greatwork_abbr_edit.blockSignals(True)
            self._greatwork_abbr_edit.setText(cleaned)
            self._greatwork_abbr_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._greatwork_abbr_edit.blockSignals(False)
        self._refresh_greatwork_type_label()
        self._handle_greatwork_field_changed()

    def _handle_add_yield_row(self) -> None:
        self._append_yield_row("YIELD_CULTURE", 0)
        self._handle_greatwork_field_changed()

    def _handle_remove_yield_row(self) -> None:
        row = self._greatwork_yield_table.currentRow()
        if row < 0:
            row = self._greatwork_yield_table.rowCount() - 1
        if row >= 0:
            self._greatwork_yield_table.removeRow(row)
            self._handle_greatwork_field_changed()

    def _handle_greatwork_field_changed(self) -> None:
        if self._internal_updating:
            return
        row = self._current_greatwork_index
        if row < 0 or row >= len(self._greatworks):
            return
        payload = self._export_current_greatwork_payload()
        self._greatworks[row] = payload
        item = self._greatwork_list.item(row)
        if item is not None:
            item.setText(self._resolve_greatwork_item_title(payload, row))
        self._emit_data_changed()

    def _refresh_type_label(self) -> None:
        short = _sanitize_short_token(self._abbr_edit.text())
        self._type_label.setText(f"GREAT_PERSON_INDIVIDUAL_{short}" if short else "")

    def _handle_abbr_changed(self, text: str) -> None:
        cleaned = _sanitize_short_token(text)
        if cleaned != text:
            cursor = self._abbr_edit.cursorPosition()
            self._abbr_edit.blockSignals(True)
            self._abbr_edit.setText(cleaned)
            self._abbr_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._abbr_edit.blockSignals(False)
        self._refresh_type_label()
        self._emit_data_changed()

    def _handle_mode_changed(self) -> None:
        is_activation = self._activation_radio.isChecked()
        self._stack.setCurrentIndex(0 if is_activation else 1)
        self._action_charges_spin.setEnabled(is_activation)
        if not is_activation:
            self._action_charges_spin.blockSignals(True)
            self._action_charges_spin.setValue(0)
            self._action_charges_spin.blockSignals(False)
        self._set_greatwork_editor_enabled((not is_activation) and self._current_greatwork_index >= 0)
        self._emit_data_changed()

    def _emit_data_changed(self) -> None:
        if self._internal_updating:
            return
        self.dataChanged.emit()

    def set_class_type_provider(self, provider: Callable[[], str]) -> None:
        self._class_type_provider = provider
        self._class_type_label.setText(provider())

    def set_payload(self, payload: dict[str, object]) -> None:
        self._internal_updating = True
        mode = _safe_text(payload.get("mode") or "activation").lower()
        self._activation_radio.setChecked(mode != "greatwork")
        self._greatwork_radio.setChecked(mode == "greatwork")

        raw_type = _safe_text(payload.get("GreatPersonIndividualType") or payload.get("type"))
        raw_abbr = _safe_text(payload.get("abbr"))
        if not raw_abbr and raw_type.startswith("GREAT_PERSON_INDIVIDUAL_"):
            raw_abbr = raw_type[len("GREAT_PERSON_INDIVIDUAL_") :]
        self._abbr_edit.setText(raw_abbr)
        self._name_edit.setText(_safe_text(payload.get("Name") or payload.get("name")))

        if self._class_type_provider is not None:
            self._class_type_label.setText(self._class_type_provider())

        era = _safe_text(payload.get("EraType"))
        idx = self._era_combo.findText(era)
        self._era_combo.setCurrentIndex(0 if idx < 0 else idx)
        default_charges = 0 if mode == "greatwork" else 1
        self._action_charges_spin.setValue(int(payload.get("ActionCharges", default_charges) or default_charges))

        gender = _safe_text(payload.get("Gender") or "M")
        gidx = self._gender_combo.findText(gender)
        self._gender_combo.setCurrentIndex(0 if gidx < 0 else gidx)

        self._area_highlight_radius.setValue(int(payload.get("AreaHighlightRadius", 0) or 0))

        for key, widget in self._bool_fields.items():
            widget.setChecked(bool(payload.get(key)))
        for key, widget in self._number_fields.items():
            widget.setValue(int(payload.get(key, 0) or 0))
        for key, widget in self._text_template_fields.items():
            incoming = payload.get(key)
            if key == "ActionNameTextOverride" and not _safe_text(incoming):
                incoming = "LOC_GREATPERSON_ACTION_NAME_RETIRE"
            self._set_template_value(widget, incoming)

        self._greatworks = []
        self._greatwork_list.clear()
        greatworks = payload.get("great_works") if isinstance(payload.get("great_works"), list) else []
        for idx, item in enumerate(greatworks):
            if not isinstance(item, dict):
                continue
            gw_payload = deepcopy(item)
            self._greatworks.append(gw_payload)
            self._greatwork_list.addItem(QListWidgetItem(self._resolve_greatwork_item_title(gw_payload, idx)))
        if self._greatworks:
            self._greatwork_list.setCurrentRow(0)
        else:
            self._set_greatwork_editor_enabled(False)
            self._set_greatwork_payload({})

        self._refresh_type_label()
        self._internal_updating = False
        self._handle_mode_changed()

    def export_payload(self) -> dict[str, object]:
        data: dict[str, object] = {
            "mode": "activation" if self._activation_radio.isChecked() else "greatwork",
            "abbr": _safe_text(self._abbr_edit.text()),
            "GreatPersonIndividualType": _safe_text(self._type_label.text()),
            "Name": _safe_text(self._name_edit.text()),
            "GreatPersonClassType": _safe_text(self._class_type_label.text()),
            "EraType": _safe_text(self._era_combo.currentText()),
            "ActionCharges": 0 if self._greatwork_radio.isChecked() else int(self._action_charges_spin.value()),
            "Gender": _safe_text(self._gender_combo.currentText()),
            "AreaHighlightRadius": int(self._area_highlight_radius.value()),
            "great_works": deepcopy(self._greatworks),
        }

        if self._activation_radio.isChecked():
            for key, widget in self._bool_fields.items():
                data[key] = 1 if widget.isChecked() else 0
            for key, widget in self._number_fields.items():
                data[key] = int(widget.value())
            for key, widget in self._text_template_fields.items():
                value_key = self._text_template_value_keys.get(key, "text")
                data[key] = self._export_template_value(widget, value_key)
        return data

    @staticmethod
    def _set_template_value(widget: BaseTemplateWidget, value: object | None) -> None:
        if hasattr(widget, "set_current_value"):
            getattr(widget, "set_current_value")(_safe_text(value) or None)

    @staticmethod
    def _export_template_value(widget: BaseTemplateWidget, value_key: str) -> str:
        data = widget.export_data()
        value = data.get(value_key)
        if value is None:
            value = data.get("value")
        return _safe_text(value)

    def set_read_only(self, read_only: bool) -> None:
        for widget in (
            self._activation_radio,
            self._greatwork_radio,
            self._abbr_edit,
            self._name_edit,
            self._era_combo,
            self._action_charges_spin,
            self._gender_combo,
            self._area_highlight_radius,
        ):
            widget.setEnabled(not read_only)
        for widget in self._bool_fields.values():
            widget.setEnabled(not read_only)
        for widget in self._number_fields.values():
            widget.setEnabled(not read_only)
        for widget in self._text_template_fields.values():
            widget.setEnabled(not read_only)
        self._greatwork_add_btn.setEnabled(not read_only)
        self._greatwork_list.setEnabled(not read_only)
        self._set_greatwork_editor_enabled(not read_only and self._current_greatwork_index >= 0)


class GreatPeopleCompositeEditor(QWidget):
    dataChanged = pyqtSignal()

    _FORMATION_OPTIONS = [
        "FORMATION_CLASS_CIVILIAN",
        "FORMATION_CLASS_SUPPORT",
        "FORMATION_CLASS_LAND_COMBAT",
        "FORMATION_CLASS_AIR",
        "FORMATION_CLASS_NAVAL",
    ]
    _DOMAIN_OPTIONS = ["DOMAIN_LAND", "DOMAIN_AIR", "DOMAIN_SEA"]

    def __init__(
        self,
        shared_params_provider: Callable[[], dict[str, object]],
        image_widget_factory: Callable[[tuple[int, int], bool], QWidget],
    ) -> None:
        super().__init__()
        self._shared_params_provider = shared_params_provider
        self._image_widget_factory = image_widget_factory
        self._internal_updating = False
        self._entry_name_fallback = ""
        self._import_locked = False
        self._individuals: list[dict[str, object]] = []
        self._current_index = -1

        self._abbr_edit = QLineEdit()
        self._abbr_edit.setPlaceholderText("简称默认空，仅英文/数字/下划线")
        self._class_type_label = QLabel("")
        self._class_type_label.setObjectName("pageInfoLabel")
        self._unit_type_label = QLabel("")
        self._unit_type_label.setObjectName("pageInfoLabel")

        self._class_name_edit = QLineEdit()
        self._class_name_edit.setPlaceholderText("伟人类型名称（中文）")

        self._district_type_widget = build_template_widget("district_search")
        self._max_player_instances_spin = QSpinBox()
        self._max_player_instances_spin.setRange(-1, 99)
        self._max_player_instances_spin.setValue(-1)
        self._pseudo_yield_widget = DistinctValueEditableTemplate(
            "GreatPersonClasses",
            "PseudoYieldType",
            "选择或输入 PseudoYieldType",
        )
        self._icon_string_widget = DistinctValueEditableTemplate(
            "GreatPersonClasses",
            "IconString",
            "选择或输入 IconString",
        )
        self._action_icon_widget = DistinctValueEditableTemplate(
            "GreatPersonClasses",
            "ActionIcon",
            "选择或输入 ActionIcon",
        )
        self._timeline_check = QCheckBox("启用（AvailableInTimeline）")
        self._timeline_check.setChecked(True)
        self._duplicate_check = QCheckBox("启用（GenerateDuplicateIndividuals）")

        self._unit_base_sight = QSpinBox()
        self._unit_base_sight.setRange(0, 20)
        self._unit_base_sight.setValue(4)
        self._unit_base_moves = QSpinBox()
        self._unit_base_moves.setRange(0, 20)
        self._unit_base_moves.setValue(5)
        self._unit_formation = QComboBox()
        self._unit_formation.addItems(self._FORMATION_OPTIONS)
        self._unit_domain = QComboBox()
        self._unit_domain.addItems(self._DOMAIN_OPTIONS)
        self._unit_retreat_check = QCheckBox("启用")
        self._unit_capture_check = QCheckBox("启用")
        self._unit_cost = QSpinBox()
        self._unit_cost.setRange(1, 9999)
        self._unit_cost.setValue(1)
        self._unit_zoc_check = QCheckBox("启用")
        self._unit_found_religion_check = QCheckBox("启用")
        self._unit_can_train_check = QCheckBox("启用")
        self._unit_trait_check = QCheckBox("输出 TraitType")
        self._unit_trait_label = QLabel("")
        self._unit_trait_label.setObjectName("pageInfoLabel")
        self._unit_name_edit = QLineEdit()
        self._unit_desc_edit = IconTokenTextEdit()
        self._unit_desc_edit.setFixedHeight(72)
        self._unit_icon_name_edit = QLineEdit()
        self._unit_icon_name_edit.setReadOnly(True)
        self._unit_icon_image = image_widget_factory((256, 256), True)
        self._unit_portrait_name_edit = QLineEdit()
        self._unit_portrait_name_edit.setReadOnly(True)
        self._unit_portrait_image = image_widget_factory((256, 256), True)

        self._add_individual_btn = QPushButton("新增伟人个体")
        self._individual_list = QListWidget()
        self._individual_editor = GreatPersonIndividualEditor()
        self._individual_editor.set_class_type_provider(lambda: _safe_text(self._class_type_label.text()))

        self._build_ui()
        self._bind_events()
        self._refresh_type_labels()

    @staticmethod
    def _field_desc_map() -> dict[str, str]:
        return {
            "GreatPersonClassType": "伟人类型ID",
            "UnitType": "对应伟人单位ID）",
            "Name": "伟人类型名称",
            "DistrictType": "该伟人类型主要来源区域",
            "MaxPlayerInstances": "每位玩家最大可拥有数量，-1为不限制",
            "PseudoYieldType": "伪产出类型，用于积分来源分类",
            "IconString": "UI图标字符串（通常是 [ICON_...] ）",
            "ActionIcon": "伟人行动按钮图标",
            "AvailableInTimeline": "是否参与时间轴展示",
            "GenerateDuplicateIndividuals": "是否允许生成重复个体",
            "BaseSightRange": "单位基础视野",
            "BaseMoves": "单位基础移动力",
            "FormationClass": "单位编队类型",
            "Domain": "单位活动领域",
            "CanRetreatWhenCaptured": "被俘时可撤退",
            "CanCapture": "可俘获单位",
            "Cost": "单位成本",
            "ZoneOfControl": "是否产生控制区",
            "FoundReligion": "可创立宗教",
            "CanTrain": "可在城市训练",
            "TraitType": "是否输出关联 TraitType",
            "TraitType值": "TraitType",
            "Description": "单位描述",
        }

    def _build_two_col_widget(self, pairs: list[tuple[str, str, QWidget]]) -> QWidget:
        host = QWidget()
        grid = QGridLayout(host)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        for idx, (english_key, chinese_label, widget) in enumerate(pairs):
            row = idx // 2
            col = (idx % 2) * 2
            label = QLabel(chinese_label)
            label.setToolTip(english_key)
            widget.setToolTip(english_key)
            grid.addWidget(label, row, col)
            grid.addWidget(widget, row, col + 1)
        return host

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        class_group = QGroupBox("GreatPersonClasses（伟人类型）")
        class_rows = [
            ("abbr", "简称", self._abbr_edit),
            ("GreatPersonClassType", "伟人类型ID", self._class_type_label),
            ("UnitType", "关联单位ID", self._unit_type_label),
            ("Name", "伟人类型名称", self._class_name_edit),
            ("DistrictType", "来源区域", self._district_type_widget),
            ("MaxPlayerInstances", "玩家最大实例数", self._max_player_instances_spin),
            ("PseudoYieldType", "伪产出类型", self._pseudo_yield_widget),
            ("IconString", "图标字符串", self._icon_string_widget),
            ("ActionIcon", "行动图标", self._action_icon_widget),
            ("AvailableInTimeline", "时间轴可见", self._timeline_check),
            ("GenerateDuplicateIndividuals", "允许重复个体", self._duplicate_check),
        ]
        class_group.setLayout(QVBoxLayout())
        class_group.layout().addWidget(self._build_two_col_widget(class_rows))
        root.addWidget(class_group)

        unit_group = QGroupBox("Units（简化单位）")
        unit_rows = [
            ("UnitType", "单位ID", self._unit_type_label),
            ("BaseSightRange", "基础视野", self._unit_base_sight),
            ("BaseMoves", "基础移动力", self._unit_base_moves),
            ("FormationClass", "编队类型", self._unit_formation),
            ("Domain", "领域", self._unit_domain),
            ("CanRetreatWhenCaptured", "可被俘撤退", self._unit_retreat_check),
            ("CanCapture", "可俘获", self._unit_capture_check),
            ("Cost", "成本", self._unit_cost),
            ("ZoneOfControl", "控制区", self._unit_zoc_check),
            ("FoundReligion", "可创立宗教", self._unit_found_religion_check),
            ("CanTrain", "可训练", self._unit_can_train_check),
            ("TraitType", "输出Trait", self._unit_trait_check),
            ("Name", "单位名称", self._unit_name_edit),
            ("TraitType", "TraitType完整名字", self._unit_trait_label),
            ("Description", "单位描述", self._unit_desc_edit),
        ]
        unit_group_layout = QVBoxLayout()
        unit_group_layout.addWidget(self._build_two_col_widget(unit_rows), 1)

        image_row = QHBoxLayout()
        image_row.setContentsMargins(0, 0, 0, 0)
        image_row.setSpacing(10)

        icon_holder = QWidget()
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(6)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        icon_label = QLabel("单位图标名称")
        icon_label.setToolTip("IconName")
        self._unit_icon_name_edit.setToolTip("IconName")
        icon_layout.addWidget(icon_label)
        icon_layout.addWidget(self._unit_icon_name_edit)
        icon_widget_label = QLabel("单位图标（256x256）")
        icon_widget_label.setToolTip("UnitIconImage")
        self._unit_icon_image.setToolTip("UnitIconImage")
        icon_layout.addWidget(icon_widget_label)
        icon_layout.addWidget(self._unit_icon_image)
        icon_layout.addStretch(1)
        icon_holder.setLayout(icon_layout)

        portrait_holder = QWidget()
        portrait_layout = QVBoxLayout()
        portrait_layout.setContentsMargins(0, 0, 0, 0)
        portrait_layout.setSpacing(6)
        portrait_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        portrait_label = QLabel("单位肖像名称")
        portrait_label.setToolTip("PortraitName")
        self._unit_portrait_name_edit.setToolTip("PortraitName")
        portrait_layout.addWidget(portrait_label)
        portrait_layout.addWidget(self._unit_portrait_name_edit)
        portrait_widget_label = QLabel("单位肖像（256x256）")
        portrait_widget_label.setToolTip("UnitPortraitImage")
        self._unit_portrait_image.setToolTip("UnitPortraitImage")
        portrait_layout.addWidget(portrait_widget_label)
        portrait_layout.addWidget(self._unit_portrait_image)
        portrait_layout.addStretch(1)
        portrait_holder.setLayout(portrait_layout)

        image_row.addWidget(icon_holder, 1)
        image_row.addWidget(portrait_holder, 1)

        unit_group_layout.addLayout(image_row)
        unit_group.setLayout(unit_group_layout)
        root.addWidget(unit_group)

        individual_group = QGroupBox("伟人个体")
        individual_layout = QVBoxLayout()
        individual_layout.setContentsMargins(8, 8, 8, 8)
        individual_layout.setSpacing(8)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)
        button_row.addWidget(self._add_individual_btn)
        button_row.addStretch(1)
        individual_layout.addLayout(button_row)

        editor_row = QHBoxLayout()
        editor_row.setContentsMargins(0, 0, 0, 0)
        editor_row.setSpacing(8)
        editor_row.addWidget(self._individual_list, 0)
        editor_row.addWidget(self._individual_editor, 1)
        individual_layout.addLayout(editor_row)
        individual_group.setLayout(individual_layout)
        root.addWidget(individual_group)

        root.addStretch(1)
        self.setLayout(root)

    def _bind_events(self) -> None:
        self._abbr_edit.textChanged.connect(self._handle_abbr_changed)

        for widget in (
            self._class_name_edit,
            self._unit_name_edit,
            self._unit_desc_edit,
        ):
            widget.textChanged.connect(lambda *_args: self._emit_data_changed())

        for widget in (
            self._max_player_instances_spin,
            self._unit_base_sight,
            self._unit_base_moves,
            self._unit_cost,
        ):
            widget.valueChanged.connect(lambda *_args: self._emit_data_changed())

        for widget in (
            self._timeline_check,
            self._duplicate_check,
            self._unit_retreat_check,
            self._unit_capture_check,
            self._unit_zoc_check,
            self._unit_found_religion_check,
            self._unit_can_train_check,
            self._unit_trait_check,
        ):
            widget.toggled.connect(lambda *_args: self._emit_data_changed())

        self._district_type_widget.dataChanged.connect(self._emit_data_changed)
        self._pseudo_yield_widget.dataChanged.connect(self._emit_data_changed)
        self._icon_string_widget.dataChanged.connect(self._emit_data_changed)
        self._action_icon_widget.dataChanged.connect(self._emit_data_changed)
        self._unit_icon_image.dataChanged.connect(self._emit_data_changed)
        self._unit_portrait_image.dataChanged.connect(self._emit_data_changed)

        self._unit_formation.currentIndexChanged.connect(lambda *_args: self._emit_data_changed())
        self._unit_domain.currentIndexChanged.connect(lambda *_args: self._emit_data_changed())
        self._unit_trait_check.toggled.connect(lambda *_args: self._refresh_type_labels())

        self._add_individual_btn.clicked.connect(self._handle_add_individual)
        self._individual_list.currentRowChanged.connect(self._handle_individual_selection_changed)
        self._individual_editor.dataChanged.connect(self._handle_individual_changed)

    def _refresh_type_labels(self) -> None:
        class_type = _build_type(
            self._shared_params_provider(),
            "GREAT_PERSON_CLASS",
            "G",
            self._abbr_edit.text(),
        )
        unit_type = class_type.replace("GREAT_PERSON_CLASS", "UNIT_GREAT", 1) if class_type else ""
        self._class_type_label.setText(class_type)
        self._unit_type_label.setText(unit_type)
        self._unit_trait_label.setText(f"TRAIT_{unit_type}" if self._unit_trait_check.isChecked() and unit_type else "")
        self._unit_icon_name_edit.setText(f"ICON_{unit_type}" if unit_type else "")
        self._unit_portrait_name_edit.setText(f"ICON_{unit_type}_PORTRAIT" if unit_type else "")

    def _handle_abbr_changed(self, text: str) -> None:
        cleaned = _sanitize_short_token(text)
        if cleaned != text:
            cursor = self._abbr_edit.cursorPosition()
            self._abbr_edit.blockSignals(True)
            self._abbr_edit.setText(cleaned)
            self._abbr_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._abbr_edit.blockSignals(False)
        self._refresh_type_labels()
        self._emit_data_changed()

    def _resolve_individual_item_title(self, payload: dict[str, object], index: int) -> str:
        name = _safe_text(payload.get("Name"))
        if name:
            return name
        gp_type = _safe_text(payload.get("GreatPersonIndividualType"))
        if gp_type:
            return gp_type
        return "未命名个体" if index < 0 else f"未命名个体 {index + 1}"

    def _handle_add_individual(self) -> None:
        base = _safe_text(self._class_type_label.text())
        new_payload = {
            "mode": "activation",
            "abbr": "",
            "GreatPersonIndividualType": "",
            "Name": "",
            "GreatPersonClassType": base,
            "EraType": "ERA_ANCIENT",
            "ActionCharges": 1,
            "Gender": "M",
            "AreaHighlightRadius": 0,
            "ActionNameTextOverride": "LOC_GREATPERSON_ACTION_NAME_RETIRE",
        }
        self._individuals.append(new_payload)
        item = QListWidgetItem(self._resolve_individual_item_title(new_payload, len(self._individuals) - 1))
        self._individual_list.addItem(item)
        self._individual_list.setCurrentRow(len(self._individuals) - 1)
        self._emit_data_changed()

    def _handle_individual_selection_changed(self, row: int) -> None:
        self._current_index = row
        if row < 0 or row >= len(self._individuals):
            self._individual_editor.set_payload({})
            return
        self._individual_editor.set_payload(self._individuals[row])

    def _handle_individual_changed(self) -> None:
        row = self._current_index
        if row < 0 or row >= len(self._individuals):
            return
        payload = self._individual_editor.export_payload()
        payload["GreatPersonClassType"] = _safe_text(self._class_type_label.text())
        self._individuals[row] = payload
        self._individual_list.item(row).setText(self._resolve_individual_item_title(payload, row))
        self._emit_data_changed()

    def _emit_data_changed(self) -> None:
        if self._internal_updating:
            return
        self.dataChanged.emit()

    def _set_locked(self, locked: bool) -> None:
        self._import_locked = locked
        for widget in (
            self._abbr_edit,
            self._class_name_edit,
            self._max_player_instances_spin,
            self._timeline_check,
            self._duplicate_check,
            self._unit_base_sight,
            self._unit_base_moves,
            self._unit_formation,
            self._unit_domain,
            self._unit_retreat_check,
            self._unit_capture_check,
            self._unit_cost,
            self._unit_zoc_check,
            self._unit_found_religion_check,
            self._unit_can_train_check,
            self._unit_trait_check,
            self._unit_name_edit,
            self._unit_desc_edit,
        ):
            widget.setEnabled(not locked)
        self._district_type_widget.setEnabled(not locked)
        self._pseudo_yield_widget.set_read_only(locked)
        self._icon_string_widget.set_read_only(locked)
        self._action_icon_widget.set_read_only(locked)
        self._unit_icon_image.setEnabled(not locked)
        self._unit_portrait_image.setEnabled(not locked)
        self._add_individual_btn.setEnabled(True)
        self._individual_editor.set_read_only(False)

    @staticmethod
    def _set_template_value(widget: BaseTemplateWidget, value: object | None) -> None:
        if hasattr(widget, "set_current_value"):
            getattr(widget, "set_current_value")(_safe_text(value) or None)

    @staticmethod
    def _export_template_value(widget: BaseTemplateWidget, value_key: str) -> str:
        data = widget.export_data()
        value = data.get(value_key)
        if value is None:
            value = data.get("value")
        return _safe_text(value)

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._internal_updating = True
        self._entry_name_fallback = fallback_name

        class_data = entry.get("class_data") if isinstance(entry.get("class_data"), dict) else {}
        unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}

        self._abbr_edit.setText(_safe_text(entry.get("abbr")))
        self._class_name_edit.setText(_safe_text(class_data.get("Name") or entry.get("name")))
        self._set_template_value(self._district_type_widget, class_data.get("DistrictType"))
        self._max_player_instances_spin.setValue(int(class_data.get("MaxPlayerInstances", -1) or -1))
        self._pseudo_yield_widget.set_value(class_data.get("PseudoYieldType"))
        self._icon_string_widget.set_value(class_data.get("IconString"))
        self._action_icon_widget.set_value(class_data.get("ActionIcon"))
        self._timeline_check.setChecked(bool(class_data.get("AvailableInTimeline", True)))
        self._duplicate_check.setChecked(bool(class_data.get("GenerateDuplicateIndividuals", False)))

        self._unit_base_sight.setValue(int(unit_data.get("BaseSightRange", 4) or 4))
        self._unit_base_moves.setValue(int(unit_data.get("BaseMoves", 5) or 5))
        form = _safe_text(unit_data.get("FormationClass") or "FORMATION_CLASS_CIVILIAN")
        fidx = self._unit_formation.findText(form)
        self._unit_formation.setCurrentIndex(0 if fidx < 0 else fidx)
        domain = _safe_text(unit_data.get("Domain") or "DOMAIN_LAND")
        didx = self._unit_domain.findText(domain)
        self._unit_domain.setCurrentIndex(0 if didx < 0 else didx)
        self._unit_retreat_check.setChecked(bool(unit_data.get("CanRetreatWhenCaptured", False)))
        self._unit_capture_check.setChecked(bool(unit_data.get("CanCapture", False)))
        self._unit_cost.setValue(int(unit_data.get("Cost", 1) or 1))
        self._unit_zoc_check.setChecked(bool(unit_data.get("ZoneOfControl", False)))
        self._unit_found_religion_check.setChecked(bool(unit_data.get("FoundReligion", False)))
        self._unit_can_train_check.setChecked(bool(unit_data.get("CanTrain", False)))
        self._unit_trait_check.setChecked(bool(unit_data.get("TraitType")))
        self._unit_name_edit.setText(_safe_text(unit_data.get("Name")))
        self._unit_desc_edit.import_tokenized_text(unit_data.get("Description"))
        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        if hasattr(self._unit_icon_image, "set_state"):
            getattr(self._unit_icon_image, "set_state")(images.get("unit_icon"))
        if hasattr(self._unit_portrait_image, "set_state"):
            getattr(self._unit_portrait_image, "set_state")(images.get("unit_portrait"))

        self._individuals = []
        self._individual_list.clear()
        individuals = entry.get("individuals") if isinstance(entry.get("individuals"), list) else []
        for idx, item in enumerate(individuals, start=1):
            if not isinstance(item, dict):
                continue
            payload = deepcopy(item)
            self._individuals.append(payload)
            self._individual_list.addItem(QListWidgetItem(self._resolve_individual_item_title(payload, idx - 1)))

        self._refresh_type_labels()
        self._set_locked(bool(entry.get("import_locked", False)))
        if self._individuals:
            self._individual_list.setCurrentRow(0)
        else:
            self._individual_editor.set_payload({})

        self._internal_updating = False

    def export_entry(self) -> dict[str, object]:
        class_type = _safe_text(self._class_type_label.text())
        unit_type = _safe_text(self._unit_type_label.text())
        trait_type = f"TRAIT_{unit_type}" if self._unit_trait_check.isChecked() and unit_type else ""

        class_data = {
            "GreatPersonClassType": class_type,
            "Name": _safe_text(self._class_name_edit.text()),
            "UnitType": unit_type,
            "DistrictType": self._export_template_value(self._district_type_widget, "district_type"),
            "MaxPlayerInstances": int(self._max_player_instances_spin.value()),
            "PseudoYieldType": self._pseudo_yield_widget.value(),
            "IconString": self._icon_string_widget.value(),
            "ActionIcon": self._action_icon_widget.value(),
            "AvailableInTimeline": 1 if self._timeline_check.isChecked() else 0,
            "GenerateDuplicateIndividuals": 1 if self._duplicate_check.isChecked() else 0,
        }
        unit_data = {
            "UnitType": unit_type,
            "BaseSightRange": int(self._unit_base_sight.value()),
            "BaseMoves": int(self._unit_base_moves.value()),
            "FormationClass": _safe_text(self._unit_formation.currentText()),
            "Domain": _safe_text(self._unit_domain.currentText()),
            "CanRetreatWhenCaptured": 1 if self._unit_retreat_check.isChecked() else 0,
            "CanCapture": 1 if self._unit_capture_check.isChecked() else 0,
            "Cost": int(self._unit_cost.value()),
            "ZoneOfControl": 1 if self._unit_zoc_check.isChecked() else 0,
            "FoundReligion": 1 if self._unit_found_religion_check.isChecked() else 0,
            "CanTrain": 1 if self._unit_can_train_check.isChecked() else 0,
            "TraitType": trait_type,
            "Name": _safe_text(self._unit_name_edit.text()),
            "Description": self._unit_desc_edit.export_tokenized_text(),
        }

        class_name = _safe_text(self._class_name_edit.text())
        unit_icon_state: dict[str, object] = {}
        unit_portrait_state: dict[str, object] = {}
        if hasattr(self._unit_icon_image, "export_state"):
            exported = getattr(self._unit_icon_image, "export_state")()
            if isinstance(exported, dict):
                unit_icon_state = exported
        if hasattr(self._unit_portrait_image, "export_state"):
            exported = getattr(self._unit_portrait_image, "export_state")()
            if isinstance(exported, dict):
                unit_portrait_state = exported
        images = {
            "unit_icon_name": _safe_text(self._unit_icon_name_edit.text()),
            "unit_portrait_name": _safe_text(self._unit_portrait_name_edit.text()),
            "unit_icon": unit_icon_state,
            "unit_portrait": unit_portrait_state,
        }
        return {
            "name": class_name or class_type,
            "abbr": _safe_text(self._abbr_edit.text()),
            "type": class_type,
            "import_locked": bool(self._import_locked),
            "class_data": class_data,
            "unit_data": unit_data,
            "images": images,
            "individuals": deepcopy(self._individuals),
        }
