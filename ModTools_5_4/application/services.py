"""Small, Qt-free service boundaries for incremental extraction.

The services intentionally delegate to existing pure models or an adapter
protocol.  This gives callers a stable seam while the large GUI implementation
is migrated in later phases.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..project.civ_project import CivProject, create_empty_project, load_civ_project, save_civ_project
from ..project.output_manifest import OutputManifest


class GenerationAdapter(Protocol):
    """Public operations required from the current GUI generation adapter."""

    def output_manifest(self) -> OutputManifest: ...

    def generate_all_output_files(self, *, overwrite_policy: str = "ask") -> dict[str, object] | None: ...

    def generate_single_output_file(
        self, relative_path: str, *, overwrite: bool | None = None
    ) -> dict[str, object] | None: ...


class ProjectService:
    """Persistence boundary for .CIV projects."""

    def create(self, project_name: str = "未命名工程") -> CivProject:
        return create_empty_project(project_name)

    def load(self, file_path: Path) -> CivProject:
        return load_civ_project(file_path)

    def save(self, file_path: Path, project: CivProject) -> None:
        save_civ_project(file_path, project)


class GenerationService:
    """Adapter-facing generation boundary used by AI and future CLI code."""

    def manifest(self, adapter: GenerationAdapter) -> OutputManifest:
        return adapter.output_manifest()

    def generate_all(
        self, adapter: GenerationAdapter, *, overwrite_policy: str = "ask"
    ) -> dict[str, object] | None:
        return adapter.generate_all_output_files(overwrite_policy=overwrite_policy)

    def generate_file(
        self,
        adapter: GenerationAdapter,
        relative_path: str,
        *,
        overwrite: bool | None = None,
    ) -> dict[str, object] | None:
        return adapter.generate_single_output_file(relative_path, overwrite=overwrite)
