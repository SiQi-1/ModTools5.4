"""Text DB query helpers for UI localization lookups."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import re

from ..app.settings_store import load_settings


_LOC_TOKEN_PATTERN = re.compile(r"\{\s*(LOC_[^}\s]+)\s*\}", re.IGNORECASE)


def _active_text_db_path() -> Path | None:
    settings = load_settings()
    if not settings.active_text_db_path:
        return None
    path = Path(settings.active_text_db_path)
    if not path.exists():
        return None
    return path


def get_chinese_text_for_tag(tag: str) -> str | None:
    """Return Simplified Chinese text for a tag from the active text DB."""
    normalized = str(tag or "").strip()
    if not normalized:
        return None

    db_path = _active_text_db_path()
    if db_path is None:
        return None

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT Text FROM LocalizedText WHERE Tag = ? AND lower(Language) = ? LIMIT 1",
            (normalized, "zh_hans_cn"),
        ).fetchone()
        if row is None:
            return None
        return str(row[0] or "").strip() or None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _resolve_value_or_unknown(
    value: str,
    *,
    unknown_text: str,
    visited: set[str],
    depth: int,
    max_depth: int,
) -> str:
    text = str(value or "").strip()
    if not text:
        return unknown_text
    if depth > max_depth:
        return unknown_text

    upper = text.upper()
    if upper.startswith("LOC_"):
        return _resolve_tag_or_unknown(
            text,
            unknown_text=unknown_text,
            visited=visited,
            depth=depth + 1,
            max_depth=max_depth,
        )

    if _LOC_TOKEN_PATTERN.search(text):
        def repl(match: re.Match[str]) -> str:
            ref_tag = str(match.group(1) or "").strip()
            if not ref_tag:
                return unknown_text
            return _resolve_tag_or_unknown(
                ref_tag,
                unknown_text=unknown_text,
                visited=visited,
                depth=depth + 1,
                max_depth=max_depth,
            )

        replaced = _LOC_TOKEN_PATTERN.sub(repl, text).strip()
        if not replaced:
            return unknown_text
        if replaced.upper().startswith("LOC_") or _LOC_TOKEN_PATTERN.search(replaced):
            return _resolve_value_or_unknown(
                replaced,
                unknown_text=unknown_text,
                visited=visited,
                depth=depth + 1,
                max_depth=max_depth,
            )
        return replaced

    return text


def _resolve_tag_or_unknown(
    tag: str,
    *,
    unknown_text: str,
    visited: set[str],
    depth: int,
    max_depth: int,
) -> str:
    normalized = str(tag or "").strip()
    if not normalized:
        return unknown_text
    key = normalized.upper()
    if key in visited:
        return unknown_text
    if depth > max_depth:
        return unknown_text

    visited.add(key)
    resolved = get_chinese_text_for_tag(normalized)
    if not resolved:
        return unknown_text
    return _resolve_value_or_unknown(
        resolved,
        unknown_text=unknown_text,
        visited=visited,
        depth=depth + 1,
        max_depth=max_depth,
    )


def get_chinese_text_for_tag_or_unknown(tag: str, unknown_text: str = "未知") -> str:
    """Return zh text for tag, fallback to `unknown_text` when unresolved/LOC placeholder."""
    return _resolve_tag_or_unknown(
        tag,
        unknown_text=unknown_text,
        visited=set(),
        depth=0,
        max_depth=12,
    )


def resolve_chinese_text_or_unknown(value: str, unknown_text: str = "未知") -> str:
    """Resolve plain text that may contain nested LOC references; fallback to unknown."""
    return _resolve_value_or_unknown(
        value,
        unknown_text=unknown_text,
        visited=set(),
        depth=0,
        max_depth=12,
    )
