"""Repository CLI adapters for the shareable HTML -> Civ6 UI skill bundle.

The bundle owns rendering, the manifest contract and export verification. Keep
these adapters Qt-free and do not maintain another copy of those implementations.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent / "skills" / "civ6-html-ui"


def script_path(name: str) -> Path:
    path = skill_root() / "scripts" / name
    if not path.is_file():
        raise ValueError(f"缺少随包 HTML UI 工具，请保留完整 skills/civ6-html-ui 目录：{path}")
    return path


def manifest_entries(manifest, png_dir=None):
    spec = importlib.util.spec_from_file_location("_modtools_texture_manifest", script_path("texture_manifest.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.source_entries(Path(manifest), Path(png_dir) if png_dir is not None else None)


def _resolve_executable(value: str) -> str:
    found = shutil.which(value)
    if found:
        return str(Path(found).resolve())
    path = Path(value).expanduser()
    if path.is_file():
        return str(path.resolve())
    raise ValueError(f"找不到可执行程序：{value}")


def find_node(explicit=None) -> str:
    return _resolve_executable(explicit or os.environ.get("CIV6_UI_NODE") or "node")


def find_browser(explicit=None) -> str:
    requested = explicit or os.environ.get("CIV6_UI_BROWSER")
    if requested:
        return _resolve_executable(requested)
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve())
    candidates = []
    if sys.platform == "win32":
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(env)
            if root:
                candidates.extend(Path(root) / relative for relative in (
                    "Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"))
    elif sys.platform == "darwin":
        candidates.extend(Path(value) for value in (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise ValueError("找不到 Edge/Chrome/Chromium；使用 --browser 指定可执行文件，或设置 CIV6_UI_BROWSER")


def _run(command: list[str]) -> subprocess.CompletedProcess:
    # argv list: paths with spaces/unicode work without shell interpolation.
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace",
                            env=dict(os.environ, PYTHONIOENCODING="utf-8"), **options)
    if result.returncode:
        raise ValueError((result.stderr or result.stdout).strip() or f"进程失败，退出码 {result.returncode}")
    return result


def render_textures(html, out, *, browser=None, node=None, replace=False) -> dict:
    node_exe, browser_exe = find_node(node), find_browser(browser)
    destination = Path(out).resolve()
    command = [node_exe, str(script_path("render-textures.cjs")), "--html", str(Path(html).resolve()),
               "--out", str(destination), "--browser", browser_exe]
    if replace:
        command.append("--replace")
    _run(command)
    manifest = destination / "texture_manifest.json"
    entries = manifest_entries(manifest)
    return {"ok": True, "count": len(entries), "manifest": str(manifest),
            "directory": str(destination), "node": node_exe, "browser": browser_exe}


def verify_textures(manifest, *, png_dir=None, project=None, tolerance=0) -> dict:
    manifest = Path(manifest).resolve()
    command = [sys.executable, str(script_path("verify-textures.py")), "--manifest", str(manifest),
               "--png-dir", str(Path(png_dir).resolve() if png_dir is not None else manifest.parent),
               "--tolerance", str(tolerance)]
    if project is not None:
        command.extend(["--project", str(Path(project).resolve())])
    return json.loads(_run(command).stdout)
