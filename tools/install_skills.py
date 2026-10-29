r"""Install shareable skill packages into an agent's skill directory.

Packages live in skills/packages/<name>/ (SKILL.md + references/scripts/assets).
They are plain folders, so an agent only auto-loads them after they are copied or
linked into that agent's skill directory.

Usage:
    python tools/install_skills.py --list
    python tools/install_skills.py --target claude            # ~/.claude/skills
    python tools/install_skills.py --target codex             # ~/.codex/skills
    python tools/install_skills.py --target dsh               # ~/.dsh/skills (DeepSeek Harness)
    python tools/install_skills.py --target agents            # ~/.agents/skills
    python tools/install_skills.py --target dsh --link        # 目录联接，不复制（Windows junction）
    python tools/install_skills.py --dir <目标目录>            # explicit directory
    python tools/install_skills.py --target claude --dry-run
    python tools/install_skills.py --target claude --force    # overwrite existing

No third-party dependencies; never modifies the repository.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "skills" / "packages"
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
TARGETS = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "dsh": Path.home() / ".dsh" / "skills",
    "agents": Path.home() / ".agents" / "skills",
}
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def packages() -> list[Path]:
    if not PACKAGES.is_dir():
        return []
    return sorted(p for p in PACKAGES.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def read_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def validate(pkg: Path) -> list[str]:
    problems = []
    skill_md = pkg / "SKILL.md"
    meta = read_frontmatter(skill_md)
    name = meta.get("name", "")
    description = meta.get("description", "")
    if not name:
        problems.append("SKILL.md missing frontmatter name")
    elif name != pkg.name:
        problems.append(f"frontmatter name {name!r} != directory {pkg.name!r}")
    if not description:
        problems.append("SKILL.md missing frontmatter description")
    elif len(description) > 1024:
        problems.append(f"description too long ({len(description)} > 1024)")
    return problems


def copy_package(src: Path, dest_root: Path, force: bool) -> str:
    target = dest_root / src.name
    if target.exists() or target.is_symlink():
        if not force:
            return f"skip (exists): {target}"
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    def ignore(directory: str, names: list[str]) -> set[str]:
        return {n for n in names if n in SKIP_DIRS or Path(n).suffix in SKIP_SUFFIXES}
    shutil.copytree(src, target, ignore=ignore)
    return f"installed: {src.name} -> {target}"


def link_package(src: Path, dest_root: Path, force: bool) -> str:
    target = dest_root / src.name
    if target.exists() or target.is_symlink():
        if not force:
            return f"skip (exists): {target}"
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(src)], capture_output=True, text=True)
        if result.returncode != 0:
            return f"link failed: {target} :: {(result.stderr or result.stdout).strip()}"
    else:
        os.symlink(src, target, target_is_directory=True)
    return f"linked: {src.name} -> {target}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install repository skill packages into an agent skill directory.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="list available packages and their validation status")
    parser.add_argument("--target", choices=sorted(TARGETS), help="known agent skill directory")
    parser.add_argument("--dir", default="", help="explicit destination directory")
    parser.add_argument("--package", action="append", default=[], help="install only this package (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="validate and print actions without copying")
    parser.add_argument("--force", action="store_true", help="overwrite an existing installed copy")
    parser.add_argument("--link", action="store_true", help="create a directory link instead of copying (Windows junction / symlink)")
    args = parser.parse_args(argv)

    available = packages()
    if not available:
        print(f"No packages found under {PACKAGES}", file=sys.stderr)
        return 1

    if args.list or not (args.target or args.dir):
        for pkg in available:
            problems = validate(pkg)
            status = "OK" if not problems else "INVALID: " + "; ".join(problems)
            print(f"{pkg.name:32} {status}")
        if not args.list:
            print("\nChoose a destination: --target claude|codex or --dir <path>", file=sys.stderr)
            return 2
        return 0

    dest_root = Path(args.dir) if args.dir else TARGETS[args.target]
    selected = [p for p in available if not args.package or p.name in args.package]
    missing = sorted(set(args.package) - {p.name for p in selected})
    if missing:
        print(f"Unknown package(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    invalid = [(p, validate(p)) for p in selected]
    invalid = [(p, problems) for p, problems in invalid if problems]
    if invalid:
        for pkg, problems in invalid:
            print(f"INVALID {pkg.name}: {'; '.join(problems)}", file=sys.stderr)
        return 1

    if not args.dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)
    for pkg in selected:
        if args.dry_run:
            action = "link" if args.link else "install"
            print(f"would {action}: {pkg.name} -> {dest_root / pkg.name}")
        else:
            print(link_package(pkg, dest_root, args.force) if args.link else copy_package(pkg, dest_root, args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
