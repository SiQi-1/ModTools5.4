"""Search page with text search and staged placeholders."""
from __future__ import annotations

from pathlib import Path
import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage
from ...app.settings_store import load_settings
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
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        info = QLabel("全局搜索用于跨分类定位内容；可先使用文本搜索与 ModifierType 搜索完成常用检索。")
        info.setObjectName("pageInfoLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        category_tabs = QTabWidget()
        for name in ("文明", "领袖", "区域", "单位", "建筑", "改良设施", "总督", "伟人", "信仰", "政策卡", "项目"):
            category_tabs.addTab(self._build_placeholder_panel(name), name)
        layout.addWidget(category_tabs, 1)
        return tab

    def _build_placeholder_panel(self, title: str) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(card)
        text = QLabel(f"{title}搜索入口已预留，可先通过工作区与上方专题搜索进行定位。")
        text.setObjectName("pageInfoLabel")
        text.setWordWrap(True)
        card_layout.addWidget(text)
        panel_layout.addWidget(card)
        panel_layout.addStretch(1)
        return panel

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
