"""Auto-generate UI screenshots for README (no manual screenshots needed).

Usage:
    python tools/make_screenshots.py

Renders the real UI (a window will flash briefly), loads a small demo
project, navigates each page and saves PNGs to ModTools_5_4/docs/screenshots/.

For headless environments you can force offscreen rendering:
    QT_QPA_PLATFORM=offscreen python tools/make_screenshots.py
(Note: offscreen text is not antialiased, so prefer the default platform.)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "windows"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ModTools_5_4.app.application import build_application  # noqa: E402
from ModTools_5_4.ui.main_window import MainWindow  # noqa: E402
from ModTools_5_4.project.civ_project import save_civ_project  # noqa: E402
from tests.sample_project import build_sample_project  # noqa: E402

OUT_DIR = REPO_ROOT / "ModTools_5_4" / "docs" / "screenshots"
WINDOW_SIZE = (1280, 820)


def _wait(app, ms: int = 120) -> None:
    import time
    time.sleep(ms / 1000.0)
    app.processEvents()
    app.processEvents()


def _select_leaf(page, section: str) -> None:
    """Select a direct-workspace section node (基础信息/美术/文本/修改器)."""
    from PyQt6.QtCore import Qt

    root = page._tree.topLevelItem(0)
    if root is None:
        return
    for i in range(root.childCount()):
        item = root.child(i)
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict) and payload.get("kind") == "section_leaf" and payload.get("section") == section:
            page._tree.setCurrentItem(item)
            return


def main() -> int:
    import hashlib
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice

    app = build_application()
    window = MainWindow(app.config)
    window.resize(*WINDOW_SIZE)
    window.show()
    _wait(app)

    out = OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    seen_hashes: list[str] = []

    def _shoot(name: str, widget) -> None:
        path = out / name
        pix = widget.grab()
        if not pix.save(str(path)):
            raise RuntimeError(f"failed to save {path}")
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        buf.close()
        digest = hashlib.md5(bytes(ba)).hexdigest()[:10]
        if digest in seen_hashes:
            print(f"WARNING: {name} identical to an earlier shot ({digest})")
        seen_hashes.append(digest)
        size = path.stat().st_size
        print(f"saved {path.relative_to(REPO_ROOT)} ({size // 1024} KB) [{digest}]")

    with tempfile.TemporaryDirectory() as tmp:
        demo_path = Path(tmp) / "demo.CIV"
        save_civ_project(demo_path, build_sample_project())

        page = window._workspace_page
        page.load_project(demo_path)
        _wait(app, 300)

        window.show_page("home")
        _wait(app)
        _shoot("01_home.png", window._pages["home"])

        window.show_page("workspace")
        _wait(app)
        _shoot("02_workspace_overview.png", page._workspace_stack.currentWidget())

        page._select_section_item("文明", 0)
        _wait(app, 250)
        _shoot("03_civilization_editor.png", page._workspace_stack.currentWidget())

        page._select_section_item("领袖", 0)
        _wait(app, 250)
        _shoot("04_leader_editor.png", page._workspace_stack.currentWidget())

        page._select_section_item("单位晋升", 0)
        _wait(app, 250)
        _shoot("05_promotion_tree_editor.png", page._workspace_stack.currentWidget())

        page._select_section_item("议程", 0)
        _wait(app, 250)
        _shoot("06_agenda_editor.png", page._workspace_stack.currentWidget())

        page._select_section_item("伟人", 0)
        _wait(app, 250)
        _shoot("07_great_people_editor.png", page._workspace_stack.currentWidget())

        _select_leaf(page, "基础信息")
        _wait(app)
        _shoot("08_basic_info.png", page._workspace_stack.currentWidget())

        _select_leaf(page, "美术")
        _wait(app)
        _shoot("09_art_workspace.png", page._workspace_stack.currentWidget())

        _select_leaf(page, "修改器")
        _wait(app)
        _shoot("10_modifier_workspace.png", page._workspace_stack.currentWidget())

        _select_leaf(page, "文本")
        _wait(app)
        _shoot("11_text_workspace.png", page._workspace_stack.currentWidget())

        window.show_page("search")
        _wait(app)
        _shoot("12_search.png", window._pages["search"])

        window.show_page("settings")
        _wait(app)
        _shoot("13_settings.png", window._pages["settings"])

    print(f"\nDone. {len(seen_hashes)} screenshots -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
