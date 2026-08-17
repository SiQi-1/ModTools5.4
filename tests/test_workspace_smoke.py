"""Headless GUI smoke test.

Runs the real application with QT_QPA_PLATFORM=offscreen (no display needed):
- application + main window boot
- new project creation, save / load roundtrip
- core SQL preview builders run without crashing
- section tree rebuild
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.main_window import MainWindow  # noqa: E402


class WorkspaceSmokeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.window = MainWindow(config)
        cls.window.show()
        cls.page = cls.window._workspace_page

    def test_main_window_has_three_pages(self) -> None:
        self.assertEqual(
            set(self.window._pages.keys()),
            {"home", "workspace", "settings"},
        )

    def test_tools_window_opens_as_independent_window(self) -> None:
        self.window._tools_window = None  # 重置单例
        self.window._open_tools_window()
        self.assertIsNotNone(self.window._tools_window)
        tools = self.window._tools_window
        self.assertTrue(tools.isVisible() or not tools.isHidden())
        self.assertEqual(tools.windowTitle(), "ModTools 小工具")
        # 关闭 = 隐藏（保留状态），不销毁
        tools.close()
        self.assertFalse(tools.isVisible())
        self.assertIs(self.window._tools_window, tools, "关闭后单例应保留（隐藏）")
        # 再次打开恢复显示
        self.window._open_tools_window()
        self.assertTrue(tools.isVisible())

    def test_create_project_and_rebuild_tree(self) -> None:
        self.page.create_new_project("冒烟测试")
        self.assertEqual(self.page.project_name(), "冒烟测试")
        self.page._rebuild_tree()  # must not raise

    def test_project_save_load_roundtrip(self) -> None:
        self.page.create_new_project("往返测试")
        self.page.sections_add_marker = None
        with tempfile.TemporaryDirectory() as tmp:
            path = self.page.save_project(Path(tmp) / "smoke.CIV")
            self.assertTrue(path.exists())
            self.page.load_project(path)
            self.assertEqual(self.page.project_name(), "往返测试")

    def test_core_sql_preview_builders_run_on_empty_project(self) -> None:
        self.page.create_new_project("空工程")
        checks = {
            "civilization": lambda: self.page._build_civilization_sql_pair()[0],
            "leader": lambda: self.page._build_leader_sql_pair()[0],
            "modifier": lambda: self.page.build_modifier_sql_preview(),
            "text": lambda: self.page._build_text_workspace_preview("sql"),
        }
        for label, builder in checks.items():
            with self.subTest(label=label):
                result = builder()
                self.assertIsNotNone(result, label)
                self.assertTrue(str(result).strip(), label)

    def test_promotion_bundle_returns_none_when_empty(self) -> None:
        self.page.create_new_project("空工程")
        self.assertIsNone(self.page._build_promotion_tree_sql_bundle())


if __name__ == "__main__":
    unittest.main()
