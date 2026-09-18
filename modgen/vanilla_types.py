"""原版 ModifierType 快照加载（modgen 侧；与 GUI 共用同一份数据文件）。

数据文件：``ModTools_5_4/data/vanilla_modifier_types.json``
生成方式：``python -m modgen.tools.extract_vanilla_modifier_types``

判定规则见 GUI 侧同源实现 ``ModTools_5_4/project/vanilla_modifier_types.py``；
两处只共享**数据文件**，逻辑各自保持极薄，避免 modgen 反向依赖 GUI 包。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "ModTools_5_4" / "data" / "vanilla_modifier_types.json"
SNAPSHOT_FORMAT = "MODTOOLS54_VANILLA_MODIFIER_TYPES"

SOURCE_NEW = "new"
SOURCE_VANILLA = "vanilla"


@lru_cache(maxsize=1)
def load_vanilla_modifier_types() -> dict[str, tuple[str, str]]:
    """``{ModifierType: (CollectionType, EffectType)}``；文件缺失/损坏返回空 dict。"""
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict) or payload.get("format") != SNAPSHOT_FORMAT:
        return {}
    raw = payload.get("modifier_types")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, tuple[str, str]] = {}
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
        result[name] = (collection, effect)
    return result


def snapshot_available() -> bool:
    return bool(load_vanilla_modifier_types())


def needs_registration(
    modifier_type: str,
    source: str = "",
    *,
    snapshot: dict | None = None,
    legacy_known_types=None,
) -> bool:
    """该 ModifierType 是否需要在本工程补 ``Types`` + ``DynamicModifiers`` 行。

    快照缺失时回退旧启发式（“不在本机库类型集合里”即视为新建），
    以保证老环境仍能工作 —— 但此时不应产出硬 ERROR。
    """
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
    if legacy_known_types is None:
        return True
    return name not in legacy_known_types
