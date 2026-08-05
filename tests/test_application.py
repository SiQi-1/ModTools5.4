"""Regression tests for app bootstrap (application.py crash handler)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app import application  # noqa: E402


class ApplicationBootstrapTestCase(unittest.TestCase):
    def test_mod_tools_application_class_exists(self) -> None:
        """build_application 依赖的 ModToolsApplication 类必须存在（曾因重写丢失）。"""
        cls = getattr(application, "ModToolsApplication", None)
        self.assertIsNotNone(cls)
        self.assertTrue(issubclass(cls, QApplication))

    def test_build_application_returns_app(self) -> None:
        app = application.build_application()
        self.assertIsInstance(app, application.ModToolsApplication)
        self.assertEqual(app.applicationName(), "ModTools 5.4")

    def test_crash_handler_writes_log_and_does_not_crash(self) -> None:
        """崩溃兜底本身不能抛异常（曾因闭包内 global 缺失触发 UnboundLocalError）。"""
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "crash.log"

            original_log_path = application._crash_log_path
            original_exit = application.sys.exit
            original_flag = application._CRASH_BOX_SHOWN
            application._crash_log_path = lambda: log_path
            application.sys.exit = lambda code: None  # 测试中不真正退出
            application._CRASH_BOX_SHOWN = False
            try:
                application._install_crash_handler()
                handler = application.sys.excepthook
                self.assertTrue(callable(handler))

                try:
                    raise ValueError("测试崩溃")
                except ValueError:
                    exc_type, exc_value, exc_tb = __import__("sys").exc_info()
                    handler(exc_type, exc_value, exc_tb)

                self.assertTrue(log_path.exists(), "crash.log 应被写入")
                content = log_path.read_text(encoding="utf-8")
                self.assertIn("ValueError", content)
                self.assertIn("测试崩溃", content)

                # 第二次调用应直接返回（防重复弹窗/重复写入由 flag 控制）
                handler(exc_type, exc_value, exc_tb)
            finally:
                application._crash_log_path = original_log_path
                application.sys.exit = original_exit
                application._CRASH_BOX_SHOWN = original_flag


if __name__ == "__main__":
    unittest.main()
