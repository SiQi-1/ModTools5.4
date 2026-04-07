"""Debug tools page for quick manual testing."""
from __future__ import annotations

import heapq
from pathlib import Path
import sqlite3

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from .base_page import BasePage
from ...app.settings_store import load_settings
from ...db.text_database import query_text_by_tag
from ..ui_widget_kit import BaseTemplateWidget, TEMPLATE_SPECS, UITemplateSpec, build_template_widget


class UITemplateBadge(QWidget):
    """Compact badge representing a template instance."""

    def __init__(
        self,
        template_id: int,
        template_name: str,
        remove_callback,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._template_id = template_id
        self._remove_callback = remove_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._label = QLabel(f"编号 {template_id}: {template_name}")
        layout.addWidget(self._label)
        layout.addStretch(1)

        self._remove_btn = QPushButton("删除")
        self._remove_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove_btn.clicked.connect(self._on_remove_clicked)
        layout.addWidget(self._remove_btn)

    def _on_remove_clicked(self) -> None:
        self._remove_callback(self._template_id)

    def cleanup(self) -> None:
        try:
            self._remove_btn.clicked.disconnect(self._on_remove_clicked)
        except Exception:
            pass


class CanvasWidget(QWidget):
    """Scrollable canvas that hosts draggable cards."""

    BASE_MIN_WIDTH = 520
    BASE_MIN_HEIGHT = 560

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: #f8fafc; border: 1px dashed #94a3b8;")
        self.setMinimumSize(self.BASE_MIN_WIDTH, self.BASE_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def request_card_geometry(self, card: QWidget, rect: QRect) -> None:
        rect = rect.normalized()
        if rect.left() < 0:
            rect.moveLeft(0)
        if rect.top() < 0:
            rect.moveTop(0)
        card.setGeometry(rect)
        self._recompute_extent()

    def _recompute_extent(self) -> None:
        max_right = 0
        max_bottom = 0
        for child in self.findChildren(QWidget):
            if child is self:
                continue
            if not child.isVisible():
                continue
            rect = child.geometry()
            max_right = max(max_right, rect.right())
            max_bottom = max(max_bottom, rect.bottom())

        padding = 40
        target_width = max(self.BASE_MIN_WIDTH, max_right + padding)
        target_height = max(self.BASE_MIN_HEIGHT, max_bottom + padding)
        if target_width != self.minimumWidth() or target_height != self.minimumHeight():
            self.setMinimumSize(target_width, target_height)
            self.updateGeometry()


class MoveHandleButton(QPushButton):
    """Dedicated handle for card movement."""

    def __init__(self, card: "DraggableResizableCard") -> None:
        super().__init__("移动")
        self._card = card
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            local_point = self.mapTo(self._card, event.position().toPoint())
            self._card.begin_move(event.globalPosition(), local_point)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._card.perform_move(event.globalPosition())
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._card.end_move()
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        super().mouseReleaseEvent(event)


class DraggableResizableCard(QWidget):
    """Card wrapper embedding a template widget."""

    MIN_WIDTH = 220
    MIN_HEIGHT = 150

    def __init__(
        self,
        template_id: int,
        spec: UITemplateSpec,
        template_widget: BaseTemplateWidget,
        canvas: CanvasWidget,
        remove_callback,
        data_changed_callback,
    ) -> None:
        super().__init__(canvas)
        self._template_id = template_id
        self._spec = spec
        self._template_widget = template_widget
        self._canvas = canvas
        self._remove_callback = remove_callback
        self._data_changed_callback = data_changed_callback

        self._move_active = False
        self._move_offset = QPoint(0, 0)
        self.setMouseTracking(True)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.setStyleSheet("background: #ffffff; border: 1px solid #cbd5f5; border-radius: 10px;")

        self._template_widget.setParent(self)
        self._template_widget.dataChanged.connect(self._handle_data_changed)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        title = QLabel(f"编号：{self._template_id} · {self._spec.name}")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        delete_btn = QPushButton("删除")
        delete_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        delete_btn.clicked.connect(self._on_delete_clicked)
        header_layout.addWidget(delete_btn)
        layout.addWidget(header_container)

        content_container = QFrame()
        content_container.setFrameShape(QFrame.Shape.NoFrame)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._template_widget)
        layout.addWidget(content_container, 1)

        footer_container = QWidget()
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        self._move_handle = MoveHandleButton(self)
        footer_layout.addWidget(self._move_handle)
        layout.addWidget(footer_container)

    def begin_move(self, global_pos: QPointF, local_point: QPoint) -> None:
        self._move_active = True
        self._move_offset = local_point
        self.raise_()
        self.perform_move(global_pos)

    def perform_move(self, global_pos: QPointF) -> None:
        if not self._move_active:
            return
        parent = self.parentWidget()
        if parent is None:
            return
        parent_point = parent.mapFromGlobal(global_pos.toPoint())
        new_top_left = parent_point - self._move_offset
        rect = QRect(new_top_left, self.geometry().size())
        self._apply_geometry(rect)

    def end_move(self) -> None:
        self._move_active = False

    def _apply_geometry(self, rect: QRect) -> None:
        rect = rect.normalized()
        if rect.width() < self.MIN_WIDTH:
            rect.setWidth(self.MIN_WIDTH)
        if rect.height() < self.MIN_HEIGHT:
            rect.setHeight(self.MIN_HEIGHT)
        self._canvas.request_card_geometry(self, rect)

    def _on_delete_clicked(self) -> None:
        self._remove_callback(self._template_id)

    def _handle_data_changed(self) -> None:
        self._data_changed_callback(self._template_id)

    def summary_text(self) -> str:
        return self._template_widget.summary_text()

    def template_name(self) -> str:
        return self._spec.name

    def template_key(self) -> str:
        return self._spec.key

    def export_data(self) -> dict[str, object]:
        return self._template_widget.export_data()

    def dispose(self) -> None:
        try:
            self._template_widget.dataChanged.disconnect(self._handle_data_changed)
        except Exception:
            pass


class UITestManager:
    """Coordinates template instances across UI areas."""

    def __init__(
        self,
        specs: tuple[UITemplateSpec, ...],
        badge_layout: QVBoxLayout,
        badge_placeholder: QLabel,
        canvas: CanvasWidget,
        data_table: QTableWidget,
    ) -> None:
        self._specs = {spec.key: spec for spec in specs}
        self._badge_layout = badge_layout
        self._badge_placeholder = badge_placeholder
        self._canvas = canvas
        self._data_table = data_table
        self._cards: dict[int, DraggableResizableCard] = {}
        self._badges: dict[int, UITemplateBadge] = {}
        self._freed_ids: list[int] = []
        self._next_id = 1

        self._configure_table()
        self._show_placeholder(True)

    def _configure_table(self) -> None:
        self._data_table.setColumnCount(4)
        self._data_table.setHorizontalHeaderLabels(["编号", "模板Key", "英文数据", "中文参考"])
        header = self._data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        v_header = self._data_table.verticalHeader()
        v_header.setDefaultSectionSize(28)
        self._data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._data_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._data_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def _show_placeholder(self, visible: bool) -> None:
        self._badge_placeholder.setVisible(visible)

    def _allocate_id(self) -> int:
        if self._freed_ids:
            return heapq.heappop(self._freed_ids)
        value = self._next_id
        self._next_id += 1
        return value

    def add_card(self, template_key: str) -> None:
        spec = self._specs.get(template_key)
        if spec is None:
            return
        template_widget = build_template_widget(spec.key)
        template_id = self._allocate_id()

        card = DraggableResizableCard(
            template_id=template_id,
            spec=spec,
            template_widget=template_widget,
            canvas=self._canvas,
            remove_callback=self.remove_card,
            data_changed_callback=self.notify_data_changed,
        )

        card_size = card.sizeHint()
        width = max(card_size.width(), card.MIN_WIDTH)
        height = max(card_size.height(), card.MIN_HEIGHT)
        column = (template_id - 1) % 3
        row = (template_id - 1) // 3
        x = 30 + column * (width + 30)
        y = 30 + row * (height + 30)
        self._canvas.request_card_geometry(card, QRect(x, y, width, height))
        card.show()

        badge = UITemplateBadge(template_id, spec.name, self.remove_card)
        insert_index = max(0, self._badge_layout.count() - 1)
        self._badge_layout.insertWidget(insert_index, badge)

        self._cards[template_id] = card
        self._badges[template_id] = badge
        self._show_placeholder(False)
        self._refresh_data_table()

    def remove_card(self, template_id: int) -> None:
        card = self._cards.pop(template_id, None)
        if card is None:
            return
        card.dispose()
        card.setParent(None)
        card.deleteLater()

        badge = self._badges.pop(template_id, None)
        if badge is not None:
            badge.cleanup()
            badge.setParent(None)
            badge.deleteLater()

        heapq.heappush(self._freed_ids, template_id)
        self._show_placeholder(not self._cards)
        self._refresh_data_table()

    def notify_data_changed(self, template_id: int) -> None:
        if template_id not in self._cards:
            return
        self._refresh_data_table()

    def _refresh_data_table(self) -> None:
        sorted_ids = sorted(self._cards.keys())
        self._data_table.setRowCount(len(sorted_ids))
        for row_index, template_id in enumerate(sorted_ids):
            card = self._cards[template_id]
            id_item = QTableWidgetItem(str(template_id))
            type_item = QTableWidgetItem(card.template_key())
            english_value = self._extract_primary_value(card.export_data())
            data_item = QTableWidgetItem(english_value)
            reference_item = QTableWidgetItem(card.template_name())
            for item in (id_item, type_item, data_item, reference_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._data_table.setItem(row_index, 0, id_item)
            self._data_table.setItem(row_index, 1, type_item)
            self._data_table.setItem(row_index, 2, data_item)
            self._data_table.setItem(row_index, 3, reference_item)

    def _extract_primary_value(self, data: dict[str, object]) -> str:
        if not data:
            return ""

        preferred_keys = ("value", "type", "key", "id")
        for key in preferred_keys:
            if key in data and data[key] not in (None, ""):
                return str(data[key])

        for key, value in data.items():
            if key.endswith("_type") and value not in (None, ""):
                return str(value)

        for key, value in data.items():
            if key in {"display", "name", "label", "text"}:
                continue
            if value not in (None, ""):
                return str(value)

        return ""


class DebugPage(BasePage):
    """ModTools 5.4 的 DEBUG 页面。"""

    page_id = "debug"
    display_name = "DEBUG"

    def __init__(self) -> None:
        super().__init__()
        self._tag_input = QLineEdit()
        self._text_result = QPlainTextEdit()
        self._text_result.setReadOnly(True)
        self._game_sql_input = QPlainTextEdit()
        self._game_sql_result = QTableWidget()
        self._game_sql_message = QLabel("")

        self._ui_manager: UITestManager | None = None
        self._ui_template_combo: QComboBox | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_body = QWidget()
        body_layout = QVBoxLayout(scroll_body)
        body_layout.setContentsMargins(8, 8, 8, 8)
        body_layout.setSpacing(12)

        title = QLabel("DEBUG 页面")
        title.setObjectName("pageHeaderLabel")
        body_layout.addWidget(title)

        body_layout.addWidget(self._build_text_db_test_group())
        body_layout.addWidget(self._build_game_db_test_group())
        body_layout.addWidget(self._build_ui_test_group())
        body_layout.addStretch(1)

        page_scroll.setWidget(scroll_body)
        root.addWidget(page_scroll)

    def _build_text_db_test_group(self) -> QGroupBox:
        group = QGroupBox("文本数据库测试区")

        self._tag_input.setPlaceholderText("输入 Tag，例如 LOC_UNIT_WARRIOR_NAME")
        resolve_btn = QPushButton("通过 Tag 获取文本")
        resolve_btn.clicked.connect(self._resolve_text)

        row = QHBoxLayout()
        row.addWidget(self._tag_input)
        row.addWidget(resolve_btn)

        layout = QVBoxLayout(group)
        layout.addLayout(row)
        layout.addWidget(self._text_result)
        return group

    def _build_game_db_test_group(self) -> QGroupBox:
        group = QGroupBox("游戏数据库测试区")

        self._game_sql_input.setPlaceholderText("输入 SELECT 语句，例如：SELECT UnitType, Name FROM Units LIMIT 10;")
        self._game_sql_input.setFixedHeight(90)

        sample_btn = QPushButton("填充示例")
        sample_btn.clicked.connect(self._fill_game_sql_example)

        run_btn = QPushButton("执行 SELECT")
        run_btn.clicked.connect(self._run_game_sql)

        action_row = QHBoxLayout()
        action_row.addWidget(sample_btn)
        action_row.addWidget(run_btn)
        action_row.addStretch(1)

        self._game_sql_message.setObjectName("pageInfoLabel")
        self._game_sql_message.setWordWrap(True)

        self._game_sql_result.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._game_sql_result.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._game_sql_result.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        layout = QVBoxLayout(group)
        layout.addWidget(self._game_sql_input)
        layout.addLayout(action_row)
        layout.addWidget(self._game_sql_message)
        layout.addWidget(self._game_sql_result)
        return group

    def _build_ui_test_group(self) -> QGroupBox:
        group = QGroupBox("UI控件测试区")
        container_layout = QVBoxLayout(group)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(10)

        control_box = QGroupBox("添加/删除UI模版")
        control_layout = QVBoxLayout(control_box)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("选择模版:"))

        template_combo = QComboBox()
        for spec in TEMPLATE_SPECS:
            template_combo.addItem(spec.name, userData=spec.key)
        self._ui_template_combo = template_combo
        selector_row.addWidget(template_combo, 1)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._handle_add_template)
        selector_row.addWidget(add_btn)

        control_layout.addLayout(selector_row)
        container_layout.addWidget(control_box)

        badge_box = QGroupBox("模版实例列表")
        badge_layout = QVBoxLayout(badge_box)
        badge_placeholder = QLabel("暂无模版实例")
        badge_layout.addWidget(badge_placeholder)
        badge_layout.addStretch(1)
        container_layout.addWidget(badge_box)

        canvas_box = QGroupBox("拖拽预览区")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas = CanvasWidget()
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(True)
        canvas_scroll.setFrameShape(QFrame.Shape.NoFrame)
        canvas_scroll.setWidget(canvas)
        canvas_scroll.setMinimumHeight(560)
        canvas_layout.addWidget(canvas_scroll)
        container_layout.addWidget(canvas_box)

        data_box = QGroupBox("模版数据")
        data_layout = QVBoxLayout(data_box)
        data_table = QTableWidget()
        data_table.setMinimumHeight(160)
        data_layout.addWidget(data_table)
        container_layout.addWidget(data_box)

        self._ui_manager = UITestManager(TEMPLATE_SPECS, badge_layout, badge_placeholder, canvas, data_table)
        return group

    def _handle_add_template(self) -> None:
        if self._ui_template_combo is None or self._ui_manager is None:
            return
        template_key = self._ui_template_combo.currentData()
        if not template_key:
            return
        self._ui_manager.add_card(str(template_key))

    def _resolve_text(self) -> None:
        tag = self._tag_input.text().strip()
        if not tag:
            self._text_result.setPlainText("请输入 Tag。")
            return

        settings = load_settings()
        if not settings.active_text_db_path:
            self._text_result.setPlainText("未配置当前文本数据库，请先到设置页选择文本数据库。")
            return

        db_path = Path(settings.active_text_db_path)
        if not db_path.exists():
            self._text_result.setPlainText(f"文本数据库不存在: {db_path}")
            return

        try:
            value = query_text_by_tag(db_path, tag, resolve_nested=True)
        except Exception as exc:
            self._text_result.setPlainText(f"查询失败: {exc}")
            return

        self._text_result.setPlainText(value)

    def _fill_game_sql_example(self) -> None:
        self._game_sql_input.setPlainText("SELECT UnitType, Name FROM Units LIMIT 10;")

    def _run_game_sql(self) -> None:
        sql = self._game_sql_input.toPlainText().strip()
        if not sql:
            self._game_sql_message.setText("请输入 SELECT 语句。")
            return

        if not sql.lower().startswith("select"):
            self._game_sql_message.setText("仅允许执行 SELECT 语句。")
            return

        settings = load_settings()
        db_path = Path(settings.game_db_path)
        if not db_path.exists():
            self._game_sql_message.setText(f"游戏数据库不存在: {db_path}")
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [meta[0] for meta in (cursor.description or [])]
            conn.close()
        except Exception as exc:
            self._game_sql_message.setText(f"查询失败: {exc}")
            return

        self._game_sql_result.clear()
        self._game_sql_result.setColumnCount(len(columns))
        self._game_sql_result.setHorizontalHeaderLabels(columns)
        self._game_sql_result.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                self._game_sql_result.setItem(row_index, col_index, item)

        self._game_sql_result.resizeColumnsToContents()
        self._game_sql_message.setText(f"查询成功：返回 {len(rows)} 行。")
