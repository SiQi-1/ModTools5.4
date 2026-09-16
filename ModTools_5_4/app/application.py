"""Application bootstrap entry points."""
from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .config import AppConfig, load_config
from .logging_setup import configure_logging
from .user_paths import log_dir_path
from ..ui.assets import app_icon_path
from ..ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)
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


def find_initial_project_path() -> Path | None:
    """从命令行参数中找 .CIV 工程路径（文件关联双击打开用）。"""
    for raw in sys.argv[1:]:
        text = str(raw or "").strip().strip('"')
        if not text:
            continue
        candidate = Path(text)
        if candidate.suffix.upper() == ".CIV" and candidate.exists():
            return candidate
    return None


def _parse_cli_ai_args(
    argv: list[str],
) -> tuple[list[str], int | None, str | None, list[str], bool]:
    """解析 AI 控制相关 CLI 参数，返回（剩余 argv, ai_port, ai_token, ai_exec 列表, headless）。"""
    ai_port: int | None = None
    ai_token: str | None = None
    ai_exec: list[str] = []
    headless = False
    cleaned: list[str] = []

    def _next_value(index: int, inline: str | None, name: str) -> tuple[object, int]:
        if inline is not None:
            return inline, index
        if index + 1 < len(argv):
            return argv[index + 1], index + 1
        raise ValueError(f"{name} 缺少参数值")

    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--headless":
            headless = True
        elif arg == "--ai-port" or arg.startswith("--ai-port="):
            value, index = _next_value(index, arg.split("=", 1)[1] if "=" in arg else None, "--ai-port")
            ai_port = int(value)
        elif arg == "--ai-token" or arg.startswith("--ai-token="):
            value, index = _next_value(index, arg.split("=", 1)[1] if "=" in arg else None, "--ai-token")
            ai_token = str(value)
        elif arg == "--ai-exec" or arg.startswith("--ai-exec="):
            value, index = _next_value(index, arg.split("=", 1)[1] if "=" in arg else None, "--ai-exec")
            ai_exec.append(str(value))
        else:
            cleaned.append(arg)
        index += 1
    return cleaned, ai_port, ai_token, ai_exec, headless


def _ai_exec_result_path() -> Path:
    return log_dir_path() / "ai_exec_result.json"


def launch(config: AppConfig | None = None) -> int:
    """Launch the ModTools 5.4 GUI（含 AI 控制接口：--ai-port / --ai-token / --ai-exec / --headless）。"""
    try:
        cleaned_argv, ai_port, ai_token, ai_exec_raw, headless = _parse_cli_ai_args(sys.argv[1:])
        if cleaned_argv != sys.argv[1:]:
            sys.argv = [sys.argv[0]] + cleaned_argv
        if headless:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        app = build_application(config)
        window = MainWindow(app.config)
        window.show()
        initial_project = find_initial_project_path()
        if initial_project is not None:
            window.open_project_file(initial_project)

        if ai_port is not None or ai_exec_raw:
            from ..ai.control_server import (
                ControlContext,
                ControlServer,
                emit_exec_results,
                parse_ai_exec_requests,
                run_ai_requests,
            )

            workspace = window.workspace_page()
            context = ControlContext(window, workspace)

            if ai_exec_raw:
                try:
                    requests = parse_ai_exec_requests(ai_exec_raw)
                except ValueError as exc:
                    emit_exec_results(
                        [{"action": "", "response": {"ok": False, "error": str(exc)}}],
                        _ai_exec_result_path(),
                    )
                    return 2

                def _run_exec_and_exit() -> None:
                    results = run_ai_requests(context, requests)
                    emit_exec_results(results, _ai_exec_result_path())
                    all_ok = all(bool(item["response"].get("ok")) for item in results)
                    app.exit(0 if all_ok else 1)

                QTimer.singleShot(0, _run_exec_and_exit)
            elif ai_port is not None:
                server = ControlServer(context, port=ai_port, token=ai_token)
                server.start()
                endpoint = f"http://127.0.0.1:{server.port}/api"
                LOGGER.info("[AI控制] HTTP 服务已启动：%s", endpoint)
                if sys.stdout is not None:
                    try:
                        sys.stdout.write(f"AI control server: {endpoint}\n")
                        sys.stdout.flush()
                    except OSError:
                        pass
                window.statusBar().showMessage(f"AI 控制服务: {endpoint}", 8000)
                window._ai_control_server = server  # type: ignore[attr-defined] - 保持引用防止回收

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
