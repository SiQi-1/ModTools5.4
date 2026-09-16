"""Pure .CIV envelope and workspace schema helpers."""
from __future__ import annotations

from typing import Any

CIV_FILE_EXTENSION = ".CIV"
CIV_SCHEMA_VERSION = "0.1.0"

CIV_SECTION_ORDER = [
    "基础信息", "文明", "领袖", "区域", "建筑", "单位", "单位晋升", "改良设施",
    "总督", "伟人", "政策卡", "项目", "信仰", "议程", "美术", "文本", "修改器",
]
CIV_DIRECT_WORKSPACE_SECTIONS = {"基础信息", "美术", "文本", "修改器"}
CIV_GROUP_SECTIONS = [name for name in CIV_SECTION_ORDER if name not in CIV_DIRECT_WORKSPACE_SECTIONS]


def normalize_workspace(workspace: Any) -> dict[str, object]:
    """Normalize a workspace to the current top-level section shape."""
    if not isinstance(workspace, dict):
        raise ValueError("工程文件缺少 workspace 节点")
    normalized: dict[str, object] = {}
    for section in CIV_SECTION_ORDER:
        value = workspace.get(section)
        if section in CIV_DIRECT_WORKSPACE_SECTIONS:
            normalized[section] = value if isinstance(value, dict) else {}
        else:
            normalized[section] = value if isinstance(value, list) else []
    return normalized


def parse_project_payload(payload: Any) -> tuple[str, dict[str, object]]:
    """Validate the project envelope and return its name plus normalized data."""
    if not isinstance(payload, dict):
        raise ValueError("工程文件格式错误，应为 JSON 对象")
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("工程文件缺少 meta 节点")
    project_name = str(meta.get("project_name") or "未命名工程").strip() or "未命名工程"
    return project_name, normalize_workspace(payload.get("workspace"))


def project_envelope(project_name: str, workspace: dict[str, object]) -> dict[str, object]:
    """Build the stable JSON envelope used by CivProject."""
    return {
        "meta": {
            "format": "CIV_PROJECT",
            "schema_version": CIV_SCHEMA_VERSION,
            "project_name": project_name,
        },
        "workspace": workspace,
    }
