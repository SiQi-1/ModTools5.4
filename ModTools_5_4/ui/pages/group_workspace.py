"""分组工作区：文明/领袖/区域等分类与子条目编辑。"""
from __future__ import annotations

from copy import deepcopy
import re
import random
import sqlite3
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...app.settings_store import load_settings
from ...db.interface import get_chinese_text_for_tag_or_unknown, resolve_chinese_text_or_unknown
from ...db.paths import DEFAULT_GAME_DB
from ..ui_widget_kit import IconTokenTextEdit, NewlineTokenTextEdit, build_template_widget
from .entity_table_form import AgendaCompositeEditor, BeliefCompositeEditor, BuildingCompositeEditor, DistrictCompositeEditor, ImprovementCompositeEditor, PolicyCompositeEditor, ProjectCompositeEditor, UnitCompositeEditor
from .great_people_editor import GreatPeopleCompositeEditor

SECTION_FILE_BASENAME = {
    "文明": "Civilizations",
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
}

CIV_LEVEL_LABELS = {
    "CIVILIZATION_LEVEL_FULL_CIV": "主要文明",
    "CIVILIZATION_LEVEL_CITY_STATE": "城邦",
    "CIVILIZATION_LEVEL_TRIBE": "蛮族",
    "CIVILIZATION_LEVEL_FREE_CITIES": "自由城市",
}

ETHNICITY_LABELS = {
    "NULL": "无",
    "ETHNICITY_AFRICAN": "非洲人",
    "ETHNICITY_ASIAN": "亚洲人",
    "ETHNICITY_EURO": "欧洲人",
    "ETHNICITY_MEDIT": "地中海人",
    "ETHNICITY_SOUTHAM": "南美人",
}

BINDABLE_SECTION_OPTIONS: list[tuple[str, str]] = [
    ("区域", "区域"),
    ("建筑", "建筑"),
    ("单位", "单位"),
    ("改良设施", "改良设施"),
    ("总督", "总督"),
    ("伟人", "伟人"),
    ("议程", "议程"),
]

LEADER_DIPLO_SCENES: list[tuple[str, str]] = [
    ("当你第一次遇到AI", "FIRST_MEET_LEADER_XXX_ANY"),
    ("当你第一次遇到AI并且TA邀请你参观城市", "FIRST_MEET_VISIT_RECIPIENT_LEADER_XXX_ANY"),
    ("当你第一次遇到AI并且你邀请TA参观城市", "FIRST_MEET_NEAR_INITIATOR_POSITIVE_LEADER_XXX_ANY"),
    ("当你第一次遇到AI并且TA请求分享首都位置", "FIRST_MEET_NO_MANS_INFO_EXCHANGE_LEADER_XXX_ANY"),
    ("一般打招呼用", "GREETING_LEADER_XXX_ANY"),
    ("你接受AI的交易", "MAKE_DEAL_AI_ACCEPT_DEAL_LEADER_XXX_ANY"),
    ("你拒绝AI的交易", "MAKE_DEAL_AI_REFUSE_DEAL_LEADER_XXX_ANY"),
    ("AI接受你的交易", "ACCEPT_MAKE_DEAL_FROM_AI_LEADER_XXX_ANY"),
    ("AI拒绝你的交易", "REJECT_MAKE_DEAL_FROM_AI_LEADER_XXX_ANY"),
    ("AI同意你的索取", "AI_ACCEPT_DEMAND_LEADER_XXX_ANY"),
    ("AI拒绝你的索取", "AI_REFUSE_DEMAND_LEADER_XXX_ANY"),
    ("当你同意AI的索取", "HUMAN_ACCEPT_DEMAND_FROM_AI_LEADER_XXX_ANY"),
    ("当你拒绝AI的索取", "HUMAN_REFUSE_DEMAND_FROM_AI_LEADER_XXX_ANY"),
    ("当AI同意你的代表团", "ACCEPT_DELEGATION_FROM_HUMAN_LEADER_XXX_ANY"),
    ("当AI拒绝你的代表团", "REJECT_DELEGATION_FROM_HUMAN_LEADER_XXX_ANY"),
    ("当AI派遣代表团的时候", "DELEGATION_FROM_AI_LEADER_XXX_ANY"),
    ("你对AI宣布友谊获得允许的时候", "ACCEPT_DECLARE_FRIEND_FROM_HUMAN_LEADER_XXX_ANY"),
    ("你对AI宣布友谊被拒绝的时候", "REJECT_DECLARE_FRIEND_FROM_HUMAN_LEADER_XXX_ANY"),
    ("当AI对你宣布友谊的时候", "DECLARE_FRIEND_FROM_AI_LEADER_XXX_ANY"),
    ("当你同意AI对你宣布友谊", "ACCEPT_DECLARE_FRIEND_FROM_AI_LEADER_XXX_ANY"),
    ("当你拒绝AI对你宣布友谊", "REJECT_DECLARE_FRIEND_FROM_AI_LEADER_XXX_ANY"),
    ("AI希望延续同盟", "MAKE_ALLIANCE_FROM_AI_LEADER_XXX_ANY"),
    ("AI希望你开放边界", "OPEN_BORDERS_FROM_AI_LEADER_XXX_ANY"),
    ("AI同意对你开放边界", "ACCEPT_OPEN_BORDERS_FROM_HUMAN_LEADER_XXX_ANY"),
    ("AI拒绝对你开放边界", "REJECT_OPEN_BORDERS_FROM_HUMAN_LEADER_XXX_ANY"),
    ("AI说你军队靠近边界", "WARNING_TOO_MANY_TROOPS_NEAR_ME_LEADER_XXX_ANY"),
    ("AI不同意撤离军队", "WARNING_TOO_MANY_TROOPS_NEAR_ME_AI_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
    ("AI同意撤离军队", "WARNING_TOO_MANY_TROOPS_NEAR_ME_AI_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("AI说你的国土靠的太近了", "WARNING_DONT_SETTLE_NEAR_ME_AI_LEADER_XXX_ANY"),
    ("AI同意远离你的领土", "WARNING_DONT_SETTLE_NEAR_ME_AI_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("AI不同意远离你的领土", "WARNING_DONT_SETTLE_NEAR_ME_AI_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
    ("你同意远离AI的领土", "WARNING_DONT_SETTLE_NEAR_ME_HUMAN_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("你不同意远离AI的领土", "WARNING_DONT_SETTLE_NEAR_ME_HUMAN_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
    ("当你公开谴责AI", "DENOUNCE_FROM_HUMAN_LEADER_XXX_ANY"),
    ("当AI公开谴责你", "DENOUNCE_FROM_AI_LEADER_XXX_ANY"),
    ("当你对这个AI宣战", "DECLARE_WAR_FROM_HUMAN_LEADER_XXX_ANY"),
    ("当这个AI向你宣战", "DECLARE_WAR_FROM_AI_LEADER_XXX_ANY"),
    ("当AI被其他AI击败会说这些话", "DEFEAT_FROM_AI_LEADER_XXX_ANY"),
    ("当你击败AI他会说这些话", "DEFEAT_FROM_HUMAN_LEADER_XXX_ANY"),
    ("AI让你别派间谍", "WARNING_STOP_SPYING_ON_ME_LEADER_XXX_ANY"),
    ("AI同意不派间谍", "WARNING_STOP_SPYING_ON_ME_AI_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("AI不同意不派间谍", "WARNING_STOP_SPYING_ON_ME_AI_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
    ("你同意不派间谍", "WARNING_STOP_SPYING_ON_ME_HUMAN_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("你不同意不派间谍", "WARNING_STOP_SPYING_ON_ME_HUMAN_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
    ("AI让你别来传教", "WARNING_STOP_CONVERTING_MY_CITIES_LEADER_XXX_ANY"),
    ("AI同意不来传教", "WARNING_STOP_CONVERTING_MY_CITIES_AI_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("AI不同意不来传教", "WARNING_STOP_CONVERTING_MY_CITIES_AI_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
    ("你同意不来传教", "WARNING_STOP_CONVERTING_MY_CITIES_HUMAN_RESPONSE_POSITIVE_LEADER_XXX_ANY"),
    ("你不同意不来传教", "WARNING_STOP_CONVERTING_MY_CITIES_HUMAN_RESPONSE_NEGATIVE_LEADER_XXX_ANY"),
]

DESC_SUFFIX_OPTIONS = ["帝国", "王国", "共和国", "城邦"]

SMALL_BUTTON_QSS = (
    "QPushButton {"
    "padding: 4px 10px;"
    "font-size: 12px;"
    "min-height: 24px;"
    "border: 1px solid #c7d3e9;"
    "border-radius: 8px;"
    "background: #ffffff;"
    "color: #1f4c88;"
    "}"
    "QPushButton:hover {"
    "background: #eef5ff;"
    "border-color: #9eb7de;"
    "}"
    "QPushButton:pressed {"
    "background: #dce9ff;"
    "border-color: #86a3d3;"
    "}"
)


def _safe_text(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def _sanitize_short_token(value: object | None) -> str:
    raw = _safe_text(value)
    if not raw:
        return ""
    return re.sub(r"[^A-Za-z0-9_]", "", raw).upper()


def _build_entity_type(shared: dict[str, object], *, head: str, midfix_code: str, short_name: object | None) -> str:
    prefix = _safe_text(shared.get("prefix")).upper()
    try:
        infix = max(0, int(shared.get("infix", 0)))
    except (TypeError, ValueError):
        infix = 0
    short = _sanitize_short_token(short_name)

    parts = [head]
    if prefix:
        parts.append(prefix)
    if infix > 0:
        parts.append(f"{midfix_code}{infix:04d}")
    if short:
        parts.append(short)
    return "_".join(parts)


def _first_non_empty_value(data: dict[str, object]) -> str:
    for value in data.values():
        text = _safe_text(value)
        if text:
            return text
    return ""


def _apply_small_button(button: QPushButton) -> None:
    button.setStyleSheet(SMALL_BUTTON_QSS)
    button.setMinimumHeight(22)


def _active_game_db_path() -> Path:
    settings = load_settings()
    configured = _safe_text(settings.game_db_path)
    if configured and Path(configured).exists():
        return Path(configured)
    return DEFAULT_GAME_DB


def _query_random_agendas() -> list[tuple[str, str]]:
    """Return (AgendaType, display_name) from RandomAgendas with Chinese names resolved."""
    gdb = _active_game_db_path()
    if not gdb.exists():
        return []
    try:
        conn = sqlite3.connect(str(gdb))
        rows = conn.execute(
            "SELECT ra.AgendaType, a.Name FROM RandomAgendas ra "
            "LEFT JOIN Agendas a ON ra.AgendaType = a.AgendaType "
            "ORDER BY ra.AgendaType"
        ).fetchall()
        conn.close()
        result: list[tuple[str, str]] = []
        for agenda_type, name_tag in rows:
            chinese_name = resolve_chinese_text_or_unknown(str(name_tag or ""))
            display = f"{agenda_type}（{chinese_name}）"
            result.append((str(agenda_type), display))
        return result
    except sqlite3.Error:
        return []


def _query_ai_list_types() -> list[str]:
    """Return distinct System values from AiListTypes table in game DB."""
    gdb = _active_game_db_path()
    if not gdb.exists():
        return []
    try:
        conn = sqlite3.connect(str(gdb))
        rows = conn.execute("SELECT DISTINCT System FROM AiLists ORDER BY System").fetchall()
        conn.close()
        return [str(r[0]) for r in rows if r[0]]
    except sqlite3.Error:
        return []


def _query_agenda_reqset_options() -> list[tuple[str, str]]:
    """Return (SubjectRequirementSetId, display) for all agenda diplomacy ReqSets."""
    gdb = _active_game_db_path()
    if not gdb.exists():
        return []
    try:
        conn = sqlite3.connect(str(gdb))
        rows = conn.execute(
            "SELECT DISTINCT m.SubjectRequirementSetId "
            "FROM Modifiers m "
            "WHERE m.ModifierType = 'MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER' "
            "AND m.SubjectRequirementSetId IS NOT NULL "
            "ORDER BY m.SubjectRequirementSetId"
        ).fetchall()
        conn.close()
        return [(str(r[0]), str(r[0])) for r in rows]
    except sqlite3.Error:
        return []


def _resolve_loc_text(tag: str) -> str:
    """Resolve a LOC tag to Chinese text from the active text database."""
    if not tag or not tag.strip():
        return ""
    from ...db.interface import get_chinese_text_for_tag_or_unknown
    result = get_chinese_text_for_tag_or_unknown(tag)
    if result == "未知":
        # Try base text source database as fallback
        from ...app.settings_store import load_settings
        settings = load_settings()
        base_path = settings.base_text_source_db_path
        if base_path and Path(base_path).exists():
            try:
                conn = sqlite3.connect(str(base_path))
                row = conn.execute(
                    "SELECT Text FROM LocalizedText WHERE Tag = ? AND lower(Language) = 'zh_hans_cn' LIMIT 1",
                    (tag,),
                ).fetchone()
                conn.close()
                if row:
                    return str(row[0] or "") or tag
            except sqlite3.Error:
                pass
    return result


def _query_empty_reqsets() -> list[dict[str, object]]:
    """Fallback: return empty list for custom reqset provider."""
    return []


def _active_text_db_path() -> Path | None:
    settings = load_settings()
    configured = _safe_text(settings.active_text_db_path)
    if configured and Path(configured).exists():
        return Path(configured)
    return None


def _resolve_text_from_tag(tag: str) -> str:
    return get_chinese_text_for_tag_or_unknown(tag, unknown_text="未知")


def _fetch_major_civilizations() -> list[tuple[str, str]]:
    db_path = _active_game_db_path()
    if not db_path.exists():
        return []

    rows: list[tuple[str, str]] = []
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT CivilizationType, Name
            FROM Civilizations
            WHERE StartingCivilizationLevelType = 'CIVILIZATION_LEVEL_FULL_CIV'
            ORDER BY CivilizationType
            """
        )
        rows = [(str(civ_type), str(name_tag or "")) for civ_type, name_tag in cursor.fetchall()]
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    mapped = [(civ_type, _resolve_text_from_tag(name_tag) if name_tag else "未知") for civ_type, name_tag in rows]
    mapped.sort(key=lambda item: (item[1] == "未知", item[1], item[0]))
    return mapped


def _fetch_city_names_for_civ(civ_type: str) -> list[str]:
    db_path = _active_game_db_path()
    if not db_path.exists() or not civ_type:
        return []

    rows: list[str] = []
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT CityName
            FROM CityNames
            WHERE CivilizationType = ?
            ORDER BY rowid
            """,
            (civ_type,),
        )
        rows = [str(tag or "").strip() for (tag,) in cursor.fetchall()]
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    return [_resolve_text_from_tag(tag) for tag in rows if tag]


def _fetch_citizens_for_civ(civ_type: str) -> list[tuple[str, bool, bool]]:
    db_path = _active_game_db_path()
    if not db_path.exists() or not civ_type:
        return []

    rows: list[tuple[str, int, int]] = []
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT CitizenName, Female, Modern
            FROM CivilizationCitizenNames
            WHERE CivilizationType = ?
            ORDER BY rowid
            """,
            (civ_type,),
        )
        rows = [(str(tag or ""), int(female or 0), int(modern or 0)) for tag, female, modern in cursor.fetchall()]
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    output: list[tuple[str, bool, bool]] = []
    for tag, female, modern in rows:
        if not tag:
            continue
        output.append((_resolve_text_from_tag(tag), bool(female), bool(modern)))
    return output


def _fetch_random_city_pool_zh() -> list[str]:
    db_path = _active_text_db_path()
    if db_path is None:
        return []

    pool: list[str] = []
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Text
            FROM LocalizedText
            WHERE Tag LIKE 'LOC_CITY_NAME_%'
              AND lower(Language) = 'zh_hans_cn'
              AND Text IS NOT NULL
              AND trim(Text) != ''
            """
        )
        raw_values = [str(text or "").strip() for (text,) in cursor.fetchall() if str(text or "").strip()]
        pool = [resolve_chinese_text_or_unknown(item, unknown_text="未知") for item in raw_values]
    except sqlite3.Error:
        pool = []
    finally:
        conn.close()
    return [name for name in pool if _safe_text(name) and _safe_text(name) != "未知"]


def _fetch_random_citizen_pool_zh() -> list[tuple[str, bool, bool]]:
    db_path = _active_game_db_path()
    if not db_path.exists():
        return []

    rows: list[tuple[str, int, int]] = []
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT CitizenName, Female, Modern FROM CivilizationCitizenNames")
        rows = [(str(tag or ""), int(female or 0), int(modern or 0)) for tag, female, modern in cursor.fetchall()]
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    output: list[tuple[str, bool, bool]] = []
    for tag, female, modern in rows:
        if not tag:
            continue
        localized = _resolve_text_from_tag(tag)
        if localized and localized != "未知":
            output.append((localized, bool(female), bool(modern)))
    return output


class _CityNamesTable(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 1)
        self.setHorizontalHeaderLabels(["城市名字"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def set_count(self, count: int) -> None:
        target = max(1, count)
        current = self.rowCount()
        if target == current:
            return
        if target > current:
            for _ in range(target - current):
                row = self.rowCount()
                self.insertRow(row)
                if self.item(row, 0) is None:
                    self.setItem(row, 0, QTableWidgetItem(""))
        else:
            while self.rowCount() > target:
                self.removeRow(self.rowCount() - 1)
        self._sync_height()

    def set_names(self, names: list[str], *, min_rows: int = 1) -> None:
        self.set_count(max(min_rows, len(names)))
        for row in range(self.rowCount()):
            value = names[row] if row < len(names) else ""
            item = self.item(row, 0)
            if item is None:
                item = QTableWidgetItem("")
                self.setItem(row, 0, item)
            item.setText(value)
        self._sync_height()

    def names(self) -> list[str]:
        return [self.item(row, 0).text() if self.item(row, 0) else "" for row in range(self.rowCount())]

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self._handle_paste()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            row = self.currentRow()
            if row < 0:
                row = 0
            if row + 1 < self.rowCount():
                self.setCurrentCell(row + 1, 0)
            event.accept()
            return
        super().keyPressEvent(event)

    def _handle_paste(self) -> None:
        raw = QApplication.clipboard().text()
        if raw is None:
            return
        text = str(raw).replace("\r\n", "\n").replace("\r", "\n")
        parts = text.split("\n")
        if len(parts) <= 1:
            row = max(0, self.currentRow())
            self.set_count(max(self.rowCount(), row + 1))
            item = self.item(row, 0)
            if item is None:
                item = QTableWidgetItem("")
                self.setItem(row, 0, item)
            item.setText(text)
            return

        start_row = max(0, self.currentRow())
        self.set_count(max(self.rowCount(), start_row + len(parts)))
        for offset, value in enumerate(parts):
            row = start_row + offset
            item = self.item(row, 0)
            if item is None:
                item = QTableWidgetItem("")
                self.setItem(row, 0, item)
            item.setText(value)
        self.setCurrentCell(min(self.rowCount() - 1, start_row + len(parts) - 1), 0)
        self._sync_height()

    def _sync_height(self) -> None:
        header_height = self.horizontalHeader().height()
        frame_height = self.frameWidth() * 2
        row_height = max(22, self.verticalHeader().defaultSectionSize())
        body_height = max(1, self.rowCount()) * row_height
        self.setMinimumHeight(header_height + body_height + frame_height + 2)


class _CitizenTable(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["市民名字", "女性", "现代"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def set_count(self, count: int) -> None:
        target = max(1, count)
        current = self.rowCount()
        if target == current:
            return
        if target > current:
            for _ in range(target - current):
                row = self.rowCount()
                self.insertRow(row)
                self._ensure_row(row)
        else:
            while self.rowCount() > target:
                self.removeRow(self.rowCount() - 1)
        self._sync_height()

    def _ensure_row(self, row: int) -> None:
        if self.item(row, 0) is None:
            self.setItem(row, 0, QTableWidgetItem(""))
        for col in (1, 2):
            item = self.item(row, col)
            if item is None:
                item = QTableWidgetItem("")
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(Qt.CheckState.Unchecked)
                self.setItem(row, col, item)

    def set_rows(self, rows: list[tuple[str, bool, bool]], *, min_rows: int = 1) -> None:
        self.set_count(max(min_rows, len(rows)))
        for row in range(self.rowCount()):
            name, female, modern = rows[row] if row < len(rows) else ("", False, False)
            self._ensure_row(row)
            self.item(row, 0).setText(name)
            self.item(row, 1).setCheckState(Qt.CheckState.Checked if female else Qt.CheckState.Unchecked)
            self.item(row, 2).setCheckState(Qt.CheckState.Checked if modern else Qt.CheckState.Unchecked)
        self._sync_height()

    def rows_payload(self) -> list[tuple[str, bool, bool]]:
        payload: list[tuple[str, bool, bool]] = []
        for row in range(self.rowCount()):
            name = self.item(row, 0).text() if self.item(row, 0) else ""
            female = bool(self.item(row, 1) and self.item(row, 1).checkState() == Qt.CheckState.Checked)
            modern = bool(self.item(row, 2) and self.item(row, 2).checkState() == Qt.CheckState.Checked)
            payload.append((name, female, modern))
        return payload

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self._handle_paste()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            row = self.currentRow()
            if row < 0:
                row = 0
            if row + 1 < self.rowCount():
                self.setCurrentCell(row + 1, 0)
            event.accept()
            return
        super().keyPressEvent(event)

    def _handle_paste(self) -> None:
        raw = QApplication.clipboard().text()
        if raw is None:
            return
        text = str(raw).replace("\r\n", "\n").replace("\r", "\n")
        parts = text.split("\n")
        if len(parts) <= 1:
            row = max(0, self.currentRow())
            self.set_count(max(self.rowCount(), row + 1))
            self._ensure_row(row)
            self.item(row, 0).setText(text)
            return

        start_row = max(0, self.currentRow())
        self.set_count(max(self.rowCount(), start_row + len(parts)))
        for offset, value in enumerate(parts):
            row = start_row + offset
            self._ensure_row(row)
            self.item(row, 0).setText(value)
        self.setCurrentCell(min(self.rowCount() - 1, start_row + len(parts) - 1), 0)
        self._sync_height()

    def _sync_height(self) -> None:
        header_height = self.horizontalHeader().height()
        frame_height = self.frameWidth() * 2
        row_height = max(22, self.verticalHeader().defaultSectionSize())
        body_height = max(1, self.rowCount()) * row_height
        self.setMinimumHeight(header_height + body_height + frame_height + 2)


class SectionGroupWorkspacePanel(QWidget):
    """分类总览页：新增按钮、预览格式切换、数据文件预览。"""

    def __init__(
        self,
        *,
        on_add_entry: Callable[[str], None],
        on_import_entry: Callable[[str], None],
        preview_provider: Callable[[str, str], str],
        preview_format_getter: Callable[[str], str] | None = None,
        preview_format_setter: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("sectionGroupWorkspacePanel")
        self.setProperty("workspacePanel", "true")
        self._on_add_entry = on_add_entry
        self._on_import_entry = on_import_entry
        self._preview_provider = preview_provider
        self._preview_format_getter = preview_format_getter
        self._preview_format_setter = preview_format_setter
        self._section = ""

        self._add_button = QPushButton("新增")
        self._add_button.clicked.connect(self._handle_add)
        _apply_small_button(self._add_button)

        self._import_button = QPushButton("导入")
        self._import_button.clicked.connect(self._handle_import)
        _apply_small_button(self._import_button)

        self._data_sql_button = QPushButton("SQL预览")
        self._data_xml_button = QPushButton("XML预览")
        self._data_sql_button.setCheckable(True)
        self._data_xml_button.setCheckable(True)
        self._data_sql_button.setChecked(True)
        _apply_small_button(self._data_sql_button)
        _apply_small_button(self._data_xml_button)

        self._data_format_group = QButtonGroup(self)
        self._data_format_group.setExclusive(True)
        self._data_format_group.addButton(self._data_sql_button)
        self._data_format_group.addButton(self._data_xml_button)
        self._data_sql_button.clicked.connect(lambda: self._handle_format_button_clicked("sql"))
        self._data_xml_button.clicked.connect(lambda: self._handle_format_button_clicked("xml"))

        self._data_preview_tab = QTabWidget()
        self._data_preview_text = QPlainTextEdit()
        self._data_preview_text.setReadOnly(True)
        self._data_preview_tab.addTab(self._data_preview_text, "Preview")

        top_row = QHBoxLayout()
        top_row.addWidget(self._add_button)
        top_row.addWidget(self._import_button)
        top_row.addStretch(1)

        data_group = QGroupBox("数据文件预览")
        data_layout = QVBoxLayout()
        data_toolbar = QHBoxLayout()
        data_toolbar.addWidget(self._data_sql_button)
        data_toolbar.addWidget(self._data_xml_button)
        data_toolbar.addStretch(1)
        data_layout.addLayout(data_toolbar)
        data_layout.addWidget(self._data_preview_tab, 1)
        data_group.setLayout(data_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_row)
        layout.addWidget(data_group, 1)
        self.setLayout(layout)

    def set_section(self, section: str) -> None:
        self._section = section
        self._add_button.setText(f"新增{section}")
        self._import_button.setText(f"导入{section}")

        needs_import = section not in {"文明", "领袖", "总督", "政策卡", "项目", "信仰", "议程"}
        self._import_button.setVisible(needs_import)

        preferred_fmt = "sql"
        if callable(self._preview_format_getter):
            got = str(self._preview_format_getter(section) or "sql").strip().lower()
            if got in {"sql", "xml"}:
                preferred_fmt = got
        self._data_sql_button.setChecked(preferred_fmt != "xml")
        self._data_xml_button.setChecked(preferred_fmt == "xml")

        self.refresh_preview()

    def _handle_format_button_clicked(self, fmt: str) -> None:
        if self._section and callable(self._preview_format_setter):
            self._preview_format_setter(self._section, fmt)
        self._refresh_data_preview()

    def current_format(self) -> str:
        return "xml" if self._data_xml_button.isChecked() else "sql"

    def refresh_preview(self) -> None:
        self._refresh_data_preview()

    def _refresh_data_preview(self) -> None:
        if not self._section:
            self._data_preview_text.setPlainText("")
            return
        fmt = self.current_format()
        tab_name = SECTION_FILE_BASENAME.get(self._section, self._section)
        preview = self._preview_provider(self._section, fmt)
        if isinstance(preview, dict):
            self._data_preview_tab.clear()
            for file_name, content in preview.items():
                text_edit = QPlainTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setPlainText(str(content or ""))
                self._data_preview_tab.addTab(text_edit, str(file_name))
            if self._data_preview_tab.count() == 0:
                fallback = QPlainTextEdit()
                fallback.setReadOnly(True)
                self._data_preview_tab.addTab(fallback, f"{tab_name}.{fmt}")
        else:
            if self._data_preview_tab.count() != 1 or self._data_preview_tab.widget(0) is not self._data_preview_text:
                self._data_preview_tab.clear()
                self._data_preview_text = QPlainTextEdit()
                self._data_preview_text.setReadOnly(True)
                self._data_preview_tab.addTab(self._data_preview_text, "Preview")
            self._data_preview_tab.setTabText(0, f"{tab_name}.{fmt}")
            self._data_preview_text.setPlainText(str(preview or ""))

    def _handle_add(self) -> None:
        if self._section:
            self._on_add_entry(self._section)

    def _handle_import(self) -> None:
        if self._section:
            self._on_import_entry(self._section)

class _BindingSelectionDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        entries_provider: Callable[[str], list[dict[str, object]]],
        categories: list[tuple[str, str]],
        *,
        exclude_keys: Optional[set[tuple[str, object, str]]] = None,
    ) -> None:
        super().__init__(parent)
        self._entries_provider = entries_provider
        self._categories = categories
        self._exclude_keys: set[tuple[str, object, str]] = set(exclude_keys or set())
        self._list = QListWidget()

        self.setWindowTitle("选择绑定对象")
        self.resize(460, 380)

        layout = QVBoxLayout()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._list.itemDoubleClicked.connect(self._handle_item_double_clicked)
        self._populate_list()
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _populate_list(self) -> None:
        self._list.clear()
        has_entries = False
        for section_key, label in self._categories:
            entries = self._entries_provider(section_key)
            if not entries:
                continue
            has_entries = True
            for entry in entries:
                name = str(entry.get("name") or "").strip()
                type_name = str(entry.get("type") or "").strip()
                item_index = entry.get("index")
                if (section_key, item_index, type_name) in self._exclude_keys:
                    continue
                core = f"{name} ({type_name})" if name and type_name else (name or type_name or "未命名对象")
                display = core
                list_item = QListWidgetItem(display)
                list_item.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "section": section_key,
                        "name": name,
                        "type": type_name,
                        "index": item_index,
                    },
                )
                self._list.addItem(list_item)

        if not has_entries:
            placeholder = QListWidgetItem("当前无可用对象")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(placeholder)

    def selected_entries(self) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for item in self._list.selectedItems():
            payload = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, dict):
                results.append(dict(payload))
        return results

    def _handle_item_double_clicked(self, item: QListWidgetItem) -> None:
        if item.flags() & Qt.ItemFlag.ItemIsSelectable:
            item.setSelected(True)
            self.accept()


class _TraitBindingsEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        entries_provider: Callable[[str], list[dict[str, object]]],
        *,
        extra_excluded_keys_provider: Callable[[], set[tuple[str, object, str]]] | None = None,
    ) -> None:
        super().__init__()
        self._entries_provider = entries_provider
        self._extra_excluded_keys_provider = extra_excluded_keys_provider
        self._items: list[dict[str, object]] = []

        self._add_button = QPushButton("添加")
        self._remove_button = QPushButton("删除所选")
        self._add_button.clicked.connect(self._handle_add)
        self._remove_button.clicked.connect(self._handle_remove)
        _apply_small_button(self._add_button)
        _apply_small_button(self._remove_button)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["名称", "Type"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        top = QHBoxLayout()
        top.addWidget(self._add_button)
        top.addWidget(self._remove_button)
        top.addStretch(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self._table)
        self.setLayout(layout)

        self._sync_height()

    def set_values(self, values: list[object]) -> None:
        normalized: list[dict[str, object]] = []
        for value in values:
            if isinstance(value, dict):
                type_name = _safe_text(value.get("type"))
                if not type_name:
                    continue
                normalized.append(
                    {
                        "section": _safe_text(value.get("section")),
                        "category_label": _safe_text(value.get("category_label")) or _safe_text(value.get("section")),
                        "name": _safe_text(value.get("name")),
                        "type": type_name,
                        "index": value.get("index"),
                    }
                )
                continue

            legacy_text = _safe_text(value)
            if not legacy_text:
                continue
            type_name = legacy_text[6:] if legacy_text.startswith("TRAIT_") else legacy_text
            normalized.append(
                {
                    "section": "",
                    "category_label": "",
                    "name": "",
                    "type": type_name,
                    "index": None,
                }
            )

        self._items = normalized
        self._refresh_table()
        self._sync_height()

    def values(self) -> list[dict[str, object]]:
        return deepcopy(self._items)

    def _sync_height(self) -> None:
        row_height = max(22, self._table.verticalHeader().defaultSectionSize())
        header_height = self._table.horizontalHeader().height()
        frame = self._table.frameWidth() * 2
        row_count = max(3, len(self._items))
        self._table.setMinimumHeight(header_height + row_height * row_count + frame)

    def _handle_add(self) -> None:
        excluded: set[tuple[str, object, str]] = {
            (
                _safe_text(existing.get("section")),
                existing.get("index"),
                _safe_text(existing.get("type")),
            )
            for existing in self._items
            if _safe_text(existing.get("section")) and _safe_text(existing.get("type"))
        }
        if callable(self._extra_excluded_keys_provider):
            try:
                excluded |= set(self._extra_excluded_keys_provider())
            except Exception:
                pass

        dialog = _BindingSelectionDialog(
            self,
            self._entries_provider,
            BINDABLE_SECTION_OPTIONS,
            exclude_keys=excluded,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dialog.selected_entries()
        if not selected:
            return

        for entry in selected:
            type_name = _safe_text(entry.get("type"))
            if not type_name:
                continue
            section_key = _safe_text(entry.get("section"))
            item_index = entry.get("index")
            already_exists = any(
                _safe_text(existing.get("section")) == section_key
                and existing.get("index") == item_index
                and _safe_text(existing.get("type")) == type_name
                for existing in self._items
            )
            if already_exists:
                continue
            self._items.append(
                {
                    "section": section_key,
                    "name": _safe_text(entry.get("name")),
                    "type": type_name,
                    "index": item_index,
                }
            )

        self._refresh_table()
        self._sync_height()
        self.dataChanged.emit()

    def _handle_remove(self) -> None:
        selection = self._table.selectionModel()
        if selection is None:
            return
        rows = sorted({index.row() for index in selection.selectedRows()}, reverse=True)
        if not rows:
            return
        for row in rows:
            if 0 <= row < len(self._items):
                self._items.pop(row)
        self._refresh_table()
        self._sync_height()
        self.dataChanged.emit()

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._items))
        for row, entry in enumerate(self._items):
            name_item = QTableWidgetItem(_safe_text(entry.get("name")))
            type_item = QTableWidgetItem(_safe_text(entry.get("type")))
            for item in (name_item, type_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, type_item)


class _BiasRowsEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, title: str, template_key: str) -> None:
        super().__init__()
        self._template_key = template_key
        self._rows: list[tuple[QWidget, object, QSpinBox]] = []

        self._group = QGroupBox(title)
        self._add_button = QPushButton("添加")
        self._add_button.clicked.connect(self._add_row)
        _apply_small_button(self._add_button)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)

        group_layout = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(self._add_button)
        top.addStretch(1)
        group_layout.addLayout(top)
        group_layout.addLayout(self._rows_layout)
        self._group.setLayout(group_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._group)
        self.setLayout(layout)

    def set_payload(self, payload: list[dict[str, object]]) -> None:
        while self._rows:
            container, _widget, _tier = self._rows.pop()
            container.setParent(None)

        for item in payload:
            selector_data = item.get("selector_data") if isinstance(item, dict) else None
            tier_value = 1
            try:
                tier_value = max(1, min(5, int(item.get("tier", 1)))) if isinstance(item, dict) else 1
            except (TypeError, ValueError):
                tier_value = 1
            self._add_row(initial_selector=selector_data if isinstance(selector_data, dict) else None, initial_tier=tier_value)

    def export_payload(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for _container, widget, tier_spin in self._rows:
            export_data = widget.export_data() if hasattr(widget, "export_data") else {}
            if not isinstance(export_data, dict):
                export_data = {}
            result.append(
                {
                    "selector_data": export_data,
                    "selector_value": _first_non_empty_value(export_data),
                    "tier": int(tier_spin.value()),
                }
            )
        return result

    def _add_row(self, initial_selector: dict[str, object] | None = None, initial_tier: int = 1) -> None:
        container = QFrame()
        container.setObjectName("biasRowFrame")
        container.setStyleSheet(
            "QFrame#biasRowFrame {"
            "background: #f8fafc;"
            "border: 1px solid #e2e8f0;"
            "border-radius: 8px;"
            "padding: 6px;"
            "}"
        )

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(10)

        selector_widget = build_template_widget(self._template_key)
        if initial_selector and hasattr(selector_widget, "set_current_value"):
            try:
                value = _first_non_empty_value(initial_selector)
                selector_widget.set_current_value(value)
            except Exception:
                pass

        tier_label = QLabel("绑定等级")
        tier_spin = QSpinBox()
        tier_spin.setRange(1, 5)
        tier_spin.setValue(max(1, min(5, int(initial_tier))))

        delete_button = QPushButton("删除")
        _apply_small_button(delete_button)

        row_layout.addWidget(selector_widget, 1)
        row_layout.addWidget(tier_label)
        row_layout.addWidget(tier_spin)
        row_layout.addWidget(delete_button)
        container.setLayout(row_layout)

        self._rows_layout.addWidget(container)
        self._rows.append((container, selector_widget, tier_spin))

        if hasattr(selector_widget, "dataChanged"):
            selector_widget.dataChanged.connect(self.dataChanged.emit)
        tier_spin.valueChanged.connect(lambda _v: self.dataChanged.emit())
        delete_button.clicked.connect(lambda: self._delete_row(container))

        self.dataChanged.emit()

    def _delete_row(self, container: QWidget) -> None:
        for idx, (widget_container, _widget, _tier) in enumerate(self._rows):
            if widget_container is container:
                self._rows.pop(idx)
                widget_container.setParent(None)
                self.dataChanged.emit()
                return


class CivilizationItemEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        shared_params_provider: Callable[[], dict[str, object]],
        bindable_entries_provider: Callable[[str], list[dict[str, object]]],
    ) -> None:
        super().__init__()
        self._shared_params_provider = shared_params_provider
        self._bindable_entries_provider = bindable_entries_provider
        self._entry_name_fallback = "新文明"
        self._internal_updating = False
        self._auto_filling_name_fields = False
        self._desc_manual = False
        self._adj_manual = False

        self._abbr_edit = QLineEdit()
        self._abbr_edit.setPlaceholderText("仅英文/数字/下划线")

        self._type_label = QLabel("CIVILIZATION")
        self._type_label.setObjectName("pageInfoLabel")
        self._icon_name = QLineEdit()
        self._icon_name.setReadOnly(True)
        self._icon_image = _ImageSlotWidget((256, 256), enable_circle_crop=True)

        self._name_edit = QLineEdit()
        self._desc_edit = QLineEdit()
        self._adj_edit = QLineEdit()

        self._name_loc_label = QLabel("")
        self._desc_loc_label = QLabel("")
        self._adj_loc_label = QLabel("")
        for label in (self._name_loc_label, self._desc_loc_label, self._adj_loc_label):
            label.setObjectName("pageInfoLabel")
            label.setStyleSheet("font-size: 11px;")

        self._desc_suffix_combo = QComboBox()
        self._desc_suffix_combo.addItems(DESC_SUFFIX_OPTIONS)
        self._desc_suffix_combo.setCurrentText("帝国")

        self._level_combo = QComboBox()
        for key, text in CIV_LEVEL_LABELS.items():
            self._level_combo.addItem(f"{text}（{key}）", key)

        self._ethnicity_combo = QComboBox()
        for key, text in ETHNICITY_LABELS.items():
            self._ethnicity_combo.addItem(f"{text}（{key}）", key)
        self._ethnicity_combo.setCurrentIndex(max(0, self._ethnicity_combo.findData("ETHNICITY_ASIAN")))

        self._city_depth_spin = QSpinBox()
        self._city_depth_spin.setRange(1, 100)
        self._city_depth_spin.setValue(10)

        self._trait_name_edit = QLineEdit()
        self._trait_desc_edit = IconTokenTextEdit()
        self._trait_desc_edit.setPlaceholderText("输入文明能力描述，换行会在导出时转为 [NEWLINE]")
        self._trait_desc_edit.setFixedHeight(96)

        self._trait_bindings = _TraitBindingsEditor(self._bindable_entries_provider)

        self._city_mode_combo = QComboBox()
        self._city_mode_combo.addItems(["现有文明", "自定义", "随机模式"])
        self._city_mode_stack = QStackedWidget()
        self._city_mode_stack.addWidget(self._build_existing_city_widget())
        self._city_mode_stack.addWidget(self._build_custom_city_widget())
        self._city_mode_stack.addWidget(self._build_random_city_widget())

        self._citizen_mode_combo = QComboBox()
        self._citizen_mode_combo.addItems(["现有文明", "自定义", "随机模式"])
        self._citizen_mode_stack = QStackedWidget()
        self._citizen_mode_stack.addWidget(self._build_existing_citizen_widget())
        self._citizen_mode_stack.addWidget(self._build_custom_citizen_widget())
        self._citizen_mode_stack.addWidget(self._build_random_citizen_widget())

        self._terrain_bias = _BiasRowsEditor("开局绑定地形", "terrain")
        self._feature_bias = _BiasRowsEditor("开局绑定地貌", "feature_passable")
        self._resource_bias = _BiasRowsEditor("开局绑定资源", "resource_search")

        self._river_enabled = QCheckBox("开局绑定河流")
        self._river_tier_spin = QSpinBox()
        self._river_tier_spin.setRange(1, 5)
        self._river_tier_spin.setValue(1)

        self._city_panel: QWidget | None = None
        self._citizen_panel: QWidget | None = None
        self._city_citizen_layout: QGridLayout | None = None
        self._is_compact_city_layout = False
        self._top_left_panel: QWidget | None = None
        self._top_icon_panel: QWidget | None = None

        self._build_layout()
        self._bind_events()
        self._refresh_type_and_loc_hints()

    def _build_layout(self) -> None:
        content = QWidget()
        content_layout = QVBoxLayout()

        base_group = QGroupBox("基础信息区域")
        base_layout = QVBoxLayout()

        top_row = QHBoxLayout()

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        type_form = QFormLayout()
        type_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        type_form.addRow("简称", self._abbr_edit)
        type_form.addRow("完整Type", self._type_label)
        left_layout.addLayout(type_form)

        name_form = QFormLayout()
        name_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        name_form.addRow("文明名字", self._name_edit)

        icon_panel = QWidget()
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(self._icon_name)
        icon_layout.addWidget(self._icon_image)
        icon_panel.setLayout(icon_layout)

        desc_row = QWidget()
        desc_layout = QHBoxLayout()
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.addWidget(self._desc_edit, 1)
        desc_layout.addWidget(self._desc_suffix_combo)
        desc_row.setLayout(desc_layout)
        name_form.addRow("文明描述", desc_row)

        name_form.addRow("文明形容", self._adj_edit)
        left_layout.addLayout(name_form)

        extra_form = QFormLayout()
        extra_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        extra_form.addRow("文明等级", self._level_combo)
        extra_form.addRow("种族", self._ethnicity_combo)
        extra_form.addRow("随机城市名深度", self._city_depth_spin)
        extra_form.addRow("文明能力名字（中文）", self._trait_name_edit)
        left_layout.addLayout(extra_form)

        left_panel.setLayout(left_layout)
        self._top_left_panel = left_panel

        top_row.addWidget(left_panel, 1)
        top_row.addWidget(icon_panel, 0)
        self._top_icon_panel = icon_panel

        base_layout.addLayout(top_row)

        loc_row = QWidget()
        loc_layout = QHBoxLayout()
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(10)
        loc_layout.addWidget(self._name_loc_label, 1)
        loc_layout.addWidget(self._desc_loc_label, 1)
        loc_layout.addWidget(self._adj_loc_label, 1)
        loc_row.setLayout(loc_layout)
        base_layout.addWidget(loc_row)

        trait_desc_form = QFormLayout()
        trait_desc_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        trait_desc_form.addRow("文明能力描述（中文）", self._trait_desc_edit)
        base_layout.addLayout(trait_desc_form)

        trait_group = QGroupBox("Trait绑定区域")
        trait_layout = QVBoxLayout()
        trait_layout.addWidget(self._trait_bindings)
        trait_group.setLayout(trait_layout)
        base_layout.addWidget(trait_group)

        base_group.setLayout(base_layout)

        city_citizen_group = QGroupBox("城市市民信息区域")
        city_citizen_layout = QGridLayout()
        self._city_panel = self._build_mode_panel("城市名字", self._city_mode_combo, self._city_mode_stack)
        self._citizen_panel = self._build_mode_panel("市民名字", self._citizen_mode_combo, self._citizen_mode_stack)
        city_citizen_layout.addWidget(self._city_panel, 0, 0)
        city_citizen_layout.addWidget(self._citizen_panel, 0, 1)
        city_citizen_layout.setColumnStretch(0, 1)
        city_citizen_layout.setColumnStretch(1, 1)
        self._city_citizen_layout = city_citizen_layout
        city_citizen_group.setLayout(city_citizen_layout)

        bias_group = QGroupBox("出生点信息区域")
        bias_layout = QVBoxLayout()
        bias_layout.addWidget(self._terrain_bias)
        bias_layout.addWidget(self._feature_bias)
        bias_layout.addWidget(self._resource_bias)

        river_row = QHBoxLayout()
        river_row.addWidget(self._river_enabled)
        river_row.addWidget(QLabel("绑定等级"))
        river_row.addWidget(self._river_tier_spin)
        river_row.addStretch(1)
        bias_layout.addLayout(river_row)
        bias_group.setLayout(bias_layout)

        content_layout.addWidget(base_group)
        content_layout.addWidget(bias_group)
        content_layout.addWidget(city_citizen_group)
        content_layout.addStretch(1)
        content.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)
        self.setLayout(root_layout)
        self._apply_responsive_city_citizen_layout()
        QTimer.singleShot(0, self._sync_top_column_balance)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_city_citizen_layout()
        self._sync_top_column_balance()

    def _sync_top_column_balance(self) -> None:
        if self._top_left_panel is None or self._top_icon_panel is None:
            return
        left_height = self._top_left_panel.sizeHint().height()
        available = left_height - self._icon_name.sizeHint().height() - self._icon_image.non_canvas_height_hint() - 10
        target = max(120, min(220, available))
        self._icon_image.set_preview_max_height(target)

    def _apply_responsive_city_citizen_layout(self) -> None:
        layout = self._city_citizen_layout
        city_panel = self._city_panel
        citizen_panel = self._citizen_panel
        if layout is None or city_panel is None or citizen_panel is None:
            return

        compact = self.width() < 1180
        if compact == self._is_compact_city_layout:
            return

        layout.removeWidget(city_panel)
        layout.removeWidget(citizen_panel)
        if compact:
            layout.addWidget(city_panel, 0, 0)
            layout.addWidget(citizen_panel, 1, 0)
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 0)
        else:
            layout.addWidget(city_panel, 0, 0)
            layout.addWidget(citizen_panel, 0, 1)
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)

        self._is_compact_city_layout = compact

    def _build_mode_panel(self, title: str, mode_combo: QComboBox, stack: QStackedWidget) -> QWidget:
        panel = QGroupBox(title)
        layout = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(QLabel("模式"))
        top.addWidget(mode_combo)
        top.addStretch(1)
        layout.addLayout(top)
        layout.addWidget(stack)
        panel.setLayout(layout)
        return panel

    def _build_existing_city_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("选择文明"))
        self._city_existing_civ_combo = QComboBox()
        self._city_existing_map: dict[str, str] = {}
        civs = _fetch_major_civilizations()
        items: list[str] = []
        for civ_type, civ_name in civs:
            display = f"{civ_type} - {civ_name}"
            items.append(display)
            self._city_existing_map[display] = civ_type
        self._city_existing_civ_combo.addItems(items if items else ["请先配置数据库路径"])
        row.addWidget(self._city_existing_civ_combo, 1)
        layout.addLayout(row)
        self._city_existing_table = _CityNamesTable()
        self._city_existing_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._city_existing_table)
        widget.setLayout(layout)
        return widget

    def _build_custom_city_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = QHBoxLayout()
        row.addWidget(QLabel("城市数量"))
        self._city_custom_count = QSpinBox()
        self._city_custom_count.setRange(1, 100)
        self._city_custom_count.setValue(25)
        row.addWidget(self._city_custom_count)
        self._city_custom_expanded = False
        self._city_custom_toggle = QPushButton("展开")
        _apply_small_button(self._city_custom_toggle)
        row.addWidget(self._city_custom_toggle)
        row.addStretch(1)
        layout.addLayout(row)
        self._city_custom_table = _CityNamesTable()
        self._city_custom_table.set_count(25)
        self._city_custom_table_container = QWidget()
        c_layout = QVBoxLayout()
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.addWidget(self._city_custom_table)
        self._city_custom_table_container.setLayout(c_layout)
        self._city_custom_table_container.setVisible(False)
        layout.addWidget(self._city_custom_table_container)
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget

    def _build_random_city_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("城市数量"))
        self._city_random_count = QSpinBox()
        self._city_random_count.setRange(1, 200)
        self._city_random_count.setValue(25)
        row.addWidget(self._city_random_count)
        self._city_random_btn = QPushButton("开始随机")
        _apply_small_button(self._city_random_btn)
        row.addWidget(self._city_random_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self._city_random_table = _CityNamesTable()
        layout.addWidget(self._city_random_table)
        widget.setLayout(layout)
        return widget

    def _build_existing_citizen_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("选择文明"))
        self._citizen_existing_civ_combo = QComboBox()
        self._citizen_existing_map: dict[str, str] = {}
        civs = _fetch_major_civilizations()
        items: list[str] = []
        for civ_type, civ_name in civs:
            display = f"{civ_type} - {civ_name}"
            items.append(display)
            self._citizen_existing_map[display] = civ_type
        self._citizen_existing_civ_combo.addItems(items if items else ["请先配置数据库路径"])
        row.addWidget(self._citizen_existing_civ_combo, 1)
        layout.addLayout(row)
        self._citizen_existing_table = _CitizenTable()
        self._citizen_existing_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._citizen_existing_table)
        widget.setLayout(layout)
        return widget

    def _build_custom_citizen_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = QHBoxLayout()
        row.addWidget(QLabel("市民数量"))
        self._citizen_custom_count = QSpinBox()
        self._citizen_custom_count.setRange(1, 200)
        self._citizen_custom_count.setValue(25)
        row.addWidget(self._citizen_custom_count)
        self._citizen_custom_expanded = False
        self._citizen_custom_toggle = QPushButton("展开")
        _apply_small_button(self._citizen_custom_toggle)
        row.addWidget(self._citizen_custom_toggle)
        row.addStretch(1)
        layout.addLayout(row)
        self._citizen_custom_table = _CitizenTable()
        self._citizen_custom_table.set_count(25)
        self._citizen_custom_table_container = QWidget()
        c_layout = QVBoxLayout()
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.addWidget(self._citizen_custom_table)
        self._citizen_custom_table_container.setLayout(c_layout)
        self._citizen_custom_table_container.setVisible(False)
        layout.addWidget(self._citizen_custom_table_container)
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget

    def _build_random_citizen_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("市民数量"))
        self._citizen_random_count = QSpinBox()
        self._citizen_random_count.setRange(1, 200)
        self._citizen_random_count.setValue(25)
        row.addWidget(self._citizen_random_count)
        self._citizen_random_btn = QPushButton("开始随机")
        _apply_small_button(self._citizen_random_btn)
        row.addWidget(self._citizen_random_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self._citizen_random_table = _CitizenTable()
        layout.addWidget(self._citizen_random_table)
        widget.setLayout(layout)
        return widget

    def _bind_events(self) -> None:
        self._abbr_edit.textChanged.connect(self._handle_abbr_changed)
        self._name_edit.textChanged.connect(self._handle_name_changed)
        self._desc_edit.textChanged.connect(self._mark_desc_manual)
        self._adj_edit.textChanged.connect(self._mark_adj_manual)
        self._desc_suffix_combo.currentTextChanged.connect(self._handle_suffix_changed)

        for widget in (
            self._level_combo,
            self._ethnicity_combo,
            self._city_depth_spin,
            self._trait_name_edit,
            self._trait_desc_edit,
            self._river_enabled,
            self._river_tier_spin,
            self._city_custom_count,
            self._city_random_count,
            self._citizen_custom_count,
            self._citizen_random_count,
        ):
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._emit_data_changed)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(lambda _v: self._emit_data_changed())
            elif hasattr(widget, "stateChanged"):
                widget.stateChanged.connect(lambda _v: self._emit_data_changed())
            elif hasattr(widget, "currentIndexChanged"):
                widget.currentIndexChanged.connect(lambda _v: self._emit_data_changed())

        self._city_mode_combo.currentIndexChanged.connect(self._city_mode_stack.setCurrentIndex)
        self._city_mode_combo.currentIndexChanged.connect(lambda _v: self._emit_data_changed())
        self._citizen_mode_combo.currentIndexChanged.connect(self._citizen_mode_stack.setCurrentIndex)
        self._citizen_mode_combo.currentIndexChanged.connect(lambda _v: self._emit_data_changed())

        self._city_custom_count.valueChanged.connect(self._sync_city_custom_count)
        self._citizen_custom_count.valueChanged.connect(self._sync_citizen_custom_count)

        self._city_custom_toggle.clicked.connect(self._toggle_city_custom_table)
        self._citizen_custom_toggle.clicked.connect(self._toggle_citizen_custom_table)

        self._city_random_btn.clicked.connect(self._randomize_city_names)
        self._citizen_random_btn.clicked.connect(self._randomize_citizen_names)
        self._city_existing_civ_combo.currentTextChanged.connect(self._on_city_existing_selected)
        self._citizen_existing_civ_combo.currentTextChanged.connect(self._on_citizen_existing_selected)

        self._city_existing_table.itemChanged.connect(lambda _item: self._emit_data_changed())
        self._city_custom_table.itemChanged.connect(lambda _item: self._emit_data_changed())
        self._city_random_table.itemChanged.connect(lambda _item: self._emit_data_changed())
        self._citizen_existing_table.itemChanged.connect(lambda _item: self._emit_data_changed())
        self._citizen_custom_table.itemChanged.connect(lambda _item: self._emit_data_changed())
        self._citizen_random_table.itemChanged.connect(lambda _item: self._emit_data_changed())

        self._trait_bindings.dataChanged.connect(self._emit_data_changed)
        self._terrain_bias.dataChanged.connect(self._emit_data_changed)
        self._feature_bias.dataChanged.connect(self._emit_data_changed)
        self._resource_bias.dataChanged.connect(self._emit_data_changed)
        self._icon_image.dataChanged.connect(self._emit_data_changed)

        self._sync_city_custom_count(self._city_custom_count.value())
        self._sync_citizen_custom_count(self._citizen_custom_count.value())
        self._on_city_existing_selected(self._city_existing_civ_combo.currentText())
        self._on_citizen_existing_selected(self._citizen_existing_civ_combo.currentText())

    def _toggle_city_custom_table(self) -> None:
        self._city_custom_expanded = not self._city_custom_expanded
        self._city_custom_table_container.setVisible(self._city_custom_expanded)
        self._city_custom_toggle.setText("折叠" if self._city_custom_expanded else "展开")
        self._emit_data_changed()

    def _toggle_citizen_custom_table(self) -> None:
        self._citizen_custom_expanded = not self._citizen_custom_expanded
        self._citizen_custom_table_container.setVisible(self._citizen_custom_expanded)
        self._citizen_custom_toggle.setText("折叠" if self._citizen_custom_expanded else "展开")
        self._emit_data_changed()

    def _sync_city_custom_count(self, value: int) -> None:
        self._city_custom_table.set_count(max(1, int(value)))

    def _sync_citizen_custom_count(self, value: int) -> None:
        self._citizen_custom_table.set_count(max(1, int(value)))

    def _on_city_existing_selected(self, key: str) -> None:
        civ_type = self._city_existing_map.get(key)
        if not civ_type:
            return
        names = _fetch_city_names_for_civ(civ_type)
        if not names:
            names = ["该文明没有城市名字数据"]

        self._city_existing_table.blockSignals(True)
        self._city_existing_table.set_names(names, min_rows=max(1, len(names)))
        self._city_existing_table.blockSignals(False)
        self._emit_data_changed()

    def _on_citizen_existing_selected(self, key: str) -> None:
        civ_type = self._citizen_existing_map.get(key)
        if not civ_type:
            return
        rows = _fetch_citizens_for_civ(civ_type)

        self._citizen_existing_table.blockSignals(True)
        self._citizen_existing_table.set_rows(rows, min_rows=max(1, len(rows) if rows else 1))
        self._citizen_existing_table.blockSignals(False)
        self._emit_data_changed()

    def _randomize_city_names(self) -> None:
        pool = [name for name in _fetch_random_city_pool_zh() if _safe_text(name) and _safe_text(name) != "未知"]
        if not pool:
            QMessageBox.information(self, "提示", "未找到城市名字数据")
            return
        count = max(1, min(int(self._city_random_count.value()), len(pool)))
        selected = random.sample(pool, count)

        self._city_random_table.blockSignals(True)
        self._city_random_table.set_names(selected, min_rows=count)
        self._city_random_table.blockSignals(False)
        self._emit_data_changed()

    def _randomize_citizen_names(self) -> None:
        pool = [row for row in _fetch_random_citizen_pool_zh() if _safe_text(row[0]) and _safe_text(row[0]) != "未知"]
        if not pool:
            QMessageBox.information(self, "提示", "未找到有中文文本的市民名字")
            return
        count = max(1, min(int(self._citizen_random_count.value()), len(pool)))
        selected = random.sample(pool, count)

        self._citizen_random_table.blockSignals(True)
        self._citizen_random_table.set_rows(selected, min_rows=count)
        self._citizen_random_table.blockSignals(False)
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._internal_updating = True
        self._entry_name_fallback = fallback_name
        self._desc_manual = False
        self._adj_manual = False

        self._abbr_edit.setText(_safe_text(entry.get("abbr")))
        if "civilization_name" in entry:
            self._name_edit.setText(_safe_text(entry.get("civilization_name")))
        else:
            self._name_edit.setText(fallback_name)
        self._desc_edit.setText(_safe_text(entry.get("civilization_description")))
        self._adj_edit.setText(_safe_text(entry.get("civilization_adjective")))

        suffix = _safe_text(entry.get("description_suffix")) or "帝国"
        if self._desc_suffix_combo.findText(suffix) >= 0:
            self._desc_suffix_combo.setCurrentText(suffix)

        self._select_combo_data(self._level_combo, _safe_text(entry.get("level")) or "CIVILIZATION_LEVEL_FULL_CIV")
        self._select_combo_data(self._ethnicity_combo, _safe_text(entry.get("ethnicity")) or "ETHNICITY_ASIAN")

        self._city_depth_spin.setValue(max(1, min(100, int(entry.get("city_name_depth", 10) or 10))))
        self._trait_name_edit.setText(_safe_text(entry.get("trait_name")))
        self._trait_desc_edit.import_tokenized_text(entry.get("trait_description"))
        self._trait_bindings.set_values(list(entry.get("trait_bindings", [])) if isinstance(entry.get("trait_bindings"), list) else [])
        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        self._icon_image.set_state(images.get("icon"))

        city = entry.get("city_info") if isinstance(entry.get("city_info"), dict) else {}
        citizen = entry.get("citizen_info") if isinstance(entry.get("citizen_info"), dict) else {}

        self._city_mode_combo.setCurrentIndex(int(city.get("mode_index", 0) or 0))
        self._city_custom_count.setValue(max(1, min(100, int(city.get("custom_count", 25) or 25))))
        city_custom_entries = [str(item) for item in city.get("custom_entries", [])] if isinstance(city.get("custom_entries"), list) else []
        if not city_custom_entries and _safe_text(city.get("custom_text")):
            city_custom_entries = str(city.get("custom_text", "")).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self._city_custom_table.set_names(
            city_custom_entries,
            min_rows=int(self._city_custom_count.value()),
        )
        self._city_random_count.setValue(max(1, min(200, int(city.get("random_count", 25) or 25))))
        city_random_entries = [str(item) for item in city.get("random_entries", [])] if isinstance(city.get("random_entries"), list) else []
        if not city_random_entries and _safe_text(city.get("random_text")):
            city_random_entries = str(city.get("random_text", "")).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self._city_random_table.set_names(
            city_random_entries,
            min_rows=max(1, int(self._city_random_count.value())),
        )
        city_expanded = bool(city.get("custom_expanded", False))
        self._city_custom_expanded = city_expanded
        self._city_custom_table_container.setVisible(city_expanded)
        self._city_custom_toggle.setText("折叠" if city_expanded else "展开")

        self._citizen_mode_combo.setCurrentIndex(int(citizen.get("mode_index", 0) or 0))
        self._citizen_custom_count.setValue(max(1, min(200, int(citizen.get("custom_count", 25) or 25))))
        citizen_custom_rows = []
        if isinstance(citizen.get("custom_entries"), list):
            for item in citizen.get("custom_entries", []):
                if isinstance(item, dict):
                    citizen_custom_rows.append((
                        _safe_text(item.get("name")),
                        bool(item.get("female", False)),
                        bool(item.get("modern", False)),
                    ))
        if not citizen_custom_rows and _safe_text(citizen.get("custom_text")):
            raw_lines = str(citizen.get("custom_text", "")).replace("\r\n", "\n").replace("\r", "\n").split("\n")
            citizen_custom_rows = [(line, False, False) for line in raw_lines]
        self._citizen_custom_table.set_rows(citizen_custom_rows, min_rows=int(self._citizen_custom_count.value()))
        self._citizen_random_count.setValue(max(1, min(200, int(citizen.get("random_count", 25) or 25))))
        citizen_random_rows = []
        if isinstance(citizen.get("random_entries"), list):
            for item in citizen.get("random_entries", []):
                if isinstance(item, dict):
                    citizen_random_rows.append((
                        _safe_text(item.get("name")),
                        bool(item.get("female", False)),
                        bool(item.get("modern", False)),
                    ))
        if not citizen_random_rows and _safe_text(citizen.get("random_text")):
            raw_lines = str(citizen.get("random_text", "")).replace("\r\n", "\n").replace("\r", "\n").split("\n")
            citizen_random_rows = [(line, False, False) for line in raw_lines]
        self._citizen_random_table.set_rows(citizen_random_rows, min_rows=max(1, int(self._citizen_random_count.value())))
        citizen_expanded = bool(citizen.get("custom_expanded", False))
        self._citizen_custom_expanded = citizen_expanded
        self._citizen_custom_table_container.setVisible(citizen_expanded)
        self._citizen_custom_toggle.setText("折叠" if citizen_expanded else "展开")

        bias = entry.get("start_bias") if isinstance(entry.get("start_bias"), dict) else {}
        self._terrain_bias.set_payload(list(bias.get("terrains", [])) if isinstance(bias.get("terrains"), list) else [])
        self._feature_bias.set_payload(list(bias.get("features", [])) if isinstance(bias.get("features"), list) else [])
        self._resource_bias.set_payload(list(bias.get("resources", [])) if isinstance(bias.get("resources"), list) else [])
        self._river_enabled.setChecked(bool(bias.get("river_enabled", False)))
        self._river_tier_spin.setValue(max(1, min(5, int(bias.get("river_tier", 1) or 1))))

        city_existing_selection = _safe_text(city.get("existing_selection"))
        if city_existing_selection and self._city_existing_civ_combo.findText(city_existing_selection) >= 0:
            self._city_existing_civ_combo.setCurrentText(city_existing_selection)
        else:
            self._on_city_existing_selected(self._city_existing_civ_combo.currentText())

        citizen_existing_selection = _safe_text(citizen.get("existing_selection"))
        if citizen_existing_selection and self._citizen_existing_civ_combo.findText(citizen_existing_selection) >= 0:
            self._citizen_existing_civ_combo.setCurrentText(citizen_existing_selection)
        else:
            self._on_citizen_existing_selected(self._citizen_existing_civ_combo.currentText())

        self._refresh_type_and_loc_hints()
        self._internal_updating = False

    def export_entry(self) -> dict[str, object]:
        civ_name = _safe_text(self._name_edit.text())
        display_name = civ_name or self._entry_name_fallback
        return {
            "name": display_name,
            "abbr": _safe_text(self._abbr_edit.text()),
            "type": self._current_type_text(),
            "civilization_name": civ_name,
            "civilization_description": _safe_text(self._desc_edit.text()),
            "civilization_adjective": _safe_text(self._adj_edit.text()),
            "description_suffix": _safe_text(self._desc_suffix_combo.currentText()) or "帝国",
            "loc_name": self._name_loc_label.text(),
            "loc_description": self._desc_loc_label.text(),
            "loc_adjective": self._adj_loc_label.text(),
            "level": _safe_text(self._level_combo.currentData()),
            "ethnicity": _safe_text(self._ethnicity_combo.currentData()),
            "city_name_depth": int(self._city_depth_spin.value()),
            "trait_name": _safe_text(self._trait_name_edit.text()),
            "trait_description": self._trait_desc_edit.export_tokenized_text(),
            "trait_bindings": self._trait_bindings.values(),
            "icon_image_name": _safe_text(self._icon_name.text()),
            "images": {
                "icon": self._icon_image.export_state(),
            },
            "city_info": {
                "mode_index": int(self._city_mode_combo.currentIndex()),
                "existing_selection": _safe_text(self._city_existing_civ_combo.currentText()),
                "existing_entries": self._city_existing_table.names(),
                "custom_count": int(self._city_custom_count.value()),
                "custom_entries": self._city_custom_table.names(),
                "custom_expanded": bool(self._city_custom_expanded),
                "random_count": int(self._city_random_count.value()),
                "random_entries": self._city_random_table.names(),
            },
            "citizen_info": {
                "mode_index": int(self._citizen_mode_combo.currentIndex()),
                "existing_selection": _safe_text(self._citizen_existing_civ_combo.currentText()),
                "existing_entries": [
                    {"name": name, "female": female, "modern": modern}
                    for name, female, modern in self._citizen_existing_table.rows_payload()
                ],
                "custom_count": int(self._citizen_custom_count.value()),
                "custom_entries": [
                    {"name": name, "female": female, "modern": modern}
                    for name, female, modern in self._citizen_custom_table.rows_payload()
                ],
                "custom_expanded": bool(self._citizen_custom_expanded),
                "random_count": int(self._citizen_random_count.value()),
                "random_entries": [
                    {"name": name, "female": female, "modern": modern}
                    for name, female, modern in self._citizen_random_table.rows_payload()
                ],
            },
            "start_bias": {
                "terrains": self._terrain_bias.export_payload(),
                "features": self._feature_bias.export_payload(),
                "resources": self._resource_bias.export_payload(),
                "river_enabled": bool(self._river_enabled.isChecked()),
                "river_tier": int(self._river_tier_spin.value()),
            },
        }

    def _select_combo_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        if idx < 0:
            idx = 0
        combo.setCurrentIndex(idx)

    def _current_type_text(self) -> str:
        shared = self._shared_params_provider()
        return _build_entity_type(shared, head="CIVILIZATION", midfix_code="C", short_name=self._abbr_edit.text())

    def _refresh_type_and_loc_hints(self) -> None:
        type_text = self._current_type_text()
        self._type_label.setText(type_text)
        self._icon_name.setText(f"ICON_{type_text}" if type_text else "")
        self._name_loc_label.setText(f"LOC_{type_text}_NAME")
        self._desc_loc_label.setText(f"LOC_{type_text}_DESCRIPTION")
        self._adj_loc_label.setText(f"LOC_{type_text}_ADJECTIVE")

    def _handle_abbr_changed(self, text: str) -> None:
        cleaned = re.sub(r"[^A-Za-z0-9_]", "", text)
        if cleaned != text:
            cursor = self._abbr_edit.cursorPosition()
            self._abbr_edit.blockSignals(True)
            self._abbr_edit.setText(cleaned)
            self._abbr_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._abbr_edit.blockSignals(False)
        self._refresh_type_and_loc_hints()
        self._emit_data_changed()

    def _handle_name_changed(self, name: str) -> None:
        self._auto_filling_name_fields = True
        try:
            if not self._desc_manual:
                target_desc = f"{name}{self._desc_suffix_combo.currentText()}" if name else ""
                if self._desc_edit.text() != target_desc:
                    self._desc_edit.setText(target_desc)
            if not self._adj_manual:
                target_adj = f"{name}的" if name else ""
                if self._adj_edit.text() != target_adj:
                    self._adj_edit.setText(target_adj)
        finally:
            self._auto_filling_name_fields = False
        self._emit_data_changed()

    def _mark_desc_manual(self, _text: str) -> None:
        if self._internal_updating or self._auto_filling_name_fields:
            return
        if not self._internal_updating:
            self._desc_manual = True
        self._emit_data_changed()

    def _mark_adj_manual(self, _text: str) -> None:
        if self._internal_updating or self._auto_filling_name_fields:
            return
        if not self._internal_updating:
            self._adj_manual = True
        self._emit_data_changed()

    def _handle_suffix_changed(self, _value: str) -> None:
        if not self._desc_manual:
            name = _safe_text(self._name_edit.text())
            target_desc = f"{name}{self._desc_suffix_combo.currentText()}" if name else ""
            self._auto_filling_name_fields = True
            try:
                if self._desc_edit.text() != target_desc:
                    self._desc_edit.setText(target_desc)
            finally:
                self._auto_filling_name_fields = False
        self._emit_data_changed()

    def _emit_data_changed(self) -> None:
        if self._internal_updating:
            return
        self._refresh_type_and_loc_hints()
        self.dataChanged.emit()


class _ImageAdjustCanvas(QWidget):
    pathSelected = pyqtSignal(str)
    viewChanged = pyqtSignal()

    def __init__(self, target_size: tuple[int, int]) -> None:
        super().__init__()
        self._target_width = max(1, int(target_size[0]))
        self._target_height = max(1, int(target_size[1]))
        self._preview_max_width = 320
        self._preview_max_height = 240
        self._path = ""
        self._pixmap = QPixmap()
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._dragging = False
        self._drag_start = None
        self._circle_preview = False

        self.setAcceptDrops(True)
        self._apply_preview_size()

    def set_preview_limits(self, *, max_width: int | None = None, max_height: int | None = None) -> None:
        if max_width is not None:
            self._preview_max_width = max(120, int(max_width))
        if max_height is not None:
            self._preview_max_height = max(96, int(max_height))
        self._apply_preview_size()
        if not self._pixmap.isNull():
            self._clamp_offset()
        self.update()

    def set_circle_preview(self, enabled: bool) -> None:
        self._circle_preview = bool(enabled)
        self.update()

    @staticmethod
    def _circle_inset_for_target(*, target_w: int, target_h: int) -> float:
        target_min = float(max(1, min(int(target_w), int(target_h))))
        return float(round(target_min * 10.0 / 256.0))

    @staticmethod
    def _circle_border_for_target(*, target_w: int, target_h: int) -> float:
        target_min = float(max(1, min(int(target_w), int(target_h))))
        return float(max(1.0, round(target_min * 3.0 / 256.0)))

    def _compute_preview_size(self) -> tuple[int, int]:
        ratio = self._target_width / self._target_height
        max_w = self._preview_max_width
        max_h = self._preview_max_height
        if ratio >= 1.0:
            width = max_w
            height = max(96, int(round(width / ratio)))
            if height > max_h:
                height = max_h
                width = max(96, int(round(height * ratio)))
        else:
            height = max_h
            width = max(96, int(round(height * ratio)))
            if width > max_w:
                width = max_w
                height = max(96, int(round(width / ratio)))
        return width, height

    def _apply_preview_size(self) -> None:
        preview_w, preview_h = self._compute_preview_size()
        self.setMinimumSize(preview_w, preview_h)
        self.setMaximumSize(preview_w, preview_h)

    def path(self) -> str:
        return self._path

    def set_image_path(self, value: str, *, scale: float | None = None, offset_x: float | None = None, offset_y: float | None = None) -> None:
        self._path = _safe_text(value)
        self._pixmap = QPixmap(self._path) if self._path and Path(self._path).exists() else QPixmap()
        if self._pixmap.isNull():
            self._scale = 1.0
            self._offset_x = 0.0
            self._offset_y = 0.0
            self.update()
            self.viewChanged.emit()
            return

        fit_scale = self._minimum_scale()
        if scale is not None:
            try:
                self._scale = max(fit_scale, float(scale))
            except (TypeError, ValueError):
                self._scale = fit_scale
        else:
            self._scale = fit_scale
        self._offset_x = float(offset_x) if offset_x is not None else 0.0
        self._offset_y = float(offset_y) if offset_y is not None else 0.0
        self._clamp_offset()
        self.update()
        self.viewChanged.emit()

    def export_state(self) -> dict[str, object]:
        if not self._path:
            return {}
        preview_w, preview_h = self._compute_preview_size()
        return {
            "path": self._path,
            "scale": float(self._scale),
            "offset_x": float(self._offset_x),
            "offset_y": float(self._offset_y),
            "target_width": int(self._target_width),
            "target_height": int(self._target_height),
            "preview_max_width": int(self._preview_max_width),
            "preview_max_height": int(self._preview_max_height),
            "canvas_width": int(preview_w),
            "canvas_height": int(preview_h),
        }

    def render_view_image(self, *, target_size: tuple[int, int] | None = None, circle_crop: bool = False) -> QImage | None:
        if self._pixmap.isNull():
            return None

        target_w = self._target_width
        target_h = self._target_height
        if target_size is not None:
            target_w = max(1, int(target_size[0]))
            target_h = max(1, int(target_size[1]))

        canvas_w = max(1, self.width())
        canvas_h = max(1, self.height())
        scale_x = target_w / canvas_w
        scale_y = target_h / canvas_h

        image = QImage(target_w, target_h, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if circle_crop:
            inset = self._circle_inset_for_target(target_w=target_w, target_h=target_h)
            radius = max(1.0, min(float(target_w), float(target_h)) / 2.0 - inset)
            center_x = float(target_w) / 2.0
            center_y = float(target_h) / 2.0
            path = QPainterPath()
            path.addEllipse(center_x - radius, center_y - radius, radius * 2.0, radius * 2.0)
            painter.setClipPath(path)

        draw_x = self._offset_x * scale_x
        draw_y = self._offset_y * scale_y
        draw_w = self._pixmap.width() * self._scale * scale_x
        draw_h = self._pixmap.height() * self._scale * scale_y
        painter.drawPixmap(int(round(draw_x)), int(round(draw_y)), int(round(draw_w)), int(round(draw_h)), self._pixmap)
        painter.end()
        return image

    def reset_view(self) -> None:
        if self._pixmap.isNull():
            return
        self._scale = self._minimum_scale()
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._clamp_offset()
        self.update()
        self.viewChanged.emit()

    def zoom_by(self, factor: float) -> None:
        if self._pixmap.isNull():
            return
        old_scale = self._scale
        min_scale = self._minimum_scale()
        max_scale = 64.0
        new_scale = max(min_scale, min(old_scale * factor, max_scale))
        if abs(new_scale - old_scale) < 1e-6:
            return
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        source_x = (cx - self._offset_x) / old_scale
        source_y = (cy - self._offset_y) / old_scale
        self._scale = new_scale
        self._offset_x = cx - source_x * new_scale
        self._offset_y = cy - source_y * new_scale
        self._clamp_offset()
        self.update()
        self.viewChanged.emit()

    def _minimum_scale(self) -> float:
        if self._pixmap.isNull() or self._pixmap.width() <= 0 or self._pixmap.height() <= 0:
            return 1.0
        return max(self.width() / self._pixmap.width(), self.height() / self._pixmap.height())

    def _clamp_offset(self) -> None:
        if self._pixmap.isNull():
            self._offset_x = 0.0
            self._offset_y = 0.0
            return
        scaled_w = self._pixmap.width() * self._scale
        scaled_h = self._pixmap.height() * self._scale
        min_x = -scaled_w + 20.0
        max_x = self.width() - 20.0
        min_y = -scaled_h + 20.0
        max_y = self.height() - 20.0
        if min_x > max_x:
            min_x, max_x = max_x, min_x
        if min_y > max_y:
            min_y, max_y = max_y, min_y
        self._offset_x = min(max_x, max(min_x, self._offset_x))
        self._offset_y = min(max_y, max(min_y, self._offset_y))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        painter.setPen(QColor("#94a3b8"))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self._pixmap.isNull():
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "拖入图片或点击“选择”")
        else:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            draw_w = int(round(self._pixmap.width() * self._scale))
            draw_h = int(round(self._pixmap.height() * self._scale))
            painter.drawPixmap(int(round(self._offset_x)), int(round(self._offset_y)), draw_w, draw_h, self._pixmap)

        if self._circle_preview:
            canvas_min = float(max(1, min(self.width(), self.height())))
            target_min = float(max(1, min(self._target_width, self._target_height)))
            inset_target = self._circle_inset_for_target(target_w=self._target_width, target_h=self._target_height)
            inset_canvas = inset_target * (canvas_min / target_min)
            radius = max(1.0, canvas_min / 2.0 - inset_canvas)
            cx = float(self.width()) / 2.0
            cy = float(self.height()) / 2.0
            outer = QPainterPath()
            outer.addRect(0.0, 0.0, float(self.width()), float(self.height()))
            inner = QPainterPath()
            inner.addEllipse(cx - radius, cy - radius, radius * 2.0, radius * 2.0)
            mask = outer.subtracted(inner)
            painter.fillPath(mask, QColor(15, 23, 42, 140))
            painter.setPen(QColor("#f8fafc"))
            painter.drawEllipse(int(round(cx - radius)), int(round(cy - radius)), int(round(radius * 2.0)), int(round(radius * 2.0)))

        painter.setPen(QColor("#334155"))
        painter.drawText(
            self.rect().adjusted(6, 6, -6, -6),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            f"{self._target_width}x{self._target_height}",
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._pixmap.isNull():
            self._dragging = True
            self._drag_start = event.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_start is not None:
            delta = event.pos() - self._drag_start
            self._drag_start = event.pos()
            self._offset_x += float(delta.x())
            self._offset_y += float(delta.y())
            self._clamp_offset()
            self.update()
            self.viewChanged.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_start = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        if self._pixmap.isNull():
            event.ignore()
            return
        if event.angleDelta().y() > 0:
            self.zoom_by(1.1)
        elif event.angleDelta().y() < 0:
            self.zoom_by(1 / 1.1)
        event.accept()

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            for url in mime.urls():
                local = url.toLocalFile()
                if local:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            event.ignore()
            return
        for url in mime.urls():
            local = url.toLocalFile()
            if local:
                self.pathSelected.emit(local)
                event.acceptProposedAction()
                return
        event.ignore()


class _ImageSlotWidget(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, target_size: tuple[int, int], *, enable_circle_crop: bool = False) -> None:
        super().__init__()
        self._target_size = target_size
        self._enable_circle_crop = enable_circle_crop
        self._canvas = _ImageAdjustCanvas(target_size)
        self._canvas.pathSelected.connect(self.set_image_path)
        self._canvas.viewChanged.connect(self._emit_data_changed)

        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)

        self._choose_button = QPushButton("选择")
        self._clear_button = QPushButton("清除")
        self._reset_button = QPushButton("重置")
        self._zoom_out_button = QPushButton("-")
        self._zoom_in_button = QPushButton("+")
        self._circle_preview_button = QPushButton("圆形预览") if self._enable_circle_crop else None
        self._black_border_check = QCheckBox("添加黑边") if self._enable_circle_crop else None
        for button in (
            self._choose_button,
            self._clear_button,
            self._reset_button,
            self._zoom_out_button,
            self._zoom_in_button,
            self._circle_preview_button,
        ):
            if button is None:
                continue
            _apply_small_button(button)

        self._choose_button.clicked.connect(self._choose_file)
        self._clear_button.clicked.connect(self._clear)
        self._reset_button.clicked.connect(self._canvas.reset_view)
        self._zoom_out_button.clicked.connect(lambda: self._canvas.zoom_by(1 / 1.1))
        self._zoom_in_button.clicked.connect(lambda: self._canvas.zoom_by(1.1))
        if self._circle_preview_button is not None:
            self._circle_preview_button.setCheckable(True)
            self._circle_preview_button.toggled.connect(self._toggle_circle_preview)
        if self._black_border_check is not None:
            self._black_border_check.toggled.connect(lambda _checked: self._emit_data_changed())

        self._top_info_label = QLabel(f"输出尺寸：{target_size[0]} x {target_size[1]}")

        top_row = QHBoxLayout()
        top_row.addWidget(self._top_info_label)
        top_row.addStretch(1)

        self._controls_widget = QWidget()
        controls = QVBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(self._choose_button)

        zoom_row = QHBoxLayout()
        zoom_row.setContentsMargins(0, 0, 0, 0)
        zoom_row.addWidget(self._zoom_out_button)
        zoom_row.addWidget(self._zoom_in_button)
        controls.addLayout(zoom_row)

        controls.addWidget(self._reset_button)
        controls.addWidget(self._clear_button)
        if self._circle_preview_button is not None:
            controls.addWidget(self._circle_preview_button)
        if self._black_border_check is not None:
            controls.addWidget(self._black_border_check)
        controls.addStretch(1)
        self._controls_widget.setLayout(controls)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.addWidget(self._canvas, 1)
        body_row.addWidget(self._controls_widget, 0)

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(self._path_edit, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_row)
        layout.addLayout(body_row)
        layout.addLayout(path_row)
        self.setLayout(layout)

    def _emit_data_changed(self) -> None:
        self._path_edit.setText(self.image_path())
        self.dataChanged.emit()

    def _choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp *.gif)",
        )
        if file_path:
            self.set_image_path(file_path)

    def image_path(self) -> str:
        return self._canvas.path()

    def set_image_path(self, value: str) -> None:
        self._canvas.set_image_path(value)

    def set_state(self, payload: object) -> None:
        if isinstance(payload, dict):
            path = _safe_text(payload.get("path"))
            scale = payload.get("scale")
            offset_x = payload.get("offset_x")
            offset_y = payload.get("offset_y")
            try:
                scale_value = float(scale) if scale is not None else None
            except (TypeError, ValueError):
                scale_value = None
            try:
                offset_x_value = float(offset_x) if offset_x is not None else None
            except (TypeError, ValueError):
                offset_x_value = None
            try:
                offset_y_value = float(offset_y) if offset_y is not None else None
            except (TypeError, ValueError):
                offset_y_value = None
            self._canvas.set_image_path(path, scale=scale_value, offset_x=offset_x_value, offset_y=offset_y_value)

            if self._circle_preview_button is not None:
                circle_crop = bool(payload.get("circle_crop", False))
                self._circle_preview_button.blockSignals(True)
                self._circle_preview_button.setChecked(circle_crop)
                self._circle_preview_button.blockSignals(False)
                self._canvas.set_circle_preview(circle_crop)

            if self._black_border_check is not None:
                add_border = bool(payload.get("add_black_border", False))
                self._black_border_check.blockSignals(True)
                self._black_border_check.setChecked(add_border)
                self._black_border_check.blockSignals(False)
            return
        if self._circle_preview_button is not None:
            self._circle_preview_button.blockSignals(True)
            self._circle_preview_button.setChecked(False)
            self._circle_preview_button.blockSignals(False)
            self._canvas.set_circle_preview(False)
        if self._black_border_check is not None:
            self._black_border_check.blockSignals(True)
            self._black_border_check.setChecked(False)
            self._black_border_check.blockSignals(False)
        self._canvas.set_image_path(_safe_text(payload))

    def export_state(self) -> dict[str, object]:
        state = self._canvas.export_state()
        if not state:
            return {}
        if self._circle_preview_button is not None:
            state["circle_crop"] = bool(self._circle_preview_button.isChecked())
        if self._black_border_check is not None:
            state["add_black_border"] = bool(self._black_border_check.isChecked())
        return state

    def non_canvas_height_hint(self) -> int:
        return self._top_info_label.sizeHint().height() + self._path_edit.sizeHint().height() + 10

    def set_preview_max_height(self, max_height: int) -> None:
        self._canvas.set_preview_limits(max_height=max_height)

    def _clear(self) -> None:
        if self._circle_preview_button is not None:
            self._circle_preview_button.blockSignals(True)
            self._circle_preview_button.setChecked(False)
            self._circle_preview_button.blockSignals(False)
        if self._black_border_check is not None:
            self._black_border_check.blockSignals(True)
            self._black_border_check.setChecked(False)
            self._black_border_check.blockSignals(False)
        self._canvas.set_circle_preview(False)
        self._canvas.set_image_path("")

    def _toggle_circle_preview(self, checked: bool) -> None:
        self._canvas.set_circle_preview(bool(checked))
        self.dataChanged.emit()


class _LeaderCivilizationSelectionDialog(QDialog):
    def __init__(self, parent: QWidget, local_provider: Callable[[], list[dict[str, object]]]) -> None:
        super().__init__(parent)
        self._local_provider = local_provider
        self._entries: list[dict[str, object]] = []
        self._filtered: list[dict[str, object]] = []

        self.setWindowTitle("选择文明")
        self.resize(560, 420)

        layout = QVBoxLayout()
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("输入 Type 或名字过滤")
        self._search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search, 1)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Type", "名字"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(lambda _r, _c: self.accept())
        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._load_entries()
        self._apply_filter("")

    def _load_entries(self) -> None:
        entries: list[dict[str, object]] = []
        for local in self._local_provider():
            if not isinstance(local, dict):
                continue
            civ_type = _safe_text(local.get("type"))
            if not civ_type:
                continue
            civ_name = _safe_text(local.get("name")) or "未知"
            merged = dict(local)
            merged["type"] = civ_type
            merged["name"] = civ_name
            merged["source"] = "local"
            entries.append(merged)

        for civ_type, civ_name in _fetch_major_civilizations():
            entries.append({"type": _safe_text(civ_type), "name": _safe_text(civ_name) or "未知", "source": "db"})

        dedup: dict[str, dict[str, object]] = {}
        for entry in entries:
            key = _safe_text(entry.get("type"))
            if not key:
                continue
            if key not in dedup:
                dedup[key] = entry

        self._entries = list(dedup.values())
        self._entries.sort(
            key=lambda item: (
                0 if _safe_text(item.get("source")) == "local" else 1,
                0 if _safe_text(item.get("name")).startswith("新文明") else 1,
                _safe_text(item.get("name")) in {"", "未知"},
                _safe_text(item.get("name")),
                _safe_text(item.get("type")),
            )
        )

    def _apply_filter(self, text: str) -> None:
        needle = _safe_text(text).lower()
        if not needle:
            self._filtered = list(self._entries)
        else:
            self._filtered = [
                entry
                for entry in self._entries
                if needle in _safe_text(entry.get("type")).lower() or needle in _safe_text(entry.get("name")).lower()
            ]
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._filtered))
        for row, entry in enumerate(self._filtered):
            type_item = QTableWidgetItem(_safe_text(entry.get("type")))
            name_item = QTableWidgetItem(_safe_text(entry.get("name")))
            type_item.setData(Qt.ItemDataRole.UserRole, entry)
            if _safe_text(entry.get("source")) == "local":
                highlight = QColor(38, 130, 90)
                type_item.setForeground(highlight)
                name_item.setForeground(highlight)
            self._table.setItem(row, 0, type_item)
            self._table.setItem(row, 1, name_item)

    def selected_entry(self) -> dict[str, object] | None:
        selection = self._table.selectionModel()
        if selection is None:
            return None
        rows = selection.selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self._table.item(row, 0)
        if item is None:
            return None
        payload = item.data(Qt.ItemDataRole.UserRole)
        return dict(payload) if isinstance(payload, dict) else None


class LeaderItemEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(
        self,
        shared_params_provider: Callable[[], dict[str, object]],
        bindable_entries_provider: Callable[[str], list[dict[str, object]]],
        civilizations_provider: Callable[[], list[dict[str, str]]],
    ) -> None:
        super().__init__()
        self._shared_params_provider = shared_params_provider
        self._bindable_entries_provider = bindable_entries_provider
        self._civilizations_provider = civilizations_provider
        self._entry_name_fallback = "新领袖"
        self._internal_updating = False
        self._top_left_panel: QWidget | None = None
        self._top_icon_panel: QWidget | None = None

        self._abbr_edit = QLineEdit()
        self._abbr_edit.setPlaceholderText("仅英文/数字/下划线")
        self._type_label = QLabel("LEADER")
        self._type_label.setObjectName("pageInfoLabel")
        self._icon_name = QLineEdit()
        self._icon_name.setReadOnly(True)
        self._icon_image = _ImageSlotWidget((256, 256), enable_circle_crop=True)

        self._name_edit = QLineEdit()
        self._sex_group = QButtonGroup(self)
        self._male_radio = QCheckBox("男")
        self._female_radio = QCheckBox("女")
        self._sex_group.setExclusive(True)
        self._sex_group.addButton(self._male_radio)
        self._sex_group.addButton(self._female_radio)
        self._male_radio.setChecked(True)

        self._capital_edit = QLineEdit()

        self._civilization_edit = QLineEdit()
        self._civilization_choose_btn = QPushButton("选择")
        _apply_small_button(self._civilization_choose_btn)
        self._civilization_hint = QLabel("")
        self._civilization_hint.setObjectName("pageInfoLabel")

        self._leader_text_edit = IconTokenTextEdit()
        self._leader_text_edit.setPlaceholderText("输入时回车会写入 [NEWLINE]")
        self._leader_text_edit.setFixedHeight(96)
        self._quote_edit = QLineEdit()

        self._ability_name_edit = QLineEdit()
        self._ability_desc_edit = IconTokenTextEdit()
        self._ability_desc_edit.setPlaceholderText("输入时回车会写入 [NEWLINE]")
        self._ability_desc_edit.setFixedHeight(96)
        self._select_sort_index_spin = QSpinBox()
        self._select_sort_index_spin.setRange(0, 999999999)
        self._select_sort_index_spin.setValue(0)
        self._add_diplo_background_curtain_check = QCheckBox("是否新增外交背景幕布(BARBAROSSA_4)")

        self._foreground_name = QLineEdit()
        self._background_name = QLineEdit()
        self._diplo_foreground_name = QLineEdit()
        self._diplo_background_name = QLineEdit()
        self._select_foreground_name = QLineEdit()
        self._select_background_name = QLineEdit()
        for line_edit in (
            self._foreground_name,
            self._background_name,
            self._diplo_foreground_name,
            self._diplo_background_name,
            self._select_foreground_name,
            self._select_background_name,
        ):
            line_edit.setReadOnly(True)

        self._foreground_image = _ImageSlotWidget((960, 960))
        self._background_image = _ImageSlotWidget((1920, 960))
        self._diplo_foreground_image = _ImageSlotWidget((960, 960))
        self._diplo_background_image = _ImageSlotWidget((1960, 1600))
        self._select_foreground_image = _ImageSlotWidget((512, 1024))
        self._select_background_image = _ImageSlotWidget((384, 1024))

        self._bindings = _TraitBindingsEditor(
            self._bindable_entries_provider,
            extra_excluded_keys_provider=self._excluded_binding_keys_from_bound_civilization,
        )

        self._diplomacy_table = QTableWidget(len(LEADER_DIPLO_SCENES), 3)
        self._diplomacy_table.setHorizontalHeaderLabels(["场景", "文本", "Tag"])
        header = self._diplomacy_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._diplomacy_table.verticalHeader().setVisible(False)
        self._diplomacy_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self._diplomacy_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._build_layout()
        self._bind_events()
        self._refresh_type_and_related()

    def _build_layout(self) -> None:
        content = QWidget()
        content_layout = QVBoxLayout()

        basic_group = QGroupBox("领袖基础信息")
        basic_layout = QVBoxLayout()

        type_form = QFormLayout()
        type_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        type_form.addRow("领袖简称", self._abbr_edit)
        type_form.addRow("完整Type", self._type_label)
        type_form.addRow("领袖名字（中文）", self._name_edit)

        sex_row = QWidget()
        sex_layout = QHBoxLayout()
        sex_layout.setContentsMargins(0, 0, 0, 0)
        sex_layout.addWidget(self._male_radio)
        sex_layout.addWidget(self._female_radio)
        sex_layout.addStretch(1)
        sex_row.setLayout(sex_layout)

        detail_form = QFormLayout()
        detail_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        detail_form.addRow("性别", sex_row)
        detail_form.addRow("首都名字（中文）", self._capital_edit)

        bind_civ_row = QWidget()
        bind_civ_layout = QHBoxLayout()
        bind_civ_layout.setContentsMargins(0, 0, 0, 0)
        bind_civ_layout.addWidget(self._civilization_edit, 1)
        bind_civ_layout.addWidget(self._civilization_choose_btn)
        bind_civ_row.setLayout(bind_civ_layout)
        detail_form.addRow("绑定文明", bind_civ_row)
        detail_form.addRow("", self._civilization_hint)
        detail_form.addRow("加载文本（中文）", self._leader_text_edit)

        top_row = QHBoxLayout()
        top_left_panel = QWidget()
        top_left_layout = QVBoxLayout()
        top_left_layout.setContentsMargins(0, 0, 0, 0)
        top_left_layout.addLayout(type_form)
        top_left_layout.addLayout(detail_form)
        top_left_panel.setLayout(top_left_layout)
        self._top_left_panel = top_left_panel
        top_row.addWidget(top_left_panel, 1)

        icon_panel = QWidget()
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(self._icon_name)
        icon_layout.addWidget(self._icon_image)
        icon_panel.setLayout(icon_layout)
        self._top_icon_panel = icon_panel
        top_row.addWidget(icon_panel, 0)
        basic_layout.addLayout(top_row)

        post_text_form = QFormLayout()
        post_text_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        post_text_form.addRow("领袖名言（中文）", self._quote_edit)
        post_text_form.addRow("领袖能力名字（中文）", self._ability_name_edit)
        basic_layout.addLayout(post_text_form)

        ability_desc_form = QFormLayout()
        ability_desc_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        ability_desc_form.addRow("领袖能力描述（中文）", self._ability_desc_edit)
        basic_layout.addLayout(ability_desc_form)

        extra_row = QWidget()
        extra_row_layout = QHBoxLayout()
        extra_row_layout.setContentsMargins(0, 0, 0, 0)
        extra_row_layout.addWidget(QLabel("选择界面顺序"))
        extra_row_layout.addWidget(self._select_sort_index_spin)
        extra_row_layout.addSpacing(16)
        extra_row_layout.addWidget(self._add_diplo_background_curtain_check)
        extra_row_layout.addStretch(1)
        extra_row.setLayout(extra_row_layout)
        basic_layout.addWidget(extra_row)

        image_group = QGroupBox("加载/外交图片名字")
        image_layout = QGridLayout()

        image_layout.addWidget(QLabel("ForegroundImage"), 0, 0)
        image_layout.addWidget(self._foreground_name, 0, 1)
        image_layout.addWidget(QLabel("BackgroundImage"), 0, 2)
        image_layout.addWidget(self._background_name, 0, 3)
        image_layout.addWidget(self._foreground_image, 1, 0, 1, 2)
        image_layout.addWidget(self._background_image, 1, 2, 1, 2)

        image_layout.addWidget(QLabel("DiploForegroundImage"), 2, 0)
        image_layout.addWidget(self._diplo_foreground_name, 2, 1)
        image_layout.addWidget(QLabel("DiploBackgroundImage"), 2, 2)
        image_layout.addWidget(self._diplo_background_name, 2, 3)
        image_layout.addWidget(self._diplo_foreground_image, 3, 0, 1, 2)
        image_layout.addWidget(self._diplo_background_image, 3, 2, 1, 2)

        image_layout.addWidget(QLabel("选择界面前景图"), 4, 0)
        image_layout.addWidget(self._select_foreground_name, 4, 1)
        image_layout.addWidget(QLabel("选择界面背景图"), 4, 2)
        image_layout.addWidget(self._select_background_name, 4, 3)
        image_layout.addWidget(self._select_foreground_image, 5, 0, 1, 2)
        image_layout.addWidget(self._select_background_image, 5, 2, 1, 2)
        image_group.setLayout(image_layout)
        basic_layout.addWidget(image_group)
        basic_group.setLayout(basic_layout)

        binding_group = QGroupBox("领袖绑定区域")
        binding_layout = QVBoxLayout()
        binding_layout.addWidget(self._bindings)
        binding_group.setLayout(binding_layout)

        diplomacy_group = QGroupBox("领袖外交文本区域")
        diplomacy_layout = QVBoxLayout()
        diplomacy_layout.addWidget(self._diplomacy_table)
        diplomacy_group.setLayout(diplomacy_layout)

        content_layout.addWidget(basic_group)
        content_layout.addWidget(binding_group)
        content_layout.addWidget(diplomacy_group)
        content_layout.addStretch(1)
        content.setLayout(content_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)
        self.setLayout(root)

        for row, (scene_label, _template) in enumerate(LEADER_DIPLO_SCENES):
            scene_item = QTableWidgetItem(scene_label)
            scene_item.setFlags(scene_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            text_item = QTableWidgetItem("")
            tag_item = QTableWidgetItem("")
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._diplomacy_table.setItem(row, 0, scene_item)
            self._diplomacy_table.setItem(row, 1, text_item)
            self._diplomacy_table.setItem(row, 2, tag_item)
        self._sync_diplomacy_table_height()
        QTimer.singleShot(0, self._sync_top_column_balance)

    def _bind_events(self) -> None:
        self._abbr_edit.textChanged.connect(self._handle_abbr_changed)
        self._name_edit.textChanged.connect(lambda _v: self._emit_data_changed())
        self._male_radio.toggled.connect(lambda _v: self._emit_data_changed())
        self._female_radio.toggled.connect(lambda _v: self._emit_data_changed())
        self._capital_edit.textChanged.connect(lambda _v: self._emit_data_changed())
        self._civilization_edit.textChanged.connect(lambda _v: self._emit_data_changed())
        self._civilization_choose_btn.clicked.connect(self._open_civilization_dialog)
        self._leader_text_edit.textChanged.connect(self._emit_data_changed)
        self._quote_edit.textChanged.connect(lambda _v: self._emit_data_changed())
        self._ability_name_edit.textChanged.connect(lambda _v: self._emit_data_changed())
        self._ability_desc_edit.textChanged.connect(self._emit_data_changed)
        self._select_sort_index_spin.valueChanged.connect(lambda _v: self._emit_data_changed())
        self._add_diplo_background_curtain_check.toggled.connect(lambda _v: self._emit_data_changed())
        self._bindings.dataChanged.connect(self._emit_data_changed)
        self._diplomacy_table.itemChanged.connect(lambda _item: self._emit_data_changed())
        self._diplomacy_table.horizontalHeader().sectionResized.connect(lambda *_args: self._sync_diplomacy_table_height())

        for widget in (
            self._icon_image,
            self._foreground_image,
            self._background_image,
            self._diplo_foreground_image,
            self._diplo_background_image,
            self._select_foreground_image,
            self._select_background_image,
        ):
            widget.dataChanged.connect(self._emit_data_changed)

    def _leader_short_type(self) -> str:
        type_text = self._type_label.text().strip().upper()
        if type_text.startswith("LEADER_"):
            return type_text[len("LEADER_") :]
        return type_text

    def _refresh_type_and_related(self) -> None:
        shared = self._shared_params_provider()
        type_text = _build_entity_type(shared, head="LEADER", midfix_code="L", short_name=self._abbr_edit.text())
        self._type_label.setText(type_text)
        self._icon_name.setText(f"ICON_{type_text}" if type_text else "")

        short_type = self._leader_short_type()
        self._foreground_name.setText(f"{type_text}_NEUTRAL" if type_text else "")
        self._background_name.setText(f"{type_text}_BACKGROUND" if type_text else "")
        self._diplo_foreground_name.setText(f"FALLBACK_NEUTRAL_{short_type}" if short_type else "")
        self._diplo_background_name.setText(f"{short_type}_1,{short_type}_2,{short_type}_3" if short_type else "")
        self._select_foreground_name.setText(f"PORTRAIT_{type_text}.png" if type_text else "")
        self._select_background_name.setText(f"PORTRAIT_BACKGROUND_{type_text}.png" if type_text else "")

        for row, (_label, template) in enumerate(LEADER_DIPLO_SCENES):
            tag = f"LOC_DIPLO_{template.replace('XXX', short_type)}" if short_type else ""
            tag_item = self._diplomacy_table.item(row, 2)
            if tag_item is not None:
                tag_item.setText(tag)

    def _sync_diplomacy_table_height(self) -> None:
        self._diplomacy_table.resizeRowsToContents()
        total = self._diplomacy_table.horizontalHeader().height()
        for row in range(self._diplomacy_table.rowCount()):
            total += self._diplomacy_table.rowHeight(row)
        total += self._diplomacy_table.frameWidth() * 2 + 2
        self._diplomacy_table.setMinimumHeight(max(220, total))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_top_column_balance()

    def _sync_top_column_balance(self) -> None:
        if self._top_left_panel is None or self._top_icon_panel is None:
            return
        left_height = self._top_left_panel.sizeHint().height()
        available = left_height - self._icon_name.sizeHint().height() - self._icon_image.non_canvas_height_hint() - 10
        target = max(120, min(220, available))
        self._icon_image.set_preview_max_height(target)

    def _handle_abbr_changed(self, text: str) -> None:
        cleaned = _sanitize_short_token(text)
        if cleaned != text:
            cursor = self._abbr_edit.cursorPosition()
            self._abbr_edit.blockSignals(True)
            self._abbr_edit.setText(cleaned)
            self._abbr_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._abbr_edit.blockSignals(False)
        self._refresh_type_and_related()
        self._emit_data_changed()

    def _open_civilization_dialog(self) -> None:
        dialog = _LeaderCivilizationSelectionDialog(self, self._civilizations_provider)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_entry()
        if selected is None:
            return
        civ_type = _safe_text(selected.get("type"))
        civ_name = _safe_text(selected.get("name"))
        self._civilization_edit.setText(civ_type)
        self._civilization_hint.setText(civ_name)
        self._emit_data_changed()

    def _excluded_binding_keys_from_bound_civilization(self) -> set[tuple[str, object, str]]:
        civ_type = _safe_text(self._civilization_edit.text())
        if not civ_type:
            return set()

        try:
            civ_entries = self._civilizations_provider()
        except Exception:
            civ_entries = []

        selected: dict[str, object] | None = None
        for entry in civ_entries:
            if isinstance(entry, dict) and _safe_text(entry.get("type")) == civ_type:
                selected = entry
                break
        if selected is None:
            return set()

        trait_bindings = selected.get("trait_bindings")
        if not isinstance(trait_bindings, list):
            return set()

        excluded: set[tuple[str, object, str]] = set()
        for item in trait_bindings:
            if not isinstance(item, dict):
                continue
            section = _safe_text(item.get("section"))
            type_name = _safe_text(item.get("type"))
            if not section or not type_name:
                continue
            excluded.add((section, item.get("index"), type_name))
        return excluded

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._internal_updating = True
        self._entry_name_fallback = fallback_name

        self._abbr_edit.setText(_safe_text(entry.get("abbr")))
        if "leader_name" in entry:
            self._name_edit.setText(_safe_text(entry.get("leader_name")))
        else:
            self._name_edit.setText(fallback_name)
        sex = _safe_text(entry.get("sex")).lower()
        if sex == "female":
            self._female_radio.setChecked(True)
        else:
            self._male_radio.setChecked(True)

        self._capital_edit.setText(_safe_text(entry.get("capital_name")))
        self._civilization_edit.setText(_safe_text(entry.get("civilization_type")))
        self._civilization_hint.setText(_safe_text(entry.get("civilization_name")))
        self._leader_text_edit.import_tokenized_text(entry.get("leader_text"))
        self._quote_edit.setText(_safe_text(entry.get("leader_quote")))
        self._ability_name_edit.setText(_safe_text(entry.get("ability_name")))
        self._ability_desc_edit.import_tokenized_text(entry.get("ability_description"))
        try:
            sort_index_value = int(entry.get("select_sort_index") or 0)
        except (TypeError, ValueError):
            sort_index_value = 0
        self._select_sort_index_spin.setValue(max(0, sort_index_value))
        curtain_raw = entry.get("add_diplo_background_curtain", False)
        if isinstance(curtain_raw, bool):
            curtain_checked = curtain_raw
        else:
            curtain_checked = _safe_text(curtain_raw).lower() in {"1", "true", "yes", "on"}
        self._add_diplo_background_curtain_check.setChecked(curtain_checked)

        self._bindings.set_values(list(entry.get("bindings", [])) if isinstance(entry.get("bindings"), list) else [])

        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        self._icon_image.set_state(images.get("icon"))
        self._foreground_image.set_state(images.get("foreground"))
        self._background_image.set_state(images.get("background"))
        self._diplo_foreground_image.set_state(images.get("diplo_foreground"))
        self._diplo_background_image.set_state(images.get("diplo_background"))
        self._select_foreground_image.set_state(images.get("select_foreground"))
        self._select_background_image.set_state(images.get("select_background"))

        diplomacy = entry.get("diplomacy") if isinstance(entry.get("diplomacy"), list) else []
        diplo_by_tag: dict[str, str] = {}
        for row in diplomacy:
            if not isinstance(row, dict):
                continue
            tag = _safe_text(row.get("tag"))
            text = _safe_text(row.get("text"))
            if tag:
                diplo_by_tag[tag] = text

        self._refresh_type_and_related()
        for row in range(self._diplomacy_table.rowCount()):
            tag_item = self._diplomacy_table.item(row, 2)
            text_item = self._diplomacy_table.item(row, 1)
            tag = tag_item.text() if tag_item is not None else ""
            if text_item is not None:
                text_item.setText(diplo_by_tag.get(tag, ""))

        self._internal_updating = False

    def export_entry(self) -> dict[str, object]:
        leader_name = _safe_text(self._name_edit.text())
        display_name = leader_name or self._entry_name_fallback

        diplomacy_rows: list[dict[str, str]] = []
        for row, (scene_label, template) in enumerate(LEADER_DIPLO_SCENES):
            text_item = self._diplomacy_table.item(row, 1)
            tag_item = self._diplomacy_table.item(row, 2)
            text_value = _safe_text(text_item.text() if text_item else "")
            tag_value = _safe_text(tag_item.text() if tag_item else "")
            if text_value:
                diplomacy_rows.append(
                    {
                        "label": scene_label,
                        "template": template,
                        "tag": tag_value,
                        "text": text_value,
                    }
                )

        return {
            "name": display_name,
            "abbr": _safe_text(self._abbr_edit.text()),
            "type": _safe_text(self._type_label.text()),
            "leader_name": leader_name,
            "sex": "Male" if self._male_radio.isChecked() else "Female",
            "capital_name": _safe_text(self._capital_edit.text()),
            "civilization_type": _safe_text(self._civilization_edit.text()),
            "civilization_name": _safe_text(self._civilization_hint.text()),
            "leader_text": self._leader_text_edit.export_tokenized_text(),
            "leader_quote": _safe_text(self._quote_edit.text()),
            "ability_name": _safe_text(self._ability_name_edit.text()),
            "ability_description": self._ability_desc_edit.export_tokenized_text(),
            "select_sort_index": int(self._select_sort_index_spin.value()),
            "add_diplo_background_curtain": bool(self._add_diplo_background_curtain_check.isChecked()),
            "icon_image_name": _safe_text(self._icon_name.text()),
            "foreground_image_name": _safe_text(self._foreground_name.text()),
            "background_image_name": _safe_text(self._background_name.text()),
            "diplo_foreground_image_name": _safe_text(self._diplo_foreground_name.text()),
            "diplo_background_image_name": _safe_text(self._diplo_background_name.text()),
            "select_foreground_image_name": _safe_text(self._select_foreground_name.text()),
            "select_background_image_name": _safe_text(self._select_background_name.text()),
            "images": {
                "icon": self._icon_image.export_state(),
                "foreground": self._foreground_image.export_state(),
                "background": self._background_image.export_state(),
                "diplo_foreground": self._diplo_foreground_image.export_state(),
                "diplo_background": self._diplo_background_image.export_state(),
                "select_foreground": self._select_foreground_image.export_state(),
                "select_background": self._select_background_image.export_state(),
            },
            "bindings": self._bindings.values(),
            "diplomacy": diplomacy_rows,
        }

    def _emit_data_changed(self) -> None:
        if self._internal_updating:
            return
        self.dataChanged.emit()


class _GovernorPromotionNodeCard(QGroupBox):
    dataChanged = pyqtSignal()

    def __init__(self, title: str, *, optional: bool) -> None:
        super().__init__(title)
        self._optional = optional
        self._loading = False

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._enabled_check: QCheckBox | None = None
        if optional:
            self._enabled_check = QCheckBox("启用此晋升")
            layout.addWidget(self._enabled_check)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("晋升名字（中文）")
        self._desc_edit = IconTokenTextEdit()
        self._desc_edit.setPlaceholderText("晋升描述（中文），回车会导出为 [NEWLINE]")
        self._desc_edit.setFixedHeight(72)
        form.addRow("名称", self._name_edit)
        form.addRow("描述", self._desc_edit)
        layout.addLayout(form)
        self.setLayout(layout)

        if self._enabled_check is not None:
            self._enabled_check.toggled.connect(self._handle_enabled_changed)
        self._name_edit.textChanged.connect(lambda *_args: self._emit_changed())
        self._desc_edit.textChanged.connect(lambda *_args: self._emit_changed())
        self._apply_enabled_state()

    def _handle_enabled_changed(self, _checked: bool) -> None:
        self._apply_enabled_state()
        self._emit_changed()

    def _apply_enabled_state(self) -> None:
        active = self.is_active()
        self._name_edit.setEnabled(active)
        self._desc_edit.setEnabled(active)

    def is_active(self) -> bool:
        if self._enabled_check is None:
            return True
        return self._enabled_check.isChecked()

    def set_payload(self, payload: object) -> None:
        self._loading = True
        if isinstance(payload, dict):
            if self._enabled_check is not None:
                self._enabled_check.setChecked(bool(payload.get("enabled", False)))
            self._name_edit.setText(_safe_text(payload.get("name")))
            self._desc_edit.import_tokenized_text(payload.get("description"))
        else:
            if self._enabled_check is not None:
                self._enabled_check.setChecked(False)
            self._name_edit.clear()
            self._desc_edit.import_tokenized_text("")
        self._apply_enabled_state()
        self._loading = False

    def export_payload(self) -> dict[str, object]:
        data = {
            "enabled": self.is_active(),
            "name": _safe_text(self._name_edit.text()),
            "description": self._desc_edit.export_tokenized_text(),
        }
        if self._enabled_check is None:
            data["enabled"] = True
        return data

    def _emit_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()


class GovernorPromotionTreeEditor(QWidget):
    dataChanged = pyqtSignal()

    _COL_LABELS = {0: "左", 1: "中", 2: "右"}

    def __init__(self) -> None:
        super().__init__()
        self._cards: dict[tuple[int, int], _GovernorPromotionNodeCard] = {}
        self._loading = False

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(16)

        base_card = _GovernorPromotionNodeCard("基础晋升", optional=False)
        base_card.dataChanged.connect(self._emit_changed)
        self._cards[(0, 1)] = base_card
        layout.addWidget(base_card, 0, 1)

        for level in range(1, 4):
            for col in range(3):
                card = _GovernorPromotionNodeCard(f"{level}级-{self._COL_LABELS[col]}", optional=True)
                card.dataChanged.connect(self._handle_card_changed)
                self._cards[(level, col)] = card
                layout.addWidget(card, level, col)

        self.setLayout(layout)

    def _handle_card_changed(self) -> None:
        self.update()
        self._emit_changed()

    def _emit_changed(self) -> None:
        if self._loading:
            return
        self.dataChanged.emit()

    def set_payload(self, payload: object) -> None:
        self._loading = True
        for key, card in self._cards.items():
            if key == (0, 1):
                card.set_payload({"enabled": True, "name": "", "description": ""})
            else:
                card.set_payload(None)

        if isinstance(payload, dict):
            base = payload.get("base")
            if isinstance(base, dict):
                self._cards[(0, 1)].set_payload(base)
            tiers = payload.get("tiers")
            if isinstance(tiers, list):
                for level in range(1, 4):
                    row_data = tiers[level - 1] if level - 1 < len(tiers) else None
                    if not isinstance(row_data, list):
                        continue
                    for col in range(3):
                        cell = row_data[col] if col < len(row_data) else None
                        if isinstance(cell, dict):
                            self._cards[(level, col)].set_payload(cell)

        self._loading = False
        self.update()

    def export_payload(self) -> dict[str, object]:
        tiers: list[list[dict[str, object]]] = []
        for level in range(1, 4):
            row: list[dict[str, object]] = []
            for col in range(3):
                row.append(self._cards[(level, col)].export_payload())
            tiers.append(row)
        return {
            "base": self._cards[(0, 1)].export_payload(),
            "tiers": tiers,
        }

    def _center_top(self, widget: QWidget) -> QPoint:
        geo = widget.geometry()
        return QPoint(geo.x() + geo.width() // 2, geo.y())

    def _center_bottom(self, widget: QWidget) -> QPoint:
        geo = widget.geometry()
        return QPoint(geo.x() + geo.width() // 2, geo.y() + geo.height())

    def _draw_orthogonal(self, painter: QPainter, start: QPoint, end: QPoint) -> None:
        mid_y = (start.y() + end.y()) // 2
        path = QPainterPath()
        path.moveTo(float(start.x()), float(start.y()))
        path.lineTo(float(start.x()), float(mid_y))
        path.lineTo(float(end.x()), float(mid_y))
        path.lineTo(float(end.x()), float(end.y()))
        painter.drawPath(path)

    @staticmethod
    def _parent_positions(level: int, col: int) -> list[tuple[int, int]]:
        if level <= 1:
            return [(0, 1)]
        if col == 0:
            return [(level - 1, 0), (level - 1, 1)]
        if col == 1:
            return [(level - 1, 0), (level - 1, 1), (level - 1, 2)]
        return [(level - 1, 2), (level - 1, 1)]

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor("#2563eb"), 2))

        base_card = self._cards[(0, 1)]

        active_nodes: set[tuple[int, int]] = set()
        for level in range(1, 4):
            for col in range(3):
                if self._cards[(level, col)].is_active():
                    active_nodes.add((level, col))

        for col in range(3):
            if (1, col) not in active_nodes:
                continue
            self._draw_orthogonal(
                painter,
                self._center_bottom(base_card),
                self._center_top(self._cards[(1, col)]),
            )

        for level in range(2, 4):
            for col in range(3):
                if (level, col) not in active_nodes:
                    continue
                for parent in self._parent_positions(level, col):
                    if parent not in active_nodes:
                        continue
                    self._draw_orthogonal(
                        painter,
                        self._center_bottom(self._cards[parent]),
                        self._center_top(self._cards[(level, col)]),
                    )


class GovernorItemEditor(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, shared_params_provider: Callable[[], dict[str, object]]) -> None:
        super().__init__()
        self._shared_params_provider = shared_params_provider
        self._internal_updating = False
        self._entry_name_fallback = ""

        self._code_edit = QLineEdit()
        self._code_edit.setPlaceholderText("仅英文/数字/下划线")
        self._type_label = QLabel("")
        self._type_label.setObjectName("pageInfoLabel")

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("总督名字（中文）")
        self._desc_edit = IconTokenTextEdit()
        self._desc_edit.setPlaceholderText("总督描述（中文），回车会导出为 [NEWLINE]")
        self._desc_edit.setFixedHeight(96)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("头衔（中文）")
        self._short_title_edit = QLineEdit()
        self._short_title_edit.setPlaceholderText("短头衔（中文）")

        self._identity_spin = QSpinBox()
        self._identity_spin.setRange(0, 999)
        self._identity_spin.setValue(0)
        self._transition_spin = QSpinBox()
        self._transition_spin.setRange(0, 9999)
        self._transition_spin.setValue(100)
        self._assign_city_state_check = QCheckBox("允许派驻城邦（AssignCityState）")

        self._trait_type_edit = QLineEdit()
        self._trait_type_edit.setPlaceholderText("TraitType（英文）")
        self._new_trait_check = QCheckBox("新TraitType")
        self._trait_autofill_btn = QPushButton("自动填充")

        self._assign_to_major_check = QCheckBox("Governors_XP2.AssignToMajor")
        self._cannot_assign_check = QCheckBox("GovernorsCannotAssign.CannotAssign")

        self._image_name_edit = QLineEdit(); self._image_name_edit.setReadOnly(True)
        self._portrait_name_edit = QLineEdit(); self._portrait_name_edit.setReadOnly(True)
        self._portrait_selected_name_edit = QLineEdit(); self._portrait_selected_name_edit.setReadOnly(True)
        self._icon_name_edit = QLineEdit(); self._icon_name_edit.setReadOnly(True)
        self._icon_fill_name_edit = QLineEdit(); self._icon_fill_name_edit.setReadOnly(True)
        self._icon_slot_name_edit = QLineEdit(); self._icon_slot_name_edit.setReadOnly(True)

        self._normal_image = _ImageSlotWidget((206, 208), enable_circle_crop=False)
        self._selected_image = _ImageSlotWidget((326, 339), enable_circle_crop=False)
        self._icon_image = _ImageSlotWidget((256, 256), enable_circle_crop=True)
        self._icon_fill_image = _ImageSlotWidget((256, 256), enable_circle_crop=True)
        self._icon_slot_image = _ImageSlotWidget((256, 256), enable_circle_crop=True)

        self._promotion_tree = GovernorPromotionTreeEditor()

        self._build_ui()
        self._bind_events()
        self._refresh_type_and_names()

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form_group = QGroupBox("Governors 主表")
        form = QFormLayout()
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(8)

        form.addRow("简称", self._code_edit)
        form.addRow("完整Type", self._type_label)
        form.addRow("Name（中文）", self._name_edit)
        form.addRow("Description（中文）", self._desc_edit)
        form.addRow("Title（中文）", self._title_edit)
        form.addRow("ShortTitle（中文）", self._short_title_edit)
        form.addRow("IdentityPressure", self._identity_spin)
        form.addRow("TransitionStrength", self._transition_spin)
        transition_hint = QLabel("100:5回合  125:4回合  150:3回合  250:2回合  500:1.99回合  501:0回合")
        transition_hint.setObjectName("pageInfoLabel")
        transition_hint.setWordWrap(True)
        form.addRow("说明", transition_hint)
        form.addRow("", self._assign_city_state_check)

        trait_row = QWidget()
        trait_layout = QHBoxLayout(trait_row)
        trait_layout.setContentsMargins(0, 0, 0, 0)
        trait_layout.setSpacing(6)
        trait_layout.addWidget(self._trait_type_edit, 1)
        trait_layout.addWidget(self._trait_autofill_btn, 0)
        trait_layout.addWidget(self._new_trait_check, 0)
        form.addRow("TraitType", trait_row)

        subtable_row = QWidget()
        subtable_layout = QVBoxLayout(subtable_row)
        subtable_layout.setContentsMargins(0, 0, 0, 0)
        subtable_layout.setSpacing(4)
        subtable_layout.addWidget(self._assign_to_major_check)
        subtable_layout.addWidget(self._cannot_assign_check)
        form.addRow("副表开关", subtable_row)
        form_group.setLayout(form)

        image_group = QGroupBox("主图（固定命名）")
        image_layout = QGridLayout()
        image_layout.setContentsMargins(10, 10, 10, 10)
        image_layout.setHorizontalSpacing(10)
        image_layout.setVerticalSpacing(8)

        image_layout.addWidget(QLabel("Image / PortraitImage（{完整Type}_NORMAL）"), 0, 0)
        image_layout.addWidget(QLabel("PortraitImageSelected（{完整Type}_SELECTED）"), 0, 1)

        image_layout.addWidget(self._image_name_edit, 1, 0)
        image_layout.addWidget(self._portrait_selected_name_edit, 1, 1)

        image_layout.addWidget(self._normal_image, 2, 0)
        image_layout.addWidget(self._selected_image, 2, 1)
        image_group.setLayout(image_layout)

        root.addWidget(form_group)
        root.addWidget(image_group)

        icon_group = QGroupBox("ICON 图标（256x256，支持圆形裁切）")
        icon_layout = QGridLayout()
        icon_layout.setContentsMargins(10, 10, 10, 10)
        icon_layout.setHorizontalSpacing(10)
        icon_layout.setVerticalSpacing(8)

        icon_layout.addWidget(QLabel("ICON_{完整Type}"), 0, 0)
        icon_layout.addWidget(self._icon_name_edit, 1, 0)
        icon_layout.addWidget(self._icon_image, 2, 0)
        icon_layout.addWidget(QLabel("ICON_{完整Type}_FILL"), 0, 1)
        icon_layout.addWidget(self._icon_fill_name_edit, 1, 1)
        icon_layout.addWidget(self._icon_fill_image, 2, 1)
        icon_layout.addWidget(QLabel("ICON_{完整Type}_SLOT"), 0, 2)
        icon_layout.addWidget(self._icon_slot_name_edit, 1, 2)
        icon_layout.addWidget(self._icon_slot_image, 2, 2)
        icon_group.setLayout(icon_layout)
        root.addWidget(icon_group)

        promo_group = QGroupBox("晋升树")
        promo_layout = QVBoxLayout()
        promo_layout.setContentsMargins(10, 10, 10, 10)
        promo_layout.addWidget(self._promotion_tree)
        promo_group.setLayout(promo_layout)
        root.addWidget(promo_group)

        root.addStretch(1)
        self.setLayout(root)

    def _bind_events(self) -> None:
        self._code_edit.textChanged.connect(self._handle_code_changed)
        for widget in (
            self._name_edit,
            self._desc_edit,
            self._title_edit,
            self._short_title_edit,
            self._trait_type_edit,
        ):
            widget.textChanged.connect(lambda *_args: self._emit_data_changed())

        self._identity_spin.valueChanged.connect(lambda *_args: self._emit_data_changed())
        self._transition_spin.valueChanged.connect(lambda *_args: self._emit_data_changed())
        self._assign_city_state_check.toggled.connect(lambda *_args: self._emit_data_changed())
        self._new_trait_check.toggled.connect(lambda *_args: self._emit_data_changed())
        self._assign_to_major_check.toggled.connect(lambda *_args: self._emit_data_changed())
        self._cannot_assign_check.toggled.connect(lambda *_args: self._emit_data_changed())
        self._trait_autofill_btn.clicked.connect(self._handle_trait_autofill)

        for image_widget in (
            self._normal_image,
            self._selected_image,
            self._icon_image,
            self._icon_fill_image,
            self._icon_slot_image,
        ):
            image_widget.dataChanged.connect(self._emit_data_changed)

        self._promotion_tree.dataChanged.connect(self._emit_data_changed)

    def _current_type(self) -> str:
        shared = self._shared_params_provider()
        return _build_entity_type(shared, head="GOVERNOR", midfix_code="G", short_name=self._code_edit.text())

    def _refresh_type_and_names(self) -> None:
        governor_type = self._current_type()
        self._type_label.setText(governor_type)

        image_name = f"{governor_type}_NORMAL" if governor_type else ""
        selected_name = f"{governor_type}_SELECTED" if governor_type else ""
        icon_name = f"ICON_{governor_type}" if governor_type else ""

        self._image_name_edit.setText(image_name)
        self._portrait_name_edit.setText(image_name)
        self._portrait_selected_name_edit.setText(selected_name)
        self._icon_name_edit.setText(icon_name)
        self._icon_fill_name_edit.setText(f"{icon_name}_FILL" if icon_name else "")
        self._icon_slot_name_edit.setText(f"{icon_name}_SLOT" if icon_name else "")

    def _handle_code_changed(self, text: str) -> None:
        cleaned = _sanitize_short_token(text)
        if cleaned != text:
            cursor = self._code_edit.cursorPosition()
            self._code_edit.blockSignals(True)
            self._code_edit.setText(cleaned)
            self._code_edit.setCursorPosition(max(0, min(cursor - (len(text) - len(cleaned)), len(cleaned))))
            self._code_edit.blockSignals(False)
        self._refresh_type_and_names()
        self._emit_data_changed()

    def _infer_code_from_type(self, governor_type: str) -> str:
        normalized = _safe_text(governor_type).upper()
        if not normalized.startswith("GOVERNOR_"):
            return ""
        pieces = [token for token in normalized.split("_") if token]
        if len(pieces) <= 1:
            return ""
        return _sanitize_short_token(pieces[-1])

    def _handle_trait_autofill(self) -> None:
        governor_type = _safe_text(self._type_label.text())
        if not governor_type:
            return
        self._trait_type_edit.setText(f"TRAIT_{governor_type}")
        self._new_trait_check.setChecked(True)
        self._emit_data_changed()

    def set_entry(self, entry: dict[str, object], fallback_name: str) -> None:
        self._internal_updating = True
        self._entry_name_fallback = fallback_name

        governor_type = _safe_text(entry.get("GovernorType") or entry.get("type"))
        code = _safe_text(entry.get("code"))
        if not code:
            code = self._infer_code_from_type(governor_type)
        self._code_edit.setText(code)

        self._name_edit.setText(_safe_text(entry.get("Name")))
        self._desc_edit.import_tokenized_text(entry.get("Description") or entry.get("description"))
        self._title_edit.setText(_safe_text(entry.get("Title") or entry.get("title")))
        self._short_title_edit.setText(_safe_text(entry.get("ShortTitle") or entry.get("short_title")))
        self._identity_spin.setValue(int(entry.get("IdentityPressure", 0) or 0))
        transition_raw = entry.get("TransitionStrength")
        if transition_raw is None:
            self._transition_spin.setValue(100)
        else:
            self._transition_spin.setValue(int(transition_raw or 0))
        self._assign_city_state_check.setChecked(bool(entry.get("AssignCityState", False)))

        self._trait_type_edit.setText(_safe_text(entry.get("TraitType") or entry.get("trait_type")))
        self._new_trait_check.setChecked(bool(entry.get("new_trait_type", False)))
        self._assign_to_major_check.setChecked(bool(entry.get("assign_to_major", False)))
        self._cannot_assign_check.setChecked(bool(entry.get("cannot_assign", False)))

        images = entry.get("images") if isinstance(entry.get("images"), dict) else {}
        self._normal_image.set_state(images.get("normal"))
        self._selected_image.set_state(images.get("selected"))
        self._icon_image.set_state(images.get("icon"))
        self._icon_fill_image.set_state(images.get("icon_fill"))
        self._icon_slot_image.set_state(images.get("icon_slot"))

        self._promotion_tree.set_payload(entry.get("promotions"))
        self._refresh_type_and_names()

        self._internal_updating = False

    def export_entry(self) -> dict[str, object]:
        governor_type = _safe_text(self._type_label.text())
        name_text = _safe_text(self._name_edit.text())
        return {
            "name": name_text or self._entry_name_fallback,
            "code": _safe_text(self._code_edit.text()),
            "GovernorType": governor_type,
            "Name": name_text,
            "Description": self._desc_edit.export_tokenized_text(),
            "Title": _safe_text(self._title_edit.text()),
            "ShortTitle": _safe_text(self._short_title_edit.text()),
            "IdentityPressure": int(self._identity_spin.value()),
            "TransitionStrength": int(self._transition_spin.value()),
            "AssignCityState": 1 if self._assign_city_state_check.isChecked() else 0,
            "TraitType": _safe_text(self._trait_type_edit.text()),
            "new_trait_type": bool(self._new_trait_check.isChecked()),
            "assign_to_major": bool(self._assign_to_major_check.isChecked()),
            "cannot_assign": bool(self._cannot_assign_check.isChecked()),
            "Image": _safe_text(self._image_name_edit.text()),
            "PortraitImage": _safe_text(self._portrait_name_edit.text()),
            "PortraitImageSelected": _safe_text(self._portrait_selected_name_edit.text()),
            "icon_image_name": _safe_text(self._icon_name_edit.text()),
            "icon_fill_image_name": _safe_text(self._icon_fill_name_edit.text()),
            "icon_slot_image_name": _safe_text(self._icon_slot_name_edit.text()),
            "images": {
                "normal": self._normal_image.export_state(),
                "selected": self._selected_image.export_state(),
                "icon": self._icon_image.export_state(),
                "icon_fill": self._icon_fill_image.export_state(),
                "icon_slot": self._icon_slot_image.export_state(),
            },
            "promotions": self._promotion_tree.export_payload(),
        }

    def _emit_data_changed(self) -> None:
        if self._internal_updating:
            return
        self.dataChanged.emit()


class SectionItemWorkspacePanel(QWidget):
    """子条目编辑页：文明/领袖/区域/建筑/单位/改良设施/总督/伟人已接入，其它分类先占位。"""

    def __init__(
        self,
        *,
        shared_params_provider: Callable[[], dict[str, object]],
        bindable_entries_provider: Callable[[str], list[dict[str, object]]],
        civilizations_provider: Callable[[], list[dict[str, str]]],
        on_item_changed: Callable[[str, int, dict[str, object]], None],
        on_duplicate_item: Callable[[str, int, dict[str, object]], None] | None = None,
        on_delete_item: Callable[[str, int], None] | None = None,
        custom_reqsets_provider: Callable[[], list[dict[str, object]]] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("sectionItemWorkspacePanel")
        self.setProperty("workspacePanel", "true")
        self._shared_params_provider = shared_params_provider
        self._bindable_entries_provider = bindable_entries_provider
        self._on_item_changed = on_item_changed
        self._on_duplicate_item = on_duplicate_item
        self._on_delete_item = on_delete_item

        self._section = ""
        self._index = -1
        self._loading = False

        self._delete_button = QPushButton("删除当前对象")
        self._delete_button.clicked.connect(self._handle_delete_current)
        _apply_small_button(self._delete_button)
        self._delete_button.setVisible(False)

        self._stack = QStackedWidget()
        self._placeholder = QLabel("该分类子条目编辑器待接入。")
        self._placeholder.setObjectName("pageInfoLabel")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._civilization_editor = CivilizationItemEditor(shared_params_provider, bindable_entries_provider)
        self._civilization_editor.dataChanged.connect(self._handle_civilization_changed)

        self._leader_editor = LeaderItemEditor(shared_params_provider, bindable_entries_provider, civilizations_provider)
        self._leader_editor.dataChanged.connect(self._handle_leader_changed)

        self._district_editor = DistrictCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._district_editor.dataChanged.connect(self._handle_district_changed)

        self._building_editor = BuildingCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._building_editor.dataChanged.connect(self._handle_building_changed)

        self._unit_editor = UnitCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._unit_editor.dataChanged.connect(self._handle_unit_changed)

        self._improvement_editor = ImprovementCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._improvement_editor.dataChanged.connect(self._handle_improvement_changed)

        self._policy_editor = PolicyCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._policy_editor.dataChanged.connect(self._handle_policy_changed)
        self._policy_editor.duplicateRequested.connect(self._handle_policy_duplicate_requested)

        self._belief_editor = BeliefCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._belief_editor.dataChanged.connect(self._handle_belief_changed)
        self._belief_editor.duplicateRequested.connect(self._handle_belief_duplicate_requested)

        self._project_editor = ProjectCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
            project_entries_provider=lambda: self._bindable_entries_provider("项目"),
        )
        self._project_editor.dataChanged.connect(self._handle_project_changed)

        self._governor_editor = GovernorItemEditor(shared_params_provider)
        self._governor_editor.dataChanged.connect(self._handle_governor_changed)

        self._great_people_editor = GreatPeopleCompositeEditor(
            shared_params_provider,
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
        )
        self._great_people_editor.dataChanged.connect(self._handle_great_people_changed)

        self._agenda_editor = AgendaCompositeEditor(
            shared_params_provider=shared_params_provider,
            type_builder=lambda shared, head, midfix_code, short_name: _build_entity_type(
                shared,
                head=head,
                midfix_code=midfix_code,
                short_name=short_name,
            ),
            image_widget_factory=lambda size, enable_circle: _ImageSlotWidget(size, enable_circle_crop=enable_circle),
            leader_entries_provider=lambda: list(self._bindable_entries_provider("领袖")),
            random_agendas_provider=_query_random_agendas,
            ai_list_types_provider=_query_ai_list_types,
            custom_reqset_provider=custom_reqsets_provider or _query_empty_reqsets,
            text_search_provider=_resolve_loc_text,
        )
        self._agenda_editor.dataChanged.connect(self._handle_agenda_changed)

        self._placeholder_page = self._wrap_main_scroll(self._placeholder)
        self._civilization_page = self._wrap_main_scroll(self._civilization_editor)
        self._leader_page = self._wrap_main_scroll(self._leader_editor)
        self._district_page = self._wrap_main_scroll(self._district_editor)
        self._building_page = self._wrap_main_scroll(self._building_editor)
        self._unit_page = self._wrap_main_scroll(self._unit_editor)
        self._improvement_page = self._wrap_main_scroll(self._improvement_editor)
        self._policy_page = self._wrap_main_scroll(self._policy_editor)
        self._belief_page = self._wrap_main_scroll(self._belief_editor)
        self._project_page = self._wrap_main_scroll(self._project_editor)
        self._governor_page = self._wrap_main_scroll(self._governor_editor)
        self._great_people_page = self._wrap_main_scroll(self._great_people_editor)
        self._agenda_page = self._wrap_main_scroll(self._agenda_editor)

        self._stack.addWidget(self._placeholder_page)
        self._stack.addWidget(self._civilization_page)
        self._stack.addWidget(self._leader_page)
        self._stack.addWidget(self._district_page)
        self._stack.addWidget(self._building_page)
        self._stack.addWidget(self._unit_page)
        self._stack.addWidget(self._improvement_page)
        self._stack.addWidget(self._policy_page)
        self._stack.addWidget(self._belief_page)
        self._stack.addWidget(self._project_page)
        self._stack.addWidget(self._governor_page)
        self._stack.addWidget(self._great_people_page)
        self._stack.addWidget(self._agenda_page)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        top_row = QHBoxLayout()
        top_row.addWidget(self._delete_button)
        top_row.addStretch(1)
        layout.addLayout(top_row)
        layout.addWidget(self._stack)
        self.setLayout(layout)

    def _wrap_main_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        return scroll

    def set_item(self, section: str, index: int, entry: dict[str, object], fallback_name: str) -> None:
        self._section = section
        self._index = index
        self._loading = True
        self._delete_button.setVisible(bool(section) and index >= 0)
        self._delete_button.setEnabled(callable(self._on_delete_item) and bool(section) and index >= 0)

        if section == "文明":
            self._civilization_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._civilization_page)
        elif section == "领袖":
            self._leader_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._leader_page)
        elif section == "区域":
            self._district_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._district_page)
        elif section == "建筑":
            self._building_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._building_page)
        elif section == "单位":
            self._unit_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._unit_page)
        elif section == "改良设施":
            self._improvement_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._improvement_page)
        elif section == "政策卡":
            self._policy_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._policy_page)
        elif section == "信仰":
            self._belief_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._belief_page)
        elif section == "项目":
            self._project_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._project_page)
        elif section == "总督":
            self._governor_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._governor_page)
        elif section == "伟人":
            self._great_people_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._great_people_page)
        elif section == "议程":
            self._agenda_editor.set_entry(entry, fallback_name=fallback_name)
            self._stack.setCurrentWidget(self._agenda_page)
        else:
            self._placeholder.setText(f"{section} 子条目编辑器待接入。\n已保留统一框架与预览逻辑。")
            self._stack.setCurrentWidget(self._placeholder_page)

        self._loading = False
        self._sync_current_item_to_project()

    def _sync_current_item_to_project(self) -> None:
        if self._section == "文明" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._civilization_editor.export_entry())
            return
        if self._section == "领袖" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._leader_editor.export_entry())
            return
        if self._section == "区域" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._district_editor.export_entry())
            return
        if self._section == "建筑" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._building_editor.export_entry())
            return
        if self._section == "单位" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._unit_editor.export_entry())
            return
        if self._section == "改良设施" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._improvement_editor.export_entry())
            return
        if self._section == "政策卡" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._policy_editor.export_entry())
            return
        if self._section == "信仰" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._belief_editor.export_entry())
            return
        if self._section == "项目" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._project_editor.export_entry())
            return
        if self._section == "总督" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._governor_editor.export_entry())
            return
        if self._section == "伟人" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._great_people_editor.export_entry())
            return
        if self._section == "议程" and self._index >= 0:
            self._on_item_changed(self._section, self._index, self._agenda_editor.export_entry())
            return

    def _handle_civilization_changed(self) -> None:
        if self._loading:
            return
        if self._section != "文明" or self._index < 0:
            return
        payload = self._civilization_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_leader_changed(self) -> None:
        if self._loading:
            return
        if self._section != "领袖" or self._index < 0:
            return
        payload = self._leader_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_district_changed(self) -> None:
        if self._loading:
            return
        if self._section != "区域" or self._index < 0:
            return
        payload = self._district_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_building_changed(self) -> None:
        if self._loading:
            return
        if self._section != "建筑" or self._index < 0:
            return
        payload = self._building_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_unit_changed(self) -> None:
        if self._loading:
            return
        if self._section != "单位" or self._index < 0:
            return
        payload = self._unit_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_improvement_changed(self) -> None:
        if self._loading:
            return
        if self._section != "改良设施" or self._index < 0:
            return
        payload = self._improvement_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_governor_changed(self) -> None:
        if self._loading:
            return
        if self._section != "总督" or self._index < 0:
            return
        payload = self._governor_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_policy_changed(self) -> None:
        if self._loading:
            return
        if self._section != "政策卡" or self._index < 0:
            return
        payload = self._policy_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_policy_duplicate_requested(self, payload: dict[str, object]) -> None:
        if self._loading:
            return
        if self._section != "政策卡" or self._index < 0:
            return
        if not callable(self._on_duplicate_item):
            return
        self._on_duplicate_item(self._section, self._index, payload)

    def _handle_belief_changed(self) -> None:
        if self._loading:
            return
        if self._section != "信仰" or self._index < 0:
            return
        payload = self._belief_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_belief_duplicate_requested(self, payload: dict[str, object]) -> None:
        if self._loading:
            return
        if self._section != "信仰" or self._index < 0:
            return
        if not callable(self._on_duplicate_item):
            return
        self._on_duplicate_item(self._section, self._index, payload)

    def _handle_project_changed(self) -> None:
        if self._loading:
            return
        if self._section != "项目" or self._index < 0:
            return
        payload = self._project_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_great_people_changed(self) -> None:
        if self._loading:
            return
        if self._section != "伟人" or self._index < 0:
            return
        payload = self._great_people_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_agenda_changed(self) -> None:
        if self._loading:
            return
        if self._section != "议程" or self._index < 0:
            return
        payload = self._agenda_editor.export_entry()
        self._on_item_changed(self._section, self._index, payload)

    def _handle_delete_current(self) -> None:
        if self._loading:
            return
        if not callable(self._on_delete_item):
            return
        if not self._section or self._index < 0:
            return
        self._on_delete_item(self._section, self._index)
