"""Persistent settings storage for ModTools 5.4.

Packaging note:
- When bundled into an .exe, the package directory is not a good place to persist writes.
- Settings are stored under a user-writable directory by default (or next to the exe in portable mode).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

from .config import PACKAGE_ROOT
from .user_paths import is_frozen, settings_file_path
from ..db.paths import DEFAULT_GAME_DB, DEFAULT_TEXT_SOURCE_DB

SETTINGS_FILE = settings_file_path()
SOURCE_SETTINGS_FILE = PACKAGE_ROOT / "data" / "settings.json"


@dataclass(slots=True)
class TextDbEntry:
    name: str
    path: str


@dataclass(slots=True)
class UserSettings:
    game_db_path: str = str(DEFAULT_GAME_DB)
    base_text_source_db_path: str = str(DEFAULT_TEXT_SOURCE_DB)
    text_databases: list[TextDbEntry] = field(default_factory=list)
    active_text_db_path: str = ""


def _default_settings() -> UserSettings:
    return UserSettings()


def _resolve_settings_path(raw_path: object) -> str:
    text = str(raw_path or "").strip()
    if not text:
        return ""
    candidate = Path(text)
    if candidate.is_absolute():
        return str(candidate)
    return str((SETTINGS_FILE.parent / candidate).resolve())


def _load_json_dict(path: Path) -> dict[str, object] | None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def load_settings() -> UserSettings:
    payload: dict[str, object] | None = None

    if SETTINGS_FILE.exists():
        payload = _load_json_dict(SETTINGS_FILE)
    elif (not is_frozen()) and SOURCE_SETTINGS_FILE.exists():
        # Source checkout compatibility: allow loading a repo-shipped settings.json.
        # In bundled mode we intentionally ignore it to avoid developer-specific absolute paths.
        payload = _load_json_dict(SOURCE_SETTINGS_FILE)

    if not isinstance(payload, dict):
        return _default_settings()
    text_dbs_payload = payload.get("text_databases", [])
    text_dbs: list[TextDbEntry] = []
    if isinstance(text_dbs_payload, list):
        for item in text_dbs_payload:
            if isinstance(item, dict):
                name = str(item.get("name") or "未命名文本库")
                path = _resolve_settings_path(item.get("path"))
                if path:
                    text_dbs.append(TextDbEntry(name=name, path=path))

    settings = UserSettings(
        game_db_path=str(payload.get("game_db_path") or DEFAULT_GAME_DB),
        base_text_source_db_path=str(payload.get("base_text_source_db_path") or DEFAULT_TEXT_SOURCE_DB),
        text_databases=text_dbs,
        active_text_db_path=_resolve_settings_path(payload.get("active_text_db_path")),
    )

    if settings.active_text_db_path:
        active = Path(settings.active_text_db_path)
        if active.exists() and all(Path(entry.path) != active for entry in settings.text_databases):
            settings.text_databases.append(TextDbEntry(name=active.stem or "默认文本库", path=str(active)))
    return settings


def save_settings(settings: UserSettings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    SETTINGS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_text_db_entry(settings: UserSettings, db_path: Path, display_name: str | None = None) -> None:
    normalized = str(db_path)
    for entry in settings.text_databases:
        if entry.path == normalized:
            if display_name:
                entry.name = display_name
            return
    settings.text_databases.append(TextDbEntry(name=display_name or db_path.stem, path=normalized))


def set_active_text_db(settings: UserSettings, db_path: Path) -> None:
    settings.active_text_db_path = str(db_path)
