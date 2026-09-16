"""提取工程级骨架（基础信息/美术/修改器/文本 默认结构）→ schemas/project_scaffold.json。

需要 PyQt 环境（offscreen）：
    python modgen/tools/extract_scaffold.py

用途：`modgen new-project` 在运行时（纯标准库）读取该 JSON 生成工程骨架，
保证骨架结构与 GUI"新建工程"的编辑器默认导出完全一致。
编辑器（基础信息/美术/修改器）结构变化后，重新运行本脚本并提交生成的 JSON。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel  # noqa: E402
from ModTools_5_4.ui.pages.basic_info_workspace import BasicInfoWorkspacePanel  # noqa: E402
from ModTools_5_4.ui.pages.modifier_workspace import ModifierWorkspacePanel  # noqa: E402

OUT_FILE = ROOT / "modgen" / "schemas" / "project_scaffold.json"


def main() -> int:
    config = load_config()
    configure_logging(config.log_dir, config.debug)
    app = QApplication.instance() or QApplication([])

    basic = BasicInfoWorkspacePanel()
    basic._apply_defaults()
    basic_payload = basic.export_project_payload()

    art = ArtWorkspacePanel()
    # ArtWorkspacePanel.export_project_payload() 已自带 format/schema_version/data 包装
    art_payload = art.export_project_payload()

    mod = ModifierWorkspacePanel()
    mod_payload = mod.export_home_data()
    # 清空编辑器初始残留（如空 MODIFIER_ 记录），骨架只保留空结构
    for key in ("owners", "unit_abilities", "modifiers", "requirement_sets", "requirements"):
        mod_payload[key] = []

    scaffold = {
        "基础信息": {
            "format": "MODTOOLS54_BASIC_INFO_WORKSPACE",
            "schema_version": "1.0.0",
            "data": basic_payload,
        },
        "美术": art_payload,
        "修改器": {
            "format": "MODTOOLS54_MODIFIER_WORKSPACE",
            "schema_version": "1.0.0",
            "data": mod_payload,
        },
        "文本": {"preview_settings": {}},
    }

    OUT_FILE.write_text(
        json.dumps(scaffold, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"written: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
