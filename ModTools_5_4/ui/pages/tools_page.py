"""小工具窗口：搜索（能力实现 / 文本 / Modifiers）。

图片工具与 PSD 模板总结已按用户要求移除（2026-08-16）；
底层能力保留在 image_ops.py / psd_summarizer.py，后续新设计可复用。
"""
from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .search_page import SearchPage


class ToolsWindow(QWidget):
    """小工具独立窗口：搜索。

    设计：独立窗口便于与主窗口并排使用（边搜索边做 Mod）。
    关闭窗口 = 隐藏（保留搜索/操作状态），再次打开恢复。
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ModTools 小工具")
        self.resize(1100, 720)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(SearchPage())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """关闭即隐藏：保留搜索历史，重新打开时恢复。"""
        self.hide()
        event.ignore()
