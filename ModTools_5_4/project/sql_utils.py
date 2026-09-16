"""Pure SQL formatting helpers used by output builders."""
from __future__ import annotations

from collections.abc import Callable


def sql_escape(value: object | None) -> str:
    """Escape text without adding enclosing SQL quotes."""
    return str(value or "").replace("'", "''")


def sql_literal(value: object, escape: Callable[[str], str] = sql_escape) -> str:
    """Return a SQLite literal while preserving the generator's NULL rules.

    The default escape policy matches the GUI generator. Callers may inject
    an alternate policy without depending on Qt or ``WorkspacePage``.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".15g")
    text = str(value)
    if not text.strip():
        return "NULL"
    if text.strip().lower() == "none":
        return "NULL"
    return f"'{escape(text)}'"


def deduplicate_rows(rows: list[str]) -> list[str]:
    """Remove duplicate rows while retaining their first-seen order."""
    seen: set[str] = set()
    output: list[str] = []
    for row in rows:
        if row in seen:
            continue
        seen.add(row)
        output.append(row)
    return output


def build_insert_block(comment: str, table: str, columns: list[str], rows: list[str]) -> str:
    """Render preformatted SQL rows; an empty list produces no block."""
    if not rows:
        return ""
    lines = [
        f"-- {comment}",
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES",
        ",\n".join(rows) + ";",
        "",
    ]
    return "\n".join(lines)
