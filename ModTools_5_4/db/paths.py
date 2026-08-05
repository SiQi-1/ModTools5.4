"""Path utilities for Civ VI database defaults."""
from __future__ import annotations

from pathlib import Path
import os
import sys

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PACKAGE_ROOT / "data"

CACHE_DIR = Path.home() / "AppData" / "Local" / "Firaxis Games" / "Sid Meier's Civilization VI" / "Cache"
DEFAULT_GAME_DB = CACHE_DIR / "DebugGameplay.sqlite"
DEFAULT_TEXT_SOURCE_DB = CACHE_DIR / "DebugLocalization.sqlite"
DEFAULT_MODS_DB = Path.home() / "AppData" / "Local" / "Firaxis Games" / "Sid Meier's Civilization VI" / "Mods.sqlite"


def _resolve_data_path(filename: str) -> Path:
    """取数据文件路径：优先 exe 同目录 data/ 下的便携覆盖，否则取内嵌版本。

    打包版用户可以修改 exe 同级 data/ 下的 JSON/XML 文件（modifier 注释模板等），
    程序会自动读取覆盖版而非 exe 内嵌的默认版。
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        portable = Path(sys.executable).resolve().parent / "data" / filename
        if portable.exists():
            return portable
    return DATA_DIR / filename


def expand_user_path(path: str) -> Path:
    """Expand environment and user tokens in a string path."""
    expanded = os.path.expandvars(os.path.expanduser(path))
    return Path(expanded)
