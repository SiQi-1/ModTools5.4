"""query / loc：游戏库只读查询 + 文本库 LOC 查询（AI 知识获取/验证工具）。

- `query`：对 DebugGameplay.sqlite 的安全只读查询。只允许 SELECT/WITH/PRAGMA/EXPLAIN，
  以只读模式打开（mode=ro），任何写语句直接被拒。行数默认上限 50。
- `loc`：把 LOC_xxx 标签解析为简体中文文本（含 {LOC_...} 引用展开），
  数据源为文本库 LocalizedText 表（与 GUI db/interface.py 同约定）。
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .mt_bridge import fetcher_for, loc_text
from .search import resolve_db_paths

# ── query：语句白名单 ──────────────────────────────────────────────
_ALLOWED_FIRST_KEYWORDS = {"select", "with", "pragma", "explain"}
_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create",
    "replace", "attach", "detach", "reindex", "vacuum",
)
_DEFAULT_ROW_LIMIT = 50
_MAX_ROW_LIMIT = 500


class QueryError(ValueError):
    pass


def _split_statements(sql: str) -> list[str]:
    """按分号切分语句（去掉注释与空白），返回非空语句列表。"""
    cleaned = re.sub(r"--[^\n]*", "", sql)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    statements = [part.strip() for part in cleaned.split(";") if part.strip()]
    return statements


def _check_statement(statement: str) -> None:
    first_word_match = re.match(r"[A-Za-z]+", statement.lstrip())
    if not first_word_match:
        raise QueryError("无法识别的 SQL 语句（需以 SELECT/WITH/PRAGMA/EXPLAIN 开头）")
    first_word = first_word_match.group(0).lower()
    if first_word not in _ALLOWED_FIRST_KEYWORDS:
        raise QueryError(
            f"只允许只读查询（SELECT/WITH/PRAGMA/EXPLAIN），拒绝：{first_word.upper()} ..."
        )
    lowered = statement.lower()
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise QueryError(f"语句包含写操作关键字：{keyword.upper()}（只读查询）")
    if first_word == "pragma" and "=" in statement:
        raise QueryError("PRAGMA 只允许只读形式（不允许赋值）")


def open_game_db_readonly(path: Path) -> sqlite3.Connection:
    """以只读模式打开游戏库。"""
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def run_query(conn: sqlite3.Connection, sql: str, limit: int = _DEFAULT_ROW_LIMIT) -> dict[str, Any]:
    """执行单条只读查询，返回 {columns, rows, truncated}。

    - 多条语句（含注释/尾分号）会被拆解并逐一检查，但只执行第一条；
    - rows 至多 limit 行（默认 50，上限 500）。
    """
    statements = _split_statements(sql)
    if not statements:
        raise QueryError("SQL 为空")
    if len(statements) > 1:
        raise QueryError(f"一次只允许一条语句（检测到 {len(statements)} 条）")
    statement = statements[0]
    _check_statement(statement)
    row_limit = max(1, min(int(limit or _DEFAULT_ROW_LIMIT), _MAX_ROW_LIMIT))
    try:
        cursor = conn.execute(statement)
    except sqlite3.Error as exc:
        raise QueryError(f"SQL 执行失败：{exc}") from exc
    columns = [description[0] for description in (cursor.description or [])]
    rows = cursor.fetchmany(row_limit + 1)
    truncated = len(rows) > row_limit
    rows = rows[:row_limit]
    cursor.close()
    return {"columns": columns, "rows": rows, "truncated": truncated}


def _format_value(value: Any) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if len(text) > 80:
        return text[:77] + "..."
    return text


def format_query_result(result: dict[str, Any]) -> str:
    """把查询结果格式化为对齐表格（类 sqlite3 CLI 输出）。"""
    columns = result["columns"]
    rows = result["rows"]
    if not columns:
        return "(无结果列)"
    lines: list[str] = []
    header = " | ".join(columns)
    lines.append(header)
    lines.append("-+-".join("-" * len(name) for name in columns))
    for row in rows:
        lines.append(" | ".join(_format_value(value) for value in row))
    lines.append(f"({len(rows)} 行" + ("，已截断（超出上限）" if result["truncated"] else "") + ")")
    return "\n".join(lines)


def resolve_game_db_path(game_db: str = "") -> Path:
    """解析游戏库路径（参数 > settings.json > 游戏默认 Cache），缺失时报错。"""
    path, _ = resolve_db_paths(game_db, "")
    if path is None:
        raise QueryError(
            "未找到游戏数据库。可指定 --game-db 路径，或确认本机已运行过文明6（生成 Cache/DebugGameplay.sqlite）。"
        )
    return path


def resolve_text_db_path(text_db: str = "") -> Path:
    """解析文本库路径（参数 > settings.json），缺失时报错。"""
    _, path = resolve_db_paths("", text_db)
    if path is None:
        raise QueryError(
            "未找到文本数据库（中文检索/查询需要）。可指定 --text-db 路径，"
            "或在 settings.json 配置 active_text_db_path（发布包自带 local_text_New.sqlite）。"
        )
    return path


# ── loc：LOC 文本查询（嵌套解析统一由 db.loc_text 提供）────────────


def resolve_loc_tag(conn: sqlite3.Connection, tag: str) -> str | None:
    """解析单个 LOC tag（含 {LOC_...} 引用链展开），失败返回 None。

    嵌套展开委托 `ModTools_5_4.db.loc_text`（单一实现，不在 modgen 内另维护一份）。
    """
    if conn is None:
        return None
    return loc_text.resolve_tag(fetcher_for(conn), tag)


def format_loc_results(results: list[tuple[str, str | None]]) -> str:
    lines: list[str] = []
    for tag, text in results:
        if text is None:
            lines.append(f"{tag} -> (未找到 zh_Hans_CN 文本)")
        else:
            lines.append(f"{tag} -> {text}")
    return "\n".join(lines)
