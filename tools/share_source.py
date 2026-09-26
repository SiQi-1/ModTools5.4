"""Export the current Git working tree as a source-only skill + tools directory.

No Python packages, compiler, executable builder or archive writer are required.
Only tracked, distributable files are copied; local changes to those files are included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_SUFFIXES = {
    ".exe", ".dll", ".msi", ".msix", ".zip", ".7z", ".rar", ".tar",
    ".gz", ".tgz", ".bz2", ".xz", ".whl", ".pyd", ".so", ".dylib",
    ".pyc", ".pyo", ".spec",
}
LOCAL_DIRS = {".git", ".venv", "__pycache__", "node_modules", "logs"}
OUTPUT_DIRS = {"build", "dist", "release", "shares", "modgen_work", "_work"}
ROOT_FILES = {
    ".gitignore", ".gitattributes", "AGENT.md", "AGENTS.md", "AGENT_SETUP.md",
    "CLAUDE.md", "README.md", "CIV6_MOD_TUTORIAL.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "ModTools5.4.py", "requirements.txt",
    "local_text_New.sqlite",
}
SOURCE_DIRS = {"ModTools_5_4", "modgen", "skills", "tools", "docs", "licenses", "tests", ".github"}
REQUIRED = {
    "AGENTS.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "modgen/cli.py", "modgen/schemas/entry_schemas.json",
    "ModTools_5_4/project/civ_project.py", "skills/RULES.md", "skills/catalog.json",
    "tools/setup_env.py", "tools/share_source.py", "local_text_New.sqlite",
    "licenses/civ6-modding-skills.LICENSE", "licenses/Civ6WorkshopUploader.LICENSE",
}


def forbidden(path: str) -> bool:
    parts = PurePosixPath(path.replace("\\", "/")).parts
    lower = [part.lower() for part in parts]
    return bool(
        not parts or ".." in parts or PurePosixPath(path).is_absolute()
        or any(part in LOCAL_DIRS for part in lower)
        or lower[0] in OUTPUT_DIRS
        or lower[-1] in {"settings.json", "source_manifest.json"}
        or any(suffix in ARTIFACT_SUFFIXES for suffix in PurePosixPath(lower[-1]).suffixes)
    )


def distributable(path: str) -> bool:
    if forbidden(path):
        return False
    if path.startswith("tools/legacy_skill_builders/"):
        return path == "tools/legacy_skill_builders/README.md"
    return path in ROOT_FILES or PurePosixPath(path).parts[0] in SOURCE_DIRS


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def tracked_files(root: Path) -> list[str]:
    actual = Path(git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    if actual != root.resolve():
        raise ValueError("Run this tool from a complete Git checkout (not a copied share directory).")
    return sorted(p.decode("utf-8") for p in git(root, "ls-files", "-z").split(b"\0") if p)


def check_tracked(paths: list[str]) -> list[str]:
    # A historical log placeholder contains no generated data.
    issues = [f"Tracked artifact/local file: {p}" for p in paths
              if forbidden(p) and p != "ModTools_5_4/logs/.gitkeep"]
    issues.extend(f"Missing tracked source: {p}" for p in sorted(REQUIRED - set(paths)))
    return issues


def export_source(root: Path, destination: Path, paths: list[str]) -> dict:
    root = root.resolve()
    destination = destination.resolve()
    if destination == root or destination in root.parents:
        raise ValueError("Destination must not contain or replace the source checkout.")
    if root in destination.parents and destination.relative_to(root).parts[0] != "shares":
        raise ValueError("Inside the checkout, export only below the ignored shares/ directory.")
    if destination.exists():
        raise ValueError("Destination already exists; use a new directory.")
    selected = [p for p in paths if distributable(p)]
    # Preflight before creating any output, including directory symlinks/junctions.
    for relative in selected:
        source = root / relative
        if not source.is_file() or not source.resolve().is_relative_to(root):
            raise ValueError(f"Missing or external source: {relative}")
        for part in (source, *source.parents):
            if part == root:
                break
            if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
                raise ValueError(f"Linked source is not distributable: {relative}")
    commit = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=normal"))
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for relative in selected:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
        data = target.read_bytes()
        records.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "format": "modtools-source-share", "version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": commit, "working_tree_dirty": dirty,
        "content": "Tracked working-tree source files; per-file hashes describe the shared content.",
        "files": records,
    }
    (destination / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Git hygiene or export a skill + tools source directory.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Reject tracked archives, executables and local settings")
    mode.add_argument("--out", type=Path, help="New output directory; never overwrite an existing share")
    args = parser.parse_args()
    try:
        paths = tracked_files(ROOT)
        issues = check_tracked(paths)
        if issues:
            for issue in issues:
                print(issue, file=sys.stderr)
            return 1
        if args.check:
            print("Source distribution check passed: no tracked release artifacts or local settings.")
        else:
            manifest = export_source(ROOT, args.out, paths)
            print(f"Source share: {args.out.resolve()} ({len(manifest['files'])} files)")
            print(f"Base commit: {manifest['base_commit']}; working tree dirty: {manifest['working_tree_dirty']}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Source distribution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
