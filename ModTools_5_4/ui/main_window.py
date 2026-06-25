"""Main application window and navigation shell."""
from __future__ import annotations

import logging
from pathlib import Path
from functools import partial
from typing import Dict

from PyQt6.QtGui import QAction, QGuiApplication, QIcon
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox, QStackedWidget

from ..app.config import AppConfig
from ..project import CIV_FILE_EXTENSION
from .assets import app_icon_path
from .theme import load_base_qss
from .pages.base_page import BasePage
from .pages.debug_page import DebugPage
from .pages.home_page import HomePage
from .pages.search_page import SearchPage
from .pages.settings_page import SettingsPage
from .pages.workspace_page import WorkspacePage

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level window with menu and page stack."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._stack = QStackedWidget()
        self._pages: Dict[str, BasePage] = {}
        self._workspace_page: WorkspacePage | None = None

        self._build_pages()
        self._build_menu()

        self.setWindowTitle(config.app_title)
        icon_path = app_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(config.window_min_width, config.window_min_height)
        self.setCentralWidget(self._stack)
        self.setStyleSheet(load_base_qss())
        self._apply_initial_geometry()
        self.show_page("home")

    def _apply_initial_geometry(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1120, 760)
            return

        available = screen.availableGeometry()
        width = min(1200, max(1024, available.width() - 80))
        height = min(800, max(700, available.height() - 100))
        self.resize(width, height)

    def _build_pages(self) -> None:
        self._add_page(HomePage(self.show_page))
        self._workspace_page = WorkspacePage()
        self._add_page(self._workspace_page)
        self._add_page(SearchPage())
        self._add_page(SettingsPage())
        self._add_page(DebugPage())

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件")
        self._add_action(file_menu, "新建工程", self._handle_new_project)
        self._add_action(file_menu, "打开工程", self._handle_open_project)
        self._add_action(file_menu, "保存工程", self._handle_save_project)

        view_menu = menu_bar.addMenu("窗口")
        for page_id, label in (
            ("home", "主页"),
            ("workspace", "工作区"),
            ("search", "搜索"),
            ("settings", "设置"),
            ("debug", "DEBUG"),
        ):
            action = QAction(label, self)
            action.triggered.connect(partial(self.show_page, page_id))
            view_menu.addAction(action)

        view_menu.addSeparator()
        self._add_action(view_menu, "AI助手", self._toggle_agent_chat)
        self._add_action(view_menu, "切换AI面板 (Ctrl+Shift+A)", self._toggle_agent_chat)

        about_menu = menu_bar.addMenu("关于")
        self._add_action(about_menu, "版本信息", self._show_about_dialog)

    def _add_action(self, menu, label: str, callback) -> QAction:
        action = QAction(label, self)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _show_about_dialog(self) -> None:
        QMessageBox.information(self, "版本信息", "ModTools 5.4")

    def _add_page(self, page: BasePage) -> None:
        if page.page_id in self._pages:
            raise ValueError(f"Page id '{page.page_id}' already registered")
        self._pages[page.page_id] = page
        self._stack.addWidget(page)

    def show_page(self, page_id: str) -> None:
        page = self._pages.get(page_id)
        if page is None:
            LOGGER.warning("Requested page '%s' not found", page_id)
            return
        self._stack.setCurrentWidget(page)
        page.on_activate()
        self.statusBar().showMessage(f"当前页面: {page.display_name or page_id}", 1600)

    def _toggle_agent_chat(self) -> None:
        if self._workspace_page is not None:
            self._workspace_page.toggle_agent_chat_panel()

    def _handle_new_project(self) -> None:
        if self._workspace_page is None:
            return
        project_name, accepted = QInputDialog.getText(self, "新建工程", "工程名称：", text="未命名工程")
        if not accepted:
            return
        self._workspace_page.create_new_project(project_name)
        self.show_page("workspace")
        self.statusBar().showMessage("已创建新工程（未保存）", 2500)

    def _handle_open_project(self) -> None:
        if self._workspace_page is None:
            return

        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "打开工程",
            "",
            f"CIV Project (*{CIV_FILE_EXTENSION});;All Files (*)",
        )
        if not selected_file:
            return

        try:
            self._workspace_page.load_project(Path(selected_file))
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", str(exc))
            return

        self.show_page("workspace")
        self.statusBar().showMessage(f"已打开工程: {Path(selected_file).name}", 3000)

    def _handle_save_project(self) -> None:
        if self._workspace_page is None:
            return

        target = self._workspace_page.project_file_path()
        if target is None:
            default_name = f"{self._workspace_page.project_name()}{CIV_FILE_EXTENSION}"
            selected_file, _ = QFileDialog.getSaveFileName(
                self,
                "保存工程",
                default_name,
                f"CIV Project (*{CIV_FILE_EXTENSION});;All Files (*)",
            )
            if not selected_file:
                return
            target = Path(selected_file)

        try:
            saved_path = self._workspace_page.save_project(target)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return

        self.statusBar().showMessage(f"已保存工程: {saved_path.name}", 3000)
