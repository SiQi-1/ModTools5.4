"""preview：无头运行 GUI 生成引擎，输出 .CIV → 生成文件清单（验证闭环）。

原理：与 tests/test_sql_previews.py 相同——QT_QPA_PLATFORM=offscreen 下实例化
WorkspacePage、加载工程、调用 `_project_root_manifest()` 得到全部将生成的文件内容，
然后**写入 --out 目录（默认 modgen_work/preview_*）**，绝不写入 .civ6proj 目录。

- 需要 PyQt6 + ModTools 源码（GUI 同环境）；缺失时给出明确报错；
- 生成"工程总览"所见即所得的 SQL/XML/Icons/ArtDef/XLP/Text 等文件；
- `--section` + `--format`：只预览单个分类的 SQL/XML 文本（stdout 输出）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


class PreviewError(RuntimeError):
    pass


# 持有 QApplication 引用，防止被垃圾回收（Qt 对象生命周期）
_APP_HOLDER: list[Any] = []


def _import_gui():
    """延迟导入 GUI 模块（preview 是唯一依赖 PyQt 的 modgen 命令）。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication  # noqa: F401

        from ModTools_5_4.app.config import load_config
        from ModTools_5_4.app.logging_setup import configure_logging
        from ModTools_5_4.ui.pages.workspace_page import WorkspacePage
    except ImportError as exc:
        raise PreviewError(
            f"preview 需要 PyQt6 + ModTools 源码环境（当前不可用：{exc}）。"
            "其余 modgen 命令不受影响。"
        ) from exc
    return load_config, configure_logging, WorkspacePage


def _build_page(civ_path: Path) -> Any:
    load_config, configure_logging, WorkspacePage = _import_gui()
    from PyQt6.QtWidgets import QApplication

    config = load_config()
    configure_logging(config.log_dir, config.debug)
    app = QApplication.instance() or QApplication([])
    _APP_HOLDER.append(app)
    page = WorkspacePage()
    page.load_project(civ_path)
    return page


def build_preview_files(civ_path: Path) -> dict[str, str | bytes]:
    """构建 .CIV → 生成文件内容映射（{相对路径: 内容}），不落盘。"""
    result = build_preview_manifest(civ_path)
    if result.get("extension_errors"):
        raise PreviewError("\n".join(e["message"] for e in result["extension_errors"]))
    return result["files"]


def build_preview_manifest(civ_path: Path, *, page=None) -> dict[str, Any]:
    """构建完整清单：files/folders/can_generate/civ6proj_path/readonly_custom_paths。

    readonly_custom_paths = 工程目录里自定义（外部）文件的路径集合——它们是
    "原样透传、不参与生成"的文件，供 check-conflicts 区分生成内容与自定义内容。
    """
    owned_page = page is None
    page = page if page is not None else _build_page(civ_path)
    files, folders, can_generate, civ6proj_path = page._project_root_manifest()
    if not isinstance(files, dict):
        raise PreviewError("生成总览未返回文件清单")
    extensions = getattr(page, "_extension_plan", {})
    basic = page._load_basic_info_payload_from_project() or {}
    action_info = extensions if page._project.extensions else basic.get("file_info", {})
    result = {
        "extension_errors": extensions.get("errors", []),
        "extension_paths": sorted(extensions.get("files", {})),
        "actions": {key: action_info.get(key, []) for key in ("front_end_actions", "in_game_actions")},
        "files": {str(rel).replace("\\", "/"): content if isinstance(content, bytes) else str(content) for rel, content in files.items()},
        "folders": sorted(str(folder).replace("\\", "/") for folder in folders),
        "can_generate": bool(can_generate),
        "civ6proj_path": str(civ6proj_path) if civ6proj_path else "",
        "readonly_custom_paths": sorted(
            str(path).replace("\\", "/") for path in page._readonly_custom_paths
        ),
    }
    if owned_page:
        page.close()
        page.deleteLater()
    return result


def preview_section(civ_path: Path, section: str, fmt: str = "sql") -> str:
    """预览单个内容分类 / 修改器 / UI图标的输出文本（stdout 直接打印）。

    「UI图标」段不产出 SQL，无论 ``--format`` 都返回 Icons.xml（与美术页同一实现）。
    """
    page = _build_page(civ_path)
    fmt = str(fmt or "sql").lower()
    if fmt not in ("sql", "xml"):
        raise PreviewError("--format 只支持 sql / xml")
    if section == "修改器":
        if fmt == "xml":
            return page.build_modifier_xml_preview()
        return page.build_modifier_sql_preview()
    from ModTools_5_4.project.civ_project import CIV_GROUP_SECTIONS  # noqa: PLC0415

    if section not in CIV_GROUP_SECTIONS:
        raise PreviewError(
            f"未知分类：{section}。可用内容分类：{'/'.join(CIV_GROUP_SECTIONS)}；修改器用「修改器」。"
        )
    result = page._build_group_data_preview_text(section, fmt)
    if isinstance(result, dict):
        return "\n\n".join(f"===== {name} =====\n{content}" for name, content in result.items())
    return str(result)


def write_preview_files(files: dict[str, str | bytes], out_dir: Path) -> tuple[int, int]:
    """把预览文件写入 out_dir（相对路径映射），返回 (文件数, 总字节)。"""
    total_bytes = 0
    for rel, content in files.items():
        target = out_dir / Path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
            total_bytes += len(content)
        else:
            target.write_text(content, encoding="utf-8")
            total_bytes += len(content.encode("utf-8"))
    return len(files), total_bytes


def safe_out_dir_name(project_name: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", str(project_name or "project").strip())
    text = re.sub(r"\s+", "_", text)
    return text or "project"
