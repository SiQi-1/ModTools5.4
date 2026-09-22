"""Shared, Qt-free retrieval: task routes, section BM25, Chinese bigrams."""
from __future__ import annotations
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

SEARCH_EXTS = {".md"}
MAX_SNIPPET_CHARS = 160
_index_cache: dict[str, Any] = {}


def default_skills_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        portable = Path(sys.executable).resolve().parent / "skills"
        if portable.exists():
            return portable
    return Path(__file__).resolve().parents[1] / "skills"


def _is_dev_artifact(rel_path: str) -> bool:
    return any(p.startswith("_") for p in str(rel_path).replace("\\", "/").split("/"))


def _safe_path(root: Path, rel: str) -> Path | None:
    clean = str(rel).replace("\\", "/")
    if not clean or clean.startswith("/") or ":" in clean or ".." in clean.split("/"):
        return None
    target = (root / clean).resolve()
    if not target.is_relative_to(root.resolve()) or _is_dev_artifact(clean):
        return None
    return target


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return ""


def _terms(text: str) -> list[str]:
    tokens = []
    for part in re.findall(r"[A-Za-z][A-Za-z0-9_]*|[\u3400-\u9fff]+|[0-9]+", text):
        if re.fullmatch(r"[\u3400-\u9fff]+", part):
            tokens.extend([part[i:i + 2] for i in range(len(part) - 1)] if len(part) > 1 else [part])
        else:
            tokens.append(part.casefold())
            pieces = re.sub(r"([a-z])([A-Z])", r"\1 \2", part).replace("_", " ").casefold().split()
            if len(pieces) > 1:
                tokens.extend(pieces)
    return tokens


def markdown_sections(text: str) -> list[dict[str, Any]]:
    """Leaf heading blocks with ancestor titles; fenced code isn't a heading."""
    lines = text.splitlines()
    headings = []
    fence = None
    for i, line in enumerate(lines):
        mark = re.match(r"^\s*(`{3,}|~{3,})", line)
        if mark:
            if fence is None:
                fence = mark[1][0]
            elif fence == mark[1][0]:
                fence = None
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match and fence is None:
            headings.append((i, len(match[1]), match[2]))
    if not headings or headings[0][0] != 0:
        headings.insert(0, (0, 0, "正文"))
    result, stack = [], []
    for k, (start, level, title) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        end = headings[k + 1][0] if k + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start:end])
        searchable = re.sub(r"(?m)^\s*python\s+-m\s+modgen\.cli\s+skill\b.*$", "", body)
        result.append({"section": title, "title": " / ".join(s[1] for s in stack),
                       "level": level, "start_line": start + 1, "end_line": end,
                       "text": body, "terms": Counter(_terms(searchable))})
    return result


def load_catalog(root: Path) -> dict[str, Any]:
    path = root / "catalog.json"
    if not path.exists():
        return {"version": 1, "always_read": [], "routes": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("skills/catalog.json 版本或结构无效")
    def strings(value):
        return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)
    if not strings(data.get("always_read")) or not isinstance(data.get("routes"), list):
        raise ValueError("catalog 的 always_read/routes 必须是列表")
    for route in data["routes"]:
        if (not isinstance(route, dict) or not isinstance(route.get("id"), str)
                or not route["id"].strip() or not strings(route.get("aliases"))
                or not route["aliases"] or not strings(route.get("read")) or not route["read"]):
            raise ValueError("catalog 的每个任务需要 id、aliases、read")
    for rel in data["always_read"] + [p for r in data["routes"] for p in r["read"]]:
        path = _safe_path(root, rel)
        if path is None or path.suffix != ".md":
            raise ValueError(f"catalog 必读路径非法：{rel}")
    return data


def _alias_matches(alias: str, query: str) -> bool:
    if re.search(r"[\u3400-\u9fff]", alias):
        return re.sub(r"\s+", "", alias.casefold()) in re.sub(r"\s+", "", query.casefold())
    suffix = "" if alias.endswith("_") else r"(?![A-Za-z0-9_])"
    return bool(re.search(r"(?<![A-Za-z0-9_])" + re.escape(alias) + suffix, query, re.I))


def reading_plan(keyword: str, *, root: Path | None = None) -> dict[str, Any]:
    catalog = load_catalog(root or default_skills_root())
    routes = [r for r in catalog["routes"] if any(_alias_matches(a, keyword) for a in r["aliases"])]
    required = list(dict.fromkeys(catalog["always_read"] + [p for r in routes for p in r["read"]]))
    return {"matched": bool(routes), "topics": [r["id"] for r in routes], "required": required,
            "hint": "RULES/WORKFLOW 全文读取；专题读导读与命中章节，参数表和案例按需。未匹配时补充实体、效果、Lua 或 UI 关键词。"}


def _kind(rel: str) -> str:
    if rel in {"RULES.md", "SOURCES.md", "AGENTS.md"} or "checklist" in rel or rel.endswith("code-style.md"):
        return "rule"
    if rel in {"WORKFLOW.md", "SKILLS_OUTLINE.md"} or rel.endswith(("INDEX.md", "pipeline.md")):
        return "workflow"
    if rel.startswith("05-modtools-civ/") or rel == "07-techniques/modifier-techniques.md":
        return "guide"
    if "cases/" in rel or "lua-workshop-" in rel:
        return "example"
    return "reference"


def build_index(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    paths = [p for p in sorted(root.rglob("*.md")) if p.is_file()
             and _safe_path(root, p.relative_to(root).as_posix()) is not None]
    key = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
    cached = _index_cache.get(str(root))
    if cached and cached[0] == key:
        return cached[1]
    docs = []
    for path in paths:
        text = _load_text(path)
        if text.strip():
            rel = path.relative_to(root).as_posix()
            docs.append({"rel": rel, "text": text, "kind": _kind(rel), "sections": markdown_sections(text)})
    _index_cache[str(root)] = (key, docs)
    return docs


def search_skills(keyword: str, *, root: Path | None = None, limit: int = 10) -> list[dict[str, Any]]:
    terms = set(_terms(str(keyword or "")))
    if not terms:
        return []
    skills_root = root or default_skills_root()
    docs = build_index(skills_root)
    sections = [s for d in docs for s in d["sections"]]
    if not sections:
        return []
    frequency = Counter(t for s in sections for t in terms.intersection(s["terms"]))
    average = sum(sum(s["terms"].values()) for s in sections) / len(sections) or 1
    preferred = set(reading_plan(keyword, root=skills_root)["required"]) - {"RULES.md", "WORKFLOW.md"}
    results = []
    for doc in docs:
        best = None
        for section in doc["sections"]:
            counts = section["terms"]
            title_terms = set(_terms(section["title"]))
            path_terms = set(_terms(doc["rel"]))
            matches = terms.intersection(counts.keys() | title_terms | path_terms)
            if not matches:
                continue
            score = 0.0
            length = sum(counts.values())
            for term in matches:
                tf = counts.get(term, 0)
                idf = math.log(1 + (len(sections) - frequency[term] + .5) / (frequency[term] + .5))
                score += idf * (tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average)))
                score += idf * (1.5 if term in title_terms else 0)
                score += idf * (.5 if term in path_terms else 0)
            score *= .25 + .75 * len(matches) / len(terms)
            score *= {"rule": 1.3, "workflow": 1.1, "guide": 1.25, "example": .85, "reference": 1}[doc["kind"]]
            if doc["rel"] in preferred:
                score *= 1.35
            if best is None or score > best[0]:
                best = (score, section, bool(terms & path_terms))
        if best:
            score, section, name_hit = best
            snippets = [line.strip()[:MAX_SNIPPET_CHARS] for line in section["text"].splitlines()
                        if terms.intersection(_terms(line)) and not re.match(r"^\s*python\s+-m\s+modgen\.cli\s+skill\b", line)][:3]
            results.append({"rel": doc["rel"], "score": round(score, 3), "name_hit": name_hit,
                            "snippets": snippets, "kind": doc["kind"], "title": section["title"],
                            "section": section["section"], "start_line": section["start_line"], "end_line": section["end_line"]})
    results.sort(key=lambda r: (-r["score"], r["rel"]))
    return results[:max(1, limit)]


def read_skill_file(rel_path: str, *, root: Path | None = None, section: str | None = None) -> str | None:
    target = _safe_path(root or default_skills_root(), rel_path)
    if target is None or target.suffix != ".md" or not target.is_file():
        return None
    text = _load_text(target)
    if not section:
        return text
    blocks = markdown_sections(text)
    for i, block in enumerate(blocks):
        if block["section"].casefold() == section.casefold():
            end = next((b["start_line"] - 1 for b in blocks[i + 1:] if b["level"] <= block["level"]), len(text.splitlines()))
            return "\n".join(text.splitlines()[block["start_line"] - 1:end])
    return None
