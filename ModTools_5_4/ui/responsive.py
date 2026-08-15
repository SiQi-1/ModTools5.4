"""宽度响应式布局组件：小窗口自动减少列数/堆叠。

- ResponsiveGrid：网格容器，按可用宽度切换列数（如 3→2→1）。
- ResponsiveSplit：两元素容器，宽时并排、窄时上下堆叠。

实现要点：布局对象只创建一次并永久安装，切换时清空重填，
绝不删除/替换布局——避免 deleteLater 异步删除期间 setLayout 冲突，
导致子控件失去布局管理而重叠。
"""
from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QGridLayout, QWidget


def _clear_layout(layout: QGridLayout) -> None:
    """取出全部 item（子控件仍为容器的 child，仅失去布局管理）。"""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            layout.removeWidget(item.widget())


class ResponsiveGrid(QWidget):
    """按宽度自动调整列数的网格容器。

    items: QWidget 或 (QWidget, colspan) 元组列表
    breakpoints: (min_width, columns) 降序；self.width() >= min_width 时用对应列数。
    """

    def __init__(
        self,
        items: Sequence[QWidget | tuple[QWidget, int]],
        breakpoints: Sequence[tuple[int, int]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items: list[tuple[QWidget, int]] = []
        for item in items:
            if isinstance(item, tuple):
                widget, colspan = item
            else:
                widget, colspan = item, 1
            self._items.append((widget, int(colspan)))
        self._breakpoints = sorted(breakpoints, key=lambda entry: -entry[0])
        self._current_cols: int | None = None
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(10)
        self._layout.setVerticalSpacing(8)
        self._relayout(self._cols_for_width(self.width()))
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_after_show)
        self._refresh_timer.start(400)

    def _cols_for_width(self, width: int) -> int:
        for min_width, columns in self._breakpoints:
            if width >= min_width:
                return columns
        return self._breakpoints[-1][1] if self._breakpoints else 1

    def _relayout(self, columns: int) -> None:
        if columns == self._current_cols:
            return
        self._current_cols = columns
        _clear_layout(self._layout)
        row = 0
        col = 0
        for widget, colspan in self._items:
            effective_span = min(colspan, columns)
            if col > 0 and col + effective_span > columns:
                row += 1
                col = 0
            self._layout.addWidget(widget, row, col, 1, effective_span)
            col += effective_span

    def _refresh_after_show(self) -> None:
        """构造时宽度可能为 0，显示后兜底重算一次。"""
        self._relayout(self._cols_for_width(self.width()))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._relayout(self._cols_for_width(self.width()))


class ResponsiveSplit(QWidget):
    """两元素：宽时左右并排，窄时上下堆叠。

    min_width: 低于此宽度切换为堆叠模式。
    """

    def __init__(
        self,
        left: QWidget,
        right: QWidget,
        min_width: int = 750,
        parent: QWidget | None = None,
        *,
        left_stretch: int = 1,
        right_stretch: int = 0,
    ) -> None:
        super().__init__(parent)
        self._left = left
        self._right = right
        self._min_width = int(min_width)
        self._left_stretch = int(left_stretch)
        self._right_stretch = int(right_stretch)
        self._side_by_side: bool | None = None
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(10)
        self._layout.setVerticalSpacing(8)
        self._relayout(self.width() >= self._min_width)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_after_show)
        self._refresh_timer.start(400)

    def _relayout(self, side_by_side: bool) -> None:
        if side_by_side == self._side_by_side:
            return
        self._side_by_side = side_by_side
        _clear_layout(self._layout)
        if side_by_side:
            self._layout.addWidget(self._left, 0, 0, 1, 1)
            self._layout.addWidget(self._right, 0, 1, 1, 1)
            self._layout.setRowStretch(0, self._left_stretch + self._right_stretch)
            self._layout.setColumnStretch(0, self._left_stretch)
            self._layout.setColumnStretch(1, self._right_stretch)
        else:
            self._layout.addWidget(self._left, 0, 0, 1, 1)
            self._layout.addWidget(self._right, 1, 0, 1, 1, Qt.AlignmentFlag.AlignTop)
            self._layout.setRowStretch(0, self._left_stretch)
            self._layout.setRowStretch(1, self._right_stretch)

    def _refresh_after_show(self) -> None:
        """构造时宽度可能为 0，显示后兜底重算一次。"""
        self._relayout(self.width() >= self._min_width)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._relayout(self.width() >= self._min_width)
