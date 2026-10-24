"""Pure SQL formatting helpers used by output builders."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence


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
    if text.strip().lower() in {"none", "null"}:
        return "NULL"
    return f"'{escape(text)}'"


def sql_value_present(value: object | None) -> bool:
    """Return whether *value* carries data worth writing to an optional column.

    Empty strings (including the historical ``"None"``/``"NULL"`` sentinels)
    are input placeholders, not database values.  Numeric zero and ``False``
    remain meaningful and therefore are retained.  Required columns can be
    preserved separately with :func:`sparse_row`'s ``keep_columns`` argument.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "none", "null"}
    return True


def sparse_row(
    row: Mapping[str, object],
    column_order: Sequence[str],
    *,
    keep_columns: Iterable[str] = (),
) -> tuple[list[str], list[object]]:
    """Select only meaningful values from one row while preserving order.

    ``keep_columns`` is for required semantic columns such as a primary key,
    ``Name`` and ``Description``.  A kept column is emitted even when its
    value is ``None`` so the caller can surface a required-field error rather
    than silently changing the row shape.
    """
    keep = set(keep_columns)
    columns: list[str] = []
    values: list[object] = []
    for column in column_order:
        value = row.get(column)
        if column not in keep and not sql_value_present(value):
            continue
        columns.append(column)
        values.append(value)
    return columns, values


def build_sparse_insert_blocks(
    comment: str,
    table: str,
    rows: Sequence[Mapping[str, object]],
    column_order: Sequence[str],
    *,
    keep_columns: Iterable[str] = (),
    escape: Callable[[str], str] = sql_escape,
) -> str:
    """Render INSERT blocks grouped by each row's meaningful column set.

    SQLite requires every row in a multi-row INSERT to use the same column
    list.  Grouping by the sparse column signature lets rows omit unrelated
    optional values without padding other rows with meaningless ``NULL``
    literals.
    """
    groups: dict[tuple[str, ...], list[str]] = {}
    keep = set(keep_columns)
    for row in rows:
        columns, values = sparse_row(row, column_order, keep_columns=keep)
        if not columns:
            continue
        signature = tuple(columns)
        groups.setdefault(signature, []).append(
            "(" + ", ".join(sql_literal(value, escape) for value in values) + ")"
        )

    blocks: list[str] = []
    for columns, values in groups.items():
        lines = [
            f"-- {comment}",
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES",
            ",\n".join(values) + ";",
            "",
        ]
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


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
