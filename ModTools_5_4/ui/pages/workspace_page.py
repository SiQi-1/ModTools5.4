"""Workspace page with project tree and content area."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import html
import logging
import re
import sqlite3
import struct
from xml.dom import minidom
from xml.etree import ElementTree

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressDialog,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage
from .art_workspace import ArtWorkspacePanel
from .basic_info_workspace import BasicInfoWorkspacePanel
from .entity_table_form import REQUIRED_MAIN_TABLE_FIELD_RULES, build_beliefs_main_schema, build_buildings_main_schema, build_districts_main_schema, build_improvements_main_schema, build_policies_main_schema, build_projects_main_schema, build_units_main_schema
from .group_workspace import SectionGroupWorkspacePanel, SectionItemWorkspacePanel
from .modifier_workspace import ModifierWorkspacePanel
from ..ui_widget_kit import _BuildingSearchByDistrictDialog, _DistrictSearchDialog, _ImprovementSearchDialog, _UnitSearchDialog
from ..ui_widget_kit import set_workspace_sections_provider
from ..ui_widget_kit import _build_building_entries, _build_district_hierarchy, _build_improvement_entries, _build_unit_entries
from ...app.settings_store import load_settings
from ...db.paths import DEFAULT_GAME_DB
from ...db.interface import resolve_chinese_text_or_unknown
from ...project import (
    CIV_DIRECT_WORKSPACE_SECTIONS,
    CIV_FILE_EXTENSION,
    CIV_SECTION_ORDER,
    CivProject,
    create_empty_project,
    load_civ_project,
    save_civ_project,
)


MODIFIER_SECTION_FORMAT = "MODTOOLS54_MODIFIER_WORKSPACE"
MODIFIER_SECTION_SCHEMA = "1.0.0"
BASIC_INFO_SECTION_FORMAT = "MODTOOLS54_BASIC_INFO_WORKSPACE"
BASIC_INFO_SECTION_SCHEMA = "1.0.0"
LOGGER = logging.getLogger(__name__)


def _greatwork_slot_short(slot_type: str) -> str:
    slot = str(slot_type or "").strip().upper()
    if slot.startswith("GREATWORKSLOT_"):
        short = slot[len("GREATWORKSLOT_") :]
        return short or slot
    return slot


@dataclass(slots=True)
class ProjectSession:
    project: CivProject
    file_path: Path | None


class TextWorkspacePanel(QWidget):
    """文本工作区：统一承载 Text.sql / Text.xml 预览。"""

    def __init__(self, preview_provider, format_getter=None, format_setter=None) -> None:
        super().__init__()
        self.setObjectName("workspaceTextPanel")
        self.setProperty("workspacePanel", "true")
        self._preview_provider = preview_provider
        self._format_getter = format_getter
        self._format_setter = format_setter

        self._sql_button = QPushButton("SQL预览")
        self._xml_button = QPushButton("XML预览")
        self._sql_button.setCheckable(True)
        self._xml_button.setCheckable(True)
        self._sql_button.setChecked(True)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._button_group.addButton(self._sql_button)
        self._button_group.addButton(self._xml_button)

        self._sql_button.clicked.connect(lambda: self._handle_format_button_clicked("sql"))
        self._xml_button.clicked.connect(lambda: self._handle_format_button_clicked("xml"))

        self._preview_tab = QTabWidget()
        self._preview_text = QPlainTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_tab.addTab(self._preview_text, "Text.sql")

        top = QHBoxLayout()
        top.addWidget(self._sql_button)
        top.addWidget(self._xml_button)
        top.addStretch(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self._preview_tab, 1)
        self.setLayout(layout)

    def current_format(self) -> str:
        return "xml" if self._xml_button.isChecked() else "sql"

    def _apply_saved_format(self) -> None:
        preferred = "sql"
        if callable(self._format_getter):
            got = str(self._format_getter() or "sql").strip().lower()
            if got in {"sql", "xml"}:
                preferred = got
        self._sql_button.setChecked(preferred != "xml")
        self._xml_button.setChecked(preferred == "xml")

    def _handle_format_button_clicked(self, fmt: str) -> None:
        if callable(self._format_setter):
            self._format_setter(fmt)
        self.refresh_preview()

    def refresh_preview(self) -> None:
        self._apply_saved_format()
        fmt = self.current_format()
        self._preview_tab.setTabText(0, f"Text.{fmt}")
        self._preview_text.setPlainText(self._preview_provider(fmt))


class _OverwriteSelectionDialog(QDialog):
    def __init__(self, relative_paths: list[str], parent: QWidget | None = None, delete_paths: list[str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择覆盖文件")
        self.resize(760, 520)

        tip = QLabel("以下文件已存在：勾选表示覆盖；不勾选表示跳过。")
        tip.setWordWrap(True)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for path in sorted(relative_paths):
            item = QListWidgetItem(path)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list.addItem(item)

        self._delete_tip = QLabel("")
        self._delete_tip.setWordWrap(True)
        self._delete_list = QListWidget()
        self._delete_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        delete_items = [str(item or "").strip() for item in (delete_paths or []) if str(item or "").strip()]
        if delete_items:
            self._delete_tip.setText("以下文件将执行删除（默认勾选）。删除后不可复原，不勾选将忽略删除。")
            for path in sorted(set(delete_items), key=lambda item: item.lower()):
                item = QListWidgetItem(path)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self._delete_list.addItem(item)
        else:
            self._delete_tip.setText("当前无待删除文件。")
            self._delete_list.setEnabled(False)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tip)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._delete_tip)
        layout.addWidget(self._delete_list, 1)
        layout.addWidget(buttons)

    def selected_paths(self) -> set[str]:
        picked: set[str] = set()
        for idx in range(self._list.count()):
            item = self._list.item(idx)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                picked.add(item.text())
        return picked

    def selected_delete_paths(self) -> set[str]:
        picked: set[str] = set()
        for idx in range(self._delete_list.count()):
            item = self._delete_list.item(idx)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                picked.add(item.text())
        return picked


class ProjectRootWorkspacePanel(QWidget):
    def __init__(self, on_generate_single, on_generate_all) -> None:
        super().__init__()
        self.setObjectName("workspaceRootPanel")
        self.setProperty("workspacePanel", "true")
        self._on_generate_single = on_generate_single
        self._on_generate_all = on_generate_all
        self._files: dict[str, str] = {}
        self._folders: set[str] = set()
        self._img_plan_path: str = ""
        self._img_plan_rows: list[dict[str, str]] = []
        self._textures_plan_path: str = ""
        self._textures_plan_rows: list[dict[str, str]] = []
        self._delete_marked_paths: set[str] = set()
        self._build_ui()

    def _build_ui(self) -> None:
        self._generate_single_btn = QPushButton("生成该文件")
        self._generate_all_btn = QPushButton("生成所有文件")
        self._generate_single_btn.clicked.connect(self._handle_generate_single)
        self._generate_all_btn.clicked.connect(self._handle_generate_all)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        top.addWidget(self._generate_single_btn)
        top.addWidget(self._generate_all_btn)
        top.addStretch(1)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemSelectionChanged.connect(self._handle_selection_changed)
        self._tree.setMinimumWidth(260)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)

        self._img_table = QTableWidget(0, 4)
        self._img_table.setHorizontalHeaderLabels(["输出文件", "尺寸", "来源图片", "说明"])
        self._img_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._img_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._img_table.setAlternatingRowColors(True)
        self._img_table.verticalHeader().setVisible(False)
        header = self._img_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self._preview_stack = QStackedWidget()
        self._preview_stack.addWidget(self._preview)
        self._preview_stack.addWidget(self._img_table)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._tree)
        splitter.addWidget(self._preview_stack)
        splitter.setSizes([320, 880])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

    def set_manifest(self, files: dict[str, str], folders: set[str], can_generate: bool, delete_marked_paths: set[str] | None = None) -> None:
        self._files = dict(files)
        self._folders = set(folders)
        self._delete_marked_paths = {str(path or "").replace("\\", "/").strip().lower() for path in (delete_marked_paths or set())}
        self._generate_single_btn.setEnabled(can_generate)
        self._generate_all_btn.setEnabled(can_generate)

        self._tree.clear()

        nodes: dict[str, QTreeWidgetItem] = {}

        def _ensure_dir(path: str) -> QTreeWidgetItem:
            if not path:
                raise ValueError("empty path")
            if path in nodes:
                return nodes[path]
            parent_path = path.rsplit("/", 1)[0] if "/" in path else ""
            item = QTreeWidgetItem([path.split("/")[-1]])
            item.setData(0, Qt.ItemDataRole.UserRole, {"path": path, "is_file": False})
            if parent_path:
                parent = _ensure_dir(parent_path)
                parent.addChild(item)
            else:
                self._tree.addTopLevelItem(item)
            nodes[path] = item
            return item

        project_files = sorted([path for path in self._files.keys() if path.lower().endswith(".civ6proj")])
        for proj_path in project_files:
            top = QTreeWidgetItem([proj_path.split("/")[-1]])
            top.setData(0, Qt.ItemDataRole.UserRole, {"path": proj_path, "is_file": True})
            self._tree.addTopLevelItem(top)

        for folder in sorted(self._folders):
            _ensure_dir(folder)

        for file_path in sorted(path for path in self._files.keys() if path not in set(project_files)):
            parent_path = file_path.rsplit("/", 1)[0] if "/" in file_path else ""
            item = QTreeWidgetItem([file_path.split("/")[-1]])
            item.setData(0, Qt.ItemDataRole.UserRole, {"path": file_path, "is_file": True})
            if file_path.replace("\\", "/").strip().lower() in self._delete_marked_paths:
                item.setForeground(0, QColor("#d32f2f"))
            if parent_path:
                parent = _ensure_dir(parent_path)
                parent.addChild(item)
            else:
                self._tree.addTopLevelItem(item)

        self._tree.expandAll()
        if self._tree.topLevelItemCount() > 0:
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def set_img_plan_preview(self, plan_path: str, rows: list[dict[str, str]]) -> None:
        self._img_plan_path = str(plan_path or "").strip()
        self._img_plan_rows = [dict(row) for row in rows if isinstance(row, dict)]

    def set_textures_plan_preview(self, plan_path: str, rows: list[dict[str, str]]) -> None:
        self._textures_plan_path = str(plan_path or "").strip()
        self._textures_plan_rows = [dict(row) for row in rows if isinstance(row, dict)]

    def _populate_plan_table(self, rows: list[dict[str, str]] | None, *, empty_note: str) -> None:
        rows = rows if rows else [
            {
                "output": "（无）",
                "size": "-",
                "source": "-",
                "note": empty_note,
            }
        ]
        self._img_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row.get("output") or ""),
                str(row.get("size") or ""),
                str(row.get("source") or ""),
                str(row.get("note") or ""),
            ]
            for col_index, value in enumerate(values):
                self._img_table.setItem(row_index, col_index, QTableWidgetItem(value))

    def selected_file_path(self) -> str | None:
        selected = self._tree.selectedItems()
        if not selected:
            return None
        payload = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict) or not bool(payload.get("is_file")):
            return None
        path = str(payload.get("path") or "").strip()
        return path or None

    def _handle_selection_changed(self) -> None:
        selected = self._tree.selectedItems()
        if not selected:
            return
        payload = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return
        path = str(payload.get("path") or "").strip()
        if not path:
            return
        if bool(payload.get("is_file")):
            if self._img_plan_path and path == self._img_plan_path:
                self._populate_plan_table(self._img_plan_rows, empty_note="当前没有可生成图片")
                self._preview_stack.setCurrentWidget(self._img_table)
                return
            if self._textures_plan_path and path == self._textures_plan_path:
                self._populate_plan_table(self._textures_plan_rows, empty_note="当前没有可生成纹理（dds/tex）")
                self._preview_stack.setCurrentWidget(self._img_table)
                return
            self._preview_stack.setCurrentWidget(self._preview)
            content = self._files.get(path, "")
            self._preview.setPlainText(content if content else "-- 空文件")
        else:
            self._preview_stack.setCurrentWidget(self._preview)
            children = sorted(
                p for p in list(self._folders) + list(self._files.keys())
                if p.startswith(path + "/") and p != path and "/" not in p[len(path) + 1 :]
            )
            self._preview.setPlainText("\n".join(children) if children else "-- 空文件夹")

    def _handle_generate_single(self) -> None:
        path = self.selected_file_path()
        if path:
            self._on_generate_single(path)

    def _handle_generate_all(self) -> None:
        self._on_generate_all()


class WorkspacePage(BasePage):
    """Main editing workspace with .CIV project tree."""

    page_id = "workspace"
    display_name = "工作区"

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("workspacePage")
        self._loading_project = False
        self._project: CivProject = create_empty_project()
        self._project_file_path: Path | None = None
        self._sessions: list[ProjectSession] = []
        self._active_session_index: int = -1
        self._handling_tab_change = False
        self._readonly_custom_paths: set[str] = set()
        self._cached_custom_project_files: list[str] = []

        # Expose current project workspace to shared UI selectors (ui_widget_kit).
        set_workspace_sections_provider(self._workspace_sections_snapshot_for_selectors)

        self._project_tabs = QTabBar()
        self._project_tabs.setDocumentMode(True)
        self._project_tabs.setExpanding(False)
        self._project_tabs.currentChanged.connect(self._handle_project_tab_changed)

        self._tree = QTreeWidget()
        self._tree.setObjectName("workspaceTree")
        self._tree.setHeaderHidden(True)
        self._tree.itemSelectionChanged.connect(self._handle_selection_changed)

        self._workspace_title = QLabel("工作区")
        self._workspace_title.setObjectName("pageHeaderLabel")

        self._workspace_info = QLabel("请选择左侧节点")
        self._workspace_info.setObjectName("pageInfoLabel")
        self._workspace_info.setWordWrap(True)

        self._workspace_path = QLabel("")
        self._workspace_path.setObjectName("workspacePathLabel")
        self._workspace_path.setWordWrap(True)

        self._project_root_workspace = ProjectRootWorkspacePanel(
            on_generate_single=self._generate_single_output_file,
            on_generate_all=self._generate_all_output_files,
        )

        self._basic_info_workspace = BasicInfoWorkspacePanel(
            group_preview_format_getter=self._get_group_preview_format,
            text_preview_format_getter=self._get_text_preview_format,
            section_has_entries_getter=self._section_has_entries,
            workspace_params_changed_callback=self._handle_basic_workspace_params_changed,
            refresh_project_config_callback=self._handle_refresh_project_config_from_basic,
            custom_project_files_provider=self._custom_project_files_for_actions,
        )
        self._art_workspace = ArtWorkspacePanel()

        self._modifier_workspace = ModifierWorkspacePanel(
            save_to_project_callback=self._save_modifier_payload_to_project,
            load_from_project_callback=self._load_modifier_payload_from_project,
            owner_sources_provider=lambda: self._project.sections,
        )

        self._group_workspace = SectionGroupWorkspacePanel(
            on_add_entry=self._handle_add_group_entry,
            on_import_entry=self._handle_import_group_entry,
            preview_provider=self._build_group_data_preview_text,
            preview_format_getter=self._get_group_preview_format,
            preview_format_setter=self._set_group_preview_format,
        )

        self._text_workspace = TextWorkspacePanel(
            self._build_text_workspace_preview,
            format_getter=self._get_text_preview_format,
            format_setter=self._set_text_preview_format,
        )

        self._section_item_workspace = SectionItemWorkspacePanel(
            shared_params_provider=self.shared_workspace_parameters,
            bindable_entries_provider=self._list_bindable_entries,
            civilizations_provider=self._list_civilizations_for_leader,
            on_item_changed=self._handle_section_item_changed,
            on_duplicate_item=self._handle_duplicate_section_item,
            on_delete_item=self._handle_delete_section_item,
        )

        for panel in (
            self._project_root_workspace,
            self._basic_info_workspace,
            self._art_workspace,
            self._modifier_workspace,
            self._group_workspace,
            self._section_item_workspace,
            self._text_workspace,
        ):
            panel.setProperty("workspacePanel", "true")

        self._workspace_placeholder = QWidget()
        self._workspace_placeholder.setObjectName("workspacePlaceholder")
        self._workspace_placeholder.setProperty("workspacePanel", "true")
        placeholder_layout = QVBoxLayout()
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.addWidget(self._workspace_info)
        placeholder_layout.addStretch(1)
        self._workspace_placeholder.setLayout(placeholder_layout)

        self._workspace_stack = QStackedWidget()
        self._workspace_stack.addWidget(self._workspace_placeholder)
        self._workspace_stack.addWidget(self._project_root_workspace)
        self._workspace_stack.addWidget(self._basic_info_workspace)
        self._workspace_stack.addWidget(self._art_workspace)
        self._workspace_stack.addWidget(self._modifier_workspace)
        self._workspace_stack.addWidget(self._group_workspace)
        self._workspace_stack.addWidget(self._section_item_workspace)
        self._workspace_stack.addWidget(self._text_workspace)

        left_container = QWidget()
        left_container.setObjectName("workspaceLeftCard")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._tree)
        left_container.setLayout(left_layout)

        right_container = QWidget()
        right_container.setObjectName("workspaceRightCard")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)
        right_layout.addWidget(self._workspace_title)
        right_layout.addWidget(self._workspace_path)
        right_layout.addWidget(self._workspace_stack, 1)
        right_container.setLayout(right_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("workspaceMainSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 900])

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._project_tabs, 0)
        layout.addWidget(splitter, 1)
        self.setLayout(layout)

        self._add_session(create_empty_project(), None)

    def create_new_project(self, project_name: str = "未命名工程") -> None:
        self._sync_workspace_sections_from_editors()
        self._add_session(create_empty_project(project_name), None)

    def load_project(self, file_path: Path) -> None:
        self._sync_workspace_sections_from_editors()
        loaded = load_civ_project(file_path)
        self._add_session(loaded, file_path)
        self._refresh_all_workspaces_after_project_open()

    def save_project(self, file_path: Path | None = None) -> Path:
        self._sync_workspace_sections_from_editors()
        target_path = file_path or self._project_file_path
        if target_path is None:
            raise ValueError("尚未指定工程保存路径")
        if target_path.suffix.upper() != CIV_FILE_EXTENSION:
            target_path = target_path.with_suffix(CIV_FILE_EXTENSION)
        save_civ_project(target_path, self._project)
        self._project_file_path = target_path
        if 0 <= self._active_session_index < len(self._sessions):
            self._sessions[self._active_session_index].file_path = target_path
            self._sessions[self._active_session_index].project = self._project
        self._refresh_project_tab_titles()
        self._rebuild_tree()
        return target_path

    def project_name(self) -> str:
        return self._project.project_name

    def project_file_path(self) -> Path | None:
        return self._project_file_path

    def build_modifier_sql_preview(self) -> str:
        return self._modifier_workspace.generate_sql_preview_text()

    def build_modifier_xml_preview(self) -> str:
        return self._modifier_workspace.generate_xml_preview_text()

    def shared_workspace_parameters(self) -> dict[str, object]:
        """工作区共享参数（供基础信息外的编辑页读取）。"""
        return self._basic_info_workspace.shared_workspace_parameters()

    def shared_prefix(self) -> str:
        return str(self.shared_workspace_parameters().get("prefix") or "")

    def shared_infix(self) -> int:
        value = self.shared_workspace_parameters().get("infix")
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    def shared_file_name(self) -> str:
        return str(self.shared_workspace_parameters().get("file_name") or "")

    def _handle_basic_workspace_params_changed(self) -> None:
        self._save_basic_info_payload_to_project(self._basic_info_workspace.export_project_payload())
        if self._loading_project:
            return

        self._art_workspace.refresh_from_sections(self._project.sections)

        selected = self._tree.selectedItems()
        if not selected:
            return

        payload = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return

        if payload.get("kind") == "project_root":
            self._refresh_project_root_workspace()
            return

        self._handle_selection_changed()

    def _rebuild_tree(self) -> None:
        self._tree.clear()
        root_label = self._project_file_path.name if self._project_file_path else f"{self._project.project_name}{CIV_FILE_EXTENSION}"
        root = QTreeWidgetItem([root_label])
        root.setData(0, Qt.ItemDataRole.UserRole, {"kind": "project_root", "name": self._project.project_name})
        root.setExpanded(True)

        for section in CIV_SECTION_ORDER:
            section_item = QTreeWidgetItem([section])
            if section in CIV_DIRECT_WORKSPACE_SECTIONS:
                section_item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "section_leaf", "section": section})
            else:
                section_item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "section_group", "section": section})
                entries = self._project.sections.get(section, [])
                if isinstance(entries, list):
                    for index, entry in enumerate(entries):
                        child_name = self._resolve_entry_name(entry, index)
                        child_item = QTreeWidgetItem([child_name])
                        child_item.setData(
                            0,
                            Qt.ItemDataRole.UserRole,
                            {
                                "kind": "section_item",
                                "section": section,
                                "index": index,
                                "entry_name": child_name,
                            },
                        )
                        section_item.addChild(child_item)
            root.addChild(section_item)

        self._tree.addTopLevelItem(root)
        self._tree.expandItem(root)
        self._tree.setCurrentItem(root)

    def _build_group_data_preview_text(self, section: str, fmt: str) -> str:
        if section == "文明":
            data_sql, _text_sql = self._build_civilization_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "领袖":
            data_sql, _text_sql = self._build_leader_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "区域":
            data_sql, _text_sql = self._build_district_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "建筑":
            data_sql, _text_sql = self._build_building_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "单位":
            unit_sql, ability_sql, _text_sql = self._build_unit_sql_bundle()
            if fmt == "xml":
                return {
                    "Units.xml": self._sql_preview_to_xml(unit_sql),
                    "UnitAbilities.xml": self._sql_preview_to_xml(ability_sql),
                }
            return {
                "Units.sql": unit_sql,
                "UnitAbilities.sql": ability_sql,
            }

        if section == "改良设施":
            data_sql, _text_sql = self._build_improvement_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "总督":
            data_sql, _text_sql = self._build_governor_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "伟人":
            data_sql, greatwork_sql, _text_sql = self._build_great_people_sql_bundle()
            if fmt == "xml":
                return {
                    "GreatPeople.xml": self._sql_preview_to_xml(data_sql),
                    "GreatWorks.xml": self._sql_preview_to_xml(greatwork_sql),
                }
            return {
                "GreatPeople.sql": data_sql,
                "GreatWorks.sql": greatwork_sql,
            }

        if section == "政策卡":
            data_sql, _text_sql = self._build_policy_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "项目":
            data_sql, _text_sql = self._build_project_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section == "信仰":
            data_sql, _text_sql = self._build_belief_sql_pair()
            if fmt == "xml":
                return self._sql_preview_to_xml(data_sql)
            return data_sql

        if section != "文明":
            base_name = {
                "领袖": "Leaders",
                "区域": "Districts",
                "建筑": "Buildings",
                "单位": "Units",
                "改良设施": "Improvements",
                "总督": "Governors",
                "伟人": "GreatPeople",
                "政策卡": "Policies",
                "项目": "Projects",
                "信仰": "Beliefs",
                "议程": "Agendas",
            }.get(section, section)
            return f"-- {base_name}.{fmt} 预览\n-- 该分类生成逻辑待接入"

        return ""

    def _build_text_workspace_preview(self, fmt: str) -> str:
        _civ_data_sql, civ_text_sql = self._build_civilization_sql_pair()
        _leader_data_sql, leader_text_sql = self._build_leader_sql_pair()
        _district_data_sql, district_text_sql = self._build_district_sql_pair()
        _building_data_sql, building_text_sql = self._build_building_sql_pair()
        _unit_data_sql, unit_text_sql = self._build_unit_sql_pair()
        _improvement_data_sql, improvement_text_sql = self._build_improvement_sql_pair()
        _governor_data_sql, governor_text_sql = self._build_governor_sql_pair()
        _great_people_data_sql, _greatwork_data_sql, great_people_text_sql = self._build_great_people_sql_bundle()
        _policy_data_sql, policy_text_sql = self._build_policy_sql_pair()
        _project_data_sql, project_text_sql = self._build_project_sql_pair()
        _belief_data_sql, belief_text_sql = self._build_belief_sql_pair()

        civ_infos = self._extract_localized_row_infos(civ_text_sql)
        leader_infos = self._extract_localized_row_infos(leader_text_sql)
        district_infos = self._extract_localized_row_infos(district_text_sql)
        building_infos = self._extract_localized_row_infos(building_text_sql)
        unit_infos = self._extract_localized_row_infos(unit_text_sql)
        improvement_infos = self._extract_localized_row_infos(improvement_text_sql)
        governor_infos = self._extract_localized_row_infos(governor_text_sql)
        great_people_infos = self._extract_localized_row_infos(great_people_text_sql)
        policy_infos = self._extract_localized_row_infos(policy_text_sql)
        project_infos = self._extract_localized_row_infos(project_text_sql)
        belief_infos = self._extract_localized_row_infos(belief_text_sql)

        civ_entries = self._project.sections.get("文明")
        civ_entries = [entry for entry in civ_entries if isinstance(entry, dict)] if isinstance(civ_entries, list) else []
        leader_entries = self._project.sections.get("领袖")
        leader_entries = [entry for entry in leader_entries if isinstance(entry, dict)] if isinstance(leader_entries, list) else []

        def _entry_name(entry: dict[str, object], key: str, fallback: str) -> str:
            value = str(entry.get(key) or "").strip()
            if value:
                return value
            alt = str(entry.get("name") or "").strip()
            return alt or fallback

        civ_base_groups: list[tuple[str, list[str]]] = []
        civ_city_groups: list[tuple[str, list[str]]] = []
        civ_citizen_groups: list[tuple[str, list[str]]] = []
        for index, entry in enumerate(civ_entries, start=1):
            civ_type = str(entry.get("type") or "").strip() or f"CIVILIZATION_CUSTOM_{index}"
            loc_core = civ_type[13:] if civ_type.startswith("CIVILIZATION_") else civ_type
            name = _entry_name(entry, "civilization_name", civ_type)
            civ_base_groups.append(
                (
                    name,
                    [
                        row for row, tag, _text in civ_infos
                        if civ_type in tag and "_CITY_NAME_" not in tag and "_CITIZEN_NAME_" not in tag
                    ],
                )
            )
            civ_city_groups.append(
                (
                    name,
                    [
                        row for row, tag, _text in civ_infos
                        if f"LOC_{loc_core}_CITY_NAME_" in tag
                    ],
                )
            )
            civ_citizen_groups.append(
                (
                    name,
                    [
                        row for row, tag, _text in civ_infos
                        if f"LOC_{loc_core}_CITIZEN_NAME_" in tag
                    ],
                )
            )

        leader_base_groups: list[tuple[str, list[str]]] = []
        leader_diplomacy_groups: list[tuple[str, list[str]]] = []
        for index, entry in enumerate(leader_entries, start=1):
            leader_type = str(entry.get("type") or "").strip() or f"LEADER_CUSTOM_{index}"
            name = _entry_name(entry, "leader_name", leader_type)
            short_type = leader_type[7:] if leader_type.startswith("LEADER_") else leader_type
            capital_tag = f"LOC_CITY_NAME_{short_type}_CAPITAL" if short_type else f"LOC_CITY_NAME_LEADER_{index}_CAPITAL"
            quote_tag = f"LOC_PEDIA_LEADERS_PAGE_{short_type}_QUOTE" if short_type else f"LOC_PEDIA_LEADERS_PAGE_LEADER_{index}_QUOTE"
            diplomacy_rows = entry.get("diplomacy") if isinstance(entry.get("diplomacy"), list) else []
            diplomacy_tags = {
                str(row.get("tag") or "").strip()
                for row in diplomacy_rows
                if isinstance(row, dict) and str(row.get("tag") or "").strip()
            }

            leader_base_groups.append(
                (
                    name,
                    [
                        row for row, tag, _text in leader_infos
                        if ((leader_type in tag) or (tag in {capital_tag, quote_tag})) and tag not in diplomacy_tags
                    ],
                )
            )
            leader_diplomacy_groups.append(
                (
                    name,
                    [
                        row for row, tag, _text in leader_infos
                        if tag in diplomacy_tags
                    ],
                )
            )

        def _groups_by_section(section_name: str, infos: list[tuple[str, str, str]]) -> list[tuple[str, list[str]]]:
            entries = self._project.sections.get(section_name)
            section_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
            groups: list[tuple[str, list[str]]] = []
            for idx, item in enumerate(section_entries, start=1):
                entity_type = str(item.get("type") or "").strip() or f"{section_name}_CUSTOM_{idx}"
                display_name = _entry_name(item, "name", entity_type)
                groups.append((display_name, [row for row, tag, _text in infos if entity_type in tag]))
            return groups

        # 区域基础文本：除常规 LOC_{DistrictType}_* 外，还需要包含“自定义相邻加成”的描述文本。
        # 这些 Tag 形如 LOC_<AdjacencyId>_DESCRIPTION，并不包含 DistrictType，因此不能只靠 entity_type in tag。
        district_entries = self._project.sections.get("区域")
        district_section_entries = [entry for entry in district_entries if isinstance(entry, dict)] if isinstance(district_entries, list) else []
        district_groups: list[tuple[str, list[str]]] = []
        used_rows: set[str] = set()
        for idx, item in enumerate(district_section_entries, start=1):
            district_type = str(item.get("type") or "").strip() or f"区域_CUSTOM_{idx}"
            display_name = _entry_name(item, "name", district_type)

            subtables = item.get("subtables") if isinstance(item.get("subtables"), dict) else {}
            adjacency_payload = subtables.get("District_Adjacencies") if isinstance(subtables.get("District_Adjacencies"), list) else None
            if adjacency_payload is None:
                adjacency_payload = item.get("adjacencies") if isinstance(item.get("adjacencies"), list) else []

            custom_adj_tags: set[str] = set()
            for adj in adjacency_payload:
                if not isinstance(adj, dict):
                    continue
                mode = str(adj.get("mode") or adj.get("type") or "").strip().lower()
                if mode != "custom":
                    continue
                adj_id = str(adj.get("id") or "").strip()
                if not adj_id:
                    continue
                custom_adj_tags.add(f"LOC_{adj_id.upper()}_DESCRIPTION")

            rows: list[str] = []
            for row, tag, _text in district_infos:
                if (district_type in tag) or (tag in custom_adj_tags):
                    if row in used_rows:
                        continue
                    rows.append(row)
                    used_rows.add(row)
            district_groups.append((display_name, rows))
        building_groups = _groups_by_section("建筑", building_infos)

        # 单位基础文本：不包含 UnitAbility 的 LOC_ABILITY_*，避免与后续“单位Ability文本”重复。
        unit_entries = self._project.sections.get("单位")
        unit_section_entries = [entry for entry in unit_entries if isinstance(entry, dict)] if isinstance(unit_entries, list) else []
        unit_groups: list[tuple[str, list[str]]] = []
        for idx, item in enumerate(unit_section_entries, start=1):
            entity_type = str(item.get("type") or "").strip() or f"单位_CUSTOM_{idx}"
            display_name = _entry_name(item, "name", entity_type)
            unit_groups.append(
                (
                    display_name,
                    [
                        row
                        for row, tag, _text in unit_infos
                        if (entity_type in tag) and (not tag.startswith("LOC_ABILITY_"))
                    ],
                )
            )
        improvement_groups = _groups_by_section("改良设施", improvement_infos)

        governor_section_entries = self._project.sections.get("总督")
        governor_section_entries = [entry for entry in governor_section_entries if isinstance(entry, dict)] if isinstance(governor_section_entries, list) else []
        governor_groups: list[tuple[str, list[str]]] = []
        for idx, item in enumerate(governor_section_entries, start=1):
            governor_type = str(item.get("GovernorType") or item.get("type") or "").strip() or f"GOVERNOR_CUSTOM_{idx}"
            display_name = _entry_name(item, "Name", governor_type)
            trait_type = str(item.get("TraitType") or item.get("trait_type") or "").strip()
            trait_tags = {
                f"LOC_{trait_type}_NAME",
                f"LOC_{trait_type}_DESCRIPTION",
            } if trait_type else set()
            governor_groups.append(
                (
                    display_name,
                    [
                        row
                        for row, tag, _text in governor_infos
                        if (governor_type in tag) or (tag in trait_tags)
                    ],
                )
            )
        great_people_groups = _groups_by_section("伟人", great_people_infos)
        policy_groups = _groups_by_section("政策卡", policy_infos)
        belief_groups = _groups_by_section("信仰", belief_infos)
        project_groups = _groups_by_section("项目", project_infos)
        agenda_groups: list[tuple[str, list[str]]] = []

        # 额外文本：UnitAbility / ModifierStrings 等不一定包含“单位type”的 Tag，
        # 若仅按 entity_type in tag 过滤，会导致它们在 Text 预览里缺失。
        ability_text_groups: list[tuple[str, list[str]]] = []
        ability_rows_by_type: dict[str, list[str]] = {}
        for row, tag, _text in unit_infos:
            if not tag.startswith("LOC_ABILITY_"):
                continue
            base = tag[len("LOC_"):]
            for suffix in ("_NAME", "_DESCRIPTION"):
                if base.endswith(suffix):
                    base = base[: -len(suffix)]
                    break
            ability_rows_by_type.setdefault(base, []).append(row)
        for ability_type in sorted(ability_rows_by_type.keys()):
            ability_text_groups.append((ability_type, ability_rows_by_type[ability_type]))

        modifier_preview_groups: list[tuple[str, list[str]]] = []
        modifier_rows_by_id: dict[str, list[str]] = {}
        for row, tag, _text in unit_infos:
            if not (tag.startswith("LOC_MODIFIER_") and tag.endswith("_PREVIEW")):
                continue
            base = tag[len("LOC_") : -len("_PREVIEW")].strip()
            modifier_rows_by_id.setdefault(base or "MODIFIER", []).append(row)
        for modifier_id in sorted(modifier_rows_by_id.keys()):
            modifier_preview_groups.append((modifier_id, modifier_rows_by_id[modifier_id]))

        sections: list[tuple[str, list[tuple[str, list[str]]]]] = [
            ("文明基础文本", civ_base_groups),
            ("领袖基础文本", leader_base_groups),
            ("区域基础文本", district_groups),
            ("建筑基础文本", building_groups),
            ("单位基础文本", unit_groups),
            ("单位Ability文本", ability_text_groups),
            ("修改器预览文本", modifier_preview_groups),
            ("改良基础文本", improvement_groups),
            ("总督基础文本", governor_groups),
            ("伟人基础文本", great_people_groups),
            ("政策卡基础文本", policy_groups),
            ("信仰基础文本", belief_groups),
            ("项目基础文本", project_groups),
            ("议程基础文本", agenda_groups),
            ("文明城市文本", civ_city_groups),
            ("文明市民文本", civ_citizen_groups),
            ("领袖外交文本", leader_diplomacy_groups),
        ]

        ordered_rows: list[str] = []
        for _title, groups in sections:
            for _name, rows in groups:
                ordered_rows.extend(rows)
        ordered_rows = self._deduplicate_rows(ordered_rows)

        if not ordered_rows:
            text_sql = "-- Text.sql\n-- 暂无文本数据"
        else:
            total_rows = len(ordered_rows)
            current = 0
            lines = [
                "-- Text.sql",
                "",
                "-- LocalizedText 表",
                "INSERT INTO LocalizedText (Language, Tag, Text) VALUES",
            ]
            non_empty_sections = [(title, groups) for title, groups in sections if any(rows for _name, rows in groups)]
            for sec_idx, (title, groups) in enumerate(non_empty_sections):
                lines.append(f"-- {title}")
                non_empty_groups = [(name, rows) for name, rows in groups if rows]
                for group_idx, (name, rows) in enumerate(non_empty_groups):
                    lines.append(f"-- {name}")
                    for row in rows:
                        current += 1
                        suffix = "," if current < total_rows else ";"
                        lines.append(f"{row}{suffix}")
                    if group_idx < len(non_empty_groups) - 1:
                        lines.append("")
                if sec_idx < len(non_empty_sections) - 1:
                    lines.extend(["", ""])  # 三换行分隔不同文本类别
            text_sql = "\n".join(lines).rstrip()

        LOGGER.info(
            "[TextPreview] ordered rows civ_base=%d leader_base=%d district=%d building=%d unit=%d improvement=%d governor=%d great_people=%d policy=%d belief=%d project=%d agenda=%d civ_city=%d civ_citizen=%d leader_diplomacy=%d total=%d",
            sum(len(rows) for _name, rows in civ_base_groups),
            sum(len(rows) for _name, rows in leader_base_groups),
            sum(len(rows) for _name, rows in district_groups),
            sum(len(rows) for _name, rows in building_groups),
            sum(len(rows) for _name, rows in unit_groups),
            sum(len(rows) for _name, rows in improvement_groups),
            sum(len(rows) for _name, rows in governor_groups),
            sum(len(rows) for _name, rows in great_people_groups),
            sum(len(rows) for _name, rows in policy_groups),
            sum(len(rows) for _name, rows in belief_groups),
            sum(len(rows) for _name, rows in project_groups),
            sum(len(rows) for _name, rows in agenda_groups),
            sum(len(rows) for _name, rows in civ_city_groups),
            sum(len(rows) for _name, rows in civ_citizen_groups),
            sum(len(rows) for _name, rows in leader_diplomacy_groups),
            len(ordered_rows),
        )

        if fmt == "xml":
            return self._sql_preview_to_xml(text_sql)
        return text_sql

    def _extract_localized_row_infos(self, text_sql: str) -> list[tuple[str, str, str]]:
        rows = self._extract_insert_rows(text_sql, "LocalizedText")
        output: list[tuple[str, str, str]] = []
        for row in rows:
            tuple_text = row.strip()
            if tuple_text.startswith("(") and tuple_text.endswith(")"):
                tuple_text = tuple_text[1:-1]
            fields = self._split_sql_fields(tuple_text)
            if len(fields) < 3:
                continue
            tag = self._decode_sql_value(fields[1])
            text = self._decode_sql_value(fields[2])
            output.append((row, tag, text))
        return output

    @staticmethod
    def _sql_escape(value: object | None) -> str:
        return str(value or "").replace("'", "''")

    @staticmethod
    def _deduplicate_rows(rows: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for row in rows:
            if row in seen:
                continue
            seen.add(row)
            output.append(row)
        return output

    @staticmethod
    def _normalize_selector_type(raw: object | None) -> str:
        text = str(raw or "").strip()
        if not text:
            return ""
        if "(" in text and ")" in text and text.index("(") < text.index(")"):
            inner = text[text.index("(") + 1 : text.index(")")].strip()
            if inner:
                return inner
        return text

    @staticmethod
    def _collect_city_names(entry: dict[str, object]) -> list[str]:
        city = entry.get("city_info") if isinstance(entry.get("city_info"), dict) else {}
        mode_index = int(city.get("mode_index", 0) or 0)
        if mode_index == 1:
            source = city.get("custom_entries") if isinstance(city.get("custom_entries"), list) else []
        elif mode_index == 2:
            source = city.get("random_entries") if isinstance(city.get("random_entries"), list) else []
        else:
            source = city.get("existing_entries") if isinstance(city.get("existing_entries"), list) else []
        return [str(item).strip() for item in source if str(item).strip()]

    @staticmethod
    def _collect_citizens(entry: dict[str, object]) -> list[tuple[str, bool, bool]]:
        citizen = entry.get("citizen_info") if isinstance(entry.get("citizen_info"), dict) else {}
        mode_index = int(citizen.get("mode_index", 0) or 0)
        if mode_index == 1:
            source = citizen.get("custom_entries") if isinstance(citizen.get("custom_entries"), list) else []
        elif mode_index == 2:
            source = citizen.get("random_entries") if isinstance(citizen.get("random_entries"), list) else []
        else:
            source = citizen.get("existing_entries") if isinstance(citizen.get("existing_entries"), list) else []

        rows: list[tuple[str, bool, bool]] = []
        for item in source:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            rows.append((name, bool(item.get("female", False)), bool(item.get("modern", False))))
        return rows

    @staticmethod
    def _build_insert_block(comment: str, table: str, columns: list[str], rows: list[str]) -> str:
        if not rows:
            return ""
        lines = [
            f"-- {comment}",
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES",
            ",\n".join(rows) + ";",
            "",
        ]
        return "\n".join(lines)

    def _art_moments_map(self) -> dict[str, dict[str, object]]:
        """读取“美术”工作区保存的 Moments 配置。"""

        payload = self._art_workspace.export_project_payload()
        if not isinstance(payload, dict):
            return {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        raw = data.get("moments_map") if isinstance(data, dict) else {}
        if not isinstance(raw, dict):
            return {}
        output: dict[str, dict[str, object]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            key = str(k or "").strip()
            if not key:
                continue
            output[key] = v
        return output

    @staticmethod
    def _moment_state_key(entity: str, game_data_type: str) -> str:
        return f"moment:{entity}:{game_data_type}"

    @staticmethod
    def _moment_output_stem(game_data_type: str) -> str:
        safe = str(game_data_type or "").strip()
        return f"Moment_{safe}" if safe else ""

    def _iter_moment_bindable_items(self) -> list[dict[str, str]]:
        """列出可生成 Moments 的对象（导出用）。"""

        output: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        def _add(entity: str, game_data_type: str, illustration: str, data_type: str) -> None:
            key = (entity, game_data_type)
            if not game_data_type or key in seen:
                return
            seen.add(key)
            output.append(
                {
                    "entity": entity,
                    "game_data_type": game_data_type,
                    "moment_illustration_type": illustration,
                    "moment_data_type": data_type,
                }
            )
        def _extract_trait_type(entry: dict[str, object]) -> str:
            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            return str(
                table_data.get("TraitType")
                or entry.get("TraitType")
                or entry.get("trait_type")
                or entry.get("traitType")
                or ""
            ).strip()

        for section, entity, illustration, data_type in [
            ("区域", "district", "MOMENT_ILLUSTRATION_UNIQUE_DISTRICT", "MOMENT_DATA_DISTRICT"),
            ("建筑", "building", "MOMENT_ILLUSTRATION_UNIQUE_BUILDING", "MOMENT_DATA_BUILDING"),
            ("单位", "unit", "MOMENT_ILLUSTRATION_UNIQUE_UNIT", "MOMENT_DATA_UNIT"),
            ("改良设施", "improvement", "MOMENT_ILLUSTRATION_UNIQUE_IMPROVEMENT", "MOMENT_DATA_IMPROVEMENT"),
        ]:
            for entry in self._iter_section_entries(section):
                type_name = str(entry.get("type") or "").strip()
                if not type_name:
                    continue
                trait_type = _extract_trait_type(entry)
                if not trait_type:
                    continue
                _add(entity, type_name, illustration, data_type)

        for entry in self._iter_section_entries("总督"):
            governor_type = str(entry.get("GovernorType") or entry.get("type") or "").strip()
            if not governor_type:
                continue
            _add("governor", governor_type, "MOMENT_ILLUSTRATION_GOVERNOR", "MOMENT_DATA_GOVERNOR")

        for entry in self._iter_section_entries("伟人"):
            unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
            unit_type = str(unit_data.get("UnitType") or entry.get("unit_type") or "").strip()
            trait_type = str(unit_data.get("TraitType") or "").strip()
            if not unit_type or not trait_type:
                continue
            _add("unit", unit_type, "MOMENT_ILLUSTRATION_UNIQUE_UNIT", "MOMENT_DATA_UNIT")

        output.sort(key=lambda r: (r["entity"], r["game_data_type"]))
        return output

    def _build_moments_sql_preview(self) -> str:
        moments_map = self._art_moments_map()
        rows: list[str] = []
        for item in self._iter_moment_bindable_items():
            entity = item["entity"]
            game_data_type = item["game_data_type"]
            illustration = item["moment_illustration_type"]
            data_type = item["moment_data_type"]

            key = self._moment_state_key(entity, game_data_type)
            meta = moments_map.get(key, {})
            mode = str(meta.get("mode") or "import").strip().lower()

            if mode == "db":
                texture = str(meta.get("db_texture") or "").strip()
                if not texture:
                    continue
            else:
                stem = self._moment_output_stem(game_data_type)
                if not stem:
                    continue
                # 兼容：Texture 字段写逻辑名，不附带 .dds 后缀。
                # 即使导入模式尚未选图，也保留 SQL 行（图片导入环节可后续补齐）。
                texture = stem

            rows.append(
                "(" + ",".join(
                    [
                        f"'{self._sql_escape(illustration)}'",
                        f"'{self._sql_escape(data_type)}'",
                        f"'{self._sql_escape(game_data_type)}'",
                        f"'{self._sql_escape(texture)}'",
                    ]
                ) + ")"
            )

        if not rows:
            return "-- Moments.sql\n-- 暂无历史时刻插画数据\n"

        sql = "\n".join(
            [
                "-- Moments.sql",
                "",
                self._build_insert_block(
                    "MomentIllustrations",
                    "MomentIllustrations",
                    ["MomentIllustrationType", "MomentDataType", "GameDataType", "Texture"],
                    rows,
                ).rstrip(),
                "",
            ]
        )
        return sql

    def _collect_moment_image_plans(self) -> list[dict[str, object]]:
        """Moments 导入图模式的 456x332 PNG 输出计划。"""

        moments_map = self._art_moments_map()
        plans: list[dict[str, object]] = []
        for item in self._iter_moment_bindable_items():
            entity = item["entity"]
            game_data_type = item["game_data_type"]
            key = self._moment_state_key(entity, game_data_type)
            meta = moments_map.get(key, {})
            mode = str(meta.get("mode") or "import").strip().lower()
            if mode == "db":
                continue

            image = meta.get("image") if isinstance(meta.get("image"), dict) else {}
            source_path = str(image.get("path") or "").strip()
            stem = self._moment_output_stem(game_data_type)
            if not stem:
                continue
            plans.append(
                {
                    "relative_path": f"IMG/{stem}.png",
                    "target_width": 456,
                    "target_height": 332,
                    "source_state": image if isinstance(image, dict) else {},
                    "source_path": source_path,
                    "category": "moment",
                }
            )
        return plans

    @staticmethod
    def _extract_insert_rows(sql_text: str, table: str) -> list[str]:
        pattern = re.compile(
            rf"INSERT\s+INTO\s+{re.escape(table)}\s*\((.*?)\)\s*VALUES\s*(.*?);",
            re.IGNORECASE | re.DOTALL,
        )
        rows: list[str] = []
        for match in pattern.finditer(sql_text):
            values_blob = match.group(2)
            tuples = WorkspacePage._split_sql_tuples(values_blob)
            rows.extend([f"({item.strip()})" for item in tuples if item.strip()])
        return rows

    def _build_civilization_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("文明")
        civ_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not civ_entries:
            return "-- Civilizations.sql\n-- 暂无文明数据", "-- Text.sql\n-- 暂无文明文本数据"

        great_people_entries = self._project.sections.get("伟人")
        great_person_trait_map: dict[str, str] = {}
        if isinstance(great_people_entries, list):
            for gp_entry in great_people_entries:
                if not isinstance(gp_entry, dict):
                    continue
                class_data = gp_entry.get("class_data") if isinstance(gp_entry.get("class_data"), dict) else {}
                unit_data = gp_entry.get("unit_data") if isinstance(gp_entry.get("unit_data"), dict) else {}
                class_type = str(class_data.get("GreatPersonClassType") or gp_entry.get("type") or "").strip()
                unit_type = str(unit_data.get("UnitType") or class_data.get("UnitType") or "").strip()
                unit_trait_type = str(unit_data.get("TraitType") or "").strip()
                if not unit_trait_type:
                    continue
                if class_type:
                    great_person_trait_map[class_type] = unit_trait_type
                if unit_type:
                    great_person_trait_map[unit_type] = unit_trait_type

        governor_entries = self._project.sections.get("总督")
        governor_trait_map: dict[str, str] = {}
        if isinstance(governor_entries, list):
            for governor_entry in governor_entries:
                if not isinstance(governor_entry, dict):
                    continue
                if not bool(governor_entry.get("new_trait_type", False)):
                    continue
                governor_type = str(governor_entry.get("GovernorType") or governor_entry.get("type") or "").strip()
                governor_trait = str(governor_entry.get("TraitType") or governor_entry.get("trait_type") or "").strip()
                if governor_type and governor_trait:
                    governor_trait_map[governor_type] = governor_trait

        types_rows: list[str] = []
        traits_rows: list[str] = []
        civ_rows: list[str] = []
        civ_trait_rows: list[str] = []
        city_rows: list[str] = []
        citizen_rows: list[str] = []
        bias_feature_rows: list[str] = []
        bias_terrain_rows: list[str] = []
        bias_resource_rows: list[str] = []
        bias_river_rows: list[str] = []

        text_rows: list[str] = []
        mapped_great_person_bindings = 0
        fallback_great_person_bindings = 0

        for index, entry in enumerate(civ_entries, start=1):
            civ_type = str(entry.get("type") or "").strip()
            if not civ_type:
                civ_type = f"CIVILIZATION_CUSTOM_{index}"

            trait_type = f"TRAIT_{civ_type}"
            loc_core = civ_type[13:] if civ_type.startswith("CIVILIZATION_") else civ_type

            level = str(entry.get("level") or "CIVILIZATION_LEVEL_FULL_CIV").strip() or "CIVILIZATION_LEVEL_FULL_CIV"
            ethnicity = str(entry.get("ethnicity") or "ETHNICITY_ASIAN").strip() or "ETHNICITY_ASIAN"
            try:
                city_depth = max(1, int(entry.get("city_name_depth", 10) or 10))
            except (TypeError, ValueError):
                city_depth = 10

            civ_name = str(entry.get("civilization_name") or entry.get("name") or "").strip()
            civ_desc = str(entry.get("civilization_description") or "").strip()
            civ_adj = str(entry.get("civilization_adjective") or "").strip()
            trait_name = str(entry.get("trait_name") or "").strip()
            trait_desc = str(entry.get("trait_description") or "").strip()

            types_rows.append(f"('{civ_type}', 'KIND_CIVILIZATION')")
            types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")

            traits_rows.append(
                f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')"
            )

            civ_rows.append(
                "(" +
                f"'{civ_type}', 'LOC_{civ_type}_NAME', 'LOC_{civ_type}_DESCRIPTION', 'LOC_{civ_type}_ADJECTIVE', "
                f"'{level}', '{ethnicity}', {city_depth}" +
                ")"
            )

            civ_trait_rows.append(f"('{civ_type}', '{trait_type}')")
            trait_bindings = entry.get("trait_bindings") if isinstance(entry.get("trait_bindings"), list) else []
            for binding in trait_bindings:
                section = ""
                if isinstance(binding, dict):
                    section = str(binding.get("section") or "").strip()
                    target_type = str(binding.get("type") or "").strip()
                else:
                    target_type = str(binding or "").strip()
                if not target_type:
                    continue
                if target_type.startswith("TRAIT_"):
                    trait_code = target_type
                elif section == "总督":
                    mapped_trait = governor_trait_map.get(target_type)
                    if mapped_trait:
                        trait_code = mapped_trait
                    else:
                        trait_code = f"TRAIT_{target_type}"
                elif section == "伟人" or target_type.startswith("GREAT_PERSON_CLASS_"):
                    mapped_trait = great_person_trait_map.get(target_type)
                    if mapped_trait:
                        trait_code = mapped_trait
                        mapped_great_person_bindings += 1
                    else:
                        trait_code = f"TRAIT_{target_type}"
                        fallback_great_person_bindings += 1
                else:
                    trait_code = f"TRAIT_{target_type}"
                civ_trait_rows.append(f"('{civ_type}', '{trait_code}')")

            text_rows.append(f"('zh_Hans_CN','LOC_{civ_type}_NAME','{self._sql_escape(civ_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{civ_type}_DESCRIPTION','{self._sql_escape(civ_desc)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{civ_type}_ADJECTIVE','{self._sql_escape(civ_adj)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{self._sql_escape(trait_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{self._sql_escape(trait_desc)}')")

            city_names = self._collect_city_names(entry)
            for city_idx, city_name in enumerate(city_names, start=1):
                city_tag = f"LOC_{loc_core}_CITY_NAME_{city_idx}"
                city_rows.append(f"('{civ_type}', '{city_tag}')")
                text_rows.append(f"('zh_Hans_CN','{city_tag}','{self._sql_escape(city_name)}')")

            citizen_names = self._collect_citizens(entry)
            for citizen_idx, (name, female, modern) in enumerate(citizen_names, start=1):
                citizen_tag = f"LOC_{loc_core}_CITIZEN_NAME_{citizen_idx}"
                citizen_rows.append(f"('{civ_type}', '{citizen_tag}', {1 if female else 0}, {1 if modern else 0})")
                text_rows.append(f"('zh_Hans_CN','{citizen_tag}','{self._sql_escape(name)}')")

            start_bias = entry.get("start_bias") if isinstance(entry.get("start_bias"), dict) else {}
            terrains = start_bias.get("terrains") if isinstance(start_bias.get("terrains"), list) else []
            for item in terrains:
                if not isinstance(item, dict):
                    continue
                selector = item.get("selector_value")
                if not selector and isinstance(item.get("selector_data"), dict):
                    selector_data = item.get("selector_data") or {}
                    selector = next((v for v in selector_data.values() if str(v or "").strip()), "")
                terrain_type = self._normalize_selector_type(selector)
                if not terrain_type:
                    continue
                try:
                    tier = max(1, int(item.get("tier", 1) or 1))
                except (TypeError, ValueError):
                    tier = 1
                bias_terrain_rows.append(f"('{civ_type}', '{terrain_type}', {tier})")

            features = start_bias.get("features") if isinstance(start_bias.get("features"), list) else []
            for item in features:
                if not isinstance(item, dict):
                    continue
                selector = item.get("selector_value")
                if not selector and isinstance(item.get("selector_data"), dict):
                    selector_data = item.get("selector_data") or {}
                    selector = next((v for v in selector_data.values() if str(v or "").strip()), "")
                feature_type = self._normalize_selector_type(selector)
                if not feature_type:
                    continue
                try:
                    tier = max(1, int(item.get("tier", 1) or 1))
                except (TypeError, ValueError):
                    tier = 1
                bias_feature_rows.append(f"('{civ_type}', '{feature_type}', {tier})")

            resources = start_bias.get("resources") if isinstance(start_bias.get("resources"), list) else []
            for item in resources:
                if not isinstance(item, dict):
                    continue
                selector = item.get("selector_value")
                if not selector and isinstance(item.get("selector_data"), dict):
                    selector_data = item.get("selector_data") or {}
                    selector = next((v for v in selector_data.values() if str(v or "").strip()), "")
                resource_type = self._normalize_selector_type(selector)
                if not resource_type:
                    continue
                try:
                    tier = max(1, int(item.get("tier", 1) or 1))
                except (TypeError, ValueError):
                    tier = 1
                bias_resource_rows.append(f"('{civ_type}', '{resource_type}', {tier})")

            if bool(start_bias.get("river_enabled", False)):
                try:
                    river_tier = max(1, int(start_bias.get("river_tier", 1) or 1))
                except (TypeError, ValueError):
                    river_tier = 1
                bias_river_rows.append(f"('{civ_type}', {river_tier})")

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        civ_trait_rows = self._deduplicate_rows(civ_trait_rows)

        sql_blocks = [
            "-- Civilizations.sql",
            "",
            self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows),
            self._build_insert_block("Traits", "Traits", ["TraitType", "Name", "Description"], traits_rows),
            self._build_insert_block(
                "Civilizations",
                "Civilizations",
                ["CivilizationType", "Name", "Description", "Adjective", "StartingCivilizationLevelType", "Ethnicity", "RandomCityNameDepth"],
                civ_rows,
            ),
            self._build_insert_block("CivilizationTraits", "CivilizationTraits", ["CivilizationType", "TraitType"], civ_trait_rows),
            self._build_insert_block("CityNames", "CityNames", ["CivilizationType", "CityName"], city_rows),
            self._build_insert_block(
                "CivilizationCitizenNames",
                "CivilizationCitizenNames",
                ["CivilizationType", "CitizenName", "Female", "Modern"],
                citizen_rows,
            ),
            self._build_insert_block("StartBiasFeatures", "StartBiasFeatures", ["CivilizationType", "FeatureType", "Tier"], bias_feature_rows),
            self._build_insert_block("StartBiasTerrains", "StartBiasTerrains", ["CivilizationType", "TerrainType", "Tier"], bias_terrain_rows),
            self._build_insert_block("StartBiasResources", "StartBiasResources", ["CivilizationType", "ResourceType", "Tier"], bias_resource_rows),
            self._build_insert_block("StartBiasRivers", "StartBiasRivers", ["CivilizationType", "Tier"], bias_river_rows),
        ]
        data_sql = "\n".join([block for block in sql_blocks if block.strip()]).rstrip()

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        LOGGER.info(
            "Built civilization SQL preview: civ_entries=%d mapped_gp_bindings=%d fallback_gp_bindings=%d",
            len(civ_entries),
            mapped_great_person_bindings,
            fallback_great_person_bindings,
        )
        return data_sql, text_sql

    def _build_leader_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("领袖")
        leader_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not leader_entries:
            return "-- Leaders.sql\n-- 暂无领袖数据", "-- Text.sql\n-- 暂无领袖文本数据"

        great_people_entries = self._project.sections.get("伟人")
        great_person_trait_map: dict[str, str] = {}
        if isinstance(great_people_entries, list):
            for gp_entry in great_people_entries:
                if not isinstance(gp_entry, dict):
                    continue
                class_data = gp_entry.get("class_data") if isinstance(gp_entry.get("class_data"), dict) else {}
                unit_data = gp_entry.get("unit_data") if isinstance(gp_entry.get("unit_data"), dict) else {}
                class_type = str(class_data.get("GreatPersonClassType") or gp_entry.get("type") or "").strip()
                unit_type = str(unit_data.get("UnitType") or class_data.get("UnitType") or "").strip()
                unit_trait_type = str(unit_data.get("TraitType") or "").strip()
                if not unit_trait_type:
                    continue
                if class_type:
                    great_person_trait_map[class_type] = unit_trait_type
                if unit_type:
                    great_person_trait_map[unit_type] = unit_trait_type

        governor_entries = self._project.sections.get("总督")
        governor_trait_map: dict[str, str] = {}
        if isinstance(governor_entries, list):
            for governor_entry in governor_entries:
                if not isinstance(governor_entry, dict):
                    continue
                if not bool(governor_entry.get("new_trait_type", False)):
                    continue
                governor_type = str(governor_entry.get("GovernorType") or governor_entry.get("type") or "").strip()
                governor_trait = str(governor_entry.get("TraitType") or governor_entry.get("trait_type") or "").strip()
                if governor_type and governor_trait:
                    governor_trait_map[governor_type] = governor_trait

        types_rows: list[str] = []
        traits_rows: list[str] = []
        leaders_rows: list[str] = []
        civilization_leaders_rows: list[str] = []
        quotes_rows: list[str] = []
        leader_traits_rows: list[str] = []
        loading_rows: list[str] = []
        image_comments: list[str] = []
        text_rows: list[str] = []

        for index, entry in enumerate(leader_entries, start=1):
            leader_type = str(entry.get("type") or "").strip()
            if not leader_type:
                leader_type = f"LEADER_CUSTOM_{index}"

            short_type = leader_type[7:] if leader_type.startswith("LEADER_") else leader_type
            trait_type = f"TRAIT_LEADER_{short_type}" if short_type else f"TRAIT_LEADER_CUSTOM_{index}"

            leader_name = str(entry.get("leader_name") or entry.get("name") or "").strip()
            sex = str(entry.get("sex") or "Male").strip() or "Male"
            civilization_type = str(entry.get("civilization_type") or "").strip()
            capital_name = str(entry.get("capital_name") or "").strip()
            leader_text = str(entry.get("leader_text") or "").strip()
            leader_quote = str(entry.get("leader_quote") or "").strip()
            ability_name = str(entry.get("ability_name") or "").strip()
            ability_desc = str(entry.get("ability_description") or "").strip()

            leader_name_tag = f"LOC_{leader_type}_NAME"
            capital_tag = f"LOC_CITY_NAME_{short_type}_CAPITAL" if short_type else f"LOC_CITY_NAME_LEADER_{index}_CAPITAL"
            leader_text_tag = f"LOC_LOADING_INFO_{leader_type}"
            quote_tag = f"LOC_PEDIA_LEADERS_PAGE_{short_type}_QUOTE" if short_type else f"LOC_PEDIA_LEADERS_PAGE_LEADER_{index}_QUOTE"

            types_rows.append(f"('{leader_type}', 'KIND_LEADER')")
            types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")

            traits_rows.append(f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')")

            leaders_rows.append(
                f"('{leader_type}', '{leader_name_tag}', '{self._sql_escape(sex)}', 'LEADER_DEFAULT', '4')"
            )

            if civilization_type:
                civilization_leaders_rows.append(
                    f"('{civilization_type}', '{leader_type}', '{capital_tag}')"
                )

            quotes_rows.append(f"('{leader_type}', '{quote_tag}')")

            leader_traits_rows.append(f"('{leader_type}', '{trait_type}')")
            bindings = entry.get("bindings") if isinstance(entry.get("bindings"), list) else []
            for binding in bindings:
                if not isinstance(binding, dict):
                    continue
                section = str(binding.get("section") or "").strip()
                raw_type = str(binding.get("type") or "").strip()
                if not raw_type:
                    continue
                if raw_type.startswith("TRAIT_"):
                    target_trait = raw_type
                elif section == "总督":
                    target_trait = governor_trait_map.get(raw_type) or f"TRAIT_{raw_type}"
                elif section == "伟人" or raw_type.startswith("GREAT_PERSON_CLASS_"):
                    target_trait = great_person_trait_map.get(raw_type) or f"TRAIT_{raw_type}"
                else:
                    target_trait = f"TRAIT_{raw_type}"
                leader_traits_rows.append(f"('{leader_type}', '{target_trait}')")

            foreground_name = str(entry.get("foreground_image_name") or f"{leader_type}_NEUTRAL").strip()
            background_name = str(entry.get("background_image_name") or f"{leader_type}_BACKGROUND").strip()
            diplo_foreground_name = str(entry.get("diplo_foreground_image_name") or f"FALLBACK_NEUTRAL_{short_type}").strip()
            diplo_background_name = str(entry.get("diplo_background_image_name") or f"{short_type}_1,{short_type}_2,{short_type}_3").strip()

            loading_rows.append(
                f"('{leader_type}', '{self._sql_escape(foreground_name)}', '{self._sql_escape(background_name)}', 1, '{leader_text_tag}')"
            )

            display_name = leader_name or short_type or leader_type
            image_comments.extend(
                [
                    f"--领袖{display_name}加载前景：{foreground_name}",
                    f"--领袖{display_name}加载背景：{background_name}",
                    f"--领袖{display_name}外交肖像：{diplo_foreground_name}",
                    f"--领袖{display_name}外交背景：{diplo_background_name}",
                    "",
                ]
            )

            text_rows.append(f"('zh_Hans_CN','{leader_name_tag}','{self._sql_escape(leader_name)}')")
            text_rows.append(f"('zh_Hans_CN','{capital_tag}','{self._sql_escape(capital_name)}')")
            text_rows.append(f"('zh_Hans_CN','{leader_text_tag}','{self._sql_escape(leader_text)}')")
            text_rows.append(f"('zh_Hans_CN','{quote_tag}','{self._sql_escape(leader_quote)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{self._sql_escape(ability_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{self._sql_escape(ability_desc)}')")

            diplomacy_rows = entry.get("diplomacy") if isinstance(entry.get("diplomacy"), list) else []
            for row in diplomacy_rows:
                if not isinstance(row, dict):
                    continue
                tag = str(row.get("tag") or "").strip()
                text = str(row.get("text") or "").strip()
                if tag and text:
                    text_rows.append(f"('zh_Hans_CN','{self._sql_escape(tag)}','{self._sql_escape(text)}')")

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        civilization_leaders_rows = self._deduplicate_rows(civilization_leaders_rows)
        leader_traits_rows = self._deduplicate_rows(leader_traits_rows)
        text_rows = self._deduplicate_rows(text_rows)

        sql_blocks = [
            "-- Leaders.sql",
            "",
            self._build_insert_block("Types 表", "Types", ["Type", "Kind"], types_rows),
            self._build_insert_block("Traits 表", "Traits", ["TraitType", "Name", "Description"], traits_rows),
            self._build_insert_block("Leaders 表", "Leaders", ["LeaderType", "Name", "Sex", "InheritFrom", "SceneLayers"], leaders_rows),
            self._build_insert_block("CivilizationLeaders 表", "CivilizationLeaders", ["CivilizationType", "LeaderType", "CapitalName"], civilization_leaders_rows),
            self._build_insert_block("LeaderQuotes 表", "LeaderQuotes", ["LeaderType", "Quote"], quotes_rows),
            self._build_insert_block("LeaderTraits 表", "LeaderTraits", ["LeaderType", "TraitType"], leader_traits_rows),
            self._build_insert_block("LoadingInfo 表", "LoadingInfo", ["LeaderType", "ForegroundImage", "BackgroundImage", "PlayDawnOfManAudio", "LeaderText"], loading_rows),
            "\n".join(image_comments).rstrip(),
        ]
        data_sql = "\n".join([block for block in sql_blocks if block.strip()]).rstrip()

        if not text_rows:
            text_sql = "-- Text.sql\n-- 暂无领袖文本数据"
        else:
            text_sql = "\n".join(
                [
                    "-- Text.sql",
                    "",
                    self._build_insert_block("LocalizedText 表", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
                ]
            ).rstrip()
        return data_sql, text_sql

    def _build_district_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("区域")
        district_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not district_entries:
            return "-- Districts.sql\n-- 暂无区域数据", "-- Text.sql\n-- 暂无区域文本数据"

        schema = build_districts_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        traits_rows: list[str] = []
        district_insert_blocks: list[str] = []

        districts_xp2_groups: dict[tuple[str, ...], list[str]] = {}
        district_replaces_rows: list[str] = []

        district_citizen_yield_rows: list[str] = []
        district_trade_route_rows: list[str] = []
        district_gpp_rows: list[str] = []
        district_required_feature_rows: list[str] = []
        district_valid_terrain_rows: list[str] = []

        district_adjacency_rows: list[str] = []
        adjacency_custom_groups: dict[tuple[str, ...], list[str]] = {}

        text_rows: list[str] = []

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        def _normalized(field_key: str, value: object) -> object:
            default = field_defaults.get(field_key)
            if isinstance(default, float):
                try:
                    return float(value if value is not None else default)
                except (TypeError, ValueError):
                    return float(default)
            if isinstance(default, int):
                try:
                    return int(value if value is not None else default)
                except (TypeError, ValueError):
                    return int(default)
            if field_key == "TraitType":
                return str(value or "").strip()
            if field_key == "MilitaryDomain":
                text = str(value or "").strip()
                return text or "NO_DOMAIN"
            if field_key == "PlunderType":
                text = str(value or "").strip()
                return text or "NO_PLUNDER"
            return str(value or "").strip()

        def _sql_literal(value: object) -> str:
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                return format(value, ".15g")
            return f"'{self._sql_escape(str(value))}'"

        def _append_grouped_row(groups: dict[tuple[str, ...], list[str]], columns: list[str], values: list[object]) -> None:
            key = tuple(columns)
            row = "(" + ", ".join(_sql_literal(v) for v in values) + ")"
            groups.setdefault(key, []).append(row)

        # 这些字段即便等于默认值也必须输出（主表必填/需要显式覆盖默认）。
        always_emit_fields = {
            "NoAdjacentCity",
            "Aqueduct",
            "InternalOnly",
            "CaptureRemovesBuildings",
            "CaptureRemovesCityDefenses",
            "PlunderType",
            "MilitaryDomain",
        }

        for index, entry in enumerate(district_entries, start=1):
            district_type = str(entry.get("type") or "").strip()
            if not district_type:
                district_type = f"DISTRICT_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}

            district_name = str(_value_or_default(table_data, "Name") or "")
            district_desc = str(_value_or_default(table_data, "Description") or "")

            trait_type = str(_value_or_default(table_data, "TraitType") or "").strip()
            has_trait = bool(trait_type)

            types_rows.append(f"('{district_type}', 'KIND_DISTRICT')")
            if has_trait:
                types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")
                traits_rows.append(
                    f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')"
                )

            text_rows.append(f"('zh_Hans_CN','LOC_{district_type}_NAME','{self._sql_escape(district_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{district_type}_DESCRIPTION','{self._sql_escape(district_desc)}')")
            if has_trait:
                trait_name = str(entry.get("trait_name") or "")
                trait_desc = str(entry.get("trait_description") or "")
                _ = trait_name
                _ = trait_desc
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{{LOC_{district_type}_NAME}}')")
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{{LOC_{district_type}_DESCRIPTION}}')")

            district_columns = ["DistrictType", "Name", "Description"]
            district_values: list[object] = [
                district_type,
                f"LOC_{district_type}_NAME",
                f"LOC_{district_type}_DESCRIPTION",
            ]

            cost_value = _normalized("Cost", _value_or_default(table_data, "Cost"))
            try:
                cost_value = max(1, int(cost_value))
            except (TypeError, ValueError):
                cost_value = 1
            district_columns.append("Cost")
            district_values.append(cost_value)

            for field in schema.fields:
                key = field.key
                if key in {"Name", "Description", "TraitType", "Cost"}:
                    continue
                current = _normalized(key, _value_or_default(table_data, key))
                default = _normalized(key, field_defaults.get(key))
                if current == default and key not in always_emit_fields:
                    continue
                district_columns.append(key)
                district_values.append(current)

            if has_trait:
                district_columns.append("TraitType")
                district_values.append(trait_type)

            district_insert_blocks.append(
                "INSERT INTO Districts (\n    "
                + ",\n    ".join(district_columns)
                + "\n) VALUES\n(\n    "
                + ",\n    ".join(_sql_literal(v) for v in district_values)
                + "\n);"
            )

            xp2_payload = entry.get("districts_xp2") if isinstance(entry.get("districts_xp2"), dict) else {}
            if isinstance(entry.get("subtables"), dict):
                subtables = entry.get("subtables") or {}
                if isinstance(subtables.get("Districts_XP2"), dict):
                    xp2_payload = subtables.get("Districts_XP2") or {}
            xp2_defaults = {
                "OnePerRiver": 0,
                "PreventsFloods": 0,
                "PreventsDrought": 0,
                "Canal": 0,
                "AttackRange": 0,
            }
            xp2_values = {
                "OnePerRiver": int(xp2_payload.get("OnePerRiver", 0) or 0),
                "PreventsFloods": int(xp2_payload.get("PreventsFloods", 0) or 0),
                "PreventsDrought": int(xp2_payload.get("PreventsDrought", 0) or 0),
                "Canal": int(xp2_payload.get("Canal", 0) or 0),
                "AttackRange": int(xp2_payload.get("AttackRange", 0) or 0),
            }
            if any(xp2_values[k] != xp2_defaults[k] for k in xp2_defaults):
                xp2_cols = ["DistrictType"]
                xp2_vals: list[object] = [district_type]
                for key in ["OnePerRiver", "PreventsFloods", "PreventsDrought", "Canal", "AttackRange"]:
                    if xp2_values[key] != xp2_defaults[key]:
                        xp2_cols.append(key)
                        xp2_vals.append(xp2_values[key])
                _append_grouped_row(districts_xp2_groups, xp2_cols, xp2_vals)

            replaces_payload = entry.get("district_replaces") if isinstance(entry.get("district_replaces"), dict) else {}
            if isinstance(entry.get("subtables"), dict):
                subtables = entry.get("subtables") or {}
                if isinstance(subtables.get("DistrictReplaces"), dict):
                    replaces_payload = subtables.get("DistrictReplaces") or {}
            replaces_type = str(replaces_payload.get("ReplacesDistrictType") or "").strip()
            if replaces_type:
                district_replaces_rows.append(f"('{district_type}', '{self._sql_escape(replaces_type)}')")

            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

            citizen_payload = subtables.get("District_CitizenYieldChanges") if isinstance(subtables.get("District_CitizenYieldChanges"), list) else None
            if citizen_payload is None:
                citizen_payload = entry.get("district_citizen_yield_changes") if isinstance(entry.get("district_citizen_yield_changes"), list) else []
            for row in citizen_payload:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                yield_change = int(row.get("YieldChange", 0) or 0)
                district_citizen_yield_rows.append(f"('{district_type}', '{self._sql_escape(yield_type)}', {yield_change})")

            trade_payload = subtables.get("District_TradeRouteYields") if isinstance(subtables.get("District_TradeRouteYields"), list) else None
            if trade_payload is None:
                trade_payload = entry.get("district_trade_route_yields") if isinstance(entry.get("district_trade_route_yields"), list) else []
            for row in trade_payload:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                origin = float(row.get("YieldChangeAsOrigin", 0.0) or 0.0)
                domestic = float(row.get("YieldChangeAsDomesticDestination", 0.0) or 0.0)
                international = float(row.get("YieldChangeAsInternationalDestination", 0.0) or 0.0)
                district_trade_route_rows.append(
                    f"('{district_type}', '{self._sql_escape(yield_type)}', {format(origin, '.15g')}, {format(domestic, '.15g')}, {format(international, '.15g')})"
                )

            gpp_payload = subtables.get("District_GreatPersonPoints") if isinstance(subtables.get("District_GreatPersonPoints"), list) else None
            if gpp_payload is None:
                gpp_payload = entry.get("district_great_person_points") if isinstance(entry.get("district_great_person_points"), list) else []
            for row in gpp_payload:
                if not isinstance(row, dict):
                    continue
                class_type = str(row.get("GreatPersonClassType") or "").strip()
                if not class_type:
                    continue
                points = int(row.get("PointsPerTurn", 0) or 0)
                district_gpp_rows.append(f"('{district_type}', '{self._sql_escape(class_type)}', {points})")

            feature_payload = subtables.get("District_RequiredFeatures") if isinstance(subtables.get("District_RequiredFeatures"), list) else None
            if feature_payload is None:
                feature_payload = entry.get("district_required_features") if isinstance(entry.get("district_required_features"), list) else []
            for row in feature_payload:
                if not isinstance(row, dict):
                    continue
                feature_type = str(row.get("FeatureType") or "").strip()
                if not feature_type:
                    continue
                district_required_feature_rows.append(f"('{district_type}', '{self._sql_escape(feature_type)}')")

            terrain_payload = subtables.get("District_ValidTerrains") if isinstance(subtables.get("District_ValidTerrains"), list) else None
            if terrain_payload is None:
                terrain_payload = entry.get("district_valid_terrains") if isinstance(entry.get("district_valid_terrains"), list) else []
            for row in terrain_payload:
                if not isinstance(row, dict):
                    continue
                terrain_type = str(row.get("TerrainType") or "").strip()
                if not terrain_type:
                    continue
                district_valid_terrain_rows.append(f"('{district_type}', '{self._sql_escape(terrain_type)}')")

            adjacency_payload = subtables.get("District_Adjacencies") if isinstance(subtables.get("District_Adjacencies"), list) else None
            if adjacency_payload is None:
                adjacency_payload = entry.get("adjacencies") if isinstance(entry.get("adjacencies"), list) else []
            for adj in adjacency_payload:
                if not isinstance(adj, dict):
                    continue
                adj_mode = str(adj.get("mode") or adj.get("type") or "").strip().lower()
                adj_id = str(adj.get("id") or "").strip()
                if not adj_id:
                    continue
                district_adjacency_rows.append(f"('{district_type}', '{self._sql_escape(adj_id)}')")

                if adj_mode != "custom":
                    continue

                description_text = str(adj.get("description") or "")
                desc_tag = f"LOC_{adj_id.upper()}_DESCRIPTION"
                text_rows.append(f"('zh_Hans_CN','{desc_tag}','{self._sql_escape(description_text)}')")

                columns = ["ID", "Description", "YieldType", "YieldChange"]
                values: list[object] = [adj_id, desc_tag, str(adj.get("yield_type") or ""), int(adj.get("yield_change", 0) or 0)]

                tiles_required = int(adj.get("tiles_required", 1) or 1)
                if tiles_required != 1:
                    columns.append("TilesRequired")
                    values.append(tiles_required)

                source_type = str(adj.get("source_type") or "").strip()
                source_detail = str(adj.get("source_detail") or "").strip()

                bool_source_fields = {
                    "OtherDistrictAdjacent": "OtherDistrictAdjacent",
                    "AdjacentSeaResource": "AdjacentSeaResource",
                    "AdjacentRiver": "AdjacentRiver",
                    "AdjacentWonder": "AdjacentWonder",
                    "AdjacentNaturalWonder": "AdjacentNaturalWonder",
                    "AdjacentResource": "AdjacentResource",
                    "Self": "Self",
                }
                value_source_fields = {
                    "AdjacentTerrain": "AdjacentTerrain",
                    "AdjacentFeature": "AdjacentFeature",
                    "AdjacentImprovement": "AdjacentImprovement",
                    "AdjacentDistrict": "AdjacentDistrict",
                    "AdjacentResourceClass": "AdjacentResourceClass",
                }

                if source_type in bool_source_fields:
                    columns.append(bool_source_fields[source_type])
                    values.append(1)
                elif source_type in value_source_fields and source_detail:
                    column_name = value_source_fields[source_type]
                    if source_type == "AdjacentResourceClass" and source_detail == "NO_RESOURCECLASS":
                        pass
                    else:
                        columns.append(column_name)
                        values.append(source_detail)

                prereq_tech = str(adj.get("prereq_tech") or "").strip()
                prereq_civic = str(adj.get("prereq_civic") or "").strip()
                obsolete_tech = str(adj.get("obsolete_tech") or "").strip()
                obsolete_civic = str(adj.get("obsolete_civic") or "").strip()
                if prereq_tech:
                    columns.append("PrereqTech")
                    values.append(prereq_tech)
                if prereq_civic:
                    columns.append("PrereqCivic")
                    values.append(prereq_civic)
                if obsolete_tech:
                    columns.append("ObsoleteTech")
                    values.append(obsolete_tech)
                if obsolete_civic:
                    columns.append("ObsoleteCivic")
                    values.append(obsolete_civic)

                _append_grouped_row(adjacency_custom_groups, columns, values)

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        district_replaces_rows = self._deduplicate_rows(district_replaces_rows)
        district_adjacency_rows = self._deduplicate_rows(district_adjacency_rows)
        text_rows = self._deduplicate_rows(text_rows)

        sql_blocks: list[str] = []

        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        if traits_rows:
            sql_blocks.append(self._build_insert_block("Traits", "Traits", ["TraitType", "Name", "Description"], traits_rows))
        if district_replaces_rows:
            sql_blocks.append(self._build_insert_block("DistrictReplaces", "DistrictReplaces", ["CivUniqueDistrictType", "ReplacesDistrictType"], district_replaces_rows))

        if district_insert_blocks:
            sql_blocks.append("-- Districts")
            sql_blocks.append("\n\n".join(district_insert_blocks))
            sql_blocks.append("")

        for columns_key, rows in districts_xp2_groups.items():
            sql_blocks.append(
                self._build_insert_block(
                    "Districts_XP2",
                    "Districts_XP2",
                    list(columns_key),
                    rows,
                )
            )

        if district_citizen_yield_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "District_CitizenYieldChanges",
                    "District_CitizenYieldChanges",
                    ["DistrictType", "YieldType", "YieldChange"],
                    district_citizen_yield_rows,
                )
            )

        if district_trade_route_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "District_TradeRouteYields",
                    "District_TradeRouteYields",
                    [
                        "DistrictType",
                        "YieldType",
                        "YieldChangeAsOrigin",
                        "YieldChangeAsDomesticDestination",
                        "YieldChangeAsInternationalDestination",
                    ],
                    district_trade_route_rows,
                )
            )

        if district_gpp_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "District_GreatPersonPoints",
                    "District_GreatPersonPoints",
                    ["DistrictType", "GreatPersonClassType", "PointsPerTurn"],
                    district_gpp_rows,
                )
            )

        if district_required_feature_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "District_RequiredFeatures",
                    "District_RequiredFeatures",
                    ["DistrictType", "FeatureType"],
                    district_required_feature_rows,
                )
            )

        if district_valid_terrain_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "District_ValidTerrains",
                    "District_ValidTerrains",
                    ["DistrictType", "TerrainType"],
                    district_valid_terrain_rows,
                )
            )

        if district_adjacency_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "District_Adjacencies",
                    "District_Adjacencies",
                    ["DistrictType", "YieldChangeId"],
                    district_adjacency_rows,
                )
            )

        if adjacency_custom_groups:
            for columns_key, rows in adjacency_custom_groups.items():
                sql_blocks.append(
                    self._build_insert_block(
                        "Adjacency_YieldChanges",
                        "Adjacency_YieldChanges",
                        list(columns_key),
                        rows,
                    )
                )

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_building_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("建筑")
        building_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not building_entries:
            return "-- Buildings.sql\n-- 暂无建筑数据", "-- Text.sql\n-- 暂无建筑文本数据"

        schema = build_buildings_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        traits_rows: list[str] = []
        buildings_rows: list[str] = []
        buildings_xp2_rows: list[str] = []
        building_replaces_rows: list[str] = []
        building_prereqs_rows: list[str] = []
        building_citizen_yield_rows: list[str] = []
        building_gpp_rows: list[str] = []
        building_required_feature_rows: list[str] = []
        building_tourism_bomb_rows: list[str] = []
        building_resource_cost_rows: list[str] = []
        building_valid_feature_rows: list[str] = []
        building_valid_terrain_rows: list[str] = []
        building_yield_change_rows: list[str] = []
        building_yield_power_rows: list[str] = []
        building_yield_district_copy_rows: list[str] = []
        building_yield_per_era_rows: list[str] = []
        building_conditions_rows: list[str] = []
        building_build_charge_rows: list[str] = []
        greatworks_insert_blocks: list[str] = []
        text_rows: list[str] = []

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        def _normalized(field_key: str, value: object) -> object:
            default = field_defaults.get(field_key)
            if isinstance(default, float):
                try:
                    return float(value if value is not None else default)
                except (TypeError, ValueError):
                    return float(default)
            if isinstance(default, int):
                try:
                    return int(value if value is not None else default)
                except (TypeError, ValueError):
                    return int(default)
            if field_key == "TraitType":
                return str(value or "").strip()
            return str(value or "").strip()

        def _sql_literal(value: object) -> str:
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                return format(value, ".15g")
            return f"'{self._sql_escape(str(value))}'"

        for index, entry in enumerate(building_entries, start=1):
            building_type = str(entry.get("type") or "").strip()
            if not building_type:
                building_type = f"BUILDING_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            name_zh = str(_value_or_default(table_data, "Name") or "")
            desc_zh = str(_value_or_default(table_data, "Description") or "")
            quote_zh = str(_value_or_default(table_data, "Quote") or "")

            trait_type = str(_value_or_default(table_data, "TraitType") or "").strip()
            has_trait = bool(trait_type)

            types_rows.append(f"('{building_type}', 'KIND_BUILDING')")
            if has_trait:
                types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")
                traits_rows.append(f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')")

            text_rows.append(f"('zh_Hans_CN','LOC_{building_type}_NAME','{self._sql_escape(name_zh)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{building_type}_DESCRIPTION','{self._sql_escape(desc_zh)}')")
            if quote_zh:
                text_rows.append(f"('zh_Hans_CN','LOC_{building_type}_QUOTE','{self._sql_escape(quote_zh)}')")
            if has_trait:
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{{LOC_{building_type}_NAME}}')")
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{{LOC_{building_type}_DESCRIPTION}}')")

            columns = ["BuildingType", "Name", "Description"]
            values: list[object] = [
                building_type,
                f"LOC_{building_type}_NAME",
                f"LOC_{building_type}_DESCRIPTION",
            ]

            cost_value = _normalized("Cost", _value_or_default(table_data, "Cost"))
            try:
                cost_value = max(1, int(cost_value))
            except (TypeError, ValueError):
                cost_value = 1
            columns.append("Cost")
            values.append(cost_value)

            if quote_zh:
                columns.append("Quote")
                values.append(f"LOC_{building_type}_QUOTE")

            for field in schema.fields:
                key = field.key
                if key in {"Name", "Description", "TraitType", "Cost", "Quote"}:
                    continue
                current = _normalized(key, _value_or_default(table_data, key))
                default = _normalized(key, field_defaults.get(key))
                if key == "ObsoleteEra":
                    current_text = str(current or "").strip().upper()
                    if current_text in {"", "NO_ERA"}:
                        continue
                if current == default:
                    continue
                columns.append(key)
                values.append(current)

            if has_trait:
                columns.append("TraitType")
                values.append(trait_type)

            buildings_rows.append(
                "INSERT INTO Buildings (\n    "
                + ",\n    ".join(columns)
                + "\n) VALUES\n(\n    "
                + ",\n    ".join(_sql_literal(item) for item in values)
                + "\n);"
            )

            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

            xp2 = subtables.get("Buildings_XP2") if isinstance(subtables.get("Buildings_XP2"), dict) else entry.get("buildings_xp2") if isinstance(entry.get("buildings_xp2"), dict) else {}
            xp2_defaults = {
                "RequiredPower": 0,
                "ResourceTypeConvertedToPower": "",
                "PreventsFloods": 0,
                "PreventsDrought": 0,
                "BlocksCoastalFlooding": 0,
                "CostMultiplierPerTile": 0,
                "CostMultiplierPerSeaLevel": 0,
                "Bridge": 0,
                "CanalWonder": 0,
                "EntertainmentBonusWithPower": 0,
                "NuclearReactor": 0,
                "Pillage": 1,
            }
            xp2_current = {
                "RequiredPower": int(xp2.get("RequiredPower", 0) or 0),
                "ResourceTypeConvertedToPower": str(xp2.get("ResourceTypeConvertedToPower") or "").strip(),
                "PreventsFloods": int(xp2.get("PreventsFloods", 0) or 0),
                "PreventsDrought": int(xp2.get("PreventsDrought", 0) or 0),
                "BlocksCoastalFlooding": int(xp2.get("BlocksCoastalFlooding", 0) or 0),
                "CostMultiplierPerTile": int(xp2.get("CostMultiplierPerTile", 0) or 0),
                "CostMultiplierPerSeaLevel": int(xp2.get("CostMultiplierPerSeaLevel", 0) or 0),
                "Bridge": int(xp2.get("Bridge", 0) or 0),
                "CanalWonder": int(xp2.get("CanalWonder", 0) or 0),
                "EntertainmentBonusWithPower": int(xp2.get("EntertainmentBonusWithPower", 0) or 0),
                "NuclearReactor": int(xp2.get("NuclearReactor", 0) or 0),
                "Pillage": int(xp2.get("Pillage", 1) or 1),
            }
            if any(xp2_current[key] != xp2_defaults[key] for key in xp2_defaults):
                xp2_values: list[object] = [
                    building_type,
                    xp2_current["RequiredPower"],
                    xp2_current["ResourceTypeConvertedToPower"],
                    xp2_current["PreventsFloods"],
                    xp2_current["PreventsDrought"],
                    xp2_current["BlocksCoastalFlooding"],
                    xp2_current["CostMultiplierPerTile"],
                    xp2_current["CostMultiplierPerSeaLevel"],
                    xp2_current["Bridge"],
                    xp2_current["CanalWonder"],
                    xp2_current["EntertainmentBonusWithPower"],
                    xp2_current["NuclearReactor"],
                    xp2_current["Pillage"],
                ]
                buildings_xp2_rows.append("(" + ", ".join(_sql_literal(item) for item in xp2_values) + ")")

            replaces = subtables.get("BuildingReplaces") if isinstance(subtables.get("BuildingReplaces"), dict) else entry.get("building_replaces") if isinstance(entry.get("building_replaces"), dict) else {}
            replaces_type = str(replaces.get("ReplacesBuildingType") or "").strip()
            if replaces_type:
                building_replaces_rows.append(f"('{building_type}', '{self._sql_escape(replaces_type)}')")

            prereqs = subtables.get("BuildingPrereqs") if isinstance(subtables.get("BuildingPrereqs"), list) else entry.get("building_prereqs") if isinstance(entry.get("building_prereqs"), list) else []
            for row in prereqs:
                if not isinstance(row, dict):
                    continue
                prereq_building = str(row.get("PrereqBuilding") or "").strip()
                if prereq_building:
                    building_prereqs_rows.append(f"('{building_type}', '{self._sql_escape(prereq_building)}')")

            citizen_yields = subtables.get("Building_CitizenYieldChanges") if isinstance(subtables.get("Building_CitizenYieldChanges"), list) else entry.get("building_citizen_yield_changes") if isinstance(entry.get("building_citizen_yield_changes"), list) else []
            for row in citizen_yields:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                yield_change = int(row.get("YieldChange", 0) or 0)
                building_citizen_yield_rows.append(f"('{building_type}', '{self._sql_escape(yield_type)}', {yield_change})")

            gpps = subtables.get("Building_GreatPersonPoints") if isinstance(subtables.get("Building_GreatPersonPoints"), list) else entry.get("building_great_person_points") if isinstance(entry.get("building_great_person_points"), list) else []
            for row in gpps:
                if not isinstance(row, dict):
                    continue
                gp_class = str(row.get("GreatPersonClassType") or "").strip()
                if not gp_class:
                    continue
                points = int(row.get("PointsPerTurn", 0) or 0)
                building_gpp_rows.append(f"('{building_type}', '{self._sql_escape(gp_class)}', {points})")

            required_features = subtables.get("Building_RequiredFeatures") if isinstance(subtables.get("Building_RequiredFeatures"), list) else entry.get("building_required_features") if isinstance(entry.get("building_required_features"), list) else []
            for row in required_features:
                if not isinstance(row, dict):
                    continue
                feature_type = str(row.get("FeatureType") or "").strip()
                if feature_type:
                    building_required_feature_rows.append(f"('{building_type}', '{self._sql_escape(feature_type)}')")

            tourism_bombs = subtables.get("Building_TourismBombs_XP2") if isinstance(subtables.get("Building_TourismBombs_XP2"), list) else entry.get("building_tourism_bombs_xp2") if isinstance(entry.get("building_tourism_bombs_xp2"), list) else []
            for row in tourism_bombs:
                if not isinstance(row, dict):
                    continue
                bomb_value = int(row.get("TourismBombValue", 0) or 0)
                building_tourism_bomb_rows.append(f"('{building_type}', {bomb_value})")

            resource_costs = subtables.get("Building_ResourceCosts") if isinstance(subtables.get("Building_ResourceCosts"), list) else entry.get("building_resource_costs") if isinstance(entry.get("building_resource_costs"), list) else []
            for row in resource_costs:
                if not isinstance(row, dict):
                    continue
                resource_type = str(row.get("ResourceType") or "").strip()
                if not resource_type:
                    continue
                start_cost = int(row.get("StartProductionCost", 0) or 0)
                per_turn = int(row.get("PerTurnMaintenanceCost", 0) or 0)
                building_resource_cost_rows.append(f"('{building_type}', '{self._sql_escape(resource_type)}', {start_cost}, {per_turn})")

            valid_features = subtables.get("Building_ValidFeatures") if isinstance(subtables.get("Building_ValidFeatures"), list) else entry.get("building_valid_features") if isinstance(entry.get("building_valid_features"), list) else []
            for row in valid_features:
                if not isinstance(row, dict):
                    continue
                feature_type = str(row.get("FeatureType") or "").strip()
                if feature_type:
                    building_valid_feature_rows.append(f"('{building_type}', '{self._sql_escape(feature_type)}')")

            valid_terrains = subtables.get("Building_ValidTerrains") if isinstance(subtables.get("Building_ValidTerrains"), list) else entry.get("building_valid_terrains") if isinstance(entry.get("building_valid_terrains"), list) else []
            for row in valid_terrains:
                if not isinstance(row, dict):
                    continue
                terrain_type = str(row.get("TerrainType") or "").strip()
                if terrain_type:
                    building_valid_terrain_rows.append(f"('{building_type}', '{self._sql_escape(terrain_type)}')")

            yield_changes = subtables.get("Building_YieldChanges") if isinstance(subtables.get("Building_YieldChanges"), list) else entry.get("building_yield_changes") if isinstance(entry.get("building_yield_changes"), list) else []
            for row in yield_changes:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                yield_change = int(row.get("YieldChange", 0) or 0)
                building_yield_change_rows.append(f"('{building_type}', '{self._sql_escape(yield_type)}', {yield_change})")

            yield_power = subtables.get("Building_YieldChangesBonusWithPower") if isinstance(subtables.get("Building_YieldChangesBonusWithPower"), list) else entry.get("building_yield_changes_bonus_with_power") if isinstance(entry.get("building_yield_changes_bonus_with_power"), list) else []
            for row in yield_power:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                yield_change = int(row.get("YieldChange", 0) or 0)
                building_yield_power_rows.append(f"('{building_type}', '{self._sql_escape(yield_type)}', {yield_change})")

            yield_district_copies = subtables.get("Building_YieldDistrictCopies") if isinstance(subtables.get("Building_YieldDistrictCopies"), list) else entry.get("building_yield_district_copies") if isinstance(entry.get("building_yield_district_copies"), list) else []
            for row in yield_district_copies:
                if not isinstance(row, dict):
                    continue
                old_yield = str(row.get("OldYieldType") or "").strip() or "NO_YIELD"
                new_yield = str(row.get("NewYieldType") or "").strip() or "NO_YIELD"
                building_yield_district_copy_rows.append(f"('{building_type}', '{self._sql_escape(old_yield)}', '{self._sql_escape(new_yield)}')")

            yields_per_era = subtables.get("Building_YieldsPerEra") if isinstance(subtables.get("Building_YieldsPerEra"), list) else entry.get("building_yields_per_era") if isinstance(entry.get("building_yields_per_era"), list) else []
            for row in yields_per_era:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip() or "NO_YIELD"
                yield_change = int(row.get("YieldChange", 0) or 0)
                building_yield_per_era_rows.append(f"('{building_type}', '{self._sql_escape(yield_type)}', {yield_change})")

            conditions_payload = subtables.get("BuildingConditions")
            if isinstance(conditions_payload, list):
                conditions_payload = conditions_payload[0] if conditions_payload else {}
            if not isinstance(conditions_payload, dict):
                conditions_payload = entry.get("building_conditions") if isinstance(entry.get("building_conditions"), dict) else {}
            if isinstance(conditions_payload, dict):
                unlocks = int(conditions_payload.get("UnlocksFromEffect", 0) or 0)
                if unlocks != 0:
                    building_conditions_rows.append(f"('{building_type}', {unlocks})")

            build_charge = subtables.get("Building_BuildChargeProductions") if isinstance(subtables.get("Building_BuildChargeProductions"), list) else entry.get("building_build_charge_productions") if isinstance(entry.get("building_build_charge_productions"), list) else []
            for row in build_charge:
                if not isinstance(row, dict):
                    continue
                unit_type = str(row.get("UnitType") or "").strip()
                if not unit_type:
                    continue
                percent = int(row.get("PercentProductionPerCharge", 0) or 0)
                building_build_charge_rows.append(f"('{building_type}', '{self._sql_escape(unit_type)}', {percent})")

            greatworks = subtables.get("Building_GreatWorks") if isinstance(subtables.get("Building_GreatWorks"), list) else entry.get("building_greatworks") if isinstance(entry.get("building_greatworks"), list) else []
            defaults = {
                "NumSlots": 1,
                "ThemingUniquePerson": 0,
                "ThemingSameObjectType": 0,
                "ThemingUniqueCivs": 0,
                "ThemingSameEras": 0,
                "ThemingYieldMultiplier": 0,
                "ThemingTourismMultiplier": 0,
                "NonUniquePersonYield": 0,
                "NonUniquePersonTourism": 0,
                "ThemingBonusDescription": None,
            }
            ordered_cols = [
                "BuildingType",
                "GreatWorkSlotType",
                "NumSlots",
                "ThemingUniquePerson",
                "ThemingSameObjectType",
                "ThemingUniqueCivs",
                "ThemingSameEras",
                "ThemingYieldMultiplier",
                "ThemingTourismMultiplier",
                "NonUniquePersonYield",
                "NonUniquePersonTourism",
                "ThemingBonusDescription",
            ]
            for row in greatworks:
                if not isinstance(row, dict):
                    continue
                slot_type = str(row.get("GreatWorkSlotType") or "").strip()
                if not slot_type:
                    continue
                theming_text = str(row.get("ThemingBonusDescriptionText") or "").strip()
                theming_desc_value = str(row.get("ThemingBonusDescription") or "").strip()
                if not theming_text and theming_desc_value and not theming_desc_value.upper().startswith("LOC_"):
                    theming_text = theming_desc_value
                    theming_desc_value = ""
                if theming_text:
                    theming_desc_value = f"LOC_{building_type}_{_greatwork_slot_short(slot_type)}_THEMING"
                    text_rows.append(
                        f"('zh_Hans_CN','{self._sql_escape(theming_desc_value)}','{self._sql_escape(theming_text)}')"
                    )
                mapped: dict[str, object] = {
                    "BuildingType": building_type,
                    "GreatWorkSlotType": slot_type,
                    "NumSlots": int(row.get("NumSlots", 1) or 1),
                    "ThemingUniquePerson": int(row.get("ThemingUniquePerson", 0) or 0),
                    "ThemingSameObjectType": int(row.get("ThemingSameObjectType", 0) or 0),
                    "ThemingUniqueCivs": int(row.get("ThemingUniqueCivs", 0) or 0),
                    "ThemingSameEras": int(row.get("ThemingSameEras", 0) or 0),
                    "ThemingYieldMultiplier": int(row.get("ThemingYieldMultiplier", 0) or 0),
                    "ThemingTourismMultiplier": int(row.get("ThemingTourismMultiplier", 0) or 0),
                    "NonUniquePersonYield": int(row.get("NonUniquePersonYield", 0) or 0),
                    "NonUniquePersonTourism": int(row.get("NonUniquePersonTourism", 0) or 0),
                    "ThemingBonusDescription": theming_desc_value or None,
                }

                use_cols: list[str] = []
                use_vals: list[object] = []
                for col in ordered_cols:
                    value = mapped.get(col)
                    if col in {"BuildingType", "GreatWorkSlotType"}:
                        use_cols.append(col)
                        use_vals.append(value if value is not None else "")
                        continue
                    default = defaults.get(col)
                    if default is None:
                        if value is None:
                            continue
                        if isinstance(value, str) and not value.strip():
                            continue
                    elif value == default:
                        continue
                    use_cols.append(col)
                    use_vals.append(value if value is not None else "")

                if not use_cols:
                    continue
                greatworks_insert_blocks.append(
                    "INSERT INTO Building_GreatWorks (\n    "
                    + ",\n    ".join(use_cols)
                    + "\n) VALUES\n(\n    "
                    + ",\n    ".join(_sql_literal(item) for item in use_vals)
                    + "\n);"
                )

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        buildings_xp2_rows = self._deduplicate_rows(buildings_xp2_rows)
        building_replaces_rows = self._deduplicate_rows(building_replaces_rows)
        building_prereqs_rows = self._deduplicate_rows(building_prereqs_rows)
        building_citizen_yield_rows = self._deduplicate_rows(building_citizen_yield_rows)
        building_gpp_rows = self._deduplicate_rows(building_gpp_rows)
        building_required_feature_rows = self._deduplicate_rows(building_required_feature_rows)
        building_tourism_bomb_rows = self._deduplicate_rows(building_tourism_bomb_rows)
        building_resource_cost_rows = self._deduplicate_rows(building_resource_cost_rows)
        building_valid_feature_rows = self._deduplicate_rows(building_valid_feature_rows)
        building_valid_terrain_rows = self._deduplicate_rows(building_valid_terrain_rows)
        building_yield_change_rows = self._deduplicate_rows(building_yield_change_rows)
        building_yield_power_rows = self._deduplicate_rows(building_yield_power_rows)
        building_yield_district_copy_rows = self._deduplicate_rows(building_yield_district_copy_rows)
        building_yield_per_era_rows = self._deduplicate_rows(building_yield_per_era_rows)
        building_conditions_rows = self._deduplicate_rows(building_conditions_rows)
        building_build_charge_rows = self._deduplicate_rows(building_build_charge_rows)
        text_rows = self._deduplicate_rows(text_rows)

        sql_blocks: list[str] = []
        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        if traits_rows:
            sql_blocks.append(self._build_insert_block("Traits", "Traits", ["TraitType", "Name", "Description"], traits_rows))
        if buildings_rows:
            sql_blocks.append("-- Buildings")
            sql_blocks.append("\n\n".join(buildings_rows))
            sql_blocks.append("")
        if buildings_xp2_rows:
            sql_blocks.append(self._build_insert_block("Buildings_XP2", "Buildings_XP2", [
                "BuildingType",
                "RequiredPower",
                "ResourceTypeConvertedToPower",
                "PreventsFloods",
                "PreventsDrought",
                "BlocksCoastalFlooding",
                "CostMultiplierPerTile",
                "CostMultiplierPerSeaLevel",
                "Bridge",
                "CanalWonder",
                "EntertainmentBonusWithPower",
                "NuclearReactor",
                "Pillage",
            ], buildings_xp2_rows))
        if building_replaces_rows:
            sql_blocks.append(self._build_insert_block("BuildingReplaces", "BuildingReplaces", ["CivUniqueBuildingType", "ReplacesBuildingType"], building_replaces_rows))
        if building_prereqs_rows:
            sql_blocks.append(self._build_insert_block("BuildingPrereqs", "BuildingPrereqs", ["Building", "PrereqBuilding"], building_prereqs_rows))
        if building_citizen_yield_rows:
            sql_blocks.append(self._build_insert_block("Building_CitizenYieldChanges", "Building_CitizenYieldChanges", ["BuildingType", "YieldType", "YieldChange"], building_citizen_yield_rows))
        if building_gpp_rows:
            sql_blocks.append(self._build_insert_block("Building_GreatPersonPoints", "Building_GreatPersonPoints", ["BuildingType", "GreatPersonClassType", "PointsPerTurn"], building_gpp_rows))
        if building_required_feature_rows:
            sql_blocks.append(self._build_insert_block("Building_RequiredFeatures", "Building_RequiredFeatures", ["BuildingType", "FeatureType"], building_required_feature_rows))
        if building_tourism_bomb_rows:
            sql_blocks.append(self._build_insert_block("Building_TourismBombs_XP2", "Building_TourismBombs_XP2", ["BuildingType", "TourismBombValue"], building_tourism_bomb_rows))
        if building_resource_cost_rows:
            sql_blocks.append(self._build_insert_block("Building_ResourceCosts", "Building_ResourceCosts", ["BuildingType", "ResourceType", "StartProductionCost", "PerTurnMaintenanceCost"], building_resource_cost_rows))
        if building_valid_feature_rows:
            sql_blocks.append(self._build_insert_block("Building_ValidFeatures", "Building_ValidFeatures", ["BuildingType", "FeatureType"], building_valid_feature_rows))
        if building_valid_terrain_rows:
            sql_blocks.append(self._build_insert_block("Building_ValidTerrains", "Building_ValidTerrains", ["BuildingType", "TerrainType"], building_valid_terrain_rows))
        if building_yield_change_rows:
            sql_blocks.append(self._build_insert_block("Building_YieldChanges", "Building_YieldChanges", ["BuildingType", "YieldType", "YieldChange"], building_yield_change_rows))
        if building_yield_power_rows:
            sql_blocks.append(self._build_insert_block("Building_YieldChangesBonusWithPower", "Building_YieldChangesBonusWithPower", ["BuildingType", "YieldType", "YieldChange"], building_yield_power_rows))
        if building_yield_district_copy_rows:
            sql_blocks.append(self._build_insert_block("Building_YieldDistrictCopies", "Building_YieldDistrictCopies", ["BuildingType", "OldYieldType", "NewYieldType"], building_yield_district_copy_rows))
        if building_yield_per_era_rows:
            sql_blocks.append(self._build_insert_block("Building_YieldsPerEra", "Building_YieldsPerEra", ["BuildingType", "YieldType", "YieldChange"], building_yield_per_era_rows))
        if building_conditions_rows:
            sql_blocks.append(self._build_insert_block("BuildingConditions", "BuildingConditions", ["BuildingType", "UnlocksFromEffect"], building_conditions_rows))
        if building_build_charge_rows:
            sql_blocks.append(self._build_insert_block("Building_BuildChargeProductions", "Building_BuildChargeProductions", ["BuildingType", "UnitType", "PercentProductionPerCharge"], building_build_charge_rows))
        if greatworks_insert_blocks:
            sql_blocks.append("-- Building_GreatWorks")
            sql_blocks.append("\n\n".join(greatworks_insert_blocks))
            sql_blocks.append("")

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_unit_sql_pair(self) -> tuple[str, str]:
        units_sql, _ability_sql, text_sql = self._build_unit_sql_bundle()
        return units_sql, text_sql

    def _build_unit_sql_bundle(self) -> tuple[str, str, str]:
        entries = self._project.sections.get("单位")
        unit_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []

        existing_unit_types: set[str] = set()
        for item in unit_entries:
            unit_type = str(item.get("type") or "").strip()
            if unit_type:
                existing_unit_types.add(unit_type)

        great_entries_raw = self._project.sections.get("伟人")
        great_entries = [entry for entry in great_entries_raw if isinstance(entry, dict)] if isinstance(great_entries_raw, list) else []
        for great_entry in great_entries:
            if bool(great_entry.get("import_locked", False)):
                continue
            class_data = great_entry.get("class_data") if isinstance(great_entry.get("class_data"), dict) else {}
            unit_data = great_entry.get("unit_data") if isinstance(great_entry.get("unit_data"), dict) else {}
            unit_type = str(unit_data.get("UnitType") or class_data.get("UnitType") or "").strip()
            if not unit_type or unit_type in existing_unit_types:
                continue

            table_data = {
                "Name": str(unit_data.get("Name") or ""),
                "Description": str(unit_data.get("Description") or ""),
                "BaseSightRange": int(unit_data.get("BaseSightRange", 4) or 4),
                "BaseMoves": int(unit_data.get("BaseMoves", 5) or 5),
                "FormationClass": str(unit_data.get("FormationClass") or "FORMATION_CLASS_CIVILIAN"),
                "Domain": str(unit_data.get("Domain") or "DOMAIN_LAND"),
                "CanRetreatWhenCaptured": int(unit_data.get("CanRetreatWhenCaptured", 0) or 0),
                "CanCapture": int(unit_data.get("CanCapture", 0) or 0),
                "Cost": int(unit_data.get("Cost", 1) or 1),
                "ZoneOfControl": int(unit_data.get("ZoneOfControl", 0) or 0),
                "FoundReligion": int(unit_data.get("FoundReligion", 0) or 0),
                "CanTrain": int(unit_data.get("CanTrain", 0) or 0),
                "TraitType": str(unit_data.get("TraitType") or ""),
            }
            unit_entries.append(
                {
                    "type": unit_type,
                    "table_data": table_data,
                    "subtables": {},
                    "images": great_entry.get("images") if isinstance(great_entry.get("images"), dict) else {},
                }
            )
            existing_unit_types.add(unit_type)

        if not unit_entries:
            return "-- Units.sql\n-- 暂无单位数据", "-- UnitAbility.sql\n-- 暂无单位能力数据", "-- Text.sql\n-- 暂无单位文本数据"

        schema = build_units_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        traits_rows: list[str] = []
        units_rows: list[str] = []
        units_mode_rows: list[str] = []
        units_presentation_rows: list[str] = []
        units_xp2_grouped_rows: dict[tuple[str, ...], list[str]] = {}
        unit_replaces_rows: list[str] = []
        unit_upgrades_rows: list[str] = []
        unit_captures_rows: list[str] = []
        unit_retreat_rows: list[str] = []
        unit_building_prereq_rows: list[str] = []
        unit_ai_info_rows: list[str] = []
        tags_rows: list[str] = []
        type_tags_rows: list[str] = []
        ability_types_rows: list[str] = []
        ability_tags_rows: list[str] = []
        ability_type_tags_rows: list[str] = []
        unit_abilities_rows: list[str] = []
        custom_unit_abilities_rows: list[str] = []
        ability_type_seen: set[str] = set()
        image_comment_rows: list[str] = []
        unit_text_rows: list[str] = []
        ability_text_rows: list[str] = []
        battle_text_rows: list[str] = []

        fixed_class_tags = {
            "CLASS_LANDCIVILIAN",
            "CLASS_RECON",
            "CLASS_BUILDER",
            "CLASS_MELEE",
            "CLASS_RANGED",
            "CLASS_SIEGE",
            "CLASS_HEAVY_CAVALRY",
            "CLASS_LIGHT_CAVALRY",
            "CLASS_ANTI_CAVALRY",
            "CLASS_NAVAL_MELEE",
            "CLASS_NAVAL_RANGED",
            "CLASS_NAVAL_RAIDER",
            "CLASS_NAVAL_CARRIER",
            "CLASS_TRADER",
            "CLASS_RELIGIOUS",
            "CLASS_AIRCRAFT",
            "CLASS_AIR_BOMBER",
            "CLASS_AIR_FIGHTER",
            "CLASS_ARCHAEOLOGIST",
            "CLASS_SPY",
            "CLASS_ANTI_AIR",
            "CLASS_MOBILE_RANGED",
            "CLASS_SUPPORT",
        }
        existing_ability_class_tags: set[str] = set()
        db_path = self._resolve_preview_game_db_path()
        if db_path is not None:
            try:
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.execute("SELECT Tag FROM Tags WHERE Vocabulary = 'ABILITY_CLASS'")
                    existing_ability_class_tags = {
                        str(row[0] or "").strip()
                        for row in cursor.fetchall()
                        if str(row[0] or "").strip()
                    }
            except sqlite3.Error:
                existing_ability_class_tags = set()

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        def _normalized(field_key: str, value: object) -> object:
            default = field_defaults.get(field_key)
            if isinstance(default, int):
                try:
                    return int(value if value is not None else default)
                except (TypeError, ValueError):
                    return int(default)
            if isinstance(default, float):
                try:
                    return float(value if value is not None else default)
                except (TypeError, ValueError):
                    return float(default)
            if field_key == "TraitType":
                return str(value or "").strip()
            return str(value or "").strip()

        def _sql_literal(value: object) -> str:
            if value is None:
                return "NULL"
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                return format(value, ".15g")
            if isinstance(value, str) and value.strip().lower() == "none":
                return "NULL"
            return f"'{self._sql_escape(str(value))}'"

        for index, entry in enumerate(unit_entries, start=1):
            unit_type = str(entry.get("type") or "").strip()
            if not unit_type:
                unit_type = f"UNIT_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            name_zh = str(_value_or_default(table_data, "Name") or "")
            desc_zh = str(_value_or_default(table_data, "Description") or "")
            trait_type = str(_value_or_default(table_data, "TraitType") or "").strip()
            has_trait = bool(trait_type)

            types_rows.append(f"('{unit_type}', 'KIND_UNIT')")
            if has_trait:
                types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")
                traits_rows.append(f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')")

            unit_text_rows.append(f"('zh_Hans_CN','LOC_{unit_type}_NAME','{self._sql_escape(name_zh)}')")
            unit_text_rows.append(f"('zh_Hans_CN','LOC_{unit_type}_DESCRIPTION','{self._sql_escape(desc_zh)}')")
            if has_trait:
                unit_text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{{LOC_{unit_type}_NAME}}')")
                unit_text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{{LOC_{unit_type}_DESCRIPTION}}')")

            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
            unit_icon = images.get("unit_icon") if isinstance(images.get("unit_icon"), dict) else {}
            unit_icon_path = str(unit_icon.get("path") or "").strip()
            unit_icon_name = str(images.get("unit_icon_name") or "").strip()
            if unit_icon_path:
                image_comment_rows.append(
                    f"--单位{unit_type}图标(256x256)：{self._sql_escape(unit_icon_name or f'ICON_{unit_type}')} <- {self._sql_escape(unit_icon_path)}"
                )

            columns = ["UnitType", "Name"]
            values: list[object] = [unit_type, f"LOC_{unit_type}_NAME"]

            # Domain 在游戏表结构中没有可依赖的默认值，因此即便等于 UI 默认值也必须输出。
            # 其它字段仍按当前预览规则：与字段默认值一致时可省略（required_main_fields 除外）。
            required_main_fields = {"Description", "BaseSightRange", "BaseMoves", "Domain", "FormationClass"}
            for field in schema.fields:
                key = field.key
                if key in {"Name", "TraitType"}:
                    continue
                if key == "Description":
                    columns.append("Description")
                    values.append(f"LOC_{unit_type}_DESCRIPTION")
                    continue
                current = _normalized(key, _value_or_default(table_data, key))
                default = _normalized(key, field_defaults.get(key))
                if key in required_main_fields:
                    columns.append(key)
                    values.append(current)
                    continue
                if current == default:
                    continue
                columns.append(key)
                values.append(current)

            if has_trait:
                columns.append("TraitType")
                values.append(trait_type)

            units_rows.append(
                "INSERT INTO Units (\n    "
                + ",\n    ".join(columns)
                + "\n) VALUES\n(\n    "
                + ",\n    ".join(_sql_literal(item) for item in values)
                + "\n);"
            )

            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

            units_mode = subtables.get("Units_MODE") if isinstance(subtables.get("Units_MODE"), dict) else entry.get("units_mode") if isinstance(entry.get("units_mode"), dict) else {}
            action_charges = int(units_mode.get("ActionCharges", 0) or 0)
            if action_charges != 0:
                units_mode_rows.append(f"('{unit_type}', {action_charges})")

            units_presentation = subtables.get("Units_Presentation") if isinstance(subtables.get("Units_Presentation"), dict) else entry.get("units_presentation") if isinstance(entry.get("units_presentation"), dict) else {}
            ui_flag_offset = int(units_presentation.get("UIFlagOffset", 0) or 0)
            if ui_flag_offset != 0:
                units_presentation_rows.append(f"('{unit_type}', {ui_flag_offset})")

            units_xp2 = subtables.get("Units_XP2") if isinstance(subtables.get("Units_XP2"), dict) else entry.get("units_xp2") if isinstance(entry.get("units_xp2"), dict) else {}
            xp2_defaults = {
                "ResourceMaintenanceAmount": 0,
                "ResourceCost": 0,
                "ResourceMaintenanceType": "",
                "TourismBomb": 0,
                "CanEarnExperience": 1,
                "TourismBombPossible": 0,
                "CanFormMilitaryFormation": 1,
                "MajorCivOnly": 0,
                "CanCauseDisasters": 0,
                "CanSacrificeUnits": 0,
            }
            xp2_export_order = [
                "ResourceMaintenanceAmount",
                "ResourceCost",
                "ResourceMaintenanceType",
                "TourismBomb",
                "CanEarnExperience",
                "TourismBombPossible",
                "CanFormMilitaryFormation",
                "MajorCivOnly",
                "CanCauseDisasters",
                "CanSacrificeUnits",
            ]
            xp2_current = {
                "ResourceMaintenanceAmount": int(units_xp2.get("ResourceMaintenanceAmount", 0) or 0),
                "ResourceCost": int(units_xp2.get("ResourceCost", 0) or 0),
                "ResourceMaintenanceType": str(units_xp2.get("ResourceMaintenanceType") or "").strip(),
                "TourismBomb": int(units_xp2.get("TourismBomb", 0) or 0),
                "CanEarnExperience": int(units_xp2.get("CanEarnExperience", 1) or 1),
                "TourismBombPossible": int(units_xp2.get("TourismBombPossible", 0) or 0),
                "CanFormMilitaryFormation": int(units_xp2.get("CanFormMilitaryFormation", 1) or 1),
                "MajorCivOnly": int(units_xp2.get("MajorCivOnly", 0) or 0),
                "CanCauseDisasters": int(units_xp2.get("CanCauseDisasters", 0) or 0),
                "CanSacrificeUnits": int(units_xp2.get("CanSacrificeUnits", 0) or 0),
            }
            changed_fields = [key for key in xp2_export_order if xp2_current[key] != xp2_defaults[key]]
            if changed_fields:
                export_columns = ["UnitType", *changed_fields]
                export_values = [unit_type, *(xp2_current[key] for key in changed_fields)]
                row_sql = "(" + ", ".join(_sql_literal(item) for item in export_values) + ")"
                units_xp2_grouped_rows.setdefault(tuple(export_columns), []).append(row_sql)

            unit_replaces = subtables.get("UnitReplaces") if isinstance(subtables.get("UnitReplaces"), dict) else entry.get("unit_replaces") if isinstance(entry.get("unit_replaces"), dict) else {}
            replaces_type = str(unit_replaces.get("ReplacesUnitType") or "").strip()
            if replaces_type:
                unit_replaces_rows.append(f"('{unit_type}', '{self._sql_escape(replaces_type)}')")

            unit_upgrades = subtables.get("UnitUpgrades") if isinstance(subtables.get("UnitUpgrades"), dict) else entry.get("unit_upgrades") if isinstance(entry.get("unit_upgrades"), dict) else {}
            upgrade_unit = str(unit_upgrades.get("UpgradeUnit") or "").strip()
            if upgrade_unit:
                unit_upgrades_rows.append(f"('{unit_type}', '{self._sql_escape(upgrade_unit)}')")

            unit_captures = subtables.get("UnitCaptures") if isinstance(subtables.get("UnitCaptures"), dict) else entry.get("unit_captures") if isinstance(entry.get("unit_captures"), dict) else {}
            becomes_unit = str(unit_captures.get("BecomesUnitType") or "").strip()
            if becomes_unit:
                unit_captures_rows.append(f"('{unit_type}', '{self._sql_escape(becomes_unit)}')")

            retreats = subtables.get("UnitRetreats_XP1") if isinstance(subtables.get("UnitRetreats_XP1"), list) else entry.get("unit_retreats_xp1") if isinstance(entry.get("unit_retreats_xp1"), list) else []
            for row in retreats:
                if not isinstance(row, dict):
                    continue
                retreat_type = str(row.get("UnitRetreatType") or "").strip()
                if not retreat_type:
                    continue
                building_type = str(row.get("BuildingType") or "").strip()
                improvement_type = str(row.get("ImprovementType") or "").strip()
                unit_retreat_rows.append(
                    "("
                    + ", ".join(
                        [
                            _sql_literal(retreat_type),
                            _sql_literal(building_type or None),
                            _sql_literal(unit_type),
                            _sql_literal(improvement_type or None),
                        ]
                    )
                    + ")"
                )

            unit_building_prereqs = subtables.get("Unit_BuildingPrereqs") if isinstance(subtables.get("Unit_BuildingPrereqs"), list) else entry.get("unit_building_prereqs") if isinstance(entry.get("unit_building_prereqs"), list) else []
            for row in unit_building_prereqs:
                if not isinstance(row, dict):
                    continue
                prereq_building = str(row.get("PrereqBuilding") or "").strip()
                if not prereq_building:
                    continue
                num_supported = int(row.get("NumSupported", -1) or -1)
                unit_building_prereq_rows.append(f"('{unit_type}', '{self._sql_escape(prereq_building)}', {num_supported})")

            unit_ai_infos = subtables.get("UnitAiInfos") if isinstance(subtables.get("UnitAiInfos"), list) else entry.get("unit_ai_infos") if isinstance(entry.get("unit_ai_infos"), list) else []
            for row in unit_ai_infos:
                if not isinstance(row, dict):
                    continue
                ai_type = str(row.get("AiType") or "").strip()
                if ai_type:
                    unit_ai_info_rows.append(f"('{unit_type}', '{self._sql_escape(ai_type)}')")

            type_tags = subtables.get("TypeTags") if isinstance(subtables.get("TypeTags"), list) else entry.get("type_tags") if isinstance(entry.get("type_tags"), list) else []
            for row in type_tags:
                if not isinstance(row, dict):
                    continue
                type_value = str(row.get("Type") or unit_type).strip() or unit_type
                tag = str(row.get("Tag") or "").strip()
                if tag:
                    type_tags_rows.append(f"('{self._sql_escape(type_value)}', '{self._sql_escape(tag)}')")
                    if tag.startswith("CLASS_") and tag not in fixed_class_tags and tag not in existing_ability_class_tags:
                        tags_rows.append(f"('{self._sql_escape(tag)}', 'ABILITY_CLASS')")

            ability_bindings = subtables.get("UnitAbilityBindings") if isinstance(subtables.get("UnitAbilityBindings"), list) else entry.get("unit_ability_bindings") if isinstance(entry.get("unit_ability_bindings"), list) else []
            for bind in ability_bindings:
                if not isinstance(bind, dict):
                    continue
                enabled = bool(bind.get("Enabled", True))
                if not enabled:
                    continue
                ability_type = f"ABILITY_{unit_type}"
                if not ability_type:
                    continue
                tag_value = f"CLASS_{unit_type}"
                permanent = 1

                ability_types_rows.append(f"('{ability_type}', 'KIND_ABILITY')")
                if tag_value:
                    ability_type_tags_rows.append(f"('{ability_type}', '{self._sql_escape(tag_value)}')")
                    ability_type_tags_rows.append(f"('{self._sql_escape(unit_type)}', '{self._sql_escape(tag_value)}')")
                    if tag_value.startswith("CLASS_") and tag_value not in fixed_class_tags and tag_value not in existing_ability_class_tags:
                        ability_tags_rows.append(f"('{self._sql_escape(tag_value)}', 'ABILITY_CLASS')")

                ability_name = str(bind.get("AbilityName") or "").strip()
                ability_desc = str(bind.get("AbilityDescription") or "").strip()
                name_tag = f"LOC_{ability_type}_NAME"
                desc_tag = f"LOC_{ability_type}_DESCRIPTION"
                if ability_name:
                    ability_text_rows.append(f"('zh_Hans_CN','{name_tag}','{self._sql_escape(ability_name)}')")
                if ability_desc:
                    ability_text_rows.append(f"('zh_Hans_CN','{desc_tag}','{self._sql_escape(ability_desc)}')")

                unit_abilities_rows.append(
                    "("
                    + ", ".join(
                        [
                            _sql_literal(ability_type),
                            _sql_literal(name_tag if ability_name else None),
                            _sql_literal(desc_tag if ability_desc else None),
                            _sql_literal(0),
                            _sql_literal(permanent),
                        ]
                    )
                    + ")"
                )
                ability_type_seen.add(ability_type)

        custom_abilities = self._modifier_custom_unit_abilities()
        for row in custom_abilities:
            ability_type = str(row.get("unit_ability_type") or "").strip()
            if not ability_type or ability_type in ability_type_seen:
                continue

            ability_types_rows.append(f"('{ability_type}', 'KIND_ABILITY')")

            type_tags = row.get("type_tags") if isinstance(row.get("type_tags"), list) else []
            for tag in type_tags:
                tag_text = str(tag or "").strip()
                if not tag_text:
                    continue
                ability_type_tags_rows.append(f"('{self._sql_escape(ability_type)}', '{self._sql_escape(tag_text)}')")

            ability_name = str(row.get("name_zh") or "").strip()
            ability_desc = str(row.get("description_zh") or "").strip()
            name_tag = f"LOC_{ability_type}_NAME"
            desc_tag = f"LOC_{ability_type}_DESCRIPTION"
            if ability_name:
                ability_text_rows.append(f"('zh_Hans_CN','{name_tag}','{self._sql_escape(ability_name)}')")
            if ability_desc:
                ability_text_rows.append(f"('zh_Hans_CN','{desc_tag}','{self._sql_escape(ability_desc)}')")

            inactive = 1 if bool(row.get("inactive", False)) else 0
            show_float = 1 if bool(row.get("show_float_text_when_earned", False)) else 0
            permanent = 1 if bool(row.get("permanent", True)) else 0
            custom_unit_abilities_rows.append(
                "("
                + ", ".join(
                    [
                        _sql_literal(ability_type),
                        _sql_literal(name_tag if ability_name else None),
                        _sql_literal(desc_tag if ability_desc else None),
                        _sql_literal(inactive),
                        _sql_literal(show_float),
                        _sql_literal(permanent),
                    ]
                )
                + ")"
            )
            ability_type_seen.add(ability_type)

        battle_text_rows.extend(self._modifier_strength_preview_text_rows())

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        units_mode_rows = self._deduplicate_rows(units_mode_rows)
        units_presentation_rows = self._deduplicate_rows(units_presentation_rows)
        for columns_key in list(units_xp2_grouped_rows.keys()):
            units_xp2_grouped_rows[columns_key] = self._deduplicate_rows(units_xp2_grouped_rows[columns_key])
        unit_replaces_rows = self._deduplicate_rows(unit_replaces_rows)
        unit_upgrades_rows = self._deduplicate_rows(unit_upgrades_rows)
        unit_captures_rows = self._deduplicate_rows(unit_captures_rows)
        unit_retreat_rows = self._deduplicate_rows(unit_retreat_rows)
        unit_building_prereq_rows = self._deduplicate_rows(unit_building_prereq_rows)
        unit_ai_info_rows = self._deduplicate_rows(unit_ai_info_rows)
        tags_rows = self._deduplicate_rows(tags_rows)
        type_tags_rows = self._deduplicate_rows(type_tags_rows)
        ability_types_rows = self._deduplicate_rows(ability_types_rows)
        ability_tags_rows = self._deduplicate_rows(ability_tags_rows)
        ability_type_tags_rows = self._deduplicate_rows(ability_type_tags_rows)
        unit_abilities_rows = self._deduplicate_rows(unit_abilities_rows)
        custom_unit_abilities_rows = self._deduplicate_rows(custom_unit_abilities_rows)
        unit_text_rows = self._deduplicate_rows(unit_text_rows)
        ability_text_rows = self._deduplicate_rows(ability_text_rows)
        battle_text_rows = self._deduplicate_rows(battle_text_rows)
        text_rows = unit_text_rows + ability_text_rows + battle_text_rows

        sql_blocks: list[str] = []
        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        if traits_rows:
            sql_blocks.append(self._build_insert_block("Traits", "Traits", ["TraitType", "Name", "Description"], traits_rows))
        if units_rows:
            sql_blocks.append("-- Units")
            sql_blocks.append("\n\n".join(units_rows))
            sql_blocks.append("")
        if units_mode_rows:
            sql_blocks.append(self._build_insert_block("Units_MODE", "Units_MODE", ["UnitType", "ActionCharges"], units_mode_rows))
        if units_presentation_rows:
            sql_blocks.append(self._build_insert_block("Units_Presentation", "Units_Presentation", ["UnitType", "UIFlagOffset"], units_presentation_rows))
        if units_xp2_grouped_rows:
            for columns_key, grouped_rows in units_xp2_grouped_rows.items():
                if grouped_rows:
                    sql_blocks.append(self._build_insert_block("Units_XP2", "Units_XP2", list(columns_key), grouped_rows))
        if unit_replaces_rows:
            sql_blocks.append(self._build_insert_block("UnitReplaces", "UnitReplaces", ["CivUniqueUnitType", "ReplacesUnitType"], unit_replaces_rows))
        if unit_upgrades_rows:
            sql_blocks.append(self._build_insert_block("UnitUpgrades", "UnitUpgrades", ["Unit", "UpgradeUnit"], unit_upgrades_rows))
        if unit_captures_rows:
            sql_blocks.append(self._build_insert_block("UnitCaptures", "UnitCaptures", ["CapturedUnitType", "BecomesUnitType"], unit_captures_rows))
        if unit_retreat_rows:
            sql_blocks.append(self._build_insert_block("UnitRetreats_XP1", "UnitRetreats_XP1", ["UnitRetreatType", "BuildingType", "UnitType", "ImprovementType"], unit_retreat_rows))
        if unit_building_prereq_rows:
            sql_blocks.append(self._build_insert_block("Unit_BuildingPrereqs", "Unit_BuildingPrereqs", ["Unit", "PrereqBuilding", "NumSupported"], unit_building_prereq_rows))
        if unit_ai_info_rows:
            sql_blocks.append(self._build_insert_block("UnitAiInfos", "UnitAiInfos", ["UnitType", "AiType"], unit_ai_info_rows))
        if tags_rows:
            sql_blocks.append(self._build_insert_block("Tags", "Tags", ["Tag", "Vocabulary"], tags_rows))
        if type_tags_rows:
            sql_blocks.append(self._build_insert_block("TypeTags", "TypeTags", ["Type", "Tag"], type_tags_rows))
        if image_comment_rows:
            sql_blocks.append("-- 单位图标（简化单位）")
            sql_blocks.append("\n".join(image_comment_rows))
        units_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        units_sql = re.sub(r";\n(-- )", r";\n\n\1", units_sql)

        ability_sql_blocks: list[str] = []
        if ability_types_rows:
            ability_sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], ability_types_rows))
        if ability_tags_rows:
            ability_sql_blocks.append(self._build_insert_block("Tags", "Tags", ["Tag", "Vocabulary"], ability_tags_rows))
        if ability_type_tags_rows:
            ability_sql_blocks.append(self._build_insert_block("TypeTags", "TypeTags", ["Type", "Tag"], ability_type_tags_rows))
        if unit_abilities_rows:
            ability_sql_blocks.append(self._build_insert_block("UnitAbilities", "UnitAbilities", ["UnitAbilityType", "Name", "Description", "Inactive", "Permanent"], unit_abilities_rows))
        if custom_unit_abilities_rows:
            ability_sql_blocks.append(
                self._build_insert_block(
                    "UnitAbilities",
                    "UnitAbilities",
                    ["UnitAbilityType", "Name", "Description", "Inactive", "ShowFloatTextWhenEarned", "Permanent"],
                    custom_unit_abilities_rows,
                )
            )

        ability_sql = "\n".join([block for block in ability_sql_blocks if block and block.strip()]).rstrip()
        if not ability_sql:
            ability_sql = "-- UnitAbility.sql\n-- 暂无单位能力数据"

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return units_sql, ability_sql, text_sql

    def _build_improvement_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("改良设施")
        imp_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not imp_entries:
            return "-- Improvements.sql\n-- 暂无改良设施数据", "-- Text.sql\n-- 暂无改良设施文本数据"

        schema = build_improvements_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        traits_rows: list[str] = []
        improvements_rows: list[str] = []
        improvements_mode_rows: list[str] = []
        improvements_xp2_rows: list[str] = []
        improvement_tourism_rows: list[str] = []
        improvement_yields_outside_rows: list[str] = []
        improvement_bonus_yield_groups: dict[tuple[str, ...], list[str]] = {}
        improvement_yield_rows: list[str] = []
        improvement_invalid_adj_feature_rows: list[str] = []
        improvement_valid_adj_resource_rows: list[str] = []
        improvement_valid_adj_terrain_rows: list[str] = []
        improvement_valid_build_unit_rows: list[str] = []
        improvement_valid_feature_groups: dict[tuple[str, ...], list[str]] = {}
        improvement_valid_resource_rows: list[str] = []
        improvement_valid_terrain_groups: dict[tuple[str, ...], list[str]] = {}
        improvement_adjacency_rows: list[str] = []
        adjacency_custom_groups: dict[tuple[str, ...], list[str]] = {}
        text_rows: list[str] = []

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        def _normalized(field_key: str, value: object) -> object:
            default = field_defaults.get(field_key)
            if isinstance(default, int):
                try:
                    return int(value if value is not None else default)
                except (TypeError, ValueError):
                    return int(default)
            if isinstance(default, float):
                try:
                    return float(value if value is not None else default)
                except (TypeError, ValueError):
                    return float(default)
            if field_key == "TraitType":
                return str(value or "").strip()
            return str(value or "").strip()

        def _sql_literal(value: object) -> str:
            if value is None:
                return "NULL"
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                return format(value, ".15g")
            return f"'{self._sql_escape(str(value))}'"

        def _append_grouped_row(groups: dict[tuple[str, ...], list[str]], columns: list[str], values: list[object]) -> None:
            key = tuple(columns)
            row = "(" + ", ".join(_sql_literal(item) for item in values) + ")"
            groups.setdefault(key, []).append(row)

        for index, entry in enumerate(imp_entries, start=1):
            improvement_type = str(entry.get("type") or "").strip()
            if not improvement_type:
                improvement_type = f"IMPROVEMENT_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            name_zh = str(_value_or_default(table_data, "Name") or "")
            desc_zh = str(_value_or_default(table_data, "Description") or "")
            trait_type = str(_value_or_default(table_data, "TraitType") or "").strip()
            has_trait = bool(trait_type)

            types_rows.append(f"('{improvement_type}', 'KIND_IMPROVEMENT')")
            if has_trait:
                types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")
                traits_rows.append(f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')")

            text_rows.append(f"('zh_Hans_CN','LOC_{improvement_type}_NAME','{self._sql_escape(name_zh)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{improvement_type}_DESCRIPTION','{self._sql_escape(desc_zh)}')")
            if has_trait:
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{{LOC_{improvement_type}_NAME}}')")
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{{LOC_{improvement_type}_DESCRIPTION}}')")

            columns = ["ImprovementType", "Name", "Description", "Icon"]
            values: list[object] = [
                improvement_type,
                f"LOC_{improvement_type}_NAME",
                f"LOC_{improvement_type}_DESCRIPTION",
                f"ICON_{improvement_type}",
            ]

            for field in schema.fields:
                key = field.key
                if key in {"Name", "Description", "TraitType"}:
                    continue
                current = _normalized(key, _value_or_default(table_data, key))
                default = _normalized(key, field_defaults.get(key))
                if current == default:
                    continue
                columns.append(key)
                values.append(current)

            if has_trait:
                columns.append("TraitType")
                values.append(trait_type)

            improvements_rows.append(
                "INSERT INTO Improvements (\n    "
                + ",\n    ".join(columns)
                + "\n) VALUES\n(\n    "
                + ",\n    ".join(_sql_literal(item) for item in values)
                + "\n);"
            )

            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

            mode_payload = subtables.get("Improvements_MODE") if isinstance(subtables.get("Improvements_MODE"), dict) else entry.get("improvements_mode") if isinstance(entry.get("improvements_mode"), dict) else {}
            mode_defaults = {"Industry": 0, "Corporation": 0}
            mode_values = {
                "Industry": int(mode_payload.get("Industry", 0) or 0),
                "Corporation": int(mode_payload.get("Corporation", 0) or 0),
            }
            if any(mode_values[k] != mode_defaults[k] for k in mode_defaults):
                cols = ["ImprovementType"]
                vals: list[object] = [improvement_type]
                for key in ["Industry", "Corporation"]:
                    if mode_values[key] != mode_defaults[key]:
                        cols.append(key)
                        vals.append(mode_values[key])
                improvements_mode_rows.append("(" + ", ".join(_sql_literal(item) for item in vals) + ")")

            xp2_payload = subtables.get("Improvements_XP2") if isinstance(subtables.get("Improvements_XP2"), dict) else entry.get("improvements_xp2") if isinstance(entry.get("improvements_xp2"), dict) else {}
            xp2_defaults = {
                "AllowImpassableMovement": 0,
                "BuildOnAdjacentPlot": 0,
                "PreventsDrought": 0,
                "DisasterResistant": 0,
            }
            xp2_values = {
                "AllowImpassableMovement": int(xp2_payload.get("AllowImpassableMovement", 0) or 0),
                "BuildOnAdjacentPlot": int(xp2_payload.get("BuildOnAdjacentPlot", 0) or 0),
                "PreventsDrought": int(xp2_payload.get("PreventsDrought", 0) or 0),
                "DisasterResistant": int(xp2_payload.get("DisasterResistant", 0) or 0),
            }
            if any(xp2_values[k] != xp2_defaults[k] for k in xp2_defaults):
                cols = ["ImprovementType"]
                vals = [improvement_type]
                for key in ["AllowImpassableMovement", "BuildOnAdjacentPlot", "PreventsDrought", "DisasterResistant"]:
                    if xp2_values[key] != xp2_defaults[key]:
                        cols.append(key)
                        vals.append(xp2_values[key])
                improvements_xp2_rows.append("(" + ", ".join(_sql_literal(item) for item in vals) + ")")

            tourism_payload = subtables.get("Improvement_Tourism") if isinstance(subtables.get("Improvement_Tourism"), dict) else entry.get("improvement_tourism") if isinstance(entry.get("improvement_tourism"), dict) else {}
            tourism_defaults = {
                "TourismSource": "NO_TOURISMSOURCE",
                "PrereqCivic": "",
                "PrereqTech": "",
                "ScalingFactor": 100,
            }
            tourism_source = str(
                tourism_payload.get("TourismSource")
                or tourism_payload.get("tourism_source")
                or "NO_TOURISMSOURCE"
            ).strip() or "NO_TOURISMSOURCE"
            prereq_civic = str(
                tourism_payload.get("PrereqCivic")
                or tourism_payload.get("prereq_civic")
                or ""
            ).strip()
            prereq_tech = str(
                tourism_payload.get("PrereqTech")
                or tourism_payload.get("prereq_tech")
                or ""
            ).strip()
            scaling_factor_raw = tourism_payload.get("ScalingFactor")
            if scaling_factor_raw is None:
                scaling_factor_raw = tourism_payload.get("scaling_factor")
            if scaling_factor_raw is None:
                scaling_factor_raw = tourism_payload.get("scale_factor")
            try:
                scaling_factor = int(scaling_factor_raw if scaling_factor_raw is not None else 100)
            except (TypeError, ValueError):
                scaling_factor = 100
            tourism_values = {
                "TourismSource": tourism_source,
                "PrereqCivic": prereq_civic,
                "PrereqTech": prereq_tech,
                "ScalingFactor": scaling_factor,
            }
            if any(tourism_values[k] != tourism_defaults[k] for k in tourism_defaults):
                vals: list[object] = [
                    improvement_type,
                    tourism_values["TourismSource"],
                    tourism_values["PrereqCivic"] or None,
                    tourism_values["PrereqTech"] or None,
                    tourism_values["ScalingFactor"],
                ]
                improvement_tourism_rows.append("(" + ", ".join(_sql_literal(item) for item in vals) + ")")

            outside_payload = subtables.get("Improvement_YieldsOutsideTerritories") if isinstance(subtables.get("Improvement_YieldsOutsideTerritories"), list) else entry.get("improvement_yields_outside_territories") if isinstance(entry.get("improvement_yields_outside_territories"), list) else []
            if outside_payload:
                improvement_yields_outside_rows.append(f"('{improvement_type}')")

            bonus_payload = subtables.get("Improvement_BonusYieldChanges") if isinstance(subtables.get("Improvement_BonusYieldChanges"), list) else entry.get("improvement_bonus_yield_changes") if isinstance(entry.get("improvement_bonus_yield_changes"), list) else []
            for row_index, row in enumerate(bonus_payload, start=1):
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                bonus_change = int(row.get("BonusYieldChange", 0) or 0)
                prereq_tech = str(row.get("PrereqTech") or "").strip()
                prereq_civic = str(row.get("PrereqCivic") or "").strip()
                bonus_id = f"{improvement_type}_{row_index}"

                cols = ["Id", "ImprovementType", "YieldType", "BonusYieldChange"]
                vals: list[object] = [bonus_id, improvement_type, yield_type, bonus_change]
                if prereq_tech:
                    cols.append("PrereqTech")
                    vals.append(prereq_tech)
                if prereq_civic:
                    cols.append("PrereqCivic")
                    vals.append(prereq_civic)
                _append_grouped_row(improvement_bonus_yield_groups, cols, vals)

            yield_payload = subtables.get("Improvement_YieldChanges") if isinstance(subtables.get("Improvement_YieldChanges"), list) else entry.get("improvement_yield_changes") if isinstance(entry.get("improvement_yield_changes"), list) else []
            for row in yield_payload:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                yield_change = int(row.get("YieldChange", 0) or 0)
                improvement_yield_rows.append(f"('{improvement_type}', '{self._sql_escape(yield_type)}', {yield_change})")

            invalid_adj_feature_payload = subtables.get("Improvement_InvalidAdjacentFeatures") if isinstance(subtables.get("Improvement_InvalidAdjacentFeatures"), list) else entry.get("improvement_invalid_adjacent_features") if isinstance(entry.get("improvement_invalid_adjacent_features"), list) else []
            for row in invalid_adj_feature_payload:
                if not isinstance(row, dict):
                    continue
                feature_type = str(row.get("FeatureType") or "").strip()
                if feature_type:
                    improvement_invalid_adj_feature_rows.append(f"('{improvement_type}', '{self._sql_escape(feature_type)}')")

            valid_adj_resource_payload = subtables.get("Improvement_ValidAdjacentResources") if isinstance(subtables.get("Improvement_ValidAdjacentResources"), list) else entry.get("improvement_valid_adjacent_resources") if isinstance(entry.get("improvement_valid_adjacent_resources"), list) else []
            for row in valid_adj_resource_payload:
                if not isinstance(row, dict):
                    continue
                resource_type = str(row.get("ResourceType") or "").strip()
                if resource_type:
                    improvement_valid_adj_resource_rows.append(f"('{improvement_type}', '{self._sql_escape(resource_type)}')")

            valid_adj_terrain_payload = subtables.get("Improvement_ValidAdjacentTerrains") if isinstance(subtables.get("Improvement_ValidAdjacentTerrains"), list) else entry.get("improvement_valid_adjacent_terrains") if isinstance(entry.get("improvement_valid_adjacent_terrains"), list) else []
            for row in valid_adj_terrain_payload:
                if not isinstance(row, dict):
                    continue
                terrain_type = str(row.get("TerrainType") or "").strip()
                if terrain_type:
                    improvement_valid_adj_terrain_rows.append(f"('{improvement_type}', '{self._sql_escape(terrain_type)}')")

            valid_build_unit_payload = subtables.get("Improvement_ValidBuildUnits") if isinstance(subtables.get("Improvement_ValidBuildUnits"), list) else entry.get("improvement_valid_build_units") if isinstance(entry.get("improvement_valid_build_units"), list) else []
            for row in valid_build_unit_payload:
                if not isinstance(row, dict):
                    continue
                unit_type = str(row.get("UnitType") or "").strip()
                if unit_type:
                    improvement_valid_build_unit_rows.append(f"('{improvement_type}', '{self._sql_escape(unit_type)}')")

            valid_feature_payload = subtables.get("Improvement_ValidFeatures") if isinstance(subtables.get("Improvement_ValidFeatures"), list) else entry.get("improvement_valid_features") if isinstance(entry.get("improvement_valid_features"), list) else []
            for row in valid_feature_payload:
                if not isinstance(row, dict):
                    continue
                feature_type = str(row.get("FeatureType") or "").strip()
                if not feature_type:
                    continue
                prereq_tech = str(row.get("PrereqTech") or "").strip()
                prereq_civic = str(row.get("PrereqCivic") or "").strip()
                cols = ["ImprovementType", "FeatureType"]
                vals: list[object] = [improvement_type, feature_type]
                if prereq_tech:
                    cols.append("PrereqTech")
                    vals.append(prereq_tech)
                if prereq_civic:
                    cols.append("PrereqCivic")
                    vals.append(prereq_civic)
                _append_grouped_row(improvement_valid_feature_groups, cols, vals)

            valid_resource_payload = subtables.get("Improvement_ValidResources") if isinstance(subtables.get("Improvement_ValidResources"), list) else entry.get("improvement_valid_resources") if isinstance(entry.get("improvement_valid_resources"), list) else []
            for row in valid_resource_payload:
                if not isinstance(row, dict):
                    continue
                resource_type = str(row.get("ResourceType") or "").strip()
                if not resource_type:
                    continue
                must_remove_feature = int(row.get("MustRemoveFeature", 1) or 1)
                improvement_valid_resource_rows.append(f"('{improvement_type}', '{self._sql_escape(resource_type)}', {must_remove_feature})")

            valid_terrain_payload = subtables.get("Improvement_ValidTerrains") if isinstance(subtables.get("Improvement_ValidTerrains"), list) else entry.get("improvement_valid_terrains") if isinstance(entry.get("improvement_valid_terrains"), list) else []
            for row in valid_terrain_payload:
                if not isinstance(row, dict):
                    continue
                terrain_type = str(row.get("TerrainType") or "").strip()
                if not terrain_type:
                    continue
                prereq_tech = str(row.get("PrereqTech") or "").strip()
                prereq_civic = str(row.get("PrereqCivic") or "").strip()
                cols = ["ImprovementType", "TerrainType"]
                vals: list[object] = [improvement_type, terrain_type]
                if prereq_tech:
                    cols.append("PrereqTech")
                    vals.append(prereq_tech)
                if prereq_civic:
                    cols.append("PrereqCivic")
                    vals.append(prereq_civic)
                _append_grouped_row(improvement_valid_terrain_groups, cols, vals)

            adjacency_payload = subtables.get("Improvement_Adjacencies") if isinstance(subtables.get("Improvement_Adjacencies"), list) else entry.get("improvement_adjacencies") if isinstance(entry.get("improvement_adjacencies"), list) else []
            for adj in adjacency_payload:
                if not isinstance(adj, dict):
                    continue
                adj_mode = str(adj.get("mode") or adj.get("type") or "").strip().lower()
                adj_id = str(adj.get("id") or "").strip()
                if not adj_id:
                    continue
                improvement_adjacency_rows.append(f"('{improvement_type}', '{self._sql_escape(adj_id)}')")

                if adj_mode != "custom":
                    continue

                columns = ["ID", "Description", "YieldType", "YieldChange"]
                values: list[object] = [adj_id, "Placeholder", str(adj.get("yield_type") or ""), int(adj.get("yield_change", 0) or 0)]

                tiles_required = int(adj.get("tiles_required", 1) or 1)
                if tiles_required != 1:
                    columns.append("TilesRequired")
                    values.append(tiles_required)

                source_type = str(adj.get("source_type") or "").strip()
                source_detail = str(adj.get("source_detail") or "").strip()

                bool_source_fields = {
                    "OtherDistrictAdjacent": "OtherDistrictAdjacent",
                    "AdjacentSeaResource": "AdjacentSeaResource",
                    "AdjacentRiver": "AdjacentRiver",
                    "AdjacentWonder": "AdjacentWonder",
                    "AdjacentNaturalWonder": "AdjacentNaturalWonder",
                    "AdjacentResource": "AdjacentResource",
                    "Self": "Self",
                }
                value_source_fields = {
                    "AdjacentTerrain": "AdjacentTerrain",
                    "AdjacentFeature": "AdjacentFeature",
                    "AdjacentImprovement": "AdjacentImprovement",
                    "AdjacentDistrict": "AdjacentDistrict",
                    "AdjacentResourceClass": "AdjacentResourceClass",
                }

                if source_type in bool_source_fields:
                    columns.append(bool_source_fields[source_type])
                    values.append(1)
                elif source_type in value_source_fields and source_detail:
                    column_name = value_source_fields[source_type]
                    if not (source_type == "AdjacentResourceClass" and source_detail == "NO_RESOURCECLASS"):
                        columns.append(column_name)
                        values.append(source_detail)

                prereq_tech = str(adj.get("prereq_tech") or "").strip()
                prereq_civic = str(adj.get("prereq_civic") or "").strip()
                obsolete_tech = str(adj.get("obsolete_tech") or "").strip()
                obsolete_civic = str(adj.get("obsolete_civic") or "").strip()
                if prereq_tech:
                    columns.append("PrereqTech")
                    values.append(prereq_tech)
                if prereq_civic:
                    columns.append("PrereqCivic")
                    values.append(prereq_civic)
                if obsolete_tech:
                    columns.append("ObsoleteTech")
                    values.append(obsolete_tech)
                if obsolete_civic:
                    columns.append("ObsoleteCivic")
                    values.append(obsolete_civic)

                _append_grouped_row(adjacency_custom_groups, columns, values)

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        improvements_mode_rows = self._deduplicate_rows(improvements_mode_rows)
        improvements_xp2_rows = self._deduplicate_rows(improvements_xp2_rows)
        improvement_tourism_rows = self._deduplicate_rows(improvement_tourism_rows)
        improvement_yields_outside_rows = self._deduplicate_rows(improvement_yields_outside_rows)
        improvement_yield_rows = self._deduplicate_rows(improvement_yield_rows)
        improvement_invalid_adj_feature_rows = self._deduplicate_rows(improvement_invalid_adj_feature_rows)
        improvement_valid_adj_resource_rows = self._deduplicate_rows(improvement_valid_adj_resource_rows)
        improvement_valid_adj_terrain_rows = self._deduplicate_rows(improvement_valid_adj_terrain_rows)
        improvement_valid_build_unit_rows = self._deduplicate_rows(improvement_valid_build_unit_rows)
        improvement_valid_resource_rows = self._deduplicate_rows(improvement_valid_resource_rows)
        improvement_adjacency_rows = self._deduplicate_rows(improvement_adjacency_rows)
        text_rows = self._deduplicate_rows(text_rows)
        for columns_key in list(improvement_bonus_yield_groups.keys()):
            improvement_bonus_yield_groups[columns_key] = self._deduplicate_rows(improvement_bonus_yield_groups[columns_key])
        for columns_key in list(improvement_valid_feature_groups.keys()):
            improvement_valid_feature_groups[columns_key] = self._deduplicate_rows(improvement_valid_feature_groups[columns_key])
        for columns_key in list(improvement_valid_terrain_groups.keys()):
            improvement_valid_terrain_groups[columns_key] = self._deduplicate_rows(improvement_valid_terrain_groups[columns_key])
        for columns_key in list(adjacency_custom_groups.keys()):
            adjacency_custom_groups[columns_key] = self._deduplicate_rows(adjacency_custom_groups[columns_key])

        sql_blocks: list[str] = []
        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        if traits_rows:
            sql_blocks.append(self._build_insert_block("Traits", "Traits", ["TraitType", "Name", "Description"], traits_rows))
        if improvements_rows:
            sql_blocks.append("-- Improvements")
            sql_blocks.append("\n\n".join(improvements_rows))
            sql_blocks.append("")
        if improvements_mode_rows:
            sql_blocks.append(self._build_insert_block("Improvements_MODE", "Improvements_MODE", ["ImprovementType", "Industry", "Corporation"], improvements_mode_rows))
        if improvements_xp2_rows:
            sql_blocks.append(self._build_insert_block("Improvements_XP2", "Improvements_XP2", ["ImprovementType", "AllowImpassableMovement", "BuildOnAdjacentPlot", "PreventsDrought", "DisasterResistant"], improvements_xp2_rows))
        if improvement_tourism_rows:
            sql_blocks.append(self._build_insert_block("Improvement_Tourism", "Improvement_Tourism", ["ImprovementType", "TourismSource", "PrereqCivic", "PrereqTech", "ScalingFactor"], improvement_tourism_rows))
        if improvement_yields_outside_rows:
            sql_blocks.append(self._build_insert_block("Improvement_YieldsOutsideTerritories", "Improvement_YieldsOutsideTerritories", ["ImprovementType"], improvement_yields_outside_rows))
        for columns_key, rows in improvement_bonus_yield_groups.items():
            sql_blocks.append(self._build_insert_block("Improvement_BonusYieldChanges", "Improvement_BonusYieldChanges", list(columns_key), rows))
        if improvement_yield_rows:
            sql_blocks.append(self._build_insert_block("Improvement_YieldChanges", "Improvement_YieldChanges", ["ImprovementType", "YieldType", "YieldChange"], improvement_yield_rows))
        if improvement_invalid_adj_feature_rows:
            sql_blocks.append(self._build_insert_block("Improvement_InvalidAdjacentFeatures", "Improvement_InvalidAdjacentFeatures", ["ImprovementType", "FeatureType"], improvement_invalid_adj_feature_rows))
        if improvement_valid_adj_resource_rows:
            sql_blocks.append(self._build_insert_block("Improvement_ValidAdjacentResources", "Improvement_ValidAdjacentResources", ["ImprovementType", "ResourceType"], improvement_valid_adj_resource_rows))
        if improvement_valid_adj_terrain_rows:
            sql_blocks.append(self._build_insert_block("Improvement_ValidAdjacentTerrains", "Improvement_ValidAdjacentTerrains", ["ImprovementType", "TerrainType"], improvement_valid_adj_terrain_rows))
        if improvement_valid_build_unit_rows:
            sql_blocks.append(self._build_insert_block("Improvement_ValidBuildUnits", "Improvement_ValidBuildUnits", ["ImprovementType", "UnitType"], improvement_valid_build_unit_rows))
        for columns_key, rows in improvement_valid_feature_groups.items():
            sql_blocks.append(self._build_insert_block("Improvement_ValidFeatures", "Improvement_ValidFeatures", list(columns_key), rows))
        if improvement_valid_resource_rows:
            sql_blocks.append(self._build_insert_block("Improvement_ValidResources", "Improvement_ValidResources", ["ImprovementType", "ResourceType", "MustRemoveFeature"], improvement_valid_resource_rows))
        for columns_key, rows in improvement_valid_terrain_groups.items():
            sql_blocks.append(self._build_insert_block("Improvement_ValidTerrains", "Improvement_ValidTerrains", list(columns_key), rows))
        if improvement_adjacency_rows:
            sql_blocks.append(self._build_insert_block("Improvement_Adjacencies", "Improvement_Adjacencies", ["ImprovementType", "YieldChangeId"], improvement_adjacency_rows))

        for columns_key, rows in adjacency_custom_groups.items():
            sql_blocks.append(self._build_insert_block("Adjacency_YieldChanges", "Adjacency_YieldChanges", list(columns_key), rows))

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_policy_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("政策卡")
        policy_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not policy_entries:
            return "-- Policies.sql\n-- 暂无政策卡数据", "-- Text.sql\n-- 暂无政策卡文本数据"

        schema = build_policies_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        policies_rows: list[str] = []
        policies_xp1_rows: list[str] = []
        policy_exclusive_rows: list[str] = []
        text_rows: list[str] = []

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        def _normalized(field_key: str, value: object) -> object:
            default = field_defaults.get(field_key)
            if isinstance(default, int):
                try:
                    return int(value if value is not None else default)
                except (TypeError, ValueError):
                    return int(default)
            return str(value or "").strip()

        def _sql_literal(value: object | None) -> str:
            if value is None:
                return "NULL"
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                return format(value, ".15g")
            return f"'{self._sql_escape(str(value))}'"

        for index, entry in enumerate(policy_entries, start=1):
            policy_type = str(entry.get("type") or "").strip()
            if not policy_type:
                policy_type = f"POLICY_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            policy_name = str(_value_or_default(table_data, "Name") or "")
            policy_desc = str(_value_or_default(table_data, "Description") or "")

            prereq_civic = str(_normalized("PrereqCivic", _value_or_default(table_data, "PrereqCivic")) or "")
            prereq_tech = str(_normalized("PrereqTech", _value_or_default(table_data, "PrereqTech")) or "")
            slot_type = str(_normalized("GovernmentSlotType", _value_or_default(table_data, "GovernmentSlotType")) or "")
            if not slot_type:
                slot_type = "SLOT_WILDCARD"
            requires_unlock = int(_normalized("RequiresGovernmentUnlock", _value_or_default(table_data, "RequiresGovernmentUnlock")) or 0)
            explicit_unlock = int(_normalized("ExplicitUnlock", _value_or_default(table_data, "ExplicitUnlock")) or 0)

            types_rows.append(f"('{policy_type}', 'KIND_POLICY')")

            text_rows.append(f"('zh_Hans_CN','LOC_{policy_type}_NAME','{self._sql_escape(policy_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{policy_type}_DESCRIPTION','{self._sql_escape(policy_desc)}')")

            policy_values: list[object | None] = [
                policy_type,
                f"LOC_{policy_type}_NAME",
                f"LOC_{policy_type}_DESCRIPTION",
                prereq_civic or None,
                prereq_tech or None,
                slot_type,
                requires_unlock,
                explicit_unlock,
            ]

            policies_rows.append("(" + ", ".join(_sql_literal(item) for item in policy_values) + ")")

            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
            xp1_payload = subtables.get("Policies_XP1") if isinstance(subtables.get("Policies_XP1"), dict) else entry.get("policies_xp1") if isinstance(entry.get("policies_xp1"), dict) else {}
            min_era = str(xp1_payload.get("MinimumGameEra") or "").strip()
            max_era = str(xp1_payload.get("MaximumGameEra") or "").strip()
            requires_dark_age = int(xp1_payload.get("RequiresDarkAge", 0) or 0)
            requires_golden_age = int(xp1_payload.get("RequiresGoldenAge", 0) or 0)
            if min_era or max_era or requires_dark_age or requires_golden_age:
                policies_xp1_rows.append(
                    "(" + ", ".join(
                        _sql_literal(item)
                        for item in [policy_type, min_era or None, max_era or None, requires_dark_age, requires_golden_age]
                    ) + ")"
                )

            exclusive_payload = subtables.get("Policy_GovernmentExclusives_XP2") if isinstance(subtables.get("Policy_GovernmentExclusives_XP2"), dict) else entry.get("policy_government_exclusive") if isinstance(entry.get("policy_government_exclusive"), dict) else {}
            government_type = str(exclusive_payload.get("GovernmentType") or "").strip()
            if government_type:
                policy_exclusive_rows.append(f"('{self._sql_escape(policy_type)}', '{self._sql_escape(government_type)}')")

        types_rows = self._deduplicate_rows(types_rows)
        policies_rows = self._deduplicate_rows(policies_rows)
        policies_xp1_rows = self._deduplicate_rows(policies_xp1_rows)
        policy_exclusive_rows = self._deduplicate_rows(policy_exclusive_rows)
        text_rows = self._deduplicate_rows(text_rows)

        sql_blocks: list[str] = []
        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        if policies_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "Policies",
                    "Policies",
                    [
                        "PolicyType",
                        "Name",
                        "Description",
                        "PrereqCivic",
                        "PrereqTech",
                        "GovernmentSlotType",
                        "RequiresGovernmentUnlock",
                        "ExplicitUnlock",
                    ],
                    policies_rows,
                )
            )
        if policies_xp1_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "Policies_XP1",
                    "Policies_XP1",
                    ["PolicyType", "MinimumGameEra", "MaximumGameEra", "RequiresDarkAge", "RequiresGoldenAge"],
                    policies_xp1_rows,
                )
            )
        if policy_exclusive_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "Policy_GovernmentExclusives_XP2",
                    "Policy_GovernmentExclusives_XP2",
                    ["PolicyType", "GovernmentType"],
                    policy_exclusive_rows,
                )
            )

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_project_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("项目")
        project_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not project_entries:
            return "-- Projects.sql\n-- 暂无项目数据", "-- Text.sql\n-- 暂无项目文本数据"

        schema = build_projects_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        projects_grouped: dict[tuple[str, ...], list[str]] = {}
        projects_mode_grouped: dict[tuple[str, ...], list[str]] = {}
        projects_xp1_grouped: dict[tuple[str, ...], list[str]] = {}
        projects_xp2_grouped: dict[tuple[str, ...], list[str]] = {}
        project_building_costs_rows: list[str] = []
        project_great_person_points_grouped: dict[tuple[str, ...], list[str]] = {}
        project_resource_costs_rows: list[str] = []
        project_yield_conversions_grouped: dict[tuple[str, ...], list[str]] = {}
        project_prereqs_rows: list[str] = []
        text_rows: list[str] = []

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        def _normalized(field_key: str, value: object) -> object:
            default = field_defaults.get(field_key)
            if isinstance(default, int):
                try:
                    return int(value if value is not None else default)
                except (TypeError, ValueError):
                    return int(default)
            return str(value or "").strip()

        def _sql_literal(value: object | None) -> str:
            if value is None:
                return "NULL"
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                return format(value, ".15g")
            return f"'{self._sql_escape(str(value))}'"

        def _is_default(value: object | None, default: object | None) -> bool:
            if value is None:
                return default is None or default == ""
            if isinstance(default, bool):
                return bool(value) == default
            if isinstance(default, int):
                try:
                    return int(value) == default
                except (TypeError, ValueError):
                    return False
            if isinstance(default, float):
                try:
                    return abs(float(value) - default) < 1e-12
                except (TypeError, ValueError):
                    return False
            return str(value or "").strip() == str(default or "").strip()

        def _append_grouped_row(
            grouped: dict[tuple[str, ...], list[str]],
            *,
            required_columns: list[str],
            values: dict[str, object | None],
            optional_defaults: dict[str, object | None],
        ) -> None:
            columns = list(required_columns)
            for col_name, default_value in optional_defaults.items():
                value = values.get(col_name)
                if _is_default(value, default_value):
                    continue
                columns.append(col_name)
            key = tuple(columns)
            row_sql = "(" + ", ".join(_sql_literal(values.get(col)) for col in columns) + ")"
            grouped.setdefault(key, []).append(row_sql)

        def _append_grouped_blocks(
            sql_blocks: list[str],
            *,
            comment: str,
            table: str,
            grouped: dict[tuple[str, ...], list[str]],
        ) -> None:
            for columns_key, rows in grouped.items():
                dedup_rows = self._deduplicate_rows(rows)
                if not dedup_rows:
                    continue
                sql_blocks.append(self._build_insert_block(comment, table, list(columns_key), dedup_rows))

        def _count_grouped_rows(grouped: dict[tuple[str, ...], list[str]]) -> int:
            return sum(len(rows) for rows in grouped.values())

        for index, entry in enumerate(project_entries, start=1):
            project_type = str(entry.get("type") or "").strip()
            if not project_type:
                project_type = f"PROJECT_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            project_name = str(_value_or_default(table_data, "Name") or "")
            short_name = str(_value_or_default(table_data, "ShortName") or "")
            description = str(_value_or_default(table_data, "Description") or "")
            popup_text = str(_value_or_default(table_data, "PopupText") or "")

            types_rows.append(f"('{project_type}', 'KIND_PROJECT')")

            text_rows.append(f"('zh_Hans_CN','LOC_{project_type}_NAME','{self._sql_escape(project_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{project_type}_SHORT_NAME','{self._sql_escape(short_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{project_type}_DESCRIPTION','{self._sql_escape(description)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{project_type}_POPUP_TEXT','{self._sql_escape(popup_text)}')")

            project_values: dict[str, object | None] = {
                "ProjectType": project_type,
                "Name": f"LOC_{project_type}_NAME",
                "ShortName": f"LOC_{project_type}_SHORT_NAME",
                "Description": f"LOC_{project_type}_DESCRIPTION" if description else None,
                "PopupText": f"LOC_{project_type}_POPUP_TEXT" if popup_text else None,
                "Cost": _normalized("Cost", _value_or_default(table_data, "Cost")),
                "CostProgressionModel": _normalized("CostProgressionModel", _value_or_default(table_data, "CostProgressionModel")) or "NO_PROGRESSION_MODEL",
                "CostProgressionParam1": _normalized("CostProgressionParam1", _value_or_default(table_data, "CostProgressionParam1")),
                "PrereqTech": _normalized("PrereqTech", _value_or_default(table_data, "PrereqTech")) or None,
                "PrereqCivic": _normalized("PrereqCivic", _value_or_default(table_data, "PrereqCivic")) or None,
                "PrereqDistrict": _normalized("PrereqDistrict", _value_or_default(table_data, "PrereqDistrict")) or None,
                "RequiredBuilding": _normalized("RequiredBuilding", _value_or_default(table_data, "RequiredBuilding")) or None,
                "VisualBuildingType": _normalized("VisualBuildingType", _value_or_default(table_data, "VisualBuildingType")) or None,
                "SpaceRace": _normalized("SpaceRace", _value_or_default(table_data, "SpaceRace")),
                "OuterDefenseRepair": _normalized("OuterDefenseRepair", _value_or_default(table_data, "OuterDefenseRepair")),
                "MaxPlayerInstances": _normalized("MaxPlayerInstances", _value_or_default(table_data, "MaxPlayerInstances")),
                "AmenitiesWhileActive": _normalized("AmenitiesWhileActive", _value_or_default(table_data, "AmenitiesWhileActive")),
                "PrereqResource": _normalized("PrereqResource", _value_or_default(table_data, "PrereqResource")) or None,
                "AdvisorType": _normalized("AdvisorType", _value_or_default(table_data, "AdvisorType")) or None,
                "WMD": _normalized("WMD", _value_or_default(table_data, "WMD")),
                "UnlocksFromEffect": _normalized("UnlocksFromEffect", _value_or_default(table_data, "UnlocksFromEffect")),
            }
            _append_grouped_row(
                projects_grouped,
                required_columns=["ProjectType", "Name", "ShortName", "Cost"],
                values=project_values,
                optional_defaults={
                    "Description": None,
                    "PopupText": None,
                    "CostProgressionModel": "NO_PROGRESSION_MODEL",
                    "CostProgressionParam1": 0,
                    "PrereqTech": None,
                    "PrereqCivic": None,
                    "PrereqDistrict": None,
                    "RequiredBuilding": None,
                    "VisualBuildingType": None,
                    "SpaceRace": 0,
                    "OuterDefenseRepair": 0,
                    "MaxPlayerInstances": -1,
                    "AmenitiesWhileActive": 0,
                    "PrereqResource": None,
                    "AdvisorType": None,
                    "WMD": 0,
                    "UnlocksFromEffect": 0,
                },
            )

            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}

            mode_payload = subtables.get("Projects_MODE") if isinstance(subtables.get("Projects_MODE"), dict) else entry.get("projects_mode") if isinstance(entry.get("projects_mode"), dict) else {}
            mode_improvement = str(mode_payload.get("PrereqImprovement") or "").strip()
            mode_resource = str(mode_payload.get("ResourceType") or "").strip()
            if mode_improvement or mode_resource:
                _append_grouped_row(
                    projects_mode_grouped,
                    required_columns=["ProjectType"],
                    values={
                        "ProjectType": project_type,
                        "PrereqImprovement": mode_improvement or None,
                        "ResourceType": mode_resource or None,
                    },
                    optional_defaults={
                        "PrereqImprovement": None,
                        "ResourceType": None,
                    },
                )

            xp1_payload = subtables.get("Projects_XP1") if isinstance(subtables.get("Projects_XP1"), dict) else entry.get("projects_xp1") if isinstance(entry.get("projects_xp1"), dict) else {}
            xp1_identity = float(xp1_payload.get("IdentityPerCitizenChange", 0.0) or 0.0)
            xp1_unlocks = int(xp1_payload.get("UnlocksFromEffect", 0) or 0)
            if xp1_identity != 0.0 or xp1_unlocks != 0:
                _append_grouped_row(
                    projects_xp1_grouped,
                    required_columns=["ProjectType"],
                    values={
                        "ProjectType": project_type,
                        "IdentityPerCitizenChange": xp1_identity,
                        "UnlocksFromEffect": xp1_unlocks,
                    },
                    optional_defaults={
                        "IdentityPerCitizenChange": 0.0,
                        "UnlocksFromEffect": 0,
                    },
                )

            xp2_payload = subtables.get("Projects_XP2") if isinstance(subtables.get("Projects_XP2"), dict) else entry.get("projects_xp2") if isinstance(entry.get("projects_xp2"), dict) else {}
            xp2_required_power = int(xp2_payload.get("RequiredPowerWhileActive", 0) or 0)
            xp2_religious = int(xp2_payload.get("ReligiousPressureModifier", 0) or 0)
            xp2_unlocks = int(xp2_payload.get("UnlocksFromEffect", 0) or 0)
            xp2_required_building = str(xp2_payload.get("RequiredBuilding") or "").strip()
            xp2_create_building = str(xp2_payload.get("CreateBuilding") or "").strip()
            xp2_fully_powered = int(xp2_payload.get("FullyPoweredWhileActive", 0) or 0)
            xp2_max_sim = int(xp2_payload.get("MaxSimultaneousInstances", 0) or 0)
            if (
                xp2_required_power != 0
                or xp2_religious != 0
                or xp2_unlocks != 0
                or xp2_required_building
                or xp2_create_building
                or xp2_fully_powered != 0
                or xp2_max_sim != 0
            ):
                _append_grouped_row(
                    projects_xp2_grouped,
                    required_columns=["ProjectType"],
                    values={
                        "ProjectType": project_type,
                        "RequiredPowerWhileActive": xp2_required_power,
                        "ReligiousPressureModifier": xp2_religious,
                        "UnlocksFromEffect": xp2_unlocks,
                        "RequiredBuilding": xp2_required_building or None,
                        "CreateBuilding": xp2_create_building or None,
                        "FullyPoweredWhileActive": xp2_fully_powered,
                        "MaxSimultaneousInstances": xp2_max_sim,
                    },
                    optional_defaults={
                        "RequiredPowerWhileActive": 0,
                        "ReligiousPressureModifier": 0,
                        "UnlocksFromEffect": 0,
                        "RequiredBuilding": None,
                        "CreateBuilding": None,
                        "FullyPoweredWhileActive": 0,
                        "MaxSimultaneousInstances": 0,
                    },
                )

            building_costs = subtables.get("Project_BuildingCosts") if isinstance(subtables.get("Project_BuildingCosts"), list) else entry.get("project_building_costs") if isinstance(entry.get("project_building_costs"), list) else []
            for row in building_costs:
                if not isinstance(row, dict):
                    continue
                consumed_building = str(row.get("ConsumedBuildingType") or "").strip()
                if not consumed_building:
                    continue
                project_building_costs_rows.append(
                    "(" + ", ".join(_sql_literal(item) for item in [project_type, consumed_building]) + ")"
                )

            great_person_rows = subtables.get("Project_GreatPersonPoints") if isinstance(subtables.get("Project_GreatPersonPoints"), list) else entry.get("project_great_person_points") if isinstance(entry.get("project_great_person_points"), list) else []
            for row in great_person_rows:
                if not isinstance(row, dict):
                    continue
                class_type = str(row.get("GreatPersonClassType") or "").strip()
                if not class_type:
                    continue
                points = int(row.get("Points", 0) or 0)
                progression = str(row.get("PointProgressionModel") or "").strip() or "NO_PROGRESSION_MODEL"
                progression_param = int(row.get("PointProgressionParam1", 0) or 0)
                _append_grouped_row(
                    project_great_person_points_grouped,
                    required_columns=["ProjectType", "GreatPersonClassType"],
                    values={
                        "ProjectType": project_type,
                        "GreatPersonClassType": class_type,
                        "Points": points,
                        "PointProgressionModel": progression,
                        "PointProgressionParam1": progression_param,
                    },
                    optional_defaults={
                        "Points": 0,
                        "PointProgressionModel": "NO_PROGRESSION_MODEL",
                        "PointProgressionParam1": 0,
                    },
                )

            resource_rows = subtables.get("Project_ResourceCosts") if isinstance(subtables.get("Project_ResourceCosts"), list) else entry.get("project_resource_costs") if isinstance(entry.get("project_resource_costs"), list) else []
            for row in resource_rows:
                if not isinstance(row, dict):
                    continue
                resource_type = str(row.get("ResourceType") or "").strip()
                if not resource_type:
                    continue
                start_cost = int(row.get("StartProductionCost", 0) or 0)
                project_resource_costs_rows.append(
                    "(" + ", ".join(_sql_literal(item) for item in [project_type, resource_type, start_cost]) + ")"
                )

            conversion_rows = subtables.get("Project_YieldConversions") if isinstance(subtables.get("Project_YieldConversions"), list) else entry.get("project_yield_conversions") if isinstance(entry.get("project_yield_conversions"), list) else []
            for row in conversion_rows:
                if not isinstance(row, dict):
                    continue
                yield_type = str(row.get("YieldType") or "").strip()
                if not yield_type:
                    continue
                percent_rate = int(row.get("PercentOfProductionRate", 0) or 0)
                _append_grouped_row(
                    project_yield_conversions_grouped,
                    required_columns=["ProjectType", "YieldType"],
                    values={
                        "ProjectType": project_type,
                        "YieldType": yield_type,
                        "PercentOfProductionRate": percent_rate,
                    },
                    optional_defaults={
                        "PercentOfProductionRate": 0,
                    },
                )

            prereq_rows = subtables.get("ProjectPrereqs") if isinstance(subtables.get("ProjectPrereqs"), list) else entry.get("project_prereqs") if isinstance(entry.get("project_prereqs"), list) else []
            for row in prereq_rows:
                if not isinstance(row, dict):
                    continue
                prereq_project_type = str(row.get("PrereqProjectType") or "").strip()
                if not prereq_project_type:
                    continue
                min_instances = int(row.get("MinimumPlayerInstances", 1) or 1)
                project_prereqs_rows.append(
                    "(" + ", ".join(_sql_literal(item) for item in [project_type, prereq_project_type, min_instances]) + ")"
                )

        types_rows = self._deduplicate_rows(types_rows)
        project_building_costs_rows = self._deduplicate_rows(project_building_costs_rows)
        project_resource_costs_rows = self._deduplicate_rows(project_resource_costs_rows)
        project_prereqs_rows = self._deduplicate_rows(project_prereqs_rows)
        text_rows = self._deduplicate_rows(text_rows)

        LOGGER.info(
            "Built project SQL preview: entries=%d, mode=%d, xp1=%d, xp2=%d, prereqs=%d",
            len(project_entries),
            _count_grouped_rows(projects_mode_grouped),
            _count_grouped_rows(projects_xp1_grouped),
            _count_grouped_rows(projects_xp2_grouped),
            len(project_prereqs_rows),
        )

        sql_blocks: list[str] = []
        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        _append_grouped_blocks(sql_blocks, comment="Projects", table="Projects", grouped=projects_grouped)
        _append_grouped_blocks(sql_blocks, comment="Projects_MODE", table="Projects_MODE", grouped=projects_mode_grouped)
        _append_grouped_blocks(sql_blocks, comment="Projects_XP1", table="Projects_XP1", grouped=projects_xp1_grouped)
        _append_grouped_blocks(sql_blocks, comment="Projects_XP2", table="Projects_XP2", grouped=projects_xp2_grouped)
        if project_building_costs_rows:
            sql_blocks.append(self._build_insert_block("Project_BuildingCosts", "Project_BuildingCosts", ["ProjectType", "ConsumedBuildingType"], project_building_costs_rows))
        _append_grouped_blocks(
            sql_blocks,
            comment="Project_GreatPersonPoints",
            table="Project_GreatPersonPoints",
            grouped=project_great_person_points_grouped,
        )
        if project_resource_costs_rows:
            sql_blocks.append(self._build_insert_block("Project_ResourceCosts", "Project_ResourceCosts", ["ProjectType", "ResourceType", "StartProductionCost"], project_resource_costs_rows))
        _append_grouped_blocks(
            sql_blocks,
            comment="Project_YieldConversions",
            table="Project_YieldConversions",
            grouped=project_yield_conversions_grouped,
        )
        if project_prereqs_rows:
            sql_blocks.append(self._build_insert_block("ProjectPrereqs", "ProjectPrereqs", ["ProjectType", "PrereqProjectType", "MinimumPlayerInstances"], project_prereqs_rows))

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_belief_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("信仰")
        belief_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not belief_entries:
            return "-- Beliefs.sql\n-- 暂无信仰数据", "-- Text.sql\n-- 暂无信仰文本数据"

        schema = build_beliefs_main_schema()
        field_defaults: dict[str, object] = {field.key: field.default for field in schema.fields}

        types_rows: list[str] = []
        beliefs_rows: list[str] = []
        text_rows: list[str] = []

        def _value_or_default(data: dict[str, object], key: str) -> object:
            value = data.get(key)
            if value is None:
                return field_defaults.get(key)
            return value

        for index, entry in enumerate(belief_entries, start=1):
            belief_type = str(entry.get("type") or "").strip()
            if not belief_type:
                belief_type = f"BELIEF_CUSTOM_{index}"

            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            belief_name = str(_value_or_default(table_data, "Name") or "")
            belief_desc = str(_value_or_default(table_data, "Description") or "")
            belief_class_type = str(_value_or_default(table_data, "BeliefClassType") or "").strip()
            if not belief_class_type:
                belief_class_type = "BELIEF_CLASS_PANTHEON"

            types_rows.append(f"('{self._sql_escape(belief_type)}', 'KIND_BELIEF')")
            beliefs_rows.append(
                "(" + ", ".join(
                    [
                        f"'{self._sql_escape(belief_type)}'",
                        f"'LOC_{self._sql_escape(belief_type)}_NAME'",
                        f"'LOC_{self._sql_escape(belief_type)}_DESCRIPTION'",
                        f"'{self._sql_escape(belief_class_type)}'",
                    ]
                ) + ")"
            )
            text_rows.append(f"('zh_Hans_CN','LOC_{belief_type}_NAME','{self._sql_escape(belief_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{belief_type}_DESCRIPTION','{self._sql_escape(belief_desc)}')")

        types_rows = self._deduplicate_rows(types_rows)
        beliefs_rows = self._deduplicate_rows(beliefs_rows)
        text_rows = self._deduplicate_rows(text_rows)

        LOGGER.info("Built belief SQL preview: entries=%d", len(belief_entries))

        sql_blocks: list[str] = []
        sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        sql_blocks.append(self._build_insert_block("Beliefs", "Beliefs", ["BeliefType", "Name", "Description", "BeliefClassType"], beliefs_rows))

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_governor_sql_pair(self) -> tuple[str, str]:
        entries = self._project.sections.get("总督")
        governor_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not governor_entries:
            return "-- Governors.sql\n-- 暂无总督数据", "-- Text.sql\n-- 暂无总督文本数据"

        types_rows: list[str] = []
        traits_rows: list[str] = []
        governors_rows: list[str] = []
        governors_xp2_rows: list[str] = []
        governors_cannot_assign_rows: list[str] = []
        promotion_sets_rows: list[str] = []
        promotions_rows: list[str] = []
        promotion_prereq_rows: list[str] = []
        text_rows: list[str] = []

        def _promo_type(governor_type: str, level: int, col: int) -> str:
            if level == 0:
                return f"{governor_type}_PROMOTION_BASE"
            letter = {0: "L", 1: "M", 2: "R"}.get(col, "M")
            return f"{governor_type}_PROMOTION_{letter}{level}"

        def _promo_parents(level: int, col: int) -> list[tuple[int, int]]:
            if level <= 1:
                return [(0, 1)]
            if col == 0:
                return [(level - 1, 0), (level - 1, 1)]
            if col == 1:
                return [(level - 1, 0), (level - 1, 1), (level - 1, 2)]
            return [(level - 1, 2), (level - 1, 1)]

        for entry in governor_entries:
            governor_type = str(entry.get("GovernorType") or "").strip()
            if not governor_type:
                continue

            name_text = str(entry.get("Name") or "").strip()
            desc_text = str(entry.get("Description") or "").strip()
            title_text = str(entry.get("Title") or "").strip()
            short_title_text = str(entry.get("ShortTitle") or "").strip()
            identity_pressure = int(entry.get("IdentityPressure", 0) or 0)
            transition_strength = int(entry.get("TransitionStrength", 0) or 0)
            assign_city_state = 1 if bool(entry.get("AssignCityState", False)) else 0

            trait_type = str(entry.get("TraitType") or "").strip()
            new_trait_type = bool(entry.get("new_trait_type", False))
            if new_trait_type and trait_type:
                types_rows.append(f"('{trait_type}', 'KIND_TRAIT')")
                traits_rows.append(
                    f"('{trait_type}', 'LOC_{trait_type}_NAME', 'LOC_{trait_type}_DESCRIPTION')"
                )

            image_name = f"{governor_type}_NORMAL"
            portrait_name = f"{governor_type}_NORMAL"
            portrait_selected_name = f"{governor_type}_SELECTED"
            trait_sql = f"'{self._sql_escape(trait_type)}'" if trait_type else "NULL"

            types_rows.append(f"('{governor_type}', 'KIND_GOVERNOR')")
            governors_rows.append(
                "(" + ", ".join(
                    [
                        f"'{governor_type}'",
                        f"'LOC_{governor_type}_NAME'",
                        f"'LOC_{governor_type}_DESCRIPTION'",
                        str(identity_pressure),
                        f"'LOC_{governor_type}_TITLE'",
                        f"'LOC_{governor_type}_SHORT_TITLE'",
                        str(transition_strength),
                        str(assign_city_state),
                        f"'{image_name}'",
                        f"'{portrait_name}'",
                        f"'{portrait_selected_name}'",
                        trait_sql,
                    ]
                ) + ")"
            )

            text_rows.append(f"('zh_Hans_CN','LOC_{governor_type}_NAME','{self._sql_escape(name_text)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{governor_type}_DESCRIPTION','{self._sql_escape(desc_text)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{governor_type}_TITLE','{self._sql_escape(title_text)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{governor_type}_SHORT_TITLE','{self._sql_escape(short_title_text)}')")

            # 仅当“新TraitType”勾选时，才生成 Trait 文本键。
            # 未勾选表示复用已存在 TraitType，此处不应新增文本预览。
            if new_trait_type and trait_type:
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_NAME','{{LOC_{governor_type}_NAME}}')")
                text_rows.append(f"('zh_Hans_CN','LOC_{trait_type}_DESCRIPTION','{{LOC_{governor_type}_DESCRIPTION}}')")

            if bool(entry.get("assign_to_major", False)):
                governors_xp2_rows.append(f"('{governor_type}', 1)")
            if bool(entry.get("cannot_assign", False)):
                governors_cannot_assign_rows.append(f"('{governor_type}', 1)")

            promotions = entry.get("promotions") if isinstance(entry.get("promotions"), dict) else {}
            base_payload = promotions.get("base") if isinstance(promotions.get("base"), dict) else {}
            base_name = str(base_payload.get("name") or "").strip()
            base_desc = str(base_payload.get("description") or "").strip()
            base_type = _promo_type(governor_type, 0, 1)
            types_rows.append(f"('{base_type}', 'KIND_GOVERNOR_PROMOTION')")
            promotion_sets_rows.append(f"('{governor_type}', '{base_type}')")
            promotions_rows.append(
                f"('{base_type}', 'LOC_{base_type}_NAME', 'LOC_{base_type}_DESCRIPTION', 0, 1, 1)"
            )
            text_rows.append(f"('zh_Hans_CN','LOC_{base_type}_NAME','{self._sql_escape(base_name)}')")
            text_rows.append(f"('zh_Hans_CN','LOC_{base_type}_DESCRIPTION','{self._sql_escape(base_desc)}')")

            active_nodes: set[tuple[int, int]] = set()
            tiers = promotions.get("tiers") if isinstance(promotions.get("tiers"), list) else []
            for level in range(1, 4):
                row_data = tiers[level - 1] if level - 1 < len(tiers) and isinstance(tiers[level - 1], list) else []
                for col in range(3):
                    node = row_data[col] if col < len(row_data) and isinstance(row_data[col], dict) else {}
                    enabled = bool(node.get("enabled", False))
                    if not enabled:
                        continue
                    active_nodes.add((level, col))
                    promotion_type = _promo_type(governor_type, level, col)
                    promotion_name = str(node.get("name") or "").strip()
                    promotion_desc = str(node.get("description") or "").strip()

                    types_rows.append(f"('{promotion_type}', 'KIND_GOVERNOR_PROMOTION')")
                    promotion_sets_rows.append(f"('{governor_type}', '{promotion_type}')")
                    promotions_rows.append(
                        f"('{promotion_type}', 'LOC_{promotion_type}_NAME', 'LOC_{promotion_type}_DESCRIPTION', {level}, {col}, 0)"
                    )
                    text_rows.append(f"('zh_Hans_CN','LOC_{promotion_type}_NAME','{self._sql_escape(promotion_name)}')")
                    text_rows.append(f"('zh_Hans_CN','LOC_{promotion_type}_DESCRIPTION','{self._sql_escape(promotion_desc)}')")

            for level in range(1, 4):
                for col in range(3):
                    if (level, col) not in active_nodes:
                        continue
                    current_type = _promo_type(governor_type, level, col)
                    for parent_level, parent_col in _promo_parents(level, col):
                        if parent_level == 0:
                            parent_type = base_type
                        else:
                            if (parent_level, parent_col) not in active_nodes:
                                continue
                            parent_type = _promo_type(governor_type, parent_level, parent_col)
                        promotion_prereq_rows.append(
                            f"('{current_type}', '{parent_type}')"
                        )

        types_rows = self._deduplicate_rows(types_rows)
        traits_rows = self._deduplicate_rows(traits_rows)
        governors_rows = self._deduplicate_rows(governors_rows)
        governors_xp2_rows = self._deduplicate_rows(governors_xp2_rows)
        governors_cannot_assign_rows = self._deduplicate_rows(governors_cannot_assign_rows)
        promotion_sets_rows = self._deduplicate_rows(promotion_sets_rows)
        promotions_rows = self._deduplicate_rows(promotions_rows)
        promotion_prereq_rows = self._deduplicate_rows(promotion_prereq_rows)
        text_rows = self._deduplicate_rows(text_rows)

        sql_blocks: list[str] = []
        if types_rows:
            sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], types_rows))
        if traits_rows:
            sql_blocks.append(self._build_insert_block("Traits", "Traits", ["TraitType", "Name", "Description"], traits_rows))
        if governors_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "Governors",
                    "Governors",
                    [
                        "GovernorType",
                        "Name",
                        "Description",
                        "IdentityPressure",
                        "Title",
                        "ShortTitle",
                        "TransitionStrength",
                        "AssignCityState",
                        "Image",
                        "PortraitImage",
                        "PortraitImageSelected",
                        "TraitType",
                    ],
                    governors_rows,
                )
            )
        if governors_xp2_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "Governors_XP2",
                    "Governors_XP2",
                    ["GovernorType", "AssignToMajor"],
                    governors_xp2_rows,
                )
            )
        if governors_cannot_assign_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "GovernorsCannotAssign",
                    "GovernorsCannotAssign",
                    ["GovernorType", "CannotAssign"],
                    governors_cannot_assign_rows,
                )
            )
        if promotion_sets_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "GovernorPromotionSets",
                    "GovernorPromotionSets",
                    ["GovernorType", "GovernorPromotion"],
                    promotion_sets_rows,
                )
            )
        if promotions_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "GovernorPromotions",
                    "GovernorPromotions",
                    ["GovernorPromotionType", "Name", "Description", "Level", "Column", "BaseAbility"],
                    promotions_rows,
                )
            )
        if promotion_prereq_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "GovernorPromotionPrereqs",
                    "GovernorPromotionPrereqs",
                    ["GovernorPromotionType", "PrereqGovernorPromotion"],
                    promotion_prereq_rows,
                )
            )

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)

        LOGGER.info(
            "[GovernorSql] entries=%d governors=%d promotions=%d text_rows=%d traits=%d",
            len(governor_entries),
            len(governors_rows),
            len(promotions_rows),
            len(text_rows),
            len(traits_rows),
        )

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, text_sql

    def _build_great_people_sql_bundle(self) -> tuple[str, str, str]:
        entries = self._project.sections.get("伟人")
        great_entries = [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
        if not great_entries:
            return "-- GreatPeople.sql\n-- 暂无伟人数据", "-- GreatWorks.sql\n-- 暂无巨作数据", "-- Text.sql\n-- 暂无伟人文本数据"

        gp_types_rows: list[str] = []
        greatwork_types_rows: list[str] = []
        classes_rows: list[str] = []
        greatworks_rows: list[str] = []
        greatwork_yield_rows: list[str] = []
        individual_sql_blocks: list[str] = []
        text_rows: list[str] = []

        bool_default_true = {"ActionRequiresOwnedTile", "ActionEffectTileHighlighting"}
        bool_keys = {
            "ActionRequiresOwnedTile",
            "ActionRequiresUnownedTile",
            "ActionRequiresAdjacentMountain",
            "ActionRequiresAdjacentOwnedTile",
            "ActionRequiresAdjacentBarbarianUnit",
            "ActionRequiresOnOrAdjacentNaturalWonder",
            "ActionRequiresIncompleteWonder",
            "ActionRequiresIncompleteSpaceRaceProject",
            "ActionRequiresVisibleLuxury",
            "ActionRequiresNoMilitaryUnit",
            "ActionRequiresPlayerRelicSlot",
            "ActionEffectTileHighlighting",
            "ActionRequiresEnemyTerritory",
            "ActionRequiresCityStateTerritory",
            "ActionRequiresNonHostileTerritory",
            "ActionRequiresSuzerainTerritory",
            "ActionRequiresUnitCanGainExperience",
        }
        number_defaults = {
            "ActionRequiresLandMilitaryUnitWithinXTiles": 0,
            "ActionRequiresEnemyMilitaryUnitWithinXTiles": 0,
            "ActionRequiresGoldCost": 0,
            "AreaHighlightRadius": 0,
        }

        def _sql_literal(value: object) -> str:
            if isinstance(value, bool):
                return "1" if value else "0"
            if isinstance(value, int):
                return str(value)
            if value is None:
                return "NULL"
            return f"'{self._sql_escape(str(value))}'"

        for entry in great_entries:
            class_data = entry.get("class_data") if isinstance(entry.get("class_data"), dict) else {}
            unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
            is_import_locked = bool(entry.get("import_locked", False))

            class_type = str(class_data.get("GreatPersonClassType") or entry.get("type") or "").strip()
            if not class_type:
                continue
            unit_type = str(class_data.get("UnitType") or unit_data.get("UnitType") or "").strip()
            if not unit_type and not is_import_locked:
                continue

            class_name = str(class_data.get("Name") or "").strip()
            district_type = str(class_data.get("DistrictType") or "").strip()
            max_player_instances = int(class_data.get("MaxPlayerInstances", -1) or -1)
            pseudo_yield = str(class_data.get("PseudoYieldType") or "").strip()
            icon_string = str(class_data.get("IconString") or "").strip()
            action_icon = str(class_data.get("ActionIcon") or "").strip()
            timeline = 1 if bool(class_data.get("AvailableInTimeline", True)) else 0
            duplicate = 1 if bool(class_data.get("GenerateDuplicateIndividuals", False)) else 0

            if not is_import_locked:
                gp_types_rows.append(f"('{class_type}', 'KIND_GREAT_PERSON_CLASS')")

                classes_rows.append(
                    "(" + ", ".join(
                        [
                            f"'{self._sql_escape(class_type)}'",
                            f"'LOC_{class_type}_NAME'",
                            f"'{self._sql_escape(unit_type)}'",
                            f"'{self._sql_escape(district_type)}'",
                            str(max_player_instances),
                            f"'{self._sql_escape(pseudo_yield)}'" if pseudo_yield else "NULL",
                            f"'{self._sql_escape(icon_string)}'",
                            f"'{self._sql_escape(action_icon)}'",
                            str(timeline),
                            str(duplicate),
                        ]
                    ) + ")"
                )

                text_rows.append(f"('zh_Hans_CN','LOC_{class_type}_NAME','{self._sql_escape(class_name)}')")

            individuals = entry.get("individuals") if isinstance(entry.get("individuals"), list) else []
            for individual in individuals:
                if not isinstance(individual, dict):
                    continue
                individual_type = str(individual.get("GreatPersonIndividualType") or "").strip()
                if not individual_type:
                    continue
                gp_types_rows.append(f"('{self._sql_escape(individual_type)}', 'KIND_GREAT_PERSON_INDIVIDUAL')")
                mode = str(individual.get("mode") or "activation").strip().lower()
                row = {
                    "GreatPersonIndividualType": individual_type,
                    "Name": f"LOC_{individual_type}_NAME",
                    "GreatPersonClassType": class_type,
                }

                era_type = str(individual.get("EraType") or "ERA_ANCIENT")
                action_charges = int(individual.get("ActionCharges", 1) or 1)
                gender = str(individual.get("Gender") or "M")
                area_highlight_radius = int(individual.get("AreaHighlightRadius", 0) or 0)
                if era_type != "ERA_ANCIENT":
                    row["EraType"] = era_type
                if action_charges != 1:
                    row["ActionCharges"] = action_charges
                if gender != "M":
                    row["Gender"] = gender
                if area_highlight_radius != 0:
                    row["AreaHighlightRadius"] = area_highlight_radius

                if mode == "activation":
                    for key, value in individual.items():
                        if key in {
                            "mode",
                            "abbr",
                            "GreatPersonIndividualType",
                            "Name",
                            "GreatPersonClassType",
                            "EraType",
                            "ActionCharges",
                            "Gender",
                            "AreaHighlightRadius",
                        }:
                            continue
                        if value is None or value == "":
                            continue
                        if key in bool_keys:
                            normalized_bool = 1 if bool(value) else 0
                            default_bool = 1 if key in bool_default_true else 0
                            if normalized_bool != default_bool:
                                row[key] = normalized_bool
                            continue
                        if key in number_defaults:
                            try:
                                normalized_num = int(value)
                            except (TypeError, ValueError):
                                normalized_num = number_defaults[key]
                            if normalized_num != number_defaults[key]:
                                row[key] = normalized_num
                            continue
                        text_value = str(value).strip()
                        if text_value:
                            if key == "ActionEffectTextOverride":
                                effect_tag = f"LOC_{individual_type}_ACTICE"
                                row[key] = effect_tag
                                text_rows.append(
                                    f"('zh_Hans_CN','{effect_tag}','{self._sql_escape(text_value)}')"
                                )
                            else:
                                row[key] = text_value

                elif mode == "greatwork":
                    row["ActionCharges"] = 0
                    greatworks = individual.get("great_works") if isinstance(individual.get("great_works"), list) else []
                    for greatwork in greatworks:
                        if not isinstance(greatwork, dict):
                            continue
                        greatwork_type = str(greatwork.get("GreatWorkType") or "").strip()
                        if not greatwork_type:
                            continue
                        greatwork_types_rows.append(f"('{self._sql_escape(greatwork_type)}', 'KIND_GREATWORK')")

                        greatwork_object_type = str(greatwork.get("GreatWorkObjectType") or "").strip()
                        tourism_value = int(greatwork.get("Tourism", 1) or 1)
                        audio_value = str(greatwork.get("Audio") or "").strip()
                        image_value = str(greatwork.get("Image") or "").strip()
                        era_value = str(greatwork.get("EraType") or "").strip()
                        name_text = str(greatwork.get("Name") or "").strip()
                        quote_text = str(greatwork.get("Quote") or "").strip()

                        name_tag = f"LOC_{greatwork_type}_NAME"
                        quote_tag = f"LOC_{greatwork_type}_QUOTE"

                        greatworks_rows.append(
                            "(" + ", ".join(
                                [
                                    f"'{self._sql_escape(greatwork_type)}'",
                                    f"'{self._sql_escape(greatwork_object_type)}'",
                                    f"'{self._sql_escape(individual_type)}'",
                                    f"'{self._sql_escape(name_tag)}'",
                                    f"'{self._sql_escape(audio_value)}'" if audio_value else "NULL",
                                    f"'{self._sql_escape(image_value)}'" if image_value else "NULL",
                                    f"'{self._sql_escape(quote_tag)}'",
                                    str(tourism_value),
                                    f"'{self._sql_escape(era_value)}'" if era_value else "NULL",
                                ]
                            ) + ")"
                        )
                        text_rows.append(f"('zh_Hans_CN','{name_tag}','{self._sql_escape(name_text)}')")
                        text_rows.append(f"('zh_Hans_CN','{quote_tag}','{self._sql_escape(quote_text)}')")

                        yield_changes = greatwork.get("yield_changes") if isinstance(greatwork.get("yield_changes"), list) else []
                        for yield_row in yield_changes:
                            if not isinstance(yield_row, dict):
                                continue
                            yield_type = str(yield_row.get("YieldType") or "").strip()
                            if not yield_type:
                                continue
                            try:
                                yield_change = int(yield_row.get("YieldChange", 0) or 0)
                            except (TypeError, ValueError):
                                yield_change = 0
                            greatwork_yield_rows.append(
                                "(" + ", ".join(
                                    [
                                        f"'{self._sql_escape(greatwork_type)}'",
                                        f"'{self._sql_escape(yield_type)}'",
                                        str(yield_change),
                                    ]
                                ) + ")"
                            )

                columns = list(row.keys())
                values = [_sql_literal(row[col]) for col in columns]
                individual_sql_blocks.append(
                    "\n".join(
                        [
                            "-- GreatPersonIndividuals",
                            f"INSERT INTO GreatPersonIndividuals ({', '.join(columns)})",
                            f"VALUES ({', '.join(values)});",
                        ]
                    )
                )

                text_rows.append(f"('zh_Hans_CN','LOC_{individual_type}_NAME','{self._sql_escape(str(individual.get('Name') or ''))}')")

        gp_types_rows = self._deduplicate_rows(gp_types_rows)
        greatwork_types_rows = self._deduplicate_rows(greatwork_types_rows)
        classes_rows = self._deduplicate_rows(classes_rows)
        greatworks_rows = self._deduplicate_rows(greatworks_rows)
        greatwork_yield_rows = self._deduplicate_rows(greatwork_yield_rows)
        text_rows = self._deduplicate_rows(text_rows)

        sql_blocks: list[str] = []
        if gp_types_rows:
            sql_blocks.append(self._build_insert_block("Types", "Types", ["Type", "Kind"], gp_types_rows))
        if classes_rows:
            sql_blocks.append(
                self._build_insert_block(
                    "GreatPersonClasses",
                    "GreatPersonClasses",
                    [
                        "GreatPersonClassType",
                        "Name",
                        "UnitType",
                        "DistrictType",
                        "MaxPlayerInstances",
                        "PseudoYieldType",
                        "IconString",
                        "ActionIcon",
                        "AvailableInTimeline",
                        "GenerateDuplicateIndividuals",
                    ],
                    classes_rows,
                )
            )
        sql_blocks.extend(individual_sql_blocks)

        greatwork_sql_blocks: list[str] = []
        if greatwork_types_rows:
            greatwork_sql_blocks.append(
                self._build_insert_block("Types", "Types", ["Type", "Kind"], greatwork_types_rows)
            )
        if greatworks_rows:
            greatwork_sql_blocks.append(
                self._build_insert_block(
                    "GreatWorks",
                    "GreatWorks",
                    [
                        "GreatWorkType",
                        "GreatWorkObjectType",
                        "GreatPersonIndividualType",
                        "Name",
                        "Audio",
                        "Image",
                        "Quote",
                        "Tourism",
                        "EraType",
                    ],
                    greatworks_rows,
                )
            )
        if greatwork_yield_rows:
            greatwork_sql_blocks.append(
                self._build_insert_block(
                    "GreatWork_YieldChanges",
                    "GreatWork_YieldChanges",
                    ["GreatWorkType", "YieldType", "YieldChange"],
                    greatwork_yield_rows,
                )
            )

        data_sql = "\n".join([block for block in sql_blocks if block and block.strip()]).rstrip()
        data_sql = re.sub(r";\n(-- )", r";\n\n\1", data_sql)
        greatwork_sql = "\n".join([block for block in greatwork_sql_blocks if block and block.strip()]).rstrip()
        greatwork_sql = re.sub(r";\n(-- )", r";\n\n\1", greatwork_sql)
        if not greatwork_sql:
            greatwork_sql = "-- GreatWorks.sql\n-- 暂无巨作数据"

        text_sql = "\n".join(
            [
                "-- Text.sql",
                "",
                self._build_insert_block("LocalizedText", "LocalizedText", ["Language", "Tag", "Text"], text_rows),
            ]
        ).rstrip()
        return data_sql, greatwork_sql, text_sql

    def _build_great_people_sql_pair(self) -> tuple[str, str]:
        great_people_sql, _greatwork_sql, text_sql = self._build_great_people_sql_bundle()
        return great_people_sql, text_sql

    @staticmethod
    def _split_sql_tuples(values_blob: str) -> list[str]:
        tuples: list[str] = []
        in_quote = False
        depth = 0
        start = -1
        i = 0
        while i < len(values_blob):
            ch = values_blob[i]
            if ch == "'":
                if in_quote and i + 1 < len(values_blob) and values_blob[i + 1] == "'":
                    i += 2
                    continue
                in_quote = not in_quote
                i += 1
                continue
            if not in_quote:
                if ch == "(":
                    if depth == 0:
                        start = i + 1
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and start >= 0:
                        tuples.append(values_blob[start:i])
                        start = -1
            i += 1
        return tuples

    @staticmethod
    def _split_sql_fields(tuple_text: str) -> list[str]:
        fields: list[str] = []
        in_quote = False
        depth = 0
        start = 0
        i = 0
        while i < len(tuple_text):
            ch = tuple_text[i]
            if ch == "'":
                if in_quote and i + 1 < len(tuple_text) and tuple_text[i + 1] == "'":
                    i += 2
                    continue
                in_quote = not in_quote
                i += 1
                continue
            if not in_quote:
                if ch == "(":
                    depth += 1
                elif ch == ")" and depth > 0:
                    depth -= 1
                elif ch == "," and depth == 0:
                    fields.append(tuple_text[start:i].strip())
                    start = i + 1
            i += 1
        tail = tuple_text[start:].strip()
        if tail:
            fields.append(tail)
        return fields

    @staticmethod
    def _decode_sql_value(token: str) -> str:
        text = token.strip()
        if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
            return text[1:-1].replace("''", "'")
        if text.upper() == "NULL":
            return ""
        return text

    def _resolve_preview_game_db_path(self) -> Path | None:
        settings = load_settings()
        db_path = Path(str(settings.game_db_path or "")).expanduser()
        if db_path.exists():
            return db_path
        if DEFAULT_GAME_DB.exists():
            return DEFAULT_GAME_DB
        return None

    def _xml_preview_boolean_columns(self, table_name: str) -> set[str]:
        # 缓存按“当前 DB 路径 + 表名”区分，避免用户切换数据库后命中旧缓存。
        db_path = self._resolve_preview_game_db_path()
        cache: dict[str, set[str]] = getattr(self, "_xml_preview_bool_cols_cache", {})
        last_db = getattr(self, "_xml_preview_bool_cols_db", None)
        if last_db != db_path:
            cache = {}
            setattr(self, "_xml_preview_bool_cols_cache", cache)
            setattr(self, "_xml_preview_bool_cols_db", db_path)

        if table_name in cache:
            return cache[table_name]

        # 安全：表名只允许字母/数字/下划线。
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name or ""):
            cache[table_name] = set()
            return cache[table_name]
        if db_path is None:
            cache[table_name] = set()
            return cache[table_name]

        bool_cols: set[str] = set()
        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            cache[table_name] = set()
            return cache[table_name]

        try:
            try:
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                rows = cursor.fetchall()
            except sqlite3.Error:
                rows = []

            for row in rows:
                # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
                if len(row) < 3:
                    continue
                name = str(row[1] or "").strip()
                decl_type = str(row[2] or "").strip().upper()
                if name and "BOOLEAN" in decl_type:
                    bool_cols.add(name)
        finally:
            try:
                conn.close()
            except Exception:
                pass

        cache[table_name] = bool_cols
        return bool_cols

    def _normalize_sql_value_for_xml(self, table_name: str, col_name: str, value: str) -> str:
        # 把 SQL 里的 0/1 转成 XML 惯用的 true/false（小写）。
        if not value:
            return value

        bool_cols = self._xml_preview_boolean_columns(table_name)
        if col_name in bool_cols:
            lowered = value.strip().lower()
            if lowered in {"true", "false"}:
                return lowered
            if lowered in {"0", "1"}:
                return "true" if lowered == "1" else "false"
        return value

    @staticmethod
    def _should_skip_xml_attr(table_name: str, col_name: str, value: str) -> bool:
        if table_name == "LocalizedText" and col_name == "Text":
            return False
        if value == "":
            return True
        default_zero_columns = {
            "UnitAbilities": {"Inactive", "Permanent"},
        }
        if col_name in default_zero_columns.get(table_name, set()):
            return value in {"0", "false"}
        return False

    def _sql_preview_to_xml(self, sql_text: str) -> str:
        root = ElementTree.Element("GameInfo")
        table_map: dict[str, ElementTree.Element] = {}

        pattern = re.compile(
            r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*VALUES\s*(.*?);",
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(sql_text):
            table_name = match.group(1).strip()
            columns = [col.strip() for col in match.group(2).split(",") if col.strip()]
            values_blob = match.group(3)
            if not table_name or not columns:
                continue

            table_el = table_map.get(table_name)
            if table_el is None:
                table_el = ElementTree.SubElement(root, table_name)
                table_map[table_name] = table_el

            for tuple_text in self._split_sql_tuples(values_blob):
                fields = self._split_sql_fields(tuple_text)
                if not fields:
                    continue
                row_el = ElementTree.SubElement(table_el, "Row")
                for col_index, col_name in enumerate(columns):
                    raw_value = self._decode_sql_value(fields[col_index]) if col_index < len(fields) else ""
                    value = self._normalize_sql_value_for_xml(table_name, col_name, raw_value)
                    if self._should_skip_xml_attr(table_name, col_name, value):
                        continue
                    row_el.set(col_name, value)

        raw = ElementTree.tostring(root, encoding="utf-8")
        return minidom.parseString(raw).toprettyxml(indent="  ")

    def _next_entry_display_name(self, section: str) -> str:
        entries = self._project.sections.get(section, [])
        count = len(entries) + 1 if isinstance(entries, list) else 1
        if section == "文明":
            return f"新文明{count}"
        if section == "领袖":
            return f"新领袖{count}"
        return f"新{section}{count}"

    def _list_bindable_entries(self, section: str) -> list[dict[str, object]]:
        entries = self._project.sections.get(section)
        if not isinstance(entries, list):
            return []

        def _enabled_trait_from_entry(entry: dict[str, object]) -> str:
            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            trait_type = str(table_data.get("TraitType") or "").strip()
            return trait_type

        output: list[dict[str, object]] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            name = self._resolve_entry_name(entry, index)
            if section == "总督":
                type_name = str(entry.get("GovernorType") or entry.get("type") or "").strip()
            else:
                type_name = str(entry.get("type") or "").strip()
            if not type_name:
                continue

            if section in {"区域", "建筑", "单位", "改良设施"}:
                if not _enabled_trait_from_entry(entry):
                    continue
            elif section == "总督":
                governor_trait = str(entry.get("TraitType") or entry.get("trait_type") or "").strip()
                if not bool(entry.get("new_trait_type", False)) or not governor_trait:
                    continue
            elif section == "伟人":
                unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
                trait_type = str(unit_data.get("TraitType") or "").strip()
                if not trait_type:
                    continue

            output.append(
                {
                    "index": index,
                    "name": name,
                    "type": type_name,
                }
            )
        return output

    def _list_civilizations_for_leader(self) -> list[dict[str, object]]:
        entries = self._project.sections.get("文明")
        if not isinstance(entries, list):
            return []
        output: list[dict[str, object]] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            type_name = str(entry.get("type") or "").strip()
            if not type_name:
                continue
            name = str(entry.get("civilization_name") or entry.get("name") or self._resolve_entry_name(entry, index)).strip()
            output.append(
                {
                    "type": type_name,
                    "name": name,
                    "trait_bindings": list(entry.get("trait_bindings", []))
                    if isinstance(entry.get("trait_bindings"), list)
                    else [],
                }
            )
        return output

    def _handle_add_group_entry(self, section: str) -> None:
        entries = self._project.sections.get(section)
        if not isinstance(entries, list):
            entries = []
            self._project.sections[section] = entries

        new_name = self._next_entry_display_name(section)
        payload: dict[str, object] = {"name": new_name}
        if section == "文明":
            payload.update(
                {
                    "abbr": "",
                    "civilization_name": "",
                    "civilization_description": "",
                    "civilization_adjective": "",
                    "description_suffix": "帝国",
                    "level": "CIVILIZATION_LEVEL_FULL_CIV",
                    "ethnicity": "ETHNICITY_ASIAN",
                    "city_name_depth": 10,
                    "trait_name": "",
                    "trait_description": "",
                    "trait_bindings": [],
                    "icon_image_name": "",
                    "images": {},
                    "city_info": {},
                    "citizen_info": {},
                    "start_bias": {},
                }
            )
        elif section == "领袖":
            payload.update(
                {
                    "abbr": "",
                    "leader_name": "",
                    "sex": "Male",
                    "capital_name": "",
                    "civilization_type": "",
                    "civilization_name": "",
                    "leader_text": "",
                    "leader_quote": "",
                    "ability_name": "",
                    "ability_description": "",
                    "select_sort_index": 0,
                    "add_diplo_background_curtain": False,
                    "icon_image_name": "",
                    "bindings": [],
                    "diplomacy": [],
                    "images": {},
                }
            )
        elif section == "区域":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Districts",
                    "table_data": {},
                    "images": {},
                }
            )
        elif section == "建筑":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Buildings",
                    "table_data": {},
                    "images": {},
                }
            )
        elif section == "单位":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Units",
                    "table_data": {},
                    "images": {},
                }
            )
        elif section == "改良设施":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Improvements",
                    "table_data": {},
                    "images": {},
                }
            )
        elif section == "政策卡":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Policies",
                    "table_data": {},
                    "policies_xp1": {},
                    "policy_government_exclusive": {},
                    "subtables": {
                        "Policies_XP1": {},
                        "Policy_GovernmentExclusives_XP2": {},
                    },
                    "images": {},
                }
            )
        elif section == "项目":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Projects",
                    "table_data": {},
                    "projects_mode": {},
                    "projects_xp1": {},
                    "projects_xp2": {},
                    "project_building_costs": [],
                    "project_great_person_points": [],
                    "project_resource_costs": [],
                    "project_yield_conversions": [],
                    "project_prereqs": [],
                    "subtables": {
                        "Projects_MODE": {},
                        "Projects_XP1": {},
                        "Projects_XP2": {},
                        "Project_BuildingCosts": [],
                        "Project_GreatPersonPoints": [],
                        "Project_ResourceCosts": [],
                        "Project_YieldConversions": [],
                        "ProjectPrereqs": [],
                    },
                    "images": {},
                }
            )
        elif section == "信仰":
            payload.update(
                {
                    "abbr": "",
                    "table_name": "Beliefs",
                    "table_data": {},
                    "images": {},
                }
            )
        elif section == "伟人":
            payload.update(
                {
                    "name": "",
                    "abbr": "",
                    "type": "",
                    "import_locked": False,
                    "class_data": {
                        "GreatPersonClassType": "",
                        "Name": "",
                        "UnitType": "",
                        "DistrictType": "",
                        "MaxPlayerInstances": -1,
                        "PseudoYieldType": "",
                        "IconString": "",
                        "ActionIcon": "",
                        "AvailableInTimeline": 1,
                        "GenerateDuplicateIndividuals": 0,
                    },
                    "unit_data": {
                        "UnitType": "",
                        "BaseSightRange": 4,
                        "BaseMoves": 5,
                        "FormationClass": "FORMATION_CLASS_CIVILIAN",
                        "Domain": "DOMAIN_LAND",
                        "CanRetreatWhenCaptured": 0,
                        "CanCapture": 0,
                        "Cost": 1,
                        "ZoneOfControl": 0,
                        "FoundReligion": 0,
                        "CanTrain": 0,
                        "TraitType": "",
                        "Name": "",
                        "Description": "",
                    },
                    "individuals": [],
                }
            )

        entries.append(payload)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item(section, new_index)

    def _handle_import_group_entry(self, section: str) -> None:
        if section == "区域":
            self._handle_import_district_entry()
            return
        if section == "建筑":
            self._handle_import_building_entry()
            return
        if section == "单位":
            self._handle_import_unit_entry()
            return
        if section == "改良设施":
            self._handle_import_improvement_entry()
            return
        if section == "伟人":
            self._handle_import_great_people_entry()
            return
        QMessageBox.information(self, "导入", f"{section} 当前不支持数据库导入，请使用“新增”手动创建条目。")

    def _handle_delete_section_item(self, section: str, index: int) -> None:
        entries = self._project.sections.get(section)
        if not isinstance(entries, list):
            return
        if index < 0 or index >= len(entries):
            return

        entry_name = self._resolve_entry_name(entries[index], index)
        answer = QMessageBox.question(
            self,
            "删除对象",
            f"确认删除“{entry_name}”吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        del entries[index]
        self._modifier_workspace.sync_owners_from_sections(self._project.sections)
        self._art_workspace.refresh_from_sections(self._project.sections)

        self._rebuild_tree()
        if entries:
            next_index = min(index, len(entries) - 1)
            self._select_section_item(section, next_index)
        else:
            self._select_section_group(section)

    def _handle_import_great_people_entry(self) -> None:
        db_path = Path(load_settings().game_db_path)
        if not db_path.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            QMessageBox.warning(self, "导入伟人类型", "未找到可用游戏数据库。")
            return

        rows: list[dict[str, object]] = []
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT GreatPersonClassType, Name, UnitType, DistrictType
                    FROM GreatPersonClasses
                    ORDER BY GreatPersonClassType
                    """
                )
                for class_type, name, unit_type, district_type in cursor.fetchall():
                    rows.append(
                        {
                            "type": str(class_type or ""),
                            "name": self._resolve_loc_or_unknown(name),
                            "promotion_class": str(district_type or ""),
                            "cost": 0,
                            "domain": str(unit_type or ""),
                        }
                    )
        except sqlite3.Error:
            rows = []

        if not rows:
            QMessageBox.warning(self, "导入伟人类型", "未读取到伟人类型数据。")
            return

        dialog = _UnitSearchDialog(rows, self)
        dialog.setWindowTitle("选择伟人类型")
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        class_type = dialog.selected_type()
        if not class_type:
            return

        payload = self._import_great_people_payload_from_db(class_type)
        if payload is None:
            QMessageBox.warning(self, "导入伟人类型", f"未找到伟人类型数据：{class_type}")
            return

        entries = self._project.sections.setdefault("伟人", [])
        if not isinstance(entries, list):
            entries = []
            self._project.sections["伟人"] = entries
        entries.append(payload)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item("伟人", new_index)

    def _handle_import_district_entry(self) -> None:
        rows = _build_district_hierarchy()
        if not rows:
            QMessageBox.warning(self, "导入区域", "未能从数据库读取区域列表。")
            return

        dialog = _DistrictSearchDialog(rows, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        district_type = dialog.selected_type()
        if not district_type:
            return

        payload = self._import_district_payload_from_db(district_type)
        if payload is None:
            QMessageBox.warning(self, "导入区域", f"未找到区域数据：{district_type}")
            return

        entries = self._project.sections.setdefault("区域", [])
        if not isinstance(entries, list):
            entries = []
            self._project.sections["区域"] = entries
        entries.append(payload)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item("区域", new_index)

    def _handle_import_building_entry(self) -> None:
        rows = _build_building_entries(include_wonders=True)
        if not rows:
            QMessageBox.warning(self, "导入建筑", "未能从数据库读取建筑列表。")
            return

        dialog = _BuildingSearchByDistrictDialog(rows, self, include_wonders=True)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        building_type = dialog.selected_type()
        if not building_type:
            return

        payload = self._import_building_payload_from_db(building_type)
        if payload is None:
            QMessageBox.warning(self, "导入建筑", f"未找到建筑数据：{building_type}")
            return

        entries = self._project.sections.setdefault("建筑", [])
        if not isinstance(entries, list):
            entries = []
            self._project.sections["建筑"] = entries
        entries.append(payload)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item("建筑", new_index)

    def _handle_import_unit_entry(self) -> None:
        rows = _build_unit_entries()
        if not rows:
            QMessageBox.warning(self, "导入单位", "未能从数据库读取单位列表。")
            return

        dialog = _UnitSearchDialog(rows, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        unit_type = dialog.selected_type()
        if not unit_type:
            return

        payload = self._import_unit_payload_from_db(unit_type)
        if payload is None:
            QMessageBox.warning(self, "导入单位", f"未找到单位数据：{unit_type}")
            return

        entries = self._project.sections.setdefault("单位", [])
        if not isinstance(entries, list):
            entries = []
            self._project.sections["单位"] = entries
        entries.append(payload)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item("单位", new_index)

    def _handle_import_improvement_entry(self) -> None:
        rows = _build_improvement_entries()
        if not rows:
            QMessageBox.warning(self, "导入改良设施", "未能从数据库读取改良设施列表。")
            return

        dialog = _ImprovementSearchDialog(rows, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        improvement_type = dialog.selected_type()
        if not improvement_type:
            return

        payload = self._import_improvement_payload_from_db(improvement_type)
        if payload is None:
            QMessageBox.warning(self, "导入改良设施", f"未找到改良设施数据：{improvement_type}")
            return

        entries = self._project.sections.setdefault("改良设施", [])
        if not isinstance(entries, list):
            entries = []
            self._project.sections["改良设施"] = entries
        entries.append(payload)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item("改良设施", new_index)

    @staticmethod
    def _load_db_row_dicts(conn: sqlite3.Connection, table: str, key: str, value: str) -> list[dict[str, object]]:
        query = f"SELECT * FROM {table} WHERE {key} = ?"
        try:
            cursor = conn.execute(query, (value,))
            columns = [str(item[0]) for item in cursor.description or []]
            rows = cursor.fetchall()
        except sqlite3.Error:
            return []
        return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def _coerce_db_value(value: object | None) -> object:
        return "" if value is None else value

    @staticmethod
    def _resolve_loc_or_unknown(value: object | None) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.upper().startswith("LOC_") or "{LOC_" in text.upper():
            return resolve_chinese_text_or_unknown(text, "未知")
        return text

    def _import_district_payload_from_db(self, district_type: str) -> dict[str, object] | None:
        settings = load_settings()
        db_path = Path(str(settings.game_db_path or "")).expanduser()
        if not db_path.exists() and DEFAULT_GAME_DB.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            return None

        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return None

        try:
            district_rows = self._load_db_row_dicts(conn, "Districts", "DistrictType", district_type)
            if not district_rows:
                return None
            district_row = district_rows[0]

            def _pick_text(row: dict[str, object], keys: list[str]) -> str:
                lowered = {str(k).lower(): k for k in row.keys()}
                for key in keys:
                    real_key = lowered.get(str(key).lower())
                    if real_key is None:
                        continue
                    value = row.get(real_key)
                    if value is None:
                        continue
                    text = str(value).strip()
                    if text:
                        return text
                return ""

            schema = build_districts_main_schema()
            table_data: dict[str, object] = {}
            for field in schema.fields:
                if field.key == "PrereqTech":
                    raw = _pick_text(district_row, ["PrereqTech", "PrerequisiteTech", "TechnologyType"])
                elif field.key == "PrereqCivic":
                    raw = _pick_text(district_row, ["PrereqCivic", "PrerequisiteCivic", "CivicType"])
                else:
                    raw = district_row.get(field.key)
                value = self._coerce_db_value(raw)
                if field.key in {"Name", "Description"}:
                    table_data[field.key] = self._resolve_loc_or_unknown(value)
                elif field.key == "TraitType":
                    table_data[field.key] = "" if raw is None else str(raw)
                else:
                    table_data[field.key] = value

            xp2_rows = self._load_db_row_dicts(conn, "Districts_XP2", "DistrictType", district_type)
            xp2_row = xp2_rows[0] if xp2_rows else {}
            districts_xp2 = {
                "DistrictType": district_type,
                "OnePerRiver": int(xp2_row.get("OnePerRiver", 0) or 0),
                "PreventsFloods": int(xp2_row.get("PreventsFloods", 0) or 0),
                "PreventsDrought": int(xp2_row.get("PreventsDrought", 0) or 0),
                "Canal": int(xp2_row.get("Canal", 0) or 0),
                "AttackRange": int(xp2_row.get("AttackRange", 0) or 0),
            }

            def _rows(table: str, key: str = "DistrictType") -> list[dict[str, object]]:
                return self._load_db_row_dicts(conn, table, key, district_type)

            district_citizen_yield_changes = [
                {
                    "DistrictType": district_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "YieldChange": int(row.get("YieldChange", 0) or 0),
                }
                for row in _rows("District_CitizenYieldChanges")
            ]
            district_required_features = [
                {
                    "DistrictType": district_type,
                    "FeatureType": str(row.get("FeatureType") or ""),
                }
                for row in _rows("District_RequiredFeatures")
            ]
            district_trade_route_yields = [
                {
                    "DistrictType": district_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "YieldChangeAsOrigin": float(row.get("YieldChangeAsOrigin", 0.0) or 0.0),
                    "YieldChangeAsDomesticDestination": float(row.get("YieldChangeAsDomesticDestination", 0.0) or 0.0),
                    "YieldChangeAsInternationalDestination": float(row.get("YieldChangeAsInternationalDestination", 0.0) or 0.0),
                }
                for row in _rows("District_TradeRouteYields")
            ]
            district_valid_terrains = [
                {
                    "DistrictType": district_type,
                    "TerrainType": str(row.get("TerrainType") or ""),
                }
                for row in _rows("District_ValidTerrains")
            ]
            district_great_person_points = [
                {
                    "DistrictType": district_type,
                    "GreatPersonClassType": str(row.get("GreatPersonClassType") or ""),
                    "PointsPerTurn": int(row.get("PointsPerTurn", 0) or 0),
                }
                for row in _rows("District_GreatPersonPoints")
            ]

            replaces_rows = self._load_db_row_dicts(conn, "DistrictReplaces", "CivUniqueDistrictType", district_type)
            district_replaces = {
                "CivUniqueDistrictType": district_type,
                "ReplacesDistrictType": str((replaces_rows[0] if replaces_rows else {}).get("ReplacesDistrictType") or ""),
            }

            district_adjacencies_raw = _rows("District_Adjacencies")
            adjacencies = [
                {
                    "mode": "existing",
                    "id": str(row.get("YieldChangeId") or ""),
                }
                for row in district_adjacencies_raw
                if str(row.get("YieldChangeId") or "").strip()
            ]

            payload: dict[str, object] = {
                "name": self._resolve_loc_or_unknown(district_row.get("Name")) or district_type,
                "type": district_type,
                "abbr": district_type[9:] if district_type.startswith("DISTRICT_") else district_type,
                "table_name": "Districts",
                "table_data": table_data,
                "images": {},
                "districts_xp2": districts_xp2,
                "district_great_person_points": district_great_person_points,
                "district_citizen_yield_changes": district_citizen_yield_changes,
                "district_required_features": district_required_features,
                "district_trade_route_yields": district_trade_route_yields,
                "district_valid_terrains": district_valid_terrains,
                "district_replaces": district_replaces,
                "adjacencies": adjacencies,
                "subtables": {
                    "Districts_XP2": districts_xp2,
                    "District_GreatPersonPoints": district_great_person_points,
                    "District_CitizenYieldChanges": district_citizen_yield_changes,
                    "District_RequiredFeatures": district_required_features,
                    "District_TradeRouteYields": district_trade_route_yields,
                    "District_ValidTerrains": district_valid_terrains,
                    "DistrictReplaces": district_replaces,
                    "District_Adjacencies": adjacencies,
                },
            }
            return payload
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def _import_building_payload_from_db(self, building_type: str) -> dict[str, object] | None:
        settings = load_settings()
        db_path = Path(str(settings.game_db_path or "")).expanduser()
        if not db_path.exists() and DEFAULT_GAME_DB.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            return None

        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return None

        try:
            building_rows = self._load_db_row_dicts(conn, "Buildings", "BuildingType", building_type)
            if not building_rows:
                return None
            building_row = building_rows[0]

            schema = build_buildings_main_schema()
            table_data: dict[str, object] = {}
            for field in schema.fields:
                raw = building_row.get(field.key)
                value = self._coerce_db_value(raw)
                if field.key in {"Name", "Description", "Quote"}:
                    table_data[field.key] = self._resolve_loc_or_unknown(value)
                elif field.key == "TraitType":
                    table_data[field.key] = "" if raw is None else str(raw)
                else:
                    table_data[field.key] = value

            def _rows(table: str, key: str = "BuildingType") -> list[dict[str, object]]:
                return self._load_db_row_dicts(conn, table, key, building_type)

            xp2_rows = _rows("Buildings_XP2")
            xp2_row = xp2_rows[0] if xp2_rows else {}
            buildings_xp2 = {
                "BuildingType": building_type,
                "RequiredPower": int(xp2_row.get("RequiredPower", 0) or 0),
                "ResourceTypeConvertedToPower": str(xp2_row.get("ResourceTypeConvertedToPower") or ""),
                "PreventsFloods": int(xp2_row.get("PreventsFloods", 0) or 0),
                "PreventsDrought": int(xp2_row.get("PreventsDrought", 0) or 0),
                "BlocksCoastalFlooding": int(xp2_row.get("BlocksCoastalFlooding", 0) or 0),
                "CostMultiplierPerTile": int(xp2_row.get("CostMultiplierPerTile", 0) or 0),
                "CostMultiplierPerSeaLevel": int(xp2_row.get("CostMultiplierPerSeaLevel", 0) or 0),
                "Bridge": int(xp2_row.get("Bridge", 0) or 0),
                "CanalWonder": int(xp2_row.get("CanalWonder", 0) or 0),
                "EntertainmentBonusWithPower": int(xp2_row.get("EntertainmentBonusWithPower", 0) or 0),
                "NuclearReactor": int(xp2_row.get("NuclearReactor", 0) or 0),
                "Pillage": int(xp2_row.get("Pillage", 1) or 1),
            }

            replaces_rows = self._load_db_row_dicts(conn, "BuildingReplaces", "CivUniqueBuildingType", building_type)
            building_replaces = {
                "CivUniqueBuildingType": building_type,
                "ReplacesBuildingType": str((replaces_rows[0] if replaces_rows else {}).get("ReplacesBuildingType") or ""),
            }

            building_prereqs = [
                {"BuildingType": building_type, "PrereqBuilding": str(row.get("PrereqBuilding") or "")}
                for row in _rows("BuildingPrereqs", "Building")
            ]
            building_citizen_yield_changes = [
                {
                    "BuildingType": building_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "YieldChange": int(row.get("YieldChange", 0) or 0),
                }
                for row in _rows("Building_CitizenYieldChanges")
            ]
            building_great_person_points = [
                {
                    "BuildingType": building_type,
                    "GreatPersonClassType": str(row.get("GreatPersonClassType") or ""),
                    "PointsPerTurn": int(row.get("PointsPerTurn", 0) or 0),
                }
                for row in _rows("Building_GreatPersonPoints")
            ]
            building_required_features = [
                {
                    "BuildingType": building_type,
                    "FeatureType": str(row.get("FeatureType") or ""),
                }
                for row in _rows("Building_RequiredFeatures")
            ]
            building_tourism_bombs_xp2 = [
                {
                    "BuildingType": building_type,
                    "TourismBombValue": int(row.get("TourismBombValue", 0) or 0),
                }
                for row in _rows("Building_TourismBombs_XP2")
            ]
            building_resource_costs = [
                {
                    "BuildingType": building_type,
                    "ResourceType": str(row.get("ResourceType") or ""),
                    "StartProductionCost": int(row.get("StartProductionCost", 0) or 0),
                    "PerTurnMaintenanceCost": int(row.get("PerTurnMaintenanceCost", 0) or 0),
                }
                for row in _rows("Building_ResourceCosts")
            ]
            building_valid_features = [
                {
                    "BuildingType": building_type,
                    "FeatureType": str(row.get("FeatureType") or ""),
                }
                for row in _rows("Building_ValidFeatures")
            ]
            building_valid_terrains = [
                {
                    "BuildingType": building_type,
                    "TerrainType": str(row.get("TerrainType") or ""),
                }
                for row in _rows("Building_ValidTerrains")
            ]
            building_yield_changes = [
                {
                    "BuildingType": building_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "YieldChange": int(row.get("YieldChange", 0) or 0),
                }
                for row in _rows("Building_YieldChanges")
            ]
            building_yield_changes_bonus_with_power = [
                {
                    "BuildingType": building_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "YieldChange": int(row.get("YieldChange", 0) or 0),
                }
                for row in _rows("Building_YieldChangesBonusWithPower")
            ]
            building_yield_district_copies = [
                {
                    "BuildingType": building_type,
                    "OldYieldType": str(row.get("OldYieldType") or "NO_YIELD"),
                    "NewYieldType": str(row.get("NewYieldType") or "NO_YIELD"),
                }
                for row in _rows("Building_YieldDistrictCopies")
            ]
            building_yields_per_era = [
                {
                    "BuildingType": building_type,
                    "YieldType": str(row.get("YieldType") or "NO_YIELD"),
                    "YieldChange": int(row.get("YieldChange", 0) or 0),
                }
                for row in _rows("Building_YieldsPerEra")
            ]
            condition_rows = _rows("BuildingConditions")
            condition_row = condition_rows[0] if condition_rows else {}
            building_conditions = {
                "BuildingType": building_type,
                "UnlocksFromEffect": int(condition_row.get("UnlocksFromEffect", 0) or 0),
            }
            building_build_charge_productions = [
                {
                    "BuildingType": building_type,
                    "UnitType": str(row.get("UnitType") or ""),
                    "PercentProductionPerCharge": int(row.get("PercentProductionPerCharge", 0) or 0),
                }
                for row in _rows("Building_BuildChargeProductions")
            ]
            building_greatworks = [
                {
                    "BuildingType": building_type,
                    "GreatWorkSlotType": str(row.get("GreatWorkSlotType") or ""),
                    "NumSlots": int(row.get("NumSlots", 1) or 1),
                    "ThemingUniquePerson": int(row.get("ThemingUniquePerson", 0) or 0),
                    "ThemingSameObjectType": int(row.get("ThemingSameObjectType", 0) or 0),
                    "ThemingUniqueCivs": int(row.get("ThemingUniqueCivs", 0) or 0),
                    "ThemingSameEras": int(row.get("ThemingSameEras", 0) or 0),
                    "ThemingYieldMultiplier": int(row.get("ThemingYieldMultiplier", 0) or 0),
                    "ThemingTourismMultiplier": int(row.get("ThemingTourismMultiplier", 0) or 0),
                    "NonUniquePersonYield": int(row.get("NonUniquePersonYield", 0) or 0),
                    "NonUniquePersonTourism": int(row.get("NonUniquePersonTourism", 0) or 0),
                    "ThemingBonusDescription": self._resolve_loc_or_unknown(row.get("ThemingBonusDescription")),
                }
                for row in _rows("Building_GreatWorks")
            ]

            payload: dict[str, object] = {
                "name": self._resolve_loc_or_unknown(building_row.get("Name")) or building_type,
                "type": building_type,
                "abbr": building_type[9:] if building_type.startswith("BUILDING_") else building_type,
                "table_name": "Buildings",
                "table_data": table_data,
                "images": {},
                "buildings_xp2": buildings_xp2,
                "building_replaces": building_replaces,
                "building_prereqs": building_prereqs,
                "building_citizen_yield_changes": building_citizen_yield_changes,
                "building_great_person_points": building_great_person_points,
                "building_required_features": building_required_features,
                "building_tourism_bombs_xp2": building_tourism_bombs_xp2,
                "building_resource_costs": building_resource_costs,
                "building_valid_features": building_valid_features,
                "building_valid_terrains": building_valid_terrains,
                "building_yield_changes": building_yield_changes,
                "building_yield_changes_bonus_with_power": building_yield_changes_bonus_with_power,
                "building_yield_district_copies": building_yield_district_copies,
                "building_yields_per_era": building_yields_per_era,
                "building_conditions": building_conditions,
                "building_build_charge_productions": building_build_charge_productions,
                "building_greatworks": building_greatworks,
                "subtables": {
                    "Buildings_XP2": buildings_xp2,
                    "BuildingReplaces": building_replaces,
                    "BuildingPrereqs": building_prereqs,
                    "Building_CitizenYieldChanges": building_citizen_yield_changes,
                    "Building_GreatPersonPoints": building_great_person_points,
                    "Building_RequiredFeatures": building_required_features,
                    "Building_TourismBombs_XP2": building_tourism_bombs_xp2,
                    "Building_ResourceCosts": building_resource_costs,
                    "Building_ValidFeatures": building_valid_features,
                    "Building_ValidTerrains": building_valid_terrains,
                    "Building_YieldChanges": building_yield_changes,
                    "Building_YieldChangesBonusWithPower": building_yield_changes_bonus_with_power,
                    "Building_YieldDistrictCopies": building_yield_district_copies,
                    "Building_YieldsPerEra": building_yields_per_era,
                    "BuildingConditions": building_conditions,
                    "Building_BuildChargeProductions": building_build_charge_productions,
                    "Building_GreatWorks": building_greatworks,
                },
            }
            return payload
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def _import_unit_payload_from_db(self, unit_type: str) -> dict[str, object] | None:
        settings = load_settings()
        db_path = Path(str(settings.game_db_path or "")).expanduser()
        if not db_path.exists() and DEFAULT_GAME_DB.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            return None

        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return None

        try:
            unit_rows = self._load_db_row_dicts(conn, "Units", "UnitType", unit_type)
            if not unit_rows:
                return None
            unit_row = unit_rows[0]

            schema = build_units_main_schema()
            table_data: dict[str, object] = {}
            for field in schema.fields:
                raw = unit_row.get(field.key)
                value = self._coerce_db_value(raw)
                if field.key in {"Name", "Description"}:
                    table_data[field.key] = self._resolve_loc_or_unknown(value)
                elif field.key == "TraitType":
                    table_data[field.key] = "" if raw is None else str(raw)
                else:
                    table_data[field.key] = value

            def _rows(table: str, key: str = "UnitType") -> list[dict[str, object]]:
                return self._load_db_row_dicts(conn, table, key, unit_type)

            mode_row = (_rows("Units_MODE") or [{}])[0]
            units_mode = {"UnitType": unit_type, "ActionCharges": int(mode_row.get("ActionCharges", 0) or 0)}

            presentation_row = (_rows("Units_Presentation") or [{}])[0]
            units_presentation = {"UnitType": unit_type, "UIFlagOffset": int(presentation_row.get("UIFlagOffset", 0) or 0)}

            xp2_row = (_rows("Units_XP2") or [{}])[0]
            units_xp2 = {
                "UnitType": unit_type,
                "ResourceMaintenanceAmount": int(xp2_row.get("ResourceMaintenanceAmount", 0) or 0),
                "ResourceCost": int(xp2_row.get("ResourceCost", 0) or 0),
                "ResourceMaintenanceType": str(xp2_row.get("ResourceMaintenanceType") or ""),
                "TourismBomb": int(xp2_row.get("TourismBomb", 0) or 0),
                "CanEarnExperience": int(xp2_row.get("CanEarnExperience", 1) or 1),
                "TourismBombPossible": int(xp2_row.get("TourismBombPossible", 0) or 0),
                "CanFormMilitaryFormation": int(xp2_row.get("CanFormMilitaryFormation", 1) or 1),
                "MajorCivOnly": int(xp2_row.get("MajorCivOnly", 0) or 0),
                "CanCauseDisasters": int(xp2_row.get("CanCauseDisasters", 0) or 0),
                "CanSacrificeUnits": int(xp2_row.get("CanSacrificeUnits", 0) or 0),
            }

            replaces_row = (self._load_db_row_dicts(conn, "UnitReplaces", "CivUniqueUnitType", unit_type) or [{}])[0]
            unit_replaces = {
                "CivUniqueUnitType": unit_type,
                "ReplacesUnitType": str(replaces_row.get("ReplacesUnitType") or ""),
            }

            upgrades_row = (_rows("UnitUpgrades", "Unit") or [{}])[0]
            unit_upgrades = {
                "Unit": unit_type,
                "UpgradeUnit": str(upgrades_row.get("UpgradeUnit") or ""),
            }

            captures_row = (self._load_db_row_dicts(conn, "UnitCaptures", "CapturedUnitType", unit_type) or [{}])[0]
            unit_captures = {
                "CapturedUnitType": unit_type,
                "BecomesUnitType": str(captures_row.get("BecomesUnitType") or ""),
            }

            unit_retreats_xp1 = [
                {
                    "UnitType": unit_type,
                    "UnitRetreatType": str(row.get("UnitRetreatType") or ""),
                    "BuildingType": str(row.get("BuildingType") or ""),
                    "ImprovementType": str(row.get("ImprovementType") or ""),
                }
                for row in _rows("UnitRetreats_XP1")
            ]
            unit_building_prereqs = [
                {
                    "Unit": unit_type,
                    "PrereqBuilding": str(row.get("PrereqBuilding") or ""),
                    "NumSupported": int(row.get("NumSupported", -1) or -1),
                }
                for row in _rows("Unit_BuildingPrereqs", "Unit")
            ]
            unit_ai_infos = [
                {
                    "UnitType": unit_type,
                    "AiType": str(row.get("AiType") or ""),
                }
                for row in _rows("UnitAiInfos")
            ]
            type_tags = [
                {
                    "Type": unit_type,
                    "Tag": str(row.get("Tag") or ""),
                }
                for row in _rows("TypeTags", "Type")
            ]

            unit_ability_bindings: list[dict[str, object]] = []

            payload: dict[str, object] = {
                "name": self._resolve_loc_or_unknown(unit_row.get("Name")) or unit_type,
                "type": unit_type,
                "abbr": unit_type[5:] if unit_type.startswith("UNIT_") else unit_type,
                "table_name": "Units",
                "table_data": table_data,
                "images": {},
                "units_mode": units_mode,
                "units_presentation": units_presentation,
                "units_xp2": units_xp2,
                "unit_replaces": unit_replaces,
                "unit_upgrades": unit_upgrades,
                "unit_captures": unit_captures,
                "unit_retreats_xp1": unit_retreats_xp1,
                "unit_building_prereqs": unit_building_prereqs,
                "unit_ai_infos": unit_ai_infos,
                "type_tags": type_tags,
                "unit_ability_bindings": unit_ability_bindings,
                "subtables": {
                    "Units_MODE": units_mode,
                    "Units_Presentation": units_presentation,
                    "Units_XP2": units_xp2,
                    "UnitReplaces": unit_replaces,
                    "UnitUpgrades": unit_upgrades,
                    "UnitCaptures": unit_captures,
                    "UnitRetreats_XP1": unit_retreats_xp1,
                    "Unit_BuildingPrereqs": unit_building_prereqs,
                    "UnitAiInfos": unit_ai_infos,
                    "TypeTags": type_tags,
                    "UnitAbilityBindings": unit_ability_bindings,
                },
            }
            return payload
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def _import_improvement_payload_from_db(self, improvement_type: str) -> dict[str, object] | None:
        settings = load_settings()
        db_path = Path(str(settings.game_db_path or "")).expanduser()
        if not db_path.exists() and DEFAULT_GAME_DB.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            return None

        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return None

        try:
            improvement_rows = self._load_db_row_dicts(conn, "Improvements", "ImprovementType", improvement_type)
            if not improvement_rows:
                return None
            improvement_row = improvement_rows[0]

            schema = build_improvements_main_schema()
            table_data: dict[str, object] = {}
            for field in schema.fields:
                raw = improvement_row.get(field.key)
                value = self._coerce_db_value(raw)
                if field.key in {"Name", "Description"}:
                    table_data[field.key] = self._resolve_loc_or_unknown(value)
                elif field.key == "TraitType":
                    table_data[field.key] = "" if raw is None else str(raw)
                else:
                    table_data[field.key] = value

            def _rows(table: str, key: str = "ImprovementType") -> list[dict[str, object]]:
                return self._load_db_row_dicts(conn, table, key, improvement_type)

            mode_row = (_rows("Improvements_MODE") or [{}])[0]
            improvements_mode = {
                "ImprovementType": improvement_type,
                "Industry": int(mode_row.get("Industry", 0) or 0),
                "Corporation": int(mode_row.get("Corporation", 0) or 0),
            }

            xp2_row = (_rows("Improvements_XP2") or [{}])[0]
            improvements_xp2 = {
                "ImprovementType": improvement_type,
                "AllowImpassableMovement": int(xp2_row.get("AllowImpassableMovement", 0) or 0),
                "BuildOnAdjacentPlot": int(xp2_row.get("BuildOnAdjacentPlot", 0) or 0),
                "PreventsDrought": int(xp2_row.get("PreventsDrought", 0) or 0),
                "DisasterResistant": int(xp2_row.get("DisasterResistant", 0) or 0),
            }

            tourism_row = (_rows("Improvement_Tourism") or [{}])[0]
            improvement_tourism = {
                "ImprovementType": improvement_type,
                "TourismSource": str(tourism_row.get("TourismSource") or "NO_TOURISMSOURCE"),
                "PrereqCivic": str(tourism_row.get("PrereqCivic") or ""),
                "PrereqTech": str(tourism_row.get("PrereqTech") or ""),
                "ScalingFactor": int(tourism_row.get("ScalingFactor", 100) or 100),
            }

            outside_rows = _rows("Improvement_YieldsOutsideTerritories")
            improvement_yields_outside_territories = [{"ImprovementType": improvement_type}] if outside_rows else []

            improvement_bonus_yield_changes = [
                {
                    "Id": str(row.get("Id") or ""),
                    "ImprovementType": improvement_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "BonusYieldChange": int(row.get("BonusYieldChange", 0) or 0),
                    "PrereqTech": str(row.get("PrereqTech") or ""),
                    "PrereqCivic": str(row.get("PrereqCivic") or ""),
                }
                for row in _rows("Improvement_BonusYieldChanges")
            ]

            improvement_yield_changes = [
                {
                    "ImprovementType": improvement_type,
                    "YieldType": str(row.get("YieldType") or ""),
                    "YieldChange": int(row.get("YieldChange", 0) or 0),
                }
                for row in _rows("Improvement_YieldChanges")
            ]

            improvement_invalid_adjacent_features = [
                {
                    "ImprovementType": improvement_type,
                    "FeatureType": str(row.get("FeatureType") or ""),
                }
                for row in _rows("Improvement_InvalidAdjacentFeatures")
            ]
            improvement_valid_adjacent_resources = [
                {
                    "ImprovementType": improvement_type,
                    "ResourceType": str(row.get("ResourceType") or ""),
                }
                for row in _rows("Improvement_ValidAdjacentResources")
            ]
            improvement_valid_adjacent_terrains = [
                {
                    "ImprovementType": improvement_type,
                    "TerrainType": str(row.get("TerrainType") or ""),
                }
                for row in _rows("Improvement_ValidAdjacentTerrains")
            ]
            improvement_valid_build_units = [
                {
                    "ImprovementType": improvement_type,
                    "UnitType": str(row.get("UnitType") or ""),
                }
                for row in _rows("Improvement_ValidBuildUnits")
            ]
            if not improvement_valid_build_units:
                improvement_valid_build_units = [{"ImprovementType": improvement_type, "UnitType": "UNIT_BUILDER"}]

            improvement_valid_features = [
                {
                    "ImprovementType": improvement_type,
                    "FeatureType": str(row.get("FeatureType") or ""),
                    "PrereqTech": str(row.get("PrereqTech") or ""),
                    "PrereqCivic": str(row.get("PrereqCivic") or ""),
                }
                for row in _rows("Improvement_ValidFeatures")
            ]
            improvement_valid_resources = [
                {
                    "ImprovementType": improvement_type,
                    "ResourceType": str(row.get("ResourceType") or ""),
                    "MustRemoveFeature": int(row.get("MustRemoveFeature", 1) or 1),
                }
                for row in _rows("Improvement_ValidResources")
            ]
            improvement_valid_terrains = [
                {
                    "ImprovementType": improvement_type,
                    "TerrainType": str(row.get("TerrainType") or ""),
                    "PrereqTech": str(row.get("PrereqTech") or ""),
                    "PrereqCivic": str(row.get("PrereqCivic") or ""),
                }
                for row in _rows("Improvement_ValidTerrains")
            ]

            improvement_adjacencies: list[dict[str, object]] = []
            adjacency_links = _rows("Improvement_Adjacencies")
            for row in adjacency_links:
                yield_change_id = str(row.get("YieldChangeId") or "").strip()
                if not yield_change_id:
                    continue
                adjacency_rows = self._load_db_row_dicts(conn, "Adjacency_YieldChanges", "ID", yield_change_id)
                if not adjacency_rows:
                    improvement_adjacencies.append({"mode": "existing", "id": yield_change_id})
                    continue
                adj_row = adjacency_rows[0]

                source_type = ""
                source_detail = ""
                bool_fields = [
                    "OtherDistrictAdjacent",
                    "AdjacentSeaResource",
                    "AdjacentRiver",
                    "AdjacentWonder",
                    "AdjacentNaturalWonder",
                    "AdjacentResource",
                    "Self",
                ]
                value_fields = [
                    "AdjacentTerrain",
                    "AdjacentFeature",
                    "AdjacentImprovement",
                    "AdjacentDistrict",
                    "AdjacentResourceClass",
                ]
                for field in bool_fields:
                    if int(adj_row.get(field, 0) or 0) == 1:
                        source_type = field
                        break
                if not source_type:
                    for field in value_fields:
                        value = str(adj_row.get(field) or "").strip()
                        if value:
                            source_type = field
                            source_detail = value
                            break

                improvement_adjacencies.append(
                    {
                        "mode": "custom",
                        "id": yield_change_id,
                        "description": str(adj_row.get("Description") or "Placeholder"),
                        "yield_type": str(adj_row.get("YieldType") or ""),
                        "yield_change": int(adj_row.get("YieldChange", 0) or 0),
                        "tiles_required": int(adj_row.get("TilesRequired", 1) or 1),
                        "source_type": source_type,
                        "source_detail": source_detail,
                        "prereq_tech": str(adj_row.get("PrereqTech") or ""),
                        "prereq_civic": str(adj_row.get("PrereqCivic") or ""),
                        "obsolete_tech": str(adj_row.get("ObsoleteTech") or ""),
                        "obsolete_civic": str(adj_row.get("ObsoleteCivic") or ""),
                    }
                )

            payload: dict[str, object] = {
                "name": self._resolve_loc_or_unknown(improvement_row.get("Name")) or improvement_type,
                "type": improvement_type,
                "abbr": improvement_type[12:] if improvement_type.startswith("IMPROVEMENT_") else improvement_type,
                "table_name": "Improvements",
                "table_data": table_data,
                "images": {},
                "improvements_mode": improvements_mode,
                "improvements_xp2": improvements_xp2,
                "improvement_tourism": improvement_tourism,
                "improvement_yields_outside_territories": improvement_yields_outside_territories,
                "improvement_bonus_yield_changes": improvement_bonus_yield_changes,
                "improvement_yield_changes": improvement_yield_changes,
                "improvement_invalid_adjacent_features": improvement_invalid_adjacent_features,
                "improvement_valid_adjacent_resources": improvement_valid_adjacent_resources,
                "improvement_valid_adjacent_terrains": improvement_valid_adjacent_terrains,
                "improvement_valid_build_units": improvement_valid_build_units,
                "improvement_valid_features": improvement_valid_features,
                "improvement_valid_resources": improvement_valid_resources,
                "improvement_valid_terrains": improvement_valid_terrains,
                "improvement_adjacencies": improvement_adjacencies,
                "subtables": {
                    "Improvements_MODE": improvements_mode,
                    "Improvements_XP2": improvements_xp2,
                    "Improvement_Tourism": improvement_tourism,
                    "Improvement_YieldsOutsideTerritories": improvement_yields_outside_territories,
                    "Improvement_BonusYieldChanges": improvement_bonus_yield_changes,
                    "Improvement_YieldChanges": improvement_yield_changes,
                    "Improvement_InvalidAdjacentFeatures": improvement_invalid_adjacent_features,
                    "Improvement_ValidAdjacentResources": improvement_valid_adjacent_resources,
                    "Improvement_ValidAdjacentTerrains": improvement_valid_adjacent_terrains,
                    "Improvement_ValidBuildUnits": improvement_valid_build_units,
                    "Improvement_ValidFeatures": improvement_valid_features,
                    "Improvement_ValidResources": improvement_valid_resources,
                    "Improvement_ValidTerrains": improvement_valid_terrains,
                    "Improvement_Adjacencies": improvement_adjacencies,
                },
            }
            return payload

        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def _import_great_people_payload_from_db(self, class_type: str) -> dict[str, object] | None:
        db_path = Path(load_settings().game_db_path)
        if not db_path.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            return None

        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM GreatPersonClasses WHERE GreatPersonClassType = ?",
                    (class_type,),
                ).fetchone()
                if row is None:
                    return None

                class_data = {
                    "GreatPersonClassType": str(row["GreatPersonClassType"] or ""),
                    "Name": self._resolve_loc_or_unknown(row["Name"]),
                    "UnitType": str(row["UnitType"] or ""),
                    "DistrictType": str(row["DistrictType"] or ""),
                    "MaxPlayerInstances": int(row["MaxPlayerInstances"] or -1),
                    "PseudoYieldType": str(row["PseudoYieldType"] or ""),
                    "IconString": str(row["IconString"] or ""),
                    "ActionIcon": str(row["ActionIcon"] or ""),
                    "AvailableInTimeline": int(row["AvailableInTimeline"] or 0),
                    "GenerateDuplicateIndividuals": int(row["GenerateDuplicateIndividuals"] or 0),
                }

                unit_type = str(row["UnitType"] or "")
                unit_row = None
                if unit_type:
                    unit_row = conn.execute(
                        "SELECT UnitType, BaseSightRange, BaseMoves, FormationClass, Domain, CanRetreatWhenCaptured, CanCapture, Cost, ZoneOfControl, FoundReligion, CanTrain, TraitType, Name, Description FROM Units WHERE UnitType = ?",
                        (unit_type,),
                    ).fetchone()

                unit_data = {
                    "UnitType": unit_type,
                    "BaseSightRange": 4,
                    "BaseMoves": 5,
                    "FormationClass": "FORMATION_CLASS_CIVILIAN",
                    "Domain": "DOMAIN_LAND",
                    "CanRetreatWhenCaptured": 0,
                    "CanCapture": 0,
                    "Cost": 1,
                    "ZoneOfControl": 0,
                    "FoundReligion": 0,
                    "CanTrain": 0,
                    "TraitType": "",
                    "Name": "",
                    "Description": "",
                }
                if unit_row is not None:
                    unit_data.update(
                        {
                            "UnitType": str(unit_row["UnitType"] or unit_type),
                            "BaseSightRange": int(unit_row["BaseSightRange"] or 4),
                            "BaseMoves": int(unit_row["BaseMoves"] or 5),
                            "FormationClass": str(unit_row["FormationClass"] or "FORMATION_CLASS_CIVILIAN"),
                            "Domain": str(unit_row["Domain"] or "DOMAIN_LAND"),
                            "CanRetreatWhenCaptured": int(unit_row["CanRetreatWhenCaptured"] or 0),
                            "CanCapture": int(unit_row["CanCapture"] or 0),
                            "Cost": int(unit_row["Cost"] or 1),
                            "ZoneOfControl": int(unit_row["ZoneOfControl"] or 0),
                            "FoundReligion": int(unit_row["FoundReligion"] or 0),
                            "CanTrain": int(unit_row["CanTrain"] or 0),
                            "TraitType": str(unit_row["TraitType"] or ""),
                            "Name": self._resolve_loc_or_unknown(unit_row["Name"]),
                            "Description": self._resolve_loc_or_unknown(unit_row["Description"]),
                        }
                    )
        except sqlite3.Error:
            return None

        abbr = ""
        normalized = class_type.strip().upper()
        marker = "GREAT_PERSON_CLASS_"
        if normalized.startswith(marker):
            abbr = normalized[len(marker):].split("_")[-1]

        return {
            "name": str(class_data.get("Name") or "").strip(),
            "abbr": abbr,
            "type": class_type,
            "import_locked": True,
            "class_data": class_data,
            "unit_data": unit_data,
            "individuals": [],
        }

    def _handle_section_item_changed(self, section: str, index: int, payload: dict[str, object]) -> None:
        entries = self._project.sections.get(section)
        if not isinstance(entries, list):
            return
        if index < 0 or index >= len(entries):
            return
        previous_name = self._resolve_entry_name(entries[index], index)
        entries[index] = payload
        self._modifier_workspace.sync_owners_from_sections(self._project.sections)
        self._refresh_visible_workspace_after_item_changed(section)
        new_name = self._resolve_entry_name(payload, index)
        LOGGER.debug(
            "Section item changed: section=%s index=%d previous_name=%s new_name=%s",
            section,
            index,
            previous_name,
            new_name,
        )
        if new_name != previous_name:
            current = self._tree.currentItem()
            if current is not None:
                item_payload = current.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(item_payload, dict) and item_payload.get("kind") == "section_item":
                    raw_index = item_payload.get("index")
                    try:
                        item_index = int(raw_index)
                    except (TypeError, ValueError):
                        item_index = -1
                    if item_payload.get("section") == section and item_index == index:
                        current.setText(0, new_name)
                        item_payload["entry_name"] = new_name
                        current.setData(0, Qt.ItemDataRole.UserRole, item_payload)
                        self._workspace_title.setText(new_name)

    def _refresh_visible_workspace_after_item_changed(self, section: str) -> None:
        current = self._tree.currentItem()
        if current is None:
            return
        item_payload = current.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(item_payload, dict):
            return
        kind = str(item_payload.get("kind") or "")
        if kind == "project_root":
            self._refresh_project_root_workspace()
            return
        if kind == "section_group" and str(item_payload.get("section") or "") == section:
            self._group_workspace.set_section(section)

    @staticmethod
    def _next_copied_abbr(source_abbr: str, existing_abbrs: set[str]) -> str:
        base = str(source_abbr or "").strip().upper()
        if not base:
            base = "COPY"
        match = re.match(r"^(.*?)(?:_(\d+))?$", base)
        if match is None:
            root = base
            start = 1
        else:
            root = str(match.group(1) or base).strip("_") or base
            start = int(match.group(2)) + 1 if match.group(2) else 1
        candidate = f"{root}_{start}"
        while candidate in existing_abbrs:
            start += 1
            candidate = f"{root}_{start}"
        return candidate

    def _handle_duplicate_section_item(self, section: str, index: int, payload: dict[str, object]) -> None:
        if section not in {"政策卡", "信仰"}:
            return
        entries = self._project.sections.get(section)
        if not isinstance(entries, list):
            return
        if index < 0 or index >= len(entries):
            return
        if not isinstance(payload, dict):
            return

        clone = dict(payload)
        existing_abbrs = {
            str(item.get("abbr") or "").strip().upper()
            for item in entries
            if isinstance(item, dict)
        }
        source_abbr = str(clone.get("abbr") or "").strip()
        new_abbr = self._next_copied_abbr(source_abbr, existing_abbrs)
        clone["abbr"] = new_abbr

        entries.append(clone)
        new_index = len(entries) - 1
        self._rebuild_tree()
        self._select_section_item(section, new_index)

    def _select_section_item(self, section: str, index: int) -> None:
        root = self._tree.topLevelItem(0)
        if root is None:
            return
        for i in range(root.childCount()):
            section_item = root.child(i)
            payload = section_item.data(0, Qt.ItemDataRole.UserRole)
            if not isinstance(payload, dict):
                continue
            if payload.get("kind") != "section_group" or payload.get("section") != section:
                continue
            if index < 0 or index >= section_item.childCount():
                return
            child = section_item.child(index)
            self._tree.setCurrentItem(child)
            return

    def _select_section_group(self, section: str) -> None:
        root = self._tree.topLevelItem(0)
        if root is None:
            return
        for i in range(root.childCount()):
            section_item = root.child(i)
            payload = section_item.data(0, Qt.ItemDataRole.UserRole)
            if not isinstance(payload, dict):
                continue
            if payload.get("kind") == "section_group" and payload.get("section") == section:
                self._tree.setCurrentItem(section_item)
                return

    def _session_title(self, session: ProjectSession) -> str:
        if session.file_path is not None:
            return session.file_path.name
        return f"{session.project.project_name}{CIV_FILE_EXTENSION}"

    def _add_session(self, project: CivProject, file_path: Path | None) -> None:
        session = ProjectSession(project=project, file_path=file_path)
        self._sessions.append(session)
        self._project_tabs.addTab(self._session_title(session))
        new_index = len(self._sessions) - 1
        self._set_active_session(new_index)

    def _set_active_session(self, index: int) -> None:
        if index < 0 or index >= len(self._sessions):
            return
        self._handling_tab_change = True
        self._project_tabs.setCurrentIndex(index)
        self._handling_tab_change = False

        self._active_session_index = index
        session = self._sessions[index]
        self._project = session.project
        self._project_file_path = session.file_path
        self._load_workspace_sections_into_editors()
        self._rebuild_tree()
        self._refresh_project_tab_titles()

    def _refresh_project_tab_titles(self) -> None:
        for index, session in enumerate(self._sessions):
            self._project_tabs.setTabText(index, self._session_title(session))

    def _handle_project_tab_changed(self, new_index: int) -> None:
        if self._handling_tab_change:
            return
        if new_index < 0 or new_index >= len(self._sessions):
            return

        if 0 <= self._active_session_index < len(self._sessions):
            self._sync_workspace_sections_from_editors()
            self._sessions[self._active_session_index].project = self._project
            self._sessions[self._active_session_index].file_path = self._project_file_path

        self._active_session_index = new_index
        session = self._sessions[new_index]
        self._project = session.project
        self._project_file_path = session.file_path
        self._load_workspace_sections_into_editors()
        self._rebuild_tree()

    def _save_basic_info_payload_to_project(self, payload: dict[str, object]) -> None:
        self._project.sections["基础信息"] = {
            "format": BASIC_INFO_SECTION_FORMAT,
            "schema_version": BASIC_INFO_SECTION_SCHEMA,
            "data": payload,
        }

    def _load_basic_info_payload_from_project(self) -> dict[str, object] | None:
        section = self._project.sections.get("基础信息")
        if not isinstance(section, dict):
            return {}

        format_name = section.get("format")
        data = section.get("data")
        if format_name == BASIC_INFO_SECTION_FORMAT and isinstance(data, dict):
            return data

        return section

    def _save_modifier_payload_to_project(self, payload: dict[str, object]) -> None:
        self._project.sections["修改器"] = {
            "format": MODIFIER_SECTION_FORMAT,
            "schema_version": MODIFIER_SECTION_SCHEMA,
            "data": payload,
        }

    def _save_art_payload_to_project(self, payload: dict[str, object]) -> None:
        self._project.sections["美术"] = payload if isinstance(payload, dict) else {}

    def _load_modifier_payload_from_project(self) -> dict[str, object] | None:
        section = self._project.sections.get("修改器")
        if not isinstance(section, dict):
            return {}

        format_name = section.get("format")
        data = section.get("data")
        if format_name == MODIFIER_SECTION_FORMAT and isinstance(data, dict):
            return data

        # 兼容旧结构：直接把修改器数据字典存放在“修改器”节点
        return section

    def _modifier_custom_unit_abilities(self) -> list[dict[str, object]]:
        payload = self._load_modifier_payload_from_project()
        if not isinstance(payload, dict):
            return []
        raw_rows = payload.get("unit_abilities")
        if not isinstance(raw_rows, list):
            return []
        return [row for row in raw_rows if isinstance(row, dict)]

    def _modifier_strength_preview_text_rows(self) -> list[str]:
        payload = self._load_modifier_payload_from_project()
        if not isinstance(payload, dict):
            return []
        raw_modifiers = payload.get("modifiers")
        if not isinstance(raw_modifiers, list):
            return []

        rows: list[str] = []
        for modifier in raw_modifiers:
            if not isinstance(modifier, dict):
                continue
            effect_type = str(modifier.get("effect_type") or "").strip().upper()
            if effect_type != "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER":
                continue
            modifier_id = str(modifier.get("modifier_id") or "").strip()
            preview_text = str(modifier.get("preview_text") or "").strip()
            if not modifier_id or not preview_text:
                continue
            rows.append(
                f"('zh_Hans_CN','LOC_{modifier_id}_PREVIEW','{self._sql_escape(preview_text)}')"
            )
        return rows

    def _load_art_payload_from_project(self) -> dict[str, object] | None:
        section = self._project.sections.get("美术")
        if isinstance(section, dict):
            return section
        return {}

    def _sync_workspace_sections_from_editors(self) -> None:
        self._save_basic_info_payload_to_project(self._basic_info_workspace.export_project_payload())
        self._save_art_payload_to_project(self._art_workspace.export_project_payload())
        payload = self._modifier_workspace.export_project_payload()
        self._save_modifier_payload_to_project(payload)

    def _workspace_sections_snapshot_for_selectors(self) -> dict[str, object]:
        # Ensure selector dialogs can read the latest edits across workspaces,
        # not only the last-saved project.sections snapshot.
        if not self._loading_project:
            try:
                self._sync_workspace_sections_from_editors()
            except Exception as exc:
                LOGGER.debug("selector sections snapshot sync failed: %s", exc)
        return self._project.sections if isinstance(self._project.sections, dict) else {}

    def _load_workspace_sections_into_editors(self) -> None:
        self._loading_project = True
        try:
            basic_payload = self._load_basic_info_payload_from_project()
            self._basic_info_workspace.import_project_payload(basic_payload)

            art_payload = self._load_art_payload_from_project()
            self._art_workspace.import_project_payload(art_payload)
            self._art_workspace.refresh_from_sections(self._project.sections)

            payload = self._load_modifier_payload_from_project()
            self._modifier_workspace.import_project_payload(payload)
            self._modifier_workspace.sync_owners_from_sections(self._project.sections)
        finally:
            self._loading_project = False

    def _refresh_all_workspaces_after_project_open(self) -> None:
        # 注意：刚打开工程时不要立即把“编辑器当前状态”回写到 project。
        # 这会在加载顺序/信号回调发生时把磁盘读取到的 direct workspace（尤其是“美术”）覆盖成空。
        self._art_workspace.refresh_from_sections(self._project.sections)
        self._modifier_workspace.sync_owners_from_sections(self._project.sections)
        self._text_workspace.refresh_preview()
        self._refresh_project_root_workspace()

        for section in CIV_SECTION_ORDER:
            if section in CIV_DIRECT_WORKSPACE_SECTIONS:
                continue
            self._group_workspace.set_section(section)

        self._handle_selection_changed()
        LOGGER.info("Full workspace refresh completed after project load: project=%s", self._project.project_name)

    def _text_file_suffix(self) -> str:
        basic = self._load_basic_info_payload_from_project() or {}
        global_settings = basic.get("global_settings") if isinstance(basic, dict) else {}
        language = str(global_settings.get("language") or "简体中文") if isinstance(global_settings, dict) else "简体中文"
        mapping = {
            "简体中文": "CN",
            "简体中文，英文": "EN",
            "简体中文，英文，繁体中文": "HK",
        }
        return mapping.get(language, "CN")

    @staticmethod
    def _group_preview_format_sections() -> set[str]:
        return {"文明", "领袖", "区域", "建筑", "单位", "改良设施", "总督", "伟人", "政策卡", "项目", "信仰", "议程"}

    def _preview_settings_bucket(self) -> dict[str, object]:
        text_section = self._project.sections.get("文本")
        if not isinstance(text_section, dict):
            text_section = {}
            self._project.sections["文本"] = text_section
        settings = text_section.get("preview_settings")
        if not isinstance(settings, dict):
            settings = {}
            text_section["preview_settings"] = settings
        return settings

    def _get_group_preview_format(self, section: str) -> str:
        if section not in self._group_preview_format_sections():
            return "sql"
        settings = self._preview_settings_bucket()
        group_formats = settings.get("group_formats") if isinstance(settings.get("group_formats"), dict) else {}
        fmt = str(group_formats.get(section) or "sql").strip().lower()
        return "xml" if fmt == "xml" else "sql"

    def _set_group_preview_format(self, section: str, fmt: str) -> None:
        if section not in self._group_preview_format_sections():
            return
        normalized = "xml" if str(fmt).strip().lower() == "xml" else "sql"
        settings = self._preview_settings_bucket()
        group_formats = settings.get("group_formats")
        if not isinstance(group_formats, dict):
            group_formats = {}
            settings["group_formats"] = group_formats
        group_formats[section] = normalized

    def _get_text_preview_format(self) -> str:
        settings = self._preview_settings_bucket()
        fmt = str(settings.get("text_format") or "sql").strip().lower()
        return "xml" if fmt == "xml" else "sql"

    def _set_text_preview_format(self, fmt: str) -> None:
        normalized = "xml" if str(fmt).strip().lower() == "xml" else "sql"
        settings = self._preview_settings_bucket()
        settings["text_format"] = normalized

    def _build_configs_sql_preview(self) -> str:
        civilizations = self._project.sections.get("文明")
        civ_entries = [entry for entry in civilizations if isinstance(entry, dict)] if isinstance(civilizations, list) else []
        leaders = self._project.sections.get("领袖")
        leader_entries = [entry for entry in leaders if isinstance(entry, dict)] if isinstance(leaders, list) else []

        if not leader_entries:
            return "-- Configs.sql\n-- 暂无文明/领袖绑定数据"

        civ_map: dict[str, dict[str, object]] = {}
        for entry in civ_entries:
            civ_type = str(entry.get("type") or "").strip()
            if civ_type:
                civ_map[civ_type] = entry

        def _to_trait_type(raw_type: str) -> tuple[str, str]:
            t = str(raw_type or "").strip()
            if not t:
                return "", ""
            if t.startswith("TRAIT_"):
                return t, t[len("TRAIT_") :]
            return f"TRAIT_{t}", t

        def _strip_png_suffix(name: str) -> str:
            text = str(name or "").strip()
            if text.lower().endswith(".png"):
                return text[:-4]
            return text

        def _normalize_civ_type(civ_type: str) -> str:
            text = str(civ_type or "").strip().upper()
            if not text:
                return ""
            if text.startswith("CIVILIZATION_"):
                return text
            return f"CIVILIZATION_{text}"

        normalized_civ_map: dict[str, dict[str, object]] = {}
        for key, value in civ_map.items():
            normalized = _normalize_civ_type(key)
            if normalized:
                normalized_civ_map[normalized] = value
        civ_map.update(normalized_civ_map)

        governor_entries = self._project.sections.get("总督")
        governor_trait_map: dict[str, str] = {}
        if isinstance(governor_entries, list):
            for governor_entry in governor_entries:
                if not isinstance(governor_entry, dict):
                    continue
                if not bool(governor_entry.get("new_trait_type", False)):
                    continue
                governor_type = str(governor_entry.get("GovernorType") or governor_entry.get("type") or "").strip()
                governor_trait = str(governor_entry.get("TraitType") or governor_entry.get("trait_type") or "").strip()
                if governor_type and governor_trait:
                    governor_trait_map[governor_type] = governor_trait

        def _trait_from_loc_tag(tag: str) -> str:
            text = str(tag or "").strip()
            if text.startswith("LOC_") and text.endswith("_NAME"):
                return text[4:-5]
            if text.startswith("LOC_") and text.endswith("_DESCRIPTION"):
                return text[4:-12]
            return ""

        def _resolve_game_db_path() -> Path | None:
            settings = load_settings()
            db_path = Path(str(settings.game_db_path or "")).expanduser()
            if db_path.exists():
                return db_path
            if DEFAULT_GAME_DB.exists():
                return DEFAULT_GAME_DB
            return None

        db_civ_cache: dict[str, dict[str, object]] = {}

        def _fetch_db_civ_payload(civ_type: str) -> dict[str, object] | None:
            if civ_type in db_civ_cache:
                payload = db_civ_cache[civ_type]
                return payload if payload else None

            db_path = _resolve_game_db_path()
            if db_path is None:
                db_civ_cache[civ_type] = {}
                return None

            try:
                conn = sqlite3.connect(str(db_path))
            except sqlite3.Error:
                db_civ_cache[civ_type] = {}
                return None

            try:
                def _query_rows(sql: str, params: tuple[object, ...]) -> list[dict[str, object]]:
                    try:
                        cursor = conn.execute(sql, params)
                        columns = [str(item[0]) for item in cursor.description or []]
                        rows = cursor.fetchall()
                    except sqlite3.Error:
                        return []
                    return [dict(zip(columns, row)) for row in rows]

                player_rows = self._load_db_row_dicts(conn, "Players", "CivilizationType", civ_type)
                template = player_rows[0] if player_rows else {}
                domain = str(template.get("Domain") or "Players:Expansion2_Players").strip() or "Players:Expansion2_Players"

                civ_rows = self._load_db_row_dicts(conn, "Civilizations", "CivilizationType", civ_type)
                civ_row = civ_rows[0] if civ_rows else {}

                civ_trait_rows = _query_rows(
                    "SELECT TraitType FROM CivilizationTraits WHERE CivilizationType = ?",
                    (civ_type,),
                )
                trait_types: list[str] = []
                seen_trait_types: set[str] = set()
                for row in civ_trait_rows:
                    trait_type = str(row.get("TraitType") or "").strip()
                    if not trait_type or trait_type in seen_trait_types:
                        continue
                    seen_trait_types.add(trait_type)
                    trait_types.append(trait_type)

                trait_meta_map: dict[str, dict[str, str]] = {}
                for trait_type in trait_types:
                    trait_rows = _query_rows(
                        "SELECT Name, Description FROM Traits WHERE TraitType = ?",
                        (trait_type,),
                    )
                    trait_row = trait_rows[0] if trait_rows else {}
                    trait_meta_map[trait_type] = {
                        "name": str(trait_row.get("Name") or f"LOC_{trait_type}_NAME").strip() or f"LOC_{trait_type}_NAME",
                        "description": str(trait_row.get("Description") or f"LOC_{trait_type}_DESCRIPTION").strip() or f"LOC_{trait_type}_DESCRIPTION",
                    }

                table_mappings: list[tuple[str, str, str]] = [
                    ("区域", "Districts", "DistrictType"),
                    ("建筑", "Buildings", "BuildingType"),
                    ("单位", "Units", "UnitType"),
                    ("改良设施", "Improvements", "ImprovementType"),
                    ("总督", "Governors", "GovernorType"),
                ]

                mapped_items: list[dict[str, object]] = []
                mapped_traits: set[str] = set()
                for trait_type in trait_types:
                    found = False
                    for section_name, table_name, type_col in table_mappings:
                        rows = _query_rows(
                            f"SELECT {type_col} AS ObjectType FROM {table_name} WHERE TraitType = ?",
                            (trait_type,),
                        )
                        if not rows:
                            continue
                        object_type = str(rows[0].get("ObjectType") or "").strip()
                        if not object_type:
                            continue
                        meta = trait_meta_map.get(trait_type) or {}
                        mapped_items.append(
                            {
                                "section": section_name,
                                "trait_type": trait_type,
                                "source_type": object_type,
                                "icon": f"ICON_{object_type}",
                                "name": str(meta.get("name") or f"LOC_{trait_type}_NAME"),
                                "description": str(meta.get("description") or f"LOC_{trait_type}_DESCRIPTION"),
                                "sort_index": 0,
                            }
                        )
                        mapped_traits.add(trait_type)
                        found = True
                        break
                    if found:
                        continue

                template_ability_name = str(template.get("CivilizationAbilityName") or "").strip()
                template_ability_desc = str(template.get("CivilizationAbilityDescription") or "").strip()
                ability_trait = _trait_from_loc_tag(template_ability_name) or _trait_from_loc_tag(template_ability_desc)
                if ability_trait and ability_trait not in trait_meta_map:
                    ability_trait = ""
                if not ability_trait:
                    for trait_type in trait_types:
                        if trait_type not in mapped_traits:
                            ability_trait = trait_type
                            break

                civ_ability_name = template_ability_name
                civ_ability_description = template_ability_desc
                if ability_trait:
                    ability_meta = trait_meta_map.get(ability_trait) or {}
                    civ_ability_name = str(ability_meta.get("name") or civ_ability_name).strip() or f"LOC_{ability_trait}_NAME"
                    civ_ability_description = str(ability_meta.get("description") or civ_ability_description).strip() or f"LOC_{ability_trait}_DESCRIPTION"

                if not civ_ability_name:
                    civ_ability_name = f"LOC_TRAIT_{civ_type}_NAME"
                if not civ_ability_description:
                    civ_ability_description = f"LOC_TRAIT_{civ_type}_DESCRIPTION"

                base_items: list[dict[str, object]] = []
                for idx, item in enumerate(mapped_items, start=1):
                    payload = dict(item)
                    payload["sort_index"] = idx * 10
                    base_items.append(payload)

                payload = {
                    "domain": domain,
                    "civ_name": str(template.get("CivilizationName") or civ_row.get("Name") or f"LOC_{civ_type}_NAME").strip() or f"LOC_{civ_type}_NAME",
                    "civ_icon": str(template.get("CivilizationIcon") or f"ICON_{civ_type}").strip() or f"ICON_{civ_type}",
                    "civ_ability_name": civ_ability_name,
                    "civ_ability_description": civ_ability_description,
                    "civ_ability_icon": str(template.get("CivilizationAbilityIcon") or "").strip(),
                    "base_items": base_items,
                }
                db_civ_cache[civ_type] = payload
                return payload
            finally:
                conn.close()

        allowed_sections = {"区域", "建筑", "单位", "改良设施", "总督", "伟人"}
        section_order = {"区域": 0, "建筑": 1, "单位": 2, "伟人": 2, "改良设施": 3, "总督": 4}
        players_rows: list[dict[str, object]] = []
        player_items_rows: list[dict[str, object]] = []
        binding_comments: list[str] = []
        seen_player_rows: set[tuple[str, str]] = set()

        for leader_entry in leader_entries:
            leader_type = str(leader_entry.get("type") or "").strip()
            civ_type_raw = str(leader_entry.get("civilization_type") or "").strip()
            civ_type = _normalize_civ_type(civ_type_raw)
            if not leader_type or not civ_type:
                continue
            civ_entry = civ_map.get(civ_type)
            db_civ_payload = _fetch_db_civ_payload(civ_type) if civ_entry is None else None
            if civ_entry is None and db_civ_payload is None:
                db_civ_payload = {
                    "domain": "Players:Expansion2_Players",
                    "civ_name": f"LOC_{civ_type}_NAME",
                    "civ_icon": f"ICON_{civ_type}",
                    "civ_ability_name": f"LOC_TRAIT_{civ_type}_NAME",
                    "civ_ability_description": f"LOC_TRAIT_{civ_type}_DESCRIPTION",
                    "civ_ability_icon": f"ICON_{civ_type}",
                    "base_items": [],
                }

            row_domain = "Players:Expansion2_Players"
            civ_name = f"LOC_{civ_type}_NAME"
            civ_icon = f"ICON_{civ_type}"
            civ_ability_name = f"LOC_TRAIT_{civ_type}_NAME"
            civ_ability_desc = f"LOC_TRAIT_{civ_type}_DESCRIPTION"
            civ_ability_icon = f"ICON_{civ_type}"
            if isinstance(db_civ_payload, dict):
                row_domain = str(db_civ_payload.get("domain") or row_domain).strip() or row_domain
                civ_name = str(db_civ_payload.get("civ_name") or civ_name).strip() or civ_name
                civ_icon = str(db_civ_payload.get("civ_icon") or civ_icon).strip() or civ_icon
                civ_ability_name = str(db_civ_payload.get("civ_ability_name") or civ_ability_name).strip() or civ_ability_name
                civ_ability_desc = str(db_civ_payload.get("civ_ability_description") or civ_ability_desc).strip() or civ_ability_desc
                civ_ability_icon = str(db_civ_payload.get("civ_ability_icon") or civ_ability_icon).strip() or civ_ability_icon

            images = leader_entry.get("images") if isinstance(leader_entry.get("images"), dict) else {}
            portrait_name = _strip_png_suffix(
                str(leader_entry.get("select_foreground_image_name") or f"PORTRAIT_{leader_type}.png")
            )
            portrait_bg_name = _strip_png_suffix(
                str(leader_entry.get("select_background_image_name") or f"PORTRAIT_BACKGROUND_{leader_type}.png")
            )

            if not portrait_name:
                portrait_name = _strip_png_suffix(str(images.get("select_foreground_name") or f"PORTRAIT_{leader_type}.png"))
            if not portrait_bg_name:
                portrait_bg_name = _strip_png_suffix(str(images.get("select_background_name") or f"PORTRAIT_BACKGROUND_{leader_type}.png"))

            player_key = (civ_type, leader_type)
            if player_key not in seen_player_rows:
                seen_player_rows.add(player_key)
                try:
                    leader_sort_index = int(leader_entry.get("select_sort_index") or 0)
                except (TypeError, ValueError):
                    leader_sort_index = 0
                if leader_sort_index < 0:
                    leader_sort_index = 0
                sort_index_sql = "NULL" if leader_sort_index == 0 else str(leader_sort_index)
                players_rows.append(
                    {
                        "civ_type": civ_type,
                        "leader_type": leader_type,
                        "values": [
                            f"'{self._sql_escape(row_domain)}'",
                            f"'{self._sql_escape(civ_type)}'",
                            f"'{self._sql_escape(civ_name)}'",
                            f"'{self._sql_escape(civ_icon)}'",
                            f"'{self._sql_escape(civ_ability_name)}'",
                            f"'{self._sql_escape(civ_ability_desc)}'",
                            f"'{self._sql_escape(civ_ability_icon)}'",
                            f"'{self._sql_escape(leader_type)}'",
                            f"'LOC_{self._sql_escape(leader_type)}_NAME'",
                            f"'ICON_{self._sql_escape(leader_type)}'",
                            f"'LOC_TRAIT_{self._sql_escape(leader_type)}_NAME'",
                            f"'LOC_TRAIT_{self._sql_escape(leader_type)}_DESCRIPTION'",
                            f"'ICON_{self._sql_escape(leader_type)}'",
                            f"'{self._sql_escape(portrait_name)}'",
                            f"'{self._sql_escape(portrait_bg_name)}'",
                            sort_index_sql,
                        ],
                    }
                )

            merged_bindings: list[dict[str, object]] = []
            if isinstance(civ_entry, dict):
                civ_bindings = civ_entry.get("trait_bindings") if isinstance(civ_entry.get("trait_bindings"), list) else []
                for binding in civ_bindings:
                    if isinstance(binding, dict):
                        payload = dict(binding)
                        payload.setdefault("section", str(payload.get("section") or "文明"))
                        merged_bindings.append(payload)
            leader_bindings = leader_entry.get("bindings") if isinstance(leader_entry.get("bindings"), list) else []
            for binding in leader_bindings:
                if isinstance(binding, dict):
                    merged_bindings.append(dict(binding))

            base_items = db_civ_payload.get("base_items") if isinstance(db_civ_payload, dict) and isinstance(db_civ_payload.get("base_items"), list) else []
            typed_items: list[dict[str, object]] = []
            for item in base_items:
                if not isinstance(item, dict):
                    continue
                trait_type = str(item.get("trait_type") or "").strip()
                if not trait_type:
                    continue
                source_type = str(item.get("source_type") or "").strip() or (trait_type[len("TRAIT_"):] if trait_type.startswith("TRAIT_") else trait_type)
                typed_items.append(
                    {
                        "order": -1,
                        "section": str(item.get("section") or "数据库"),
                        "trait_type": trait_type,
                        "source_type": source_type,
                        "icon": str(item.get("icon") or f"ICON_{source_type}").strip() or f"ICON_{source_type}",
                        "name": str(item.get("name") or f"LOC_{trait_type}_NAME").strip() or f"LOC_{trait_type}_NAME",
                        "description": str(item.get("description") or f"LOC_{trait_type}_DESCRIPTION").strip() or f"LOC_{trait_type}_DESCRIPTION",
                        "sort_index": int(item.get("sort_index") or 0),
                    }
                )

            for binding in merged_bindings:
                section = str(binding.get("section") or "").strip()
                if section and section not in allowed_sections:
                    continue
                raw_type = str(binding.get("type") or "").strip()
                if not raw_type:
                    continue
                resolved_section = section
                trait_type = ""
                source_type = ""
                if section == "伟人":
                    gp_entry = None
                    for candidate in self._iter_section_entries("伟人"):
                        class_type = str(candidate.get("type") or "").strip()
                        unit_data = candidate.get("unit_data") if isinstance(candidate.get("unit_data"), dict) else {}
                        unit_type = str(unit_data.get("UnitType") or "").strip()
                        if raw_type == class_type or raw_type == unit_type:
                            gp_entry = candidate
                            break
                    if gp_entry is None:
                        continue
                    gp_unit_data = gp_entry.get("unit_data") if isinstance(gp_entry.get("unit_data"), dict) else {}
                    source_type = str(gp_unit_data.get("UnitType") or "").strip()
                    trait_type = str(gp_unit_data.get("TraitType") or "").strip()
                    if not source_type or not trait_type:
                        continue
                    resolved_section = "单位"
                elif section == "总督":
                    source_type = raw_type
                    trait_type = governor_trait_map.get(raw_type) or f"TRAIT_{raw_type}"
                    if not source_type or not trait_type:
                        continue
                else:
                    trait_type, source_type = _to_trait_type(raw_type)
                if not trait_type or not source_type:
                    continue
                order = section_order.get(section, 99)
                label = str(binding.get("name") or source_type).strip() or source_type
                typed_items.append(
                    {
                        "order": order,
                        "section": resolved_section,
                        "trait_type": trait_type,
                        "source_type": source_type,
                        "icon": f"ICON_{source_type}",
                        "name": f"LOC_{trait_type}_NAME",
                        "description": f"LOC_{trait_type}_DESCRIPTION",
                        "sort_index": 0,
                    }
                )
                binding_comments.append(f"-- {leader_type} -> {section or '未分类'}：{label} ({source_type})")

            dedup_items: list[dict[str, object]] = []
            seen_traits: set[str] = set()
            for item in sorted(
                typed_items,
                key=lambda x: (
                    int(x.get("order") or 0),
                    int(x.get("sort_index") or 0),
                    str(x.get("source_type") or ""),
                ),
            ):
                trait_type = str(item.get("trait_type") or "")
                if not trait_type or trait_type in seen_traits:
                    continue
                seen_traits.add(trait_type)
                dedup_items.append(item)

            max_existing_sort = max((int(item.get("sort_index") or 0) for item in dedup_items), default=0)
            next_sort = ((max_existing_sort + 9) // 10 + 1) * 10 if max_existing_sort > 0 else 10

            for item in dedup_items:
                trait_type = str(item.get("trait_type") or "")
                source_type = str(item.get("source_type") or "")
                icon = str(item.get("icon") or f"ICON_{source_type}")
                name_tag = str(item.get("name") or f"LOC_{trait_type}_NAME")
                desc_tag = str(item.get("description") or f"LOC_{trait_type}_DESCRIPTION")
                current_sort = int(item.get("sort_index") or 0)
                if current_sort <= 0:
                    current_sort = next_sort
                    next_sort += 10
                player_items_rows.append(
                    {
                        "civ_type": civ_type,
                        "leader_type": leader_type,
                        "trait_type": trait_type,
                        "item_type": source_type,
                        "sort_index": current_sort,
                        "values": [
                            f"'{self._sql_escape(row_domain)}'",
                            f"'{self._sql_escape(civ_type)}'",
                            f"'{self._sql_escape(leader_type)}'",
                            f"'{self._sql_escape(source_type)}'",
                            f"'{self._sql_escape(icon)}'",
                            f"'{self._sql_escape(name_tag)}'",
                            f"'{self._sql_escape(desc_tag)}'",
                            str(current_sort),
                        ],
                    }
                )

        dedup_players: list[dict[str, object]] = []
        seen_players: set[tuple[str, str]] = set()
        for row in players_rows:
            key = (str(row.get("civ_type") or ""), str(row.get("leader_type") or ""))
            if key in seen_players:
                continue
            seen_players.add(key)
            dedup_players.append(row)

        dedup_player_items: list[dict[str, object]] = []
        seen_player_items: set[tuple[str, str, str]] = set()
        for row in sorted(
            player_items_rows,
            key=lambda item: (
                str(item.get("civ_type") or ""),
                str(item.get("leader_type") or ""),
                int(item.get("sort_index") or 0),
                str(item.get("item_type") or item.get("trait_type") or ""),
            ),
        ):
            key = (
                str(row.get("civ_type") or ""),
                str(row.get("leader_type") or ""),
                str(row.get("item_type") or row.get("trait_type") or ""),
            )
            if key in seen_player_items:
                continue
            seen_player_items.add(key)
            dedup_player_items.append(row)

        binding_comments = self._deduplicate_rows(binding_comments)

        if not dedup_players and not dedup_player_items:
            return "-- Configs.sql\n-- 暂无可导出的配置绑定数据"

        def _civ_comment(civ_type: str) -> str:
            text = str(civ_type or "").strip()
            marker = "CIVILIZATION_"
            if text.upper().startswith(marker):
                text = text[len(marker):]
            return f"--{text},"

        def _render_row(values: list[str], trailing: str) -> list[str]:
            row_lines = ["   ("]
            total = len(values)
            for idx, value in enumerate(values):
                comma = "," if idx < total - 1 else ""
                row_lines.append(f"    {value}{comma}")
            row_lines.append(f"   ){trailing}")
            return row_lines

        lines: list[str] = []
        if dedup_players:
            lines.append(
                "INSERT INTO Players (Domain, CivilizationType, CivilizationName, CivilizationIcon, CivilizationAbilityName, CivilizationAbilityDescription, CivilizationAbilityIcon, LeaderType, LeaderName, LeaderIcon, LeaderAbilityName, LeaderAbilityDescription, LeaderAbilityIcon, Portrait, PortraitBackground, SortIndex) VALUES"
            )
            for idx, row in enumerate(dedup_players):
                civ_type = str(row.get("civ_type") or "")
                prev_civ = str(dedup_players[idx - 1].get("civ_type") or "") if idx > 0 else ""
                if idx == 0 or civ_type != prev_civ:
                    if idx > 0:
                        lines.append("")
                    lines.append(_civ_comment(civ_type))
                    lines.append("")
                values = row.get("values") if isinstance(row.get("values"), list) else []
                tail = "," if idx < len(dedup_players) - 1 else ";"
                lines.extend(_render_row([str(v) for v in values], tail))

        if dedup_player_items:
            lines.append("")
            lines.append(
                "INSERT INTO PlayerItems (Domain, CivilizationType, LeaderType, Type, Icon, Name, Description, SortIndex) VALUES"
            )
            for idx, row in enumerate(dedup_player_items):
                civ_type = str(row.get("civ_type") or "")
                prev_civ = str(dedup_player_items[idx - 1].get("civ_type") or "") if idx > 0 else ""
                if idx == 0 or civ_type != prev_civ:
                    if idx > 0:
                        lines.append("")
                    lines.append(_civ_comment(civ_type))
                values = row.get("values") if isinstance(row.get("values"), list) else []
                tail = "," if idx < len(dedup_player_items) - 1 else ";"
                lines.append(f"({', '.join(str(v) for v in values)}){tail}")

        if binding_comments:
            lines.append("")
            lines.append("-- 绑定对象预览（区域/建筑/单位/改良等）")
            lines.extend(binding_comments)

        return "\n".join(lines).rstrip()

    def _civ6proj_target_path(self) -> Path | None:
        basic = self._load_basic_info_payload_from_project() or {}
        project_info = basic.get("project_info") if isinstance(basic, dict) else {}
        if not isinstance(project_info, dict):
            return None
        raw = str(project_info.get("civ6proj_path") or "").strip()
        if not raw:
            return None
        return Path(raw)

    def _output_file_basename(self) -> str:
        basic = self._load_basic_info_payload_from_project() or {}
        project_info = basic.get("project_info") if isinstance(basic, dict) else {}
        raw_name = ""
        if isinstance(project_info, dict):
            raw_name = str(project_info.get("file_name") or "").strip()
        if not raw_name:
            civ6proj = self._civ6proj_target_path()
            raw_name = civ6proj.stem if civ6proj else "project"
        text = re.sub(r"[\\/:*?\"<>|]+", "_", raw_name)
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "project"

    @staticmethod
    def _read_previewable_text(file_path: Path) -> str:
        try:
            raw = file_path.read_bytes()
        except Exception:
            return "-- [只读][自定义] 文件读取失败"
        if b"\x00" in raw[:4096]:
            return "-- [只读][自定义] 二进制文件，预览已省略"
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="ignore")
        return "-- [只读][自定义] 外部工程文件（实时读取）\n" + text

    @staticmethod
    def _is_allowed_project_overview_file(relative_path: str) -> bool:
        rel = str(relative_path or "").replace("\\", "/").strip().lower()
        if not rel:
            return False
        allowed_exts = {".xml", ".xlp", ".artdef", ".civ6proj", ".sql", ".lua"}
        return any(rel.endswith(ext) for ext in allowed_exts)

    def _collect_external_project_files(
        self,
        *,
        root_dir: Path,
        civ6proj_name: str,
        generated_paths: set[str],
    ) -> tuple[dict[str, str], set[str], list[str]]:
        files: dict[str, str] = {}
        folders: set[str] = set()
        custom_paths: list[str] = []
        if not root_dir.exists():
            return files, folders, custom_paths

        generated_lower = {p.lower() for p in generated_paths}
        civ6proj_lower = civ6proj_name.lower()

        for path in root_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root_dir).as_posix()
            except ValueError:
                continue
            rel = rel.strip()
            if not rel:
                continue
            if not self._is_allowed_project_overview_file(rel):
                continue
            if rel.lower() == civ6proj_lower:
                continue
            if rel.lower() in generated_lower:
                continue

            files[rel] = self._read_previewable_text(path)
            custom_paths.append(rel)

            parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
            while parent:
                folders.add(parent)
                if "/" not in parent:
                    break
                parent = parent.rsplit("/", 1)[0]

        custom_paths.sort(key=lambda x: x.lower())
        return files, folders, custom_paths

    def _custom_project_files_for_actions(self) -> list[str]:
        return list(self._cached_custom_project_files)

    def _handle_refresh_project_config_from_basic(self) -> None:
        self._save_basic_info_payload_to_project(self._basic_info_workspace.export_project_payload())
        self._refresh_project_root_workspace()
        civ6proj = self._civ6proj_target_path()
        if isinstance(civ6proj, Path) and civ6proj.exists():
            try:
                self._art_workspace.merge_custom_xlp_source_from_project(
                    root_dir=civ6proj.parent,
                    relative_paths=self._cached_custom_project_files,
                )
            except Exception:
                LOGGER.exception("[Workspace] merge custom xlp source failed")

    @staticmethod
    def _normalize_loc_token(raw_name: str) -> str:
        text = str(raw_name or "").strip().upper()
        text = re.sub(r"[^A-Z0-9_]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "PROJECT"

    @staticmethod
    def _normalize_ascii_token(raw_name: str) -> str:
        text = str(raw_name or "").strip()
        text = re.sub(r"[^A-Za-z0-9_]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "project"

    @staticmethod
    def _xml_text(value: object) -> str:
        return html.escape(str(value or ""), quote=False)

    @staticmethod
    def _bool_text(value: object, default: bool = False) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        text = str(value or "").strip().lower()
        if text in {"true", "1", "yes"}:
            return "true"
        if text in {"false", "0", "no"}:
            return "false"
        return "true" if default else "false"

    def _build_action_data_xml(self, root_tag: str, entries: list[dict[str, object]]) -> str:
        lines = [f"<{root_tag}>"]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            action_type = str(entry.get("type") or "").strip() or "UpdateDatabase"
            action_id = str(entry.get("id") or "").strip() or action_type
            files = [
                str(item).strip()
                for item in (entry.get("files") if isinstance(entry.get("files"), list) else [])
                if str(item).strip()
            ]
            try:
                load_order = max(0, int(entry.get("load_order", 0)))
            except (TypeError, ValueError):
                load_order = 0

            lines.append(f"  <{action_type} id=\"{self._xml_text(action_id)}\">")
            needs_context = action_type == "AddUserInterfaces"
            if load_order > 0 or needs_context:
                lines.append("    <Properties>")
                if load_order > 0:
                    lines.append(f"      <LoadOrder>{load_order}</LoadOrder>")
                if needs_context:
                    lines.append("      <Context>InGame</Context>")
                lines.append("    </Properties>")
            for file_path in files:
                normalized_file = file_path
                if action_type == "UpdateIcons":
                    normalized_lower = file_path.lower()
                    if (normalized_lower.endswith("icons.xml") or normalized_lower.endswith("_icons.xml")) and not normalized_lower.startswith("icons/"):
                        normalized_file = f"Icons/{file_path.lstrip('/\\')}"
                lines.append(f"    <File>{self._xml_text(normalized_file)}</File>")
            lines.append(f"  </{action_type}>")
        lines.append(f"</{root_tag}>")
        return "\n".join(lines)

    def _build_civ6proj_preview(self, proj_name: str, files: dict[str, str], folders: set[str]) -> str:
        basic = self._load_basic_info_payload_from_project() or {}
        project_info = basic.get("project_info") if isinstance(basic, dict) else {}
        file_info = basic.get("file_info") if isinstance(basic, dict) else {}
        if not isinstance(project_info, dict):
            project_info = {}
        if not isinstance(file_info, dict):
            file_info = {}

        file_name_raw = str(project_info.get("file_name") or Path(proj_name).stem).strip() or Path(proj_name).stem
        file_token = self._normalize_loc_token(file_name_raw)
        loc_name = f"LOC_{file_token}_NAME"
        loc_desc = f"LOC_{file_token}_DESCRIPTION"

        mod_name_text = str(project_info.get("mod_name") or file_name_raw).strip() or file_name_raw
        description_text = str(project_info.get("description") or "").strip() or mod_name_text
        special_thanks = str(project_info.get("thanks") or "").strip()
        authors = str(project_info.get("authors") or "").strip()
        guid = str(project_info.get("guid") or "").strip()

        front_entries = file_info.get("front_end_actions") if isinstance(file_info.get("front_end_actions"), list) else []
        in_game_entries = file_info.get("in_game_actions") if isinstance(file_info.get("in_game_actions"), list) else []

        localized_text_cdata = "\n".join(
            [
                "<LocalizedText>",
                f"  <Text id=\"{loc_name}\">",
                f"    <zh_Hans_CN>{self._xml_text(mod_name_text)}</zh_Hans_CN>",
                "  </Text>",
                f"  <Text id=\"{loc_desc}\">",
                f"    <zh_Hans_CN>{self._xml_text(description_text)}</zh_Hans_CN>",
                "  </Text>",
                "</LocalizedText>",
            ]
        )

        front_end_cdata = self._build_action_data_xml("FrontEndActions", front_entries)
        in_game_cdata = self._build_action_data_xml("InGameActions", in_game_entries)

        include_paths = [
            path for path in sorted(files.keys())
            if path != proj_name
            and not path.lower().endswith(".civ6proj")
            and path != self._img_plan_relative_path()
            and path != self._textures_plan_relative_path()
            and not path.startswith("IMG/")
            and not path.startswith("Textures/")
            and not path.startswith("XLPs/")
            and not path.startswith("ArtDefs/")
        ]

        content_lines = []
        for rel_path in include_paths:
            include = rel_path.replace("/", "\\")
            content_lines.extend(
                [
                    f"    <Content Include=\"{self._xml_text(include)}\">",
                    "      <SubType>Content</SubType>",
                    "    </Content>",
                ]
            )

        folder_lines = []
        project_folders = [folder for folder in sorted(folders) if folder not in {"IMG", "Textures", "XLPs", "ArtDefs"}]
        for folder in project_folders:
            include = folder.replace("/", "\\")
            if not include.endswith("\\"):
                include = f"{include}\\"
            folder_lines.append(f"    <Folder Include=\"{self._xml_text(include)}\" />")

        source_path = self._civ6proj_target_path()
        if source_path and source_path.exists():
            try:
                document = minidom.parse(str(source_path))
                project_node = document.documentElement

                def _direct_elements(parent, tag_name: str):
                    return [
                        node
                        for node in parent.childNodes
                        if node.nodeType == node.ELEMENT_NODE and node.tagName == tag_name
                    ]

                def _first_direct_element(parent, tag_name: str):
                    for node in parent.childNodes:
                        if node.nodeType == node.ELEMENT_NODE and node.tagName == tag_name:
                            return node
                    return None

                def _read_child_text(parent, tag_name: str) -> str:
                    node = _first_direct_element(parent, tag_name)
                    if node is None:
                        return ""
                    return "".join(
                        child.data
                        for child in node.childNodes
                        if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE)
                    ).strip()

                def _set_child_text(parent, tag_name: str, value: str, *, cdata: bool = False) -> None:
                    node = _first_direct_element(parent, tag_name)
                    if node is None:
                        node = document.createElement(tag_name)
                        parent.appendChild(node)
                    while node.firstChild is not None:
                        node.removeChild(node.firstChild)
                    payload = value or ""
                    if cdata:
                        node.appendChild(document.createCDATASection(payload))
                    else:
                        node.appendChild(document.createTextNode(payload))

                property_groups = _direct_elements(project_node, "PropertyGroup")
                base_group = None
                for group in property_groups:
                    if not group.hasAttribute("Condition"):
                        base_group = group
                        break
                if base_group is None:
                    base_group = property_groups[0] if property_groups else document.createElement("PropertyGroup")
                    if not property_groups:
                        first_item_group = _first_direct_element(project_node, "ItemGroup")
                        if first_item_group is not None:
                            project_node.insertBefore(base_group, first_item_group)
                        else:
                            project_node.appendChild(base_group)

                existing_guid = _read_child_text(base_group, "Guid")
                existing_project_guid = _read_child_text(base_group, "ProjectGuid")
                guid_value = guid or existing_guid
                project_guid_value = existing_project_guid or guid_value

                _set_child_text(base_group, "Name", loc_name)
                _set_child_text(base_group, "Teaser", loc_desc)
                _set_child_text(base_group, "Description", loc_desc)
                _set_child_text(base_group, "SpecialThanks", special_thanks)
                _set_child_text(base_group, "Authors", authors)
                _set_child_text(base_group, "Guid", guid_value)
                _set_child_text(base_group, "ProjectGuid", project_guid_value)
                _set_child_text(base_group, "AffectsSavedGames", self._bool_text(project_info.get("affects_saved_games"), default=False))
                _set_child_text(base_group, "SupportsSinglePlayer", self._bool_text(project_info.get("supports_single_player"), default=True))
                _set_child_text(base_group, "SupportsMultiplayer", self._bool_text(project_info.get("supports_multiplayer"), default=True))
                _set_child_text(base_group, "SupportsHotSeat", self._bool_text(project_info.get("supports_hotseat"), default=True))
                _set_child_text(base_group, "FrontEndActionData", front_end_cdata, cdata=True)
                _set_child_text(base_group, "InGameActionData", in_game_cdata, cdata=True)
                _set_child_text(base_group, "LocalizedTextData", localized_text_cdata, cdata=True)
                _set_child_text(base_group, "AssemblyName", file_name_raw)
                _set_child_text(base_group, "RootNamespace", file_name_raw)

                item_groups = _direct_elements(project_node, "ItemGroup")

                existing_none: set[str] = set()
                existing_content: set[str] = set()
                existing_folder: set[str] = set()

                for group in item_groups:
                    for child in group.childNodes:
                        if child.nodeType != child.ELEMENT_NODE:
                            continue
                        include_value = str(child.getAttribute("Include") or "").replace("/", "\\").strip()
                        if not include_value:
                            continue
                        include_key = include_value.lower()
                        if child.tagName == "None":
                            existing_none.add(include_key)
                        elif child.tagName == "Content":
                            existing_content.add(include_key)
                        elif child.tagName == "Folder":
                            existing_folder.add(include_key)

                def _is_generated_asset_entry(tag_name: str, include_value: str) -> bool:
                    normalized = str(include_value or "").replace("/", "\\").strip().lower()
                    if not normalized:
                        return False
                    if tag_name == "Folder":
                        return (
                            normalized in {"img", "img\\"}
                            or normalized.startswith("img\\")
                            or normalized in {"textures", "textures\\"}
                            or normalized.startswith("textures\\")
                        )
                    if tag_name == "Content":
                        return normalized.startswith("img\\") or normalized.startswith("textures\\")
                    return False

                for group in item_groups:
                    removable: list[object] = []
                    for child in group.childNodes:
                        if child.nodeType != child.ELEMENT_NODE:
                            continue
                        tag_name = child.tagName
                        if tag_name not in {"Content", "Folder"}:
                            continue
                        include_value = str(child.getAttribute("Include") or "")
                        if _is_generated_asset_entry(tag_name, include_value):
                            removable.append(child)
                    for child in removable:
                        group.removeChild(child)

                def _find_group_with_tag(tag_name: str):
                    for group in item_groups:
                        for child in group.childNodes:
                            if child.nodeType == child.ELEMENT_NODE and child.tagName == tag_name:
                                return group
                    return None

                def _ensure_group(tag_name: str):
                    found = _find_group_with_tag(tag_name)
                    if found is not None:
                        return found
                    new_group = document.createElement("ItemGroup")
                    import_node = _first_direct_element(project_node, "Import")
                    if import_node is not None:
                        project_node.insertBefore(new_group, import_node)
                    else:
                        project_node.appendChild(new_group)
                    item_groups.append(new_group)
                    return new_group

                none_group = _ensure_group("None")
                content_group = _ensure_group("Content")
                folder_group = _ensure_group("Folder")

                art_xml_include_name = f"{Path(proj_name).stem}.Art.xml"
                none_include = art_xml_include_name.replace("/", "\\")
                if none_include.lower() not in existing_none:
                    none_node = document.createElement("None")
                    none_node.setAttribute("Include", none_include)
                    none_group.appendChild(none_node)
                    existing_none.add(none_include.lower())

                for rel_path in include_paths:
                    include = rel_path.replace("/", "\\")
                    include_key = include.lower()
                    if include_key in existing_content:
                        continue
                    content_node = document.createElement("Content")
                    content_node.setAttribute("Include", include)
                    subtype_node = document.createElement("SubType")
                    subtype_node.appendChild(document.createTextNode("Content"))
                    content_node.appendChild(subtype_node)
                    content_group.appendChild(content_node)
                    existing_content.add(include_key)

                for folder in project_folders:
                    include = folder.replace("/", "\\")
                    if not include.endswith("\\"):
                        include = f"{include}\\"
                    include_key = include.lower()
                    if include_key in existing_folder:
                        continue
                    folder_node = document.createElement("Folder")
                    folder_node.setAttribute("Include", include)
                    folder_group.appendChild(folder_node)
                    existing_folder.add(include_key)

                pretty = document.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
                pretty_lines = [line for line in pretty.splitlines() if line.strip()]
                return "\n".join(pretty_lines) + "\n"
            except Exception:
                LOGGER.exception("Failed to build civ6proj via XML DOM path, fallback to plain text emitter")

        lines = [
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
            "<Project ToolsVersion=\"12.0\" DefaultTargets=\"Default\" xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\">",
            "  <PropertyGroup>",
            "    <Configuration Condition=\" '$(Configuration)' == '' \">Default</Configuration>",
            f"    <Name>{loc_name}</Name>",
            f"    <Guid>{self._xml_text(guid)}</Guid>",
            f"    <ProjectGuid>{self._xml_text(guid)}</ProjectGuid>",
            "    <ModVersion>1</ModVersion>",
            f"    <Teaser>{loc_desc}</Teaser>",
            f"    <Description>{loc_desc}</Description>",
            f"    <Authors>{self._xml_text(authors)}</Authors>",
            f"    <SpecialThanks>{self._xml_text(special_thanks)}</SpecialThanks>",
            f"    <AffectsSavedGames>{self._bool_text(project_info.get('affects_saved_games'), default=False)}</AffectsSavedGames>",
            f"    <SupportsSinglePlayer>{self._bool_text(project_info.get('supports_single_player'), default=True)}</SupportsSinglePlayer>",
            f"    <SupportsMultiplayer>{self._bool_text(project_info.get('supports_multiplayer'), default=True)}</SupportsMultiplayer>",
            f"    <SupportsHotSeat>{self._bool_text(project_info.get('supports_hotseat'), default=True)}</SupportsHotSeat>",
            "    <CompatibleVersions>1.2,2.0</CompatibleVersions>",
            "    <AssociationData><![CDATA[<Associations></Associations>]]></AssociationData>",
            f"    <FrontEndActionData><![CDATA[{front_end_cdata}]]></FrontEndActionData>",
            f"    <InGameActionData><![CDATA[{in_game_cdata}]]></InGameActionData>",
            f"    <LocalizedTextData><![CDATA[{localized_text_cdata}]]></LocalizedTextData>",
            f"    <AssemblyName>{self._xml_text(file_name_raw)}</AssemblyName>",
            f"    <RootNamespace>{self._xml_text(file_name_raw)}</RootNamespace>",
            "  </PropertyGroup>",
            "  <PropertyGroup Condition=\" '$(Configuration)' == 'Default' \">",
            "    <OutputPath>.</OutputPath>",
            "  </PropertyGroup>",
            "  <ItemGroup>",
            f"    <None Include=\"{self._xml_text(Path(proj_name).stem)}.Art.xml\" />",
            "  </ItemGroup>",
            "  <ItemGroup>",
            *content_lines,
            "  </ItemGroup>",
            "  <ItemGroup>",
            *folder_lines,
            "  </ItemGroup>",
            "  <Import Project=\"$(MSBuildLocalExtensionPath)Civ6.targets\" />",
            "</Project>",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _img_plan_relative_path() -> str:
        return "IMG/图片生成清单.txt"

    @staticmethod
    def _textures_plan_relative_path() -> str:
        return "Textures/纹理生成清单.txt"

    @staticmethod
    def _indent_xml(root: ElementTree.Element) -> str:
        try:
            from xml.etree.ElementTree import indent as et_indent

            et_indent(root, space="\t")
        except Exception:
            def _indent(elem: ElementTree.Element, level: int = 0) -> None:
                i = "\n" + ("\t" * level)
                if len(elem):
                    if not elem.text or not elem.text.strip():
                        elem.text = i + "\t"
                    for child in elem:
                        _indent(child, level + 1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                elif level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

            _indent(root)
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" + ElementTree.tostring(root, encoding="utf-8").decode("utf-8") + "\n"

    def _build_ui_texture_xlp_xml(
        self,
        *,
        package_name: str,
        entry_ids: list[str],
        object_name_overrides: dict[str, str] | None = None,
    ) -> str:
        root = ElementTree.Element("AssetObjects..XLP")
        ver = ElementTree.SubElement(root, "m_Version")
        ElementTree.SubElement(ver, "major").text = "1"
        ElementTree.SubElement(ver, "minor").text = "0"
        ElementTree.SubElement(ver, "build").text = "0"
        ElementTree.SubElement(ver, "revision").text = "0"
        ElementTree.SubElement(root, "m_ClassName", {"text": "UITexture"})
        ElementTree.SubElement(root, "m_PackageName", {"text": str(package_name)})
        entries = ElementTree.SubElement(root, "m_Entries")
        overrides = object_name_overrides if isinstance(object_name_overrides, dict) else {}
        for entry_id in entry_ids:
            elem = ElementTree.SubElement(entries, "Element")
            ElementTree.SubElement(elem, "m_EntryID", {"text": entry_id})
            object_name = str(overrides.get(entry_id) or entry_id).strip() or entry_id
            ElementTree.SubElement(elem, "m_ObjectName", {"text": object_name})
        allowed = ElementTree.SubElement(root, "m_AllowedPlatforms")
        for platform in ["WINDOWS", "IOS", "LINUX", "XBONE", "PS4", "SWITCH", "STADIA", "MACOS"]:
            ElementTree.SubElement(allowed, "Element").text = platform
        return self._indent_xml(root)

    @staticmethod
    def _normalize_png_filename(name: str) -> str:
        clean = str(name or "").strip().replace("\\", "/")
        if not clean:
            return ""
        if "/" in clean:
            clean = clean.split("/")[-1]
        if not clean.lower().endswith(".png"):
            clean = f"{clean}.png"
        return clean

    def _iter_section_entries(self, section: str) -> list[dict[str, object]]:
        data = self._project.sections.get(section)
        if not isinstance(data, list):
            return []
        return [entry for entry in data if isinstance(entry, dict)]

    def _collect_icon_source_states(self) -> dict[str, dict[str, object]]:
        output: dict[str, dict[str, object]] = {}

        def _store(icon_name: str, payload: object) -> None:
            name = str(icon_name or "").strip()
            if not name:
                return
            if not isinstance(payload, dict):
                return
            path = str(payload.get("path") or "").strip()
            if not path:
                return
            output[name] = payload

        section_type_fallbacks: dict[str, tuple[str, ...]] = {
            "总督": ("GovernorType",),
            "政策卡": ("PolicyType",),
            "项目": ("ProjectType",),
            "信仰": ("BeliefType",),
        }

        def _resolve_type_name(section: str, entry: dict[str, object]) -> str:
            for key in ("type", *section_type_fallbacks.get(section, ())):
                value = str(entry.get(key) or "").strip()
                if value:
                    return value
            return ""

        base_sections = ["文明", "领袖", "区域", "建筑", "改良设施", "项目", "信仰", "总督"]
        for section in base_sections:
            for entry in self._iter_section_entries(section):
                type_name = _resolve_type_name(section, entry)
                if not type_name:
                    continue
                images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
                icon_name = str(images.get("icon_name") or entry.get("icon_image_name") or f"ICON_{type_name}").strip()
                _store(icon_name, images.get("icon"))
                if section == "总督":
                    fill_icon_name = str(
                        images.get("icon_fill_name")
                        or entry.get("icon_fill_image_name")
                        or (f"{icon_name}_FILL" if icon_name else "")
                    ).strip()
                    slot_icon_name = str(
                        images.get("icon_slot_name")
                        or entry.get("icon_slot_image_name")
                        or (f"{icon_name}_SLOT" if icon_name else "")
                    ).strip()
                    _store(fill_icon_name, images.get("icon_fill"))
                    _store(slot_icon_name, images.get("icon_slot"))

        for entry in self._iter_section_entries("单位"):
            type_name = str(entry.get("type") or "").strip()
            if not type_name:
                continue
            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
            _store(str(images.get("icon_name") or entry.get("icon_image_name") or f"ICON_{type_name}"), images.get("icon"))
            _store(str(images.get("portrait_name") or entry.get("portrait_image_name") or f"ICON_{type_name}_PORTRAIT"), images.get("portrait"))

        for entry in self._iter_section_entries("伟人"):
            unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
            unit_type = str(unit_data.get("UnitType") or entry.get("unit_type") or "").strip()
            if not unit_type:
                continue
            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
            _store(str(images.get("unit_icon_name") or f"ICON_{unit_type}"), images.get("unit_icon"))
            _store(str(images.get("unit_portrait_name") or f"ICON_{unit_type}_PORTRAIT"), images.get("unit_portrait"))

        return output

    def _collect_icons_atlas_image_plans(self) -> list[dict[str, object]]:
        plans: list[dict[str, object]] = []
        source_map = self._collect_icon_source_states()
        art_groups = self._art_workspace.export_preview_file_groups()
        icons_files = art_groups.get("Icons", [])
        if not icons_files:
            return plans

        icons_xml = ""
        for filename, content in icons_files:
            if str(filename).strip().lower() == "icons.xml":
                icons_xml = str(content or "")
                break
        if not icons_xml.strip():
            return plans

        try:
            root = ElementTree.fromstring(icons_xml)
        except ElementTree.ParseError:
            return plans

        for row in root.findall("./IconTextureAtlases/Row"):
            filename = str(row.attrib.get("Filename") or "").strip()
            icon_size_raw = str(row.attrib.get("IconSize") or "0").strip()
            try:
                icon_size = max(1, int(icon_size_raw))
            except ValueError:
                icon_size = 0
            if not filename or icon_size <= 0:
                continue
            base_icon_name = re.sub(r"_\d+$", "", filename)
            state = source_map.get(base_icon_name, {})
            source_path = str(state.get("path") or "").strip() if isinstance(state, dict) else ""
            plans.append(
                {
                    "relative_path": f"IMG/{filename}.png",
                    "target_width": icon_size,
                    "target_height": icon_size,
                    "source_state": state if isinstance(state, dict) else {},
                    "source_path": source_path,
                    "category": "atlas",
                }
            )
        return plans

    def _collect_leader_direct_image_plans(self) -> list[dict[str, object]]:
        plans: list[dict[str, object]] = []
        specs = [
            ("foreground_image_name", "foreground", 960, 960),
            ("background_image_name", "background", 1920, 960),
            ("diplo_foreground_image_name", "diplo_foreground", 960, 960),
            ("diplo_background_image_name", "diplo_background", 1960, 1600),
            ("select_foreground_image_name", "select_foreground", 512, 1024),
            ("select_background_image_name", "select_background", 384, 1024),
        ]
        for entry in self._iter_section_entries("领袖"):
            leader_type = str(entry.get("type") or "").strip()
            short_type = leader_type[7:] if leader_type.startswith("LEADER_") else leader_type
            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}

            fallback_names = {
                "foreground_image_name": f"{leader_type}_NEUTRAL" if leader_type else "",
                "background_image_name": f"{leader_type}_BACKGROUND" if leader_type else "",
                "diplo_foreground_image_name": f"FALLBACK_NEUTRAL_{short_type}" if short_type else "",
                "diplo_background_image_name": f"{short_type}_1" if short_type else "",
                "select_foreground_image_name": f"PORTRAIT_{leader_type}.png" if leader_type else "",
                "select_background_image_name": f"PORTRAIT_BACKGROUND_{leader_type}.png" if leader_type else "",
            }

            for name_key, image_key, width, height in specs:
                raw_name_value = str(entry.get(name_key) or fallback_names.get(name_key) or "")
                file_names = [
                    self._normalize_png_filename(part)
                    for part in raw_name_value.split(",")
                    if self._normalize_png_filename(part)
                ]
                if not file_names:
                    continue
                state = images.get(image_key) if isinstance(images.get(image_key), dict) else {}
                source_path = str(state.get("path") or "").strip() if isinstance(state, dict) else ""
                for file_name in file_names:
                    plans.append(
                        {
                            "relative_path": f"IMG/{file_name}",
                            "target_width": int(width),
                            "target_height": int(height),
                            "source_state": state if isinstance(state, dict) else {},
                            "source_path": source_path,
                            "category": "leader_final",
                        }
                    )
        return plans

    def _collect_governor_direct_image_plans(self) -> list[dict[str, object]]:
        plans: list[dict[str, object]] = []
        for entry in self._iter_section_entries("总督"):
            governor_type = str(entry.get("GovernorType") or entry.get("type") or "").strip()
            if not governor_type:
                continue

            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}

            normal_name_raw = str(entry.get("Image") or entry.get("PortraitImage") or f"{governor_type}_NORMAL").strip()
            selected_name_raw = str(entry.get("PortraitImageSelected") or f"{governor_type}_SELECTED").strip()

            normal_files = [
                self._normalize_png_filename(part)
                for part in normal_name_raw.split(",")
                if self._normalize_png_filename(part)
            ]
            selected_files = [
                self._normalize_png_filename(part)
                for part in selected_name_raw.split(",")
                if self._normalize_png_filename(part)
            ]

            normal_state = images.get("normal") if isinstance(images.get("normal"), dict) else {}
            normal_source_path = str(normal_state.get("path") or "").strip() if isinstance(normal_state, dict) else ""
            for file_name in normal_files:
                plans.append(
                    {
                        "relative_path": f"IMG/{file_name}",
                        "target_width": 206,
                        "target_height": 208,
                        "source_state": normal_state if isinstance(normal_state, dict) else {},
                        "source_path": normal_source_path,
                        "category": "governor_final",
                    }
                )

            selected_state = images.get("selected") if isinstance(images.get("selected"), dict) else {}
            selected_source_path = str(selected_state.get("path") or "").strip() if isinstance(selected_state, dict) else ""
            for file_name in selected_files:
                plans.append(
                    {
                        "relative_path": f"IMG/{file_name}",
                        "target_width": 326,
                        "target_height": 339,
                        "source_state": selected_state if isinstance(selected_state, dict) else {},
                        "source_path": selected_source_path,
                        "category": "governor_final",
                    }
                )

        return plans

    def _build_img_output_plan(self) -> list[dict[str, object]]:
        merged: dict[str, dict[str, object]] = {}
        for plan in (
            self._collect_icons_atlas_image_plans()
            + self._collect_leader_direct_image_plans()
            + self._collect_governor_direct_image_plans()
            + self._collect_moment_image_plans()
        ):
            rel_path = str(plan.get("relative_path") or "").replace("\\", "/").strip()
            if not rel_path:
                continue
            previous = merged.get(rel_path)
            current_source = str(plan.get("source_path") or "").strip()
            if previous is None:
                merged[rel_path] = plan
                continue
            previous_source = str(previous.get("source_path") or "").strip()
            if (not previous_source) and current_source:
                merged[rel_path] = plan
        return [merged[key] for key in sorted(merged.keys())]

    def _build_img_plan_table_text(self) -> str:
        plans = self._build_img_output_plan()
        lines = [
            "-- IMG 生成预览清单（仅预览；点击生成后才会输出图片）",
            "",
        ]
        headers = ["输出文件", "尺寸", "来源图片", "说明"]
        rows: list[list[str]] = []
        for plan in plans:
            rel_path = str(plan.get("relative_path") or "")
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            source_path = str(plan.get("source_path") or "").strip()
            source_name = Path(source_path).name if source_path else "（未设置来源）"
            category = str(plan.get("category") or "")
            if category == "atlas":
                note = "图标多尺寸输出"
            elif category == "moment":
                note = "历史时刻插画(456×332)"
            else:
                note = "最终尺寸图"
            rows.append([rel_path, f"{width}x{height}", source_name, note])
        if not rows:
            rows.append(["（无）", "-", "-", "当前没有可生成图片"])

        col_widths = [len(title) for title in headers]
        for row in rows:
            for idx, value in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(str(value)))

        def _sep(char: str = "-") -> str:
            return "+" + "+".join(char * (w + 2) for w in col_widths) + "+"

        def _row(values: list[str]) -> str:
            cells = [f" {str(values[i]).ljust(col_widths[i])} " for i in range(len(col_widths))]
            return "|" + "|".join(cells) + "|"

        lines.append(_sep("-"))
        lines.append(_row(headers))
        lines.append(_sep("="))
        for row in rows:
            lines.append(_row(row))
            lines.append(_sep("-"))

        configured_sources = sum(1 for row in rows if row[2] != "（未设置来源）")
        LOGGER.info("[IMGPlanPreview] rows=%d configured_sources=%d", len(rows), configured_sources)
        lines.append("")
        return "\n".join(lines)

    def _build_textures_output_plan(self) -> list[dict[str, object]]:
        """Textures 输出计划（DDS+TEX）。

        当前覆盖：
        - UI 图标纹理（IconTextureAtlases 对应的 PNG）：输出为 UISliceTexture（无 mip）
        - 总督最终图（NORMAL/SELECTED）：输出为 UISliceTexture（无 mip）
        - 历史时刻（Moments）插画：导入图模式下输出为 UISliceTexture（无 mip）
        - LeaderFallback：输出为 TextureAsset（保留 mip）
        """

        plans: list[dict[str, object]] = []

        # 1) UI 图标纹理（IconTextureAtlases）：跟随 IMG/ 图标多尺寸输出
        for plan in self._collect_icons_atlas_image_plans():
            rel_path = str(plan.get("relative_path") or "").replace("\\", "/").strip()
            if not rel_path.lower().startswith("img/") or not rel_path.lower().endswith(".png"):
                continue
            source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
            source_path = str(plan.get("source_path") or "").strip()
            if not source_path or not str(source_state.get("path") or "").strip():
                continue
            filename = Path(rel_path).name
            name = Path(filename).stem
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            if not name or width <= 0 or height <= 0:
                continue
            plans.append(
                {
                    "name": name,
                    "target_width": width,
                    "target_height": height,
                    "source_state": source_state,
                    "source_path": source_path,
                    "category": "ui_slice",
                }
            )

        # 2) 领袖最终图（前景/背景/外交/选择界面）：跟随 IMG/ 最终尺寸输出
        for plan in self._collect_leader_direct_image_plans():
            rel_path = str(plan.get("relative_path") or "").replace("\\", "/").strip()
            if not rel_path.lower().startswith("img/") or not rel_path.lower().endswith(".png"):
                continue
            source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
            source_path = str(plan.get("source_path") or "").strip()
            if not source_path or not str(source_state.get("path") or "").strip():
                continue
            filename = Path(rel_path).name
            name = Path(filename).stem
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            if not name or width <= 0 or height <= 0:
                continue
            plans.append(
                {
                    "name": name,
                    "target_width": width,
                    "target_height": height,
                    "source_state": source_state,
                    "source_path": source_path,
                    "category": "ui_slice",
                }
            )

        # 3) 总督最终图（NORMAL/SELECTED）：跟随 IMG/ 最终尺寸输出
        for plan in self._collect_governor_direct_image_plans():
            rel_path = str(plan.get("relative_path") or "").replace("\\", "/").strip()
            if not rel_path.lower().startswith("img/") or not rel_path.lower().endswith(".png"):
                continue
            source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
            source_path = str(plan.get("source_path") or "").strip()
            if not source_path or not str(source_state.get("path") or "").strip():
                continue
            filename = Path(rel_path).name
            name = Path(filename).stem
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            if not name or width <= 0 or height <= 0:
                continue
            plans.append(
                {
                    "name": name,
                    "target_width": width,
                    "target_height": height,
                    "source_state": source_state,
                    "source_path": source_path,
                    "category": "ui_slice",
                }
            )

        # 4) Moments（历史时刻插画）：导入图模式的 456x332，采用 UISliceTexture（无 mip）
        for plan in self._collect_moment_image_plans():
            rel_path = str(plan.get("relative_path") or "").replace("\\", "/").strip()
            if not rel_path.lower().startswith("img/") or not rel_path.lower().endswith(".png"):
                continue
            filename = Path(rel_path).name
            name = Path(filename).stem
            if not name:
                continue
            source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
            source_path = str(plan.get("source_path") or "").strip()
            plans.append(
                {
                    "name": name,
                    "target_width": 456,
                    "target_height": 332,
                    "source_state": source_state,
                    "source_path": source_path,
                    "category": "ui_slice",
                }
            )

        # 5) LeaderFallback（领袖外交前景 fallback）
        for entry in self._iter_section_entries("领袖"):
            leader_type = str(entry.get("type") or "").strip()
            if not leader_type:
                continue
            short_type = leader_type[7:] if leader_type.startswith("LEADER_") else leader_type
            if not short_type:
                continue
            name = f"FALLBACK_NEUTRAL_{short_type}"
            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
            state = images.get("diplo_foreground") if isinstance(images.get("diplo_foreground"), dict) else {}
            source_path = str(state.get("path") or "").strip() if isinstance(state, dict) else ""
            if not source_path:
                continue
            plans.append(
                {
                    "name": name,
                    "target_width": 960,
                    "target_height": 960,
                    "source_state": state if isinstance(state, dict) else {},
                    "source_path": source_path,
                    "category": "leader_fallback",
                }
            )

        dedup: dict[str, dict[str, object]] = {}
        for plan in plans:
            key = str(plan.get("name") or "").strip()
            if not key:
                continue
            dedup[key] = plan
        return [dedup[name] for name in sorted(dedup.keys())]

    def _build_textures_plan_table_text(self) -> str:
        plans = self._build_textures_output_plan()
        lines = [
            "-- Textures 纹理生成预览清单（仅预览；点击生成后才会输出 .dds/.tex）",
            "-- 当前覆盖：UI 图标多尺寸 / 总督最终图 / 历史时刻插画 / LeaderFallback",
            "",
        ]
        headers = ["输出文件", "尺寸", "来源图片", "说明"]
        rows: list[list[str]] = []
        for plan in plans:
            name = str(plan.get("name") or "").strip()
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            source_path = str(plan.get("source_path") or "").strip()
            source_name = Path(source_path).name if source_path else "（未设置来源）"
            rows.append([f"Textures/{name}.dds", f"{width}x{height}", source_name, f"同时生成 Textures/{name}.tex"])
        if not rows:
            rows.append(["（无）", "-", "-", "当前没有可生成纹理"])

        col_widths = [len(title) for title in headers]
        for row in rows:
            for idx, value in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(str(value)))

        def _sep(char: str = "-") -> str:
            return "+" + "+".join(char * (w + 2) for w in col_widths) + "+"

        def _row(values: list[str]) -> str:
            cells = [f" {str(values[i]).ljust(col_widths[i])} " for i in range(len(col_widths))]
            return "|" + "|".join(cells) + "|"

        lines.append(_sep("-"))
        lines.append(_row(headers))
        lines.append(_sep("="))
        for row in rows:
            lines.append(_row(row))
            lines.append(_sep("-"))

        LOGGER.info("[TexturesPlanPreview] rows=%d", len(rows))
        lines.append("")
        return "\n".join(lines)

    def _render_state_image(self, state: dict[str, object], target_size: tuple[int, int]) -> QImage | None:
        path = str(state.get("path") or "").strip()
        if not path:
            return None
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None

        target_w = max(1, int(target_size[0]))
        target_h = max(1, int(target_size[1]))

        circle_crop = bool(state.get("circle_crop", False))
        add_black_border = bool(state.get("add_black_border", False))

        def _circle_inset_px(w: int, h: int) -> float:
            target_min = float(max(1, min(int(w), int(h))))
            return float(round(target_min * 10.0 / 256.0))

        def _border_px(w: int, h: int) -> float:
            target_min = float(max(1, min(int(w), int(h))))
            return float(max(1.0, round(target_min * 3.0 / 256.0)))

        try:
            base_w = int(state.get("canvas_width") or 0)
        except (TypeError, ValueError):
            base_w = 0
        try:
            base_h = int(state.get("canvas_height") or 0)
        except (TypeError, ValueError):
            base_h = 0

        if base_w <= 0 or base_h <= 0:
            try:
                preview_max_w = max(96, int(state.get("preview_max_width") or 320))
            except (TypeError, ValueError):
                preview_max_w = 320
            try:
                preview_max_h = max(96, int(state.get("preview_max_height") or 240))
            except (TypeError, ValueError):
                preview_max_h = 240
            ratio = target_w / target_h if target_h > 0 else 1.0
            if ratio >= 1.0:
                base_w = preview_max_w
                base_h = max(96, int(round(base_w / ratio)))
                if base_h > preview_max_h:
                    base_h = preview_max_h
                    base_w = max(96, int(round(base_h * ratio)))
            else:
                base_h = preview_max_h
                base_w = max(96, int(round(base_h * ratio)))
                if base_w > preview_max_w:
                    base_w = preview_max_w
                    base_h = max(96, int(round(base_w / ratio)))

        base_w = max(1, base_w)
        base_h = max(1, base_h)

        try:
            scale = float(state.get("scale") if state.get("scale") is not None else 1.0)
        except (TypeError, ValueError):
            scale = 1.0
        try:
            offset_x = float(state.get("offset_x") if state.get("offset_x") is not None else 0.0)
        except (TypeError, ValueError):
            offset_x = 0.0
        try:
            offset_y = float(state.get("offset_y") if state.get("offset_y") is not None else 0.0)
        except (TypeError, ValueError):
            offset_y = 0.0

        pix_w = max(1, pixmap.width())
        pix_h = max(1, pixmap.height())
        min_scale = max(base_w / pix_w, base_h / pix_h)
        if scale < min_scale:
            scale = min_scale
            offset_x = (base_w - pix_w * scale) / 2.0
            offset_y = (base_h - pix_h * scale) / 2.0

        ratio_x = target_w / base_w
        ratio_y = target_h / base_h

        image = QImage(target_w, target_h, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if add_black_border:
            inset = _circle_inset_px(target_w, target_h)
            outer_radius = max(1.0, min(float(target_w), float(target_h)) / 2.0 - inset)
            border = _border_px(target_w, target_h)
            inner_radius = max(0.0, outer_radius - border)
            cx = float(target_w) / 2.0
            cy = float(target_h) / 2.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.GlobalColor.black)
            painter.drawEllipse(QRectF(cx - outer_radius, cy - outer_radius, outer_radius * 2.0, outer_radius * 2.0))
            if inner_radius > 0.0:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.drawEllipse(QRectF(cx - inner_radius, cy - inner_radius, inner_radius * 2.0, inner_radius * 2.0))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if circle_crop:
            inset = _circle_inset_px(target_w, target_h)
            outer_radius = max(1.0, min(float(target_w), float(target_h)) / 2.0 - inset)
            border = _border_px(target_w, target_h) if add_black_border else 0.0
            clip_radius = max(1.0, outer_radius - border)
            cx = float(target_w) / 2.0
            cy = float(target_h) / 2.0
            path = QPainterPath()
            path.addEllipse(cx - clip_radius, cy - clip_radius, clip_radius * 2.0, clip_radius * 2.0)
            painter.setClipPath(path)

        draw_x = offset_x * ratio_x
        draw_y = offset_y * ratio_y
        draw_w = pixmap.width() * scale * ratio_x
        draw_h = pixmap.height() * scale * ratio_y
        painter.drawPixmap(int(round(draw_x)), int(round(draw_y)), int(round(draw_w)), int(round(draw_h)), pixmap)
        painter.end()
        return image

    @staticmethod
    def _qimage_to_rgba_bytes_tight(image: QImage) -> bytes:
        img = image.convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = img.bits()
        ptr.setsize(img.sizeInBytes())
        raw = bytes(ptr)
        row_bytes = img.width() * 4
        stride = img.bytesPerLine()
        if stride == row_bytes:
            return raw
        return b"".join(raw[y * stride : y * stride + row_bytes] for y in range(img.height()))

    @staticmethod
    def _encode_dds_rgba8_with_mips(base: QImage, *, min_mip_size: int = 3) -> tuple[bytes, int]:
        base_rgba = base.convertToFormat(QImage.Format.Format_RGBA8888)
        mip_images: list[QImage] = [base_rgba]
        while mip_images[-1].width() > min_mip_size and mip_images[-1].height() > min_mip_size:
            prev = mip_images[-1]
            next_w = max(1, prev.width() // 2)
            next_h = max(1, prev.height() // 2)
            scaled = prev.scaled(
                next_w,
                next_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ).convertToFormat(QImage.Format.Format_RGBA8888)
            mip_images.append(scaled)

        width = int(base_rgba.width())
        height = int(base_rgba.height())
        mip_count = len(mip_images)

        DDS_MAGIC = b"DDS "
        DDSD_CAPS = 0x1
        DDSD_HEIGHT = 0x2
        DDSD_WIDTH = 0x4
        DDSD_PITCH = 0x8
        DDSD_PIXELFORMAT = 0x1000
        DDSD_MIPMAPCOUNT = 0x20000
        DDPF_FOURCC = 0x4
        DDSCAPS_TEXTURE = 0x1000
        DDSCAPS_COMPLEX = 0x8
        DDSCAPS_MIPMAP = 0x400000

        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH
        if mip_count > 1:
            flags |= DDSD_MIPMAPCOUNT

        caps1 = DDSCAPS_TEXTURE
        if mip_count > 1:
            caps1 |= DDSCAPS_COMPLEX | DDSCAPS_MIPMAP

        pitch = width * 4

        header = struct.pack(
            "<I"  # dwSize
            "I"  # dwFlags
            "I"  # dwHeight
            "I"  # dwWidth
            "I"  # dwPitchOrLinearSize
            "I"  # dwDepth
            "I"  # dwMipMapCount
            "11I"  # dwReserved1
            "I"  # ddspf.dwSize
            "I"  # ddspf.dwFlags
            "4s"  # ddspf.dwFourCC
            "I"  # ddspf.dwRGBBitCount
            "I"  # ddspf.dwRBitMask
            "I"  # ddspf.dwGBitMask
            "I"  # ddspf.dwBBitMask
            "I"  # ddspf.dwABitMask
            "I"  # dwCaps
            "I"  # dwCaps2
            "I"  # dwCaps3
            "I"  # dwCaps4
            "I",  # dwReserved2
            124,
            flags,
            height,
            width,
            pitch,
            0,
            mip_count,
            *([0] * 11),
            32,
            DDPF_FOURCC,
            b"DX10",
            0,
            0,
            0,
            0,
            0,
            caps1,
            0,
            0,
            0,
            0,
        )

        DXGI_FORMAT_R8G8B8A8_UNORM = 28
        DDS_DIMENSION_TEXTURE2D = 3
        header_dx10 = struct.pack(
            "<IIIII",
            DXGI_FORMAT_R8G8B8A8_UNORM,
            DDS_DIMENSION_TEXTURE2D,
            0,
            1,
            0,
        )

        payload = bytearray()
        payload.extend(DDS_MAGIC)
        payload.extend(header)
        payload.extend(header_dx10)
        for img in mip_images:
            payload.extend(WorkspacePage._qimage_to_rgba_bytes_tight(img))
        return bytes(payload), mip_count

    def _build_leader_fallback_tex_xml(
        self,
        *,
        name: str,
        width: int,
        height: int,
        mip_levels: int,
        project_folder_name: str,
        exported_time: int,
    ) -> str:
        safe_name = str(name or "").strip()
        safe_png = f"{safe_name}.png"
        safe_dds = f"{safe_name}.dds"
        project_folder = str(project_folder_name or "").strip()
        source_path = f"//civ6/main/{project_folder}\\IMG\\{safe_png}" if project_folder else f"//civ6/main/IMG\\{safe_png}"
        mip_count = max(1, int(mip_levels or 1))
        lines = [
            '<?xml version="1.0" encoding="UTF-8" ?>',
            "<AssetObjects..TextureInstance>",
            "\t<m_ExportSettings>",
            "\t\t<ePixelformat>PF_R8G8B8A8_UNORM</ePixelformat>",
            "\t\t<eFilterType>FT_BOX</eFilterType>",
            "\t\t<bUseMips>true</bUseMips>",
            "\t\t<iNumManualMips>0</iNumManualMips>",
            "\t\t<bCompleteMipChain>true</bCompleteMipChain>",
            "\t\t<fValueClampMin>0.000000</fValueClampMin>",
            "\t\t<fValueClampMax>1.000000</fValueClampMax>",
            "\t\t<fSupportScale>1.000000</fSupportScale>",
            "\t\t<fGammaIn>2.200000</fGammaIn>",
            "\t\t<fGammaOut>2.200000</fGammaOut>",
            "\t\t<iSlabWidth>0</iSlabWidth>",
            "\t\t<iSlabHeight>0</iSlabHeight>",
            "\t\t<iColorKeyX>64</iColorKeyX>",
            "\t\t<iColorKeyY>64</iColorKeyY>",
            "\t\t<iColorKeyZ>64</iColorKeyZ>",
            "\t\t<eExportMode>TEXTURE_2D</eExportMode>",
            "\t\t<bSampleFromTopLayer>false</bSampleFromTopLayer>",
            "\t</m_ExportSettings>",
            "\t<m_CookParams>",
            "\t\t<m_Values/>",
            "\t</m_CookParams>",
            "\t<m_Version>",
            "\t\t<major>1</major>",
            "\t\t<minor>0</minor>",
            "\t\t<build>0</build>",
            "\t\t<revision>0</revision>",
            "\t</m_Version>",
            f"\t<m_Height>{int(height)}</m_Height>",
            f"\t<m_Width>{int(width)}</m_Width>",
            "\t<m_Depth>1</m_Depth>",
            f"\t<m_NumMipMaps>{mip_count}</m_NumMipMaps>",
            f"\t<m_SourceFilePath text=\"{self._xml_text(source_path)}\"/>",
            "\t<m_SourceObjectName text=\"\"/>",
            "\t<m_ImportedTime>0</m_ImportedTime>",
            f"\t<m_ExportedTime>{int(exported_time)}</m_ExportedTime>",
            "\t<m_ClassName text=\"Leader_Fallback\"/>",
            "\t<m_DataFiles>",
            "\t\t<Element>",
            "\t\t\t<m_ID text=\"DDS\"/>",
            f"\t\t\t<m_RelativePath text=\"{self._xml_text(safe_dds)}\"/>",
            "\t\t</Element>",
            "\t</m_DataFiles>",
            f"\t<m_Name text=\"{self._xml_text(safe_name)}\"/>",
            "\t<m_Description text=\"\"/>",
            "\t<m_Tags>",
            "\t\t<Element text=\"Leader_Fallback\"/>",
            "\t\t<Element text=\"Leader\"/>",
            "\t\t<Element text=\"Fallback\"/>",
            "\t</m_Tags>",
            "</AssetObjects..TextureInstance>",
            "",
        ]
        return "\n".join(lines)

    def _build_ui_slice_tex_xml(self, *, name: str, width: int, height: int, project_folder_name: str, exported_time: int) -> str:
        safe_name = str(name or "").strip()
        safe_png = f"{safe_name}.png"
        safe_dds = f"{safe_name}.dds"
        project_folder = str(project_folder_name or "").strip()
        source_path = f"//civ6/main/{project_folder}\\IMG\\{safe_png}" if project_folder else f"//civ6/main/IMG\\{safe_png}"
        lines = [
            '<?xml version="1.0" encoding="UTF-8" ?>',
            "<AssetObjects..TextureInstance>",
            "\t<m_ExportSettings>",
            "\t\t<ePixelformat>PF_R8G8B8A8_UNORM</ePixelformat>",
            "\t\t<eFilterType>FT_BOX</eFilterType>",
            "\t\t<bUseMips>false</bUseMips>",
            "\t\t<iNumManualMips>0</iNumManualMips>",
            "\t\t<bCompleteMipChain>true</bCompleteMipChain>",
            "\t\t<fValueClampMin>0.000000</fValueClampMin>",
            "\t\t<fValueClampMax>1.000000</fValueClampMax>",
            "\t\t<fSupportScale>1.000000</fSupportScale>",
            "\t\t<fGammaIn>2.200000</fGammaIn>",
            "\t\t<fGammaOut>2.200000</fGammaOut>",
            "\t\t<iSlabWidth>0</iSlabWidth>",
            "\t\t<iSlabHeight>0</iSlabHeight>",
            "\t\t<iColorKeyX>64</iColorKeyX>",
            "\t\t<iColorKeyY>64</iColorKeyY>",
            "\t\t<iColorKeyZ>64</iColorKeyZ>",
            "\t\t<eExportMode>TEXTURE_2D</eExportMode>",
            "\t\t<bSampleFromTopLayer>false</bSampleFromTopLayer>",
            "\t</m_ExportSettings>",
            "\t<m_CookParams>",
            "\t\t<m_Values/>",
            "\t</m_CookParams>",
            "\t<m_Version>",
            "\t\t<major>1</major>",
            "\t\t<minor>0</minor>",
            "\t\t<build>0</build>",
            "\t\t<revision>0</revision>",
            "\t</m_Version>",
            f"\t<m_Height>{int(height)}</m_Height>",
            f"\t<m_Width>{int(width)}</m_Width>",
            "\t<m_Depth>1</m_Depth>",
            "\t<m_NumMipMaps>0</m_NumMipMaps>",
            f"\t<m_SourceFilePath text=\"{self._xml_text(source_path)}\"/>",
            "\t<m_SourceObjectName text=\"\"/>",
            "\t<m_ImportedTime>0</m_ImportedTime>",
            f"\t<m_ExportedTime>{int(exported_time)}</m_ExportedTime>",
            "\t<m_ClassName text=\"UISliceTexture\"/>",
            "\t<m_DataFiles>",
            "\t\t<Element>",
            "\t\t\t<m_ID text=\"DDS\"/>",
            f"\t\t\t<m_RelativePath text=\"{self._xml_text(safe_dds)}\"/>",
            "\t\t</Element>",
            "\t</m_DataFiles>",
            f"\t<m_Name text=\"{self._xml_text(safe_name)}\"/>",
            "\t<m_Description text=\"\"/>",
            "\t<m_Tags>",
            "\t\t<Element text=\"UISliceTexture\"/>",
            "\t</m_Tags>",
            "</AssetObjects..TextureInstance>",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_group_exported_time() -> int:
        now = datetime.now()
        ymd = int(now.strftime("%Y%m%d"))
        hms = int(now.strftime("%H%M%S"))
        return 473821489 + ymd + hms

    def _generate_texture_files(
        self,
        root_dir: Path,
        *,
        overwrite_existing: bool,
        plans: list[dict[str, object]] | None = None,
        step_callback=None,
        is_cancelled=None,
    ) -> tuple[int, int, bool]:
        plans = plans if isinstance(plans, list) else self._build_textures_output_plan()
        written = 0
        skipped = 0
        cancelled = False
        project_folder = root_dir.name
        group_exported_time = self._build_group_exported_time()
        for index, plan in enumerate(plans, start=1):
            if callable(is_cancelled) and bool(is_cancelled()):
                cancelled = True
                break
            name = str(plan.get("name") or "").strip()
            if callable(step_callback):
                step_callback(f"纹理 {index}/{len(plans)}: {name or '（未命名）'}")
            if not name:
                continue
            width = int(plan.get("target_width") or 0) or 960
            height = int(plan.get("target_height") or 0) or 960
            category = str(plan.get("category") or "").strip()
            source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
            if not isinstance(source_state, dict) or not str(source_state.get("path") or "").strip():
                skipped += 1
                continue
            exported_time = group_exported_time

            dds_target = root_dir / Path(f"Textures/{name}.dds")
            tex_target = root_dir / Path(f"Textures/{name}.tex")

            if (dds_target.exists() or tex_target.exists()) and not overwrite_existing:
                skipped += 1
                continue

            base_image = self._render_state_image(source_state, (width, height))
            if base_image is None:
                skipped += 1
                continue

            # UI Slice：无 mip；LeaderFallback：保留 mip（Beta 默认最小到 3x3）
            if category == "ui_slice":
                dds_bytes, _mip_levels = self._encode_dds_rgba8_with_mips(base_image, min_mip_size=max(width, height) + 1)
                tex_xml = self._build_ui_slice_tex_xml(
                    name=name,
                    width=width,
                    height=height,
                    project_folder_name=project_folder,
                    exported_time=exported_time,
                )
            else:
                dds_bytes, mip_levels = self._encode_dds_rgba8_with_mips(base_image, min_mip_size=3)
                tex_xml = self._build_leader_fallback_tex_xml(
                    name=name,
                    width=width,
                    height=height,
                    mip_levels=mip_levels,
                    project_folder_name=project_folder,
                    exported_time=exported_time,
                )

            dds_target.parent.mkdir(parents=True, exist_ok=True)
            dds_target.write_bytes(dds_bytes)
            tex_target.parent.mkdir(parents=True, exist_ok=True)
            tex_target.write_text(tex_xml, encoding="utf-8")
            written += 1
        return written, skipped, cancelled

    def _generate_img_files(
        self,
        root_dir: Path,
        *,
        overwrite_existing: bool,
        plans: list[dict[str, object]] | None = None,
        step_callback=None,
        is_cancelled=None,
    ) -> tuple[int, int, bool]:
        plans = plans if isinstance(plans, list) else self._build_img_output_plan()
        written = 0
        skipped = 0
        cancelled = False
        for index, plan in enumerate(plans, start=1):
            if callable(is_cancelled) and bool(is_cancelled()):
                cancelled = True
                break
            rel_path = str(plan.get("relative_path") or "")
            if callable(step_callback):
                step_callback(f"图片 {index}/{len(plans)}: {rel_path or '（未命名）'}")
            if not rel_path:
                continue
            source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
            if not isinstance(source_state, dict) or not str(source_state.get("path") or "").strip():
                skipped += 1
                continue
            target = root_dir / Path(rel_path)
            if target.exists() and not overwrite_existing:
                skipped += 1
                continue
            image = self._render_state_image(
                source_state,
                (int(plan.get("target_width") or 1), int(plan.get("target_height") or 1)),
            )
            if image is None:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if image.save(str(target), "PNG"):
                written += 1
            else:
                skipped += 1
        return written, skipped, cancelled

    def _project_root_manifest(self) -> tuple[dict[str, str], set[str], bool, Path | None]:
        self._save_basic_info_payload_to_project(self._basic_info_workspace.export_project_payload())
        self._save_art_payload_to_project(self._art_workspace.export_project_payload())
        files: dict[str, str] = {}
        output_base = self._output_file_basename()
        folders: set[str] = {
            "Data",
            "IMG",
            "Textures",
            "Icons",
            "Text",
            "XLPs",
            "ArtDefs",
            "Platforms",
            "Platforms/Windows",
            "Platforms/Windows/Audio",
            "Scripts",
            "UI",
            "Import",
        }

        civ6proj_path = self._civ6proj_target_path()
        can_generate = bool(civ6proj_path and civ6proj_path.suffix.lower() == ".civ6proj")
        proj_name = civ6proj_path.name if civ6proj_path else "project.civ6proj"

        always_show_files = {
            f"data/{output_base}_colors.sql".lower(),
            f"data/{output_base}_unitabilities.sql".lower(),
            f"data/{output_base}_modifiers.sql".lower(),
            f"data/{output_base}_configs.sql".lower(),
            f"data/{output_base}_moments.sql".lower(),
        }

        civ_data_sql, _ = self._build_civilization_sql_pair()
        leader_data_sql, _ = self._build_leader_sql_pair()
        district_data_sql, _ = self._build_district_sql_pair()
        building_data_sql, _ = self._build_building_sql_pair()
        unit_sql, ability_sql, _ = self._build_unit_sql_bundle()
        improvement_data_sql, _ = self._build_improvement_sql_pair()
        governor_data_sql, _ = self._build_governor_sql_pair()
        great_people_data_sql, great_work_data_sql, _ = self._build_great_people_sql_bundle()
        policy_data_sql, _ = self._build_policy_sql_pair()
        project_data_sql, _ = self._build_project_sql_pair()
        belief_data_sql, _ = self._build_belief_sql_pair()

        def _apply_single_data(section: str, base_name: str, sql_content: str) -> None:
            if not self._should_emit_optional_section_file(section):
                return
            fmt = self._get_group_preview_format(section)
            if fmt == "xml":
                files[f"Data/{output_base}_{base_name}.xml"] = self._sql_preview_to_xml(sql_content)
            else:
                files[f"Data/{output_base}_{base_name}.sql"] = sql_content

        _apply_single_data("文明", "Civilizations", civ_data_sql)
        _apply_single_data("领袖", "Leaders", leader_data_sql)
        _apply_single_data("区域", "Districts", district_data_sql)
        _apply_single_data("建筑", "Buildings", building_data_sql)
        _apply_single_data("改良设施", "Improvements", improvement_data_sql)
        _apply_single_data("总督", "Governors", governor_data_sql)
        _apply_single_data("政策卡", "Policies", policy_data_sql)
        _apply_single_data("项目", "Projects", project_data_sql)
        _apply_single_data("信仰", "Beliefs", belief_data_sql)

        unit_fmt = self._get_group_preview_format("单位")
        if self._should_emit_optional_section_file("单位"):
            if unit_fmt == "xml":
                files[f"Data/{output_base}_Units.xml"] = self._sql_preview_to_xml(unit_sql)
                files[f"Data/{output_base}_UnitAbilities.xml"] = self._sql_preview_to_xml(ability_sql)
            else:
                files[f"Data/{output_base}_Units.sql"] = unit_sql
                files[f"Data/{output_base}_UnitAbilities.sql"] = ability_sql

        great_people_fmt = self._get_group_preview_format("伟人")
        if self._should_emit_optional_section_file("伟人"):
            if great_people_fmt == "xml":
                files[f"Data/{output_base}_GreatPeople.xml"] = self._sql_preview_to_xml(great_people_data_sql)
                files[f"Data/{output_base}_GreatWorks.xml"] = self._sql_preview_to_xml(great_work_data_sql)
            else:
                files[f"Data/{output_base}_GreatPeople.sql"] = great_people_data_sql
                files[f"Data/{output_base}_GreatWorks.sql"] = great_work_data_sql

        if self._should_emit_optional_section_file("议程"):
            files[f"Data/{output_base}_Agendas.sql"] = "-- Agendas.sql\n-- 暂未接入"

        files.update(
            {
                f"Data/{output_base}_Modifiers.sql": self.build_modifier_sql_preview(),
                f"Data/{output_base}_Configs.sql": self._build_configs_sql_preview(),
                f"Data/{output_base}_Colors.sql": "",
                f"Data/{output_base}_Moments.sql": self._build_moments_sql_preview(),
            }
        )

        text_fmt = self._get_text_preview_format()
        text_name = f"{output_base}_Text_{self._text_file_suffix()}.{text_fmt}"
        files[f"Text/{text_name}"] = self._build_text_workspace_preview(text_fmt)
        files[self._img_plan_relative_path()] = self._build_img_plan_table_text()
        files[self._textures_plan_relative_path()] = self._build_textures_plan_table_text()

        # 工程总览下也需要美术预览文件（避免用户未进入“美术”页导致内容过旧）。
        self._art_workspace.refresh_from_sections(self._project.sections)
        art_groups = self._art_workspace.export_preview_file_groups()
        for filename, content in art_groups.get("Icons", []):
            normalized_name = str(filename or "").strip()
            if normalized_name.lower() == "icons.xml":
                files[f"Icons/{output_base}_Icons.xml"] = content
            elif normalized_name:
                files[f"Icons/{normalized_name}"] = content
        for filename, content in art_groups.get("XLP", []):
            normalized_name = str(filename or "").strip()
            if normalized_name.lower() == "ui_icons_dds.xlp":
                ascii_base = self._normalize_ascii_token(output_base)
                package_name = f"{ascii_base}_dds"
                entry_ids: set[str] = set()
                object_name_overrides: dict[str, str] = {}
                for plan in self._build_textures_output_plan():
                    name = str(plan.get("name") or "").strip()
                    if not name:
                        continue
                    category = str(plan.get("category") or "").strip().lower()
                    if category == "leader_fallback" or name.upper().startswith("FALLBACK_"):
                        continue
                    source_state = plan.get("source_state") if isinstance(plan.get("source_state"), dict) else {}
                    source_path = str(plan.get("source_path") or "").strip()
                    raw_path = str(source_state.get("path") or "").strip() if isinstance(source_state, dict) else ""
                    if not source_path or not raw_path:
                        continue
                    entry_ids.add(name)

                for leader_entry in self._iter_section_entries("领袖"):
                    leader_type = str(leader_entry.get("type") or "").strip()
                    if not leader_type:
                        continue
                    curtain_raw = leader_entry.get("add_diplo_background_curtain", False)
                    if isinstance(curtain_raw, bool):
                        enabled = curtain_raw
                    else:
                        enabled = str(curtain_raw or "").strip().lower() in {"1", "true", "yes", "on"}
                    if not enabled:
                        continue
                    suffix = leader_type[len("LEADER_") :] if leader_type.startswith("LEADER_") else leader_type
                    suffix = str(suffix or "").strip()
                    if not suffix:
                        continue
                    entry_id = f"{suffix}_4"
                    entry_ids.add(entry_id)
                    object_name_overrides[entry_id] = "BARBAROSSA_4"

                files[f"XLPs/{package_name}.xlp"] = self._build_ui_texture_xlp_xml(
                    package_name=package_name,
                    entry_ids=sorted(entry_ids),
                    object_name_overrides=object_name_overrides,
                )
            elif normalized_name:
                files[f"XLPs/{normalized_name}"] = content
        emitted_artdefs: list[tuple[str, str]] = []
        fallback_cultures: tuple[str, str] | None = None
        for filename, content in art_groups.get("ArtDef", []):
            normalized_name = str(filename or "").strip()
            if normalized_name.lower() == "cultures.artdef":
                fallback_cultures = (normalized_name, content)
            if self._should_emit_artdef_file(normalized_name):
                emitted_artdefs.append((normalized_name, content))

        if not emitted_artdefs and fallback_cultures is not None:
            emitted_artdefs.append(fallback_cultures)

        for filename, content in emitted_artdefs:
            files[f"ArtDefs/{filename}"] = content

        for filename, content in art_groups.get("Art.xml", []):
            normalized_name = str(filename or "").strip().replace("\\", "/")
            if not normalized_name:
                continue
            if normalized_name.lower().endswith(".art.xml") and "/" not in normalized_name:
                files[normalized_name] = content

        basic = self._load_basic_info_payload_from_project() or {}
        file_info = basic.get("file_info") if isinstance(basic, dict) else {}
        managed_action_paths: set[str] = set()
        if isinstance(file_info, dict):
            action_sources = []
            action_sources.extend(file_info.get("front_end_actions", []) if isinstance(file_info.get("front_end_actions"), list) else [])
            action_sources.extend(file_info.get("in_game_actions", []) if isinstance(file_info.get("in_game_actions"), list) else [])

            gameplay_lua_template = "\n".join(
                [
                    "function Initialize()",
                    "end",
                    "",
                    "Events.LoadGameViewStateDone.Add(Initialize)",
                    "",
                ]
            )
            ui_xml_template = "\n".join(
                [
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
                    "<Context></Context>",
                    "",
                ]
            )

            def _ensure_parent_folders(rel_path: str) -> None:
                parent = rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""
                while parent:
                    folders.add(parent)
                    if "/" not in parent:
                        break
                    parent = parent.rsplit("/", 1)[0]

            for action in action_sources:
                if not isinstance(action, dict):
                    continue
                action_type = str(action.get("type") or "").strip()
                file_list = action.get("files") if isinstance(action.get("files"), list) else []
                target_root = (
                    "Scripts"
                    if action_type == "AddGameplayScripts"
                    else "UI"
                    if action_type == "AddUserInterfaces"
                    else "Import"
                    if action_type == "ImportFiles"
                    else ""
                )
                if not target_root:
                    continue
                for raw in file_list:
                    rel = str(raw or "").replace("\\", "/").strip().lstrip("/")
                    if not rel:
                        continue
                    rel_path = f"{target_root}/{rel}" if not rel.startswith(f"{target_root}/") else rel
                    if action_type == "AddGameplayScripts" and rel_path.lower().endswith(".lua"):
                        existing = str(files.get(rel_path, ""))
                        files[rel_path] = existing if existing.strip() else gameplay_lua_template
                        managed_action_paths.add(rel_path.replace("\\", "/").strip().lower())
                        _ensure_parent_folders(rel_path)
                        continue

                    if action_type == "AddUserInterfaces" and rel_path.lower().endswith(".xml"):
                        existing = str(files.get(rel_path, ""))
                        files[rel_path] = existing if existing.strip() else ui_xml_template
                        managed_action_paths.add(rel_path.replace("\\", "/").strip().lower())
                        _ensure_parent_folders(rel_path)

                        lua_pair = rel_path[:-4] + ".lua"
                        lua_existing = str(files.get(lua_pair, ""))
                        files[lua_pair] = lua_existing if lua_existing.strip() else gameplay_lua_template
                        managed_action_paths.add(lua_pair.replace("\\", "/").strip().lower())
                        _ensure_parent_folders(lua_pair)
                        continue

                    if action_type == "ImportFiles" and rel_path.lower().endswith(".lua"):
                        files.setdefault(rel_path, "")
                        managed_action_paths.add(rel_path.replace("\\", "/").strip().lower())
                        _ensure_parent_folders(rel_path)
                        continue

                    files.setdefault(rel_path, "")
                    managed_action_paths.add(rel_path.replace("\\", "/").strip().lower())
                    _ensure_parent_folders(rel_path)

        filtered_files: dict[str, str] = {}
        img_plan_key = self._img_plan_relative_path().lower()
        textures_plan_key = self._textures_plan_relative_path().lower()
        for rel_path, content in files.items():
            key = rel_path.replace("\\", "/").strip().lower()
            if key not in {img_plan_key, textures_plan_key} and not self._is_allowed_project_overview_file(rel_path):
                continue
            if key.endswith(".civ6proj") or key in always_show_files or key in managed_action_paths or bool(str(content or "").strip()):
                filtered_files[rel_path] = content
        files = filtered_files

        self._readonly_custom_paths = set()
        self._cached_custom_project_files = []
        if isinstance(civ6proj_path, Path) and civ6proj_path.exists():
            external_files, external_folders, custom_paths = self._collect_external_project_files(
                root_dir=civ6proj_path.parent,
                civ6proj_name=proj_name,
                generated_paths=set(files.keys()),
            )
            files.update(external_files)
            folders.update(external_folders)
            self._readonly_custom_paths = set(custom_paths)
            self._cached_custom_project_files = list(custom_paths)

        files[proj_name] = self._build_civ6proj_preview(proj_name, files, folders)

        LOGGER.info("[RootOutput] manifest built files=%d folders=%d can_generate=%s", len(files), len(folders), can_generate)
        return files, folders, can_generate, civ6proj_path

    def _section_has_entries(self, section: str) -> bool:
        entries = self._project.sections.get(section)
        if not isinstance(entries, list):
            return False
        return any(isinstance(entry, dict) for entry in entries)

    def _should_emit_optional_section_file(self, section: str) -> bool:
        optional_sections = {"区域", "建筑", "单位", "改良设施", "伟人", "总督", "项目", "信仰", "政策卡", "议程"}
        if section not in optional_sections:
            return True
        return self._section_has_entries(section)

    def _should_emit_artdef_file(self, filename: str) -> bool:
        name = str(filename or "").strip().lower()
        section_by_file = {
            "districts.artdef": "区域",
            "buildings.artdef": "建筑",
            "units.artdef": "单位",
            "improvements.artdef": "改良设施",
            "civilizations.artdef": "文明",
            "cultures.artdef": "文明",
            "fallbackleaders.artdef": "领袖",
            "leaders.artdef": "领袖",
        }
        section = section_by_file.get(name)
        if not section:
            return True
        return self._section_has_entries(section)

    def _refresh_project_root_workspace(self) -> None:
        files, folders, can_generate, _civ6proj_path = self._project_root_manifest()
        delete_marked: set[str] = set()
        basic = self._load_basic_info_payload_from_project() or {}
        file_info = basic.get("file_info") if isinstance(basic, dict) else {}
        delete_requests = file_info.get("delete_requests") if isinstance(file_info, dict) else []
        if isinstance(delete_requests, list):
            root = self._civ6proj_target_path()
            root_dir = root.parent if isinstance(root, Path) else None
            for item in delete_requests:
                rel = str(item or "").replace("\\", "/").strip()
                if not rel:
                    continue
                if root_dir is not None and (root_dir / rel).exists():
                    delete_marked.add(rel)
        self._project_root_workspace.set_manifest(files, folders, can_generate, delete_marked)
        img_rows: list[dict[str, str]] = []
        for plan in self._build_img_output_plan():
            rel_path = str(plan.get("relative_path") or "").strip()
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            source_path = str(plan.get("source_path") or "").strip()
            source_name = Path(source_path).name if source_path else "（未设置来源）"
            category = str(plan.get("category") or "")
            if category == "atlas":
                note = "图标多尺寸输出"
            elif category == "moment":
                note = "历史时刻插画(456×332)"
            else:
                note = "最终尺寸图"
            img_rows.append(
                {
                    "output": rel_path,
                    "size": f"{width}x{height}",
                    "source": source_name,
                    "note": note,
                }
            )
        self._project_root_workspace.set_img_plan_preview(self._img_plan_relative_path(), img_rows)

        textures_rows: list[dict[str, str]] = []
        for plan in self._build_textures_output_plan():
            name = str(plan.get("name") or "").strip()
            width = int(plan.get("target_width") or 0)
            height = int(plan.get("target_height") or 0)
            source_path = str(plan.get("source_path") or "").strip()
            source_name = Path(source_path).name if source_path else "（未设置来源）"
            textures_rows.append(
                {
                    "output": f"Textures/{name}.dds",
                    "size": f"{width}x{height}",
                    "source": source_name,
                    "note": f"同时生成 Textures/{name}.tex",
                }
            )
        self._project_root_workspace.set_textures_plan_preview(self._textures_plan_relative_path(), textures_rows)

    def _write_output_file(self, root_dir: Path, relative_path: str, content: str) -> None:
        target = root_dir / Path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    @staticmethod
    def _output_needs_units_required_check(relative_path: str) -> bool:
        rel = str(relative_path or "").replace("\\", "/").lower()
        if not rel.startswith("data/"):
            return False
        if "_unitabilities." in rel:
            return False
        return "_units." in rel

    @staticmethod
    def _output_needs_districts_required_check(relative_path: str) -> bool:
        rel = str(relative_path or "").replace("\\", "/").lower()
        return rel.startswith("data/") and "_districts." in rel

    def _validate_required_main_table_fields(self, *, validate_units: bool, validate_districts: bool) -> bool:
        table_to_section = {
            "Districts": "区域",
            "Units": "单位",
        }
        enabled_tables: set[str] = set()
        if validate_districts:
            enabled_tables.add("Districts")
        if validate_units:
            enabled_tables.add("Units")

        missing_required: list[tuple[str, str, str]] = []
        for table_name in sorted(enabled_tables):
            section = table_to_section.get(table_name)
            rules = REQUIRED_MAIN_TABLE_FIELD_RULES.get(table_name, {})
            if not section or not rules:
                continue
            if not self._section_has_entries(section):
                continue
            entries = self._project.sections.get(section)
            section_entries = [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []
            for index, entry in enumerate(section_entries, start=1):
                obj_type = str(entry.get("type") or "").strip()
                if not obj_type:
                    if table_name == "Districts":
                        obj_type = f"DISTRICT_CUSTOM_{index}"
                    elif table_name == "Units":
                        obj_type = f"UNIT_CUSTOM_{index}"
                    else:
                        obj_type = f"CUSTOM_{index}"

                table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
                if not isinstance(table_data, dict) or not table_data:
                    table_data = {}
                    entry["table_data"] = table_data

                for field_key, rule in rules.items():
                    if not isinstance(rule, dict) or not bool(rule.get("required")):
                        continue
                    current = str(table_data.get(field_key) or "").strip()
                    if current:
                        continue
                    default_value = str(rule.get("default") or "").strip()
                    if default_value:
                        table_data[field_key] = default_value
                        continue
                    missing_required.append((section, obj_type, field_key))

        if missing_required:
            lines = [f"{sec} / {obj_type} / {field_key}" for sec, obj_type, field_key in missing_required[:30]]
            more = "\n..." if len(missing_required) > 30 else ""
            QMessageBox.warning(
                self,
                "必填参数未填写",
                "存在必填参数未填写，已阻止生成。\n"
                "请先在对应分类的【主表】中补全必填字段后再生成。\n\n"
                f"缺失列表（最多显示 30 条）：\n" + "\n".join(lines) + more,
            )
            return False
        return True

    def _generate_single_output_file(self, relative_path: str) -> None:
        if relative_path in self._readonly_custom_paths:
            QMessageBox.information(self, "只读文件", f"该文件为外部自定义只读文件，不参与生成：\n{relative_path}")
            return

        if not self._validate_required_main_table_fields(
            validate_units=self._output_needs_units_required_check(relative_path),
            validate_districts=self._output_needs_districts_required_check(relative_path),
        ):
            return

        files, folders, can_generate, civ6proj_path = self._project_root_manifest()
        if not can_generate or civ6proj_path is None:
            QMessageBox.warning(self, "无法生成", "请先在基础信息中导入 .civ6proj 文件后再生成。")
            return
        if relative_path not in files:
            QMessageBox.warning(self, "无法生成", "未找到所选文件内容。")
            return

        root_dir = civ6proj_path.parent
        root_dir.mkdir(parents=True, exist_ok=True)
        for folder in sorted(folders):
            (root_dir / folder).mkdir(parents=True, exist_ok=True)

        target = root_dir / Path(relative_path)
        if target.exists():
            result = QMessageBox.question(
                self,
                "文件已存在",
                f"文件已存在：{target}\n是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        is_img_target = relative_path == self._img_plan_relative_path()
        is_textures_target = relative_path == self._textures_plan_relative_path()

        if not is_textures_target:
            self._write_output_file(root_dir, relative_path, files.get(relative_path, ""))
        image_written = 0
        image_skipped = 0
        texture_written = 0
        texture_skipped = 0

        if is_img_target or is_textures_target:
            img_plans = self._build_img_output_plan() if is_img_target else []
            textures_plans = self._build_textures_output_plan() if is_textures_target else []

            total_steps = max(1, len(img_plans) + len(textures_plans))
            progress = QProgressDialog("正在生成资源...", "取消", 0, total_steps, self)
            progress.setWindowTitle("生成进度")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress_value = 0

            def _is_cancelled() -> bool:
                return progress.wasCanceled()

            def _step(label: str) -> None:
                nonlocal progress_value
                progress_value = min(total_steps, progress_value + 1)
                progress.setLabelText(label)
                progress.setValue(progress_value)
                QApplication.processEvents()

            cancelled = False
            if is_img_target:
                image_written, image_skipped, img_cancelled = self._generate_img_files(
                    root_dir,
                    overwrite_existing=True,
                    plans=img_plans,
                    step_callback=_step,
                    is_cancelled=_is_cancelled,
                )
                cancelled = cancelled or img_cancelled

            if is_textures_target and not cancelled:
                texture_written, texture_skipped, tex_cancelled = self._generate_texture_files(
                    root_dir,
                    overwrite_existing=True,
                    plans=textures_plans,
                    step_callback=_step,
                    is_cancelled=_is_cancelled,
                )
                cancelled = cancelled or tex_cancelled

            progress.setValue(total_steps)
            progress.close()

            if cancelled:
                target_message = (
                    "纹理输出（未写入纹理清单txt）"
                    if is_textures_target
                    else f"已生成文件：{target}"
                )
                QMessageBox.information(
                    self,
                    "已取消",
                    f"{target_message}\n"
                    f"图片输出：写入 {image_written}，跳过 {image_skipped}。\n"
                    f"纹理输出：写入 {texture_written}，跳过 {texture_skipped}。",
                )
                return

        target_message = (
            "纹理输出（未写入纹理清单txt）"
            if is_textures_target
            else f"已生成文件：{target}"
        )

        QMessageBox.information(
            self,
            "生成完成",
            f"{target_message}\n图片输出：写入 {image_written}，跳过 {image_skipped}。\n纹理输出：写入 {texture_written}，跳过 {texture_skipped}。",
        )

    def _generate_all_output_files(self) -> None:
        if not self._validate_required_main_table_fields(
            validate_units=self._section_has_entries("单位"),
            validate_districts=self._section_has_entries("区域"),
        ):
            return

        files, folders, can_generate, civ6proj_path = self._project_root_manifest()
        if not can_generate or civ6proj_path is None:
            QMessageBox.warning(self, "无法生成", "请先在基础信息中导入 .civ6proj 文件后再生成。")
            return

        root_dir = civ6proj_path.parent
        root_dir.mkdir(parents=True, exist_ok=True)
        for folder in sorted(folders):
            (root_dir / folder).mkdir(parents=True, exist_ok=True)

        texture_plan_path = self._textures_plan_relative_path()
        batch_items = [
            (rel, content)
            for rel, content in files.items()
            if rel != texture_plan_path and rel not in self._readonly_custom_paths
        ]

        existing = [rel for rel, _content in sorted(batch_items) if (root_dir / Path(rel)).exists()]

        basic = self._load_basic_info_payload_from_project() or {}
        file_info = basic.get("file_info") if isinstance(basic, dict) else {}
        delete_requests = file_info.get("delete_requests") if isinstance(file_info, dict) else []
        delete_candidates: list[str] = []
        if isinstance(delete_requests, list):
            for item in delete_requests:
                rel = str(item or "").replace("\\", "/").strip()
                if not rel:
                    continue
                target = root_dir / Path(rel)
                if target.exists() and target.is_file():
                    delete_candidates.append(rel)

        overwrite_set: set[str] = set()
        delete_set: set[str] = set()
        if existing or delete_candidates:
            dlg = _OverwriteSelectionDialog(existing, self, delete_paths=delete_candidates)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            overwrite_set = dlg.selected_paths()
            delete_set = dlg.selected_delete_paths()

        img_plans = self._build_img_output_plan()
        textures_plans = self._build_textures_output_plan()
        total_steps = max(1, len(delete_set) + len(batch_items) + len(img_plans) + len(textures_plans))
        progress = QProgressDialog("正在生成文件...", "取消", 0, total_steps, self)
        progress.setWindowTitle("批量生成")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress_value = 0

        def _is_cancelled() -> bool:
            return progress.wasCanceled()

        def _step(label: str) -> None:
            nonlocal progress_value
            progress_value = min(total_steps, progress_value + 1)
            progress.setLabelText(label)
            progress.setValue(progress_value)
            QApplication.processEvents()

        written = 0
        skipped = 0
        deleted = 0
        delete_skipped = 0
        cancelled = False

        for rel_path in sorted(delete_set):
            if _is_cancelled():
                cancelled = True
                break
            target = root_dir / Path(rel_path)
            _step(f"删除文件: {rel_path}")
            if not target.exists() or not target.is_file():
                delete_skipped += 1
                continue
            try:
                target.unlink()
                deleted += 1
            except Exception:
                LOGGER.exception("[GenerateAll] delete file failed: %s", target)
                delete_skipped += 1

        for rel_path, content in batch_items:
            if _is_cancelled():
                cancelled = True
                break
            target = root_dir / Path(rel_path)
            _step(f"写入文件: {rel_path}")
            if target.exists() and rel_path not in overwrite_set:
                skipped += 1
                continue
            self._write_output_file(root_dir, rel_path, content)
            written += 1

        image_written = 0
        image_skipped = 0
        texture_written = 0
        texture_skipped = 0

        if not cancelled:
            image_written, image_skipped, img_cancelled = self._generate_img_files(
                root_dir,
                overwrite_existing=(self._img_plan_relative_path() in overwrite_set),
                plans=img_plans,
                step_callback=_step,
                is_cancelled=_is_cancelled,
            )
            cancelled = cancelled or img_cancelled

        if not cancelled:
            texture_written, texture_skipped, tex_cancelled = self._generate_texture_files(
                root_dir,
                overwrite_existing=(self._textures_plan_relative_path() in overwrite_set),
                plans=textures_plans,
                step_callback=_step,
                is_cancelled=_is_cancelled,
            )
            cancelled = cancelled or tex_cancelled

        progress.setValue(total_steps)
        progress.close()

        if cancelled:
            QMessageBox.information(
                self,
                "已取消",
                f"生成已取消（已完成部分写入）。\n已删除 {deleted} 个文件，跳过删除 {delete_skipped} 个。\n已写入 {written} 个文件，跳过 {skipped} 个文件。\n"
                f"图片输出：写入 {image_written}，跳过 {image_skipped}。\n"
                f"纹理输出：写入 {texture_written}，跳过 {texture_skipped}。",
            )
            return

        QMessageBox.information(
            self,
            "生成完成",
            f"已删除 {deleted} 个文件，跳过删除 {delete_skipped} 个。\n已写入 {written} 个文件，跳过 {skipped} 个文件。\n图片输出：写入 {image_written}，跳过 {image_skipped}。\n纹理输出：写入 {texture_written}，跳过 {texture_skipped}。",
        )

    @staticmethod
    def _resolve_entry_name(entry: object, index: int) -> str:
        if isinstance(entry, dict):
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
            class_data = entry.get("class_data")
            if isinstance(class_data, dict):
                class_name = class_data.get("Name")
                if isinstance(class_name, str) and class_name.strip():
                    return class_name.strip()
                class_type = class_data.get("GreatPersonClassType")
                if isinstance(class_type, str) and class_type.strip():
                    return class_type.strip()
            identifier = entry.get("id")
            if isinstance(identifier, str) and identifier.strip():
                return identifier.strip()
        return f"子条目 {index + 1}"

    def _handle_selection_changed(self) -> None:
        selected = self._tree.selectedItems()
        if not selected:
            return
        payload = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return

        kind = payload.get("kind")
        if kind == "project_root":
            self._workspace_title.setText("工程总览")
            self._workspace_info.setText("当前节点为工程根。可在此预览并生成工程输出文件。")
            self._workspace_path.setText(f"工程：{self._project.project_name}")
            self._refresh_project_root_workspace()
            self._workspace_stack.setCurrentWidget(self._project_root_workspace)
            return

        if kind == "section_leaf":
            section = str(payload.get("section") or "")
            self._workspace_title.setText(section)
            self._workspace_path.setText(f"路径：{self._project.project_name} / {section}")
            if section == "基础信息":
                self._workspace_stack.setCurrentWidget(self._basic_info_workspace)
            elif section == "美术":
                self._art_workspace.refresh_from_sections(self._project.sections)
                self._workspace_stack.setCurrentWidget(self._art_workspace)
            elif section == "修改器":
                self._workspace_stack.setCurrentWidget(self._modifier_workspace)
            elif section == "文本":
                self._workspace_info.setText("文本工作区预览：统一查看 Text.sql / Text.xml。")
                self._text_workspace.refresh_preview()
                self._workspace_stack.setCurrentWidget(self._text_workspace)
            else:
                self._workspace_info.setText("该分类为直接工作区节点（当前阶段内容预留）。")
                self._workspace_stack.setCurrentWidget(self._workspace_placeholder)
            return

        if kind == "section_group":
            section = str(payload.get("section") or "")
            self._workspace_title.setText(section)
            self._workspace_info.setText("这是子条目组。可新增子条目，并查看 SQL/XML 预览。")
            self._workspace_path.setText(f"路径：{self._project.project_name} / {section}")
            self._group_workspace.set_section(section)
            self._workspace_stack.setCurrentWidget(self._group_workspace)
            return

        if kind == "section_item":
            section = str(payload.get("section") or "")
            entry_name = str(payload.get("entry_name") or "")
            index = int(payload.get("index") or 0)
            self._workspace_title.setText(entry_name)
            self._workspace_info.setText("已进入子条目工作区。")
            self._workspace_path.setText(f"路径：{self._project.project_name} / {section} / {entry_name}（#{index + 1}）")
            entries = self._project.sections.get(section)
            if isinstance(entries, list) and 0 <= index < len(entries) and isinstance(entries[index], dict):
                entry_payload = entries[index]
            else:
                entry_payload = {"name": entry_name}
            self._section_item_workspace.set_item(section, index, entry_payload, fallback_name=entry_name)
            self._workspace_stack.setCurrentWidget(self._section_item_workspace)
            return
