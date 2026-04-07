"""Base page widget definitions."""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class BasePage(QWidget):
    """Base class for stacked page widgets."""

    page_id: str = "base"
    display_name: str = ""

    def on_activate(self) -> None:
        """Hook called after the page becomes visible."""
        return
