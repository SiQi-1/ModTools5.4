"""Application bootstrap entry points."""
from __future__ import annotations

import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .config import AppConfig, load_config
from .logging_setup import configure_logging
from ..ui.assets import app_icon_path
from ..ui.main_window import MainWindow


class ModToolsApplication(QApplication):
    """Thin wrapper over QApplication for future service wiring."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        super().__init__(sys.argv)


def build_application(config: AppConfig | None = None) -> ModToolsApplication:
    """Create application with logging/config prepared."""
    active_config = config or load_config()
    configure_logging(active_config.log_dir, active_config.debug)
    app = ModToolsApplication(active_config)
    app.setApplicationName(active_config.app_title)
    icon_path = app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    return app


def launch(config: AppConfig | None = None) -> int:
    """Launch the ModTools 5.4 GUI."""
    app = build_application(config)
    window = MainWindow(app.config)
    window.show()
    return app.exec()
