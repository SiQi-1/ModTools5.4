"""本地技能库（仓库根 `skills/`）全文检索引擎 —— GUI/AI 接口与 modgen 单一实现。

背景（2026-08-17）：技能库内迁仓库根 skills/ 后，检索引擎统一放在本模块：
- modgen `skill` 命令经 `modgen/mt_bridge.py` 委托本模块（防漂移）；
- AI 控制接口 `skill` 动作直接调用本模块；
- 纯标准库，无 PyQt；索引按目录 mtime 缓存（3 MB 文本首次构建 ~0.1s）；
- 无中文分词器：查询按空白拆词，逐词做大小写不敏感的**子串匹配**
  （文件名命中权重高、内容词频累加），输出命中文件 + 得分 + 片段。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

SEARCH_EXTS = {".md", ".txt", ".json", ".py"}
MAX_SNIPPET_CHARS = 160
FILENAME_MATCH_WEIGHT = 20

_index_cache: dict[str, Any] = {}


def default_skills_root() -> Path:
    """技能库目录：源码运行 → 仓库根 skills/；打包 exe → exe 同目录 skills/（便携覆盖优先）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        portable = Path(sys.executable).resolve().parent / "skills"
        if portable.exists():
            return portable
    return Path(__file__).resolve().parents[1] / "skills"


def _load_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if b"\x00" in raw[:4096]:
        return ""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="ignore")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _index_key(root: Path) -> tuple[float, str]:
    newest = 0.0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                pass
    return newest, str(root)


def _is_dev_artifact(rel_path: str) -> bool:
    """`_` 前缀的文件/目录 = 技能库的开发产物（生成脚本、中间数据），不参与检索。

    例如 `07-techniques/modifiers/_fix_templates.py`、`_unit_combat_info.txt`、
    `_modifier-city.md.effects.txt` 这类文件本质是"生成知识文档的脚本与中间产物"，
    内容里密密麻麻提到同一个术语，会把真正该读的知识文档挤出检索前列。
    约定：技能库内以 `_` 开头的路径段一律跳过（`__pycache__` 等同理）。
    """
    return any(part.startswith("_") for part in str(rel_path).replace("\\", "/").split("/"))


def build_index(root: Path) -> list[dict[str, Any]]:
    """构建 [(rel_path, text), ...]（按目录 mtime 缓存）。"""
    key = _index_key(root)
    cached = _index_cache.get(str(root))
    if cached is not None and cached[0] == key:
        return cached[1]
    docs: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SEARCH_EXTS:
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.name
        if _is_dev_artifact(rel):
            continue
        text = _load_text(path)
        if not text.strip():
            continue
        docs.append({"rel": rel, "text": text})
    _index_cache[str(root)] = (key, docs)
    return docs


def _terms(keyword: str) -> list[str]:
    text = str(keyword or "").strip()
    if not text:
        return []
    return [term for term in re.split(r"\s+", text) if term]


def _snippets(text: str, terms: list[str], limit: int = 3) -> list[str]:
    hits: list[str] = []
    lowered_terms = [term.casefold() for term in terms]
    for line in text.splitlines():
        if not line.strip():
            continue
        line_lower = line.casefold()
        if any(term in line_lower for term in lowered_terms):
            snippet = line.strip()
            if len(snippet) > MAX_SNIPPET_CHARS:
                snippet = snippet[:MAX_SNIPPET_CHARS] + "…"
            hits.append(snippet)
            if len(hits) >= limit:
                break
    return hits


def search_skills(
    keyword: str,
    *,
    root: Optional[Path] = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """关键词 → [{rel, score, name_hit, snippets}]（按得分降序）。"""
    terms = _terms(keyword)
    if not terms:
        return []
    skills_root = root or default_skills_root()
    if not skills_root.exists():
        return []
    results: list[dict[str, Any]] = []
    for doc in build_index(skills_root):
        rel = doc["rel"]
        text = doc["text"]
        rel_lower = rel.casefold()
        text_lower = text.casefold()
        score = 0.0
        name_hit = False
        for term in terms:
            term_lower = term.casefold()
            if term_lower in rel_lower:
                score += FILENAME_MATCH_WEIGHT
                name_hit = True
            score += text_lower.count(term_lower)
        if score <= 0:
            continue
        results.append(
            {
                "rel": rel,
                "score": score,
                "name_hit": name_hit,
                "snippets": _snippets(text, terms),
            }
        )
    results.sort(key=lambda item: (-item["score"], item["rel"].lower()))
    return results[: max(1, limit)]


def read_skill_file(rel_path: str, *, root: Optional[Path] = None) -> str | None:
    """读取技能文件全文（相对路径，防穿越）；不存在/非法返回 None。"""
    clean = str(rel_path or "").replace("\\", "/").strip().lstrip("/")
    if not clean or clean.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", clean):
        return None
    parts = [part for part in clean.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return None
    skills_root = root or default_skills_root()
    target = skills_root / Path(clean.replace("/", "\\"))
    if not target.exists() or not target.is_file():
        return None
    return _load_text(target)
