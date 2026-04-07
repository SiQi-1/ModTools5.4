"""Shared UI asset helpers."""
from __future__ import annotations

from pathlib import Path

from ..app.config import PACKAGE_ROOT


def _resources_dir() -> Path:
    return PACKAGE_ROOT / "resources"


def _images_dir() -> Path:
    return _resources_dir() / "images"


def app_icon_path() -> Path:
    """Return the absolute path to the app icon image."""
    return _images_dir() / "app_icon_civ6.png"


def home_cover_path() -> Path:
    """Return the absolute path to the home cover image."""
    return _images_dir() / "home_cover_civ6.png"


def home_hero_bg_path() -> Path:
    """Return the absolute path to the home hero background image."""
    return _images_dir() / "home_hero_bg_civ6.png"


def app_cover_path() -> Path:
    """Backward-compatible app cover path."""
    cover = home_cover_path()
    if cover.exists():
        return cover
    return _resources_dir() / "app_cover.png"
