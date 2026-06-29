"""基础信息工作区：全局参数 + .civ6proj 基础配置。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

LANGUAGE_OPTIONS = [
    "简体中文",
    "简体中文，英文",
    "简体中文，英文，繁体中文",
]

ACTION_TYPE_OPTIONS = [
    "UpdateDatabase",
    "UpdateText",
    "UpdateIcons",
    "UpdateColors",
    "UpdateArt",
    "AddGameplayScripts",
    "AddUserInterfaces",
    "UpdateAudio",
    "ImportFiles",
]

DEFAULT_GAMEPLAY_LUA_TEMPLATE = "\n".join(
    [
        "function Initialize()",
        "end",
        "",
        "Events.LoadGameViewStateDone.Add(Initialize)",
        "",
    ]
)

DEFAULT_UI_XML_TEMPLATE = "\n".join(
    [
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
        "<Context></Context>",
        "",
    ]
)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _safe_text(value: str | None) -> str:
    return (value or "").strip()


def _parse_int(value: object, default: int = 0) -> int:
    text = _safe_text("" if value is None else str(value))
    if not text:
        return default
    try:
        parsed = int(text)
    except ValueError:
        return default
    return max(0, parsed)


def _bool_from_text(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    text = _safe_text("" if value is None else str(value)).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return default


def _text_from_bool(value: bool) -> str:
    return "true" if value else "false"


def _find_first_child(parent: ET.Element, name: str) -> ET.Element | None:
    for child in list(parent):
        if _local_name(child.tag) == name:
            return child
    return None


def _find_all_children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local_name(child.tag) == name]


def _child_text(parent: ET.Element, name: str, default: str = "") -> str:
    child = _find_first_child(parent, name)
    if child is None:
        return default
    return _safe_text(child.text) or default


def _resolve_loc_text(localized_text_data: str, loc_id: str) -> str:
    if not _safe_text(localized_text_data):
        return loc_id
    try:
        root = ET.fromstring(localized_text_data.strip())
    except ET.ParseError:
        return loc_id

    preferred_languages = ["zh_Hans_CN", "zh_Hans", "zh_CN", "en_US"]
    for text_node in root.findall(".//*"):
        if _local_name(text_node.tag) != "Text":
            continue
        if _safe_text(text_node.attrib.get("id")) != loc_id:
            continue

        by_language: dict[str, str] = {}
        for lang_node in list(text_node):
            language = _local_name(lang_node.tag)
            content = _safe_text(lang_node.text)
            if content:
                by_language[language] = content

        for language in preferred_languages:
            if language in by_language:
                return by_language[language]

        for content in by_language.values():
            if content:
                return content

    return loc_id


def _parse_action_data(raw_xml: str) -> list[dict[str, object]]:
    xml_text = _safe_text(raw_xml)
    if not xml_text:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    entries: list[dict[str, object]] = []
    for action_node in list(root):
        action_type = _local_name(action_node.tag)
        action_id = _safe_text(action_node.attrib.get("id"))

        properties_node = _find_first_child(action_node, "Properties")
        load_order = 0
        if properties_node is not None:
            load_order = _parse_int(_child_text(properties_node, "LoadOrder", "0"), default=0)

        files: list[str] = []
        for file_node in _find_all_children(action_node, "File"):
            file_text = _safe_text(file_node.text)
            if file_text:
                files.append(file_text)

        entries.append(
            {
                "type": action_type,
                "id": action_id,
                "files": files,
                "load_order": load_order,
            }
        )

    return entries


class _UpdateDatabaseCreateDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("创建 UpdateDatabase 文件")
        root = QVBoxLayout(self)

        self._sql_radio = QRadioButton("SQL")
        self._xml_radio = QRadioButton("XML")
        self._sql_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self._sql_radio)
        group.addButton(self._xml_radio)

        row = QHBoxLayout()
        row.addWidget(self._sql_radio)
        row.addWidget(self._xml_radio)
        row.addStretch(1)
        root.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def selected_ext(self) -> str:
        return "xml" if self._xml_radio.isChecked() else "sql"


class _SelectFilesDialog(QDialog):
    def __init__(self, *, title: str, files: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 520)

        tip = QLabel("勾选要加入当前加载组的文件（仅显示未被加载的文件）。")
        tip.setWordWrap(True)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for rel_path in sorted(set(files), key=lambda item: item.lower()):
            item = QListWidgetItem(rel_path)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list.addItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(tip)
        root.addWidget(self._list, 1)
        root.addWidget(buttons)

    def selected_files(self) -> list[str]:
        selected: list[str] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selected.append(str(item.text() or "").strip())
        return [item for item in selected if item]


class _ActionColumnEditor(QWidget):
    def __init__(
        self,
        title: str,
        file_basename_provider=None,
        *,
        allow_create_file: bool = True,
        disallowed_types: set[str] | None = None,
        duplicate_paths_provider=None,
        selectable_files_provider=None,
        delete_file_request_callback=None,
        file_exists_provider=None,
    ) -> None:
        super().__init__()
        self._entries: list[dict[str, object]] = []
        self._is_updating = False
        self._file_basename_provider = file_basename_provider
        self._allow_create_file = allow_create_file
        self._disallowed_types = set(disallowed_types or set())
        self._duplicate_paths_provider = duplicate_paths_provider
        self._selectable_files_provider = selectable_files_provider
        self._delete_file_request_callback = delete_file_request_callback
        self._file_exists_provider = file_exists_provider

        action_type_options = [item for item in ACTION_TYPE_OPTIONS if item not in self._disallowed_types]
        if not action_type_options:
            action_type_options = ["UpdateDatabase"]
        self._action_type_options = action_type_options

        self._title = QLabel(title)
        self._title.setObjectName("pageHeaderLabel")

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._handle_current_changed)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._add_button = QPushButton("新增")
        self._add_button.clicked.connect(self._handle_add)
        self._remove_button = QPushButton("删除")
        self._remove_button.clicked.connect(self._handle_remove)

        list_buttons = QHBoxLayout()
        list_buttons.addWidget(self._add_button)
        list_buttons.addWidget(self._remove_button)
        list_buttons.addStretch(1)

        self._type_combo = QComboBox()
        self._type_combo.setEditable(True)
        self._type_combo.addItems(self._action_type_options)
        self._type_combo.currentTextChanged.connect(self._update_current_entry)

        self._id_edit = QLineEdit()
        self._id_edit.textChanged.connect(self._update_current_entry)

        self._load_order_spin = QSpinBox()
        self._load_order_spin.setRange(0, 2_000_000_000)
        self._load_order_spin.valueChanged.connect(self._update_current_entry)

        self._files_list = QListWidget()
        self._files_list.currentRowChanged.connect(self._refresh_file_buttons)
        self._files_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._create_file_button = QPushButton("创建文件")
        self._create_file_button.clicked.connect(self._handle_create_file)
        self._create_file_button.setVisible(False)

        self._choose_file_button = QPushButton("选择文件")
        self._choose_file_button.clicked.connect(self._handle_choose_file)
        self._choose_file_button.setVisible(False)

        self._remove_from_group_button = QPushButton("从此加载组删除")
        self._remove_from_group_button.clicked.connect(self._handle_remove_from_group)
        self._remove_from_group_button.setVisible(False)

        self._delete_file_button = QPushButton("删除选中文件")
        self._delete_file_button.clicked.connect(self._handle_delete_selected_file)
        self._delete_file_button.setVisible(False)

        file_buttons = QHBoxLayout()
        file_buttons.addWidget(self._choose_file_button)
        file_buttons.addWidget(self._create_file_button)
        file_buttons.addWidget(self._remove_from_group_button)
        file_buttons.addWidget(self._delete_file_button)
        file_buttons.addStretch(1)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow("加载类型", self._type_combo)
        form_layout.addRow("加载id", self._id_edit)
        form_layout.addRow("加载顺序", self._load_order_spin)
        form_layout.addRow("文件列表", self._files_list)
        form_layout.addRow("", file_buttons)

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(self._title)
        main_layout.addWidget(self._list)
        main_layout.addLayout(list_buttons)
        main_layout.addLayout(form_layout)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

        self._set_editor_enabled(False)
        self._recalculate_heights()

    def entries(self) -> list[dict[str, object]]:
        return deepcopy(self._entries)

    def set_entries(self, entries: list[dict[str, object]]) -> None:
        self._entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            normalized_type = _safe_text(str(entry.get("type", "UpdateDatabase")))
            if normalized_type in self._disallowed_types:
                continue

            raw_files = entry.get("files", [])
            if isinstance(raw_files, str):
                files_source = [raw_files]
            elif isinstance(raw_files, list):
                files_source = raw_files
            else:
                files_source = []

            files = [
                _safe_text(str(item))
                for item in files_source
                if _safe_text(str(item))
            ]
            origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
            normalized_origins = {path: _safe_text(str(origins.get(path) or "imported")) for path in files}

            self._entries.append(
                {
                    "type": normalized_type,
                    "id": _safe_text(str(entry.get("id", "NewAction"))),
                    "files": files,
                    "load_order": _parse_int(entry.get("load_order", 0), default=0),
                    "file_origins": normalized_origins,
                }
            )
        self._rebuild_list()

    def _set_editor_enabled(self, enabled: bool) -> None:
        self._type_combo.setEnabled(enabled)
        self._id_edit.setEnabled(enabled)
        self._load_order_spin.setEnabled(enabled)
        self._files_list.setEnabled(enabled)
        self._remove_button.setEnabled(enabled)
        self._choose_file_button.setEnabled(enabled)
        self._create_file_button.setEnabled(enabled)
        self._remove_from_group_button.setEnabled(False)
        self._delete_file_button.setEnabled(False)

    def _rebuild_list(self) -> None:
        self._list.clear()
        for index, entry in enumerate(self._entries, start=1):
            item = QListWidgetItem(self._entry_label(entry, index))
            self._list.addItem(item)

        if self._entries:
            self._list.setCurrentRow(0)
        else:
            self._set_editor_enabled(False)
            self._is_updating = True
            self._type_combo.setCurrentText(self._action_type_options[0])
            self._id_edit.setText("")
            self._load_order_spin.setValue(0)
            self._files_list.clear()
            self._is_updating = False
        self._recalculate_heights()

    def _entry_label(self, entry: dict[str, object], index: int) -> str:
        action_type = _safe_text(str(entry.get("type") or "")) or "(未设置类型)"
        action_id = _safe_text(str(entry.get("id") or "")) or f"Action_{index}"
        return f"{action_type} / {action_id}"

    def _handle_add(self) -> None:
        self._entries.append(
            {
                "type": "UpdateDatabase",
                "id": "NewAction",
                "files": [],
                "load_order": 0,
                "file_origins": {},
            }
        )
        self._rebuild_list()
        self._list.setCurrentRow(len(self._entries) - 1)
        self._recalculate_heights()

    def _handle_remove(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        self._entries.pop(row)
        self._rebuild_list()
        self._recalculate_heights()

    def _handle_current_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._entries):
            self._set_editor_enabled(False)
            self._recalculate_heights()
            return

        entry = self._entries[row]
        self._is_updating = True
        self._type_combo.setCurrentText(_safe_text(str(entry.get("type") or "UpdateDatabase")))
        self._id_edit.setText(_safe_text(str(entry.get("id") or "")))
        self._load_order_spin.setValue(_parse_int(entry.get("load_order", 0), default=0))
        files = [str(item) for item in entry.get("files", []) if _safe_text(str(item))]
        self._rebuild_files_list(files)
        self._is_updating = False
        self._set_editor_enabled(True)
        self._refresh_create_file_button()
        self._refresh_file_buttons()
        self._recalculate_heights()

    def _update_current_entry(self) -> None:
        if self._is_updating:
            return
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return

        files = [
            _safe_text(str(self._files_list.item(i).text()))
            for i in range(self._files_list.count())
            if _safe_text(str(self._files_list.item(i).text()))
        ]

        entry = self._entries[row]
        entry["type"] = _safe_text(self._type_combo.currentText())
        entry["id"] = _safe_text(self._id_edit.text())
        entry["load_order"] = int(self._load_order_spin.value())
        entry["files"] = files
        origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
        entry["file_origins"] = {path: _safe_text(str(origins.get(path) or "imported")) for path in files}

        self._rebuild_files_list(files)

        item = self._list.item(row)
        if item is not None:
            item.setText(self._entry_label(entry, row + 1))
        self._refresh_create_file_button()
        self._refresh_file_buttons()
        self._recalculate_heights()

    def _supports_create_file_for_current_type(self) -> bool:
        if not self._allow_create_file:
            return False
        action_type = _safe_text(self._type_combo.currentText())
        return action_type in {"AddGameplayScripts", "AddUserInterfaces", "ImportFiles", "UpdateDatabase"}

    def _refresh_create_file_button(self) -> None:
        row = self._list.currentRow()
        has_selection = 0 <= row < len(self._entries)
        choose_show = has_selection and self._supports_select_file_for_current_type()
        create_show = has_selection and self._supports_create_file_for_current_type()
        self._choose_file_button.setVisible(choose_show)
        self._create_file_button.setVisible(create_show)
        self._remove_from_group_button.setVisible(has_selection)
        self._delete_file_button.setVisible(has_selection)

    def _refresh_file_buttons(self) -> None:
        row = self._list.currentRow()
        has_entry = 0 <= row < len(self._entries)
        has_file_selected = has_entry and self._files_list.currentRow() >= 0
        self._remove_from_group_button.setEnabled(has_file_selected)
        self._delete_file_button.setEnabled(has_file_selected)

    def _supports_select_file_for_current_type(self) -> bool:
        action_type = _safe_text(self._type_combo.currentText())
        return action_type in {"UpdateDatabase", "UpdateIcons", "UpdateText", "AddGameplayScripts", "AddUserInterfaces", "ImportFiles"}

    def _handle_choose_file(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        if not self._supports_select_file_for_current_type():
            return

        action_type = _safe_text(self._type_combo.currentText())
        provider = self._selectable_files_provider
        if not callable(provider):
            return
        try:
            candidates = provider(action_type)
        except Exception:
            candidates = []
        if not isinstance(candidates, list):
            candidates = []
        candidates = [_safe_text(str(item)) for item in candidates if _safe_text(str(item))]
        if not candidates:
            QMessageBox.information(self, "选择文件", "当前没有可加入的未加载文件。")
            return

        dlg = _SelectFilesDialog(title=f"选择文件 - {action_type}", files=candidates, parent=self)
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return
        selected = dlg.selected_files()
        if not selected:
            return

        entry = self._entries[row]
        files = entry.get("files") if isinstance(entry.get("files"), list) else []
        origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
        existing = {str(item).lower() for item in files}
        for rel in selected:
            if rel.lower() in existing:
                continue
            files.append(rel)
            origins[rel] = "imported"
            existing.add(rel.lower())
        entry["files"] = files
        entry["file_origins"] = origins
        self._is_updating = True
        self._rebuild_files_list(files)
        self._is_updating = False
        self._update_current_entry()

    def _handle_remove_from_group(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        file_item = self._files_list.currentItem()
        if file_item is None:
            return
        rel_path = _safe_text(file_item.text())
        if not rel_path:
            return
        entry = self._entries[row]
        files = entry.get("files") if isinstance(entry.get("files"), list) else []
        files = [item for item in files if _safe_text(str(item)) and _safe_text(str(item)) != rel_path]
        origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
        origins.pop(rel_path, None)
        entry["files"] = files
        entry["file_origins"] = origins
        self._is_updating = True
        self._rebuild_files_list(files)
        self._is_updating = False
        self._update_current_entry()

    def _rebuild_files_list(self, files: list[str]) -> None:
        self._files_list.clear()
        for path in files:
            self._files_list.addItem(QListWidgetItem(path))

    def _existing_paths_for_duplicate_check(self) -> set[str]:
        paths: set[str] = set()
        for entry in self._entries:
            files = entry.get("files") if isinstance(entry.get("files"), list) else []
            for item in files:
                text = _safe_text(str(item)).lower()
                if text:
                    paths.add(text)

        provider = self._duplicate_paths_provider
        if callable(provider):
            try:
                payload = provider()
                if isinstance(payload, list):
                    for item in payload:
                        text = _safe_text(str(item)).lower()
                        if text:
                            paths.add(text)
            except Exception:
                pass
        return paths

    @staticmethod
    def _normalize_short_name(raw_short_name: str) -> str:
        text = _safe_text(raw_short_name)
        text = re.sub(r"[\s\-\.]+", "_", text)
        text = re.sub(r"[^A-Za-z0-9_]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text

    def _handle_create_file(self) -> None:
        if not self._allow_create_file:
            return
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return

        action_type = _safe_text(self._type_combo.currentText())
        if action_type not in {"AddGameplayScripts", "AddUserInterfaces", "ImportFiles", "UpdateDatabase"}:
            return

        file_base = ""
        if callable(self._file_basename_provider):
            file_base = _safe_text(str(self._file_basename_provider() or ""))
        if not file_base:
            QMessageBox.warning(self, "创建文件", "请先在基础信息中设置文件名。")
            return

        short_name, accepted = QInputDialog.getText(self, "创建文件", "输入文件简称（无需文件名前缀）：")
        if not accepted:
            return

        short_token = self._normalize_short_name(short_name)
        if not short_token:
            QMessageBox.warning(self, "创建文件", "请输入有效简称（英文、数字、下划线）。")
            return

        rel_paths: list[str] = []
        if action_type == "AddGameplayScripts":
            rel_paths = [f"Scripts/{file_base}_{short_token}.lua"]
        elif action_type == "AddUserInterfaces":
            rel_paths = [f"UI/{file_base}_{short_token}.xml", f"UI/{file_base}_{short_token}.lua"]
        elif action_type == "ImportFiles":
            rel_paths = [f"Import/{file_base}_{short_token}.lua"]
        elif action_type == "UpdateDatabase":
            ext_dialog = _UpdateDatabaseCreateDialog(self)
            if ext_dialog.exec() != int(QDialog.DialogCode.Accepted):
                return
            rel_paths = [f"Data/{file_base}_{short_token}.{ext_dialog.selected_ext()}"]

        existing = self._existing_paths_for_duplicate_check()
        for rel in rel_paths:
            if rel.lower() in existing:
                QMessageBox.warning(self, "创建文件", f"文件已存在，不能重复创建：{rel}")
                return

        files = [
            _safe_text(str(self._files_list.item(i).text()))
            for i in range(self._files_list.count())
            if _safe_text(str(self._files_list.item(i).text()))
        ]
        entry = self._entries[row]
        origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
        for rel in rel_paths:
            if rel not in files:
                files.append(rel)
            origins[rel] = "created"
        entry["files"] = files
        entry["file_origins"] = origins
        self._rebuild_files_list(files)
        self._refresh_file_buttons()
        added_text = "\n".join(rel_paths)
        QMessageBox.information(self, "创建文件", f"已添加：\n{added_text}")

    def _handle_delete_selected_file(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        file_item = self._files_list.currentItem()
        if file_item is None:
            return
        rel_path = _safe_text(file_item.text())
        if not rel_path:
            return

        entry = self._entries[row]
        origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
        origin = _safe_text(str(origins.get(rel_path) or "imported"))
        exists_provider = self._file_exists_provider
        file_exists = bool(callable(exists_provider) and exists_provider(rel_path))

        if origin != "created" or file_exists:
            answer = QMessageBox.question(
                self,
                "删除文件",
                f"将删除文件：{rel_path}\n删除后不可恢复，确认继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        callback = self._delete_file_request_callback
        if callable(callback):
            if not bool(callback(rel_path)):
                return

        files = [item for item in (entry.get("files") if isinstance(entry.get("files"), list) else []) if _safe_text(str(item)) != rel_path]
        origins.pop(rel_path, None)
        entry["files"] = files
        entry["file_origins"] = origins
        self._is_updating = True
        self._rebuild_files_list(files)
        self._is_updating = False
        self._update_current_entry()

    def _line_count_for_selected_entry(self) -> int:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            return 1
        files = self._entries[row].get("files", [])
        if not isinstance(files, list):
            return 1
        return max(1, len([item for item in files if _safe_text(str(item))]))

    def _recalculate_heights(self) -> None:
        row_height = max(22, self._list.sizeHintForRow(0)) if self._entries else 24
        list_count = max(1, len(self._entries))
        list_frame = self._list.frameWidth() * 2
        list_height = list_count * row_height + list_frame + 6
        self._list.setFixedHeight(list_height)

        file_list_row_h = max(20, self._files_list.sizeHintForRow(0)) if self._files_list.count() > 0 else 22
        file_list_height = max(56, file_list_row_h * max(1, self._files_list.count()) + self._files_list.frameWidth() * 2 + 4)
        self._files_list.setFixedHeight(file_list_height)

        self.updateGeometry()


class BasicInfoWorkspacePanel(QWidget):
    """基础信息面板，负责 .civ6proj 参数编辑与序列化。"""

    def __init__(
        self,
        *,
        group_preview_format_getter=None,
        text_preview_format_getter=None,
        section_has_entries_getter=None,
        workspace_params_changed_callback=None,
        refresh_project_config_callback=None,
        custom_project_files_provider=None,
        has_custom_unit_abilities_getter=None,
    ) -> None:
        super().__init__()
        self.setObjectName("basicInfoWorkspacePanel")
        self.setProperty("workspacePanel", "true")

        self._group_preview_format_getter = group_preview_format_getter
        self._text_preview_format_getter = text_preview_format_getter
        self._section_has_entries_getter = section_has_entries_getter
        self._workspace_params_changed_callback = workspace_params_changed_callback
        self._refresh_project_config_callback = refresh_project_config_callback
        self._custom_project_files_provider = custom_project_files_provider
        self._has_custom_unit_abilities_getter = has_custom_unit_abilities_getter
        self._suspend_workspace_params_signal = True
        self._delete_requests: list[str] = []

        self._civ6proj_path_edit = QLineEdit()
        self._civ6proj_path_edit.setReadOnly(True)
        self._select_civ6proj_button = QPushButton("选择 .civ6proj")
        self._select_civ6proj_button.clicked.connect(self._handle_choose_civ6proj)
        self._refresh_config_button = QPushButton("刷新配置")
        self._refresh_config_button.clicked.connect(self._handle_refresh_project_config)

        self._prefix_edit = QLineEdit()
        self._prefix_edit.setPlaceholderText("英文字符串")
        self._prefix_edit.textChanged.connect(self._handle_workspace_params_input_changed)

        self._infix_spin = QSpinBox()
        self._infix_spin.setRange(0, 2_000_000_000)
        self._infix_spin.valueChanged.connect(self._handle_workspace_params_input_changed)

        self._language_combo = QComboBox()
        self._language_combo.addItems(LANGUAGE_OPTIONS)

        self._mod_name_edit = QLineEdit()
        self._description_edit = QPlainTextEdit()
        self._description_edit.setPlaceholderText("Mod描述（支持多行）")
        self._description_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._description_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._description_edit.setFixedHeight(88)
        self._thanks_edit = QLineEdit()
        self._authors_edit = QLineEdit()

        self._guid_edit = QLineEdit()
        self._guid_edit.setReadOnly(True)

        self._file_name_edit = QLineEdit()
        self._file_name_edit.setReadOnly(True)

        self._affects_saved_games = QCheckBox("影响游戏存档")
        self._supports_single_player = QCheckBox("支持单人游戏")
        self._supports_multiplayer = QCheckBox("支持多人游戏")
        self._supports_hotseat = QCheckBox("支持热座模式")

        self._quick_config_button = QPushButton("一键配置")
        self._quick_config_button.clicked.connect(self._handle_quick_config)
        self._quick_clear_button = QPushButton("一键删除")
        self._quick_clear_button.clicked.connect(self._handle_quick_clear)

        self._front_end_editor = _ActionColumnEditor(
            "FrontEndActionData",
            self._safe_file_basename_for_actions,
            allow_create_file=True,
            disallowed_types={"AddGameplayScripts", "AddUserInterfaces"},
            duplicate_paths_provider=self._all_known_action_paths,
            selectable_files_provider=self._selectable_files_for_action,
            delete_file_request_callback=self._request_delete_file,
            file_exists_provider=self._file_exists_in_project_root,
        )
        self._in_game_editor = _ActionColumnEditor(
            "InGameActionData",
            self._safe_file_basename_for_actions,
            duplicate_paths_provider=self._all_known_action_paths,
            selectable_files_provider=self._selectable_files_for_action,
            delete_file_request_callback=self._request_delete_file,
            file_exists_provider=self._file_exists_in_project_root,
        )

        self._name_raw = ""
        self._teaser_raw = ""
        self._description_raw = ""
        self._localized_text_data = ""

        self._build_layout()
        self._apply_defaults()
        self._suspend_workspace_params_signal = False

    def _emit_workspace_params_changed(self) -> None:
        if self._suspend_workspace_params_signal:
            return
        callback = self._workspace_params_changed_callback
        if callable(callback):
            callback()

    def _handle_workspace_params_input_changed(self, _value: object = None) -> None:
        self._emit_workspace_params_changed()

    def _build_layout(self) -> None:
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        global_group = QGroupBox("全局参数设置区域")
        global_form = QFormLayout()
        global_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        global_form.setContentsMargins(10, 12, 10, 12)
        global_form.setSpacing(8)
        global_form.addRow("前缀", self._prefix_edit)
        global_form.addRow("中缀", self._infix_spin)
        global_form.addRow("语言", self._language_combo)
        global_group.setLayout(global_form)

        project_group = QGroupBox("工程文件配置区域")
        project_layout = QVBoxLayout()
        project_layout.setContentsMargins(10, 12, 10, 12)
        project_layout.setSpacing(10)

        refresh_row = QHBoxLayout()
        refresh_row.setContentsMargins(0, 0, 0, 0)
        refresh_row.setSpacing(8)
        refresh_row.addWidget(self._refresh_config_button, 0)
        refresh_row.addStretch(1)
        project_layout.addLayout(refresh_row)

        base_group = QGroupBox("基础信息区域")
        base_layout = QVBoxLayout()
        base_layout.setContentsMargins(10, 12, 10, 12)
        base_layout.setSpacing(10)

        proj_path_row = QHBoxLayout()
        proj_path_row.setContentsMargins(0, 0, 0, 0)
        proj_path_row.setSpacing(8)
        proj_path_row.addWidget(self._civ6proj_path_edit, 1)
        proj_path_row.addWidget(self._select_civ6proj_button)

        base_form = QFormLayout()
        base_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        base_form.setContentsMargins(0, 0, 0, 0)
        base_form.setSpacing(8)
        base_form.addRow("选择工程文件", proj_path_row)
        base_form.addRow("Mod名字", self._mod_name_edit)
        base_form.addRow("描述", self._description_edit)
        base_form.addRow("致谢", self._thanks_edit)
        base_form.addRow("作者", self._authors_edit)
        base_form.addRow("ID", self._guid_edit)
        base_form.addRow("文件名", self._file_name_edit)

        checkbox_row = QHBoxLayout()
        checkbox_row.setContentsMargins(0, 0, 0, 0)
        checkbox_row.setSpacing(12)
        checkbox_row.addWidget(self._affects_saved_games)
        checkbox_row.addWidget(self._supports_single_player)
        checkbox_row.addWidget(self._supports_multiplayer)
        checkbox_row.addWidget(self._supports_hotseat)
        checkbox_row.addStretch(1)

        base_layout.addLayout(base_form)
        base_layout.addLayout(checkbox_row)
        base_group.setLayout(base_layout)

        file_group = QGroupBox("文件信息区域")
        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(10, 12, 10, 12)
        file_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.addStretch(1)
        quick_buttons = QVBoxLayout()
        quick_buttons.setSpacing(6)
        quick_buttons.addWidget(self._quick_config_button)
        quick_buttons.addWidget(self._quick_clear_button)
        top_row.addLayout(quick_buttons)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._front_end_editor)
        splitter.addWidget(self._in_game_editor)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        file_layout.addLayout(top_row)
        file_layout.addWidget(splitter, 1)
        file_group.setLayout(file_layout)

        project_layout.addWidget(base_group)
        project_layout.addWidget(file_group, 1)
        project_group.setLayout(project_layout)

        content_layout.addWidget(global_group)
        content_layout.addWidget(project_group)
        content_layout.addStretch(1)
        content_widget.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content_widget)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)
        self.setLayout(root_layout)

    def _apply_defaults(self) -> None:
        old_state = self._suspend_workspace_params_signal
        self._suspend_workspace_params_signal = True
        self._prefix_edit.setText("")
        self._infix_spin.setValue(0)
        self._language_combo.setCurrentText("简体中文")
        self._civ6proj_path_edit.setText("")
        self._mod_name_edit.setText("")
        self._description_edit.setPlainText("")
        self._thanks_edit.setText("")
        self._authors_edit.setText("")
        self._guid_edit.setText("")
        self._file_name_edit.setText("")
        self._affects_saved_games.setChecked(False)
        self._supports_single_player.setChecked(False)
        self._supports_multiplayer.setChecked(False)
        self._supports_hotseat.setChecked(False)
        self._front_end_editor.set_entries([])
        self._in_game_editor.set_entries([])
        self._name_raw = ""
        self._teaser_raw = ""
        self._description_raw = ""
        self._localized_text_data = ""
        self._delete_requests = []
        self._refresh_quick_buttons_enabled()
        self._suspend_workspace_params_signal = old_state
        self._emit_workspace_params_changed()

    def _handle_choose_civ6proj(self) -> None:
        default_dir = Path.home() / "Documents" / "Firaxis ModBuddy" / "Civilization VI"
        start_dir = str(default_dir if default_dir.exists() else Path.home() / "Documents")
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择 .civ6proj 文件",
            start_dir,
            "Civ6 Project (*.civ6proj);;XML (*.xml);;All Files (*)",
        )
        if not selected_file:
            return

        file_path = Path(selected_file)
        try:
            parsed = self._parse_civ6proj_file(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "解析失败", f"读取工程文件失败：{exc}")
            return

        self._apply_parsed_civ6proj(parsed)
        self._civ6proj_path_edit.setText(str(file_path))
        self._file_name_edit.setText(file_path.stem)
        self._refresh_quick_buttons_enabled()

    def _parse_civ6proj_file(self, file_path: Path) -> dict[str, object]:
        tree = ET.parse(file_path)
        root = tree.getroot()

        property_groups = [node for node in list(root) if _local_name(node.tag) == "PropertyGroup"]
        if not property_groups:
            raise ValueError("未找到 PropertyGroup 节点")

        base_group: ET.Element | None = None
        for group in property_groups:
            if "Condition" not in group.attrib:
                base_group = group
                break
        if base_group is None:
            base_group = property_groups[0]

        name_raw = _child_text(base_group, "Name", "")
        teaser_raw = _child_text(base_group, "Teaser", "")
        description_raw = _child_text(base_group, "Description", "")
        special_thanks_raw = _child_text(base_group, "SpecialThanks", "")
        localized_text_data = _child_text(base_group, "LocalizedTextData", "")

        if name_raw.startswith("LOC_"):
            mod_name = _resolve_loc_text(localized_text_data, name_raw)
        else:
            mod_name = name_raw

        if teaser_raw.startswith("LOC_"):
            teaser = _resolve_loc_text(localized_text_data, teaser_raw)
        else:
            teaser = teaser_raw

        if description_raw.startswith("LOC_"):
            description = _resolve_loc_text(localized_text_data, description_raw)
        else:
            description = description_raw

        front_end_actions = _parse_action_data(_child_text(base_group, "FrontEndActionData", ""))
        in_game_actions = _parse_action_data(_child_text(base_group, "InGameActionData", ""))

        return {
            "project_info": {
                "mod_name": mod_name,
                "teaser": teaser,
                "description": description,
                "thanks": special_thanks_raw,
                "authors": _child_text(base_group, "Authors", ""),
                "guid": _child_text(base_group, "Guid", ""),
                "file_name": file_path.stem,
                "affects_saved_games": _bool_from_text(_child_text(base_group, "AffectsSavedGames", "false")),
                "supports_single_player": _bool_from_text(_child_text(base_group, "SupportsSinglePlayer", "true"), default=True),
                "supports_multiplayer": _bool_from_text(_child_text(base_group, "SupportsMultiplayer", "true"), default=True),
                "supports_hotseat": _bool_from_text(_child_text(base_group, "SupportsHotSeat", "true"), default=True),
                "name_raw": name_raw,
                "teaser_raw": teaser_raw,
                "description_raw": description_raw,
                "localized_text_data": localized_text_data,
            },
            "file_info": {
                "front_end_actions": front_end_actions,
                "in_game_actions": in_game_actions,
            },
        }

    def _apply_parsed_civ6proj(self, parsed: dict[str, object]) -> None:
        project_info = parsed.get("project_info") if isinstance(parsed, dict) else None
        if not isinstance(project_info, dict):
            project_info = {}

        file_info = parsed.get("file_info") if isinstance(parsed, dict) else None
        if not isinstance(file_info, dict):
            file_info = {}

        self._mod_name_edit.setText(_safe_text(str(project_info.get("mod_name", ""))))
        description_value = _safe_text(str(project_info.get("description", "")))
        if not description_value:
            description_value = _safe_text(str(project_info.get("teaser", "")))
        self._description_edit.setPlainText(description_value)
        thanks_value = _safe_text(str(project_info.get("thanks", "")))
        self._thanks_edit.setText(thanks_value)
        self._authors_edit.setText(_safe_text(str(project_info.get("authors", ""))))
        self._guid_edit.setText(_safe_text(str(project_info.get("guid", ""))))
        self._file_name_edit.setText(_safe_text(str(project_info.get("file_name", ""))))

        self._affects_saved_games.setChecked(bool(project_info.get("affects_saved_games", False)))
        self._supports_single_player.setChecked(bool(project_info.get("supports_single_player", True)))
        self._supports_multiplayer.setChecked(bool(project_info.get("supports_multiplayer", True)))
        self._supports_hotseat.setChecked(bool(project_info.get("supports_hotseat", True)))

        self._front_end_editor.set_entries(list(file_info.get("front_end_actions", [])))
        self._in_game_editor.set_entries(list(file_info.get("in_game_actions", [])))

        self._name_raw = _safe_text(str(project_info.get("name_raw", "")))
        self._teaser_raw = _safe_text(str(project_info.get("teaser_raw", "")))
        self._description_raw = _safe_text(str(project_info.get("description_raw", "")))
        self._localized_text_data = _safe_text(str(project_info.get("localized_text_data", "")))

        self._refresh_quick_buttons_enabled()

    def export_project_payload(self) -> dict[str, object]:
        self._sync_created_file_origins()
        language = _safe_text(self._language_combo.currentText())
        if language not in LANGUAGE_OPTIONS:
            language = "简体中文"

        front_entries = [
            entry
            for entry in self._front_end_editor.entries()
            if _safe_text(str(entry.get("type") or "")) not in {"AddGameplayScripts", "AddUserInterfaces"}
        ]

        payload = {
            "global_settings": {
                "prefix": _safe_text(self._prefix_edit.text()),
                "infix": int(self._infix_spin.value()),
                "language": language,
            },
            "shared_workspace_params": self.shared_workspace_parameters(),
            "project_info": {
                "civ6proj_path": _safe_text(self._civ6proj_path_edit.text()),
                "mod_name": _safe_text(self._mod_name_edit.text()),
                "teaser": _safe_text(self._description_edit.toPlainText()),
                "description": _safe_text(self._description_edit.toPlainText()),
                "thanks": _safe_text(self._thanks_edit.text()),
                "authors": _safe_text(self._authors_edit.text()),
                "guid": _safe_text(self._guid_edit.text()),
                "file_name": _safe_text(self._file_name_edit.text()),
                "affects_saved_games": bool(self._affects_saved_games.isChecked()),
                "supports_single_player": bool(self._supports_single_player.isChecked()),
                "supports_multiplayer": bool(self._supports_multiplayer.isChecked()),
                "supports_hotseat": bool(self._supports_hotseat.isChecked()),
                "name_raw": self._name_raw,
                "teaser_raw": self._teaser_raw,
                "description_raw": self._description_raw,
                "localized_text_data": self._localized_text_data,
            },
            "file_info": {
                "front_end_actions": front_entries,
                "in_game_actions": self._in_game_editor.entries(),
                "delete_requests": list(self._delete_requests),
            },
        }
        return payload

    def import_project_payload(self, payload: dict[str, object] | None) -> None:
        if not isinstance(payload, dict):
            self._apply_defaults()
            return

        old_state = self._suspend_workspace_params_signal
        self._suspend_workspace_params_signal = True

        global_settings = payload.get("global_settings")
        project_info = payload.get("project_info")
        file_info = payload.get("file_info")

        if not isinstance(global_settings, dict):
            global_settings = {}
        if not isinstance(project_info, dict):
            project_info = {}
        if not isinstance(file_info, dict):
            file_info = {}

        self._prefix_edit.setText(_safe_text(str(global_settings.get("prefix", ""))))
        self._infix_spin.setValue(_parse_int(global_settings.get("infix", 0), default=0))

        language = _safe_text(str(global_settings.get("language", "简体中文")))
        if language not in LANGUAGE_OPTIONS:
            language = "简体中文"
        self._language_combo.setCurrentText(language)

        self._civ6proj_path_edit.setText(_safe_text(str(project_info.get("civ6proj_path", ""))))
        self._mod_name_edit.setText(_safe_text(str(project_info.get("mod_name", ""))))
        description_value = _safe_text(str(project_info.get("description", "")))
        if not description_value:
            description_value = _safe_text(str(project_info.get("teaser", "")))
        self._description_edit.setPlainText(description_value)
        thanks_value = _safe_text(str(project_info.get("thanks", "")))
        self._thanks_edit.setText(thanks_value)
        self._authors_edit.setText(_safe_text(str(project_info.get("authors", ""))))
        self._guid_edit.setText(_safe_text(str(project_info.get("guid", ""))))
        self._file_name_edit.setText(_safe_text(str(project_info.get("file_name", ""))))

        self._affects_saved_games.setChecked(_bool_from_text(project_info.get("affects_saved_games"), default=False))
        self._supports_single_player.setChecked(_bool_from_text(project_info.get("supports_single_player"), default=True))
        self._supports_multiplayer.setChecked(_bool_from_text(project_info.get("supports_multiplayer"), default=True))
        self._supports_hotseat.setChecked(_bool_from_text(project_info.get("supports_hotseat"), default=True))

        self._name_raw = _safe_text(str(project_info.get("name_raw", "")))
        self._teaser_raw = _safe_text(str(project_info.get("teaser_raw", "")))
        self._description_raw = _safe_text(str(project_info.get("description_raw", "")))
        self._localized_text_data = _safe_text(str(project_info.get("localized_text_data", "")))

        front_raw = file_info.get("front_end_actions", [])
        if not isinstance(front_raw, list):
            front_raw = []
        front_entries = [
            entry
            for entry in front_raw
            if isinstance(entry, dict) and _safe_text(str(entry.get("type") or "")) not in {"AddGameplayScripts", "AddUserInterfaces"}
        ]
        self._front_end_editor.set_entries(front_entries)
        in_game_raw = file_info.get("in_game_actions", [])
        if not isinstance(in_game_raw, list):
            in_game_raw = []
        self._in_game_editor.set_entries(in_game_raw)
        delete_raw = file_info.get("delete_requests", [])
        if not isinstance(delete_raw, list):
            delete_raw = []
        self._delete_requests = [self._normalize_rel_path(str(item)) for item in delete_raw if self._normalize_rel_path(str(item))]
        self._refresh_quick_buttons_enabled()
        self._suspend_workspace_params_signal = old_state
        self._emit_workspace_params_changed()

    def shared_workspace_parameters(self) -> dict[str, object]:
        return {
            "prefix": _safe_text(self._prefix_edit.text()),
            "infix": int(self._infix_spin.value()),
            "file_name": _safe_text(self._file_name_edit.text()),
        }

    def _refresh_quick_buttons_enabled(self) -> None:
        enabled = bool(_safe_text(self._file_name_edit.text()))
        self._quick_config_button.setEnabled(enabled)
        self._quick_clear_button.setEnabled(enabled)
        has_civ6proj = bool(_safe_text(self._civ6proj_path_edit.text()))
        self._refresh_config_button.setEnabled(has_civ6proj)

    def _handle_refresh_project_config(self) -> None:
        callback = self._refresh_project_config_callback
        if not callable(callback):
            QMessageBox.warning(self, "刷新配置", "当前工作区不支持刷新配置。")
            return
        if not _safe_text(self._civ6proj_path_edit.text()):
            QMessageBox.warning(self, "刷新配置", "请先选择 .civ6proj 文件。")
            return
        try:
            callback()
        except Exception as exc:
            QMessageBox.warning(self, "刷新配置", f"刷新配置失败：{exc}")
            return
        QMessageBox.information(self, "刷新配置", "已刷新工程目录配置并同步到工程总览。")

    def _safe_file_basename_for_actions(self) -> str:
        return self._safe_file_basename(self._file_name_edit.text())

    @staticmethod
    def _normalize_file_token(raw_name: str) -> str:
        text = _safe_text(raw_name).upper()
        text = re.sub(r"[^A-Z0-9_]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "PROJECT"

    @staticmethod
    def _safe_file_basename(raw_name: str) -> str:
        text = _safe_text(raw_name)
        text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "project"

    def _group_format(self, section: str) -> str:
        if callable(self._group_preview_format_getter):
            got = _safe_text(str(self._group_preview_format_getter(section))).lower()
            if got in {"sql", "xml"}:
                return got
        return "sql"

    def _text_format(self) -> str:
        if callable(self._text_preview_format_getter):
            got = _safe_text(str(self._text_preview_format_getter())).lower()
            if got in {"sql", "xml"}:
                return got
        return "sql"

    def _quick_text_files(self) -> list[str]:
        text_ext = self._text_format()
        file_token = self._safe_file_basename(self._file_name_edit.text())
        mapping = {
            "简体中文": ["CN"],
            "简体中文，英文": ["CN", "EN"],
            "简体中文，英文，繁体中文": ["CN", "EN", "HK"],
        }
        language = _safe_text(self._language_combo.currentText())
        suffixes = mapping.get(language, ["CN"])
        return [f"Text/{file_token}_Text_{suffix}.{text_ext}" for suffix in suffixes]

    def _quick_data_files(self) -> list[str]:
        file_token = self._safe_file_basename(self._file_name_edit.text())
        section_basenames = [
            ("文明", "Civilizations"),
            ("领袖", "Leaders"),
            ("区域", "Districts"),
            ("建筑", "Buildings"),
            ("单位", "Units"),
            ("改良设施", "Improvements"),
            ("总督", "Governors"),
            ("伟人", "GreatPeople"),
            ("政策卡", "Policies"),
            ("项目", "Projects"),
            ("信仰", "Beliefs"),
            ("议程", "Agendas"),
        ]

        files: list[str] = []
        optional_sections = {"区域", "建筑", "单位", "改良设施", "伟人", "总督", "项目", "信仰", "政策卡", "议程"}

        def _has_custom_unit_abilities() -> bool:
            getter = self._has_custom_unit_abilities_getter
            if callable(getter):
                try:
                    return bool(getter())
                except Exception:
                    return False
            return False

        def _should_include_section(section: str) -> bool:
            if section not in optional_sections:
                return True
            getter = self._section_has_entries_getter
            if callable(getter):
                try:
                    return bool(getter(section))
                except Exception:
                    return True
            return True

        for section, base_name in section_basenames:
            if not _should_include_section(section):
                continue
            ext = self._group_format(section)
            files.append(f"Data/{file_token}_{base_name}.{ext}")
            if section == "单位":
                files.append(f"Data/{file_token}_UnitAbilities.{ext}")
            if section == "伟人":
                files.append(f"Data/{file_token}_GreatWorks.{ext}")

        if not _should_include_section("单位") and _has_custom_unit_abilities():
            ext = self._group_format("单位")
            files.append(f"Data/{file_token}_UnitAbilities.{ext}")

        files.append(f"Data/{file_token}_Modifiers.sql")
        files.append(f"Data/{file_token}_Moments.sql")
        return files

    def _quick_front_end_entries(self) -> list[dict[str, object]]:
        file_token = self._safe_file_basename(self._file_name_edit.text())
        text_files = self._quick_text_files()
        return [
            {
                "type": "UpdateDatabase",
                "id": "UpdateDatabase",
                "files": [f"Data/{file_token}_Configs.sql"],
                "load_order": 0,
            },
            {
                "type": "UpdateText",
                "id": "UpdateText",
                "files": text_files,
                "load_order": 0,
            },
            {
                "type": "UpdateIcons",
                "id": "UpdateIcons",
                "files": [f"Icons/{file_token}_Icons.xml"],
                "load_order": 1000,
            },
            {
                "type": "UpdateColors",
                "id": "UpdateColors",
                "files": [f"Data/{file_token}_Colors.sql"],
                "load_order": 0,
            },
            {
                "type": "UpdateArt",
                "id": "UpdateArt",
                "files": ["(Mod Art Dependency File)"],
                "load_order": 0,
            },
        ]

    def _quick_in_game_entries(self) -> list[dict[str, object]]:
        file_token = self._safe_file_basename(self._file_name_edit.text())
        text_files = self._quick_text_files()
        data_files = [
            path
            for path in self._quick_data_files()
            if not path.endswith("_Configs.sql") and not path.endswith("_Colors.sql")
        ]
        return [
            {
                "type": "UpdateColors",
                "id": "UpdateColors",
                "files": [f"Data/{file_token}_Colors.sql"],
                "load_order": 0,
            },
            {
                "type": "UpdateText",
                "id": "UpdateText",
                "files": text_files,
                "load_order": 0,
            },
            {
                "type": "UpdateIcons",
                "id": "UpdateIcons",
                "files": [f"Icons/{file_token}_Icons.xml"],
                "load_order": 1000,
            },
            {
                "type": "UpdateArt",
                "id": "UpdateArt",
                "files": ["(Mod Art Dependency File)"],
                "load_order": 0,
            },
            {
                "type": "UpdateDatabase",
                "id": "UpdateDatabase",
                "files": data_files,
                "load_order": 9999,
            },
        ]

    @staticmethod
    def _entry_signature(entry: dict[str, object]) -> tuple[str, str, int, tuple[str, ...]]:
        action_type = _safe_text(str(entry.get("type") or ""))
        action_id = _safe_text(str(entry.get("id") or ""))
        load_order = max(0, int(entry.get("load_order", 0)))
        files = tuple(
            _safe_text(str(item))
            for item in entry.get("files", [])
            if _safe_text(str(item))
        )
        return action_type, action_id, load_order, files

    @staticmethod
    def _normalize_rel_path(path: str) -> str:
        return _safe_text(path).replace("\\", "/")

    def _project_root_dir(self) -> Path | None:
        civ6proj = _safe_text(self._civ6proj_path_edit.text())
        if not civ6proj:
            return None
        path = Path(civ6proj)
        if not path.exists():
            return None
        return path.parent

    def _custom_project_paths(self) -> list[str]:
        provider = self._custom_project_files_provider
        if not callable(provider):
            return []
        try:
            payload = provider()
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [self._normalize_rel_path(str(item)) for item in payload if self._normalize_rel_path(str(item))]

    def _read_project_file_text(self, rel_path: str) -> str:
        root = self._project_root_dir()
        if root is None:
            return ""
        path = root / rel_path
        if not path.exists() or not path.is_file():
            return ""
        try:
            raw = path.read_bytes()
        except Exception:
            return ""
        if b"\x00" in raw[:4096]:
            return ""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _looks_like_ui_context_xml(xml_text: str) -> bool:
        text = _safe_text(xml_text)
        if not text:
            return False
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return False
        return _local_name(root.tag).lower() == "context"

    def _classify_custom_import_paths(self) -> dict[str, list[str]]:
        result = {
            "db": [],
            "icons": [],
            "text": [],
            "gameplay_lua": [],
            "ui_files": [],
            "import_lua": [],
        }
        custom_paths = self._custom_project_paths()
        custom_set = {path.lower() for path in custom_paths}

        for rel in custom_paths:
            rel_norm = self._normalize_rel_path(rel)
            lower = rel_norm.lower()
            if "." not in lower:
                continue
            ext = lower.rsplit(".", 1)[-1]
            parts = [part for part in lower.split("/") if part]
            top = parts[0] if parts else ""

            if ext in {"sql", "xml"}:
                if top == "icons":
                    result["icons"].append(rel_norm)
                elif top == "text":
                    result["text"].append(rel_norm)
                elif top == "ui" and ext == "xml":
                    lua_peer = rel_norm[:-4] + ".lua"
                    if lua_peer.lower() in custom_set and self._looks_like_ui_context_xml(self._read_project_file_text(rel_norm)):
                        result["ui_files"].append(rel_norm)
                else:
                    result["db"].append(rel_norm)
                continue

            if ext != "lua":
                continue

            if top == "scripts":
                result["gameplay_lua"].append(rel_norm)
            elif top == "ui":
                xml_peer = rel_norm[:-4] + ".xml"
                if xml_peer.lower() in custom_set and self._looks_like_ui_context_xml(self._read_project_file_text(xml_peer)):
                    result["ui_files"].append(rel_norm)
            elif top == "import":
                result["import_lua"].append(rel_norm)

        for key, values in result.items():
            result[key] = sorted(set(values), key=lambda item: item.lower())
        return result

    def _all_known_action_paths(self) -> list[str]:
        paths: set[str] = set()
        for entry in self._front_end_editor.entries() + self._in_game_editor.entries():
            files = entry.get("files") if isinstance(entry.get("files"), list) else []
            for item in files:
                text = self._normalize_rel_path(str(item))
                if text:
                    paths.add(text)
        for item in self._quick_text_files() + self._quick_data_files():
            text = self._normalize_rel_path(item)
            if text:
                paths.add(text)
        for entry in self._quick_front_end_entries() + self._quick_in_game_entries():
            files = entry.get("files") if isinstance(entry.get("files"), list) else []
            for item in files:
                text = self._normalize_rel_path(str(item))
                if text:
                    paths.add(text)
        for item in self._custom_project_paths():
            text = self._normalize_rel_path(item)
            if text:
                paths.add(text)
        for item in self._delete_requests:
            text = self._normalize_rel_path(item)
            if text:
                paths.add(text)
        return sorted(paths)

    def _loaded_action_paths(self) -> list[str]:
        paths: set[str] = set()
        for entry in self._front_end_editor.entries() + self._in_game_editor.entries():
            files = entry.get("files") if isinstance(entry.get("files"), list) else []
            for item in files:
                text = self._normalize_rel_path(str(item))
                if text:
                    paths.add(text)
        return sorted(paths)

    def _file_exists_in_project_root(self, rel_path: str) -> bool:
        root = self._project_root_dir()
        if root is None:
            return False
        target = root / self._normalize_rel_path(rel_path)
        return target.exists() and target.is_file()

    def _selectable_files_for_action(self, action_type: str) -> list[str]:
        action = _safe_text(action_type)
        classified = self._classify_custom_import_paths()
        bucket_map = {
            "UpdateDatabase": "db",
            "UpdateIcons": "icons",
            "UpdateText": "text",
            "AddGameplayScripts": "gameplay_lua",
            "AddUserInterfaces": "ui_files",
            "ImportFiles": "import_lua",
        }
        bucket = bucket_map.get(action)
        if not bucket:
            return []
        candidates = classified.get(bucket, [])
        if not isinstance(candidates, list):
            return []

        loaded = {
            self._normalize_rel_path(str(path)).lower()
            for path in self._loaded_action_paths()
            if self._normalize_rel_path(str(path))
        }
        delete_set = {self._normalize_rel_path(path).lower() for path in self._delete_requests}
        return [
            rel
            for rel in candidates
            if self._normalize_rel_path(rel).lower() not in loaded and self._normalize_rel_path(rel).lower() not in delete_set
        ]

    @staticmethod
    def _remove_file_from_action_entries(entries: list[dict[str, object]], rel_path: str) -> list[dict[str, object]]:
        normalized = _safe_text(rel_path)
        if not normalized:
            return entries
        output: list[dict[str, object]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            copied = deepcopy(entry)
            files = copied.get("files") if isinstance(copied.get("files"), list) else []
            copied["files"] = [item for item in files if _safe_text(str(item)) != normalized]
            origins = copied.get("file_origins") if isinstance(copied.get("file_origins"), dict) else {}
            origins.pop(normalized, None)
            copied["file_origins"] = origins
            output.append(copied)
        return output

    def _request_delete_file(self, rel_path: str) -> bool:
        normalized = self._normalize_rel_path(rel_path)
        if not normalized:
            return False
        if normalized not in self._delete_requests:
            self._delete_requests.append(normalized)

        front_entries = self._remove_file_from_action_entries(self._front_end_editor.entries(), normalized)
        in_game_entries = self._remove_file_from_action_entries(self._in_game_editor.entries(), normalized)
        self._front_end_editor.set_entries(front_entries)
        self._in_game_editor.set_entries(in_game_entries)
        return True

    def _sync_created_file_origins(self) -> None:
        root = self._project_root_dir()
        if root is None:
            return

        def _normalize_compare_text(content: str) -> str:
            lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            while lines and not lines[-1].strip():
                lines.pop()
            return "\n".join(lines).strip()

        def _default_content_for_path(action_type: str, rel_path: str) -> str | None:
            action = _safe_text(action_type)
            rel = self._normalize_rel_path(rel_path).lower()
            if action == "AddGameplayScripts" and rel.endswith(".lua"):
                return DEFAULT_GAMEPLAY_LUA_TEMPLATE
            if action == "AddUserInterfaces":
                if rel.endswith(".xml"):
                    return DEFAULT_UI_XML_TEMPLATE
                if rel.endswith(".lua"):
                    return DEFAULT_GAMEPLAY_LUA_TEMPLATE
            return None

        def _sync_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
            updated: list[dict[str, object]] = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                copied = deepcopy(entry)
                action_type = _safe_text(str(copied.get("type") or ""))
                files = copied.get("files") if isinstance(copied.get("files"), list) else []
                origins = copied.get("file_origins") if isinstance(copied.get("file_origins"), dict) else {}
                for rel in files:
                    rel_text = self._normalize_rel_path(str(rel))
                    if _safe_text(str(origins.get(rel_text))) != "created":
                        continue
                    file_path = root / rel_text
                    if not file_path.exists() or not file_path.is_file():
                        continue
                    try:
                        raw = file_path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    default_content = _default_content_for_path(action_type, rel_text)
                    if default_content is None:
                        if _safe_text(raw):
                            origins[rel_text] = "imported"
                        continue

                    if _normalize_compare_text(raw) != _normalize_compare_text(default_content):
                        origins[rel_text] = "imported"
                copied["file_origins"] = origins
                updated.append(copied)
            return updated

        self._front_end_editor.set_entries(_sync_entries(self._front_end_editor.entries()))
        self._in_game_editor.set_entries(_sync_entries(self._in_game_editor.entries()))

    def _handle_quick_config(self) -> None:
        if not _safe_text(self._file_name_edit.text()):
            QMessageBox.warning(self, "一键配置", "请先选择 .civ6proj 文件。")
            return

        front_entries = self._front_end_editor.entries()
        in_game_entries = self._in_game_editor.entries()

        existing_front_signatures = {self._entry_signature(entry) for entry in front_entries}
        existing_in_game_signatures = {self._entry_signature(entry) for entry in in_game_entries}

        for entry in self._quick_front_end_entries():
            sig = self._entry_signature(entry)
            if sig in existing_front_signatures:
                continue
            front_entries.append(entry)
            existing_front_signatures.add(sig)

        for entry in self._quick_in_game_entries():
            sig = self._entry_signature(entry)
            if sig in existing_in_game_signatures:
                continue
            in_game_entries.append(entry)
            existing_in_game_signatures.add(sig)

        def _ensure_action(
            entries: list[dict[str, object]],
            *,
            action_type: str,
            action_id: str,
            load_order: int,
        ) -> dict[str, object]:
            for item in entries:
                if _safe_text(str(item.get("type") or "")) == action_type and _safe_text(str(item.get("id") or "")) == action_id:
                    if not isinstance(item.get("files"), list):
                        item["files"] = []
                    if not isinstance(item.get("file_origins"), dict):
                        item["file_origins"] = {}
                    return item
            created = {
                "type": action_type,
                "id": action_id,
                "files": [],
                "load_order": load_order,
                "file_origins": {},
            }
            entries.append(created)
            return created

        def _merge_files(entry: dict[str, object], files: list[str], *, origin: str) -> int:
            target = entry.get("files") if isinstance(entry.get("files"), list) else []
            origins = entry.get("file_origins") if isinstance(entry.get("file_origins"), dict) else {}
            added = 0
            existing_lower = {self._normalize_rel_path(str(item)).lower() for item in target}
            for file_path in files:
                rel = self._normalize_rel_path(file_path)
                if not rel:
                    continue
                low = rel.lower()
                if low in existing_lower:
                    if rel not in origins:
                        origins[rel] = origin
                    continue
                target.append(rel)
                origins[rel] = origin
                existing_lower.add(low)
                added += 1
            entry["files"] = target
            entry["file_origins"] = origins
            return added

        classified = self._classify_custom_import_paths()
        added_count = 0

        db_files = classified.get("db", [])
        if isinstance(db_files, list) and db_files:
            db_action = _ensure_action(in_game_entries, action_type="UpdateDatabase", action_id="UpdateDatabase", load_order=9999)
            added_count += _merge_files(db_action, db_files, origin="imported")

        icon_files = classified.get("icons", [])
        if isinstance(icon_files, list) and icon_files:
            fe_icons = _ensure_action(front_entries, action_type="UpdateIcons", action_id="UpdateIcons", load_order=1000)
            ig_icons = _ensure_action(in_game_entries, action_type="UpdateIcons", action_id="UpdateIcons", load_order=1000)
            added_count += _merge_files(fe_icons, icon_files, origin="imported")
            added_count += _merge_files(ig_icons, icon_files, origin="imported")

        text_files = classified.get("text", [])
        if isinstance(text_files, list) and text_files:
            fe_text = _ensure_action(front_entries, action_type="UpdateText", action_id="UpdateText", load_order=0)
            ig_text = _ensure_action(in_game_entries, action_type="UpdateText", action_id="UpdateText", load_order=0)
            added_count += _merge_files(fe_text, text_files, origin="imported")
            added_count += _merge_files(ig_text, text_files, origin="imported")

        gameplay_lua = classified.get("gameplay_lua", [])
        if isinstance(gameplay_lua, list) and gameplay_lua:
            gameplay_action = _ensure_action(in_game_entries, action_type="AddGameplayScripts", action_id="AddGameplayScripts", load_order=9500)
            added_count += _merge_files(gameplay_action, gameplay_lua, origin="imported")

        ui_files = classified.get("ui_files", [])
        if isinstance(ui_files, list) and ui_files:
            ui_action = _ensure_action(in_game_entries, action_type="AddUserInterfaces", action_id="AddUserInterfaces", load_order=9600)
            added_count += _merge_files(ui_action, ui_files, origin="imported")

        import_lua = classified.get("import_lua", [])
        if isinstance(import_lua, list) and import_lua:
            import_action = _ensure_action(in_game_entries, action_type="ImportFiles", action_id="ImportFiles", load_order=9700)
            added_count += _merge_files(import_action, import_lua, origin="imported")

        self._front_end_editor.set_entries(front_entries)
        self._in_game_editor.set_entries(in_game_entries)
        QMessageBox.information(self, "一键配置", f"已追加文件动作配置（自动去重，不覆盖现有配置）。\n本次新增导入文件：{added_count} 个")

    def _handle_quick_clear(self) -> None:
        target_front_signatures = {
            self._entry_signature(entry)
            for entry in self._quick_front_end_entries()
        }
        target_in_game_signatures = {
            self._entry_signature(entry)
            for entry in self._quick_in_game_entries()
        }

        front_existing = self._front_end_editor.entries()
        in_game_existing = self._in_game_editor.entries()

        kept_front = [entry for entry in front_existing if self._entry_signature(entry) not in target_front_signatures]
        kept_in_game = [entry for entry in in_game_existing if self._entry_signature(entry) not in target_in_game_signatures]

        removed_count = (len(front_existing) - len(kept_front)) + (len(in_game_existing) - len(kept_in_game))
        self._front_end_editor.set_entries(kept_front)
        self._in_game_editor.set_entries(kept_in_game)
        QMessageBox.information(self, "一键删除", f"已删除 {removed_count} 条一键配置动作。")
