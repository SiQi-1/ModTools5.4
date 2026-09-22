"""Conservative generated/custom SQL conflict checks with explicit coverage limits.

Literal INSERT rows use known primary keys, including composite keys. Dynamic
SQL, INSERT SELECT and runtime semantics remain outside static verification.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .preview import PreviewError, build_preview_manifest
from .sql_inspect import insert_rows, updated_tables, xml_rows, schema_keys, row_key


def parse_inserts(sql_text: str) -> list[tuple[str, str]]:
    """Compatibility helper: all literal VALUES rows' first values (not PKs)."""
    rows, _ = insert_rows(sql_text)
    return [(table, str(values[0])) for table, _cols, values in rows if values and values[0] is not None]


def parse_updated_tables(sql_text: str) -> set[str]:
    return updated_tables(sql_text)


def check_conflicts(civ_path: Path, *, payload: dict | None = None, manifest: dict | None = None) -> dict[str, Any]:
    if payload is None:
        from .merger import load_civ
        payload = load_civ(civ_path)
    try:
        manifest = manifest if manifest is not None else build_preview_manifest(civ_path)
    except (PreviewError, ValueError, OSError) as exc:
        return {"errors": [{"message": str(exc)}], "warnings": [], "generated_files": [], "custom_files": []}
    errors = list(manifest.get("extension_errors", []))
    warnings = []
    files = manifest["files"]
    readonly = {p.casefold() for p in manifest.get("readonly_custom_paths", [])}
    extension_entries = (payload.get("extensions") or {}).get("files", [])
    extensions = {e["path"].casefold(): e for e in extension_entries}
    action_scopes: dict[str, set[str]] = {}
    action_files = set()
    for key, entries in manifest.get("actions", {}).items():
        scope = "front" if key == "front_end_actions" else "in_game"
        for action in entries:
            if action.get("type") != "UpdateDatabase":
                continue
            for raw in action.get("files", []):
                rel = str(raw).replace("\\", "/")
                action_scopes.setdefault(rel.casefold(), set()).add(scope)
                action_files.add(rel)
    for entry in extension_entries:
        if entry["role"] == "database":
            action_files.add(entry["path"])
    # Separate database actions from text/icons, even when they share SQL syntax.
    candidates = {p: text for p, text in files.items()
                  if Path(p).suffix.lower() in {".sql", ".xml"}
                  and (p.lower().startswith("data/") or p in action_files)
                  and (p.casefold() not in extensions or extensions[p.casefold()]["role"] == "database")}
    custom = {p: text for p, text in candidates.items()
              if p.casefold() in readonly or p.casefold() in extensions}
    generated = {p: text for p, text in candidates.items() if p not in custom}
    for rel in sorted(action_files):
        if rel.casefold() not in {p.casefold() for p in files}:
            warnings.append({"file": rel, "message": "UpdateDatabase 动作引用的文件不在输出清单中"})

    def scopes(path: str) -> set[str]:
        entry = extensions.get(path.casefold())
        if entry:
            return {"front", "in_game"} if entry["scope"] == "both" else {entry["scope"]}
        return action_scopes.get(path.casefold(), {"front" if Path(path).stem.lower().endswith("_configs") else "in_game"})

    def rows(path, content):
        return (xml_rows(content), set()) if path.lower().endswith(".xml") else insert_rows(content)

    # Each action scope has a separate key space and custom table schema.
    for scope in ("front", "in_game"):
        scoped = {p: t for p, t in candidates.items() if scope in scopes(p)}
        keys, columns = schema_keys({p: t for p, t in scoped.items() if p.lower().endswith(".sql")})
        generated_keys, generated_tables, custom_keys = {}, set(), {}
        for path, content in generated.items():
            if path not in scoped:
                continue
            parsed, _ = rows(path, content)
            for table, cols, values in parsed:
                generated_tables.add(table.casefold())
                key = row_key(table, cols, values, keys, columns)
                if key:
                    generated_keys.setdefault(key, path)
        for path, content in custom.items():
            if path not in scoped:
                continue
            parsed, skipped = rows(path, content)
            unknown = set()
            for table, cols, values in parsed:
                key = row_key(table, cols, values, keys, columns)
                if key is None:
                    if keys.get(table.casefold()) != ():
                        unknown.add(table)
                    continue
                pk = key[1][0] if len(key[1]) == 1 else list(key[1])
                common = {"file": path, "scope": scope, "table": table, "pk": pk}
                if key in custom_keys:
                    errors.append({**common, "message": f"自定义数据主键重复（另见 {custom_keys[key]}）"})
                custom_keys[key] = path
                if key in generated_keys:
                    errors.append({**common, "generated_file": generated_keys[key],
                                   "message": "主键与生成数据冲突：请在 .CIV 或扩展中保留一个维护入口"})
            for table in sorted(unknown | skipped):
                warnings.append({"file": path, "scope": scope, "table": table,
                                 "message": "静态主键检查未覆盖该表的部分语句：主键未知、动态表达式或 INSERT SELECT；需数据库/游戏验证"})
            for table in updated_tables(content) if path.lower().endswith(".sql") else ():
                if table.casefold() in generated_tables:
                    warnings.append({"file": path, "scope": scope, "table": table,
                                     "message": "自定义 SQL 对生成表执行 UPDATE/DELETE：优先在 .CIV 修改；必要补丁需明确依赖及影响，勿机械改成 REPLACE"})
    return {"errors": errors, "warnings": warnings, "generated_files": sorted(generated),
            "custom_files": [{"path": p, "on_disk": True} for p in sorted(custom)],
            "coverage": "已知主键的静态 VALUES/XML Row；不在游戏库执行 SQL、不验证 Lua 运行时"}
