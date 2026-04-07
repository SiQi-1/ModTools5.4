"""Conflict file selection dialog for text import."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class ConflictFileDialog(QDialog):
    """Let user decide which files can override conflicting tags."""

    def __init__(self, files: list[Path], title: str = "文本冲突处理", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(620, 480)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        desc = QLabel("检测到冲突 Tag。请选择允许覆盖冲突 Tag 的文件：\n未勾选文件仅忽略冲突 Tag，非冲突内容仍会导入。")
        desc.setWordWrap(True)

        for file_path in files:
            item = QListWidgetItem(str(file_path))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._list.addItem(item)

        select_all_btn = QPushButton("全选")
        select_none_btn = QPushButton("全不选")
        select_all_btn.clicked.connect(self._check_all)
        select_none_btn.clicked.connect(self._uncheck_all)

        row = QHBoxLayout()
        row.addWidget(select_all_btn)
        row.addWidget(select_none_btn)
        row.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(desc)
        layout.addLayout(row)
        layout.addWidget(self._list)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _check_all(self) -> None:
        for index in range(self._list.count()):
            self._list.item(index).setCheckState(Qt.CheckState.Checked)

    def _uncheck_all(self) -> None:
        for index in range(self._list.count()):
            self._list.item(index).setCheckState(Qt.CheckState.Unchecked)

    def selected_files(self) -> set[Path]:
        selected: set[Path] = set()
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected.add(Path(item.text()))
        return selected
