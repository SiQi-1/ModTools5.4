"""Path utilities for Civ VI database defaults."""
from __future__ import annotations

from pathlib import Path
import os

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PACKAGE_ROOT / "data"

CACHE_DIR = Path.home() / "AppData" / "Local" / "Firaxis Games" / "Sid Meier's Civilization VI" / "Cache"
DEFAULT_GAME_DB = CACHE_DIR / "DebugGameplay.sqlite"
DEFAULT_TEXT_SOURCE_DB = CACHE_DIR / "DebugLocalization.sqlite"
DEFAULT_MODS_DB = Path.home() / "AppData" / "Local" / "Firaxis Games" / "Sid Meier's Civilization VI" / "Mods.sqlite"


def expand_user_path(path: str) -> Path:
    """Expand environment and user tokens in a string path."""
    expanded = os.path.expandvars(os.path.expanduser(path))
    return Path(expanded)
