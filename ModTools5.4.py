"""Launcher script for ModTools 5.4."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _relaunch_with_project_venv() -> None:
    """Allow double-clicking this .py even when the associated Python lacks PyQt6.

    Windows associates ``.py`` with ``py.exe`` (the system Python). That interpreter
    has no PyQt6/Pillow, so the app would exit before showing a window. When the
    repository ships a ``.venv`` with the GUI dependencies, re-exec with it instead.
    """
    if os.name != "nt" or getattr(sys, "frozen", False):
        return
    root = Path(__file__).resolve().parent
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        return
    try:
        import PyQt6  # noqa: F401
        return
    except Exception:
        pass
    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except OSError:
        return
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])


if __name__ == "__main__":
    _relaunch_with_project_venv()
    from ModTools_5_4.app.application import launch

    raise SystemExit(launch())
