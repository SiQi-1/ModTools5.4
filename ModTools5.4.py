"""Launcher script for ModTools 5.4.

首次在新设备上运行时，当前 Python 可能缺少 PyQt6（Windows 的 .py 默认用 py.exe
的系统 Python 打开），此时：

1. 仓库已有 .venv 且依赖可用 → 自动切换到 .venv 解释器（不会静默失败）；
2. 仓库没有 .venv → 交互场景弹窗询问是否自动初始化（创建 .venv 并安装
   PyQt6/Pillow，需要联网）；非交互场景（AI/CI、输出被重定向）只打印指引并
   以退出码 1 结束，不会挂起等待输入；
3. 初始化成功后自动用 .venv 启动；失败则给出下一步（docs/user/install.md）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MESSAGE_TITLE = "ModTools 5.4"
VENV_RELATIVE_PYTHON = Path(".venv") / "Scripts" / "python.exe"
SETUP_RELATIVE_SCRIPT = Path("tools") / "setup_env.py"
DOCS_HINT = "docs/user/install.md"
CREATE_NEW_CONSOLE = 0x00000010
MB_YESNO = 0x00000004
MB_OK = 0x00000000
MB_ICONQUESTION = 0x00000020
MB_ICONERROR = 0x00000010
MB_SETFOREGROUND = 0x00010000
IDYES = 6


def project_root() -> Path:
    return Path(__file__).resolve().parent


def venv_python(root: Path) -> Path:
    return root / VENV_RELATIVE_PYTHON


def pyqt_available() -> bool:
    try:
        import PyQt6  # noqa: F401
    except Exception:
        return False
    return True


def is_interactive() -> bool:
    """pythonw 启动时 stdout 为 None，仍是人在点击；AI/CI 的输出是管道，不算交互。"""
    stream = sys.stdout
    if stream is None:
        return True
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def notify(text: str, *, ask: bool = False) -> bool:
    """Windows 弹窗；非 Windows 退回控制台输入。返回是否选择「是」。"""
    if os.name == "nt":
        try:
            import ctypes

            flags = MB_SETFOREGROUND
            flags |= (MB_YESNO | MB_ICONQUESTION) if ask else (MB_OK | MB_ICONERROR)
            result = ctypes.windll.user32.MessageBoxW(None, text, MESSAGE_TITLE, flags)
            return result == IDYES
        except Exception:
            pass
    print(text, flush=True)
    if not ask:
        return False
    try:
        return input("是否继续？[y/N] ").strip().lower() in {"y", "yes", "是"}
    except EOFError:
        return False


def run_setup(root: Path) -> bool:
    """运行 tools/setup_env.py；非交互场景使用新控制台让用户看到进度。"""
    script = root / SETUP_RELATIVE_SCRIPT
    if not script.is_file():
        return False
    command = [sys.executable, str(script)]
    creationflags = 0
    if os.name == "nt" and not is_interactive():
        creationflags = CREATE_NEW_CONSOLE
    try:
        result = subprocess.run(command, cwd=str(root), creationflags=creationflags)
    except OSError:
        return False
    return result.returncode == 0 and venv_python(root).is_file()


def _same_executable(candidate: Path) -> bool:
    try:
        return Path(sys.executable).resolve() == candidate.resolve()
    except OSError:
        return False


def ensure_environment(
    root: Path | None = None,
    argv: list[str] | None = None,
    *,
    pyqt_ok: bool | None = None,
    interactive: bool | None = None,
    confirm=notify,
    setup_runner=run_setup,
    execv=os.execv,
) -> None:
    """确保 GUI 依赖可用；必要时切换解释器或引导初始化。不返回时说明要退出。"""
    if os.name != "nt" or getattr(sys, "frozen", False):
        return
    root = root or project_root()
    argv = list(sys.argv[1:] if argv is None else argv)
    has_pyqt = pyqt_available() if pyqt_ok is None else pyqt_ok
    if has_pyqt:
        return
    candidate = venv_python(root)
    if candidate.is_file() and not _same_executable(candidate):
        execv(str(candidate), [str(candidate), str(Path(__file__).resolve()), *argv])
        return

    if candidate.is_file():
        problem = (
            "检测到项目 .venv，但其中缺少 PyQt6/Pillow，编辑器无法启动。\n\n"
            "是否现在重新安装运行依赖？（需要联网，约几分钟）"
        )
    else:
        problem = (
            "ModTools 5.4 尚未初始化运行环境（缺少 .venv 与 PyQt6/Pillow）。\n\n"
            "是否现在自动初始化？将创建 .venv 并安装 PyQt6/Pillow，需要联网，约几分钟。\n"
            "选择「否」可稍后按 " + DOCS_HINT + " 手动完成。"
        )
    if interactive is None:
        interactive = is_interactive()
    if not interactive:
        print(problem + "\n\n非交互环境不会自动安装；请先运行：python tools/setup_env.py", file=sys.stderr)
        raise SystemExit(1)
    if not confirm(problem, ask=True):
        raise SystemExit(1)
    if not setup_runner(root):
        notify(
            "初始化未完成：可能是网络不可用、Python 版本过低或依赖安装失败。\n\n"
            "请按 " + DOCS_HINT + " 手动初始化，或运行：python tools/setup_env.py",
            ask=False,
        )
        raise SystemExit(1)
    target = venv_python(root)
    execv(str(target), [str(target), str(Path(__file__).resolve()), *argv])


if __name__ == "__main__":
    ensure_environment()
    from ModTools_5_4.app.application import launch

    raise SystemExit(launch())
