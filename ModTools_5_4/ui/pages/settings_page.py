"""Settings page for game/text database configuration and imports."""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QComboBox,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage
from ...app.settings_store import (
    UserSettings,
    ensure_text_db_entry,
    load_settings,
    save_settings,
    set_active_text_db,
)
from ...db.text_database import (
    create_local_text_database_from_source,
    import_parsed_bundle,
    load_conflicts_against_db,
    parse_import_files,
    resolve_modinfo_text_files,
)
from ..dialogs.conflict_file_dialog import ConflictFileDialog


LOGGER = logging.getLogger(__name__)


class SettingsPage(BasePage):
    """Database settings and text import operations."""

    page_id = "settings"
    display_name = "设置"

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settingsPage")
        self._settings: UserSettings = load_settings()

        self._game_db_input = QLineEdit()
        self._base_text_source_input = QLineEdit()
        self._text_db_combo = QComboBox()

        self._import_dlc_btn = QPushButton("导入DLC")
        self._import_text_file_btn = QPushButton("导入文本文件")
        self._import_modinfo_btn = QPushButton("导入.modinfo")
        self._import_folder_btn = QPushButton("导入文件夹")

        self._status_label = QLabel("")
        self._status_label.setObjectName("settingsStatusLabel")
        self._status_label.setWordWrap(True)

        self._build_ui()
        self._bind_events()
        self._load_settings_into_ui()
        self._refresh_import_buttons_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setAlignment(Qt.AlignmentFlag.AlignTop)
        root.setSpacing(12)
        root.setContentsMargins(14, 12, 14, 12)

        header = QLabel("数据库设置")
        header.setObjectName("pageHeaderLabel")
        root.addWidget(header)

        subtitle = QLabel("配置数据库路径与文本导入来源。以下仅调整界面布局，不影响现有功能逻辑。")
        subtitle.setObjectName("settingsSubtitleLabel")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        db_row = QHBoxLayout()
        db_row.setSpacing(12)
        db_row.addWidget(self._build_game_db_group(), 1)
        db_row.addWidget(self._build_text_db_group(), 1)
        root.addLayout(db_row)

        root.addWidget(self._build_import_group())
        root.addWidget(self._status_label)
        root.addStretch(1)
        self.setLayout(root)

    def _build_game_db_group(self) -> QGroupBox:
        group = QGroupBox("游戏数据库（外部链接）")
        group.setObjectName("settingsCard")
        form = QFormLayout()
        form.setSpacing(10)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._choose_game_db)

        row = QHBoxLayout()
        row.addWidget(self._game_db_input)
        row.addWidget(browse_btn)
        row_widget = QWidget()
        row_widget.setLayout(row)
        form.addRow("游戏数据库", row_widget)

        save_btn = QPushButton("保存游戏数据库配置")
        save_btn.clicked.connect(self._save_game_db)
        form.addRow("", save_btn)

        group.setLayout(form)
        return group

    def _build_text_db_group(self) -> QGroupBox:
        group = QGroupBox("文本数据库（本地可配置多库）")
        group.setObjectName("settingsCard")
        form = QFormLayout()
        form.setSpacing(10)

        self._text_db_combo.setMinimumWidth(320)
        form.addRow("当前文本数据库", self._text_db_combo)

        add_existing_btn = QPushButton("添加已有文本数据库")
        add_existing_btn.clicked.connect(self._add_existing_text_db)

        create_new_btn = QPushButton("新建文本数据库（复制基础中文）")
        create_new_btn.clicked.connect(self._create_new_text_db)

        row_actions = QHBoxLayout()
        row_actions.addWidget(add_existing_btn)
        row_actions.addWidget(create_new_btn)
        action_widget = QWidget()
        action_widget.setLayout(row_actions)
        form.addRow("", action_widget)

        base_browse_btn = QPushButton("浏览")
        base_browse_btn.clicked.connect(self._choose_base_text_source)
        row_base = QHBoxLayout()
        row_base.addWidget(self._base_text_source_input)
        row_base.addWidget(base_browse_btn)
        base_widget = QWidget()
        base_widget.setLayout(row_base)
        form.addRow("基础文本数据库", base_widget)

        group.setLayout(form)
        return group

    def _build_import_group(self) -> QGroupBox:
        group = QGroupBox("导入文本到当前文本数据库")
        group.setObjectName("settingsCard")

        layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()

        row1.addWidget(self._import_dlc_btn)
        row1.addWidget(self._import_text_file_btn)
        row2.addWidget(self._import_modinfo_btn)
        row2.addWidget(self._import_folder_btn)

        layout.addLayout(row1)
        layout.addLayout(row2)

        hint = QLabel("导入操作会写入当前选中的文本数据库。")
        hint.setObjectName("settingsHintLabel")
        layout.addWidget(hint)

        group.setLayout(layout)
        return group

    def _bind_events(self) -> None:
        self._text_db_combo.currentIndexChanged.connect(self._handle_text_db_changed)
        self._import_dlc_btn.clicked.connect(self._import_dlc)
        self._import_text_file_btn.clicked.connect(self._import_text_file)
        self._import_modinfo_btn.clicked.connect(self._import_modinfo)
        self._import_folder_btn.clicked.connect(self._import_folder)

    def _load_settings_into_ui(self) -> None:
        self._game_db_input.setText(self._settings.game_db_path)
        self._base_text_source_input.setText(self._settings.base_text_source_db_path)

        self._text_db_combo.blockSignals(True)
        self._text_db_combo.clear()
        for entry in self._settings.text_databases:
            self._text_db_combo.addItem(f"{entry.name} | {entry.path}", entry.path)

        if self._settings.active_text_db_path:
            for index in range(self._text_db_combo.count()):
                if self._text_db_combo.itemData(index) == self._settings.active_text_db_path:
                    self._text_db_combo.setCurrentIndex(index)
                    break
        self._text_db_combo.blockSignals(False)

    def _choose_game_db(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "选择游戏数据库", self._game_db_input.text(), "SQLite (*.sqlite *.db);;All Files (*)")
        if selected:
            self._game_db_input.setText(selected)

    def _save_game_db(self) -> None:
        self._settings.game_db_path = self._game_db_input.text().strip()
        save_settings(self._settings)
        self._status_label.setText("已保存游戏数据库配置。")

    def _choose_base_text_source(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择基础文本数据库",
            self._base_text_source_input.text(),
            "SQLite (*.sqlite *.db);;All Files (*)",
        )
        if selected:
            self._base_text_source_input.setText(selected)
            self._settings.base_text_source_db_path = selected
            save_settings(self._settings)

    def _add_existing_text_db(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "添加文本数据库", "", "SQLite (*.sqlite *.db);;All Files (*)")
        if not selected:
            return

        db_path = Path(selected)
        ensure_text_db_entry(self._settings, db_path, db_path.stem)
        set_active_text_db(self._settings, db_path)
        save_settings(self._settings)
        self._load_settings_into_ui()
        self._refresh_import_buttons_state()
        self._status_label.setText(f"已添加文本数据库: {db_path.name}")

    def _create_new_text_db(self) -> None:
        source = Path(self._base_text_source_input.text().strip())
        if not source.exists():
            QMessageBox.warning(self, "基础文本缺失", "基础文本数据库路径无效，请先设置。")
            return

        selected, _ = QFileDialog.getSaveFileName(self, "新建文本数据库", "local_text.sqlite", "SQLite (*.sqlite)")
        if not selected:
            return

        target = Path(selected)
        if target.suffix.lower() != ".sqlite":
            target = target.with_suffix(".sqlite")

        try:
            copied = create_local_text_database_from_source(source, target)
        except Exception as exc:
            QMessageBox.critical(self, "创建失败", str(exc))
            return

        ensure_text_db_entry(self._settings, target, target.stem)
        set_active_text_db(self._settings, target)
        self._settings.base_text_source_db_path = str(source)
        save_settings(self._settings)

        self._load_settings_into_ui()
        self._refresh_import_buttons_state()
        self._status_label.setText(f"已创建文本数据库: {target.name}（复制中文 {copied} 条）")

    def _handle_text_db_changed(self) -> None:
        db_path = self._current_text_db_path()
        if db_path is None:
            self._settings.active_text_db_path = ""
        else:
            set_active_text_db(self._settings, db_path)
        save_settings(self._settings)
        self._refresh_import_buttons_state()

    def _refresh_import_buttons_state(self) -> None:
        has_db = self._current_text_db_path() is not None
        tooltip = "请选择当前文本数据库后才可导入" if not has_db else ""
        for btn in (self._import_dlc_btn, self._import_text_file_btn, self._import_modinfo_btn, self._import_folder_btn):
            btn.setEnabled(has_db)
            btn.setToolTip(tooltip)

    def _current_text_db_path(self) -> Path | None:
        if self._text_db_combo.currentIndex() < 0:
            return None
        path = self._text_db_combo.currentData()
        if not isinstance(path, str) or not path:
            return None
        return Path(path)

    def _import_dlc(self) -> None:
        db_path = self._current_text_db_path()
        if db_path is None:
            return

        start_dir = self._detect_default_dlc_path()
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择DLC根目录",
            str(start_dir) if start_dir is not None else "",
        )
        if not folder:
            return

        self._run_import(db_path, importer="dlc", source=Path(folder))

    def _detect_default_dlc_path(self) -> Path | None:
        """Try to find a default Civ6 DLC folder under SteamLibrary locations."""
        relative = Path("steamapps") / "common" / "Sid Meier's Civilization VI" / "DLC"

        candidates: list[Path] = []
        for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            candidates.append(Path(f"{drive}:/SteamLibrary") / relative)

        unique_candidates: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            unique_candidates.append(path)

        for path in unique_candidates:
            if path.exists() and path.is_dir():
                return path
        return None

    def _import_text_file(self) -> None:
        db_path = self._current_text_db_path()
        if db_path is None:
            return

        files, _ = QFileDialog.getOpenFileNames(self, "选择文本文件", "", "Text Files (*.xml *.sql)")
        if not files:
            return

        self._run_import(db_path, importer="files", source=[Path(item) for item in files])

    def _import_modinfo(self) -> None:
        db_path = self._current_text_db_path()
        if db_path is None:
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "选择.modinfo文件", "", "Modinfo (*.modinfo *.xml)")
        if not file_path:
            return

        self._run_import(db_path, importer="modinfo", source=Path(file_path))

    def _import_folder(self) -> None:
        db_path = self._current_text_db_path()
        if db_path is None:
            return

        folder = QFileDialog.getExistingDirectory(self, "选择导入文件夹")
        if not folder:
            return

        self._run_import(db_path, importer="folder", source=Path(folder))

    def _run_import(self, db_path: Path, importer: str, source) -> None:
        try:
            parsed_files: list[Path]
            if importer == "files":
                parsed_files = [path for path in source if isinstance(path, Path)]
            elif importer == "dlc":
                parsed_files = [
                    path
                    for path in source.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".xml", ".sql"} and any(part.lower() == "text" for part in path.parts)
                ]
            elif importer == "folder":
                parsed_files = [path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in {".xml", ".sql"}]
            elif importer == "modinfo":
                parsed_files = resolve_modinfo_text_files(source)
            else:
                parsed_files = []

            if not parsed_files:
                self._status_label.setText("未找到可导入的文本文件（仅支持 .xml / .sql）。")
                return

            bundle = parse_import_files(parsed_files)
            db_conflicts = load_conflicts_against_db(db_path, bundle.records)
            combined_files = {file for info in bundle.conflict_infos for file in info.source_files}
            combined_files.update({file for info in db_conflicts for file in info.source_files})
            selected_files: set[Path] | None = None
            if combined_files:
                unique_conflict_files = sorted(combined_files, key=lambda p: str(p))
                dialog = ConflictFileDialog(unique_conflict_files, parent=self)
                if dialog.exec() == QDialog.DialogCode.Rejected:
                    self._status_label.setText("已取消导入。")
                    return
                selected_files = dialog.selected_files()

            result = import_parsed_bundle(db_path, bundle, selected_files)

            self._status_label.setText(
                f"导入完成：文件 {result.parsed_file_count}，新增 {result.inserted_count}，覆盖 {result.updated_count}，忽略冲突 {result.ignored_conflict_count}。"
            )
        except Exception as exc:
            LOGGER.exception("Text import failed: importer=%s source=%s", importer, source)
            QMessageBox.critical(self, "导入失败", str(exc))
            self._status_label.setText("导入失败，请查看日志。")
