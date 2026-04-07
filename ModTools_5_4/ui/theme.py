"""Theme helpers for ModTools 5.4 UI."""
from __future__ import annotations

from pathlib import Path

from ..app.config import PACKAGE_ROOT


def load_base_qss() -> str:
    """Load base stylesheet text."""
    qss_path = PACKAGE_ROOT / "resources" / "styles" / "base.qss"
    if not qss_path.exists():
        return ""
    qss = qss_path.read_text(encoding="utf-8")
    panel_bg = (PACKAGE_ROOT / "resources" / "images" / "panel_bg_civ6.png").as_uri()
    button_tex = (PACKAGE_ROOT / "resources" / "images" / "button_texture_civ6.png").as_uri()
    spin_up = (PACKAGE_ROOT / "resources" / "icons" / "spin_up.png").as_posix()
    spin_down = (PACKAGE_ROOT / "resources" / "icons" / "spin_down.png").as_posix()
    qss = qss.replace("__PANEL_BG__", panel_bg)
    qss = qss.replace("__BUTTON_TEX__", button_tex)
    qss = qss.replace("__SPIN_UP__", spin_up)
    qss = qss.replace("__SPIN_DOWN__", spin_down)
    return qss
