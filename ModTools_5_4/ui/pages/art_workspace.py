"""Art workspace panel (direct workspace section).

目标：
- 作为“美术”直接工作区（无子对象）
- 提供 XLP / ArtDef / Icons.xml 三部分预览
- 优化：进入页面自动刷新；Icons.xml 对已导入图片直接输出，对未导入图片提供别名选择
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import sqlite3
from pathlib import Path
import re
import uuid
from xml.etree import ElementTree as ET

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...app.settings_store import load_settings
from ...db.interface import resolve_chinese_text_or_unknown
from ...db.paths import DEFAULT_GAME_DB
from ..ui_widget_kit import MomentTextureSearchTemplate

try:
    from ...artdef_parser import (
        get_building_entry_element,
        get_civilization_entry_element,
        get_district_entry_element,
        get_improvement_entry_element,
        get_unit_entry_element,
        list_building_artdef_names,
        list_civilization_artdef_names,
        list_district_artdef_names,
        list_improvement_artdef_names,
        list_unit_artdef_names,
    )
except Exception:
    get_building_entry_element = None  # type: ignore[assignment]
    get_civilization_entry_element = None  # type: ignore[assignment]
    get_district_entry_element = None  # type: ignore[assignment]
    get_improvement_entry_element = None  # type: ignore[assignment]
    get_unit_entry_element = None  # type: ignore[assignment]
    list_building_artdef_names = None  # type: ignore[assignment]
    list_civilization_artdef_names = None  # type: ignore[assignment]
    list_district_artdef_names = None  # type: ignore[assignment]
    list_improvement_artdef_names = None  # type: ignore[assignment]
    list_unit_artdef_names = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ART_XML_RULES_FILE = DATA_DIR / "art_xml_rules.json"
DEFAULT_BLANK_ART_XML_FILE = DATA_DIR / "default_blank_art.xml"

ART_SECTION_FORMAT = "MODTOOLS54_ART_WORKSPACE"
ART_SECTION_SCHEMA = "1.0.0"

EXTRA_XLP_TEMPLATES: list[tuple[str, str]] = [
    (
        "tilebases.xlp",
        """<?xml version="1.0" encoding="UTF-8" ?>
<AssetObjects..XLP>
    <m_Version>
        <major>1</major>
        <minor>0</minor>
        <build>0</build>
        <revision>0</revision>
    </m_Version>
    <m_ClassName text="TileBase"/>
    <m_PackageName text="landmarks/tilebases"/>
    <m_Entries/>
    <m_AllowedPlatforms>
        <Element>WINDOWS</Element>
        <Element>MACOS</Element>
        <Element>IOS</Element>
        <Element>LINUX</Element>
        <Element>XBONE</Element>
        <Element>PS4</Element>
        <Element>SWITCH</Element>
        <Element>STADIA</Element>
    </m_AllowedPlatforms>
</AssetObjects..XLP>
""",
    ),
    (
        "UILensModels.xlp",
        """<?xml version="1.0" encoding="UTF-8" ?>
<AssetObjects..XLP>
    <m_Version>
        <major>1</major>
        <minor>0</minor>
        <build>0</build>
        <revision>0</revision>
    </m_Version>
    <m_ClassName text="UILensAsset"/>
    <m_PackageName text="UILensAssets"/>
    <m_Entries/>
    <m_AllowedPlatforms>
        <Element>WINDOWS</Element>
        <Element>IOS</Element>
        <Element>LINUX</Element>
        <Element>XBONE</Element>
        <Element>PS4</Element>
        <Element>SWITCH</Element>
        <Element>STADIA</Element>
    </m_AllowedPlatforms>
</AssetObjects..XLP>
""",
    ),
    (
        "StrategicView_UILenses.xlp",
        """<?xml version="1.0" encoding="UTF-8" ?>
<AssetObjects..XLP>
    <m_Version>
        <major>1</major>
        <minor>0</minor>
        <build>0</build>
        <revision>0</revision>
    </m_Version>
    <m_ClassName text="StrategicView_Sprite"/>
    <m_PackageName text="strategicview/strategicview_uilenses"/>
    <m_Entries/>
    <m_AllowedPlatforms>
        <Element>WINDOWS</Element>
        <Element>IOS</Element>
        <Element>LINUX</Element>
        <Element>XBONE</Element>
        <Element>PS4</Element>
        <Element>SWITCH</Element>
        <Element>STADIA</Element>
    </m_AllowedPlatforms>
</AssetObjects..XLP>
""",
    ),
]

EXTRA_ARTDEF_TEMPLATES: list[tuple[str, str]] = [
    (
        "Landmarks.artdef",
        """<?xml version="1.0" encoding="UTF-8" ?>
<AssetObjects..ArtDefSet>
    <m_Version>
        <major>1</major>
        <minor>0</minor>
        <build>0</build>
        <revision>0</revision>
    </m_Version>
    <m_TemplateName text="Landmarks"/>
    <m_RootCollections>
        <Element>
            <m_CollectionName text="Districts"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="Landmarks"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="ResourceTags"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="Globals"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="TerrainTags"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
    </m_RootCollections>
</AssetObjects..ArtDefSet>
""",
    ),
    (
        "Overlay.artdef",
        """<?xml version="1.0" encoding="UTF-8" ?>
<AssetObjects..ArtDefSet>
    <m_Version>
        <major>1</major>
        <minor>0</minor>
        <build>0</build>
        <revision>0</revision>
    </m_Version>
    <m_TemplateName text="Overlay"/>
    <m_RootCollections>
        <Element>
            <m_CollectionName text="Overlays"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="Coord3D_WS"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="RangeArrows"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
        <Element>
            <m_CollectionName text="Layers"/>
            <m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
        </Element>
    </m_RootCollections>
</AssetObjects..ArtDefSet>
""",
    ),
    (
        "StrategicView.artdef",
        """<?xml version="1.0" encoding="UTF-8" ?>
<AssetObjects..ArtDefSet>
    <m_Version>
        <major>1</major>
        <minor>0</minor>
        <build>0</build>
        <revision>0</revision>
    </m_Version>
    <m_TemplateName text="StrategicView"/>
    <m_RootCollections>
        <Element><m_CollectionName text="Properties"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="PositionSets"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="PlacementRules"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="TerrainBlends"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="TerrainBlendCorners"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="TerrainSpriteEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="TerrainSprites"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="TerrainTypes"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="FeatureEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Features"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Routes"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="ImprovementEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Improvements"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="DistrictEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Districts"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="BuildingEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Buildings"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="CityEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Cities"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="ParkEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Parks"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="EffectEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="Effects"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="UILenses"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
        <Element><m_CollectionName text="UILensEntries"/><m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements></Element>
    </m_RootCollections>
</AssetObjects..ArtDefSet>
""",
    ),
]

_CULTURE_GROUPS_FALLBACK: dict[str, tuple[str, ...]] = {
    "Culture": (
        "DEFAULT",
        "NorthAfrican",
        "SouthAmerican",
        "Mughal",
        "EastAsian",
        "SouthAfrican",
        "Mediterranean",
        "SoutheastAsian",
        "AncientBrick",
        "AncientEarth",
        "America",
        "ModernGlass",
        "Colonial",
        "AncientWood",
        "Indonesian",
        "Baltic",
        "RowHouse",
        "Scottish",
        "Brazil",
    ),
    "UnitCulture": (
        "Asian",
        "Mediterranean",
        "MiddleEastern",
        "European",
        "African",
        "SouthAmerican",
        "Barbarian",
        "Indian",
        "Maori",
        "NativeAmerican",
        "SouthEastAsian",
    ),
}

_CULTURE_TRANSLATIONS: dict[str, str] = {
    "DEFAULT": "默认",
    "NorthAfrican": "北非",
    "SouthAmerican": "南美",
    "Mughal": "莫卧儿",
    "EastAsian": "东亚",
    "SouthAfrican": "南非",
    "Mediterranean": "地中海",
    "SoutheastAsian": "东南亚",
    "AncientBrick": "古砖",
    "AncientEarth": "古土",
    "America": "美洲",
    "ModernGlass": "现代玻璃",
    "Colonial": "殖民",
    "AncientWood": "古木",
    "Indonesian": "印度尼西亚",
    "Baltic": "波罗的海",
    "RowHouse": "连排屋",
    "Scottish": "苏格兰",
    "Brazil": "巴西",
    "Asian": "亚洲",
    "MiddleEastern": "中东",
    "European": "欧洲",
    "African": "非洲",
    "Barbarian": "蛮族",
    "Indian": "印度",
    "Maori": "毛利",
    "NativeAmerican": "美洲原住民",
    "SouthEastAsian": "东南亚",
}

_CULTURE_COLLECTION_TITLES: dict[str, str] = {
    "Culture": "城市与建筑文化",
    "UnitCulture": "单位文化",
}


def _safe_text(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def _active_game_db_path() -> Path:
    settings = load_settings()
    configured = _safe_text(getattr(settings, "game_db_path", ""))
    if configured and Path(configured).exists():
        return Path(configured)
    return DEFAULT_GAME_DB


@dataclass(slots=True)
class _AliasRow:
    entity: str
    type_name: str
    chinese_name: str
    icon_name: str
    variant: str  # icon / portrait

    @property
    def state_key(self) -> str:
        return f"{self.entity}:{self.type_name}:{self.variant}"


@dataclass(slots=True)
class _ArtdefSourceRow:
    entity: str
    type_name: str
    chinese_name: str
    replacement_type: str

    @property
    def state_key(self) -> str:
        return f"{self.entity}:{self.type_name}"


@dataclass(slots=True)
class _CivArtRow:
    civ_type: str
    chinese_name: str


@dataclass(frozen=True)
class _MomentRow:
    entity: str  # district/building/unit/improvement/governor
    game_data_type: str
    chinese_name: str
    moment_illustration_type: str
    moment_data_type: str

    @property
    def state_key(self) -> str:
        return f"moment:{self.entity}:{self.game_data_type}"


@dataclass(slots=True)
class _LeaderXlpRow:
    leader_type: str
    chinese_name: str

    @property
    def state_key(self) -> str:
        return f"leader_xlp:{self.leader_type.lower()}"

    @property
    def xlp_file_name(self) -> str:
        return f"{self.leader_type.lower()}.xlp"


class _CulturePickerDialog(QDialog):
    def __init__(
        self,
        civ_type: str,
        groups: dict[str, tuple[str, ...]],
        selected: dict[str, list[str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"文化组选择 - {civ_type}")
        self.resize(520, 520)
        self._selected: dict[str, list[str]] = {
            collection: [name for name in values if _safe_text(name)]
            for collection, values in selected.items()
            if isinstance(values, list)
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        for collection, options in groups.items():
            title = _CULTURE_COLLECTION_TITLES.get(collection, collection)
            box = QGroupBox(f"{title} ({collection})")
            box_layout = QGridLayout(box)
            box_layout.setHorizontalSpacing(14)
            box_layout.setVerticalSpacing(6)
            existing = set(self._selected.get(collection, []))
            for index, option in enumerate(options):
                cn = _CULTURE_TRANSLATIONS.get(option)
                label = f"{cn} ({option})" if cn else option
                checkbox = QCheckBox(label)
                checkbox.setChecked(option in existing)
                checkbox.stateChanged.connect(
                    lambda _state, col=collection, name=option, cb=checkbox: self._toggle_option(col, name, cb.isChecked())
                )
                box_layout.addWidget(checkbox, index // 2, index % 2)
            root.addWidget(box)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

    def _toggle_option(self, collection: str, group_name: str, checked: bool) -> None:
        names = [name for name in self._selected.get(collection, []) if _safe_text(name)]
        if checked:
            if group_name not in names:
                names.append(group_name)
        else:
            names = [name for name in names if name != group_name]
        self._selected[collection] = sorted(set(names))

    def selected_groups(self) -> dict[str, list[str]]:
        return {
            collection: sorted(set(values))
            for collection, values in self._selected.items()
            if isinstance(values, list) and values
        }


class _ArtPreviewDialog(QDialog):
    """独立预览窗口：一个文件一个分页。"""

    def __init__(self, preview_groups: dict[str, list[tuple[str, str]]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("美术输出预览")
        self.resize(1100, 760)

        category_tabs = QTabWidget(self)
        for category, files in preview_groups.items():
            per_file_tabs = QTabWidget()
            if not files:
                empty = QPlainTextEdit()
                empty.setReadOnly(True)
                empty.setPlainText("当前无可预览文件。")
                per_file_tabs.addTab(empty, "(空)")
            else:
                for filename, content in files:
                    editor = QPlainTextEdit()
                    editor.setReadOnly(True)
                    editor.setPlainText(content)
                    per_file_tabs.addTab(editor, filename)
            category_tabs.addTab(per_file_tabs, category)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(category_tabs, 1)


class ArtWorkspacePanel(QWidget):
    """5.4 美术工作区（直接工作区）。"""

    SIZE_CIVILIZATION = [22, 30, 32, 36, 44, 45, 48, 50, 64, 80, 128, 200, 256]
    SIZE_LEADER = [32, 45, 48, 50, 55, 64, 80, 256]
    SIZE_DISTRICT = [22, 32, 38, 50, 80, 128, 256]
    SIZE_BUILDING = [32, 38, 50, 80, 128, 256]
    SIZE_UNIT = [22, 32, 38, 50, 80, 128, 256]
    SIZE_UNIT_PORTRAIT = [38, 50, 70, 95, 200, 256]
    SIZE_IMPROVEMENT = [38, 50, 80, 256]
    SIZE_PROJECT = [30, 32, 38, 50, 70, 80, 256]
    SIZE_BELIEF = [32, 38, 50, 64, 256]
    SIZE_GOVERNOR_MAIN = [22, 32, 64]
    SIZE_GOVERNOR_FILL_SLOT = [22, 32]

    def __init__(self) -> None:
        super().__init__()
        self._sections: dict[str, object] = {}
        self._state: dict[str, object] = {
            "alias_map": {},
            "source_map": {},
            "need_map": {},
            "extra_xlp_flags": {},
            "extra_artdef_flags": {},
            "civs": {},
            "moments_map": {},
            "leader_xlp_flags": {},
            "art_xml_workspace_config": {},
            "art_xml_source_config": {},
            "art_xml_source_path": "",
        }
        self._alias_options: dict[str, list[tuple[str, str]]] = {}
        self._source_options: dict[str, list[tuple[str, str]]] = {}
        self._civ_source_options: list[tuple[str, str]] = []
        self._replacement_maps: dict[str, dict[str, str]] = {
            "district": {},
            "building": {},
            "improvement": {},
            "unit": {},
        }
        self._civ_rows: list[_CivArtRow] = []
        self._alias_rows: list[_AliasRow] = []
        self._source_rows: list[_ArtdefSourceRow] = []
        self._moment_rows: list[_MomentRow] = []
        self._leader_xlp_rows: list[_LeaderXlpRow] = []
        self._moment_texture_options: list[str] = []
        self._preview_groups: dict[str, list[tuple[str, str]]] = {}
        self._updating = False
        self._alias_columns_dirty = True
        self._source_columns_dirty = True
        self._moment_columns_dirty = True

        self._build_ui()

    def _build_ui(self) -> None:
        info = QLabel("美术工作区（自动刷新）：支持文明音乐/文化、图标别名与 ArtDef 来源编辑；预览在独立窗口打开。")
        info.setObjectName("pageInfoLabel")
        info.setWordWrap(True)

        self._civ_table = QTableWidget(0, 6)
        self._civ_table.setHorizontalHeaderLabels(["CivilizationType", "中文名", "IconTag", "文化组", "需要ArtDef", "原版文明音乐"])
        self._civ_table.verticalHeader().setVisible(False)
        self._civ_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._civ_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._civ_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        civ_group = QGroupBox("文明音乐与文化（Civilizations / Cultures）")
        civ_layout = QVBoxLayout(civ_group)
        civ_layout.addWidget(self._civ_table)

        self._alias_table = QTableWidget(0, 6)
        self._alias_table.setHorizontalHeaderLabels(["类别", "Type", "中文名", "IconName", "图片状态", "使用原图标(别名)"])
        self._alias_table.verticalHeader().setVisible(False)
        self._alias_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._alias_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._alias_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        alias_group = QGroupBox("未导入图片实体（可选别名）")
        alias_layout = QVBoxLayout(alias_group)
        alias_layout.addWidget(self._alias_table)

        self._source_table = QTableWidget(0, 6)
        self._source_table.setHorizontalHeaderLabels(["类别", "Type", "中文名", "被取代对象", "需要ArtDef", "ArtDef模板来源"])
        self._source_table.verticalHeader().setVisible(False)
        self._source_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._source_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._source_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._source_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        source_group = QGroupBox("ArtDef 来源编辑（区域/建筑/改良/单位）")
        source_layout = QVBoxLayout(source_group)
        source_layout.addWidget(self._source_table)

        self._leader_xlp_table = QTableWidget(0, 4)
        self._leader_xlp_table.setHorizontalHeaderLabels(["LeaderType", "中文名", "输出xlp", "xlp文件名"])
        self._leader_xlp_table.verticalHeader().setVisible(False)
        self._leader_xlp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._leader_xlp_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._leader_xlp_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._leader_xlp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        leader_xlp_group = QGroupBox("领袖xlp与Leaders.artdef生成")
        leader_xlp_layout = QVBoxLayout(leader_xlp_group)
        leader_xlp_layout.addWidget(self._leader_xlp_table)

        self._moment_table = QTableWidget(0, 6)
        self._moment_table.setHorizontalHeaderLabels(["类别", "GameDataType", "中文名", "模式", "导入图片(456×332)", "数据库Texture"])
        self._moment_table.verticalHeader().setVisible(False)
        self._moment_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._moment_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._moment_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._moment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        moments_group = QGroupBox("历史时刻（Moments）插画：导入图片 / 使用数据库Texture（二选一）")
        moments_layout = QVBoxLayout(moments_group)
        moments_layout.addWidget(self._moment_table)

        self._preview_summary = QLabel("预览文件：XLP 0 | ArtDef 0 | Icons 0")
        self._preview_summary.setWordWrap(True)
        self._preview_button = QPushButton("打开预览窗口")
        self._preview_button.clicked.connect(self._open_preview_dialog)
        self._import_artxml_button = QPushButton("读取Art.xml配置")
        self._import_artxml_button.clicked.connect(self._handle_import_art_xml_from_civ6proj)

        extra_group = QGroupBox("基础模板文件（勾选后生成）")
        extra_layout = QVBoxLayout(extra_group)
        xlp_row = QHBoxLayout()
        self._extra_xlp_checks: dict[str, QCheckBox] = {}
        for filename, _content in EXTRA_XLP_TEMPLATES:
            cb = QCheckBox(filename)
            cb.stateChanged.connect(lambda _state, n=filename: self._on_extra_xlp_toggled(n))
            self._extra_xlp_checks[filename] = cb
            xlp_row.addWidget(cb)
        xlp_row.addStretch(1)
        artdef_row = QHBoxLayout()
        self._extra_artdef_checks: dict[str, QCheckBox] = {}
        for filename, _content in EXTRA_ARTDEF_TEMPLATES:
            cb = QCheckBox(filename)
            cb.stateChanged.connect(lambda _state, n=filename: self._on_extra_artdef_toggled(n))
            self._extra_artdef_checks[filename] = cb
            artdef_row.addWidget(cb)
        artdef_row.addStretch(1)
        extra_layout.addLayout(xlp_row)
        extra_layout.addLayout(artdef_row)

        controls_group = QGroupBox("输出与预览")
        controls_layout = QVBoxLayout(controls_group)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(8)
        controls_layout.addWidget(extra_group)
        controls_layout.addWidget(self._import_artxml_button, 0, Qt.AlignmentFlag.AlignLeft)
        controls_layout.addWidget(self._preview_button, 0, Qt.AlignmentFlag.AlignLeft)
        controls_layout.addWidget(self._preview_summary)

        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(info)
        content_layout.addWidget(controls_group)
        content_layout.addWidget(civ_group)
        content_layout.addWidget(alias_group)
        content_layout.addWidget(moments_group)
        content_layout.addWidget(leader_xlp_group)
        content_layout.addWidget(source_group)
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)
        self._apply_table_column_widths()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_table_column_widths()
        self._apply_leader_xlp_table_height()
        self._apply_source_table_height()
        self._apply_moment_table_height()

    @staticmethod
    def _apply_content_widths(table: QTableWidget, *, recalc_contents: bool, min_col_width: int = 44) -> None:
        """按内容调整列宽。

        目标：列宽永远不超过窗口宽度（不出现横向滚动条）。
        说明：文本过长时允许被截断；下拉选项的完整显示由 combo 的弹出列表宽度负责。
        """
        if table.columnCount() <= 0:
            return

        header = table.horizontalHeader()
        viewport_width = max(100, table.viewport().width() - 2)

        # 只有在数据变化后才按内容重算；窗口尺寸变化时只做“填充/滚动”策略。
        if recalc_contents:
            table.resizeColumnsToContents()
            for col in range(table.columnCount()):
                table.setColumnWidth(col, max(min_col_width, table.columnWidth(col)))

        total_width = sum(table.columnWidth(col) for col in range(table.columnCount()))

        widths = [max(min_col_width, table.columnWidth(col)) for col in range(table.columnCount())]
        total_width = sum(widths)

        # 内容总宽度超过窗口：按“可缩减量”把列压进窗口宽度内。
        if total_width > viewport_width:
            over = total_width - viewport_width
            reducible = [max(0, w - min_col_width) for w in widths]
            while over > 0 and any(r > 0 for r in reducible):
                idx = max(range(len(reducible)), key=lambda i: reducible[i])
                dec = min(reducible[idx], over)
                widths[idx] -= dec
                reducible[idx] -= dec
                over -= dec

        ['i] for i in combo_col_indices)\n        other_width_total = total_width - combo_width_total\n        other_indices = [i for i in range(table.columnCount()) if i not in combo_col_indices]\n\n        # 调整列宽：下拉框列保持内容宽度，其他列按比例缩放\n        if total_width > viewport_width:\n            # 下拉框列保持内容宽度\n            for col in combo_col_indices:\n                widths[col] = max(min_col_width, table.columnWidth(col))\n            \n            # 其他列按比例缩放\n            available_space = viewport_width - sum(widths[i] for i in combo_col_indices)\n            if other_width_total > 0 and other_indices:\n                scale = available_space / other_width_total if other_width_total > 0 else 1\n                for col in other_indices:\n                    widths[col] = int(widths[col] * scale)\n\n        # 应用最终列宽\n        for col, w in enumerate(widths):\n            table.setColumnWidth(col, max(min_col_width, int(w)))\n        header.setStretchLastSection(False)']

    @staticmethod
    def _ensure_combo_popup_width(combo: QComboBox, *, extra_px: int = 24, min_px: int = 220, max_px: int = 1200) -> None:
        """让下拉弹窗足够宽以显示完整选项，但不影响表格列宽。"""
        try:
            fm = QFontMetrics(combo.font())
            max_text_px = 0
            for i in range(combo.count()):
                text = combo.itemText(i) or ""
                max_text_px = max(max_text_px, fm.horizontalAdvance(text))
            popup_width = max(min_px, min(max_px, max_text_px + extra_px))
            view = combo.view()
            if view is not None:
                view.setMinimumWidth(popup_width)
        except Exception:
            return

    def _apply_table_column_widths(self) -> None:
        self._apply_content_widths(self._civ_table, recalc_contents=self._alias_columns_dirty)
        self._apply_content_widths(self._alias_table, recalc_contents=self._alias_columns_dirty)
        self._apply_content_widths(self._leader_xlp_table, recalc_contents=True)
        self._apply_content_widths(self._source_table, recalc_contents=self._source_columns_dirty)
        self._apply_content_widths(self._moment_table, recalc_contents=self._moment_columns_dirty)
        if self._civ_table.columnCount() >= 6:
            self._civ_table.setColumnWidth(3, max(200, self._civ_table.columnWidth(3)))
            self._civ_table.setColumnWidth(5, max(300, self._civ_table.columnWidth(5)))
        if self._moment_table.columnCount() >= 6:
            self._moment_table.setColumnWidth(1, max(200, self._moment_table.columnWidth(1)))
            self._moment_table.setColumnWidth(2, max(180, self._moment_table.columnWidth(2)))
            self._moment_table.setColumnWidth(4, max(360, self._moment_table.columnWidth(4)))
            self._moment_table.setColumnWidth(5, max(220, self._moment_table.columnWidth(5)))
        self._alias_columns_dirty = False
        self._source_columns_dirty = False
        self._moment_columns_dirty = False

    def _apply_leader_xlp_table_height(self) -> None:
        self._leader_xlp_table.resizeRowsToContents()
        header_height = self._leader_xlp_table.horizontalHeader().height()
        rows_height = sum(self._leader_xlp_table.rowHeight(row) for row in range(self._leader_xlp_table.rowCount()))
        frame_height = self._leader_xlp_table.frameWidth() * 2
        target = max(56, header_height + rows_height + frame_height)
        self._leader_xlp_table.setMinimumHeight(target)
        self._leader_xlp_table.setMaximumHeight(target)

    def _apply_source_table_height(self) -> None:
        self._source_table.resizeRowsToContents()
        header_height = self._source_table.horizontalHeader().height()
        rows_height = sum(self._source_table.rowHeight(row) for row in range(self._source_table.rowCount()))
        frame_height = self._source_table.frameWidth() * 2
        target = max(56, header_height + rows_height + frame_height)
        self._source_table.setMinimumHeight(target)
        self._source_table.setMaximumHeight(target)

    def _apply_moment_table_height(self) -> None:
        self._moment_table.resizeRowsToContents()
        header_height = self._moment_table.horizontalHeader().height()
        rows_height = sum(self._moment_table.rowHeight(row) for row in range(self._moment_table.rowCount()))
        frame_height = self._moment_table.frameWidth() * 2
        target = max(56, header_height + rows_height + frame_height)
        self._moment_table.setMinimumHeight(target)
        self._moment_table.setMaximumHeight(target)

    def import_project_payload(self, payload: dict[str, object] | None) -> None:
        default_state: dict[str, object] = {
            "alias_map": {},
            "source_map": {},
            "need_map": {},
            "extra_xlp_flags": {},
            "extra_artdef_flags": {},
            "civs": {},
            "moments_map": {},
            "leader_xlp_flags": {},
            "art_xml_workspace_config": {},
            "art_xml_source_config": {},
            "art_xml_source_path": "",
        }

        if not isinstance(payload, dict):
            self._state = default_state
            self._sync_extra_flags_to_ui()
            return

        # 兼容：
        # - 新结构：{"format":..., "schema_version":..., "data": {...}}
        # - 旧结构：直接把 {...} 放在“美术”节点
        fmt = payload.get("format")
        data = payload.get("data")
        if fmt == ART_SECTION_FORMAT and isinstance(data, dict):
            incoming = data
        elif isinstance(data, dict) and any(k in data for k in default_state):
            incoming = data
        else:
            incoming = payload

        merged: dict[str, object] = dict(default_state)
        if isinstance(incoming, dict):
            merged.update(incoming)
        self._state = merged

        if not isinstance(self._state.get("alias_map"), dict):
            self._state["alias_map"] = {}
        if not isinstance(self._state.get("source_map"), dict):
            self._state["source_map"] = {}
        if not isinstance(self._state.get("need_map"), dict):
            self._state["need_map"] = {}
        if not isinstance(self._state.get("extra_xlp_flags"), dict):
            self._state["extra_xlp_flags"] = {}
        if not isinstance(self._state.get("extra_artdef_flags"), dict):
            self._state["extra_artdef_flags"] = {}
        if not isinstance(self._state.get("civs"), dict):
            self._state["civs"] = {}
        if not isinstance(self._state.get("moments_map"), dict):
            self._state["moments_map"] = {}
        if not isinstance(self._state.get("leader_xlp_flags"), dict):
            self._state["leader_xlp_flags"] = {}
        if not isinstance(self._state.get("art_xml_workspace_config"), dict):
            self._state["art_xml_workspace_config"] = {}
        if not isinstance(self._state.get("art_xml_source_config"), dict):
            self._state["art_xml_source_config"] = {}
        if not isinstance(self._state.get("art_xml_source_path"), str):
            self._state["art_xml_source_path"] = ""

        self._sync_extra_flags_to_ui()

        try:
            LOGGER.info(
                "[ArtWorkspace] payload imported: alias=%d source=%d need=%d civs=%d moments=%d",
                len(self._state.get("alias_map") or {}) if isinstance(self._state.get("alias_map"), dict) else -1,
                len(self._state.get("source_map") or {}) if isinstance(self._state.get("source_map"), dict) else -1,
                len(self._state.get("need_map") or {}) if isinstance(self._state.get("need_map"), dict) else -1,
                len(self._state.get("civs") or {}) if isinstance(self._state.get("civs"), dict) else -1,
                len(self._state.get("moments_map") or {}) if isinstance(self._state.get("moments_map"), dict) else -1,
            )
        except Exception:
            return

    def export_project_payload(self) -> dict[str, object]:
        alias_map = self._state.get("alias_map") if isinstance(self._state.get("alias_map"), dict) else {}
        source_map = self._state.get("source_map") if isinstance(self._state.get("source_map"), dict) else {}
        need_map = self._state.get("need_map") if isinstance(self._state.get("need_map"), dict) else {}
        extra_xlp_flags = self._state.get("extra_xlp_flags") if isinstance(self._state.get("extra_xlp_flags"), dict) else {}
        extra_artdef_flags = self._state.get("extra_artdef_flags") if isinstance(self._state.get("extra_artdef_flags"), dict) else {}
        civs = self._state.get("civs") if isinstance(self._state.get("civs"), dict) else {}
        moments_map = self._state.get("moments_map") if isinstance(self._state.get("moments_map"), dict) else {}
        leader_xlp_flags = self._state.get("leader_xlp_flags") if isinstance(self._state.get("leader_xlp_flags"), dict) else {}
        workspace_art = self._state.get("art_xml_workspace_config") if isinstance(self._state.get("art_xml_workspace_config"), dict) else {}
        source_art = self._state.get("art_xml_source_config") if isinstance(self._state.get("art_xml_source_config"), dict) else {}
        source_path = str(self._state.get("art_xml_source_path") or "").strip()
        workspace_art = self._normalize_art_xml_config(workspace_art)
        source_art = self._normalize_art_xml_config(source_art)
        return {
            "format": ART_SECTION_FORMAT,
            "schema_version": ART_SECTION_SCHEMA,
            "data": {
                "alias_map": dict(alias_map),
                "source_map": dict(source_map),
                "need_map": {str(k): bool(v) for k, v in need_map.items()},
                "extra_xlp_flags": {str(k): bool(v) for k, v in extra_xlp_flags.items()},
                "extra_artdef_flags": {str(k): bool(v) for k, v in extra_artdef_flags.items()},
                "civs": dict(civs),
                "moments_map": dict(moments_map),
                "leader_xlp_flags": {str(k): bool(v) for k, v in leader_xlp_flags.items()},
                "art_xml_workspace_config": workspace_art,
                "art_xml_source_config": source_art,
                "art_xml_source_path": source_path,
            },
        }

    def refresh_from_sections(self, sections: dict[str, object]) -> None:
        self._sections = sections if isinstance(sections, dict) else {}
        self._replacement_maps = self._load_replacement_maps()
        self._civ_source_options = self._load_civ_source_options()
        self._alias_options = self._load_alias_options()
        self._source_options = self._load_source_options()
        try:
            self._moment_texture_options = self._load_moment_texture_options()
        except Exception:
            LOGGER.exception("[ArtWorkspace] load moment texture options failed")
            self._moment_texture_options = []
        self._civ_rows = self._build_civ_rows()
        self._alias_rows = self._build_alias_rows()
        self._source_rows = self._build_source_rows()
        self._leader_xlp_rows = self._build_leader_xlp_rows()
        try:
            self._moment_rows = self._build_moment_rows()
        except Exception:
            LOGGER.exception("[ArtWorkspace] build moment rows failed")
            self._moment_rows = []
        self._render_civ_table()
        self._render_alias_table()
        try:
            self._render_moment_table()
        except Exception:
            LOGGER.exception("[ArtWorkspace] render moment table failed")
        self._render_source_table()
        self._render_leader_xlp_table()
        self._state["art_xml_workspace_config"] = self._build_workspace_art_xml_config()
        self._try_auto_import_source_art_xml()
        self._refresh_previews()
        try:
            need_map = self._state_need_map()
            need_hits = sum(1 for r in self._source_rows if need_map.get(r.state_key))
        except Exception:
            need_hits = -1
        LOGGER.info(
            "[ArtWorkspace] refreshed rows: civ=%d alias=%d moment=%d source=%d | need_hits=%s",
            len(self._civ_rows),
            len(self._alias_rows),
            len(self._moment_rows),
            len(self._source_rows),
            str(need_hits),
        )

    def _state_moments_map(self) -> dict[str, dict[str, object]]:
        raw = self._state.get("moments_map")
        if not isinstance(raw, dict):
            raw = {}
            self._state["moments_map"] = raw
        cleaned: dict[str, dict[str, object]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            key = str(k)
            if not key.strip():
                continue
            cleaned[key] = v
        return cleaned

    def _moment_meta(self, key: str) -> dict[str, object]:
        moments = self._state_moments_map()
        meta = moments.get(key)
        if not isinstance(meta, dict):
            meta = {}
        mode = _safe_text(meta.get("mode"))
        if mode not in {"import", "db"}:
            meta["mode"] = "import"
        image = meta.get("image")
        if not isinstance(image, dict):
            meta["image"] = {}
        if "db_texture" not in meta:
            meta["db_texture"] = ""
        moments[key] = meta
        self._state["moments_map"] = moments
        return meta

    def _load_moment_texture_options(self) -> list[str]:
        db_path = Path(load_settings().game_db_path)
        if not db_path.exists():
            db_path = DEFAULT_GAME_DB
        if not db_path.exists():
            return []

        textures: list[str] = []
        try:
            with sqlite3.connect(str(db_path)) as conn:
                rows = conn.execute(
                    "SELECT DISTINCT Texture FROM MomentIllustrations WHERE IFNULL(Texture,'') <> '' ORDER BY Texture"
                ).fetchall()
            for (tex,) in rows:
                t = _safe_text(tex)
                if t:
                    textures.append(t)
        except sqlite3.Error:
            return []
        return textures

    @staticmethod
    def _extract_trait_type(entry: dict[str, object]) -> str:
        table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
        return _safe_text(
            table_data.get("TraitType")
            or entry.get("TraitType")
            or entry.get("trait_type")
            or entry.get("traitType")
        )

    @staticmethod
    def _moment_types_for_entity(entity: str) -> tuple[str, str] | None:
        mapping: dict[str, tuple[str, str]] = {
            "district": ("MOMENT_ILLUSTRATION_UNIQUE_DISTRICT", "MOMENT_DATA_DISTRICT"),
            "building": ("MOMENT_ILLUSTRATION_UNIQUE_BUILDING", "MOMENT_DATA_BUILDING"),
            "unit": ("MOMENT_ILLUSTRATION_UNIQUE_UNIT", "MOMENT_DATA_UNIT"),
            "improvement": ("MOMENT_ILLUSTRATION_UNIQUE_IMPROVEMENT", "MOMENT_DATA_IMPROVEMENT"),
            "governor": ("MOMENT_ILLUSTRATION_GOVERNOR", "MOMENT_DATA_GOVERNOR"),
        }
        return mapping.get(entity)

    def _build_moment_rows(self) -> list[_MomentRow]:
        rows: list[_MomentRow] = []
        seen: set[tuple[str, str]] = set()

        def _add(entity: str, game_data_type: str, cn: str, illustration: str, data_type: str) -> None:
            key = (entity, game_data_type)
            if not game_data_type or key in seen:
                return
            seen.add(key)
            rows.append(
                _MomentRow(
                    entity=entity,
                    game_data_type=game_data_type,
                    chinese_name=cn or game_data_type,
                    moment_illustration_type=illustration,
                    moment_data_type=data_type,
                )
            )

        # 1) 区域/建筑/单位/改良设施：仅 TraitType 非空者
        for type_name, cn, entry in self._collect_new_items("区域", name_key="Name"):
            if not self._extract_trait_type(entry):
                continue
            _add("district", type_name, cn, "MOMENT_ILLUSTRATION_UNIQUE_DISTRICT", "MOMENT_DATA_DISTRICT")

        for type_name, cn, entry in self._collect_new_items("建筑", name_key="Name"):
            if not self._extract_trait_type(entry):
                continue
            _add("building", type_name, cn, "MOMENT_ILLUSTRATION_UNIQUE_BUILDING", "MOMENT_DATA_BUILDING")

        for type_name, cn, entry in self._collect_new_items("单位", name_key="Name"):
            if not self._extract_trait_type(entry):
                continue
            _add("unit", type_name, cn, "MOMENT_ILLUSTRATION_UNIQUE_UNIT", "MOMENT_DATA_UNIT")

        for type_name, cn, entry in self._collect_new_items("改良设施", name_key="Name"):
            if not self._extract_trait_type(entry):
                continue
            _add("improvement", type_name, cn, "MOMENT_ILLUSTRATION_UNIQUE_IMPROVEMENT", "MOMENT_DATA_IMPROVEMENT")

        # 2) 总督：始终可配置（不依赖 new_trait_type）
        for gov_type, cn, _entry in self._collect_new_items("总督"):
            if not _safe_text(gov_type):
                continue
            _add("governor", gov_type, cn, "MOMENT_ILLUSTRATION_GOVERNOR", "MOMENT_DATA_GOVERNOR")

        # 3) 伟人：映射到其单位（UnitType），且需 TraitType
        for _gp_type, cn, entry in self._collect_new_items("伟人"):
            unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
            unit_type = _safe_text(unit_data.get("UnitType") or entry.get("unit_type"))
            if not unit_type:
                continue
            if not _safe_text(unit_data.get("TraitType")):
                continue
            display = _safe_text(unit_data.get("Name")) or cn
            _add("unit", unit_type, display, "MOMENT_ILLUSTRATION_UNIQUE_UNIT", "MOMENT_DATA_UNIT")

        # 4) 清理：重命名/删除后遗留的 moments_map 旧 key 不应继续显示或导出。
        try:
            moments_map = self._state_moments_map()
            valid_keys = {r.state_key for r in rows}
            stale_keys = [k for k in moments_map.keys() if _safe_text(k).startswith("moment:") and k not in valid_keys]
            if stale_keys:
                for k in stale_keys:
                    moments_map.pop(k, None)
                self._state["moments_map"] = moments_map
                LOGGER.info("[ArtWorkspace] cleaned stale moment keys: %d", len(stale_keys))
        except Exception:
            LOGGER.exception("[ArtWorkspace] cleanup stale moment keys failed")

        rows.sort(key=lambda r: (r.entity, r.game_data_type))
        return rows

    def _render_moment_table(self) -> None:
        self._updating = True
        try:
            self._moment_table.setRowCount(0)
            moments_map = self._state_moments_map()
            for row_idx, row in enumerate(self._moment_rows):
                self._moment_table.insertRow(row_idx)
                self._moment_table.setItem(row_idx, 0, QTableWidgetItem(row.entity))
                self._moment_table.setItem(row_idx, 1, QTableWidgetItem(row.game_data_type))
                self._moment_table.setItem(row_idx, 2, QTableWidgetItem(row.chinese_name))

                meta = self._moment_meta(row.state_key)

                mode_combo = QComboBox()
                mode_combo.addItem("导入图片", "import")
                mode_combo.addItem("数据库Texture", "db")
                mode_value = _safe_text(meta.get("mode"))
                if mode_value:
                    idx = mode_combo.findData(mode_value)
                    if idx >= 0:
                        mode_combo.setCurrentIndex(idx)

                image_payload = meta.get("image") if isinstance(meta.get("image"), dict) else {}
                image_path = _safe_text(image_payload.get("path"))
                image_label = QLabel(Path(image_path).name if image_path else "（未选择）")
                image_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                image_btn = QPushButton("选择图片")
                image_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                image_btn.clicked.connect(
                    lambda _checked=False, key=row.state_key, label=image_label: self._handle_moment_pick_image(key, label)
                )
                image_cell = QWidget()
                image_layout = QHBoxLayout(image_cell)
                image_layout.setContentsMargins(0, 0, 0, 0)
                image_layout.setSpacing(6)
                image_layout.addWidget(image_label, 1)
                image_layout.addWidget(image_btn, 0)

                tex_selector = MomentTextureSearchTemplate(compact=True)
                tex_selector.set_options(self._moment_texture_options, preserve_value=False)
                current_tex = _safe_text(meta.get("db_texture"))
                tex_selector.set_current_value(current_tex)
                tex_selector.setMinimumWidth(180)

                def _apply_enabled() -> None:
                    mode = _safe_text(mode_combo.currentData())
                    is_import = mode != "db"
                    image_label.setEnabled(is_import)
                    image_btn.setEnabled(is_import)
                    # 搜索输入框始终显示；导入模式下也允许预先填写 db_texture。
                    tex_selector.setEnabled(True)

                _apply_enabled()

                mode_combo.currentIndexChanged.connect(
                    lambda _idx, cb=mode_combo, key=row.state_key, apply=_apply_enabled: self._handle_moment_mode_changed(key, cb, apply)
                )
                tex_selector.dataChanged.connect(
                    lambda key=row.state_key, w=tex_selector: self._handle_moment_texture_changed(key, w)
                )

                self._moment_table.setCellWidget(row_idx, 3, mode_combo)
                self._moment_table.setCellWidget(row_idx, 4, image_cell)
                self._moment_table.setCellWidget(row_idx, 5, tex_selector)
                self._moment_table.setRowHeight(row_idx, 34)

            self._moment_columns_dirty = True
            self._apply_table_column_widths()
            self._apply_moment_table_height()
        finally:
            self._updating = False

    def _handle_moment_mode_changed(self, key: str, combo: QComboBox, apply_enabled) -> None:
        if self._updating:
            return
        meta = self._moment_meta(key)
        meta["mode"] = _safe_text(combo.currentData()) or "import"
        moments = self._state_moments_map()
        moments[key] = meta
        self._state["moments_map"] = moments
        try:
            apply_enabled()
        except Exception:
            pass

    def _handle_moment_texture_changed(self, key: str, widget: MomentTextureSearchTemplate) -> None:
        if self._updating:
            return
        meta = self._moment_meta(key)
        meta["db_texture"] = _safe_text(widget.current_value())
        moments = self._state_moments_map()
        moments[key] = meta
        self._state["moments_map"] = moments

    def _handle_moment_pick_image(self, key: str, label: QLabel) -> None:
        if self._updating:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择历史时刻图片（456×332）",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        clean = _safe_text(file_path)
        if not clean:
            return
        meta = self._moment_meta(key)
        image = meta.get("image") if isinstance(meta.get("image"), dict) else {}
        image["path"] = clean
        meta["image"] = image
        moments = self._state_moments_map()
        moments[key] = meta
        self._state["moments_map"] = moments
        label.setText(Path(clean).name)

    def _state_alias_map(self) -> dict[str, str]:
        alias_map = self._state.get("alias_map")
        if not isinstance(alias_map, dict):
            alias_map = {}
            self._state["alias_map"] = alias_map
        return {str(k): _safe_text(v) for k, v in alias_map.items() if _safe_text(v)}

    def _state_source_map(self) -> dict[str, str]:
        source_map = self._state.get("source_map")
        if not isinstance(source_map, dict):
            source_map = {}
            self._state["source_map"] = source_map
        return {str(k): _safe_text(v) for k, v in source_map.items() if _safe_text(v)}

    def _state_need_map(self) -> dict[str, bool]:
        need_map = self._state.get("need_map")
        if not isinstance(need_map, dict):
            need_map = {}
            self._state["need_map"] = need_map
        return {str(k): bool(v) for k, v in need_map.items()}

    def _set_alias(self, key: str, value: str) -> None:
        alias_map = self._state_alias_map()
        clean = _safe_text(value)
        if clean:
            alias_map[key] = clean
        elif key in alias_map:
            alias_map.pop(key, None)
        self._state["alias_map"] = alias_map

    def _set_source(self, key: str, value: str) -> None:
        source_map = self._state_source_map()
        clean = _safe_text(value)
        if clean:
            source_map[key] = clean
        elif key in source_map:
            source_map.pop(key, None)
        self._state["source_map"] = source_map

    def _set_need(self, key: str, value: bool) -> None:
        need_map = self._state_need_map()
        need_map[key] = bool(value)
        self._state["need_map"] = need_map

    def _state_extra_xlp_flags(self) -> dict[str, bool]:
        data = self._state.get("extra_xlp_flags")
        if not isinstance(data, dict):
            data = {}
            self._state["extra_xlp_flags"] = data
        return {str(k): bool(v) for k, v in data.items()}

    def _state_extra_artdef_flags(self) -> dict[str, bool]:
        data = self._state.get("extra_artdef_flags")
        if not isinstance(data, dict):
            data = {}
            self._state["extra_artdef_flags"] = data
        return {str(k): bool(v) for k, v in data.items()}

    def _sync_extra_flags_to_ui(self) -> None:
        self._updating = True
        try:
            xlp_flags = self._state_extra_xlp_flags()
            for filename, checkbox in self._extra_xlp_checks.items():
                checkbox.setChecked(bool(xlp_flags.get(filename, False)))
            artdef_flags = self._state_extra_artdef_flags()
            for filename, checkbox in self._extra_artdef_checks.items():
                checkbox.setChecked(bool(artdef_flags.get(filename, False)))
        finally:
            self._updating = False

    def _on_extra_xlp_toggled(self, filename: str) -> None:
        if self._updating:
            return
        flags = self._state_extra_xlp_flags()
        flags[filename] = bool(self._extra_xlp_checks[filename].isChecked())
        self._state["extra_xlp_flags"] = flags
        self._refresh_previews()

    def _on_extra_artdef_toggled(self, filename: str) -> None:
        if self._updating:
            return
        flags = self._state_extra_artdef_flags()
        flags[filename] = bool(self._extra_artdef_checks[filename].isChecked())
        self._state["extra_artdef_flags"] = flags
        self._refresh_previews()

    def _load_replacement_maps(self) -> dict[str, dict[str, str]]:
        maps: dict[str, dict[str, str]] = {
            "district": {},
            "building": {},
            "improvement": {},
            "unit": {},
        }

        db_path = _active_game_db_path()
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                try:
                    queries = {
                        "district": "SELECT CivUniqueDistrictType, ReplacesDistrictType FROM DistrictReplaces",
                        "building": "SELECT CivUniqueBuildingType, ReplacesBuildingType FROM BuildingReplaces",
                        "improvement": "SELECT CivUniqueImprovementType, ReplacesImprovementType FROM ImprovementReplaces",
                        "unit": "SELECT CivUniqueUnitType, ReplacesUnitType FROM UnitReplaces",
                    }
                    for entity, query in queries.items():
                        try:
                            for unique_type, replaces_type in conn.execute(query).fetchall():
                                u = _safe_text(unique_type)
                                r = _safe_text(replaces_type)
                                if u and r:
                                    maps[entity][u] = r
                        except sqlite3.Error:
                            continue
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                LOGGER.warning("[ArtWorkspace] replacement maps DB load failed: %s", exc)

        for type_name, _cn, entry in self._collect_new_items("区域", name_key="Name"):
            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
            replaces = subtables.get("DistrictReplaces") if isinstance(subtables.get("DistrictReplaces"), dict) else entry.get("district_replaces") if isinstance(entry.get("district_replaces"), dict) else {}
            replaces_type = _safe_text(replaces.get("ReplacesDistrictType"))
            if replaces_type:
                maps["district"][type_name] = replaces_type

        for type_name, _cn, entry in self._collect_new_items("建筑", name_key="Name"):
            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
            replaces = subtables.get("BuildingReplaces") if isinstance(subtables.get("BuildingReplaces"), dict) else entry.get("building_replaces") if isinstance(entry.get("building_replaces"), dict) else {}
            replaces_type = _safe_text(replaces.get("ReplacesBuildingType"))
            if replaces_type:
                maps["building"][type_name] = replaces_type

        for type_name, _cn, entry in self._collect_new_items("单位", name_key="Name"):
            subtables = entry.get("subtables") if isinstance(entry.get("subtables"), dict) else {}
            replaces = subtables.get("UnitReplaces") if isinstance(subtables.get("UnitReplaces"), dict) else entry.get("unit_replaces") if isinstance(entry.get("unit_replaces"), dict) else {}
            replaces_type = _safe_text(replaces.get("ReplacesUnitType"))
            if replaces_type:
                maps["unit"][type_name] = replaces_type

        for type_name, _cn, entry in self._collect_new_items("改良设施", name_key="Name"):
            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            replaces_type = _safe_text(table_data.get("ReplacesImprovementType"))
            if replaces_type:
                maps["improvement"][type_name] = replaces_type

        return maps

    def _build_display_by_type(self, entity: str) -> dict[str, str]:
        output: dict[str, str] = {}
        for type_name, cn_name in self._alias_options.get(entity, []):
            output[type_name] = f"{type_name} | {cn_name}"
        return output

    def _load_civ_source_options(self) -> list[tuple[str, str]]:
        if list_civilization_artdef_names is None:
            return []
        try:
            names = list_civilization_artdef_names()
        except Exception as exc:
            LOGGER.warning("[ArtWorkspace] load civilization source options failed: %s", exc)
            return []
        labels = self._load_civilization_display_labels(names)
        return [(name, labels.get(name, name)) for name in names]

    def _load_civilization_display_labels(self, civ_types: list[str]) -> dict[str, str]:
        output = {civ_type: civ_type for civ_type in civ_types if _safe_text(civ_type)}
        if not output:
            return output

        db_path = _active_game_db_path()
        if not db_path.exists():
            return output

        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return output

        try:
            rows = conn.execute(
                "SELECT CivilizationType, IFNULL(Name, '') FROM Civilizations"
            ).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()

        for civ_type_raw, name_tag_raw in rows:
            civ_type = _safe_text(civ_type_raw)
            if not civ_type or civ_type not in output:
                continue
            name_tag = _safe_text(name_tag_raw)
            if not name_tag:
                continue
            cn = resolve_chinese_text_or_unknown(name_tag)
            if _safe_text(cn) and cn != "未知":
                output[civ_type] = f"{civ_type} | {cn}"
        return output

    def _build_civ_rows(self) -> list[_CivArtRow]:
        section_items = self._collect_new_items("文明")
        section_types = [type_name for type_name, _cn, _entry in section_items if _safe_text(type_name)]
        state_types = list(self._state_civ_art_map().keys())
        civ_types = sorted({*section_types, *state_types})
        labels = self._load_civilization_display_labels(civ_types)
        rows: list[_CivArtRow] = []
        for civ_type, cn, _entry in section_items:
            display_cn = cn
            if not _safe_text(display_cn):
                label = labels.get(civ_type, "")
                display_cn = label.split("|", 1)[1].strip() if "|" in label else ""
            rows.append(_CivArtRow(civ_type=civ_type, chinese_name=display_cn))

        # 兼容：旧工程 state 中有 civs，但“文明”分区条目丢失/结构变更导致无法枚举时，仍显示出来。
        missing = [c for c in state_types if c not in set(section_types)]
        for civ_type in sorted(missing):
            label = labels.get(civ_type, "")
            display_cn = label.split("|", 1)[1].strip() if "|" in label else ""
            rows.append(_CivArtRow(civ_type=civ_type, chinese_name=display_cn or "（已丢失对象）"))

        rows.sort(key=lambda r: r.civ_type)
        return rows

    def _civ_meta(self, civ_type: str) -> dict[str, object]:
        civs = self._state_civ_art_map()
        meta = civs.get(civ_type)
        if not isinstance(meta, dict):
            meta = {}
        if "need" not in meta:
            meta["need"] = False
        if "music_source" not in meta:
            meta["music_source"] = ""
        cultures = meta.get("cultures")
        if not isinstance(cultures, dict):
            meta["cultures"] = {}
        civs[civ_type] = meta
        self._state["civs"] = civs
        return meta

    @staticmethod
    def _culture_count(meta: dict[str, object]) -> int:
        cultures = meta.get("cultures") if isinstance(meta.get("cultures"), dict) else {}
        total = 0
        for values in cultures.values():
            if isinstance(values, (list, tuple, set)):
                total += len({str(v) for v in values if _safe_text(v)})
        return total

    def _render_civ_table(self) -> None:
        self._updating = True
        try:
            self._civ_table.setRowCount(0)
            for row_index, row in enumerate(self._civ_rows):
                self._civ_table.insertRow(row_index)
                self._civ_table.setItem(row_index, 0, QTableWidgetItem(row.civ_type))
                self._civ_table.setItem(row_index, 1, QTableWidgetItem(row.chinese_name))
                self._civ_table.setItem(row_index, 2, QTableWidgetItem(f"ICON_{row.civ_type}"))

                meta = self._civ_meta(row.civ_type)

                culture_button = QPushButton(f"文化 ({self._culture_count(meta)})")
                culture_button.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
                culture_button.setMinimumWidth(120)
                culture_button.setMinimumHeight(30)
                culture_button.clicked.connect(
                    lambda _checked=False, civ_type=row.civ_type, button=culture_button: self._open_culture_picker(civ_type, button)
                )
                self._civ_table.setCellWidget(row_index, 3, culture_button)
                self._civ_table.setRowHeight(row_index, 36)

                need_box = QCheckBox()
                need_box.setChecked(bool(meta.get("need")))
                need_box.stateChanged.connect(
                    lambda _state, cb=need_box, civ_type=row.civ_type: self._handle_civ_need_changed(civ_type, cb)
                )
                self._civ_table.setCellWidget(row_index, 4, need_box)

                music_combo = QComboBox()
                music_combo.addItem("", "")
                for source_type, display in self._civ_source_options:
                    music_combo.addItem(display, source_type)
                music_source = _safe_text(meta.get("music_source"))
                if music_source:
                    idx = music_combo.findData(music_source)
                    if idx >= 0:
                        music_combo.setCurrentIndex(idx)
                music_combo.currentIndexChanged.connect(
                    lambda _idx, cb=music_combo, civ_type=row.civ_type: self._handle_civ_music_changed(civ_type, cb)
                )
                self._ensure_combo_popup_width(music_combo)
                self._civ_table.setCellWidget(row_index, 5, music_combo)

            self._alias_columns_dirty = True
            self._apply_table_column_widths()
        finally:
            self._updating = False

    def _handle_civ_need_changed(self, civ_type: str, checkbox: QCheckBox) -> None:
        if self._updating:
            return
        meta = self._civ_meta(civ_type)
        meta["need"] = bool(checkbox.isChecked())
        self._refresh_previews()

    def _handle_civ_music_changed(self, civ_type: str, combo: QComboBox) -> None:
        if self._updating:
            return
        meta = self._civ_meta(civ_type)
        meta["music_source"] = _safe_text(combo.currentData())
        self._refresh_previews()

    def _open_culture_picker(self, civ_type: str, button: QPushButton) -> None:
        meta = self._civ_meta(civ_type)
        if not bool(meta.get("need")):
            return

        current_raw = meta.get("cultures") if isinstance(meta.get("cultures"), dict) else {}
        current: dict[str, list[str]] = {}
        for collection, values in current_raw.items():
            if isinstance(values, (list, tuple, set)):
                current[str(collection)] = sorted({str(v) for v in values if _safe_text(v)})

        dialog = _CulturePickerDialog(civ_type, _CULTURE_GROUPS_FALLBACK, current, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        meta["cultures"] = dialog.selected_groups()
        button.setText(f"文化 ({self._culture_count(meta)})")
        self._refresh_previews()

    def _load_source_options(self) -> dict[str, list[tuple[str, str]]]:
        options: dict[str, list[tuple[str, str]]] = {"district": [], "building": [], "improvement": [], "unit": []}
        display_maps = {
            "district": self._build_display_by_type("district"),
            "building": self._build_display_by_type("building"),
            "improvement": self._build_display_by_type("improvement"),
            "unit": self._build_display_by_type("unit"),
        }

        loaders = {
            "district": list_district_artdef_names,
            "building": list_building_artdef_names,
            "improvement": list_improvement_artdef_names,
            "unit": list_unit_artdef_names,
        }

        for entity, loader in loaders.items():
            if loader is None:
                options[entity] = []
                continue
            try:
                names = loader()
            except Exception as exc:
                LOGGER.warning("[ArtWorkspace] load source options failed entity=%s err=%s", entity, exc)
                names = []
            display_map = display_maps[entity]
            options[entity] = [(name, display_map.get(name) or name) for name in names]

        return options

    def _load_alias_options(self) -> dict[str, list[tuple[str, str]]]:
        db_path = _active_game_db_path()
        if not db_path.exists():
            LOGGER.warning("[ArtWorkspace] alias options skipped: game DB not found at %s", db_path)
            return {}

        config: dict[str, tuple[str, str, str]] = {
            "district": ("Districts", "DistrictType", "Name"),
            "building": ("Buildings", "BuildingType", "Name"),
            "improvement": ("Improvements", "ImprovementType", "Name"),
            "unit": ("Units", "UnitType", "Name"),
            "project": ("Projects", "ProjectType", "Name"),
            "belief": ("Beliefs", "BeliefType", "Name"),
        }

        output: dict[str, list[tuple[str, str]]] = {}
        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error as exc:
            LOGGER.warning("[ArtWorkspace] alias options open DB failed: %s", exc)
            return output

        try:
            for entity, (table_name, type_col, name_col) in config.items():
                rows: list[tuple[str, str]] = []
                try:
                    raw_rows = conn.execute(
                        f"SELECT {type_col}, IFNULL({name_col}, '') FROM {table_name} ORDER BY {type_col}"
                    ).fetchall()
                except sqlite3.Error as exc:
                    LOGGER.warning("[ArtWorkspace] alias query failed for %s: %s", table_name, exc)
                    output[entity] = []
                    continue
                for type_name, name_tag in raw_rows:
                    t = _safe_text(type_name)
                    if not t:
                        continue
                    cn = resolve_chinese_text_or_unknown(_safe_text(name_tag)) if _safe_text(name_tag) else "未知"
                    rows.append((t, cn if cn and cn != "未知" else t))
                output[entity] = rows
                LOGGER.info("[ArtWorkspace] loaded alias options entity=%s count=%d", entity, len(rows))
        finally:
            conn.close()

        return output

    @staticmethod
    def _iter_entries(section_value: object) -> list[dict[str, object]]:
        if not isinstance(section_value, list):
            return []
        return [item for item in section_value if isinstance(item, dict)]

    @staticmethod
    def _image_path(entry: dict[str, object], key: str = "icon") -> str:
        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        payload = images.get(key) if isinstance(images.get(key), dict) else {}
        return _safe_text(payload.get("path"))

    def _collect_new_items(self, section: str, *, name_key: str | None = None) -> list[tuple[str, str, dict[str, object]]]:
        output: list[tuple[str, str, dict[str, object]]] = []
        section_type_fallbacks: dict[str, tuple[str, ...]] = {
            "总督": ("GovernorType",),
            "政策卡": ("PolicyType",),
            "项目": ("ProjectType",),
            "信仰": ("BeliefType",),
        }
        type_keys = ("type", *section_type_fallbacks.get(section, ()))
        for entry in self._iter_entries(self._sections.get(section)):
            type_name = ""
            for key in type_keys:
                type_name = _safe_text(entry.get(key))
                if type_name:
                    break
            if not type_name:
                continue
            cn = ""
            if name_key:
                table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
                cn = _safe_text(table_data.get(name_key))
            if not cn:
                cn = _safe_text(entry.get("name"))
            output.append((type_name, cn or "（未命名）", entry))
        return output

    def _build_alias_rows(self) -> list[_AliasRow]:
        rows: list[_AliasRow] = []

        for type_name, cn, entry in self._collect_new_items("区域", name_key="Name"):
            if self._image_path(entry, "icon"):
                continue
            rows.append(_AliasRow("district", type_name, cn, f"ICON_{type_name}", "icon"))

        for type_name, cn, entry in self._collect_new_items("建筑", name_key="Name"):
            if self._image_path(entry, "icon"):
                continue
            rows.append(_AliasRow("building", type_name, cn, f"ICON_{type_name}", "icon"))

        for type_name, cn, entry in self._collect_new_items("改良设施", name_key="Name"):
            if self._image_path(entry, "icon"):
                continue
            rows.append(_AliasRow("improvement", type_name, cn, f"ICON_{type_name}", "icon"))

        for type_name, cn, entry in self._collect_new_items("单位", name_key="Name"):
            if not self._image_path(entry, "icon"):
                rows.append(_AliasRow("unit", type_name, cn, f"ICON_{type_name}", "icon"))
            if not self._image_path(entry, "portrait"):
                rows.append(_AliasRow("unit", type_name, cn, f"ICON_{type_name}_PORTRAIT", "portrait"))

        for _type_name, _cn, entry in self._collect_new_items("伟人"):
            unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
            unit_type = _safe_text(unit_data.get("UnitType") or entry.get("unit_type"))
            if not unit_type:
                continue
            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
            icon_payload = images.get("unit_icon") if isinstance(images.get("unit_icon"), dict) else {}
            portrait_payload = images.get("unit_portrait") if isinstance(images.get("unit_portrait"), dict) else {}
            icon_path = _safe_text(icon_payload.get("path"))
            portrait_path = _safe_text(portrait_payload.get("path"))
            display_name = _safe_text(unit_data.get("Name") or entry.get("name")) or unit_type
            if not icon_path:
                rows.append(_AliasRow("unit", unit_type, display_name, f"ICON_{unit_type}", "icon"))
            if not portrait_path:
                rows.append(_AliasRow("unit", unit_type, display_name, f"ICON_{unit_type}_PORTRAIT", "portrait"))

        for type_name, cn, entry in self._collect_new_items("项目", name_key="Name"):
            if self._image_path(entry, "icon"):
                continue
            rows.append(_AliasRow("project", type_name, cn, f"ICON_{type_name}", "icon"))

        for type_name, cn, entry in self._collect_new_items("信仰", name_key="Name"):
            if self._image_path(entry, "icon"):
                continue
            rows.append(_AliasRow("belief", type_name, cn, f"ICON_{type_name}", "icon"))

        return rows

    def _render_alias_table(self) -> None:
        self._updating = True
        try:
            self._alias_table.setRowCount(0)
            alias_map = self._state_alias_map()
            for row_idx, row in enumerate(self._alias_rows):
                self._alias_table.insertRow(row_idx)
                self._alias_table.setItem(row_idx, 0, QTableWidgetItem(row.entity))
                self._alias_table.setItem(row_idx, 1, QTableWidgetItem(row.type_name))
                self._alias_table.setItem(row_idx, 2, QTableWidgetItem(row.chinese_name))
                self._alias_table.setItem(row_idx, 3, QTableWidgetItem(row.icon_name))
                self._alias_table.setItem(row_idx, 4, QTableWidgetItem("未导入" if row.variant == "icon" else "肖像未导入"))

                combo = QComboBox()
                combo.setEditable(True)
                combo.addItem("", "")
                options = list(self._alias_options.get(row.entity, []))
                replacement = _safe_text(self._replacement_maps.get(row.entity, {}).get(row.type_name))
                if replacement:
                    base_pair = next((p for p in options if p[0] == replacement), None)
                    if base_pair is None:
                        options.insert(0, (replacement, replacement))
                    else:
                        options = [base_pair] + [p for p in options if p[0] != replacement]

                for alias_type, cn_name in options:
                    prefix = "★ " if replacement and alias_type == replacement else ""
                    label = f"{prefix}{alias_type} | {cn_name}"
                    combo.addItem(label, alias_type)
                current_alias = _safe_text(alias_map.get(row.state_key))
                if current_alias:
                    idx = combo.findData(current_alias)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    else:
                        combo.setEditText(current_alias)
                self._ensure_combo_popup_width(combo)
                combo.currentTextChanged.connect(
                    lambda _text, cb=combo, key=row.state_key: self._handle_alias_changed(cb, key)
                )
                self._alias_table.setCellWidget(row_idx, 5, combo)

            self._alias_columns_dirty = True
            self._apply_table_column_widths()
        finally:
            self._updating = False

    def _handle_alias_changed(self, combo: QComboBox, key: str) -> None:
        if self._updating:
            return
        value = _safe_text(combo.currentData())
        if not value:
            raw = _safe_text(combo.currentText())
            value = raw
        if value and not value.startswith("ICON_") and "|" not in value and " " not in value:
            value = f"ICON_{value}" if not value.startswith("ICON_") else value

        # 单位肖像别名规范化：ICON_UNIT_*_PORTRAIT 必须指向 portrait 图标。
        # 旧逻辑/旧数据可能会把肖像别名写成 ICON_UNIT_XXX（缺少 _PORTRAIT），导致 Icons.xml OtherName 不正确。
        if key.startswith("unit:") and key.endswith(":portrait"):
            clean = _safe_text(value)
            if clean and clean.startswith("ICON_UNIT_") and not clean.endswith("_PORTRAIT"):
                value = f"{clean}_PORTRAIT"
        self._set_alias(key, value)
        self._refresh_previews()

    def _build_source_rows(self) -> list[_ArtdefSourceRow]:
        rows: list[_ArtdefSourceRow] = []
        mappings = [
            ("district", "区域"),
            ("building", "建筑"),
            ("improvement", "改良设施"),
            ("unit", "单位"),
        ]
        for entity, section in mappings:
            replace_map = self._replacement_maps.get(entity, {})
            for type_name, cn, _entry in self._collect_new_items(section, name_key="Name"):
                rows.append(
                    _ArtdefSourceRow(
                        entity=entity,
                        type_name=type_name,
                        chinese_name=cn,
                        replacement_type=_safe_text(replace_map.get(type_name)),
                    )
                )

        # 兼容：旧工程 state 中有 need/source，但对应分区条目缺失时，补“孤儿行”避免看起来像没导入。
        seen = {r.state_key for r in rows}
        state_keys: set[str] = set()
        try:
            state_keys |= set(self._state_need_map().keys())
        except Exception:
            pass
        try:
            state_keys |= set(self._state_source_map().keys())
        except Exception:
            pass
        allowed_entities = {e for e, _s in mappings}
        for key in sorted(state_keys):
            if key in seen:
                continue
            if ":" not in key:
                continue
            entity, type_name = key.split(":", 1)
            if entity not in allowed_entities:
                continue
            if not _safe_text(type_name):
                continue
            rows.append(
                _ArtdefSourceRow(
                    entity=entity,
                    type_name=type_name,
                    chinese_name="（已丢失对象）",
                    replacement_type="",
                )
            )

        rows.sort(key=lambda r: (r.entity, r.type_name))
        return rows

    def _state_leader_xlp_flags(self) -> dict[str, bool]:
        raw = self._state.get("leader_xlp_flags")
        if not isinstance(raw, dict):
            raw = {}
            self._state["leader_xlp_flags"] = raw
        return {str(k): bool(v) for k, v in raw.items()}

    def _build_leader_xlp_rows(self) -> list[_LeaderXlpRow]:
        rows: list[_LeaderXlpRow] = []
        for leader_type, cn, _entry in self._collect_new_items("领袖"):
            rows.append(_LeaderXlpRow(leader_type=leader_type, chinese_name=cn))
        rows.sort(key=lambda r: r.leader_type)
        return rows

    def _render_leader_xlp_table(self) -> None:
        self._updating = True
        try:
            flags = self._state_leader_xlp_flags()
            self._leader_xlp_table.setRowCount(0)
            for row_idx, row in enumerate(self._leader_xlp_rows):
                self._leader_xlp_table.insertRow(row_idx)
                self._leader_xlp_table.setItem(row_idx, 0, QTableWidgetItem(row.leader_type))
                self._leader_xlp_table.setItem(row_idx, 1, QTableWidgetItem(row.chinese_name))

                checkbox = QCheckBox()
                checkbox.setChecked(bool(flags.get(row.state_key, False)))
                checkbox.stateChanged.connect(
                    lambda _state, cb=checkbox, key=row.state_key: self._handle_leader_xlp_toggled(cb, key)
                )
                self._leader_xlp_table.setCellWidget(row_idx, 2, checkbox)

                self._leader_xlp_table.setItem(row_idx, 3, QTableWidgetItem(row.xlp_file_name))

            self._apply_content_widths(self._leader_xlp_table, recalc_contents=True)
            self._apply_leader_xlp_table_height()
        finally:
            self._updating = False

    def _handle_leader_xlp_toggled(self, checkbox: QCheckBox, key: str) -> None:
        if self._updating:
            return
        flags = self._state_leader_xlp_flags()
        flags[str(key)] = bool(checkbox.isChecked())
        self._state["leader_xlp_flags"] = flags
        self._state["art_xml_workspace_config"] = self._build_workspace_art_xml_config()
        self._refresh_previews()

    def _render_source_table(self) -> None:
        self._updating = True
        try:
            self._source_table.setRowCount(0)
            source_map = self._state_source_map()
            need_map = self._state_need_map()
            for row_idx, row in enumerate(self._source_rows):
                self._source_table.insertRow(row_idx)
                self._source_table.setItem(row_idx, 0, QTableWidgetItem(row.entity))
                self._source_table.setItem(row_idx, 1, QTableWidgetItem(row.type_name))
                self._source_table.setItem(row_idx, 2, QTableWidgetItem(row.chinese_name))
                self._source_table.setItem(row_idx, 3, QTableWidgetItem(row.replacement_type or "-"))

                need_box = QCheckBox()
                need_box.setChecked(bool(need_map.get(row.state_key)))
                need_box.stateChanged.connect(
                    lambda _state, cb=need_box, key=row.state_key: self._handle_need_changed(cb, key)
                )
                self._source_table.setCellWidget(row_idx, 4, need_box)

                combo = QComboBox()
                combo.setEditable(False)
                combo.addItem("", "")

                options = list(self._source_options.get(row.entity, []))

                for source_type, display in options:
                    prefix = "★ " if row.replacement_type and source_type == row.replacement_type else ""
                    combo.addItem(f"{prefix}{display}", source_type)

                current = _safe_text(source_map.get(row.state_key))
                if current:
                    idx = combo.findData(current)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)

                self._ensure_combo_popup_width(combo)

                combo.currentIndexChanged.connect(
                    lambda _idx, cb=combo, key=row.state_key: self._handle_source_changed(cb, key)
                )
                self._source_table.setCellWidget(row_idx, 5, combo)

            self._source_columns_dirty = True
            self._apply_table_column_widths()
            self._apply_source_table_height()
        finally:
            self._updating = False

    def _handle_source_changed(self, combo: QComboBox, key: str) -> None:
        if self._updating:
            return
        value = _safe_text(combo.currentData())
        self._set_source(key, value)
        if value:
            self._set_need(key, True)
        self._refresh_previews()

    def _handle_need_changed(self, checkbox: QCheckBox, key: str) -> None:
        if self._updating:
            return
        self._set_need(key, checkbox.isChecked())
        self._refresh_previews()

    def _policy_slot_index(self, slot_type: str) -> int:
        s = (slot_type or "").upper().strip()
        if s.endswith("ECONOMIC"):
            return 0
        if s.endswith("MILITARY"):
            return 1
        if s.endswith("DIPLOMATIC"):
            return 2
        if s.endswith("GREAT_PERSON"):
            return 3
        if s.endswith("WILDCARD"):
            return 3
        return 3

    def _refresh_previews(self) -> None:
        art_xml_files = self._build_art_xml_preview_files()
        self._preview_groups = {
            "XLP": self._build_xlp_files(),
            "ArtDef": self._build_artdef_files(),
            "Icons": [("Icons.xml", self._build_icons_xml())],
            "Art.xml": art_xml_files,
        }
        self._preview_summary.setText(
            f"预览文件：XLP {len(self._preview_groups.get('XLP', []))} | "
            f"ArtDef {len(self._preview_groups.get('ArtDef', []))} | "
            f"Icons {len(self._preview_groups.get('Icons', []))} | "
            f"Art.xml {len(self._preview_groups.get('Art.xml', []))}"
        )

    def _open_preview_dialog(self) -> None:
        if not self._preview_groups:
            self._refresh_previews()
        dlg = _ArtPreviewDialog(self._preview_groups, self)
        dlg.exec()

    def export_preview_file_groups(self) -> dict[str, list[tuple[str, str]]]:
        if not self._preview_groups:
            self._refresh_previews()
        return {
            "XLP": list(self._preview_groups.get("XLP", [])),
            "ArtDef": list(self._preview_groups.get("ArtDef", [])),
            "Icons": list(self._preview_groups.get("Icons", [])),
            "Art.xml": list(self._preview_groups.get("Art.xml", [])),
        }

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            output.append(text)
        return output

    def _normalize_art_xml_config(self, payload: object) -> dict[str, object]:
        data = payload if isinstance(payload, dict) else {}

        raw_consumers = data.get("art_consumers") if isinstance(data.get("art_consumers"), dict) else {}
        consumers: dict[str, list[str]] = {}
        for name, values in raw_consumers.items():
            key = str(name or "").strip()
            if not key:
                continue
            entries = values if isinstance(values, list) else []
            consumers[key] = self._dedupe_preserve_order([str(v or "") for v in entries])

        raw_libraries = data.get("libraries") if isinstance(data.get("libraries"), dict) else {}
        libraries: dict[str, list[str]] = {}
        for name, values in raw_libraries.items():
            key = str(name or "").strip()
            if not key:
                continue
            entries = values if isinstance(values, list) else []
            normalized_entries: list[str] = []
            for raw in entries:
                text = str(raw or "").strip()
                if not text:
                    continue
                if text.lower().endswith(".xlp"):
                    text = text[:-4]
                normalized_entries.append(text)
            libraries[key] = self._dedupe_preserve_order(normalized_entries)

        raw_required = data.get("required_game_art_ids") if isinstance(data.get("required_game_art_ids"), list) else []
        required_ids: list[dict[str, str]] = []
        for item in raw_required:
            if not isinstance(item, dict):
                continue
            n = str(item.get("name") or "").strip()
            i = str(item.get("id") or "").strip()
            if not n and not i:
                continue
            required_ids.append({"name": n, "id": i})

        return {
            "art_consumers": consumers,
            "libraries": libraries,
            "required_game_art_ids": required_ids,
        }

    def _merge_art_xml_configs(self, primary: object, secondary: object) -> dict[str, object]:
        first = self._normalize_art_xml_config(primary)
        second = self._normalize_art_xml_config(secondary)

        merged_consumers: dict[str, list[str]] = {}
        keys = list(first.get("art_consumers", {}).keys()) + [
            k for k in second.get("art_consumers", {}).keys() if k not in first.get("art_consumers", {})
        ]
        for key in keys:
            a = first.get("art_consumers", {}).get(key, [])
            b = second.get("art_consumers", {}).get(key, [])
            merged_consumers[key] = self._dedupe_preserve_order([*(a if isinstance(a, list) else []), *(b if isinstance(b, list) else [])])

        merged_libraries: dict[str, list[str]] = {}
        lkeys = list(first.get("libraries", {}).keys()) + [
            k for k in second.get("libraries", {}).keys() if k not in first.get("libraries", {})
        ]
        for key in lkeys:
            a = first.get("libraries", {}).get(key, [])
            b = second.get("libraries", {}).get(key, [])
            merged_libraries[key] = self._dedupe_preserve_order([*(a if isinstance(a, list) else []), *(b if isinstance(b, list) else [])])

        required: list[dict[str, str]] = []
        seen_required: set[tuple[str, str]] = set()
        for source in [first.get("required_game_art_ids", []), second.get("required_game_art_ids", [])]:
            if not isinstance(source, list):
                continue
            for item in source:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                rid = str(item.get("id") or "").strip()
                key = (name.lower(), rid.lower())
                if key in seen_required:
                    continue
                seen_required.add(key)
                required.append({"name": name, "id": rid})

        return {
            "art_consumers": merged_consumers,
            "libraries": merged_libraries,
            "required_game_art_ids": required,
        }

    def _load_art_xml_rules(self) -> dict[str, object]:
        if not ART_XML_RULES_FILE.exists():
            return {"art_consumers": {}, "libraries": {}, "required_game_art_ids": []}
        try:
            raw = json.loads(ART_XML_RULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            LOGGER.exception("[ArtWorkspace] read art_xml_rules.json failed")
            return {"art_consumers": {}, "libraries": {}, "required_game_art_ids": []}
        return self._normalize_art_xml_config(raw)

    def _build_workspace_art_xml_config(self) -> dict[str, object]:
        merged = self._merge_art_xml_configs(self._default_blank_art_xml_config(), self._load_art_xml_rules())
        libraries = merged.get("libraries") if isinstance(merged.get("libraries"), dict) else {}
        merged["libraries"] = libraries

        leader_packages = [row.leader_type.lower() for row in self._selected_leader_xlp_rows() if _safe_text(row.leader_type)]
        existing = libraries.get("Leader") if isinstance(libraries.get("Leader"), list) else []
        libraries["Leader"] = self._dedupe_preserve_order([*existing, *leader_packages])
        return merged

    def _default_blank_art_xml_config(self) -> dict[str, object]:
        if not DEFAULT_BLANK_ART_XML_FILE.exists():
            return {"art_consumers": {}, "libraries": {}, "required_game_art_ids": []}
        try:
            return self._parse_art_xml_file_config(DEFAULT_BLANK_ART_XML_FILE)
        except Exception:
            LOGGER.exception("[ArtWorkspace] parse default blank Art.xml failed")
            return {"art_consumers": {}, "libraries": {}, "required_game_art_ids": []}

    def _source_art_xml_config(self) -> dict[str, object]:
        payload = self._state.get("art_xml_source_config")
        if not isinstance(payload, dict):
            payload = {}
        normalized = self._normalize_art_xml_config(payload)
        self._state["art_xml_source_config"] = normalized
        return normalized

    def _workspace_art_xml_config(self) -> dict[str, object]:
        payload = self._state.get("art_xml_workspace_config")
        if not isinstance(payload, dict):
            payload = {}
        normalized = self._normalize_art_xml_config(payload)
        self._state["art_xml_workspace_config"] = normalized
        return normalized

    def merge_custom_xlp_source_from_project(
        self,
        *,
        root_dir: Path,
        relative_paths: list[str],
    ) -> None:
        if not isinstance(root_dir, Path) or not root_dir.exists() or not isinstance(relative_paths, list):
            return

        discovered: dict[str, list[str]] = {}
        for rel in relative_paths:
            rel_text = str(rel or "").strip().replace("\\", "/")
            if not rel_text.lower().endswith(".xlp"):
                continue
            file_path = (root_dir / rel_text).resolve()
            if not file_path.exists() or not file_path.is_file():
                continue
            try:
                xlp_root = ET.parse(file_path).getroot()
            except Exception:
                continue

            class_node = xlp_root.find("m_ClassName")
            package_node = xlp_root.find("m_PackageName")
            class_name = ""
            package_name = ""
            if class_node is not None:
                class_name = str(class_node.attrib.get("text") or class_node.text or "").strip()
            if package_node is not None:
                package_name = str(package_node.attrib.get("text") or package_node.text or "").strip()
            if package_name.lower().endswith(".xlp"):
                package_name = package_name[:-4]
            if not package_name:
                package_name = file_path.stem
            if not class_name or not package_name:
                continue

            bucket = discovered.setdefault(class_name, [])
            bucket.append(package_name)

        if not discovered:
            return

        source = self._source_art_xml_config()
        libraries = source.get("libraries") if isinstance(source.get("libraries"), dict) else {}
        source["libraries"] = libraries
        for class_name, package_names in discovered.items():
            existing = libraries.get(class_name) if isinstance(libraries.get(class_name), list) else []
            libraries[class_name] = self._dedupe_preserve_order([
                *(existing if isinstance(existing, list) else []),
                *[str(p) for p in package_names],
            ])

        self._state["art_xml_source_config"] = self._normalize_art_xml_config(source)
        self._refresh_previews()

    def _merged_art_xml_config(self) -> dict[str, object]:
        workspace = self._workspace_art_xml_config()
        source = self._source_art_xml_config()
        return self._merge_art_xml_configs(workspace, source)

    def _current_civ6proj_path(self) -> Path | None:
        basic = self._sections.get("基础信息")
        if not isinstance(basic, dict):
            return None
        data = basic.get("data") if isinstance(basic.get("data"), dict) else basic
        if not isinstance(data, dict):
            return None
        project_info = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}
        raw = str(project_info.get("civ6proj_path") or "").strip()
        if not raw:
            return None
        path = Path(raw)
        return path if path.suffix.lower() == ".civ6proj" else None

    @staticmethod
    def _find_art_xml_for_civ6proj(civ6proj_path: Path) -> Path | None:
        if not civ6proj_path.exists():
            return None
        base = civ6proj_path.with_suffix(".Art.xml")
        if base.exists():
            return base
        parent = civ6proj_path.parent
        candidates = sorted(parent.glob("*.Art.xml"))
        return candidates[0] if candidates else None

    def _parse_art_xml_file_config(self, art_xml_path: Path) -> dict[str, object]:
        tree = ET.parse(art_xml_path)
        root = tree.getroot()

        consumers: dict[str, list[str]] = {}
        libraries: dict[str, list[str]] = {}
        required_ids: list[dict[str, str]] = []

        art_consumers = root.find("artConsumers")
        if art_consumers is not None:
            for elem in art_consumers.findall("Element"):
                name_node = elem.find("consumerName")
                name = str(name_node.attrib.get("text") or "").strip() if name_node is not None else ""
                if not name:
                    continue
                paths: list[str] = []
                rel_paths = elem.find("relativeArtDefPaths")
                if rel_paths is not None:
                    for p in rel_paths.findall("Element"):
                        text = str(p.attrib.get("text") or "").strip()
                        if text:
                            paths.append(text)
                consumers[name] = self._dedupe_preserve_order(paths)

        game_libraries = root.find("gameLibraries")
        if game_libraries is not None:
            for elem in game_libraries.findall("Element"):
                name_node = elem.find("libraryName")
                name = str(name_node.attrib.get("text") or "").strip() if name_node is not None else ""
                if not name:
                    continue
                packages: list[str] = []
                rel_paths = elem.find("relativePackagePaths")
                if rel_paths is not None:
                    for p in rel_paths.findall("Element"):
                        text = str(p.attrib.get("text") or "").strip()
                        if text:
                            packages.append(text)
                libraries[name] = self._dedupe_preserve_order(packages)

        required = root.find("requiredGameArtIDs")
        if required is not None:
            for elem in required.findall("Element"):
                name_node = elem.find("name")
                id_node = elem.find("id")
                n = str(name_node.attrib.get("text") or "").strip() if name_node is not None else ""
                rid = str(id_node.attrib.get("text") or "").strip() if id_node is not None else ""
                if not n and not rid:
                    continue
                required_ids.append({"name": n, "id": rid})

        return self._normalize_art_xml_config(
            {
                "art_consumers": consumers,
                "libraries": libraries,
                "required_game_art_ids": required_ids,
            }
        )

    def _import_art_xml_from_file(self, art_xml_path: Path, *, auto: bool) -> bool:
        try:
            parsed = self._parse_art_xml_file_config(art_xml_path)
        except Exception:
            LOGGER.exception("[ArtWorkspace] parse Art.xml failed: %s", art_xml_path)
            if not auto:
                QMessageBox.warning(self, "读取失败", f"解析 Art.xml 失败：\n{art_xml_path}")
            return False

        merged = self._merge_art_xml_configs(self._source_art_xml_config(), parsed)
        self._state["art_xml_source_config"] = merged
        self._state["art_xml_source_path"] = str(art_xml_path)

        if not auto:
            consumer_count = len(merged.get("art_consumers", {}))
            library_count = len(merged.get("libraries", {}))
            QMessageBox.information(
                self,
                "读取完成",
                f"已读取并合并 Art.xml 配置：\n{art_xml_path}\n\nArtConsumer: {consumer_count}\nLibrary: {library_count}",
            )
        return True

    def _try_auto_import_source_art_xml(self) -> None:
        civ6proj = self._current_civ6proj_path()
        if civ6proj is None:
            return
        art_xml_path = self._find_art_xml_for_civ6proj(civ6proj)
        if art_xml_path is None:
            self._state["art_xml_source_config"] = self._default_blank_art_xml_config()
            self._state["art_xml_source_path"] = str(DEFAULT_BLANK_ART_XML_FILE)
            return

        existing_path = str(self._state.get("art_xml_source_path") or "").strip()
        source_config = self._source_art_xml_config()
        if existing_path == str(art_xml_path) and (source_config.get("art_consumers") or source_config.get("libraries")):
            return
        self._import_art_xml_from_file(art_xml_path, auto=True)

    def _handle_import_art_xml_from_civ6proj(self) -> None:
        civ6proj = self._current_civ6proj_path()
        if civ6proj is None:
            QMessageBox.warning(self, "无法读取", "请先在【基础信息】中选择 .civ6proj 文件。")
            return
        art_xml_path = self._find_art_xml_for_civ6proj(civ6proj)
        if art_xml_path is None:
            self._state["art_xml_source_config"] = self._default_blank_art_xml_config()
            self._state["art_xml_source_path"] = str(DEFAULT_BLANK_ART_XML_FILE)
            QMessageBox.information(
                self,
                "未找到原始Art.xml",
                f"在目录中未找到 Art.xml：\n{civ6proj.parent}\n\n已加载内置空白 Art.xml 作为保底配置。",
            )
            self._refresh_previews()
            return
        if self._import_art_xml_from_file(art_xml_path, auto=False):
            self._refresh_previews()

    def _output_basename(self) -> str:
        civ6proj = self._current_civ6proj_path()
        if isinstance(civ6proj, Path):
            stem = str(civ6proj.stem or "").strip()
            if stem:
                return stem
        basic = self._sections.get("基础信息")
        if isinstance(basic, dict):
            data = basic.get("data") if isinstance(basic.get("data"), dict) else basic
            if isinstance(data, dict):
                project_info = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}
                name = str(project_info.get("file_name") or "").strip()
                if name:
                    text = re.sub(r"[\\/:*?\"<>|]+", "_", name)
                    text = re.sub(r"\s+", "_", text)
                    text = re.sub(r"_+", "_", text).strip("_")
                    if text:
                        return text
        return "project"

    def _discover_available_artdef_files(self) -> set[str]:
        names: set[str] = set()
        for filename, _content in self._build_artdef_files():
            text = str(filename or "").strip()
            if text:
                names.add(text.lower())

        civ6proj = self._current_civ6proj_path()
        if isinstance(civ6proj, Path) and civ6proj.exists():
            parent = civ6proj.parent
            for pattern in ("*.artdef", "ArtDefs/*.artdef"):
                for path in parent.glob(pattern):
                    names.add(path.name.lower())
        return names

    def _discover_available_xlp_packages(self) -> set[str]:
        packages: set[str] = set()

        for filename, _content in self._build_xlp_files():
            text = str(filename or "").strip()
            if not text:
                continue
            stem = Path(text).stem.strip().lower()
            if stem:
                packages.add(stem)

        civ6proj = self._current_civ6proj_path()
        if isinstance(civ6proj, Path) and civ6proj.exists():
            parent = civ6proj.parent
            for pattern in ("*.xlp", "XLPs/*.xlp"):
                for path in parent.glob(pattern):
                    stem = str(path.stem or "").strip().lower()
                    if stem:
                        packages.add(stem)
        return packages

    def _build_art_xml_xml(self) -> str:
        merged = self._merged_art_xml_config()
        consumers_map = merged.get("art_consumers") if isinstance(merged.get("art_consumers"), dict) else {}
        libraries_map = merged.get("libraries") if isinstance(merged.get("libraries"), dict) else {}

        if DEFAULT_BLANK_ART_XML_FILE.exists():
            try:
                root = ET.parse(DEFAULT_BLANK_ART_XML_FILE).getroot()
            except Exception:
                root = ET.Element("AssetObjects..GameArtSpecification")
        else:
            root = ET.Element("AssetObjects..GameArtSpecification")

        base_name = self._output_basename()
        token = re.sub(r"[^A-Za-z0-9_]+", "_", base_name).upper().strip("_") or "PROJECT"
        id_node = root.find("id")
        if id_node is None:
            id_node = ET.SubElement(root, "id")
        name_node = id_node.find("name")
        if name_node is None:
            name_node = ET.SubElement(id_node, "name")
        name_node.set("text", f"LOC_{token}_NAME")
        id_value_node = id_node.find("id")
        if id_value_node is None:
            id_value_node = ET.SubElement(id_node, "id")
        id_value_node.set("text", str(uuid.uuid5(uuid.NAMESPACE_DNS, f"modtools54:{token}")))

        available_artdefs = self._discover_available_artdef_files()
        available_packages = self._discover_available_xlp_packages()

        art_consumers = root.find("artConsumers")
        if art_consumers is None:
            art_consumers = ET.SubElement(root, "artConsumers")
        existing_consumers: dict[str, ET.Element] = {}
        for elem in art_consumers.findall("Element"):
            node = elem.find("consumerName")
            name = str(node.attrib.get("text") or "").strip() if node is not None else ""
            if name:
                existing_consumers[name] = elem

        all_consumer_names = list(existing_consumers.keys()) + [
            key for key in consumers_map.keys() if key not in existing_consumers
        ]
        for consumer_name in all_consumer_names:
            elem = existing_consumers.get(consumer_name)
            if elem is None:
                elem = ET.SubElement(art_consumers, "Element")
                ET.SubElement(elem, "consumerName", {"text": consumer_name})
                ET.SubElement(elem, "libraryDependencies")
                ET.SubElement(elem, "loadsLibraries").text = "false"
            rel_paths = elem.find("relativeArtDefPaths")
            if rel_paths is None:
                rel_paths = ET.SubElement(elem, "relativeArtDefPaths")

            baseline_paths: list[str] = []
            for p in rel_paths.findall("Element"):
                text = str(p.attrib.get("text") or "").strip()
                if text:
                    baseline_paths.append(text)
            configured_paths = consumers_map.get(consumer_name)
            if not isinstance(configured_paths, list):
                configured_paths = []

            merged_paths = self._dedupe_preserve_order([*baseline_paths, *[str(v) for v in configured_paths]])
            final_paths: list[str] = []
            for text in merged_paths:
                lower = text.lower()
                if text in baseline_paths or lower in available_artdefs:
                    final_paths.append(text)

            for child in list(rel_paths):
                rel_paths.remove(child)
            for text in final_paths:
                ET.SubElement(rel_paths, "Element", {"text": text})

        game_libraries = root.find("gameLibraries")
        if game_libraries is None:
            game_libraries = ET.SubElement(root, "gameLibraries")
        existing_libraries: dict[str, ET.Element] = {}
        for elem in game_libraries.findall("Element"):
            node = elem.find("libraryName")
            name = str(node.attrib.get("text") or "").strip() if node is not None else ""
            if name:
                existing_libraries[name] = elem

        all_library_names = list(existing_libraries.keys()) + [
            key for key in libraries_map.keys() if key not in existing_libraries
        ]
        for library_name in all_library_names:
            elem = existing_libraries.get(library_name)
            if elem is None:
                elem = ET.SubElement(game_libraries, "Element")
                ET.SubElement(elem, "libraryName", {"text": library_name})
            rel_paths = elem.find("relativePackagePaths")
            if rel_paths is None:
                rel_paths = ET.SubElement(elem, "relativePackagePaths")

            baseline_packages: list[str] = []
            for p in rel_paths.findall("Element"):
                text = str(p.attrib.get("text") or "").strip()
                if text:
                    if text.lower().endswith(".xlp"):
                        text = text[:-4]
                    baseline_packages.append(text)

            configured = libraries_map.get(library_name)
            if not isinstance(configured, list):
                configured = []
            configured_packages: list[str] = []
            for raw in configured:
                text = str(raw or "").strip()
                if text.lower().endswith(".xlp"):
                    text = text[:-4]
                if text:
                    configured_packages.append(text)

            merged_packages = self._dedupe_preserve_order([*baseline_packages, *configured_packages])
            final_packages: list[str] = []
            for text in merged_packages:
                if text in baseline_packages or text.lower() in available_packages:
                    final_packages.append(text)

            for child in list(rel_paths):
                rel_paths.remove(child)
            for text in final_packages:
                ET.SubElement(rel_paths, "Element", {"text": text})

        required_node = root.find("requiredGameArtIDs")
        if required_node is None:
            required_node = ET.SubElement(root, "requiredGameArtIDs")
        for child in list(required_node):
            required_node.remove(child)

        elem = ET.SubElement(required_node, "Element")
        ET.SubElement(elem, "name", {"text": "Expansion2"})
        ET.SubElement(elem, "id", {"text": "b1b63999-6b16-4dd2-a5b6-eb19794aa8ca"})

        return self._indent_xml(root)

    def _build_art_xml_config_text(self, section: str) -> str:
        merged = self._merged_art_xml_config()
        if section == "consumer":
            source = merged.get("art_consumers") if isinstance(merged.get("art_consumers"), dict) else {}
            title = "ArtConsumer"
        else:
            source = merged.get("libraries") if isinstance(merged.get("libraries"), dict) else {}
            title = "Library"

        lines = [f"# {title}（合并后）", ""]
        if not source:
            lines.append("（空）")
            lines.append("")
            return "\n".join(lines)

        for key in sorted(source.keys(), key=lambda x: x.lower()):
            values = source.get(key)
            if not isinstance(values, list):
                values = []
            lines.append(f"[{key}]")
            for value in values:
                text = str(value or "").strip()
                if text:
                    lines.append(f"- {text}")
            lines.append("")
        return "\n".join(lines)

    def _build_art_xml_preview_files(self) -> list[tuple[str, str]]:
        file_name = f"{self._output_basename()}.Art.xml"
        return [
            (file_name, self._build_art_xml_xml()),
            ("ArtConsumer（合并预览）.txt", self._build_art_xml_config_text("consumer")),
            ("Library（合并预览）.txt", self._build_art_xml_config_text("library")),
        ]

    @staticmethod
    def _indent_xml(root: ET.Element) -> str:
        try:
            from xml.etree.ElementTree import indent as et_indent

            et_indent(root, space="\t")
        except Exception:
            def _indent(elem: ET.Element, level: int = 0) -> None:
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
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" + ET.tostring(root, encoding="utf-8").decode("utf-8") + "\n"

    def _build_leader_fallback_xlp_xml(self) -> str:
        leaders = self._collect_new_items("领袖")
        root = ET.Element("AssetObjects..XLP")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_ClassName", {"text": "LeaderFallback"})
        ET.SubElement(root, "m_PackageName", {"text": "LeaderFallbacks"})
        entries = ET.SubElement(root, "m_Entries")
        for leader_type, _cn, _entry in leaders:
            # Beta 纹理链路要求：未选择外交前景图片路径时，不应生成对应 XLP 项。
            if not self._image_path(_entry, "diplo_foreground"):
                continue
            suffix = leader_type[len("LEADER_") :] if leader_type.startswith("LEADER_") else leader_type
            elem = ET.SubElement(entries, "Element")
            ET.SubElement(elem, "m_EntryID", {"text": f"FALLBACK_NEUTRAL_{suffix}"})
            ET.SubElement(elem, "m_ObjectName", {"text": f"FALLBACK_NEUTRAL_{suffix}"})
        allowed = ET.SubElement(root, "m_AllowedPlatforms")
        for platform in ["WINDOWS", "IOS", "LINUX", "XBONE", "PS4", "SWITCH", "STADIA", "MACOS"]:
            ET.SubElement(allowed, "Element").text = platform
        return self._indent_xml(root)

    def _selected_leader_xlp_rows(self) -> list[_LeaderXlpRow]:
        flags = self._state_leader_xlp_flags()
        rows: list[_LeaderXlpRow] = []
        for row in self._leader_xlp_rows:
            if not bool(flags.get(row.state_key)):
                continue
            if not _safe_text(row.leader_type):
                continue
            rows.append(row)
        return rows

    def _build_single_leader_xlp_xml(self, row: _LeaderXlpRow) -> str:
        root = ET.Element("AssetObjects..XLP")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_ClassName", {"text": "Leader"})
        ET.SubElement(root, "m_PackageName", {"text": row.leader_type.lower()})
        ET.SubElement(root, "m_Entries")
        allowed = ET.SubElement(root, "m_AllowedPlatforms")
        for platform in ["WINDOWS", "IOS", "LINUX", "XBONE", "PS4", "SWITCH", "STADIA", "MACOS"]:
            ET.SubElement(allowed, "Element").text = platform
        return self._indent_xml(root)

    def _build_ui_texture_xlp_xml(self, base_name: str) -> str:
        package = f"{base_name}_dds"
        root = ET.Element("AssetObjects..XLP")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_ClassName", {"text": "UITexture"})
        ET.SubElement(root, "m_PackageName", {"text": package})
        ET.SubElement(root, "m_Entries")
        allowed = ET.SubElement(root, "m_AllowedPlatforms")
        for platform in ["WINDOWS", "IOS", "LINUX", "XBONE", "PS4", "SWITCH", "STADIA", "MACOS"]:
            ET.SubElement(allowed, "Element").text = platform
        return self._indent_xml(root)

    def _build_leader_fallback_artdef_xml(self) -> str:
        leaders = self._collect_new_items("领袖")
        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "LeaderFallback"})
        collections = ET.SubElement(root, "m_RootCollections")
        leaders_container = ET.SubElement(collections, "Element")
        ET.SubElement(leaders_container, "m_CollectionName", {"text": "Leaders"})
        ET.SubElement(leaders_container, "m_ReplaceMergedCollectionElements").text = "false"

        for leader_type, _cn, _entry in leaders:
            # 与 LeaderFallback.xlp 保持一致：未选择外交前景图片路径时，不生成对应 ArtDef 条目。
            if not self._image_path(_entry, "diplo_foreground"):
                continue
            suffix = leader_type[len("LEADER_") :] if leader_type.startswith("LEADER_") else leader_type
            entry = ET.SubElement(leaders_container, "Element")
            fields = ET.SubElement(entry, "m_Fields")
            ET.SubElement(fields, "m_Values")
            child_cols = ET.SubElement(entry, "m_ChildCollections")

            animations = ET.SubElement(child_cols, "Element")
            ET.SubElement(animations, "m_CollectionName", {"text": "Animations"})
            ET.SubElement(animations, "m_ReplaceMergedCollectionElements").text = "false"
            anim_entry = ET.SubElement(animations, "Element")
            anim_fields = ET.SubElement(anim_entry, "m_Fields")
            anim_values = ET.SubElement(anim_fields, "m_Values")
            blp = ET.SubElement(anim_values, "Element", {"class": "AssetObjects..BLPEntryValue"})
            ET.SubElement(blp, "m_EntryName", {"text": f"FALLBACK_NEUTRAL_{suffix}"})
            ET.SubElement(blp, "m_XLPClass", {"text": "LeaderFallback"})
            ET.SubElement(blp, "m_XLPPath", {"text": "leaderfallback.xlp"})
            ET.SubElement(blp, "m_BLPPackage", {"text": "LeaderFallbacks"})
            ET.SubElement(blp, "m_LibraryName", {"text": "LeaderFallback"})
            ET.SubElement(blp, "m_ParamName", {"text": "BLP Entry"})
            ET.SubElement(anim_entry, "m_ChildCollections")
            ET.SubElement(anim_entry, "m_Name", {"text": "DEFAULT"})
            ET.SubElement(anim_entry, "m_AppendMergedParameterCollections").text = "false"

            ET.SubElement(entry, "m_Name", {"text": leader_type})
            ET.SubElement(entry, "m_AppendMergedParameterCollections").text = "false"

        return self._indent_xml(root)

    def _build_leaders_artdef_xml(self) -> str:
        leader_rows = self._selected_leader_xlp_rows()
        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Leaders"})
        collections = ET.SubElement(root, "m_RootCollections")
        leaders_container = ET.SubElement(collections, "Element")
        ET.SubElement(leaders_container, "m_CollectionName", {"text": "Leaders"})
        ET.SubElement(leaders_container, "m_ReplaceMergedCollectionElements").text = "false"

        for row in leader_rows:
            entry = ET.SubElement(leaders_container, "Element")
            ET.SubElement(entry, "m_Fields")
            ET.SubElement(entry, "m_ChildCollections")
            ET.SubElement(entry, "m_Name", {"text": row.leader_type})
            ET.SubElement(entry, "m_AppendMergedParameterCollections").text = "false"

        return self._indent_xml(root)

    def _state_civ_art_map(self) -> dict[str, dict[str, object]]:
        civs = self._state.get("civs")
        if not isinstance(civs, dict):
            civs = {}
            self._state["civs"] = civs
        output: dict[str, dict[str, object]] = {}
        for civ_type, meta in civs.items():
            key = _safe_text(civ_type)
            if not key or not isinstance(meta, dict):
                continue
            output[key] = meta
        return output

    def _collect_civilization_art_targets(self) -> list[tuple[str, str]]:
        civ_entries = self._collect_new_items("文明")
        civ_state = self._state_civ_art_map()
        targets: list[tuple[str, str]] = []
        seen: set[str] = set()

        for civ_type, _cn, _entry in civ_entries:
            if civ_type in seen:
                continue
            meta = civ_state.get(civ_type)
            if isinstance(meta, dict) and ("need" in meta) and (not bool(meta.get("need"))):
                continue
            source = _safe_text(meta.get("music_source")) if isinstance(meta, dict) else ""
            if not source:
                source = self._selected_source("civilization", civ_type)
            if not source:
                source = civ_type
            targets.append((civ_type, source))
            seen.add(civ_type)

        for civ_type, meta in civ_state.items():
            if civ_type in seen:
                continue
            if not bool(meta.get("need")):
                continue
            source = _safe_text(meta.get("music_source")) or civ_type
            targets.append((civ_type, source))
            seen.add(civ_type)

        return sorted(targets, key=lambda pair: pair[0])

    def _build_civilizations_artdef_xml(self) -> str:
        selected = self._collect_civilization_art_targets()
        if not selected:
            return self._build_empty_artdef("Civilizations", [])

        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Civilizations"})
        rc = ET.SubElement(root, "m_RootCollections")
        container = ET.SubElement(rc, "Element")
        ET.SubElement(container, "m_CollectionName", {"text": "Civilization"})
        ET.SubElement(container, "m_ReplaceMergedCollectionElements").text = "false"

        for target, source in selected:
            entry = None
            if source and get_civilization_entry_element is not None:
                entry = get_civilization_entry_element(source)
            if entry is None:
                entry = ET.Element("Element")
                fields = ET.SubElement(entry, "m_Fields")
                ET.SubElement(fields, "m_Values")
                child = ET.SubElement(entry, "m_ChildCollections")
                audio = ET.SubElement(child, "Element")
                ET.SubElement(audio, "m_CollectionName", {"text": "Audio"})
                ET.SubElement(audio, "m_ReplaceMergedCollectionElements").text = "false"
                ET.SubElement(entry, "m_Name", {"text": target})
                ET.SubElement(entry, "m_AppendMergedParameterCollections").text = "false"
            else:
                name_node = entry.find("m_Name")
                if name_node is not None:
                    name_node.set("text", target)
            container.append(entry)

        return self._indent_xml(root)

    def _build_cultures_artdef_xml(self) -> str:
        civ_state = self._state_civ_art_map()
        grouped: dict[str, dict[str, list[str]]] = {k: {} for k in _CULTURE_GROUPS_FALLBACK.keys()}
        has_selection = False

        for civ_type, meta in civ_state.items():
            if not bool(meta.get("need")):
                continue
            cultures = meta.get("cultures") if isinstance(meta.get("cultures"), dict) else {}
            if not isinstance(cultures, dict):
                continue
            for collection, options in _CULTURE_GROUPS_FALLBACK.items():
                selected = cultures.get(collection)
                if isinstance(selected, set):
                    names = sorted(selected)
                elif isinstance(selected, (list, tuple)):
                    names = sorted({str(v) for v in selected if _safe_text(v)})
                else:
                    names = []
                for name in names:
                    if name not in options:
                        continue
                    grouped.setdefault(collection, {}).setdefault(name, []).append(civ_type)
                    has_selection = True

        if not has_selection:
            return self._build_empty_artdef("Cultures", ["Culture", "UnitCulture"])

        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Cultures"})
        rc = ET.SubElement(root, "m_RootCollections")

        for collection in _CULTURE_GROUPS_FALLBACK.keys():
            container = ET.SubElement(rc, "Element")
            ET.SubElement(container, "m_CollectionName", {"text": collection})
            ET.SubElement(container, "m_ReplaceMergedCollectionElements").text = "false"
            mapping = grouped.get(collection, {})
            for group_name in _CULTURE_GROUPS_FALLBACK.get(collection, ()):
                civs = mapping.get(group_name)
                if not civs:
                    continue
                entry = ET.SubElement(container, "Element")
                fields = ET.SubElement(entry, "m_Fields")
                values = ET.SubElement(fields, "m_Values")
                coll_value = ET.SubElement(values, "Element", {"class": "AssetObjects..CollectionValue"})
                ET.SubElement(coll_value, "m_eObjectType").text = "INVALID"
                ET.SubElement(coll_value, "m_eValueType").text = "ARTDEF_REF"
                val_list = ET.SubElement(coll_value, "m_Values")
                for idx, civ in enumerate(sorted(set(civs))):
                    ref = ET.SubElement(val_list, "Element", {"class": "AssetObjects..ArtDefReferenceValue"})
                    ET.SubElement(ref, "m_ElementName", {"text": civ})
                    ET.SubElement(ref, "m_RootCollectionName", {"text": "Civilization"})
                    ET.SubElement(ref, "m_ArtDefPath", {"text": "Civilizations.artdef"})
                    ET.SubElement(ref, "m_CollectionIsLocked").text = "true"
                    ET.SubElement(ref, "m_TemplateName", {"text": "Civilizations"})
                    ET.SubElement(ref, "m_ParamName", {"text": f"Civilizations{idx + 1:03d}"})
                ET.SubElement(coll_value, "m_ParamName", {"text": "Civilizations"})
                ET.SubElement(entry, "m_ChildCollections")
                ET.SubElement(entry, "m_Name", {"text": group_name})
                ET.SubElement(entry, "m_AppendMergedParameterCollections").text = "true"

        return self._indent_xml(root)

    @staticmethod
    def _build_empty_artdef(template_name: str, collections: list[str]) -> str:
        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": template_name})
        rc = ET.SubElement(root, "m_RootCollections")
        for collection in collections:
            node = ET.SubElement(rc, "Element")
            ET.SubElement(node, "m_CollectionName", {"text": collection})
            ET.SubElement(node, "m_ReplaceMergedCollectionElements").text = "false"
        return ArtWorkspacePanel._indent_xml(root)

    def _selected_source(self, entity: str, target_type: str) -> str:
        return _safe_text(self._state_source_map().get(f"{entity}:{target_type}"))

    def _selected_need(self, entity: str, target_type: str) -> bool:
        return bool(self._state_need_map().get(f"{entity}:{target_type}"))

    @staticmethod
    def _make_empty_artdef_entry(target_type: str) -> ET.Element:
        entry = ET.Element("Element")
        fields = ET.SubElement(entry, "m_Fields")
        ET.SubElement(fields, "m_Values")
        ET.SubElement(entry, "m_ChildCollections")
        ET.SubElement(entry, "m_Name", {"text": target_type})
        ET.SubElement(entry, "m_AppendMergedParameterCollections").text = "false"
        return entry

    def _build_districts_artdef_xml(self) -> str:
        if get_district_entry_element is None:
            return self._build_empty_artdef("Districts", ["District", "BuildStates"])

        selected = []
        for type_name, _cn, _entry in self._collect_new_items("区域", name_key="Name"):
            if not self._selected_need("district", type_name):
                continue
            selected.append((type_name, self._selected_source("district", type_name)))

        if not selected:
            return self._build_empty_artdef("Districts", ["District", "BuildStates"])

        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Districts"})
        rc = ET.SubElement(root, "m_RootCollections")
        district_container = ET.SubElement(rc, "Element")
        ET.SubElement(district_container, "m_CollectionName", {"text": "District"})
        ET.SubElement(district_container, "m_ReplaceMergedCollectionElements").text = "false"
        state_container = ET.SubElement(rc, "Element")
        ET.SubElement(state_container, "m_CollectionName", {"text": "BuildStates"})
        ET.SubElement(state_container, "m_ReplaceMergedCollectionElements").text = "false"

        for target, source in selected:
            if source:
                entry = get_district_entry_element(source)
                if entry is None:
                    entry = self._make_empty_artdef_entry(target)
                else:
                    name_node = entry.find("m_Name")
                    if name_node is not None:
                        name_node.set("text", target)
            else:
                entry = self._make_empty_artdef_entry(target)
            district_container.append(entry)

        return self._indent_xml(root)

    def _build_buildings_artdef_xml(self) -> str:
        if get_building_entry_element is None:
            return self._build_empty_artdef("Buildings", ["Building"])

        selected = []
        for type_name, _cn, _entry in self._collect_new_items("建筑", name_key="Name"):
            if not self._selected_need("building", type_name):
                continue
            selected.append((type_name, self._selected_source("building", type_name)))

        if not selected:
            return self._build_empty_artdef("Buildings", ["Building"])

        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Buildings"})
        rc = ET.SubElement(root, "m_RootCollections")
        container = ET.SubElement(rc, "Element")
        ET.SubElement(container, "m_CollectionName", {"text": "Building"})
        ET.SubElement(container, "m_ReplaceMergedCollectionElements").text = "false"

        for target, source in selected:
            if source:
                entry = get_building_entry_element(source)
                if entry is None:
                    entry = self._make_empty_artdef_entry(target)
                else:
                    name_node = entry.find("m_Name")
                    if name_node is not None:
                        name_node.set("text", target)
            else:
                entry = self._make_empty_artdef_entry(target)
            container.append(entry)

        return self._indent_xml(root)

    def _build_improvements_artdef_xml(self) -> str:
        if get_improvement_entry_element is None:
            return self._build_empty_artdef("Improvements", ["Improvement", "BuildStates"])

        selected = []
        for type_name, _cn, _entry in self._collect_new_items("改良设施", name_key="Name"):
            if not self._selected_need("improvement", type_name):
                continue
            selected.append((type_name, self._selected_source("improvement", type_name)))

        if not selected:
            return self._build_empty_artdef("Improvements", ["Improvement", "BuildStates"])

        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Improvements"})
        rc = ET.SubElement(root, "m_RootCollections")
        container = ET.SubElement(rc, "Element")
        ET.SubElement(container, "m_CollectionName", {"text": "Improvement"})
        ET.SubElement(container, "m_ReplaceMergedCollectionElements").text = "false"
        state_container = ET.SubElement(rc, "Element")
        ET.SubElement(state_container, "m_CollectionName", {"text": "BuildStates"})
        ET.SubElement(state_container, "m_ReplaceMergedCollectionElements").text = "false"

        for target, source in selected:
            if source:
                entry = get_improvement_entry_element(source)
                if entry is None:
                    entry = self._make_empty_artdef_entry(target)
                else:
                    name_node = entry.find("m_Name")
                    if name_node is not None:
                        name_node.set("text", target)
            else:
                entry = self._make_empty_artdef_entry(target)
            container.append(entry)

        return self._indent_xml(root)

    def _build_units_artdef_xml(self) -> str:
        if get_unit_entry_element is None:
            return self._build_empty_artdef(
                "Units",
                [
                    "Units",
                    "UnitMovementTypes",
                    "UnitFormationTypes",
                    "MemberCombat",
                    "UnitCombat",
                    "CombatAttack",
                    "UnitFormationLayoutTypes",
                    "CombatFormation",
                    "UnitDomainTypes",
                    "UnitAttachmentBins",
                    "UnitMemberTypes",
                    "UnitTintTypes",
                    "UnitGlobals",
                ],
            )

        selected = []
        for type_name, _cn, _entry in self._collect_new_items("单位", name_key="Name"):
            if not self._selected_need("unit", type_name):
                continue
            selected.append((type_name, self._selected_source("unit", type_name)))
        selected.sort(key=lambda pair: (0 if pair[0].startswith("UNIT_GREAT") else 1, pair[0]))

        if not selected:
            return self._build_empty_artdef(
                "Units",
                [
                    "Units",
                    "UnitMovementTypes",
                    "UnitFormationTypes",
                    "MemberCombat",
                    "UnitCombat",
                    "CombatAttack",
                    "UnitFormationLayoutTypes",
                    "CombatFormation",
                    "UnitDomainTypes",
                    "UnitAttachmentBins",
                    "UnitMemberTypes",
                    "UnitTintTypes",
                    "UnitGlobals",
                ],
            )

        root = ET.Element("AssetObjects..ArtDefSet")
        ver = ET.SubElement(root, "m_Version")
        ET.SubElement(ver, "major").text = "1"
        ET.SubElement(ver, "minor").text = "0"
        ET.SubElement(ver, "build").text = "0"
        ET.SubElement(ver, "revision").text = "0"
        ET.SubElement(root, "m_TemplateName", {"text": "Units"})
        rc = ET.SubElement(root, "m_RootCollections")
        container = ET.SubElement(rc, "Element")
        ET.SubElement(container, "m_CollectionName", {"text": "Units"})
        ET.SubElement(container, "m_ReplaceMergedCollectionElements").text = "false"
        for name in [
            "UnitMovementTypes",
            "UnitFormationTypes",
            "MemberCombat",
            "UnitCombat",
            "CombatAttack",
            "UnitFormationLayoutTypes",
            "CombatFormation",
            "UnitDomainTypes",
            "UnitAttachmentBins",
            "UnitMemberTypes",
            "UnitTintTypes",
            "UnitGlobals",
        ]:
            node = ET.SubElement(rc, "Element")
            ET.SubElement(node, "m_CollectionName", {"text": name})
            ET.SubElement(node, "m_ReplaceMergedCollectionElements").text = "false"

        for target, source in selected:
            if source:
                entry = get_unit_entry_element(source)
                if entry is None:
                    entry = self._make_empty_artdef_entry(target)
                else:
                    name_node = entry.find("m_Name")
                    if name_node is not None:
                        name_node.set("text", target)
            else:
                entry = self._make_empty_artdef_entry(target)
            container.append(entry)

        return self._indent_xml(root)

    def _build_icons_xml(self) -> str:
        civs = self._collect_new_items("文明")
        leaders = self._collect_new_items("领袖")
        governors = self._collect_new_items("总督")
        policies = self._collect_new_items("政策卡", name_key="Name")
        projects = self._collect_new_items("项目", name_key="Name")
        beliefs = self._collect_new_items("信仰", name_key="Name")
        districts = self._collect_new_items("区域", name_key="Name")
        buildings = self._collect_new_items("建筑", name_key="Name")
        improvements = self._collect_new_items("改良设施", name_key="Name")
        units = self._collect_new_items("单位", name_key="Name")
        great_people = self._collect_new_items("伟人")

        alias_map = self._state_alias_map()
        atlas_rows: list[str] = []
        def_rows: list[str] = []
        alias_rows: list[str] = []
        alias_row_set: set[tuple[str, str]] = set()

        def _add_alias(name: str, other_name: str) -> None:
            key = (name, other_name)
            if key in alias_row_set:
                return
            alias_row_set.add(key)
            alias_rows.append(f'    <Row Name="{name}" OtherName="{other_name}"/>')

        def _add_atlas(atlas_name: str, icon_name: str, sizes: list[int]) -> None:
            for size in sizes:
                atlas_rows.append(f'    <Row Name="{atlas_name}" IconSize="{size}" Filename="{icon_name}_{size}"/>')

        for civ_type, _cn, _entry in civs:
            _add_atlas(f"ATLAS_{civ_type}", f"ICON_{civ_type}", self.SIZE_CIVILIZATION)
            def_rows.append(f'    <Row Name="ICON_{civ_type}" Atlas="ATLAS_{civ_type}" Index="0"/>')

        for leader_type, _cn, _entry in leaders:
            _add_atlas(f"ATLAS_{leader_type}", f"ICON_{leader_type}", self.SIZE_LEADER)
            def_rows.append(f'    <Row Name="ICON_{leader_type}" Atlas="ATLAS_{leader_type}" Index="0"/>')

        for gov_type, _cn, _entry in governors:
            main = f"ICON_{gov_type}"
            fill = f"{main}_FILL"
            slot = f"{main}_SLOT"
            promo = f"{main}_PROMOTION"
            atlas_main = f"ATLAS_{gov_type}"
            atlas_fill = f"ATLAS_{gov_type}_FILL"
            atlas_slot = f"ATLAS_{gov_type}_SLOT"
            _add_atlas(atlas_main, main, self.SIZE_GOVERNOR_MAIN)
            _add_atlas(atlas_fill, fill, self.SIZE_GOVERNOR_FILL_SLOT)
            _add_atlas(atlas_slot, slot, self.SIZE_GOVERNOR_FILL_SLOT)
            def_rows.append(f'    <Row Name="{main}" Atlas="{atlas_main}" Index="0"/>')
            def_rows.append(f'    <Row Name="{fill}" Atlas="{atlas_fill}" Index="0"/>')
            def_rows.append(f'    <Row Name="{slot}" Atlas="{atlas_slot}" Index="0"/>')
            _add_alias(promo, fill)
            _add_alias(f"{gov_type}_SLOT", slot)
            _add_alias(f"{gov_type}_FILL", fill)

        for policy_type, _cn, entry in policies:
            table_data = entry.get("table_data") if isinstance(entry.get("table_data"), dict) else {}
            slot_type = _safe_text(table_data.get("GovernmentSlotType") or "SLOT_WILDCARD")
            idx = self._policy_slot_index(slot_type)
            def_rows.append(f'    <Row Name="ICON_{policy_type}" Atlas="ICON_ATLAS_POLICIES" Index="{idx}"/>')

        def _apply_entity(
            entity_key: str,
            type_name: str,
            entry: dict[str, object],
            *,
            icon_name: str,
            atlas_name: str,
            sizes: list[int],
            variant: str = "icon",
        ) -> None:
            has_own = bool(self._image_path(entry, variant))
            state_key = f"{entity_key}:{type_name}:{variant}"
            alias = _safe_text(alias_map.get(state_key))

            # 兼容旧数据：单位肖像别名缺少 _PORTRAIT 时自动修正。
            if entity_key == "unit" and variant == "portrait":
                if alias and alias.startswith("ICON_UNIT_") and not alias.endswith("_PORTRAIT"):
                    alias = f"{alias}_PORTRAIT"
            if has_own or not alias:
                _add_atlas(atlas_name, icon_name, sizes)
                def_rows.append(f'    <Row Name="{icon_name}" Atlas="{atlas_name}" Index="0"/>')
            else:
                _add_alias(icon_name, alias)

        for type_name, _cn, entry in districts:
            _apply_entity("district", type_name, entry, icon_name=f"ICON_{type_name}", atlas_name=f"ATLAS_{type_name}", sizes=self.SIZE_DISTRICT)

        for type_name, _cn, entry in buildings:
            _apply_entity("building", type_name, entry, icon_name=f"ICON_{type_name}", atlas_name=f"ATLAS_{type_name}", sizes=self.SIZE_BUILDING)

        for type_name, _cn, entry in improvements:
            _apply_entity("improvement", type_name, entry, icon_name=f"ICON_{type_name}", atlas_name=f"ATLAS_{type_name}", sizes=self.SIZE_IMPROVEMENT)

        for type_name, _cn, entry in projects:
            _apply_entity("project", type_name, entry, icon_name=f"ICON_{type_name}", atlas_name=f"ATLAS_{type_name}", sizes=self.SIZE_PROJECT)

        for type_name, _cn, entry in beliefs:
            icon_name = f"ICON_{type_name}"
            _apply_entity("belief", type_name, entry, icon_name=icon_name, atlas_name=f"ATLAS_{icon_name}", sizes=self.SIZE_BELIEF)

        for type_name, _cn, entry in units:
            _apply_entity("unit", type_name, entry, icon_name=f"ICON_{type_name}", atlas_name=f"ATLAS_{type_name}", sizes=self.SIZE_UNIT, variant="icon")
            _apply_entity("unit", type_name, entry, icon_name=f"ICON_{type_name}_PORTRAIT", atlas_name=f"ATLAS_{type_name}_PORTRAIT", sizes=self.SIZE_UNIT_PORTRAIT, variant="portrait")

        for _great_type, _cn, entry in great_people:
            unit_data = entry.get("unit_data") if isinstance(entry.get("unit_data"), dict) else {}
            unit_type = _safe_text(unit_data.get("UnitType") or entry.get("unit_type"))
            if not unit_type:
                continue
            images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
            unit_icon_name = _safe_text(images.get("unit_icon_name")) or f"ICON_{unit_type}"
            unit_portrait_name = _safe_text(images.get("unit_portrait_name")) or f"ICON_{unit_type}_PORTRAIT"
            icon_payload = images.get("unit_icon") if isinstance(images.get("unit_icon"), dict) else {}
            portrait_payload = images.get("unit_portrait") if isinstance(images.get("unit_portrait"), dict) else {}
            icon_has_own = bool(_safe_text(icon_payload.get("path")))
            portrait_has_own = bool(_safe_text(portrait_payload.get("path")))

            icon_state_key = f"unit:{unit_type}:icon"
            icon_alias = _safe_text(alias_map.get(icon_state_key))
            if icon_has_own or not icon_alias:
                _add_atlas(f"ATLAS_{unit_type}", unit_icon_name, self.SIZE_UNIT)
                def_rows.append(f'    <Row Name="ICON_{unit_type}" Atlas="ATLAS_{unit_type}" Index="0"/>')
            else:
                _add_alias(f"ICON_{unit_type}", icon_alias)

            portrait_state_key = f"unit:{unit_type}:portrait"
            portrait_alias = _safe_text(alias_map.get(portrait_state_key))
            if portrait_alias and portrait_alias.startswith("ICON_UNIT_") and not portrait_alias.endswith("_PORTRAIT"):
                portrait_alias = f"{portrait_alias}_PORTRAIT"
            if portrait_has_own or not portrait_alias:
                _add_atlas(f"ATLAS_{unit_type}_PORTRAIT", unit_portrait_name, self.SIZE_UNIT_PORTRAIT)
                def_rows.append(f'    <Row Name="ICON_{unit_type}_PORTRAIT" Atlas="ATLAS_{unit_type}_PORTRAIT" Index="0"/>')
            else:
                _add_alias(f"ICON_{unit_type}_PORTRAIT", portrait_alias)

        lines: list[str] = [
            "<?xml version='1.0' encoding='utf-8'?>",
            "<GameData>",
            "  <IconTextureAtlases>",
            *atlas_rows,
            "  </IconTextureAtlases>",
            "  <IconDefinitions>",
            *def_rows,
            "  </IconDefinitions>",
        ]
        if alias_rows:
            lines.extend([
                "  <IconAliases>",
                *alias_rows,
                "  </IconAliases>",
            ])
        lines.append("</GameData>")
        lines.append("")
        return "\n".join(lines)

    def _build_xlp_files(self) -> list[tuple[str, str]]:
        files = [
            ("UI_Icons_dds.xlp", self._build_ui_texture_xlp_xml("UI_Icons")),
            ("LeaderFallback.xlp", self._build_leader_fallback_xlp_xml()),
        ]
        for row in self._selected_leader_xlp_rows():
            files.append((row.xlp_file_name, self._build_single_leader_xlp_xml(row)))
        extra_flags = self._state_extra_xlp_flags()
        for filename, content in EXTRA_XLP_TEMPLATES:
            if extra_flags.get(filename):
                files.append((filename, content))
        return files

    def _build_artdef_files(self) -> list[tuple[str, str]]:
        files = [
            ("Districts.artdef", self._build_districts_artdef_xml()),
            ("Buildings.artdef", self._build_buildings_artdef_xml()),
            ("Improvements.artdef", self._build_improvements_artdef_xml()),
            ("Units.artdef", self._build_units_artdef_xml()),
            ("FallbackLeaders.artdef", self._build_leader_fallback_artdef_xml()),
            ("Civilizations.artdef", self._build_civilizations_artdef_xml()),
            ("Cultures.artdef", self._build_cultures_artdef_xml()),
        ]
        if self._selected_leader_xlp_rows():
            files.append(("Leaders.artdef", self._build_leaders_artdef_xml()))
        extra_flags = self._state_extra_artdef_flags()
        for filename, content in EXTRA_ARTDEF_TEMPLATES:
            if extra_flags.get(filename):
                files.append((filename, content))
        return files
