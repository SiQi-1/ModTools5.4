"""CIV project file model (.CIV is JSON in content)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

CIV_FILE_EXTENSION = ".CIV"
CIV_SCHEMA_VERSION = "0.1.0"

CIV_SECTION_ORDER = [
    "基础信息",
    "文明",
    "领袖",
    "区域",
    "建筑",
    "单位",
    "改良设施",
    "总督",
    "伟人",
    "政策卡",
    "项目",
    "信仰",
    "议程",
    "美术",
    "文本",
    "修改器",
]

CIV_DIRECT_WORKSPACE_SECTIONS = {"基础信息", "美术", "文本", "修改器"}
CIV_GROUP_SECTIONS = [name for name in CIV_SECTION_ORDER if name not in CIV_DIRECT_WORKSPACE_SECTIONS]


@dataclass(slots=True)
class CivProject:
    """In-memory representation of a .CIV project file."""

    project_name: str
    sections: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "meta": {
                "format": "CIV_PROJECT",
                "schema_version": CIV_SCHEMA_VERSION,
                "project_name": self.project_name,
            },
            "workspace": self.sections,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "CivProject":
        meta = payload.get("meta") if isinstance(payload, dict) else None
        workspace = payload.get("workspace") if isinstance(payload, dict) else None

        if not isinstance(meta, dict):
            raise ValueError("工程文件缺少 meta 节点")
        if not isinstance(workspace, dict):
            raise ValueError("工程文件缺少 workspace 节点")

        project_name = str(meta.get("project_name") or "未命名工程").strip() or "未命名工程"

        normalized: dict[str, object] = {}
        for section in CIV_SECTION_ORDER:
            if section in CIV_DIRECT_WORKSPACE_SECTIONS:
                value = workspace.get(section, {})
                normalized[section] = value if isinstance(value, dict) else {}
            else:
                value = workspace.get(section, [])
                normalized[section] = value if isinstance(value, list) else []

        return cls(project_name=project_name, sections=normalized)


def create_empty_project(project_name: str = "未命名工程") -> CivProject:
    """Create an empty project with the baseline section structure."""
    normalized_name = project_name.strip() or "未命名工程"
    sections: dict[str, object] = {}
    for section in CIV_SECTION_ORDER:
        if section in CIV_DIRECT_WORKSPACE_SECTIONS:
            sections[section] = {}
        else:
            sections[section] = []
    return CivProject(project_name=normalized_name, sections=sections)


def load_civ_project(file_path: Path) -> CivProject:
    """Load and parse a .CIV file from disk (JSON payload)."""
    if file_path.suffix.upper() != CIV_FILE_EXTENSION:
        raise ValueError("请选择 .CIV 工程文件")

    raw_text = file_path.read_text(encoding="utf-8")
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("工程文件格式错误，应为 JSON 对象")
    return CivProject.from_dict(payload)


def save_civ_project(file_path: Path, project: CivProject) -> None:
    """Serialize the project to a .CIV file in JSON format."""
    if file_path.suffix.upper() != CIV_FILE_EXTENSION:
        raise ValueError("工程文件后缀必须是 .CIV")

    payload = project.to_dict()
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
