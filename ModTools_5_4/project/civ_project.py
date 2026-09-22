"""CIV project file model (.CIV is JSON in content)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json

from .schema import (
    CIV_DIRECT_WORKSPACE_SECTIONS,
    CIV_FILE_EXTENSION,
    CIV_GROUP_SECTIONS,
    CIV_SCHEMA_VERSION,
    CIV_SECTION_ORDER,
    CIV_UI_ICON_SECTIONS,
    parse_project_payload,
    project_envelope,
)


@dataclass(slots=True)
class CivProject:
    """In-memory representation of a .CIV project file."""

    project_name: str
    sections: dict[str, object]
    extensions: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = project_envelope(self.project_name, self.sections)
        if self.extensions:
            payload["extensions"] = self.extensions
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "CivProject":
        # Preserve the legacy direct-call error for non-object payloads.
        if not isinstance(payload, dict):
            raise ValueError("工程文件缺少 meta 节点")
        project_name, normalized = parse_project_payload(payload)
        from .extensions import manifest
        extensions = manifest(payload)
        return cls(project_name=project_name, sections=normalized, extensions=extensions or {})


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
    """Serialize the project to a .CIV file from the shared schema envelope."""
    if file_path.suffix.upper() != CIV_FILE_EXTENSION:
        raise ValueError("工程文件后缀必须是 .CIV")
    file_path.write_text(
        json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
