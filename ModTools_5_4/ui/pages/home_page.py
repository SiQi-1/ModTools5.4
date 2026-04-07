"""Home page with quick navigation cards."""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .base_page import BasePage
from ..assets import home_hero_bg_path

NavigationTarget = Callable[[str], None]


class HomePage(BasePage):
    """Landing page inspired by ModTools 5.0 simple workflow entry."""

    page_id = "home"
    display_name = "主页"

    def __init__(self, navigate_to: NavigationTarget) -> None:
        super().__init__()
        self._navigate_to = navigate_to
        self._background_pixmap = QPixmap()
        bg_path = home_hero_bg_path()
        if bg_path.exists():
            loaded = QPixmap(str(bg_path))
            if not loaded.isNull():
                self._background_pixmap = loaded
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(0)
        layout.setContentsMargins(36, 24, 36, 24)

        content_card = QWidget()
        content_card.setObjectName("homeContentCard")
        content_card.setMaximumWidth(680)

        card_layout = QVBoxLayout(content_card)
        card_layout.setSpacing(14)
        card_layout.setContentsMargins(30, 24, 30, 24)

        title = QLabel("ModTools 5.4")
        title.setObjectName("homeHeroLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("文明6 Mod 一体化编辑工作台")
        subtitle.setObjectName("homeSubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        for target, text in (
            ("workspace", "进入工作区"),
            ("search", "进入搜索页"),
            ("settings", "进入设置页"),
        ):
            button = QPushButton(text)
            button.setObjectName(f"homeButton_{target}")
            button.setProperty("homePrimary", "true")
            button.setFixedHeight(58)
            button.clicked.connect(lambda checked=False, t=target: self._navigate_to(t))
            card_layout.addWidget(button)

        layout.addStretch(1)
        layout.addWidget(content_card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.setLayout(layout)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        if not self._background_pixmap.isNull():
            scaled = self._background_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            draw_x = (self.width() - scaled.width()) // 2
            draw_y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(draw_x, draw_y, scaled)

            top_gradient = QLinearGradient(0, 0, 0, self.height())
            top_gradient.setColorAt(0.0, QColor(16, 24, 41, 156))
            top_gradient.setColorAt(0.35, QColor(20, 31, 53, 98))
            top_gradient.setColorAt(1.0, QColor(255, 255, 255, 56))
            painter.fillRect(self.rect(), top_gradient)

            warm_overlay = QLinearGradient(0, 0, self.width(), self.height())
            warm_overlay.setColorAt(0.0, QColor(201, 166, 96, 34))
            warm_overlay.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(self.rect(), warm_overlay)
        else:
            painter.fillRect(self.rect(), Qt.GlobalColor.white)
        super().paintEvent(event)
