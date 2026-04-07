"""Runtime configuration for ModTools 5.4."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from .user_paths import log_dir_path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = log_dir_path()


@dataclass(frozen=True)
class AppConfig:
    """Immutable application runtime options."""

    app_title: str
    debug: bool
    log_dir: Path
    window_min_width: int
    window_min_height: int


def load_config() -> AppConfig:
    """Build configuration from environment context."""
    debug_enabled = os.getenv("MODTOOLS54_DEBUG", "0") == "1"
    return AppConfig(
        app_title="ModTools 5.4",
        debug=debug_enabled,
        log_dir=DEFAULT_LOG_DIR,
        window_min_width=980,
        window_min_height=680,
    )
