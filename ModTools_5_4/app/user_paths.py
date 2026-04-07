"""User-writable paths for ModTools 5.4.

Goal:
- When bundled as an .exe, packaged files are read-only or non-persistent.
- Settings/logs should live in a user-writable directory.
- Support a portable mode (store settings next to the exe) when desired.
"""

from __future__ import annotations

from pathlib import Path
import os
import sys


APP_DIR_NAME = "ModTools5.4"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def exe_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Return the default user-writable data directory."""
    local_app_data = os.getenv("LOCALAPPDATA")
    app_data = os.getenv("APPDATA")

    base = None
    if local_app_data:
        base = Path(local_app_data)
    elif app_data:
        base = Path(app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    return base / APP_DIR_NAME


def use_portable_mode() -> bool:
    """Portable mode stores settings/logs next to the executable.

    Enabled when:
    - MODTOOLS54_PORTABLE=1, or
    - a settings.json exists next to the exe.
    """
    if os.getenv("MODTOOLS54_PORTABLE", "0") == "1":
        return True
    return (exe_dir() / "settings.json").exists()


def settings_file_path() -> Path:
    if use_portable_mode():
        return exe_dir() / "settings.json"
    return user_data_dir() / "settings.json"


def log_dir_path() -> Path:
    if use_portable_mode():
        return exe_dir() / "logs"
    return user_data_dir() / "logs"
