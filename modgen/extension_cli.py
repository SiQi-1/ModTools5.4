"""Project extension commands; source operations do not depend on Qt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ModTools_5_4.project import extensions as ext
from .merger import load_civ, save_civ


def register(sub) -> None:
    command = sub.add_parser("extension", help="工程扩展源码清单、Core/Lua/UI 骨架与依赖检查")
    actions = command.add_subparsers(dest="operation", required=True)
    for name in ("init", "write", "import", "list", "check", "remove"):
        p = actions.add_parser(name)
        p.add_argument("civ", help="工程 .CIV 路径")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=run)
        if name == "init":
            p.add_argument("--gameplay", action="store_true")
            p.add_argument("--ui", action="store_true")
        if name in {"write", "import", "remove"}:
            paths = p.add_mutually_exclusive_group(required=True)
            paths.add_argument("--path", help="输出相对路径；源码存放于扩展目录")
            paths.add_argument("--core", action="store_true", help="使用默认 Core.sql")
        if name in {"write", "import"}:
            p.add_argument("--role", choices=sorted(ext.ROLES))
            p.add_argument("--id", dest="entry_id")
            p.add_argument("--feature")
            p.add_argument("--scope", choices=["front", "in_game", "both"])
            p.add_argument("--phase", choices=["before_generated", "after_generated"])
            p.add_argument("--depends-on", action="append", help="依赖的扩展 id，可重复；省略保留旧值")
            p.add_argument("--clear-dependencies", action="store_true")
        if name == "write":
            content = p.add_mutually_exclusive_group(required=True)
            content.add_argument("--content")
            content.add_argument("--content-file")
        if name == "remove":
            p.add_argument("--keep-file", action="store_true")
    p = sub.add_parser("project-check", help="统一检查 .CIV、扩展依赖、预览及 SQL 冲突（需 PyQt）")
    p.add_argument("civ")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=run_check)
    p = sub.add_parser("build", help="检查并生成绑定的 ModBuddy 工程源码；不调用 ModBuddy 编译或部署")
    p.add_argument("civ")
    p.add_argument("--overwrite", choices=["all", "none"], default="none")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=run_build)


def _print(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for error in result.get("errors", []):
        print(f"ERROR: {error.get('file', '')} {error['message']}")
    for warning in result.get("warnings", []):
        print(f"WARNING: {warning.get('file', '')} {warning['message']}")
    if not result.get("errors"):
        print(json.dumps(result, ensure_ascii=False, indent=2))


def run(args: argparse.Namespace) -> int:
    civ = Path(args.civ).resolve()
    payload = load_civ(civ)
    operation = args.operation
    try:
        if operation == "init":
            result = ext.init_extensions(payload, civ, gameplay=args.gameplay, ui=args.ui)
        elif operation in {"list", "check"}:
            result = ext.plan_extensions(payload, civ)
            result.pop("files", None)  # List source metadata, not entire script bodies.
            result["ok"] = not result["errors"]
        else:
            path = args.path
            if args.core:
                core = next((e for e in (ext.manifest(payload) or {}).get("files", []) if e["id"] == "core"), None)
                if not core:
                    raise ext.ExtensionError("先执行 extension init 创建 Core.sql")
                path = core["path"]
            if operation == "remove":
                result = ext.remove_extension(payload, civ, path, keep_file=args.keep_file)
            else:
                if operation == "import":
                    from .custom_file import project_root_dir
                    source = ext.safe_path(project_root_dir(payload), path)
                    target = ext.safe_path(ext.source_root(payload, civ), path)
                    if target.exists():
                        raise ext.ExtensionError("扩展源码已存在；import 不覆盖，请使用 write 修改")
                    content = source.read_text(encoding="utf-8-sig")
                else:
                    content = Path(args.content_file).read_text(encoding="utf-8-sig") if args.content_file else args.content
                result = ext.write_extension(
                    payload, civ, path, content, role=args.role, id=args.entry_id,
                    feature=args.feature, scope=args.scope, phase=args.phase,
                    depends_on=[] if args.clear_dependencies else args.depends_on,
                )
        if operation not in {"list", "check"}:
            save_civ(civ, payload)
        _print(result, args.json)
        return 0 if result.get("ok", True) else 1
    except (ValueError, OSError) as exc:
        _print({"ok": False, "errors": [{"message": str(exc)}]}, args.json)
        return 1


def check_project(civ: Path, *, payload: dict | None = None, page=None) -> dict:
    """One report for project data, declared sources, output plan and SQL conflicts."""
    from .validator import validate_project
    from .preview import build_preview_manifest
    from .custom_conflicts import check_conflicts
    payload = payload if payload is not None else load_civ(civ)
    errors = [{"message": message, "stage": "civ"} for message in validate_project(payload)]
    plan = ext.plan_extensions(payload, civ)
    errors.extend(plan["errors"])
    result = {"ok": not errors, "errors": errors, "warnings": plan["warnings"],
              "extensions": plan["entries"], "checks": ["civ", "extensions"]}
    if errors:
        return result
    try:
        preview = build_preview_manifest(civ, page=page)
        errors.extend(preview.get("extension_errors", []))
        conflicts = check_conflicts(civ, payload=payload, manifest=preview)
        errors.extend(conflicts["errors"])
        result["warnings"].extend(conflicts["warnings"])
        result["checks"].extend(["preview", "sql_conflicts"])
        result["files"] = sorted(preview["files"])
        result["can_generate"] = preview["can_generate"]
        # Check registered references against the final output plan.
        actions = preview.get("actions", {})
        output_paths = {p.casefold() for p in preview["files"]}
        for entries in actions.values():
            for action in entries:
                for path in action.get("files", []):
                    if action.get("type") == "UpdateArt" and path == "(Mod Art Dependency File)":
                        continue  # ModBuddy virtual dependency, not a source file.
                    if str(path).replace("\\", "/").casefold() not in output_paths:
                        errors.append({"file": path, "message": "文件动作引用不在最终输出清单中"})
    except (RuntimeError, ValueError, OSError) as exc:
        errors.append({"message": str(exc), "stage": "preview"})
    result["ok"] = not errors
    return result


def run_check(args: argparse.Namespace) -> int:
    result = check_project(Path(args.civ).resolve())
    _print(result, args.json)
    return 0 if result["ok"] else 1


def run_build(args: argparse.Namespace) -> int:
    from .preview import _build_page
    civ = Path(args.civ).resolve()
    page = _build_page(civ)
    try:
        page.ai_run_quick_config()
        checked = check_project(civ, payload=page._project.to_dict(), page=page)
        if not checked["ok"]:
            _print(checked, args.json)
            return 1

        result = page.generate_all_output_files(overwrite_policy=args.overwrite)
        if result.get("ok"):
            page.save_project()
        result["checks"] = checked["checks"]
        result["warnings"] = checked["warnings"]
        result["next"] = "ModBuddy Build / Cooker / 游戏部署与实机验证尚未执行"
        _print(result, args.json)
        return 0 if result.get("ok") else 1
    finally:
        page.close()
        page.deleteLater()
