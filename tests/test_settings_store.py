"""Unit tests for persistent settings (settings_store) roundtrip.

Uses a temp settings file so the repo/portable settings are never touched.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ModTools_5_4.app import settings_store
from ModTools_5_4.app.settings_store import (
    UserSettings,
    ensure_text_db_entry,
    load_settings,
    save_settings,
    set_active_text_db,
)


class SettingsStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._original = settings_store.SETTINGS_FILE
        self._original_source = settings_store.SOURCE_SETTINGS_FILE
        settings_store.SETTINGS_FILE = Path(self._tmp.name) / "settings.json"
        settings_store.SOURCE_SETTINGS_FILE = Path(self._tmp.name) / "no_source.json"
        # Pre-create the file so load_settings does not fall back to the
        # repo-shipped data/settings.json (which contains real local paths).
        settings_store.SETTINGS_FILE.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        settings_store.SETTINGS_FILE = self._original
        settings_store.SOURCE_SETTINGS_FILE = self._original_source
        self._tmp.cleanup()

    def test_defaults_with_empty_file(self) -> None:
        settings = load_settings()
        self.assertEqual(settings.text_databases, [])
        self.assertEqual(settings.active_text_db_path, "")

    def test_save_load_roundtrip(self) -> None:
        settings = UserSettings()
        db = Path("D:/fake/text_db.sqlite")
        ensure_text_db_entry(settings, db, "测试库")
        set_active_text_db(settings, db)
        save_settings(settings)

        loaded = load_settings()
        self.assertEqual(len(loaded.text_databases), 1)
        self.assertEqual(loaded.text_databases[0].name, "测试库")
        self.assertEqual(Path(loaded.text_databases[0].path).name, "text_db.sqlite")
        self.assertEqual(Path(loaded.active_text_db_path).name, "text_db.sqlite")

    def test_ensure_entry_is_idempotent(self) -> None:
        settings = UserSettings()
        db = Path("D:/fake/text_db.sqlite")
        ensure_text_db_entry(settings, db, "库A")
        ensure_text_db_entry(settings, db, "库B")
        self.assertEqual(len(settings.text_databases), 1)
        self.assertEqual(settings.text_databases[0].name, "库B")

    def test_missing_file_returns_defaults(self) -> None:
        settings_store.SETTINGS_FILE = Path(self._tmp.name) / "does_not_exist.json"
        settings = load_settings()
        self.assertEqual(settings.text_databases, [])


if __name__ == "__main__":
    unittest.main()
