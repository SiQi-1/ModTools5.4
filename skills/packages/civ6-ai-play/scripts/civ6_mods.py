#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_mods.py —— 读写《文明6》Mods.sqlite：列出模组、查看/切换启用状态、备份/还原

一、文件位置
    用户数据目录：%LOCALAPPDATA%\\Firaxis Games\\Sid Meier's Civilization VI\\
    Mod 数据库：  Mods.sqlite（大小与 schema 版本随游戏版本/环境变化；以 PRAGMA user_version 为准）
    游戏根目录：  <Steam 库>\\steamapps\\common\\Sid Meier's Civilization VI
                  （本模块不需要游戏目录，仅说明路径来源；可由 civ6_game.find_game_dir() 探测）
    可用 --db 指定其他 Mods.sqlite；只读命令不会写入任何内容。

二、schema（列名/主键与游戏实际写入的数据库一致；下文行数均为实测示例，
    随游戏版本与已装 Mod 数量变化，不代表固定值）
    下列列名/主键来自 sqlite_master，与游戏写入的数据库一致：

    Mods(ModRowId INTEGER PK AUTOINCREMENT, ScannedFileRowId INTEGER NOT NULL,
         ModId TEXT NOT NULL, Version INTEGER NOT NULL)
        - ModRowId 是全库其他表的关联键；ModId 是 modinfo 里的 <Mod id>（大小写不固定，
          有的带花括号，如 {5E991A08-...}，比较前需去括号并忽略大小写）。

    ScannedFiles(ScannedFileRowId INTEGER PK AUTOINCREMENT, Path TEXT UNIQUE,
                 LastWriteTime INTEGER)
        - Path 是 .modinfo 路径。实测三种形态：
            * 工坊：<Steam 库>\\steamapps\\workshop\\content\\289070\\<publishedfileid>\\xxx.modinfo
            * 官方 Base/DLC：../../../Base/Assets/.../X.modinfo、../../../DLC/Expansion2/Expansion2.modinfo
            * 用户本地：Documents\\My Games\\Sid Meier's Civilization VI\\Mods\\...（未安装本地 Mod 时可能不出现）
        - LastWriteTime 是 Windows FILETIME（100ns 单位），不是 Unix 时间戳。

    ModProperties(ModRowId INTEGER NOT NULL, Name TEXT NOT NULL, Value TEXT,
                  PRIMARY KEY(ModRowId, Name))
        - 实测出现过的 Name：Name / Description / Teaser / Authors / CompatibleVersions /
          EnabledByDefault / AffectsSavedGames / SupportsSinglePlayer / SupportsMultiplayer /
          SupportsHotSeat / SubscriptionID。
        - Name 属性 = 模组显示名，值可能是字面量（如 Enhanced Mod Manager），也可能是
          本地化标签（如 LOC_EXPANSION2_MOD_TITLE），后者需要查 LocalizedText。

    LocalizedText(ModRowId INTEGER NOT NULL, Tag TEXT NOT NULL, Locale TEXT NOT NULL,
                  Text TEXT NOT NULL, PRIMARY KEY(ModRowId, Tag, Locale))
        - 实测 Locale：de_DE / en_US / es_ES / fr_FR / it_IT / ja_JP / ko_KR / pl_PL /
          pt_BR / ru_RU / zh_Hans_CN / zh_Hans_HK / zh_Hant_HK。
        - 注意：官方 Base/DLC 的模组名（LOC_EXPANSION2_MOD_TITLE 等）不在这张表里，
          它们属于游戏正文文本库；本模块此时保留原始 LOC 标签并标记 name_resolved=false。

    ModFiles(FileRowId INTEGER PK AUTOINCREMENT, ModRowId INTEGER NOT NULL, Path TEXT NOT NULL)
        - 每个 mod 根目录下的文件清单（相对路径）。

    ModGroups(ModGroupRowId INTEGER PK AUTOINCREMENT, Name TEXT NOT NULL,
              CanDelete BOOLEAN DEFAULT 1, Selected BOOLEAN DEFAULT 0,
              SortIndex INTEGER DEFAULT 100)
        - 典型 2 组（实测示例，随用户环境变化）：第 1 组 Name=LOC_MODS_GROUP_DEFAULT_NAME,
          CanDelete=0, Selected=0, SortIndex=0；第 2 组 Name=自动：上次使用的MOD组,
          CanDelete=1, Selected=1, SortIndex=100。
        - Selected=1 表示当前生效的组（切换 MOD 配置即切换选中组）。

    ModGroupItems(ModGroupRowId INTEGER NOT NULL, ModRowId INTEGER NOT NULL,
                  Disabled BOOLEAN DEFAULT 0, PRIMARY KEY(ModGroupRowId, ModRowId))
        - Disabled=1 表示该组内禁用；=0 表示启用。
        - 每组行数随启用配置变化；部分官方 DLC/场景 Mod 可能不在任何组内（首次启用时需插入行）。

    **启用集定义**（本模块统一口径）：
        启用 ModRowId 集合 = { i.ModRowId | i 属于 Selected=1 的 ModGroup 且 COALESCE(i.Disabled,0)=0 }
        启用数量随用户配置变化（可含工坊 Mod 与官方 Base/DLC/场景）。

    其余表（了解即可，本模块不写）：
        Components / ComponentFiles / ComponentProperties / ComponentCriteria /
        ComponentRelationships / ComponentReferences（modinfo 的 Components）
        Settings / SettingFiles / SettingProperties / SettingCriteria（UpdateDatabase/UpdateText 等动作）
        Criteria / Criterion / CriterionProperties（条件）
        ModRelationships（Dependency/Exclude 关系）
        ModCompatibilityWhitelist / AdditionalScannedFiles / Migrations / SystemSettings /
        sqlite_sequence / sqlite_stat1。

三、来源分类（source）
    workshop —— Path 含 /workshop/content/（Steam 创意工坊）
    official —— Path 以 ../ 开头（官方 Base/DLC/场景，相对游戏目录）
    user     —— 其余（Documents\\My Games\\Sid Meier's Civilization VI\\Mods 下的本地 Mod）

四、写操作安全约定（重要）
    1. 写前先 backup：把 Mods.sqlite 复制为 Mods.sqlite.bak-YYYYmmdd-HHMMSS（同目录或 --out），
       校验副本 SHA256 与 PRAGMA quick_check=ok；
    2. 游戏进程运行时**拒绝写入**（CivilizationVI.exe / CivilizationVI_DX12.exe / LaunchPad.exe）；
    3. 写操作放在 BEGIN IMMEDIATE 事务内，失败回滚；
    4. 写后重新以只读方式校验目标组状态，校验失败会提示用 restore 还原备份；
    5. 默认只更新 Selected=1 的组；可用 --group 指定组；可用 --dry-run 只看计划不写；
       不带 --yes 时 CLI 只输出计划，绝不写入。

五、主要 API
    default_db_path() / user_data_dir()
    load_snapshot(db_path=None) -> ModsSnapshot     一次读出 Mods/组/启用集的完整快照
    load_mods(db_path=None) -> list[ModInfo]        完整对象版
    list_mods(db_path=None) -> list[dict]           JSON 友好版（CLI/统一入口直接打印）
    load_groups(db_path=None) -> list[ModGroupInfo]
    list_groups(db_path=None) -> list[dict]         JSON 友好版
    get_enabled(db_path=None) -> dict               当前启用集
    enabled_mods(db_path=None) -> dict              兼容别名（= get_enabled）
    set_enabled(query, enabled, ...) -> dict        兼容别名（= apply=True 的 set_mod_enabled）
    backup(...) -> str / restore(path) -> str       兼容别名（返回路径）
    find_matches(mods, query, exact=False)          按 ModId/名称/RowId/路径片段匹配
    backup_database(db_path=None, out_dir=None, label=None) -> BackupInfo
    restore_database(backup_path, db_path=None)     还原并做安全备份
    set_mod_enabled(db_path, query, enabled, dry_run=False, apply=False, ...) -> dict
                                                    启用/禁用（默认 dry-run）
    running_game_processes() -> list[ProcessInfo]   游戏/启动器进程探测

六、CLI
    python civ6_mods.py list [--source user|workshop|official] [--state enabled|disabled]
                             [--limit N] [--json]
    python civ6_mods.py groups            [--json]
    python civ6_mods.py enabled           [--json]
    python civ6_mods.py enable  模组名或ModId [--dry-run] [--yes] [--exact] [--group ROWID]
    python civ6_mods.py disable 模组名或ModId [--dry-run] [--yes] [--exact] [--group ROWID]
    python civ6_mods.py backup [--out 目录] [--label 说明]
    python civ6_mods.py restore 备份文件 [--yes] [--db 目标]
    示例（PowerShell）：
      python skills/civ6-ai-play/scripts/civ6_mods.py list --source workshop --limit 10
      python skills/civ6-ai-play/scripts/civ6_mods.py enabled --json
      python skills/civ6-ai-play/scripts/civ6_mods.py backup
      python skills/civ6-ai-play/scripts/civ6_mods.py enable "Enhanced Mod Manager" --dry-run
    退出码：0 成功；2 未找到/匹配歧义/参数问题；3 游戏运行中或数据库被锁；
            4 备份/还原/写后校验失败；1 其他错误。

七、已知限制
    - 官方 Base/DLC 的 LOC 名称不在 Mods.sqlite 中，列表会显示原始标签（name_resolved=false）；
    - 游戏运行时会持续持有/更新 Mods.sqlite，此时只读查询可能看到中间状态，写入一律拒绝；
    - 切换 Selected 组（=切换整套 MOD 配置）不在本模块范围，请用游戏内置 Mod 管理器或 Enhanced Mod Manager；
    - 游戏内“启用”还受 modinfo 的 EnabledByDefault、Criteria 条件影响，本模块只忠实读写 ModGroupItems.Disabled；
    - 本模块不启动、不结束游戏进程，也不读取游戏安装目录。
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import difflib
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from typing import Iterable

if sys.platform == "win32":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    _kernel32.OpenProcess.restype = ctypes.c_void_p
    _kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    _kernel32.CloseHandle.restype = ctypes.c_int
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_ulong)]
    _kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
    _psapi.EnumProcesses.argtypes = [
        ctypes.POINTER(ctypes.c_ulong), ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    _psapi.EnumProcesses.restype = ctypes.c_int
else:  # 非 Windows 仅支持 --db 显式指定的只读分析
    _kernel32 = None
    _psapi = None

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GAME_PROCESS_NAMES = ("civilizationvi.exe", "civilizationvi_dx12.exe", "launchpad.exe")

# 名称本地化查找顺序：简体中文优先，其次英文，最后任意
LOCALE_PRIORITY = ("zh_Hans_CN", "zh_Hans", "zh_CN", "zh_Hans_HK",
                   "en_US", "en_GB", "en_US_POSIX")
CORE_TABLES = ("Mods", "ScannedFiles", "ModProperties", "LocalizedText",
               "ModGroups", "ModGroupItems")


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class Civ6ModsError(RuntimeError):
    """本模块错误基类。"""


class DatabaseNotFoundError(Civ6ModsError):
    """Mods.sqlite 不存在或不是有效数据库。"""


class GameRunningError(Civ6ModsError):
    """游戏/启动器正在运行，拒绝写入 Mods.sqlite。"""


class DatabaseLockedError(Civ6ModsError):
    """数据库被其他进程锁定（游戏或 Mod 管理器正在写）。"""


class ModNotFoundError(Civ6ModsError):
    """按名称/ModId 找不到模组。"""


class AmbiguousModError(Civ6ModsError):
    """关键字匹配到多个模组，需要更精确的名称或 ModId。"""

    def __init__(self, message: str, candidates: list["ModInfo"]):
        super().__init__(message)
        self.candidates = candidates


class VerificationError(Civ6ModsError):
    """写后/备份后校验失败。"""


# ---------------------------------------------------------------------------
# 路径与进程
# ---------------------------------------------------------------------------
def user_data_dir() -> str:
    """《文明6》用户数据目录；可用环境变量 CIV6_USER_DATA_DIR 覆盖（便于测试）。"""
    override = os.environ.get("CIV6_USER_DATA_DIR")
    if override:
        return os.path.abspath(override)
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise Civ6ModsError("环境变量 LOCALAPPDATA 不存在，无法定位《文明6》用户数据目录；"
                            "请用 --db 显式指定 Mods.sqlite")
    return os.path.join(local_appdata, "Firaxis Games", "Sid Meier's Civilization VI")


def default_db_path() -> str:
    """默认 Mods.sqlite 绝对路径。"""
    return os.path.join(user_data_dir(), "Mods.sqlite")


def resolve_db_path(db_path: str | None = None) -> str:
    """把 --db / None 归一成绝对路径，并检查文件存在。"""
    path = os.path.abspath(os.path.expanduser(db_path or default_db_path()))
    if not os.path.isfile(path):
        raise DatabaseNotFoundError(
            f"Mods.sqlite 不存在：{path}\n"
            "提示：先启动一次《文明6》让游戏生成数据库，或用 --db 指定路径。")
    return path


@dataclass
class ProcessInfo:
    pid: int
    exe: str
    image_path: str = ""

    def to_dict(self) -> dict:
        return {"pid": self.pid, "exe": self.exe, "image_path": self.image_path}


def _query_process_image_name(pid: int) -> tuple[str, str]:
    if _kernel32 is None or pid <= 0:
        return "", ""
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        return "", ""
    try:
        capacity = ctypes.c_ulong(2048)
        buffer = ctypes.create_unicode_buffer(capacity.value)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(capacity)):
            image_path = buffer.value
            return os.path.basename(image_path), image_path
        return "", ""
    finally:
        _kernel32.CloseHandle(handle)


def iter_processes() -> list[ProcessInfo]:
    """枚举当前进程（EnumProcesses + QueryFullProcessImageNameW，普通权限即可）。"""
    if _psapi is None:
        return []
    capacity = 4096
    buffer = (ctypes.c_ulong * capacity)()
    needed = ctypes.c_ulong(0)
    if not _psapi.EnumProcesses(buffer, ctypes.sizeof(buffer), ctypes.byref(needed)):
        return []
    count = needed.value // ctypes.sizeof(ctypes.c_ulong)
    processes: list[ProcessInfo] = []
    for index in range(count):
        pid = int(buffer[index])
        if pid <= 0:
            continue
        exe, image_path = _query_process_image_name(pid)
        if exe:
            processes.append(ProcessInfo(pid=pid, exe=exe, image_path=image_path))
    return processes


def running_game_processes() -> list[ProcessInfo]:
    """返回正在运行的《文明6》/启动器进程（用于写前拒绝判断）。"""
    return [process for process in iter_processes()
            if process.exe.lower() in GAME_PROCESS_NAMES]


def _require_game_closed() -> None:
    processes = running_game_processes()
    if processes:
        detail = ", ".join(f"{process.exe}(PID {process.pid})" for process in processes)
        raise GameRunningError(
            "检测到《文明6》/启动器正在运行：" + detail + "\n"
            "游戏运行时会持续写入 Mods.sqlite，本工具拒绝修改。请完全退出游戏后再试"
            "（本工具不启动、不结束游戏进程，请手动退出）。")


# ---------------------------------------------------------------------------
# 数据库连接与读取
# ---------------------------------------------------------------------------
def _sqlite_ro_uri(path: str) -> str:
    """构造只读 SQLite URI（路径含空格/中文/撇号时必须百分号编码）。"""
    posix = os.path.abspath(path).replace("\\", "/")
    return "file:" + urllib.parse.quote(posix, safe="/:") + "?mode=ro"


def _validate_schema(connection: sqlite3.Connection) -> None:
    names = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = [table for table in CORE_TABLES if table not in names]
    if missing:
        raise DatabaseNotFoundError(
            "不是有效的《文明6》Mods.sqlite（缺少表：" + ", ".join(missing) + "）")


def connect_readonly(db_path: str | None = None) -> sqlite3.Connection:
    """以只读方式连接 Mods.sqlite（sqlite URI mode=ro + PRAGMA query_only），并校验表结构。"""
    path = resolve_db_path(db_path)
    try:
        connection = sqlite3.connect(_sqlite_ro_uri(path), uri=True, timeout=5.0)
    except sqlite3.Error as exc:
        raise DatabaseNotFoundError(f"无法以只读方式打开 {path}：{exc}") from exc
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
    except sqlite3.DatabaseError as exc:
        connection.close()
        raise DatabaseNotFoundError(
            f"读取 {path} 失败（可能不是 SQLite 数据库）：{exc}") from exc
    return connection


@dataclass
class ModInfo:
    """一个已扫描 Mod 的信息（来自 Mods + ScannedFiles + ModProperties + LocalizedText）。"""

    row_id: int
    mod_id: str
    version: int
    name: str
    name_raw: str
    name_resolved: bool
    modinfo_path: str
    source: str
    origin: str = ""
    enabled: bool = False
    in_current_group: bool = False
    disabled: int | None = None

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "mod_id": self.mod_id,
            "version": self.version,
            "name": self.name,
            "name_raw": self.name_raw,
            "name_resolved": self.name_resolved,
            "modinfo_path": self.modinfo_path,
            "source": self.source,
            "origin": self.origin,
            "enabled": self.enabled,
            "in_current_group": self.in_current_group,
            "disabled": self.disabled,
        }


@dataclass
class ModGroupInfo:
    """Mod 组（一套 MOD 启用配置）。"""

    row_id: int
    name: str
    can_delete: bool
    selected: bool
    sort_index: int
    item_count: int
    enabled_count: int
    disabled_count: int

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "name": self.name,
            "can_delete": self.can_delete,
            "selected": self.selected,
            "sort_index": self.sort_index,
            "item_count": self.item_count,
            "enabled_count": self.enabled_count,
            "disabled_count": self.disabled_count,
        }


@dataclass
class ModsSnapshot:
    """Mods.sqlite 的一次完整只读快照。"""

    db_path: str
    db_size: int
    db_mtime: str
    user_version: int
    mods: list[ModInfo]
    groups: list[ModGroupInfo]
    selected_group_ids: list[int]
    group_items: dict[tuple[int, int], int] = field(default_factory=dict)

    @property
    def enabled_mods(self) -> list[ModInfo]:
        return [mod for mod in self.mods if mod.enabled]

    def mod_by_row_id(self, row_id: int) -> ModInfo | None:
        for mod in self.mods:
            if mod.row_id == row_id:
                return mod
        return None

    def group_by_row_id(self, row_id: int) -> ModGroupInfo | None:
        for group in self.groups:
            if group.row_id == row_id:
                return group
        return None


def _normalize_mod_id(value: str) -> str:
    return (value or "").strip().strip("{}").upper()


def _resolve_name(raw: str, localized: dict[str, str]) -> tuple[str, bool]:
    if not raw:
        return "", False
    if not raw.upper().startswith("LOC_"):
        return raw, False
    for locale in LOCALE_PRIORITY:
        if locale in localized and localized[locale]:
            return localized[locale], True
    for locale in sorted(localized):
        if localized[locale]:
            return localized[locale], True
    return raw, False


def _classify_source(path: str) -> tuple[str, str]:
    """返回 (source, origin)。source：workshop/official/user。"""
    normalized = (path or "").replace("\\", "/")
    lowered = normalized.lower()
    if "/workshop/content/" in lowered or lowered.startswith("steamapps/workshop"):
        parts = normalized.split("/")
        published_id = ""
        for index, part in enumerate(parts):
            if part == "content" and index + 2 < len(parts):
                published_id = parts[index + 2]
                break
        return "workshop", published_id
    if normalized.startswith(".."):
        segments = [segment for segment in normalized.split("/") if segment not in ("..", "")]
        if len(segments) >= 2:
            return "official", "/".join(segments[:2])
        return "official", segments[0] if segments else ""
    return "user", ""


def _read_mods(connection: sqlite3.Connection) -> list[ModInfo]:
    rows = connection.execute(
        "SELECT m.ModRowId AS row_id, m.ModId AS mod_id, m.Version AS version,"
        "       sf.Path AS modinfo_path "
        "FROM Mods m JOIN ScannedFiles sf ON sf.ScannedFileRowId = m.ScannedFileRowId "
        "ORDER BY m.ModRowId").fetchall()
    name_props: dict[int, str] = {}
    for row in connection.execute(
            "SELECT ModRowId, Value FROM ModProperties WHERE Name='Name'"):
        name_props[int(row["ModRowId"])] = row["Value"] or ""
    localized_by_tag: dict[tuple[int, str], dict[str, str]] = {}
    for row in connection.execute(
            "SELECT ModRowId, Tag, Locale, Text FROM LocalizedText"):
        key = (int(row["ModRowId"]), row["Tag"])
        localized_by_tag.setdefault(key, {})[row["Locale"]] = row["Text"]
    mods: list[ModInfo] = []
    for row in rows:
        row_id = int(row["row_id"])
        raw_name = name_props.get(row_id, "")
        localized = localized_by_tag.get((row_id, raw_name), {})
        name, resolved = _resolve_name(raw_name, localized)
        modinfo_path = row["modinfo_path"] or ""
        source, origin = _classify_source(modinfo_path)
        mods.append(ModInfo(
            row_id=row_id,
            mod_id=row["mod_id"] or "",
            version=int(row["version"] or 0),
            name=name or (os.path.basename(modinfo_path) or f"ModRowId {row_id}"),
            name_raw=raw_name,
            name_resolved=resolved,
            modinfo_path=modinfo_path,
            source=source,
            origin=origin,
        ))
    return mods


def _read_groups(connection: sqlite3.Connection) -> list[ModGroupInfo]:
    rows = connection.execute(
        "SELECT g.ModGroupRowId AS row_id, g.Name AS name, g.CanDelete AS can_delete,"
        "       g.Selected AS selected, g.SortIndex AS sort_index,"
        "       (SELECT COUNT(*) FROM ModGroupItems i"
        "        WHERE i.ModGroupRowId = g.ModGroupRowId) AS item_count,"
        "       (SELECT COUNT(*) FROM ModGroupItems i"
        "        WHERE i.ModGroupRowId = g.ModGroupRowId AND COALESCE(i.Disabled,0)=0)"
        "        AS enabled_count,"
        "       (SELECT COUNT(*) FROM ModGroupItems i"
        "        WHERE i.ModGroupRowId = g.ModGroupRowId AND COALESCE(i.Disabled,0)<>0)"
        "        AS disabled_count "
        "FROM ModGroups g ORDER BY g.SortIndex, g.ModGroupRowId").fetchall()
    groups: list[ModGroupInfo] = []
    for row in rows:
        groups.append(ModGroupInfo(
            row_id=int(row["row_id"]),
            name=row["name"] or "",
            can_delete=bool(row["can_delete"]),
            selected=bool(row["selected"]),
            sort_index=int(row["sort_index"] or 0),
            item_count=int(row["item_count"] or 0),
            enabled_count=int(row["enabled_count"] or 0),
            disabled_count=int(row["disabled_count"] or 0),
        ))
    return groups


def load_snapshot(db_path: str | None = None) -> ModsSnapshot:
    """读取完整快照：全部 Mod、Mod 组、当前启用集、组内启用状态。"""
    path = resolve_db_path(db_path)
    connection = connect_readonly(path)
    try:
        mods = _read_mods(connection)
        groups = _read_groups(connection)
        selected_ids = [group.row_id for group in groups if group.selected]
        item_rows = connection.execute(
            "SELECT ModGroupRowId, ModRowId, Disabled FROM ModGroupItems").fetchall()
        group_items: dict[tuple[int, int], int] = {}
        for row in item_rows:
            group_items[(int(row["ModGroupRowId"]), int(row["ModRowId"]))] = \
                int(row["Disabled"] or 0)
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        stat = os.stat(path)
        for mod in mods:
            states = [(group_id, disabled)
                      for (group_id, mod_row), disabled in group_items.items()
                      if mod_row == mod.row_id and group_id in selected_ids]
            mod.disabled = states[0][1] if states else None
            mod.in_current_group = bool(states)
            mod.enabled = any(disabled == 0 for _, disabled in states)
        return ModsSnapshot(
            db_path=path,
            db_size=stat.st_size,
            db_mtime=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(" ", "seconds"),
            user_version=user_version,
            mods=mods,
            groups=groups,
            selected_group_ids=selected_ids,
            group_items=group_items,
        )
    finally:
        connection.close()


def load_mods(db_path: str | None = None) -> list[ModInfo]:
    """列出全部已扫描 Mod 的完整对象（属性访问版；内部/高级用法）。"""
    return load_snapshot(db_path).mods


def list_mods(db_path: str | None = None) -> list[dict]:
    """列出全部已扫描 Mod（JSON 友好的 dict 列表，供 CLI/外部统一入口直接打印）。"""
    return [mod.to_dict() for mod in load_snapshot(db_path).mods]


def load_groups(db_path: str | None = None) -> list[ModGroupInfo]:
    """列出 Mod 组的完整对象（属性访问版）。"""
    return load_snapshot(db_path).groups


def list_groups(db_path: str | None = None) -> list[dict]:
    """列出 Mod 组（JSON 友好的 dict 列表；Selected 为 True 的是当前生效组）。"""
    return [group.to_dict() for group in load_snapshot(db_path).groups]


def get_enabled(db_path: str | None = None) -> dict:
    """当前启用集：Selected=1 的组中 Disabled=0 的 Mod。"""
    snapshot = load_snapshot(db_path)
    selected_groups = [group for group in snapshot.groups if group.selected]
    return {
        "db_path": snapshot.db_path,
        "selected_groups": [group.to_dict() for group in selected_groups],
        "count": len(snapshot.enabled_mods),
        "mods": [mod.to_dict() for mod in snapshot.enabled_mods],
    }


def find_matches(mods: Iterable[ModInfo], query: str, exact: bool = False) -> list[ModInfo]:
    """按 ModId（忽略花括号/大小写）、RowId、显示名、原始名、modinfo 文件名匹配。

    匹配优先级：ModId 精确 → RowId → 名称精确 → 名称/路径片段（exact=True 时不做片段匹配）。
    """
    text = (query or "").strip()
    if not text:
        return []
    mods = list(mods)
    normalized = _normalize_mod_id(text)
    by_id = [mod for mod in mods if _normalize_mod_id(mod.mod_id) == normalized]
    if by_id:
        return by_id
    if text.isdigit():
        by_row = [mod for mod in mods if mod.row_id == int(text)]
        if by_row:
            return by_row
    lowered = text.casefold()
    exact_names = [mod for mod in mods
                   if mod.name.casefold() == lowered or mod.name_raw.casefold() == lowered]
    if exact_names:
        return exact_names
    if exact:
        return []
    return [mod for mod in mods
            if lowered in mod.name.casefold()
            or lowered in mod.name_raw.casefold()
            or lowered in os.path.splitext(os.path.basename(mod.modinfo_path))[0].casefold()
            or lowered in mod.mod_id.casefold()]


def _format_mod_candidates(mods: list[ModInfo], limit: int = 15) -> str:
    lines = []
    for mod in mods[:limit]:
        lines.append(f"  - RowId {mod.row_id} | {mod.name}"
                     f" | ModId {mod.mod_id} | {mod.source}")
    if len(mods) > limit:
        lines.append(f"  ...（共 {len(mods)} 个）")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 备份与还原
# ---------------------------------------------------------------------------
@dataclass
class BackupInfo:
    path: str
    source_db: str
    size: int
    sha256: str
    created_at: str
    verified: bool = True

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "source_db": self.source_db,
            "size": self.size,
            "sha256": self.sha256,
            "created_at": self.created_at,
            "verified": self.verified,
        }


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quick_check(path: str) -> str:
    """对指定 SQLite 文件做 PRAGMA quick_check，返回结果字符串（正常为 ok）。"""
    try:
        connection = sqlite3.connect(_sqlite_ro_uri(path), uri=True, timeout=5.0)
    except sqlite3.Error as exc:
        return f"无法打开：{exc}"
    try:
        _validate_schema(connection)
        return str(connection.execute("PRAGMA quick_check").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        return f"校验异常：{exc}"
    finally:
        connection.close()


def backup_database(db_path: str | None = None,
                    out_dir: str | None = None,
                    label: str | None = None) -> BackupInfo:
    """把 Mods.sqlite 复制为带时间戳的备份并校验（SHA256 + PRAGMA quick_check）。"""
    source = resolve_db_path(db_path)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{label}" if label else ""
    destination_dir = os.path.abspath(out_dir) if out_dir else os.path.dirname(source)
    os.makedirs(destination_dir, exist_ok=True)
    destination = os.path.join(destination_dir,
                               f"{os.path.basename(source)}.bak-{stamp}{suffix}")
    if os.path.exists(destination):
        destination = os.path.join(
            destination_dir,
            f"{os.path.basename(source)}.bak-{stamp}-{os.getpid()}{suffix}")
    try:
        shutil.copy2(source, destination)
    except OSError as exc:
        raise Civ6ModsError(
            f"备份失败：无法复制 {source} → {destination}：{exc}") from exc
    source_size = os.path.getsize(source)
    source_sha = _sha256(source)
    destination_sha = _sha256(destination)
    check = quick_check(destination)
    if (source_size != os.path.getsize(destination) or source_sha != destination_sha
            or check != "ok"):
        try:
            os.remove(destination)
        except OSError:
            pass
        raise VerificationError(
            f"备份校验失败（文件大小/SHA256/quick_check 不一致：{check}）。"
            "游戏可能正在写数据库，请完全退出游戏后重试。")
    return BackupInfo(
        path=destination,
        source_db=source,
        size=os.path.getsize(destination),
        sha256=destination_sha,
        created_at=datetime.datetime.now().isoformat(" ", "seconds"),
    )


def _infer_db_from_backup(backup_path: str) -> str:
    name = os.path.basename(backup_path)
    marker = ".bak-"
    db_name = name.split(marker, 1)[0] if marker in name else "Mods.sqlite"
    return os.path.join(os.path.dirname(os.path.abspath(backup_path)), db_name)


def restore_database(backup_path: str, db_path: str | None = None) -> dict:
    """从备份还原 Mods.sqlite（还原前自动再备份当前库，失败自动回滚）。"""
    _require_game_closed()
    backup_path = os.path.abspath(os.path.expanduser(backup_path))
    if not os.path.isfile(backup_path):
        raise DatabaseNotFoundError(f"备份文件不存在：{backup_path}")
    check = quick_check(backup_path)
    if check != "ok":
        raise VerificationError(
            f"备份文件自身校验失败（quick_check={check}）：{backup_path}")
    target = os.path.abspath(os.path.expanduser(db_path)) if db_path \
        else _infer_db_from_backup(backup_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    safety_backup: BackupInfo | None = None
    if os.path.isfile(target):
        safety_backup = backup_database(target, label="pre-restore")
    try:
        shutil.copy2(backup_path, target)
    except OSError as exc:
        raise Civ6ModsError(
            f"还原失败：无法复制 {backup_path} → {target}：{exc}") from exc
    check_after = quick_check(target)
    if check_after != "ok":
        if safety_backup:
            shutil.copy2(safety_backup.path, target)
        raise VerificationError(
            f"还原后校验失败（quick_check={check_after}），已尝试用安全备份回滚。"
            f"安全备份：{safety_backup.path if safety_backup else '无'}")
    snapshot = load_snapshot(target)
    return {
        "restored_from": backup_path,
        "target_db": target,
        "safety_backup": safety_backup.to_dict() if safety_backup else None,
        "mod_count": len(snapshot.mods),
        "enabled_count": len(snapshot.enabled_mods),
        "sha256": _sha256(target),
        "quick_check": check_after,
    }


# ---------------------------------------------------------------------------
# 启用/禁用
# ---------------------------------------------------------------------------
def _select_target_groups(snapshot: ModsSnapshot,
                          group_ids: list[int] | None) -> list[ModGroupInfo]:
    if group_ids:
        groups = []
        for group_id in group_ids:
            group = snapshot.group_by_row_id(int(group_id))
            if group is None:
                raise Civ6ModsError(
                    f"指定的 Mod 组不存在：ModGroupRowId={group_id}"
                    "（可用 groups 子命令查看）")
            groups.append(group)
        return groups
    selected = [group for group in snapshot.groups if group.selected]
    if not selected:
        raise Civ6ModsError("数据库中没有 Selected=1 的 Mod 组，无法确定启用集；"
                            "请先在游戏内选择 MOD 配置，或用 --group 指定组。")
    return selected


def set_mod_enabled(db_path: str | None,
                    query: str,
                    enabled: bool,
                    *,
                    dry_run: bool = False,
                    apply: bool = False,
                    group_ids: list[int] | None = None,
                    exact: bool = False,
                    create_missing: bool = True) -> dict:
    """启用或禁用指定 Mod（按名称/ModId/RowId 匹配）。

    - apply=False（默认）/ dry_run=True：只读计划，不写、不备份；
    - apply=True：先备份，再在事务内修改，最后只读校验；
    - 游戏进程运行时一律拒绝写入（GameRunningError）。
    """
    action = "enable" if enabled else "disable"
    snapshot = load_snapshot(db_path)
    matches = find_matches(snapshot.mods, query, exact=exact)
    if not matches:
        suggestions = difflib.get_close_matches(
            query, [mod.name for mod in snapshot.mods], n=5, cutoff=0.3)
        hint = ("\n相近名称：" + "；".join(suggestions)) if suggestions else ""
        raise ModNotFoundError(f"未找到匹配“{query}”的 Mod。{hint}\n"
                               "可用 list 子命令查看全部 Mod 名称/ModId。")
    if len(matches) > 1:
        raise AmbiguousModError(
            f"“{query}”匹配到 {len(matches)} 个 Mod，请改用更精确的名称、ModId 或 RowId：\n"
            + _format_mod_candidates(matches), matches)
    mod = matches[0]
    groups = _select_target_groups(snapshot, group_ids)
    target_group_ids = {group.row_id for group in groups}

    base_report = {
        "db_path": snapshot.db_path,
        "query": query,
        "action": action,
        "mod": mod.to_dict(),
        "target_groups": [group.to_dict() for group in groups],
        "enabled_before": len(snapshot.enabled_mods),
    }

    if not apply or dry_run:
        changes = []
        for group in groups:
            key = (group.row_id, mod.row_id)
            before = snapshot.group_items.get(key)
            desired = 0 if enabled else 1
            if before is None:
                if create_missing and enabled:
                    changes.append({"group_row_id": group.row_id,
                                    "group_name": group.name,
                                    "action": "would-insert", "before": None,
                                    "after": desired})
                else:
                    changes.append({"group_row_id": group.row_id,
                                    "group_name": group.name,
                                    "action": "would-skip-missing", "before": None,
                                    "after": None})
            elif before == desired:
                changes.append({"group_row_id": group.row_id,
                                "group_name": group.name,
                                "action": "noop", "before": before, "after": desired})
            else:
                changes.append({"group_row_id": group.row_id,
                                "group_name": group.name,
                                "action": "would-update", "before": before,
                                "after": desired})
        base_report.update({
            "applied": False,
            "dry_run": True,
            "changes": changes,
            "backup": None,
            "verified": None,
            "note": "未写入。加 --yes 才会真正修改 Mods.sqlite（会先自动备份）。",
        })
        return base_report

    _require_game_closed()
    backup = backup_database(snapshot.db_path, label=action)

    connection = sqlite3.connect(snapshot.db_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    changes: list[dict] = []
    try:
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("BEGIN IMMEDIATE")
        try:
            for group in groups:
                key = (group.row_id, mod.row_id)
                row = snapshot.group_items.get(key)
                desired = 0 if enabled else 1
                if row is None:
                    if not create_missing:
                        changes.append({"group_row_id": group.row_id,
                                        "group_name": group.name,
                                        "action": "skip-missing", "before": None,
                                        "after": None})
                        continue
                    connection.execute(
                        "INSERT INTO ModGroupItems(ModGroupRowId, ModRowId, Disabled) "
                        "VALUES(?,?,?)", (group.row_id, mod.row_id, desired))
                    changes.append({"group_row_id": group.row_id,
                                    "group_name": group.name,
                                    "action": "insert", "before": None,
                                    "after": desired})
                elif int(row) == desired:
                    changes.append({"group_row_id": group.row_id,
                                    "group_name": group.name,
                                    "action": "noop", "before": int(row),
                                    "after": desired})
                else:
                    connection.execute(
                        "UPDATE ModGroupItems SET Disabled=? "
                        "WHERE ModGroupRowId=? AND ModRowId=?",
                        (desired, group.row_id, mod.row_id))
                    changes.append({"group_row_id": group.row_id,
                                    "group_name": group.name,
                                    "action": "update", "before": int(row),
                                    "after": desired})
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        if "locked" in message or "busy" in message:
            raise DatabaseLockedError(
                "Mods.sqlite 被其他进程锁定（游戏或 Mod 管理器正在写入）。"
                f"备份已保存：{backup.path}；请关闭游戏后重试。") from exc
        raise Civ6ModsError(
            f"写入 Mods.sqlite 失败：{exc}（备份：{backup.path}）") from exc
    finally:
        connection.close()

    # 写后只读校验：目标组内的 Disabled 必须等于期望值
    verify_connection = connect_readonly(snapshot.db_path)
    try:
        states = {}
        for group_id in sorted(target_group_ids):
            row = verify_connection.execute(
                "SELECT Disabled FROM ModGroupItems "
                "WHERE ModGroupRowId=? AND ModRowId=?",
                (group_id, mod.row_id)).fetchone()
            states[group_id] = None if row is None else int(row["Disabled"] or 0)
        expected = 0 if enabled else 1
        verified = bool(states) and all(state == expected for state in states.values())
    finally:
        verify_connection.close()
    if not verified:
        raise VerificationError(
            "写入后校验失败：目标组状态与期望不一致。"
            f"可用备份还原：python civ6_mods.py restore \"{backup.path}\"")
    after_snapshot = load_snapshot(snapshot.db_path)
    target_mod = after_snapshot.mod_by_row_id(mod.row_id)
    base_report.update({
        "applied": True,
        "dry_run": False,
        "changes": changes,
        "backup": backup.to_dict(),
        "verified": True,
        "enabled_after": len(after_snapshot.enabled_mods),
        "mod_after": target_mod.to_dict() if target_mod else None,
        "note": "写入成功并通过只读校验。",
    })
    return base_report


# ---------------------------------------------------------------------------
# 外部统一入口兼容别名（civ6ctl.py 等）
# ---------------------------------------------------------------------------
def enabled_mods(db_path: str | None = None) -> dict:
    """当前启用集（JSON 友好 dict）；等价于 get_enabled()，供统一 CLI 直接打印。"""
    return get_enabled(db_path)


def set_enabled(query: str, enabled: bool, *, allow_running: bool = False,
                db_path: str | None = None, group_ids: list[int] | None = None,
                exact: bool = False) -> dict:
    """启用/禁用指定 Mod 的便捷入口（等价于 apply=True 的 set_mod_enabled）。

    allow_running 仅为外部 CLI 的参数兼容保留：按安全约定，本工具**始终拒绝**在
    游戏/启动器运行时写入 Mods.sqlite，传入 True 也不会绕过该检查。
    """
    _ = allow_running  # 保留参数但不提供绕过能力
    return set_mod_enabled(db_path, query, enabled, apply=True,
                           group_ids=group_ids, exact=exact)


def backup(db_path: str | None = None,
           out_dir: str | None = None,
           label: str | None = None) -> str:
    """备份 Mods.sqlite 并返回备份文件路径（civ6ctl 兼容别名）。"""
    return backup_database(db_path, out_dir=out_dir, label=label).path


def restore(backup_path: str, db_path: str | None = None) -> str:
    """从备份还原 Mods.sqlite 并返回目标数据库路径（civ6ctl 兼容别名）。"""
    return restore_database(backup_path, db_path=db_path)["target_db"]


# ---------------------------------------------------------------------------
# CLI 输出
# ---------------------------------------------------------------------------
def _display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def _truncate(text: str, max_width: int) -> str:
    if _display_width(text) <= max_width:
        return text
    result = ""
    width = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if width + char_width > max_width - 1:
            break
        result += char
        width += char_width
    return result + "…"


def _pad(text: str, width: int) -> str:
    text = _truncate(str(text), width)
    return text + " " * (width - _display_width(text))


def _print_mods(mods: list[ModInfo]) -> None:
    header = (f"{'RowId':>6}  {'ModId':<38} {'状态':<6} {'来源':<9} "
              f"{'名称':<44} 路径")
    print(header)
    print("-" * 130)
    for mod in mods:
        state = "启用" if mod.enabled else ("禁用" if mod.in_current_group else "未入组")
        print(f"{mod.row_id:>6}  {mod.mod_id:<38} {_pad(state, 6)} "
              f"{_pad(mod.source, 9)} {_pad(mod.name, 44)} {mod.modinfo_path}")


def _print_groups(groups: list[ModGroupInfo]) -> None:
    print(f"{'RowId':>6}  {'Selected':<8} {'CanDelete':<9} {'items':>5} "
          f"{'enabled':>7} {'disabled':>8}  名称")
    print("-" * 110)
    for group in groups:
        print(f"{group.row_id:>6}  {str(group.selected):<8} "
              f"{str(group.can_delete):<9} {group.item_count:>5} "
              f"{group.enabled_count:>7} {group.disabled_count:>8}  {group.name}")


def _print_report(report: dict) -> None:
    mod = report["mod"]
    print(f"目标 Mod：RowId {mod['row_id']} | {mod['name']} | ModId {mod['mod_id']} | "
          f"来源 {mod['source']}")
    print(f"操作：{'启用' if report['action'] == 'enable' else '禁用'}；目标组："
          + "、".join(f"{group['row_id']}:{group['name']}"
                      for group in report["target_groups"]))
    print("实际变更：" if report.get("applied") else "变更计划：")
    for change in report["changes"]:
        print(f"  - 组 {change['group_row_id']}（{change['group_name']}）："
              f"{change['action']}  Disabled {change.get('before')} → "
              f"{change.get('after')}")
    if report.get("applied"):
        backup = report.get("backup") or {}
        print(f"备份：{backup.get('path')}")
        print(f"校验：{'通过' if report.get('verified') else '失败'}；"
              f"当前启用集：{report.get('enabled_before')} → "
              f"{report.get('enabled_after')}")
    else:
        print(report.get("note", ""))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="以 JSON 输出（便于脚本/AI 解析）")
    parser = argparse.ArgumentParser(
        prog="civ6_mods.py",
        description="读写《文明6》Mods.sqlite：列出 Mod / 组 / 启用集，"
                    "启用或禁用 Mod，备份与还原。",
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python civ6_mods.py list --limit 20\n"
            "  python civ6_mods.py list --source workshop --json\n"
            "  python civ6_mods.py groups\n"
            "  python civ6_mods.py enabled --json\n"
            "  python civ6_mods.py enable \"Enhanced Mod Manager\" --dry-run\n"
            "  python civ6_mods.py disable 197 --yes\n"
            "  python civ6_mods.py backup --label before-test\n"
            "  python civ6_mods.py restore \"Mods.sqlite.bak-20261026-010203\" --yes\n"))
    parser.add_argument("--db", default=None, metavar="PATH",
                        help="Mods.sqlite 路径（默认 %%LOCALAPPDATA%%\\Firaxis Games\\"
                             "Sid Meier's Civilization VI\\Mods.sqlite）")
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="{list,groups,enabled,enable,disable,backup,restore}")

    parser_list = subparsers.add_parser(
        "list", parents=[common], help="列出全部 Mod（RowId/ModId/名称/路径/来源/启用状态）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_list.add_argument("--source", choices=["all", "user", "workshop", "official"],
                             default="all", help="按来源过滤（默认 all）")
    parser_list.add_argument("--state", choices=["all", "enabled", "disabled"],
                             default="all", help="按当前启用状态过滤（默认 all）")
    parser_list.add_argument("--limit", type=int, default=0,
                             help="最多显示 N 个（0 = 全部）")
    parser_list.set_defaults(func=cmd_list)

    parser_groups = subparsers.add_parser(
        "groups", parents=[common], help="列出 Mod 组及每组启用/禁用数量",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_groups.set_defaults(func=cmd_groups)

    parser_enabled = subparsers.add_parser(
        "enabled", parents=[common], help="输出当前启用集（Selected=1 组中 Disabled=0）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_enabled.set_defaults(func=cmd_enabled)

    for name, help_text in (("enable", "启用 Mod（默认只输出计划，--yes 才写入）"),
                            ("disable", "禁用 Mod（默认只输出计划，--yes 才写入）")):
        sub = subparsers.add_parser(
            name, parents=[common], help=help_text,
            formatter_class=argparse.RawDescriptionHelpFormatter)
        sub.add_argument("query", help="Mod 名称 / ModId / RowId（支持片段，精确匹配优先）")
        sub.add_argument("--dry-run", action="store_true", help="只输出计划，不写入（默认行为）")
        sub.add_argument("--yes", action="store_true", help="确认写入（会先自动备份）")
        sub.add_argument("--exact", action="store_true", help="只做精确匹配，不做片段匹配")
        sub.add_argument("--group", type=int, action="append", default=None,
                         metavar="ROWID",
                         help="指定 Mod 组 RowId（可重复；默认 Selected=1 的组）")
        sub.add_argument("--no-create-missing", action="store_true",
                         help="目标组中不存在该 Mod 时不插入新行（默认启用时插入）")
        sub.set_defaults(func=cmd_set_enabled, enable=(name == "enable"))

    parser_backup = subparsers.add_parser(
        "backup", parents=[common], help="备份 Mods.sqlite 到带时间戳文件并校验",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_backup.add_argument("--out", default=None, metavar="DIR",
                               help="备份输出目录（默认与 Mods.sqlite 同目录）")
    parser_backup.add_argument("--label", default=None,
                               help="备份文件名后缀说明，如 before-test")
    parser_backup.set_defaults(func=cmd_backup)

    parser_restore = subparsers.add_parser(
        "restore", parents=[common], help="从备份还原 Mods.sqlite（先自动备份当前库）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_restore.add_argument("backup_path", help="备份文件路径")
    parser_restore.add_argument("--yes", action="store_true",
                                help="确认还原（覆盖当前 Mods.sqlite）")
    parser_restore.set_defaults(func=cmd_restore)
    return parser


def cmd_list(args) -> int:
    snapshot = load_snapshot(args.db)
    mods = snapshot.mods
    if args.source != "all":
        mods = [mod for mod in mods if mod.source == args.source]
    if args.state == "enabled":
        mods = [mod for mod in mods if mod.enabled]
    elif args.state == "disabled":
        mods = [mod for mod in mods if not mod.enabled]
    if args.limit and args.limit > 0:
        mods = mods[:args.limit]
    if getattr(args, "json", False):
        print(json.dumps({"db_path": snapshot.db_path, "db_size": snapshot.db_size,
                          "count": len(mods),
                          "mods": [mod.to_dict() for mod in mods]},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"数据库：{snapshot.db_path}（{snapshot.db_size} 字节，"
          f"user_version={snapshot.user_version}，快照时间 {snapshot.db_mtime}）")
    print(f"共 {len(snapshot.mods)} 个 Mod，当前列出 {len(mods)} 个"
          f"（启用 {len(snapshot.enabled_mods)} 个）")
    _print_mods(mods)
    return 0


def cmd_groups(args) -> int:
    snapshot = load_snapshot(args.db)
    if getattr(args, "json", False):
        print(json.dumps({"db_path": snapshot.db_path,
                          "groups": [group.to_dict() for group in snapshot.groups]},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"数据库：{snapshot.db_path}")
    print("Mod 组（Selected=True 的组决定当前启用集）：")
    _print_groups(snapshot.groups)
    return 0


def cmd_enabled(args) -> int:
    snapshot = load_snapshot(args.db)
    selected_groups = [group for group in snapshot.groups if group.selected]
    data = {
        "db_path": snapshot.db_path,
        "selected_groups": [group.to_dict() for group in selected_groups],
        "count": len(snapshot.enabled_mods),
        "mods": [mod.to_dict() for mod in snapshot.enabled_mods],
    }
    if getattr(args, "json", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    print(f"数据库：{data['db_path']}")
    print("生效组：" + ("；".join(f"{group['row_id']}（{group['name']}）"
                                 for group in data["selected_groups"]) or "（无）"))
    print(f"启用 Mod：{data['count']} 个")
    _print_mods(snapshot.enabled_mods)
    return 0


def cmd_set_enabled(args) -> int:
    report = set_mod_enabled(
        args.db,
        args.query,
        enabled=bool(args.enable),
        dry_run=bool(args.dry_run),
        apply=bool(args.yes) and not bool(args.dry_run),
        group_ids=args.group,
        exact=bool(args.exact),
        create_missing=not bool(args.no_create_missing),
    )
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    _print_report(report)
    return 0


def cmd_backup(args) -> int:
    info = backup_database(args.db, out_dir=args.out, label=args.label)
    if getattr(args, "json", False):
        print(json.dumps(info.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"备份完成：{info.path}")
    print(f"  大小：{info.size} 字节  校验：SHA256={info.sha256[:16]}…  quick_check=ok")
    return 0


def cmd_restore(args) -> int:
    if not args.yes:
        result = {
            "backup_path": os.path.abspath(os.path.expanduser(args.backup_path)),
            "target_db": os.path.abspath(args.db) if args.db
            else _infer_db_from_backup(args.backup_path),
            "applied": False,
            "note": "未还原。加 --yes 才会覆盖当前 Mods.sqlite（会先自动备份当前库）。",
        }
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"将还原：{result['backup_path']}")
            print(f"目标库：{result['target_db']}")
            print(result["note"])
        return 0
    result = restore_database(args.backup_path, db_path=args.db)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"还原完成：{result['target_db']}")
    print(f"  来源：{result['restored_from']}")
    print(f"  安全备份：{(result['safety_backup'] or {}).get('path')}")
    print(f"  Mod 数：{result['mod_count']}，启用：{result['enabled_count']}，"
          f"quick_check={result['quick_check']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return int(args.func(args))
    except ModNotFoundError as exc:
        print(f"[未找到] {exc}", file=sys.stderr)
        return 2
    except AmbiguousModError as exc:
        print(f"[匹配歧义] {exc}", file=sys.stderr)
        return 2
    except GameRunningError as exc:
        print(f"[拒绝写入] {exc}", file=sys.stderr)
        return 3
    except DatabaseLockedError as exc:
        print(f"[数据库被锁] {exc}", file=sys.stderr)
        return 3
    except VerificationError as exc:
        print(f"[校验失败] {exc}", file=sys.stderr)
        return 4
    except (DatabaseNotFoundError, Civ6ModsError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"[SQLite 错误] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[参数错误] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
