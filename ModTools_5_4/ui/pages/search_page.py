"""Search page with text search and staged placeholders."""
from __future__ import annotations

from pathlib import Path
import sqlite3

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QFontMetrics, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyledItemDelegate,
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage
from ...app.settings_store import load_settings
from ...db.ability_search import (
    OBJECT_CATEGORY_LABELS,
    OBJECT_TYPE_ORDER,
    fetch_object_detail,
    open_dbs,
    search_all,
)
from ...db.text_database import SIMPLIFIED_LANGUAGE_NORMALIZED, query_text_by_tag


class ModifierTypePickerDialog(QDialog):
    """Dialog for selecting one ModifierType from DynamicModifiers."""

    def __init__(self, modifier_types: list[str], initial_query: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_modifier_types = sorted(set(modifier_types), key=lambda value: value.upper())
        self._selected_modifier_type = ""

        self.setWindowTitle("选择 ModifierType")
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        hint = QLabel("仅支持英文关键词搜索（大小写不敏感）。")
        hint.setObjectName("pageInfoLabel")
        root.addWidget(hint)

        row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入英文关键词，例如 MODIFIER_PLAYER_CITIES_ADJUST_...")
        self._search_input.setText(initial_query.strip())
        self._search_input.returnPressed.connect(self._refresh_result_list)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._refresh_result_list)

        row.addWidget(self._search_input, 1)
        row.addWidget(search_btn)
        root.addLayout(row)

        self._status_label = QLabel("")
        self._status_label.setObjectName("pageInfoLabel")
        root.addWidget(self._status_label)

        self._result_table = QTableWidget()
        self._result_table.setColumnCount(1)
        self._result_table.setHorizontalHeaderLabels(["ModifierType"])
        self._result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._result_table.verticalHeader().setVisible(False)
        self._result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._result_table.itemDoubleClicked.connect(self._accept_selection)
        root.addWidget(self._result_table, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_selection)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

        self._refresh_result_list()

    def selected_modifier_type(self) -> str:
        return self._selected_modifier_type

    def _is_ascii_query(self, query: str) -> bool:
        return all(ord(char) < 128 for char in query)

    def _alpha_key(self, candidate: str) -> tuple[str, str]:
        normalized = candidate.upper()
        first_letter = normalized[:1]
        return (first_letter, normalized)

    def _score(self, candidate: str, query: str) -> tuple[int, int, str]:
        if not query:
            return (3, len(candidate), candidate)
        candidate_upper = candidate.upper()
        query_upper = query.upper()
        if candidate_upper == query_upper:
            return (0, len(candidate), candidate)
        if candidate_upper.startswith(query_upper):
            return (1, len(candidate), candidate)
        if query_upper in candidate_upper:
            return (2, len(candidate), candidate)
        return (3, len(candidate), candidate)

    def _refresh_result_list(self) -> None:
        query = self._search_input.text().strip()
        if query and not self._is_ascii_query(query):
            self._status_label.setText("当前仅支持英文关键词搜索。")
            candidates = self._all_modifier_types
        else:
            candidates = self._all_modifier_types

        if query:
            ranked = sorted(candidates, key=lambda value: (self._score(value, query), self._alpha_key(value)))
        else:
            ranked = sorted(candidates, key=self._alpha_key)
        if query:
            query_upper = query.upper()
            ranked = [value for value in ranked if query_upper in value.upper()]

        self._result_table.setRowCount(len(ranked))
        for index, value in enumerate(ranked):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._result_table.setItem(index, 0, item)

        self._status_label.setText(f"共 {len(ranked)} 条结果。")
        if ranked:
            self._result_table.selectRow(0)

    def _accept_selection(self) -> None:
        row = self._result_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一个 ModifierType。")
            return
        item = self._result_table.item(row, 0)
        if item is None:
            return
        self._selected_modifier_type = item.text().strip()
        if not self._selected_modifier_type:
            return
        self.accept()


class SearchPage(BasePage):
    """Search page container."""

    page_id = "search"
    display_name = "搜索"

    def __init__(self) -> None:
        super().__init__()
        self._text_query_input = QLineEdit()
        self._text_search_hint = QLabel("")
        self._text_results_table = QTableWidget()

        self._modifier_search_input = QLineEdit()
        self._modifier_selected_type_label = QLabel("当前未选择 ModifierType")
        self._modifier_status_label = QLabel("")
        self._dynamic_table = QTableWidget()
        self._modifiers_table = QTableWidget()
        self._modifier_detail_output = QPlainTextEdit()
        self._arguments_table = QTableWidget()
        self._arguments_status_label = QLabel("")
        self._strings_table = QTableWidget()
        self._strings_status_label = QLabel("")

        self._current_game_db_path: Path | None = None
        self._current_modifier_type = ""
        self._current_modifiers_rows: list[dict[str, object]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        header = QLabel("搜索页面")
        header.setObjectName("pageHeaderLabel")
        layout.addWidget(header)

        top_tabs = QTabWidget()
        top_tabs.addTab(self._build_text_search_tab(), "文本搜索")
        top_tabs.addTab(self._build_modifiers_tab(), "Modifiers搜索")
        top_tabs.addTab(self._build_global_search_tab(), "全局搜索")
        layout.addWidget(top_tabs, 1)

    def _build_text_search_tab(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(8)

        search_box = QGroupBox("文本库检索")
        search_layout = QVBoxLayout(search_box)
        search_row = QHBoxLayout()

        self._text_query_input.setPlaceholderText("输入中文内容或Tag（例如 LOC_UNIT_WARRIOR_NAME）")
        self._text_query_input.returnPressed.connect(self._run_text_search)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._run_text_search)

        search_row.addWidget(self._text_query_input, 1)
        search_row.addWidget(search_btn)
        search_layout.addLayout(search_row)

        self._text_search_hint.setObjectName("pageInfoLabel")
        self._text_search_hint.setWordWrap(True)
        self._text_search_hint.setText("中文检索：输出 Tag + 文本（按匹配度排序）；Tag 检索：输出 中文 + Tag。")
        search_layout.addWidget(self._text_search_hint)
        root.addWidget(search_box)

        self._text_results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._text_results_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._text_results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._text_results_table.setAlternatingRowColors(True)
        self._text_results_table.verticalHeader().setVisible(False)
        self._text_results_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        root.addWidget(self._text_results_table, 1)

        self._set_text_headers(is_tag_mode=False)
        return tab

    def _build_modifiers_tab(self) -> QWidget:
        tab = QWidget()
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        search_box = QGroupBox("ModifierType 选择")
        search_layout = QVBoxLayout(search_box)

        row = QHBoxLayout()
        self._modifier_search_input.setPlaceholderText("输入英文关键词（仅英文），点击搜索后在弹窗中选择")
        pick_btn = QPushButton("搜索并选择")
        pick_btn.clicked.connect(self._open_modifier_type_picker)
        row.addWidget(self._modifier_search_input, 1)
        row.addWidget(pick_btn)
        search_layout.addLayout(row)

        self._modifier_selected_type_label.setObjectName("pageInfoLabel")
        self._modifier_selected_type_label.setWordWrap(True)
        search_layout.addWidget(self._modifier_selected_type_label)

        self._modifier_status_label.setObjectName("pageInfoLabel")
        self._modifier_status_label.setWordWrap(True)
        search_layout.addWidget(self._modifier_status_label)

        layout.addWidget(search_box)

        dynamic_box = QGroupBox("DynamicModifiers（同 ModifierType）")
        dynamic_layout = QVBoxLayout(dynamic_box)
        self._prepare_table(self._dynamic_table)
        self._dynamic_table.setMinimumHeight(120)
        self._dynamic_table.setMaximumHeight(220)
        dynamic_layout.addWidget(self._dynamic_table)
        layout.addWidget(dynamic_box)

        modifiers_box = QGroupBox("Modifiers（同 ModifierType）")
        modifiers_layout = QVBoxLayout(modifiers_box)
        self._prepare_table(self._modifiers_table)
        self._modifiers_table.setMinimumHeight(340)
        self._modifiers_table.itemSelectionChanged.connect(self._on_modifier_row_selected)
        modifiers_layout.addWidget(self._modifiers_table)
        layout.addWidget(modifiers_box)

        info_splitter = QSplitter(Qt.Orientation.Horizontal)

        detail_box = QGroupBox("Modifiers行信息（仅非空字段）")
        detail_layout = QVBoxLayout(detail_box)
        self._modifier_detail_output.setReadOnly(True)
        self._modifier_detail_output.setPlaceholderText("请在上方 Modifiers 表中选择一行。")
        self._modifier_detail_output.setMinimumHeight(220)
        detail_layout.addWidget(self._modifier_detail_output)
        info_splitter.addWidget(detail_box)

        arguments_box = QGroupBox("参数信息（ModifierArguments）")
        arguments_layout = QVBoxLayout(arguments_box)
        self._arguments_status_label.setObjectName("pageInfoLabel")
        arguments_layout.addWidget(self._arguments_status_label)
        self._prepare_table(self._arguments_table)
        self._arguments_table.setMinimumHeight(220)
        arguments_layout.addWidget(self._arguments_table)
        info_splitter.addWidget(arguments_box)

        strings_box = QGroupBox("ModifierString信息")
        strings_layout = QVBoxLayout(strings_box)
        self._strings_status_label.setObjectName("pageInfoLabel")
        strings_layout.addWidget(self._strings_status_label)
        self._prepare_table(self._strings_table)
        self._strings_table.setMinimumHeight(220)
        strings_layout.addWidget(self._strings_table)
        info_splitter.addWidget(strings_box)

        info_splitter.setStretchFactor(0, 1)
        info_splitter.setStretchFactor(1, 1)
        info_splitter.setStretchFactor(2, 1)
        layout.addWidget(info_splitter)

        layout.addStretch(1)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        self._modifier_status_label.setText("等待选择 ModifierType。")
        self._arguments_status_label.setText("无结果（未选择 Modifiers 行）。")
        self._strings_status_label.setText("无结果（未选择 Modifiers 行）。")
        return tab

    def _build_global_search_tab(self) -> QWidget:
        """能力实现搜索：按名字/描述/能力/条件搜索，反查对象与 Modifier 全链路。"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        layout.addWidget(AbilitySearchTab(self))
        return tab

    def _is_tag_query(self, query: str) -> bool:
        normalized = query.strip().upper()
        return normalized.startswith("LOC_")

    def _set_text_headers(self, is_tag_mode: bool) -> None:
        self._text_results_table.clearContents()
        self._text_results_table.setRowCount(0)
        self._text_results_table.setColumnCount(2)
        if is_tag_mode:
            self._text_results_table.setHorizontalHeaderLabels(["中文", "Tag"])
        else:
            self._text_results_table.setHorizontalHeaderLabels(["Tag", "中文"])

    def _run_text_search(self) -> None:
        query = self._text_query_input.text().strip()
        if not query:
            self._text_search_hint.setText("请输入检索内容。")
            self._text_results_table.clearContents()
            self._text_results_table.setRowCount(0)
            return

        settings = load_settings()
        if not settings.active_text_db_path:
            self._text_search_hint.setText("未配置当前文本数据库，请先到设置页选择文本数据库。")
            self._text_results_table.clearContents()
            self._text_results_table.setRowCount(0)
            return

        db_path = Path(settings.active_text_db_path)
        if not db_path.exists():
            self._text_search_hint.setText(f"文本数据库不存在: {db_path}")
            self._text_results_table.clearContents()
            self._text_results_table.setRowCount(0)
            return

        is_tag_mode = self._is_tag_query(query)
        self._set_text_headers(is_tag_mode)

        try:
            if is_tag_mode:
                rows = self._query_by_tag(db_path, query)
                self._fill_text_results_tag_mode(rows)
                self._text_search_hint.setText(f"Tag检索：{len(rows)} 条结果。")
            else:
                rows = self._query_by_chinese_text(db_path, query)
                self._fill_text_results_text_mode(rows)
                self._text_search_hint.setText(f"中文检索：{len(rows)} 条结果（按匹配度排序）。")
        except Exception as exc:
            self._text_search_hint.setText(f"查询失败: {exc}")
            self._text_results_table.clearContents()
            self._text_results_table.setRowCount(0)

    def _query_by_tag(self, db_path: Path, query: str) -> list[tuple[str, str]]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT Tag, Text
                FROM LocalizedText
                WHERE lower(Language) = ?
                  AND Tag LIKE ?
                ORDER BY
                    CASE WHEN Tag = ? THEN 0
                         WHEN Tag LIKE ? THEN 1
                         ELSE 2 END,
                    Tag
                LIMIT 200
                """,
                (
                    SIMPLIFIED_LANGUAGE_NORMALIZED,
                    f"%{query}%",
                    query,
                    f"{query}%",
                ),
            ).fetchall()
            return [(str(row["Tag"] or ""), str(row["Text"] or "")) for row in rows]
        finally:
            conn.close()

    def _query_by_chinese_text(self, db_path: Path, query: str) -> list[tuple[str, str, int]]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT Tag, Text,
                    CASE
                        WHEN Text = ? THEN 0
                        WHEN Text LIKE ? THEN 1
                        WHEN Text LIKE ? THEN 2
                        ELSE 3
                    END AS score
                FROM LocalizedText
                WHERE lower(Language) = ?
                  AND Text LIKE ?
                ORDER BY score ASC, length(Text) ASC, Tag ASC
                LIMIT 200
                """,
                (
                    query,
                    f"{query}%",
                    f"%{query}%",
                    SIMPLIFIED_LANGUAGE_NORMALIZED,
                    f"%{query}%",
                ),
            ).fetchall()
            return [(str(row["Tag"] or ""), str(row["Text"] or ""), int(row["score"] or 999)) for row in rows]
        finally:
            conn.close()

    def _fill_text_results_tag_mode(self, rows: list[tuple[str, str]]) -> None:
        self._text_results_table.setRowCount(len(rows))
        col0_values: list[str] = []
        col1_values: list[str] = []
        for row, (tag, text) in enumerate(rows):
            self._set_table_text_cell(row, 0, text)
            self._set_table_text_cell(row, 1, tag)
            col0_values.append(text)
            col1_values.append(tag)
        self._fit_result_columns(col0_values, col1_values)

    def _fill_text_results_text_mode(self, rows: list[tuple[str, str, int]]) -> None:
        self._text_results_table.setRowCount(len(rows))
        col0_values: list[str] = []
        col1_values: list[str] = []
        for row, (tag, text, _score) in enumerate(rows):
            self._set_table_text_cell(row, 0, tag)
            self._set_table_text_cell(row, 1, text)
            col0_values.append(tag)
            col1_values.append(text)
        self._fit_result_columns(col0_values, col1_values)

    def _set_table_text_cell(self, row: int, column: int, value: str) -> None:
        cell = QLineEdit(value)
        cell.setReadOnly(True)
        cell.setFrame(False)
        cell.setCursorPosition(0)
        self._text_results_table.setCellWidget(row, column, cell)

    def _fit_result_columns(self, col0_values: list[str], col1_values: list[str]) -> None:
        metrics = self._text_results_table.fontMetrics()
        header0 = self._text_results_table.horizontalHeaderItem(0)
        header1 = self._text_results_table.horizontalHeaderItem(1)
        header0_text = header0.text() if header0 is not None else ""
        header1_text = header1.text() if header1 is not None else ""

        col0_width = max((metrics.horizontalAdvance(value) for value in col0_values), default=0)
        col1_width = max((metrics.horizontalAdvance(value) for value in col1_values), default=0)
        col0_width = max(col0_width, metrics.horizontalAdvance(header0_text)) + 28
        col1_width = max(col1_width, metrics.horizontalAdvance(header1_text)) + 28

        self._text_results_table.setColumnWidth(0, min(max(120, col0_width), 800))
        self._text_results_table.setColumnWidth(1, min(max(160, col1_width), 1000))

    def _prepare_table(self, table: QTableWidget) -> None:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)

    def _open_modifier_type_picker(self) -> None:
        query = self._modifier_search_input.text().strip()
        if query and not all(ord(char) < 128 for char in query):
            QMessageBox.information(self, "提示", "Modifiers 搜索仅支持英文关键词。")
            return

        game_db_path = self._resolve_game_db_path()
        if game_db_path is None:
            return

        try:
            modifier_types = self._load_dynamic_modifier_types(game_db_path)
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", f"读取 DynamicModifiers 失败: {exc}")
            return

        if not modifier_types:
            QMessageBox.information(self, "提示", "DynamicModifiers 表中没有可用 ModifierType。")
            return

        dialog = ModifierTypePickerDialog(modifier_types, initial_query="", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dialog.selected_modifier_type()
        if not selected:
            return

        self._modifier_search_input.clear()
        self._modifier_selected_type_label.setText(f"当前选择: {selected}")
        self._load_modifier_type_details(selected)

    def _resolve_game_db_path(self) -> Path | None:
        settings = load_settings()
        game_db_path = Path(settings.game_db_path)
        if not game_db_path.exists():
            QMessageBox.critical(self, "数据库不存在", f"游戏数据库不存在: {game_db_path}")
            return None
        self._current_game_db_path = game_db_path
        return game_db_path

    def _load_dynamic_modifier_types(self, db_path: Path) -> list[str]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT DISTINCT ModifierType FROM DynamicModifiers WHERE ModifierType IS NOT NULL ORDER BY ModifierType"
            ).fetchall()
            return [str(row["ModifierType"] or "").strip() for row in rows if str(row["ModifierType"] or "").strip()]
        finally:
            conn.close()

    def _load_modifier_type_details(self, modifier_type: str) -> None:
        if self._current_game_db_path is None:
            return

        db_path = self._current_game_db_path
        self._current_modifier_type = modifier_type

        dynamic_rows = self._query_rows_by_column(db_path, "DynamicModifiers", "ModifierType", modifier_type)
        modifier_rows = self._query_rows_by_column(db_path, "Modifiers", "ModifierType", modifier_type)
        self._current_modifiers_rows = modifier_rows

        self._fill_table_from_rows(self._dynamic_table, dynamic_rows)
        self._fill_table_from_rows(self._modifiers_table, modifier_rows)

        self._modifier_detail_output.clear()
        self._arguments_table.clearContents()
        self._arguments_table.setRowCount(0)
        self._arguments_table.setColumnCount(0)
        self._strings_table.clearContents()
        self._strings_table.setRowCount(0)
        self._strings_table.setColumnCount(0)

        self._arguments_status_label.setText("无结果（请先选择一条 Modifiers 记录）。")
        self._strings_status_label.setText("无结果（请先选择一条 Modifiers 记录）。")
        self._modifier_status_label.setText(
            f"已加载 {modifier_type}：DynamicModifiers {len(dynamic_rows)} 条，Modifiers {len(modifier_rows)} 条。"
        )

    def _query_rows_by_column(self, db_path: Path, table_name: str, column_name: str, value: str) -> list[dict[str, object]]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            query = f"SELECT * FROM {table_name} WHERE {column_name} = ?"
            rows = conn.execute(query, (value,)).fetchall()
            result: list[dict[str, object]] = []
            for row in rows:
                result.append({key: row[key] for key in row.keys()})
            return result
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    def _fill_table_from_rows(self, table: QTableWidget, rows: list[dict[str, object]]) -> None:
        table.clearContents()
        table.setRowCount(0)
        table.setColumnCount(0)
        if not rows:
            return

        columns = list(rows[0].keys())
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index, column_name in enumerate(columns):
                value = row.get(column_name)
                text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, col_index, item)

        table.resizeColumnsToContents()

    def _on_modifier_row_selected(self) -> None:
        row_index = self._modifiers_table.currentRow()
        if row_index < 0 or row_index >= len(self._current_modifiers_rows):
            return
        row_data = self._current_modifiers_rows[row_index]
        self._show_modifier_row_detail(row_data)

        modifier_id = row_data.get("ModifierId")
        if modifier_id in (None, ""):
            self._arguments_status_label.setText("无结果：所选行没有 ModifierId。")
            self._strings_status_label.setText("无结果：所选行没有 ModifierId。")
            self._arguments_table.clearContents()
            self._arguments_table.setRowCount(0)
            self._arguments_table.setColumnCount(0)
            self._strings_table.clearContents()
            self._strings_table.setRowCount(0)
            self._strings_table.setColumnCount(0)
            return

        if self._current_game_db_path is None:
            return

        modifier_id_text = str(modifier_id)
        arguments_rows = self._query_rows_by_column(self._current_game_db_path, "ModifierArguments", "ModifierId", modifier_id_text)
        strings_rows = self._query_rows_by_column(self._current_game_db_path, "ModifierStrings", "ModifierId", modifier_id_text)

        self._fill_arguments_table(arguments_rows)

        resolved_strings_rows: list[dict[str, object]] = []
        for source_row in strings_rows:
            row_copy = dict(source_row)
            text_value = row_copy.get("Text")
            resolved_text = ""
            if isinstance(text_value, str) and text_value.startswith("LOC_"):
                resolved_text = self._resolve_loc_text(text_value)
            row_copy["ResolvedZh"] = resolved_text
            resolved_strings_rows.append(row_copy)

        self._fill_table_from_rows(self._strings_table, resolved_strings_rows)

        if arguments_rows:
            self._arguments_status_label.setText(f"ModifierArguments：{len(arguments_rows)} 条。")
        else:
            self._arguments_status_label.setText("ModifierArguments：无结果。")

        if resolved_strings_rows:
            self._strings_status_label.setText(f"ModifierStrings：{len(resolved_strings_rows)} 条。")
        else:
            self._strings_status_label.setText("ModifierStrings：无结果。")

    def _fill_arguments_table(self, rows: list[dict[str, object]]) -> None:
        self._arguments_table.clearContents()
        self._arguments_table.setRowCount(0)
        self._arguments_table.setColumnCount(3)
        self._arguments_table.setHorizontalHeaderLabels(["ModifierId", "Name", "Value"])

        if not rows:
            return

        self._arguments_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                "" if row.get("ModifierId") is None else str(row.get("ModifierId")),
                "" if row.get("Name") is None else str(row.get("Name")),
                "" if row.get("Value") is None else str(row.get("Value")),
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._arguments_table.setItem(row_index, col_index, item)

        self._arguments_table.resizeColumnsToContents()

    def _show_modifier_row_detail(self, row_data: dict[str, object]) -> None:
        lines: list[str] = []
        for key, value in row_data.items():
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            lines.append(f"{key}: {value}")

        if not lines:
            self._modifier_detail_output.setPlainText("该行没有可显示的非空字段。")
            return
        self._modifier_detail_output.setPlainText("\n".join(lines))

    def _resolve_loc_text(self, tag: str) -> str:
        settings = load_settings()
        if not settings.active_text_db_path:
            return ""
        db_path = Path(settings.active_text_db_path)
        if not db_path.exists():
            return ""
        try:
            value = query_text_by_tag(db_path, tag, resolve_nested=True)
            if value == tag:
                return ""
            return value
        except Exception:
            return ""


class WordWrapDelegate(QStyledItemDelegate):
    """自动换行绘制 delegate（表格/树通用）：长文本按列宽换行，行高自适应。"""

    def __init__(self, parent: QWidget | None = None, max_lines: int | None = None) -> None:
        super().__init__(parent)
        self._max_lines = max_lines

    @staticmethod
    def _wrap(text: str, metrics: QFontMetrics, width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in str(text).split("\n"):
            if not paragraph:
                lines.append("")
                continue
            current = ""
            for ch in paragraph:
                trial = current + ch
                if current and metrics.horizontalAdvance(trial) > width:
                    lines.append(current)
                    current = ch
                else:
                    current = trial
            if current:
                lines.append(current)
        return lines

    def _item_width(self, option, index) -> int:
        """换行宽度：paint 与 sizeHint 必须使用同一来源，否则行高与绘制行数不一致导致字体重叠。

        树：按视口宽度保守估计（扣除缩进/滚动条余量）；表格：取列宽。
        """
        view = self.parent()
        if isinstance(view, QTreeWidget):
            width = view.viewport().width() - 40
        elif isinstance(view, QTableWidget):
            width = view.columnWidth(index.column())
            if width <= 0:
                width = option.rect.width()
        else:
            width = option.rect.width()
        if width <= 0:
            width = 320
        return width

    def paint(self, painter: QPainter, option, index) -> None:  # type: ignore[override]
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(text, str) or not text.strip():
            super().paint(painter, option, index)
            return
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            color = option.palette.highlightedText().color()
        else:
            color = option.palette.text().color()
        metrics = QFontMetrics(option.font)
        width = self._item_width(option, index) - 8
        lines = self._wrap(text, metrics, max(width, 10))
        if self._max_lines and len(lines) > self._max_lines:
            lines = lines[: self._max_lines]
        line_height = metrics.height()
        rect = option.rect.adjusted(4, 2, -4, -2)
        painter.setFont(option.font)
        painter.setPen(color)
        y = rect.top()
        for line in lines:
            painter.drawText(
                QRect(rect.left(), y, rect.width(), line_height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line,
            )
            y += line_height
        painter.restore()

    def sizeHint(self, option, index) -> object:  # type: ignore[override]
        hint = super().sizeHint(option, index)
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(text, str) or not text.strip():
            return hint
        metrics = QFontMetrics(option.font)
        width = self._item_width(option, index) - 8
        lines = self._wrap(text, metrics, max(width, 10))
        if self._max_lines:
            lines = lines[: self._max_lines]
        height = max(int(hint.height()), len(lines) * metrics.height() + 6)
        return QRect(0, 0, int(hint.width()), height).size()


class AbilitySearchTab(QWidget):
    """能力实现搜索：三通道搜索（对象文本 / 能力层 / 效果词扩展）→ 对象详情。

    详情 = 数据表（主表+副表，相邻加成专门渲染）+ 能力树（Modifier 全链路，
    ATTACH/GRANT_ABILITY 嵌套递归展开）。支持前进/后退导航与树内过滤。
    """

    def __init__(self, host: QWidget | None = None) -> None:
        super().__init__()
        self._host = host
        self._current_results: list[dict[str, object]] = []
        self._history: list[tuple[str, str]] = []
        self._history_index = -1
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        search_box = QGroupBox("搜索")
        search_layout = QHBoxLayout(search_box)
        self._query_input = QLineEdit()
        self._query_input.setPlaceholderText(
            '输入中文（名字/描述/效果词）或英文（Type/ModifierId/参数），如 "宣战"、"WAR"、"港口"'
        )
        self._query_input.returnPressed.connect(self._run_search)
        search_layout.addWidget(self._query_input, 1)
        self._category_combo = QComboBox()
        self._category_combo.addItem("全部对象", None)
        for key in OBJECT_TYPE_ORDER:
            self._category_combo.addItem(OBJECT_CATEGORY_LABELS[key], key)
        search_layout.addWidget(self._category_combo)
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._run_search)
        search_layout.addWidget(search_btn)
        root.addWidget(search_box)

        self._hint_label = QLabel("提示：中文搜名字/描述/效果（如“宣战”）；英文搜 Type/能力/条件（如 WAR）。双击结果打开详情。")
        self._hint_label.setStyleSheet("color:#64748b; font-size:11px;")
        self._hint_label.setWordWrap(True)
        root.addWidget(self._hint_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 左侧：结果表 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        self._result_table = QTableWidget()
        self._result_table.setColumnCount(6)
        self._result_table.setHorizontalHeaderLabels(["分类", "名称", "Type", "命中", "描述", "摘要"])
        self._result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.verticalHeader().setVisible(False)
        # 描述列自动换行（完整文本，行高按内容自适应——必须 ResizeToContents 才会采用 sizeHint 行高）
        self._result_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._result_table.setItemDelegateForColumn(4, WordWrapDelegate(self._result_table))
        header = self._result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._result_table.itemDoubleClicked.connect(self._on_result_activated)
        self._result_table.itemSelectionChanged.connect(self._show_result_preview)
        self._result_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._result_table.customContextMenuRequested.connect(self._show_result_menu)
        left_layout.addWidget(self._result_table, 1)
        # 选中行完整描述预览
        self._result_preview = QPlainTextEdit()
        self._result_preview.setReadOnly(True)
        self._result_preview.setPlaceholderText("选中搜索结果后在此显示完整描述")
        self._result_preview.setMaximumHeight(110)
        left_layout.addWidget(self._result_preview)
        self._result_status = QLabel("输入关键词开始搜索")
        self._result_status.setStyleSheet("color:#64748b; font-size:11px;")
        left_layout.addWidget(self._result_status)
        splitter.addWidget(left)

        # ── 右侧：详情 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        nav_row = QHBoxLayout()
        self._back_btn = QPushButton("← 后退")
        self._back_btn.clicked.connect(self._nav_back)
        self._back_btn.setEnabled(False)
        nav_row.addWidget(self._back_btn)
        self._forward_btn = QPushButton("前进 →")
        self._forward_btn.clicked.connect(self._nav_forward)
        self._forward_btn.setEnabled(False)
        nav_row.addWidget(self._forward_btn)
        self._title_label = QLabel("未选择对象")
        self._title_label.setStyleSheet("font-weight:600;")
        self._title_label.setWordWrap(True)
        nav_row.addWidget(self._title_label, 1)
        right_layout.addLayout(nav_row)

        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("过滤树节点（表名/字段/ModifierId/参数名）")
        self._filter_input.textChanged.connect(self._apply_filter)
        right_layout.addWidget(self._filter_input)

        detail_splitter = QSplitter(Qt.Orientation.Vertical)
        self._modifier_tree = QTreeWidget()
        self._modifier_tree.setHeaderHidden(True)
        self._data_tree = QTreeWidget()
        self._data_tree.setHeaderHidden(True)
        detail_splitter.addWidget(self._modifier_tree)
        detail_splitter.addWidget(self._data_tree)
        detail_splitter.setSizes([340, 260])
        right_layout.addWidget(detail_splitter, 1)

        splitter.addWidget(right)
        splitter.setSizes([380, 640])
        root.addWidget(splitter, 1)

        for tree in (self._modifier_tree, self._data_tree):
            tree.setItemDelegate(WordWrapDelegate(tree))
            tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tree.customContextMenuRequested.connect(self._show_tree_menu)

    # ── 搜索 ──
    def _run_search(self) -> None:
        keyword = self._query_input.text().strip()
        if not keyword:
            return
        settings = load_settings()
        if not settings.game_db_path or not Path(settings.game_db_path).exists():
            QMessageBox.warning(self, "提示", "未配置游戏数据库（DebugGameplay.sqlite），请先到设置页配置。")
            return
        category = self._category_combo.currentData()
        try:
            with open_dbs(settings.game_db_path, settings.active_text_db_path) as (game_conn, loc_conn):
                result = search_all(game_conn, loc_conn, keyword, category=category)
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"搜索失败：{exc}")
            return
        self._current_results = result["results"]
        self._fill_result_table(result["results"])
        hint = str(result.get("hint") or "")
        if hint:
            self._hint_label.setText(hint)
        else:
            self._hint_label.setText("提示：中文搜名字/描述/效果；英文搜 Type/能力/条件。双击结果打开详情。")
        self._result_status.setText(f"命中 {len(result['results'])} 个对象")

    def _fill_result_table(self, results: list[dict[str, object]]) -> None:
        self._result_table.setRowCount(len(results))
        for row_index, item in enumerate(results):
            for col_index, key in enumerate(("label", "name", "type", "hit", "description", "summary")):
                cell = QTableWidgetItem(str(item.get(key) or ""))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cell.setData(Qt.ItemDataRole.UserRole, (item.get("category"), item.get("type")))
                self._result_table.setItem(row_index, col_index, cell)
        self._result_preview.clear()

    def _show_result_preview(self) -> None:
        """选中结果行 → 底部预览完整描述。"""
        row_index = self._result_table.currentRow()
        if row_index < 0:
            return
        item = self._result_table.item(row_index, 0)
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            return
        category, type_value = str(data[0]), str(data[1])
        label = self._result_table.item(row_index, 0).text() if self._result_table.item(row_index, 0) else ""
        name = self._result_table.item(row_index, 1).text() if self._result_table.item(row_index, 1) else ""
        hit = self._result_table.item(row_index, 3).text() if self._result_table.item(row_index, 3) else ""
        description = self._result_table.item(row_index, 4).text() if self._result_table.item(row_index, 4) else ""
        summary = self._result_table.item(row_index, 5).text() if self._result_table.item(row_index, 5) else ""
        lines = [f"【{label}】{name}  （{type_value}）  命中：{hit}"]
        if description:
            lines.append(description)
        if summary and summary != name:
            lines.append(f"命中详情：{summary}")
        self._result_preview.setPlainText("\n".join(lines))

    def _on_result_activated(self, item: QTableWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and len(data) == 2 and data[0] and data[1]:
            self._open_detail(str(data[0]), str(data[1]))

    def _show_result_menu(self, pos) -> None:
        item = self._result_table.itemAt(pos)
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        open_act = menu.addAction("打开详情")
        copy_act = menu.addAction("复制 Type")
        chosen = menu.exec(self._result_table.viewport().mapToGlobal(pos))
        if not isinstance(data, tuple) or len(data) != 2:
            return
        if chosen == open_act and data[0] and data[1]:
            self._open_detail(str(data[0]), str(data[1]))
        elif chosen == copy_act:
            QApplication.clipboard().setText(str(data[1]))

    # ── 详情与导航 ──
    def _open_detail(self, category: str, type_value: str) -> None:
        settings = load_settings()
        try:
            with open_dbs(settings.game_db_path, settings.active_text_db_path) as (game_conn, loc_conn):
                detail = fetch_object_detail(game_conn, loc_conn, category, type_value)
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"加载详情失败：{exc}")
            return
        if not detail:
            self._title_label.setText(f"未找到对象：{type_value}")
            return
        self._nav_push(category, type_value)
        self._filter_input.clear()
        self._title_label.setText(f"{detail.get('label', '')}：{detail.get('name', '')}（{detail.get('type', '')}）")
        self._render_detail(detail)

    def _nav_push(self, category: str, type_value: str) -> None:
        if self._history and self._history[self._history_index] == (category, type_value):
            return
        self._history = self._history[: self._history_index + 1]
        self._history.append((category, type_value))
        self._history_index = len(self._history) - 1
        self._update_nav_buttons()

    def _nav_back(self) -> None:
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._reopen_history()

    def _nav_forward(self) -> None:
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self._reopen_history()

    def _reopen_history(self) -> None:
        category, type_value = self._history[self._history_index]
        self._open_detail(category, type_value)

    def _update_nav_buttons(self) -> None:
        self._back_btn.setEnabled(self._history_index > 0)
        self._forward_btn.setEnabled(self._history_index < len(self._history) - 1)

    # ── 详情渲染 ──
    def _render_detail(self, detail: dict[str, object]) -> None:
        self._modifier_tree.clear()
        self._data_tree.clear()
        self._render_data_tree(detail)
        self._render_modifier_tree(detail)

    def _render_data_tree(self, detail: dict[str, object]) -> None:
        data_root = QTreeWidgetItem(self._data_tree, ["📄 数据表"])
        main = detail.get("main") if isinstance(detail.get("main"), dict) else {}
        main_values = main.get("values") if isinstance(main.get("values"), dict) else {}
        main_node = QTreeWidgetItem(data_root, [f"主表 {main.get('table', '')}（{len(main_values)} 列）"])
        for key, value in main_values.items():
            QTreeWidgetItem(main_node, [f"{key}: {value}"])
        main_node.setExpanded(True)

        for st in detail.get("sub_tables", []):
            if not isinstance(st, dict):
                continue
            rows = st.get("rows", [])
            if st.get("kind") == "adjacency":
                table_node = QTreeWidgetItem(data_root, [f"{st.get('table', '')}（{len(rows)} 条相邻加成）"])
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    row_node = QTreeWidgetItem(table_node, [f"🏷️ {r.get('description', '')}"])
                    for s in r.get("sources", []):
                        if isinstance(s, dict) and s.get("cn"):
                            QTreeWidgetItem(row_node, [f"条件: {s['cn']}"])
                    QTreeWidgetItem(
                        row_node,
                        [f"产出: {r.get('yield_type', '')} ×{r.get('yield_change', '')}（每 {r.get('tiles_required', '')} 格）"],
                    )
                    original = str(r.get("original_description") or "").strip()
                    if original:
                        QTreeWidgetItem(row_node, [f"原始描述: {original}"])
                    row_node.setToolTip(0, f"ID: {r.get('id', '')}")
            else:
                table_node = QTreeWidgetItem(data_root, [f"{st.get('table', '')}（{len(rows)} 行）"])
                for r in rows:
                    if isinstance(r, dict):
                        QTreeWidgetItem(table_node, [" | ".join(f"{k}={v}" for k, v in r.items())])
        for binder in detail.get("binders", []):
            QTreeWidgetItem(data_root, [f"被使用: {binder}"])
        data_root.setExpanded(True)

    def _render_modifier_tree(self, detail: dict[str, object]) -> None:
        mod_root = QTreeWidgetItem(self._modifier_tree, ["⚡ 能力 Modifiers"])
        groups = detail.get("modifier_groups", [])
        for group in groups:
            if not isinstance(group, dict):
                continue
            modifiers = group.get("modifiers", [])
            group_node = QTreeWidgetItem(mod_root, [f"{group.get('source', '')}（{len(modifiers)}）"])
            for m in modifiers:
                if isinstance(m, dict):
                    self._append_modifier_node(group_node, m, 0)
            group_node.setExpanded(True)
        if not groups:
            QTreeWidgetItem(mod_root, ["（该对象无直接绑定 Modifier，能力可能来自建筑/特质/相邻加成）"])
        mod_root.setExpanded(True)

    def _append_modifier_node(self, parent: QTreeWidgetItem, m: dict[str, object], depth: int) -> None:
        effect = str(m.get("effect_type") or "")
        title = str(m.get("modifier_id") or "")
        if effect:
            title = f"{title}  [{effect}]"
        node = QTreeWidgetItem(parent, [title])
        node.setData(0, Qt.ItemDataRole.UserRole, str(m.get("modifier_id") or ""))

        # Modifiers 表标志：仅显示非默认值（永久/仅一次/上限等）
        flags = [str(f) for f in m.get("flags", []) if str(f)]
        if flags:
            QTreeWidgetItem(node, ["标志: " + "、".join(flags)])

        for arg in m.get("args", []):
            if isinstance(arg, dict):
                QTreeWidgetItem(node, [f"参数: {arg.get('name', '')} = {arg.get('value', '')}"])
        for rs in m.get("reqsets", []):
            if not isinstance(rs, dict):
                continue
            rs_node = QTreeWidgetItem(node, [f"条件集({rs.get('role', '')}): {rs.get('id', '')}"])
            for req in rs.get("requirements", []):
                if not isinstance(req, dict):
                    continue
                req_text = f"{req.get('requirement_id', '')}  [{req.get('requirement_type', '')}]"
                if req.get("inverse"):
                    req_text += " (Inverse)"
                req_node = QTreeWidgetItem(rs_node, [req_text])
                for a in req.get("args", []):
                    if isinstance(a, dict):
                        QTreeWidgetItem(req_node, [f"参数: {a.get('name', '')} = {a.get('value', '')}"])
                nested_rs = req.get("nested_reqset")
                if isinstance(nested_rs, dict) and nested_rs.get("id"):
                    nested_node = QTreeWidgetItem(req_node, [f"嵌套条件集: {nested_rs.get('id', '')}"])
                    for nreq in nested_rs.get("requirements", []):
                        if isinstance(nreq, dict):
                            QTreeWidgetItem(
                                nested_node,
                                [f"{nreq.get('requirement_id', '')}  [{nreq.get('requirement_type', '')}]"],
                            )
        for child in m.get("nested", []):
            if isinstance(child, dict):
                self._append_modifier_node(node, child, depth + 1)
        # ModifierStrings：有内容才显示（Text 已在查询层解析为中文）
        for s in m.get("strings", []):
            if isinstance(s, dict) and str(s.get("text") or "").strip():
                context = str(s.get("context") or "").strip()
                label = f"预览文本: {s.get('text')}" if not context else f"预览文本({context}): {s.get('text')}"
                QTreeWidgetItem(node, [label])
        node.setExpanded(depth < 2)

    # ── 过滤 ──
    def _apply_filter(self, text: str) -> None:
        keyword = text.strip().lower()
        for tree in (self._modifier_tree, self._data_tree):
            self._filter_tree_recursive(tree.invisibleRootItem(), keyword)

    def _filter_tree_recursive(self, root: QTreeWidgetItem, keyword: str) -> None:
        for i in range(root.childCount()):
            item = root.child(i)
            self._filter_tree_recursive(item, keyword)
            text = (item.text(0) or "").lower()
            visible = (not keyword) or (keyword in text) or self._has_visible_child(item)
            item.setHidden(not visible)

    @staticmethod
    def _has_visible_child(item: QTreeWidgetItem) -> bool:
        for i in range(item.childCount()):
            if not item.child(i).isHidden():
                return True
        return False

    # ── 右键复制 ──
    def _show_tree_menu(self, pos) -> None:
        tree = self.sender()
        if not isinstance(tree, QTreeWidget):
            return
        item = tree.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        copy_act = menu.addAction("复制文本")
        chosen = menu.exec(tree.viewport().mapToGlobal(pos))
        if chosen == copy_act:
            QApplication.clipboard().setText(item.text(0))
