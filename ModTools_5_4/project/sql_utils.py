"""Pure SQL value formatting helpers used by output builders."""
from __future__ import annotations

from collections.abc import Callable


def sql_literal(value: object, escape: Callable[[str], str]) -> str:
    """Return a SQLite literal while preserving the generator's NULL rules.

    ``escape`` is injected by callers because the GUI generator already owns
    the project's string escaping policy. This keeps the helper independent of
    Qt and of ``WorkspacePage``.
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
