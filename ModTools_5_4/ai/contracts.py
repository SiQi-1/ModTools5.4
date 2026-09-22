"""Machine-readable metadata for external AI control actions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ActionContract:
    name: str
    description: str
    params: dict[str, dict[str, Any]] = field(default_factory=dict)
    version: str = "1"

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }
        if self.params:
            result["params"] = self.params
        return result


ACTION_PARAMS: dict[str, dict[str, dict[str, Any]]] = {
    "extension": {
        "operation": {"type": "string", "enum": ["init", "write", "list", "check", "remove"]},
        "relative_path": {"type": "string"}, "content": {"type": "string"},
        "gameplay": {"type": "boolean"}, "ui": {"type": "boolean"},
        "role": {"type": "string", "enum": ["database", "gameplay", "ui", "import", "text", "icons", "colors"]},
        "id": {"type": "string"}, "feature": {"type": "string"},
        "scope": {"type": "string", "enum": ["front", "in_game", "both"]},
        "phase": {"type": "string", "enum": ["before_generated", "after_generated"]},
        "depends_on": {"type": "array"}, "keep_file": {"type": "boolean"},
    },
    "project_check": {},
    "open_project": {"path": {"type": "string", "required": True}},
    "save_project": {"path": {"type": "string", "required": False}},
    "generate_all": {"overwrite": {"type": "string", "enum": ["ask", "all", "none"]}},
    "generate_file": {
        "relative_path": {"type": "string", "required": True},
        "overwrite": {"type": "boolean", "required": False},
    },
    "project_file_read": {"relative_path": {"type": "string", "required": True}},
    "project_file_delete": {
        "relative_path": {"type": "string", "required": True},
        "remove_action": {"type": "boolean", "required": False},
    },
    "search": {
        "keyword": {"type": "string", "required": True},
        "category": {"type": "string", "required": False},
        "limit": {"type": "integer", "required": False},
    },
    "skill": {
        "keyword": {"type": "string", "required": False},
        "file": {"type": "string", "required": False},
        "section": {"type": "string", "required": False},
        "plan": {"type": "boolean", "required": False},
        "limit": {"type": "integer", "required": False},
    },
}


def make_action_contract(name: str, description: str) -> ActionContract:
    return ActionContract(
        name=str(name).strip(),
        description=str(description),
        params=dict(ACTION_PARAMS.get(str(name).strip(), {})),
    )
