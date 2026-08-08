"""Application bootstrap entry points."""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .config import AppConfig, load_config
from .logging_setup import configure_logging
from .user_paths import log_dir_path
from ..ui.assets import app_icon_path
from ..ui.main_window import MainWindow

_CRASH_BOX_SHOWN = False


class ModToolsApplication(QApplication):
    """Thin wrapper over QApplication for future service wiring."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        super().__init__(sys.argv)


def _crash_log_path() -> Path:
    log_dir = log_dir_path()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path("crash.log")
    return log_dir / "crash.log"


def _write_crash_log(exc_type, exc_value, exc_tb) -> None:
    lines = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        with open(_crash_log_path(), "a", encoding="utf-8") as handle:
            handle.write(f"==== {datetime.now().isoformat(timespec='seconds')} ====\n{lines}\n")
    except OSError:
        pass
    return lines


def _install_crash_handler() -> None:
    """兜底：未处理异常写入 crash.log，并尽可能弹窗提示。

    打包版无控制台（--noconsole），若不加兜底，任何启动期异常都会表现为
    “双击后毫无反应”。写入 exe 旁/用户数据目录的 crash.log 便于排查。
    """
    global _CRASH_BOX_SHOWN

    def _handle(exc_type, exc_value, exc_tb) -> None:
        global _CRASH_BOX_SHOWN
        lines = _write_crash_log(exc_type, exc_value, exc_tb)
        if _CRASH_BOX_SHOWN:
            return
        _CRASH_BOX_SHOWN = True
        try:
            from PyQt6.QtWidgets import QMessageBox

            if QApplication.instance() is not None:
                QMessageBox.critical(
                    None,
                    "ModTools 崩溃",
                    "程序遇到未处理异常，已写入日志文件：\n"
                    f"{_crash_log_path()}\n\n{lines[-1500:]}",
                )
        except Exception:
            pass
        sys.exit(1)

    sys.excepthook = _handle


def build_application(config: AppConfig | None = None) -> ModToolsApplication:
    """Create application with logging/config prepared.

    若当前进程已存在 QApplication 实例（如测试环境或多次调用），复用之，
    避免重复构造 QApplication 触发 Qt 硬崩溃。
    """
    _install_crash_handler()
    active_config = config or load_config()
    configure_logging(active_config.log_dir, active_config.debug)
    existing = QApplication.instance()
    if existing is not None:
        app = existing
        app.config = active_config  # type: ignore[attr-defined]
    else:
        app = ModToolsApplication(active_config)
    app.setApplicationName(active_config.app_title)
    icon_path = app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    return app


def launch(config: AppConfig | None = None) -> int:
    """Launch the ModTools 5.4 GUI."""
    try:
        app = build_application(config)
        window = MainWindow(app.config)
        window.show()
        return app.exec()
    except SystemExit:
        raise
    except Exception:
        _install_crash_handler()
        _handle = sys.excepthook
        exc_type, exc_value, exc_tb = sys.exc_info()
        if _handle is not None and exc_type is not None:
            _handle(exc_type, exc_value, exc_tb)
        return 1
