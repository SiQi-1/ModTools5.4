"""Repository documentation linter (stdlib only).

Checks (all tracked files unless noted):
1. root whitelist      -- only the agreed root entries may be tracked
2. doc budgets         -- markdown <= 32 KB, SKILL.md <= 500 lines, always_read <= 20 KB
3. route budgets       -- each skills/catalog.json route must_read <= max_kb (default 30 KB)
4. local paths         -- no drive-letter/user-profile absolute paths in tracked text
5. markdown links      -- relative links inside tracked markdown must resolve
6. meta header         -- docs/**/*.md and skills/README.md should start with a "> 受众" line

Usage:
    python tools/doc_lint.py [--json] [--fail-on-warnings]

Exit code 0 when there are no errors (warnings do not fail unless --fail-on-warnings).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROOT_FILE_WHITELIST = {
    ".gitattributes", ".gitignore", "AGENTS.md", "CLAUDE.md", "LICENSE",
    "ModTools5.4.py", "README.md", "THIRD_PARTY_NOTICES.md",
    "local_text_New.sqlite", "requirements.txt",
}
ROOT_DIR_WHITELIST = {
    ".github", "docs", "licenses", "modgen", "ModTools_5_4", "skills", "tests", "tools",
}
MARKDOWN_BUDGET = 32 * 1024
SKILL_LINES_BUDGET = 500
ALWAYS_READ_BUDGET = 20 * 1024
ROUTE_BUDGET_DEFAULT = 30 * 1024
MARKDOWN_BUDGET_ALLOWLIST = {
    "ModTools_5_4/CHANGELOG.md",
}
BUDGET_ALLOWLIST_PREFIXES = ("docs/dev/changelog-archive/",)
LOCAL_PATH_ALLOWLIST = {
    "ModTools_5_4/CHANGELOG.md",
}
LOCAL_PATH_SKIP_PREFIXES = ("tests/", "docs/dev/changelog-archive/")
LOCAL_PATH_ALLOW_PATTERNS = (
    "C:\\Windows", "C:/Windows", "C:\\WINDOWS", "C:/WINDOWS",
    "C:\\Temp", "C:/Temp", "C:\\Users\\<", "C:/Users/<",
    "D:/...", "D:/…", "D:/MyMod", "D:/art/", "D:/fake",
)

DRIVE_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
USER_RE = re.compile(r"C:[\\/]Users[\\/]", re.IGNORECASE)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*(\x60{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".ps1", ".sh", ".toml", ".cfg", ".ini", ".bat"}
SKIP_PATH_PREFIXES = ("ModTools_5_4/From/", "skills/packages/civ6-art-images/assets/")


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout
    return sorted(p for p in out.decode("utf-8").split("\0") if p)


def is_allowed_budget(path: str) -> bool:
    return path in MARKDOWN_BUDGET_ALLOWLIST or path.startswith(BUDGET_ALLOWLIST_PREFIXES)


def lint() -> dict:
    files = tracked_files()
    errors: list[dict] = []
    warnings: list[dict] = []

    def issue(bucket, code, path, message, line=0):
        bucket.append({"code": code, "path": path, "line": line, "message": message})

    # 1 root whitelist
    for path in files:
        top = path.split("/", 1)[0]
        if "/" not in path:
            if path not in ROOT_FILE_WHITELIST:
                issue(errors, "root-file", path, "root file not in whitelist")
        elif top not in ROOT_DIR_WHITELIST:
            issue(errors, "root-dir", path, f"tracked under unexpected root directory {top}/")

    # 2/3 budgets + 4 local paths
    catalog = None
    catalog_path = ROOT / "skills" / "catalog.json"
    if catalog_path.exists():
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issue(errors, "catalog-json", "skills/catalog.json", str(exc))

    for path in files:
        full = ROOT / path
        if not full.is_file():
            continue
        suffix = full.suffix.lower()
        if (suffix in TEXT_SUFFIXES and not path.startswith(SKIP_PATH_PREFIXES)
                and not path.startswith(LOCAL_PATH_SKIP_PREFIXES)):
            try:
                text = full.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = ""
            if text and path not in LOCAL_PATH_ALLOWLIST:
                for i, line in enumerate(text.splitlines(), 1):
                    if not (DRIVE_RE.search(line) or USER_RE.search(line)):
                        continue
                    if any(pattern in line for pattern in LOCAL_PATH_ALLOW_PATTERNS):
                        continue
                    if re.search(r"C:\\\\+Windows|C:/Windows", line):
                        continue
                    issue(warnings, "local-path", path, line.strip()[:120], i)
                    break
        if suffix != ".md":
            continue
        size = full.stat().st_size
        if size > MARKDOWN_BUDGET and not is_allowed_budget(path):
            issue(errors, "md-budget", path, f"{size} B > {MARKDOWN_BUDGET} B")
        if full.name == "SKILL.md":
            lines = len(full.read_text(encoding="utf-8").splitlines())
            if lines > SKILL_LINES_BUDGET:
                issue(errors, "skill-budget", path, f"{lines} lines > {SKILL_LINES_BUDGET}")
        if path.startswith("docs/") and full.name not in {"INDEX.md", "README.md"}:
            head = full.read_text(encoding="utf-8").splitlines()[:4]
            if not any(line.lstrip().startswith("> 受众") for line in head):
                issue(warnings, "meta-header", path, "missing '> 受众 …' meta line in first 4 lines")

    if catalog:
        always = catalog.get("always_read", [])
        total = 0
        for rel in always:
            target = ROOT / "skills" / rel
            if target.exists():
                total += target.stat().st_size
            else:
                issue(errors, "catalog-missing", f"skills/{rel}", "always_read target missing")
        if total > ALWAYS_READ_BUDGET:
            issue(errors, "always-read-budget", "skills/catalog.json", f"always_read {total} B > {ALWAYS_READ_BUDGET} B")
        for route in catalog.get("routes", []):
            rid = route.get("id", "?")
            must = [r for r in route.get("read", []) if isinstance(r, str)]
            budget = int(route.get("max_kb", 0) or 0) * 1024 or ROUTE_BUDGET_DEFAULT
            size = 0
            for rel in must:
                target = ROOT / "skills" / rel
                if not target.exists():
                    issue(errors, "catalog-missing", f"skills/{rel}", f"route {rid}: read target missing")
                else:
                    size += target.stat().st_size
            if size > budget:
                issue(warnings, "route-budget", "skills/catalog.json", f"route {rid}: {size} B > {budget} B")

    # 5 links
    for path in files:
        if not path.endswith(".md"):
            continue
        full = ROOT / path
        if not full.is_file():
            continue
        raw = full.read_text(encoding="utf-8").splitlines()
        in_fence = False
        for i, line in enumerate(raw, 1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for match in LINK_RE.finditer(INLINE_CODE_RE.sub("", line)):
                target = match.group(1).strip()
                if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                resolved = (full.parent / target).resolve()
                try:
                    resolved.relative_to(ROOT.resolve())
                except ValueError:
                    issue(errors, "link-escape", path, target, i)
                    continue
                if not resolved.exists() and path not in ("ModTools_5_4/CHANGELOG.md",):
                    issue(warnings, "link-missing", path, target, i)

    return {
        "ok": not errors,
        "tracked_files": len(files),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint tracked documentation and repository layout.")
    parser.add_argument("--json", action="store_true", help="machine readable output")
    parser.add_argument("--fail-on-warnings", action="store_true", help="treat warnings as failure")
    args = parser.parse_args()
    report = lint()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"tracked files: {report['tracked_files']}")
        for bucket, label in ((report["errors"], "ERROR"), (report["warnings"], "WARN")):
            for item in bucket:
                loc = f":{item['line']}" if item.get("line") else ""
                print(f"{label} [{item['code']}] {item['path']}{loc} {item['message']}")
        print("OK" if report["ok"] else "FAILED")
    if not report["ok"]:
        return 1
    if args.fail_on_warnings and report["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())