"""原版 ModifierType 快照（Qt-free，纯标准库）。

**它解决什么问题**
    ModifierType 是否为「游戏已有类型」过去靠查询本机运行缓存
    ``DebugGameplay.sqlite`` 的 ``DynamicModifiers`` 判断。该缓存会把玩家装过的
    所有 Mod 注册的类型一起带进来，于是「库里已有」被误判成「原版已有」，
    生成时不再补 ``Types`` / ``DynamicModifiers`` 行 —— 换一台没装那个 Mod 的
    机器加载即失败。本模块改用随包分发的**原版快照**判定，与「本机装过什么」
    解耦，导出结果可复现。

**数据文件**
    ``ModTools_5_4/data/vanilla_modifier_types.json``
    由 ``python -m modgen.tools.extract_vanilla_modifier_types`` 从游戏自带
    XML（Base/DLC/CTP/Debug/LaunchPad 的 ``<DynamicModifiers><Row>``）提取。

**判定优先级**
    1. 条目标了 ``modifier_type_source == "new"``     → 需要注册（作者强制）
    2. 条目标了 ``modifier_type_source == "vanilla"`` → 不需要注册（作者强制）
    3. 自动：快照可用 → ``modifier_type not in 快照`` 即需要注册
    4. 自动：快照缺失 → 回退旧启发式（本机库 + 工程前缀），并允许上层给出提示
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "vanilla_modifier_types.json"
SNAPSHOT_FORMAT = "MODTOOLS54_VANILLA_MODIFIER_TYPES"

SOURCE_AUTO = ""
SOURCE_NEW = "new"
SOURCE_VANILLA = "vanilla"
VALID_SOURCES = (SOURCE_AUTO, SOURCE_NEW, SOURCE_VANILLA)


@lru_cache(maxsize=1)
def load_vanilla_modifier_types() -> dict[str, dict[str, str]]:
    """读取原版快照；文件缺失或损坏时返回空 dict（调用方据此走回退逻辑）。"""
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict) or payload.get("format") != SNAPSHOT_FORMAT:
        return {}
    raw = payload.get("modifier_types")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name:
            continue
        if isinstance(value, (list, tuple)):
            collection = str(value[0]).strip() if len(value) > 0 and value[0] else ""
            effect = str(value[1]).strip() if len(value) > 1 and value[1] else ""
        elif isinstance(value, dict):
            collection = str(value.get("collection_type") or "").strip()
            effect = str(value.get("effect_type") or "").strip()
        else:
            collection = effect = ""
        result[name] = {"collection_type": collection, "effect_type": effect}
    return result


def snapshot_available() -> bool:
    return bool(load_vanilla_modifier_types())


def _matches_prefix(modifier_type: str, prefixes) -> bool:
    """类型名是否带本工程前缀（两种既有命名风格都要认）。

    作者既有的两种写法：``MODIFIER_SIQI_0055_X``（下划线分隔）与
    ``MODIFIER_SIQI0055_X``（前缀+编号连写）。旧实现只做
    ``startswith(prefix)`` / ``"_PREFIX_" in name``，第二种认不出来。
    这里按 ``_`` 分段，段内允许「前缀 + 纯数字编号」。
    """
    upper = str(modifier_type or "").upper()
    if not upper:
        return False
    for raw in prefixes or ():
        prefix = str(raw or "").strip().upper()
        if not prefix:
            continue
        for segment in upper.split("_"):
            if not segment.startswith(prefix):
                continue
            rest = segment[len(prefix):]
            if rest == "" or rest.isdigit():
                return True
    return False


def resolve_needs_registration(
    modifier_type: str,
    source: str = "",
    *,
    snapshot: dict | None = None,
    legacy_known_types=None,
    prefixes=(),
) -> bool:
    """该 ModifierType 是否需要在本工程补 ``Types`` + ``DynamicModifiers`` 行。"""
    name = str(modifier_type or "").strip()
    if not name:
        return False

    flag = str(source or "").strip().lower()
    if flag == SOURCE_NEW:
        return True
    if flag == SOURCE_VANILLA:
        return False

    snap = load_vanilla_modifier_types() if snapshot is None else snapshot
    if snap:
        return name not in snap

    known = legacy_known_types or ()
    return (name not in known) or _matches_prefix(name, prefixes)


def describe_modifier_type(
    modifier_type: str,
    source: str = "",
    *,
    snapshot: dict | None = None,
    legacy_known_types=None,
    prefixes=(),
) -> str:
    """给 UI 用的判定说明：vanilla / new / forced_new / forced_vanilla / unknown。"""
    flag = str(source or "").strip().lower()
    if flag == SOURCE_NEW:
        return "forced_new"
    if flag == SOURCE_VANILLA:
        return "forced_vanilla"
    snap = load_vanilla_modifier_types() if snapshot is None else snapshot
    if snap:
        name = str(modifier_type or "").strip()
        if not name:
            return "unknown"
        return "vanilla" if name in snap else "new"
    return "legacy"
