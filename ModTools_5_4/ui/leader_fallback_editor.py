"""Compact state/image editor for leader diplomacy fallbacks."""
from copy import deepcopy

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QDialog, QLabel, QMessageBox,
)
from ..project.leader_fallbacks import FALLBACK_STATES


class LeaderFallbackEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mapping = {}
        layout = QVBoxLayout(self)
        self.toggle = QPushButton("外交表情差分（展开）")
        self.toggle.setCheckable(True)
        layout.addWidget(self.toggle)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["外交状态", "图片", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(280)
        self.table.setVisible(False)
        layout.addWidget(self.table)
        self.toggle.toggled.connect(self._toggle)
        self.set_value({})

    def _toggle(self, expanded):
        self.table.setVisible(expanded)
        self.toggle.setText("外交表情差分（收起）" if expanded else "外交表情差分（展开）")

    def set_value(self, value):
        # Preserve unknown/malformed input for validation instead of silently losing it.
        self._mapping = deepcopy(value) if value is not None else {}
        mapping = self._mapping if isinstance(self._mapping, dict) else {}
        states = list(FALLBACK_STATES) + [key for key in mapping if key not in FALLBACK_STATES]
        self.table.setRowCount(len(states))
        for row, state in enumerate(states):
            title = QTableWidgetItem(f"{FALLBACK_STATES.get(state, '未知状态')} · {state}")
            title.setFlags(title.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, title)
            image = mapping.get(state)
            path = image.get("path") if isinstance(image, dict) else None
            item = QTableWidgetItem(str(path or "使用默认回退"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(str(path or "未设置的状态使用 DEFAULT；DEFAULT 未设置时使用原外交前景图"))
            self.table.setItem(row, 1, item)
            buttons = QWidget()
            buttons_layout = QHBoxLayout(buttons)
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            for label, callback in (("选择", self._choose), ("清除", self._clear), ("预览", self._preview)):
                button = QPushButton(label)
                button.clicked.connect(lambda _checked=False, s=state, fn=callback: fn(s))
                buttons_layout.addWidget(button)
            self.table.setCellWidget(row, 2, buttons)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(2)

    def value(self):
        return deepcopy(self._mapping)

    def _choose(self, state):
        path, _ = QFileDialog.getOpenFileName(self, "选择外交表情", "", "图片 (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        mapping = self.value() if isinstance(self._mapping, dict) else {}
        # A new source resets the old image's crop; untouched states keep all metadata.
        mapping[state] = {"path": path}
        self.set_value(mapping)
        self.dataChanged.emit()

    def _clear(self, state):
        mapping = self.value() if isinstance(self._mapping, dict) else {}
        mapping.pop(state, None)
        self.set_value(mapping)
        self.dataChanged.emit()

    def _preview(self, state):
        image = self._mapping.get(state) if isinstance(self._mapping, dict) else None
        pixmap = QPixmap(str(image.get("path") or "")) if isinstance(image, dict) else QPixmap()
        if pixmap.isNull():
            QMessageBox.information(self, "外交表情", "此状态没有可读取的独立图片。")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"外交表情 · {state}")
        label = QLabel()
        label.setPixmap(pixmap.scaled(720, 720, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        QVBoxLayout(dialog).addWidget(label)
        dialog.exec()
