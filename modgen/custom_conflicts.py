"""modgen check-conflicts：自定义 SQL × 生成 SQL 的冲突检测与协调。

协调规则（与 skills/05-modtools-civ/pipeline.md 一致）：
- **硬错误**：同表同主键（VALUES 第一列）同时出现在 生成 SQL 与 自定义 SQL →
  游戏加载主键冲突；自定义 SQL 内部重复同样报错；
- **警告**：自定义 SQL UPDATE/DELETE 的表 ∈ 生成 SQL 写入的表 →
  下次生成会覆盖回退（反模式），应回 .CIV 改或改用 INSERT OR REPLACE；
- `INSERT ... SELECT`（继承/数据迁移）不产生 VALUES，不参与主键对比（合法模式）；
- 加载顺序由工具保证：自定义 UpdateDatabase load_order=10000 > 生成数据 9999。

生成 SQL 经 preview 引擎（无头 GUI）取得，需要 PyQt；缺失时明确报错。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from . import custom_file
from .preview import PreviewError, build_preview_manifest

_INSERT_RE = re.compile(
    r"INSERT\s+(?:OR\s+(?:REPLACE|IGNORE)\s+)?INTO\s+[\"'\[]?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
_UPDATE_RE = re.compile(r"UPDATE\s+[\"'\[]?([A-Za-z_][A-Za-z0-9_]*)\s+SET\b", re.IGNORECASE)
_DELETE_RE = re.compile(r"DELETE\s+FROM\s+[\"'\[]?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)


def _first_value(value_group: str) -> str:
    """取 VALUES(...) 组的第一个值（忽略字符串内的逗号，按括号/引号深度切）。"""
    text = str(value_group or "").strip()
    if not text:
        return ""
    depth = 0
    in_quote = ""
    for index, ch in enumerate(text):
        if in_quote:
            if ch == in_quote:
                in_quote = ""
            continue
        if ch in ("'", '"'):
            in_quote = ch
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                break
        elif ch == "," and depth == 0:
            return text[:index].strip().strip("'\"")
    return text.strip().strip("'\"")


def _extract_value_group(statement: str) -> str:
    """从 INSERT 语句里取 VALUES 后的第一个括号组（无 VALUES 返回空串）。"""
    match = re.search(r"VALUES\s*\(([\s\S]*)", statement, re.IGNORECASE)
    if not match:
        return ""
    text = match.group(1)
    depth = 0
    in_quote = ""
    out: list[str] = []
    for ch in text:
        if in_quote:
            out.append(ch)
            if ch == in_quote:
                in_quote = ""
            continue
        if ch in ("'", '"'):
            in_quote = ch
            out.append(ch)
            continue
        if ch == "(":
            depth += 1
            out.append(ch)
            continue
        if ch == ")":
            depth -= 1
            if depth < 0:
                break
            out.append(ch)
            continue
        out.append(ch)
    return "".join(out)


def parse_inserts(sql_text: str) -> list[tuple[str, str]]:
    """SQL 文本 → [(表名, 主键值), ...]（只取 VALUES 首列；INSERT...SELECT 跳过）。"""
    rows: list[tuple[str, str]] = []
    for statement in str(sql_text or "").split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        match = _INSERT_RE.search(stmt)
        if not match:
            continue
        table = match.group(1)
        value_group = _extract_value_group(stmt)
        if not value_group:
            continue  # INSERT...SELECT 等无 VALUES 语句：不参与主键对比
        pk = _first_value(value_group)
        if pk:
            rows.append((table, pk))
    return rows


def parse_updated_tables(sql_text: str) -> set[str]:
    """UPDATE / DELETE 涉及的表名集合。"""
    tables: set[str] = set()
    for statement in str(sql_text or "").split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        for regex in (_UPDATE_RE, _DELETE_RE):
            match = regex.search(stmt)
            if match:
                tables.add(match.group(1))
    return tables


def _sql_files(files: dict[str, str]) -> dict[str, str]:
    return {
        rel: content
        for rel, content in files.items()
        if rel.lower().startswith("data/") and rel.lower().endswith(".sql")
    }


def check_conflicts(civ_path: Path, *, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """检测自定义 SQL 与生成 SQL 的冲突。返回 {errors, warnings, generated_files, custom_files}。"""
    if payload is None:
        from .merger import load_civ

        payload = load_civ(civ_path)
    try:
        root = custom_file.project_root_dir(payload)
    except custom_file.CustomFileError as exc:
        return {"errors": [{"message": str(exc)}], "warnings": [], "generated_files": [], "custom_files": []}

    try:
        manifest = build_preview_manifest(civ_path)
    except PreviewError as exc:
        return {
            "errors": [{"message": f"无法生成预览（{exc}）；check-conflicts 需要 PyQt6 环境。"}],
            "warnings": [],
            "generated_files": [],
            "custom_files": [],
        }

    all_files = manifest["files"]
    readonly = {path.lower() for path in manifest["readonly_custom_paths"]}
    # 生成 SQL = 非 readonly 的 Data/*.sql；自定义 SQL = readonly 的 Data/*.sql
    # （manifest 里自定义文件是"原样透传"内容，但判别依据是 readonly 标记）
    generated_sql = {
        rel: content
        for rel, content in all_files.items()
        if rel.lower().startswith("data/") and rel.lower().endswith(".sql") and rel.lower() not in readonly
    }
    custom_disk_sql = {
        rel: content
        for rel, content in all_files.items()
        if rel.lower().startswith("data/") and rel.lower().endswith(".sql") and rel.lower() in readonly
    }
    generated_keys: dict[tuple[str, str], str] = {}
    generated_tables: set[str] = set()
    for rel, content in generated_sql.items():
        for table, pk in parse_inserts(content):
            generated_tables.add(table.lower())
            generated_keys.setdefault((table.lower(), pk.casefold()), rel)

    # 自定义 SQL 清单：file_info UpdateDatabase 动作里、非生成清单的 .sql（含磁盘缺失的）
    info = custom_file.file_info(payload)
    in_game = info.get("in_game_actions") if isinstance(info.get("in_game_actions"), list) else []
    action_sql: list[str] = []
    for entry in in_game:
        if not isinstance(entry, dict) or str(entry.get("type") or "") != "UpdateDatabase":
            continue
        for raw in entry.get("files") or []:
            rel = str(raw).replace("\\", "/").strip()
            if rel.lower().endswith(".sql"):
                action_sql.append(rel)

    generated_lower = {rel.lower() for rel in generated_sql}
    custom_files: list[dict[str, Any]] = []
    for rel in sorted(set(action_sql)):
        if rel.lower() in generated_lower:
            continue
        content = custom_disk_sql.get(rel, "")
        if not content:
            disk = root / Path(rel.replace("/", "\\"))
            if disk.exists() and disk.is_file():
                content = custom_file._read_text(root, rel)
        custom_files.append({"path": rel, "on_disk": bool(content), "content": content})

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    custom_keys: dict[tuple[str, str], str] = {}
    for item in custom_files:
        rel = item["path"]
        content = str(item.get("content") or "")
        if not content:
            warnings.append({"file": rel, "message": "UpdateDatabase 动作引用了文件，但磁盘上不存在（未生成/被删除）"})
            continue
        for table, pk in parse_inserts(content):
            key = (table.lower(), pk.casefold())
            if key in custom_keys:
                errors.append({
                    "file": rel,
                    "table": table,
                    "pk": pk,
                    "message": f"自定义 SQL 内部主键重复：{table} {pk}（另见 {custom_keys[key]}）",
                })
            custom_keys[key] = rel
            if key in generated_keys:
                errors.append({
                    "file": rel,
                    "table": table,
                    "pk": pk,
                    "generated_file": generated_keys[key],
                    "message": f"主键与生成 SQL 冲突：{table} {pk}（生成文件 {generated_keys[key]}；"
                               "改 .CIV 对应条目，或在 .CIV 中删除该条目后再自定义）",
                })
        for table in parse_updated_tables(content):
            if table.lower() in generated_tables:
                warnings.append({
                    "file": rel,
                    "table": table,
                    "message": f"自定义 SQL 对生成 SQL 写入的表执行 UPDATE/DELETE（{table}）："
                               "下次生成会覆盖回退——建议回 .CIV 改条目，或用 INSERT OR REPLACE 改写行",
                })

    return {
        "errors": errors,
        "warnings": warnings,
        "generated_files": sorted(generated_sql),
        "custom_files": [{"path": item["path"], "on_disk": item["on_disk"]} for item in custom_files],
    }
