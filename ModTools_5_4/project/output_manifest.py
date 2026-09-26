"""Shared output manifest value object and safe relative-path helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


@dataclass(slots=True)
class OutputManifest:
    files: dict[str, str | bytes]
    folders: set[str]
    can_generate: bool
    civ6proj_path: Path | None

    def as_tuple(self) -> tuple[dict[str, str | bytes], set[str], bool, Path | None]:
        """Return the legacy tuple consumed by the existing GUI code."""
        return self.files, self.folders, self.can_generate, self.civ6proj_path

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe AI-facing summary."""
        return {
            "can_generate": self.can_generate,
            "civ6proj_path": str(self.civ6proj_path) if self.civ6proj_path else None,
            "file_count": len(self.files),
            "files": sorted(self.files),
            "folders": sorted(self.folders),
        }


def make_output_manifest(
    files: dict[str, str | bytes], folders: Iterable[str], civ6proj_path: Path | None
) -> OutputManifest:
    """Create a manifest while preserving the current output contents."""
    path = civ6proj_path if isinstance(civ6proj_path, Path) else None
    return OutputManifest(
        files=dict(files),
        folders={str(folder) for folder in folders if str(folder).strip()},
        can_generate=bool(path and path.suffix.lower() == ".civ6proj"),
        civ6proj_path=path,
    )


def safe_relative_path(value: object) -> str | None:
    """Normalize a relative path and reject absolute paths or traversal."""
    text = str(value or "").replace("\\", "/").strip()
    if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        return None
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return None
    return "/".join(parts)


def parent_folders(relative_path: str) -> set[str]:
    """Return all parent folders for a normalized project-relative path."""
    normalized = safe_relative_path(relative_path)
    if not normalized or "/" not in normalized:
        return set()
    parent = normalized.rsplit("/", 1)[0]
    result: set[str] = set()
    while parent:
        result.add(parent)
        if "/" not in parent:
            break
        parent = parent.rsplit("/", 1)[0]
    return result
