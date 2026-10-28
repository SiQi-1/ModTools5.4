#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_logs.py —— 《文明6》日志读取、错误扫描与 Modding.log 启用列表解析（纯标准库）

一、日志目录
    %LOCALAPPDATA%\\Firaxis Games\\Sid Meier's Civilization VI\\Logs\\
    可用 --dir 指定其他目录；环境变量 CIV6_LOG_DIR 可覆盖默认值。

二、文件与格式（文件大小、行数是随游戏版本/Mod 组合变化的实测示例，不要当固定值）
    主日志（本模块默认扫描这 5 个）：
      Lua.log        Lua 运行时输出。部分行无时间戳（纯 Lua print），
                     部分为 "[秒.毫秒] 内容"；中文可能因编码问题显示为乱码。
      Database.log   数据库/本地化/配置/正文更新日志，错误最集中（通常占多数）。
                     行格式 "[相对秒.毫秒] [模块] 内容"。
      Modding.log    Mod 扫描、选择、加载日志；含多次
                     "Enabled Mods (in no particular order):" 与
                     "Target Mods (in no particular order):" 块（见下）。
      Startup.log    启动流程日志。行格式 "[YYYY-MM-DD HH:MM:SS]\t内容"（tab 分隔）。
      Engine.log     引擎/内存日志，行格式同 Startup.log。
    其他日志（--all-logs 或 --file 指定时可用）：
      ArtDef.log、UserInterface.log、Localization.log、Renderer.log、FiraxisLive.log、
      GameCoreAppConfig.log、ForgeUI_BLPTextureLoader.log、EOS.log、VisManager.log、
      UIWarnings.csv、Profile.csv。

三、Modding.log 的启用列表结构
    一次游戏启动可能在日志里产生多段配置过程，每段形如：
        [1817096.152] Configuring game content
        [1817096.152] Enabled Mods (in no particular order):
        [1817096.152] <ModId> (<显示名>)
        [1817096.152] <ModId> (<显示名>)
        ...
        [1817096.177] Target Mods (in no particular order):
        [1817096.177] <ModId> (<显示名>)
        ...
      - 若没有任何启用 Mod，会写一行 "[ts] No active mods."；
      - ModId 常见形态：UUID（大小写混合）、带花括号的 UUID、00000000-... 形式的伪 GUID；
      - 显示名可能是本地化标签（LOC_...）；含 [COLOR:...] 标记的文本原样保留；
      - 实测中 Modding.log 可能出现多段 Enabled/Target 块（块数与每块 Mod 数随配置变化）；
        通常**最后一个 Enabled 块**对应最近一次进入对局时的启用集。
      - 注意：日志启用集是“历史快照”，与当前 Mods.sqlite 的启用集可能不同
        （实测曾出现日志块的 Mod 数与数据库启用数不一致）。需要当前状态请用 civ6_mods.py。

四、错误扫描
    内置模式（大小写不敏感，可被 --pattern 替换）：
        ERROR、Error:、failed、Failed to load、Runtime Error、DB Error、
        Lua error、stack traceback、Unable to load
    扫描结果按“去掉时间戳后的消息”聚合：同一条错误重复 N 次只输出一条（count=N），
    保留首次/末次行号与命中的模式标签，便于判断影响面。
    实测命中数随 Mod 组合与游戏版本变化：Database.log 通常最多，其次 Modding.log。

五、主要 API
    default_logs_dir() / resolve_logs_dir(dir=None) / known_logs()
    read_lines(path, encoding="utf-8")
    tail_lines(path, n=50, encoding="utf-8")          从文件尾高效读取 N 行
    scan_error_file(path, patterns=None, ...)        单文件错误扫描（FileErrorReport）
    scan_all_errors(logs_dir, files=None, ...)        多文件错误扫描
    parse_mod_blocks(path)                           解析 Modding.log 中所有 Mod 列表块
    latest_enabled_mods(path)                        取最后一个 Enabled 块
    # 统一入口（civ6ctl.py）兼容别名，均返回 JSON 友好 dict：
    scan_errors(files=None, since_turn=0.0, max_lines=200)
    tail(file_name="Lua.log", lines=50) / paths() / enabled_mods_from_log()

六、CLI
    python civ6_logs.py paths            [--json]              列出已知日志文件与大小/时间
    python civ6_logs.py errors           [--file NAME ...] [--all-logs]
                                         [--pattern REGEX ...] [--max N] [--strict] [--json]
    python civ6_logs.py tail             [--file NAME] [-n N] [--json]
    python civ6_logs.py enabled-mods     [--all-blocks] [--kind enabled|target|all]
                                         [--limit N] [--json]
    示例（PowerShell）：
      python skills/civ6-ai-play/scripts/civ6_logs.py paths
      python skills/civ6-ai-play/scripts/civ6_logs.py errors --max 10
      python skills/civ6-ai-play/scripts/civ6_logs.py errors --file Lua.log --json
      python skills/civ6-ai-play/scripts/civ6_logs.py tail --file Modding.log -n 30
      python skills/civ6-ai-play/scripts/civ6_logs.py enabled-mods --json
    退出码：0 正常；2 目录/文件不存在或参数问题；1 其他错误；
            errors 加 --strict 时，发现任何错误模式返回 1。

七、已知限制
    - 日志时间戳有两套：Modding/Database/Lua 用“游戏进程相对秒”（不是墙钟时间），
      Startup/Engine 用墙钟时间；本模块只原样返回，不做时间换算；
    - 中文日志可能被 Mod/编辑器按 GBK/UTF-8 混写，默认 UTF-8 + errors=replace 读取，
      如出现乱码可用 --encoding gbk 或 gb18030 重试；
    - 日志在游戏重启时会被截断/覆盖，本模块不缓存、不修改任何日志；
    - Modding.log 的 Mod 标题不保证可读（可能是 LOC_ 标签或带 [COLOR:] 标记），
      要拿显示名请配合 civ6_mods.py 查 Mods.sqlite；
    - 错误模式是启发式匹配，可能包含无害的 “failed” 字样，需人工复核上下文。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field

if sys.platform == "win32":
    pass  # 仅用标准库文件 IO，不依赖 Win32 API

DEFAULT_ENCODING = "utf-8"

# 主日志（默认扫描/展示）
MAIN_LOG_FILES = ("Lua.log", "Database.log", "Modding.log", "Startup.log", "Engine.log")
# 其他日志（--all-logs 或 --file 指定时可用）
EXTRA_LOG_FILES = (
    "ArtDef.log", "UserInterface.log", "Localization.log", "Renderer.log",
    "FiraxisLive.log", "GameCoreAppConfig.log", "ForgeUI_BLPTextureLoader.log",
    "EOS.log", "VisManager.log", "UIWarnings.csv", "Profile.csv",
)
LOG_DESCRIPTIONS = {
    "Lua.log": "Lua 运行时输出（含 Mod 加载与脚本错误）",
    "Database.log": "数据库/本地化/配置/正文更新日志（错误最集中）",
    "Modding.log": "Mod 扫描/选择/加载日志（含启用列表块）",
    "Startup.log": "游戏启动流程日志",
    "Engine.log": "引擎/内存日志",
    "ArtDef.log": "美术资源（ArtDef）加载日志",
    "UserInterface.log": "UI 系统日志",
    "Localization.log": "本地化日志",
    "Renderer.log": "渲染器日志",
    "FiraxisLive.log": "Firaxis Live 服务日志",
    "GameCoreAppConfig.log": "GameCore 应用配置日志",
    "ForgeUI_BLPTextureLoader.log": "BLP 贴图加载日志",
    "EOS.log": "Epic Online Services 日志",
    "VisManager.log": "可见性管理器日志",
    "UIWarnings.csv": "UI 警告 CSV（游戏内 UI 警告汇总）",
    "Profile.csv": "玩家档案/统计 CSV",
}

# 内置错误模式（label, 正则）；与任务要求对齐
DEFAULT_ERROR_PATTERNS: tuple[tuple[str, str], ...] = (
    ("error", r"\bERROR\b|Error:"),
    ("failed", r"\bfailed\b"),
    ("failed-to-load", r"Failed to load"),
    ("runtime-error", r"Runtime Error"),
    ("db-error", r"DB Error|DB error"),
    ("lua-error", r"Lua error|Lua Error"),
    ("stack-traceback", r"stack traceback"),
    ("unable-to-load", r"Unable to load"),
)

_TS_BRACKET_RE = re.compile(r"^\s*\[([^\]]*)\]\s*")
_MOD_ENTRY_RE = re.compile(r"^\[[^\]]+\]\s+(?P<mod_id>[0-9A-Fa-f{}-]+)\s+\((?P<title>.*)\)\s*$")
_MOD_BLOCK_HEADING_RE = re.compile(r"(?P<kind>[A-Za-z ]*)Mods \(in no particular order\):")


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class Civ6LogsError(RuntimeError):
    """本模块错误基类。"""


class LogNotFoundError(Civ6LogsError):
    """日志目录/文件不存在。"""


# ---------------------------------------------------------------------------
# 路径与已知文件
# ---------------------------------------------------------------------------
def default_logs_dir() -> str:
    """默认日志目录：%LOCALAPPDATA%\\Firaxis Games\\Sid Meier's Civilization VI\\Logs。"""
    override = os.environ.get("CIV6_LOG_DIR")
    if override:
        return os.path.abspath(override)
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise Civ6LogsError("环境变量 LOCALAPPDATA 不存在，无法定位《文明6》日志目录；"
                            "请用 --dir 显式指定")
    return os.path.join(local_appdata, "Firaxis Games", "Sid Meier's Civilization VI", "Logs")


def resolve_logs_dir(directory: str | None = None) -> str:
    """归一化日志目录并检查存在。"""
    path = os.path.abspath(os.path.expanduser(directory or default_logs_dir()))
    if not os.path.isdir(path):
        raise LogNotFoundError(
            f"日志目录不存在：{path}\n"
            "提示：先启动一次《文明6》生成日志，或用 --dir 指定目录。")
    return path


def log_path(name: str, directory: str | None = None) -> str:
    """已知日志文件名 → 绝对路径（不做存在性检查）。"""
    return os.path.join(resolve_logs_dir(directory), name)


def resolve_log_file(value: str, directory: str | None = None) -> str:
    """把 CLI 的 --file 参数归一成路径：绝对路径/含分隔符按路径处理，否则在日志目录下找。"""
    if os.path.isabs(value) or "/" in value or "\\" in value:
        return os.path.abspath(os.path.expanduser(value))
    return os.path.join(resolve_logs_dir(directory), value)


def known_logs() -> list[dict]:
    """返回已知日志的静态清单（名称、描述、是否主日志）。"""
    entries = []
    for name in MAIN_LOG_FILES:
        entries.append({"name": name, "description": LOG_DESCRIPTIONS.get(name, ""),
                        "main": True})
    for name in EXTRA_LOG_FILES:
        entries.append({"name": name, "description": LOG_DESCRIPTIONS.get(name, ""),
                        "main": False})
    return entries


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{size} B"


def _file_metadata(path: str) -> dict:
    exists = os.path.isfile(path)
    meta = {"path": path, "exists": exists, "size": 0, "size_human": "0 B",
            "mtime": None}
    if exists:
        stat = os.stat(path)
        meta["size"] = stat.st_size
        meta["size_human"] = _human_size(stat.st_size)
        meta["mtime"] = datetime.datetime.fromtimestamp(
            stat.st_mtime).isoformat(" ", "seconds")
    return meta


# ---------------------------------------------------------------------------
# 读取与 tail
# ---------------------------------------------------------------------------
def read_lines(path: str, encoding: str = DEFAULT_ENCODING) -> list[str]:
    """读取整个日志文件为行列表（保留行内空白，去掉行尾换行）。"""
    try:
        with open(path, "r", encoding=encoding, errors="replace") as stream:
            return stream.read().splitlines()
    except OSError as exc:
        raise Civ6LogsError(f"读取日志失败：{path}：{exc}") from exc


def count_lines(path: str) -> int:
    """快速统计行数（按 \n 计数，二进制分块读取，避免解码）。"""
    if not os.path.isfile(path):
        return 0
    lines = 0
    last = b""
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            lines += chunk.count(b"\n")
            last = chunk[-1:]
    if last and last != b"\n":
        lines += 1
    return lines


def tail_lines(path: str, n: int = 50, encoding: str = DEFAULT_ENCODING) -> list[str]:
    """从文件尾高效读取最后 n 行（不需要读入整个大文件）。"""
    if n <= 0:
        return []
    if not os.path.isfile(path):
        raise LogNotFoundError(f"日志文件不存在：{path}")
    block_size = 16384
    with open(path, "rb") as stream:
        stream.seek(0, os.SEEK_END)
        position = stream.tell()
        size = position
        data = b""
        while position > 0 and data.count(b"\n") <= n:
            step = min(block_size, position)
            position -= step
            stream.seek(position)
            data = stream.read(step) + data
    text = data.decode(encoding, errors="replace")
    lines = text.splitlines()
    if position == 0 and size > 0:
        return lines[-n:]
    return lines[-(n + 1):][-n:] if lines else []


# ---------------------------------------------------------------------------
# 时间戳与错误扫描
# ---------------------------------------------------------------------------
def extract_timestamp(line: str) -> str | None:
    """提取行首方括号时间戳（相对秒或墙钟时间），没有则返回 None。"""
    match = _TS_BRACKET_RE.match(line)
    return match.group(1).strip() if match else None


def _numeric_timestamp(timestamp: str | None) -> float | None:
    """相对秒时间戳（如 1945968.177）转 float；墙钟时间等非数字返回 None。"""
    if not timestamp:
        return None
    try:
        return float(timestamp)
    except ValueError:
        return None


def _normalize_message(line: str) -> str:
    """聚合用消息：去掉行首时间戳与首尾空白。"""
    message = _TS_BRACKET_RE.sub("", line.strip(), count=1)
    return message.strip()


@dataclass
class ErrorEntry:
    """一条聚合后的错误（相同消息只保留一条，count 为出现次数）。"""

    message: str
    count: int
    first_line: int
    last_line: int
    labels: list[str] = field(default_factory=list)
    timestamp: str | None = None
    sample: str = ""

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "count": self.count,
            "first_line": self.first_line,
            "last_line": self.last_line,
            "labels": self.labels,
            "timestamp": self.timestamp,
            "sample": self.sample,
        }


@dataclass
class FileErrorReport:
    """单个日志的错误扫描结果。"""

    file: str
    path: str
    exists: bool
    size: int
    match_count: int
    unique_count: int
    errors: list[ErrorEntry] = field(default_factory=list)
    truncated: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "path": self.path,
            "exists": self.exists,
            "size": self.size,
            "match_count": self.match_count,
            "unique_count": self.unique_count,
            "truncated": self.truncated,
            "error": self.error,
            "errors": [entry.to_dict() for entry in self.errors],
        }


def _compile_patterns(patterns=None) -> list[tuple[str, re.Pattern]]:
    if patterns is None:
        patterns = DEFAULT_ERROR_PATTERNS
    compiled = []
    for index, item in enumerate(patterns):
        if isinstance(item, str):
            label, regex = f"custom-{index + 1}", item
        else:
            label, regex = item
        try:
            compiled.append((label, re.compile(regex, re.IGNORECASE)))
        except re.error as exc:
            raise Civ6LogsError(f"错误模式正则非法（{label}：{regex}）：{exc}") from exc
    return compiled


def scan_error_file(path: str,
                    patterns=None,
                    max_entries: int = 50,
                    encoding: str = DEFAULT_ENCODING,
                    since_turn: float = 0.0) -> FileErrorReport:
    """扫描单个日志文件的错误行，按消息聚合。

    patterns: (label, 正则) 元组列表；None 使用内置 DEFAULT_ERROR_PATTERNS；
              也接受纯正则字符串列表（自动编号 custom-1...）。
    max_entries: 每个文件最多返回多少条聚合错误（0 = 不限制）。
    since_turn: >0 时只统计时间戳（游戏相对秒）>= 该值的行；墙钟时间戳不做过滤。
    """
    compiled = _compile_patterns(patterns)
    file_name = os.path.basename(path)
    meta = _file_metadata(path)
    report = FileErrorReport(file=file_name, path=path, exists=meta["exists"],
                             size=meta["size"], match_count=0, unique_count=0)
    if not meta["exists"]:
        report.error = "日志文件不存在"
        return report
    entries: dict[str, ErrorEntry] = {}
    order: list[str] = []
    try:
        with open(path, "r", encoding=encoding, errors="replace") as stream:
            for line_number, raw_line in enumerate(stream, 1):
                line = raw_line.rstrip("\r\n")
                labels = [label for label, pattern in compiled if pattern.search(line)]
                if not labels:
                    continue
                timestamp = extract_timestamp(line)
                if since_turn > 0:
                    numeric = _numeric_timestamp(timestamp)
                    if numeric is not None and numeric < since_turn:
                        continue
                report.match_count += 1
                message = _normalize_message(line)
                entry = entries.get(message)
                if entry is None:
                    sample = line if len(line) <= 400 else line[:400] + "…"
                    entry = ErrorEntry(
                        message=message, count=0, first_line=line_number,
                        last_line=line_number, timestamp=timestamp,
                        sample=sample)
                    entries[message] = entry
                    order.append(message)
                entry.count += 1
                entry.last_line = line_number
                for label in labels:
                    if label not in entry.labels:
                        entry.labels.append(label)
    except OSError as exc:
        report.error = f"读取失败：{exc}"
        return report
    report.unique_count = len(order)
    selected = order if max_entries <= 0 else order[:max_entries]
    report.errors = [entries[message] for message in selected]
    report.truncated = len(selected) < len(order)
    return report


def scan_all_errors(logs_dir: str | None = None,
                    files: list[str] | None = None,
                    patterns=None,
                    max_entries: int = 50,
                    encoding: str = DEFAULT_ENCODING,
                    include_all: bool = False,
                    since_turn: float = 0.0) -> dict:
    """扫描多个日志文件；默认只扫 5 个主日志（存在才扫）。"""
    directory = resolve_logs_dir(logs_dir)
    if files:
        names = files
    else:
        names = list(MAIN_LOG_FILES)
        if include_all:
            names += [name for name in EXTRA_LOG_FILES]
    reports = []
    total_matches = 0
    files_with_matches = 0
    for name in names:
        path = resolve_log_file(name, directory)
        report = scan_error_file(path, patterns=patterns, max_entries=max_entries,
                                 encoding=encoding, since_turn=since_turn)
        reports.append(report)
        total_matches += report.match_count
        if report.match_count:
            files_with_matches += 1
    patterns_used = [label for label, _ in _compile_patterns(patterns)]
    return {
        "logs_dir": directory,
        "patterns": patterns_used,
        "files": [report.to_dict() for report in reports],
        "total_matches": total_matches,
        "files_with_matches": files_with_matches,
    }


# ---------------------------------------------------------------------------
# Modding.log 中的 Mod 列表块
# ---------------------------------------------------------------------------
@dataclass
class ModBlock:
    """Modding.log 中一段 "XXX Mods (in no particular order):" 块。"""

    kind: str
    line_number: int
    heading: str
    timestamp: str | None
    mods: list[dict] = field(default_factory=list)
    note: str = ""

    @property
    def count(self) -> int:
        return len(self.mods)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "line_number": self.line_number,
            "heading": self.heading,
            "timestamp": self.timestamp,
            "count": self.count,
            "note": self.note,
            "mods": self.mods,
        }


def parse_mod_blocks(path: str, encoding: str = DEFAULT_ENCODING) -> list[ModBlock]:
    """解析 Modding.log 中所有 Mod 列表块（Enabled Mods / Target Mods 等）。"""
    if not os.path.isfile(path):
        raise LogNotFoundError(f"日志文件不存在：{path}")
    lines = read_lines(path, encoding=encoding)
    blocks: list[ModBlock] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        heading_match = _MOD_BLOCK_HEADING_RE.search(line)
        if not heading_match:
            index += 1
            continue
        kind = heading_match.group("kind").strip().lower() or "unknown"
        block = ModBlock(kind=kind, line_number=index + 1, heading=line.strip(),
                         timestamp=extract_timestamp(line))
        cursor = index + 1
        while cursor < len(lines):
            entry_match = _MOD_ENTRY_RE.match(lines[cursor])
            if entry_match:
                block.mods.append({
                    "mod_id": entry_match.group("mod_id"),
                    "title": entry_match.group("title").strip(),
                })
                cursor += 1
                continue
            if "No active mods" in lines[cursor]:
                block.note = "No active mods."
                cursor += 1
                continue
            break
        blocks.append(block)
        index = max(cursor, index + 1)
    return blocks


def latest_enabled_mods(path: str, encoding: str = DEFAULT_ENCODING) -> dict:
    """取 Modding.log 中最后一个 "Enabled Mods" 块（最近一次进入对局时的启用集）。"""
    blocks = parse_mod_blocks(path, encoding=encoding)
    enabled_blocks = [block for block in blocks if block.kind == "enabled"]
    meta = _file_metadata(path)
    result = {
        "file": os.path.basename(path),
        "path": path,
        "found": bool(enabled_blocks),
        "block_count": len(enabled_blocks),
        "total_blocks": len(blocks),
        "size": meta["size"],
        "mtime": meta["mtime"],
    }
    if not enabled_blocks:
        result.update({"count": 0, "line_number": None, "timestamp": None,
                       "note": "未找到 Enabled Mods 块", "mods": []})
        return result
    block = enabled_blocks[-1]
    result.update({
        "count": block.count,
        "line_number": block.line_number,
        "timestamp": block.timestamp,
        "note": block.note,
        "mods": block.mods,
    })
    return result


# ---------------------------------------------------------------------------
# 外部统一入口兼容别名（civ6ctl.py 等）
# ---------------------------------------------------------------------------
def paths(directory: str | None = None) -> dict:
    """已知日志文件清单（JSON 友好 dict，供统一 CLI 直接打印）。"""
    resolved = resolve_logs_dir(directory)
    files = []
    for entry in known_logs():
        meta = _file_metadata(os.path.join(resolved, entry["name"]))
        files.append({**entry, **meta})
    return {
        "logs_dir": resolved,
        "count": len(files),
        "existing": sum(1 for entry in files if entry["exists"]),
        "files": files,
    }


def tail(file_name: str = "Lua.log", lines: int = 50, *,
         directory: str | None = None,
         encoding: str = DEFAULT_ENCODING) -> dict:
    """日志尾部 N 行（JSON 友好 dict；等价于 tail_lines 的对外封装）。"""
    path = resolve_log_file(file_name, directory)
    meta = _file_metadata(path)
    if not meta["exists"]:
        raise LogNotFoundError(f"日志文件不存在：{path}")
    selected = tail_lines(path, n=lines, encoding=encoding)
    total = count_lines(path)
    start = total - len(selected) + 1 if selected else total + 1
    return {
        "file": os.path.basename(path),
        "path": path,
        "requested_lines": lines,
        "total_lines": total,
        "start_line": start,
        "lines": selected,
    }


def enabled_mods_from_log(file_name: str = "Modding.log", *,
                          directory: str | None = None,
                          encoding: str = DEFAULT_ENCODING) -> dict:
    """Modding.log 的启用列表（JSON 友好 dict；取最后一个 Enabled 块）。"""
    path = resolve_log_file(file_name, directory)
    if not os.path.isfile(path):
        raise LogNotFoundError(f"日志文件不存在：{path}")
    return latest_enabled_mods(path, encoding=encoding)


def scan_errors(files=None, since_turn: float = 0.0, max_lines: int = 200,
                *, directory: str | None = None, patterns=None,
                encoding: str = DEFAULT_ENCODING,
                include_all: bool = False) -> dict:
    """多文件错误扫描（civ6ctl 兼容入口，返回 JSON 友好 dict）。

    files: None = 5 个主日志；也接受单个文件名或文件名列表；
    since_turn: >0 时只统计时间戳（游戏相对秒）>= 该值的行；
    max_lines: 每个文件最多返回的聚合错误条数。
    单文件扫描请用 scan_error_file()。
    """
    if isinstance(files, str):
        files = [files]
    return scan_all_errors(logs_dir=directory, files=files, patterns=patterns,
                           max_entries=max_lines, encoding=encoding,
                           include_all=include_all, since_turn=since_turn)


# ---------------------------------------------------------------------------
# CLI
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


def cmd_paths(args) -> int:
    directory = resolve_logs_dir(args.dir)
    collected = []
    for entry in known_logs():
        path = os.path.join(directory, entry["name"])
        meta = _file_metadata(path)
        collected.append({**entry, **meta})
    if getattr(args, "json", False):
        print(json.dumps({"logs_dir": directory, "count": len(collected),
                          "files": collected}, ensure_ascii=False, indent=2))
        return 0
    print(f"日志目录：{directory}")
    header = (f"{_pad('文件', 32)} {_pad('主', 3)} {_pad('存在', 5)} "
              f"{'大小':>10}  {_pad('修改时间', 20)} 说明")
    print(header)
    print("-" * 130)
    for entry in collected:
        print(f"{_pad(entry['name'], 32)} {'是' if entry['main'] else '否':<3} "
              f"{'是' if entry['exists'] else '否':<5} "
              f"{entry['size_human']:>10}  {_pad(entry['mtime'] or '-', 20)} "
              f"{_truncate(entry['description'], 50)}")
    existing = sum(1 for entry in collected if entry["exists"])
    print(f"共 {len(collected)} 个已知日志，存在 {existing} 个"
          f"（主日志存在 {sum(1 for entry in collected if entry['exists'] and entry['main'])} 个）")
    return 0


def cmd_errors(args) -> int:
    patterns = None
    if args.pattern:
        patterns = list(args.pattern)
    try:
        data = scan_all_errors(
            logs_dir=args.dir,
            files=args.file,
            patterns=patterns,
            max_entries=args.max,
            encoding=args.encoding,
            include_all=bool(args.all_logs),
        )
    except Civ6LogsError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2
    if getattr(args, "json", False):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"日志目录：{data['logs_dir']}")
        print(f"错误模式：{', '.join(data['patterns'])}")
        for report in data["files"]:
            if not report["exists"]:
                print(f"\n[{report['file']}] 不存在")
                continue
            print(f"\n[{report['file']}] {report['path']}（{report['size']} 字节）")
            if report.get("error"):
                print(f"  读取错误：{report['error']}")
                continue
            print(f"  命中 {report['match_count']} 行，聚合 {report['unique_count']} 条"
                  + ("（已截断）" if report["truncated"] else ""))
            for index, entry in enumerate(report["errors"], 1):
                location = f"L{entry['first_line']}"
                if entry["last_line"] != entry["first_line"]:
                    location += f"-L{entry['last_line']}"
                print(f"   {index:>2}. [{entry['count']}x {location}] "
                      f"{_truncate(entry['message'], 160)}")
        print(f"\n合计命中 {data['total_matches']} 行，涉及 {data['files_with_matches']} 个文件。")
    if args.strict and data["total_matches"] > 0:
        return 1
    return 0


def cmd_tail(args) -> int:
    directory = resolve_logs_dir(args.dir)
    file_name = args.file or "Lua.log"
    path = resolve_log_file(file_name, directory)
    meta = _file_metadata(path)
    if not meta["exists"]:
        print(f"[错误] 日志文件不存在：{path}", file=sys.stderr)
        return 2
    try:
        lines = tail_lines(path, n=args.lines, encoding=args.encoding)
        total = count_lines(path)
    except Civ6LogsError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    start_line = total - len(lines) + 1 if lines else total + 1
    if getattr(args, "json", False):
        print(json.dumps({
            "file": os.path.basename(path),
            "path": path,
            "requested_lines": args.lines,
            "total_lines": total,
            "start_line": start_line,
            "lines": lines,
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"{os.path.basename(path)}（{path}）：最后 {len(lines)}/{total} 行"
          f"（从第 {start_line} 行开始）")
    for offset, line in enumerate(lines):
        print(f"{start_line + offset:>6} | {line}")
    return 0


def cmd_enabled_mods(args) -> int:
    directory = resolve_logs_dir(args.dir)
    path = resolve_log_file(args.file or "Modding.log", directory)
    if not os.path.isfile(path):
        print(f"[错误] 日志文件不存在：{path}", file=sys.stderr)
        return 2
    try:
        blocks = parse_mod_blocks(path, encoding=args.encoding)
    except Civ6LogsError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    latest = latest_enabled_mods(path, encoding=args.encoding)
    if args.all_blocks or args.kind == "all":
        selected = blocks
    elif args.kind == "target":
        selected = [block for block in blocks if block.kind == "target"]
    else:
        selected = [block for block in blocks if block.kind == "enabled"]
        if selected and not args.all_blocks:
            selected = selected[-1:]
    if getattr(args, "json", False):
        payload = {
            "file": os.path.basename(path),
            "path": path,
            "latest": latest,
            "blocks": [block.to_dict() for block in selected],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"日志：{path}")
    if not blocks:
        print("未找到任何 'Mods (in no particular order):' 块。")
        return 0
    print(f"共 {len(blocks)} 个 Mod 列表块；最后一个 Enabled 块："
          f"第 {latest['line_number']} 行，{latest['count']} 个 Mod"
          f"（时间戳 {latest['timestamp'] or '-'}）")
    if latest.get("note"):
        print(f"  备注：{latest['note']}")
    if latest.get("mtime"):
        print(f"  日志修改时间：{latest['mtime']}")
    for block in selected:
        if args.all_blocks or args.kind == "all":
            print(f"\n[{block.kind}] 第 {block.line_number} 行，{block.count} 个 Mod"
                  f"（{block.timestamp or '-'}）"
                  + (f" 备注：{block.note}" if block.note else ""))
        else:
            print(f"\n[{block.kind}] 第 {block.line_number} 行"
                  f"（{block.timestamp or '-'}）")
        limit = args.limit if args.limit and args.limit > 0 else 0
        mods = block.mods[:limit] if limit else block.mods
        for mod in mods:
            print(f"  {mod['mod_id']:<42} {mod['title']}")
        if limit and block.count > limit:
            print(f"  ...（共 {block.count} 个，已显示前 {limit} 个）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="以 JSON 输出（便于脚本/AI 解析）")
    common.add_argument("--dir", default=None, metavar="DIR",
                        help="日志目录（默认 %%LOCALAPPDATA%%\\Firaxis Games\\"
                             "Sid Meier's Civilization VI\\Logs）")
    common.add_argument("--encoding", default=DEFAULT_ENCODING, metavar="ENC",
                        help="日志编码（默认 utf-8；乱码时可试 gbk/gb18030）")
    parser = argparse.ArgumentParser(
        prog="civ6_logs.py",
        description="《文明6》日志读取：列出日志文件、扫描错误、tail 日志尾、"
                    "解析 Modding.log 启用列表。",
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python civ6_logs.py paths\n"
            "  python civ6_logs.py errors --max 10\n"
            "  python civ6_logs.py errors --file Lua.log --json\n"
            "  python civ6_logs.py tail --file Modding.log -n 30\n"
            "  python civ6_logs.py enabled-mods --json\n"))
    subparsers = parser.add_subparsers(
        dest="command", metavar="{paths,errors,tail,enabled-mods}")

    parser_paths = subparsers.add_parser(
        "paths", parents=[common], help="列出已知日志文件（是否存在/大小/修改时间）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_paths.set_defaults(func=cmd_paths)

    parser_errors = subparsers.add_parser(
        "errors", parents=[common], help="按错误模式扫描日志并聚合输出",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_errors.add_argument("--file", action="append", default=None, metavar="NAME",
                               help="只扫描指定日志（可重复；默认 5 个主日志）")
    parser_errors.add_argument("--all-logs", action="store_true",
                               help="扫描全部已知日志（含非主日志）")
    parser_errors.add_argument("--pattern", action="append", default=None, metavar="REGEX",
                               help="自定义错误正则（可重复；给出时替换内置模式）")
    parser_errors.add_argument("--max", type=int, default=50,
                               help="每个文件最多输出多少条聚合错误（0 = 不限制，默认 50）")
    parser_errors.add_argument("--strict", action="store_true",
                               help="发现任何错误模式时返回退出码 1")
    parser_errors.set_defaults(func=cmd_errors)

    parser_tail = subparsers.add_parser(
        "tail", parents=[common], help="输出日志最后 N 行（默认 Lua.log，N=50）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_tail.add_argument("--file", default=None, metavar="NAME",
                             help="日志文件名或路径（默认 Lua.log）")
    parser_tail.add_argument("-n", "--lines", type=int, default=50,
                             help="输出最后 N 行（默认 50）")
    parser_tail.set_defaults(func=cmd_tail)

    parser_mods = subparsers.add_parser(
        "enabled-mods", parents=[common],
        help="解析 Modding.log 的 Mod 列表块（默认最后一个 Enabled 块）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser_mods.add_argument("--file", default=None, metavar="NAME",
                             help="日志文件名或路径（默认 Modding.log）")
    parser_mods.add_argument("--all-blocks", action="store_true",
                             help="输出所有 Mod 列表块（Enabled/Target 全部）")
    parser_mods.add_argument("--kind", choices=["enabled", "target", "all"],
                             default="enabled", help="只输出某类块（默认 enabled）")
    parser_mods.add_argument("--limit", type=int, default=0,
                             help="每个块最多显示 N 个 Mod（0 = 全部）")
    parser_mods.set_defaults(func=cmd_enabled_mods)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return int(args.func(args))
    except LogNotFoundError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2
    except Civ6LogsError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[文件错误] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[参数错误] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
