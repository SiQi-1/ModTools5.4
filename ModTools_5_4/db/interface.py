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

from ..app.settings_store import load_settings, SETTINGS_FILE
from . import loc_text


# 嵌套引用展开的最大层数（统一实现见 db.loc_text）
_MAX_REF_DEPTH = 12

# 兼容旧引用：本模块历史上自带一份 token 正则，现统一取自 db.loc_text（单一实现）
_LOC_TOKEN_PATTERN = loc_text.LOC_REF_PATTERN

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
    depth: int = 0,
    max_depth: int = _MAX_REF_DEPTH,
) -> str:
    """解析可能含嵌套引用/纯文本的值（嵌套展开统一委托 db.loc_text）；失败返回 unknown_text。"""
    text = str(value or "").strip()
    if not text or depth > max_depth:
        return unknown_text

    if text.upper().startswith("LOC_"):
        return _resolve_tag_or_unknown(
            text, unknown_text=unknown_text, depth=depth + 1, max_depth=max_depth
        )

    if not loc_text.contains_ref(text):
        return text

    replaced = loc_text.resolve_text(get_chinese_text_for_tag, text, max_depth=max_depth).strip()
    if not replaced:
        return unknown_text
    return _finalize_resolved_text(
        replaced, unknown_text=unknown_text, depth=depth + 1, max_depth=max_depth
    )


def _resolve_tag_or_unknown(
    tag: str,
    *,
    unknown_text: str,
    depth: int = 0,
    max_depth: int = _MAX_REF_DEPTH,
) -> str:
    normalized = str(tag or "").strip()
    if not normalized or depth > max_depth:
        return unknown_text

    resolved = loc_text.resolve_tag(get_chinese_text_for_tag, normalized, max_depth=max_depth)
    if not resolved:
        return unknown_text
    return _finalize_resolved_text(
        resolved, unknown_text=unknown_text, depth=depth + 1, max_depth=max_depth
    )


def _finalize_resolved_text(
    text: str,
    *,
    unknown_text: str,
    depth: int,
    max_depth: int,
) -> str:
    """收尾：残留未解析引用 → unknown_text；结果仍是引用形式 → 继续解析（防环）。"""
    if depth > max_depth:
        return unknown_text
    if loc_text.contains_ref(text):
        text = loc_text.LOC_REF_PATTERN.sub(unknown_text, text).strip()
        if not text:
            return unknown_text
    if text.upper().startswith("LOC_"):
        return _resolve_tag_or_unknown(
            text, unknown_text=unknown_text, depth=depth + 1, max_depth=max_depth
        )
    return text or unknown_text


def get_chinese_text_for_tag_or_unknown(tag: str, unknown_text: str = "未知") -> str:
    """Return zh text for tag, fallback to `unknown_text` when unresolved/LOC placeholder."""
    return _resolve_tag_or_unknown(
        tag,
        unknown_text=unknown_text,
        depth=0,
        max_depth=_MAX_REF_DEPTH,
    )


def resolve_chinese_text_or_unknown(value: str, unknown_text: str = "未知") -> str:
    """Resolve plain text that may contain nested LOC references; fallback to unknown."""
    return _resolve_value_or_unknown(
        value,
        unknown_text=unknown_text,
        depth=0,
        max_depth=_MAX_REF_DEPTH,
    )
