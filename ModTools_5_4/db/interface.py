"""Text DB query helpers for UI localization lookups.

我们不直接使用游戏的 DebugLocalization.sqlite，原因：
- DebugGameplay.sqlite 在每次启动游戏时由游戏重新生成，数据始终最新。
- DebugLocalization.sqlite 不同——游戏不会主动维护它，第一次生成后就不再更新。
  随着 DLC 安装和游戏版本更新，该文件会严重过时，缺少大量文本。
- 因此工具维护自己的可写文本库（如 local_text_New.sqlite），从游戏 XML/SQL/DLC
  目录重新导入文本，确保内容完整且可控。
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import re

from ..app.settings_store import load_settings, SETTINGS_FILE


_LOC_TOKEN_PATTERN = re.compile(r"\{\s*(LOC_[^}\s]+)\s*\}", re.IGNORECASE)

# ── 缓存（阶段2）：settings.json 与活动文本库路径按文件 mtime 自动失效，
#    不再每次 LOC 查询都重读磁盘；tag 结果缓存随文本库 mtime 失效。
_SETTINGS_MTIME: float | None = None
_SETTINGS_LOADED = False
_CACHED_ACTIVE_TEXT_DB_PATH: Path | None = None

_TAG_CACHE: dict[str, str | None] = {}
_TAG_CACHE_DB_MTIME: float | None = None


def _invalidate_caches() -> None:
    global _SETTINGS_LOADED, _CACHED_ACTIVE_TEXT_DB_PATH, _TAG_CACHE, _TAG_CACHE_DB_MTIME
    _SETTINGS_LOADED = False
    _CACHED_ACTIVE_TEXT_DB_PATH = None
    _TAG_CACHE = {}
    _TAG_CACHE_DB_MTIME = None


def _active_text_db_path() -> Path | None:
    global _SETTINGS_MTIME, _SETTINGS_LOADED, _CACHED_ACTIVE_TEXT_DB_PATH
    try:
        settings_mtime = SETTINGS_FILE.stat().st_mtime
    except OSError:
        settings_mtime = None
    if settings_mtime != _SETTINGS_MTIME or not _SETTINGS_LOADED:
        _SETTINGS_MTIME = settings_mtime
        _SETTINGS_LOADED = True
        settings = load_settings()
        configured = str(settings.active_text_db_path or "").strip()
        if configured and Path(configured).exists():
            _CACHED_ACTIVE_TEXT_DB_PATH = Path(configured)
        else:
            _CACHED_ACTIVE_TEXT_DB_PATH = None
    return _CACHED_ACTIVE_TEXT_DB_PATH


def get_chinese_text_for_tag(tag: str) -> str | None:
    """Return Simplified Chinese text for a tag from the active text DB."""
    normalized = str(tag or "").strip()
    if not normalized:
        return None

    db_path = _active_text_db_path()
    if db_path is None:
        return None

    # 文本库文件变化（重新导入/替换）时清空 tag 缓存
    global _TAG_CACHE, _TAG_CACHE_DB_MTIME
    try:
        db_mtime = db_path.stat().st_mtime
    except OSError:
        db_mtime = None
    if db_mtime != _TAG_CACHE_DB_MTIME:
        _TAG_CACHE = {}
        _TAG_CACHE_DB_MTIME = db_mtime

    if normalized in _TAG_CACHE:
        return _TAG_CACHE[normalized]

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT Text FROM LocalizedText WHERE Tag = ? AND lower(Language) = ? LIMIT 1",
            (normalized, "zh_hans_cn"),
        ).fetchone()
        if row is None:
            _TAG_CACHE[normalized] = None
            return None
        result = str(row[0] or "").strip() or None
        _TAG_CACHE[normalized] = result
        return result
    except sqlite3.Error:
        _TAG_CACHE[normalized] = None
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
