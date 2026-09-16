"""modgen → ModTools 桥（复用同一套实现，防止两份漂移）。

`modgen/` 与 `ModTools_5_4/` 始终同包分发（build_release.ps1 同时复制两者），
因此 modgen 直接复用 ModTools 侧的：
- `ModTools_5_4.db.loc_text`      —— LOC 嵌套解析（单一实现）
- `ModTools_5_4.db.search_index`  —— BM25 检索层（领域词典 + 倒排索引）

若 modgen 被单独拷贝到别处运行，本模块会把仓库根加入 sys.path 再导入。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = str(Path(__file__).resolve().parents[1])


def _load(module_name: str):
    try:
        module = __import__(f"ModTools_5_4.db.{module_name}", fromlist=[module_name])
    except ImportError:
        if _REPO_ROOT not in sys.path:
            sys.path.insert(0, _REPO_ROOT)
        module = __import__(f"ModTools_5_4.db.{module_name}", fromlist=[module_name])
    return module


def _load_project_module(module_name: str):
    try:
        module = __import__(f"ModTools_5_4.project.{module_name}", fromlist=[module_name])
    except ImportError:
        if _REPO_ROOT not in sys.path:
            sys.path.insert(0, _REPO_ROOT)
        module = __import__(f"ModTools_5_4.project.{module_name}", fromlist=[module_name])
    return module


def _load_top_module(module_name: str):
    try:
        module = __import__(f"ModTools_5_4.{module_name}", fromlist=[module_name])
    except ImportError:
        if _REPO_ROOT not in sys.path:
            sys.path.insert(0, _REPO_ROOT)
        module = __import__(f"ModTools_5_4.{module_name}", fromlist=[module_name])
    return module


loc_text = _load("loc_text")
search_index = _load("search_index")
civ6proj_generator = _load_project_module("civ6proj_generator")
custom_files = _load_project_module("custom_files")
skills_search = _load_top_module("skills_search")

DEFAULT_LANGUAGE = loc_text.DEFAULT_LANGUAGE
LOC_REF_PATTERN = loc_text.LOC_REF_PATTERN
contains_ref = loc_text.contains_ref
looks_like_tag = loc_text.looks_like_tag
make_sqlite_fetcher = loc_text.make_sqlite_fetcher
resolve_tag = loc_text.resolve_tag
resolve_tag_or_original = loc_text.resolve_tag_or_original
resolve_text = loc_text.resolve_text
TERM_MAP = search_index.TERM_MAP


def fetcher_for(conn: Optional[Any], language: str = DEFAULT_LANGUAGE):
    """取该连接的 tag → 文本 查询函数（内置缓存；批量解析请在循环外复用同一 fetcher）。"""
    if conn is None:
        return None
    return make_sqlite_fetcher(conn, language=language)


def resolve_value(conn: Optional[Any], value: object, language: str = DEFAULT_LANGUAGE) -> str:
    """tag 或含 `{LOC_...}` 的文本 → 中文（统一入口，失败返回原文）。"""
    text = str(value or "").strip()
    if not text or conn is None:
        return text
    fetch = fetcher_for(conn, language)
    if looks_like_tag(text):
        return resolve_tag_or_original(fetch, text)
    if contains_ref(text):
        return resolve_text(fetch, text)
    return text


def search_objects_bm25(
    game_conn: Any,
    loc_conn: Optional[Any],
    object_types: dict[str, dict[str, Any]],
    keyword: str,
    *,
    category: Optional[str] = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """BM25 对象检索（与 GUI 能力实现搜索同一实现与排序）。

    中文查询经领域词典扩展出英文 Type 片段作为降权加分项，
    因此"贸易路线加产出"这类中文描述能命中 MODIFIER_*_TRADE_ROUTE_YIELD_* 实现。
    """
    kw = str(keyword or "").strip()
    if not kw:
        return []
    index = search_index.get_index(game_conn, loc_conn, object_types)
    boost_terms = list(search_index.iter_matched_terms(kw))
    return index.search(
        kw,
        category=category,
        limit=limit,
        boost_query=" ".join(boost_terms),
        boost_weight=search_index.EXPANSION_BOOST_WEIGHT,
    )
