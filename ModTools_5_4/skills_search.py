"""Shared, Qt-free retrieval: task routes with must/optional levels and section reads."""
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
PLAN_MAX_KB = 30
DEFAULT_ROUTE_MAX_KB = 13
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


def _read_item(item: Any) -> tuple[str, str | None]:
    if isinstance(item, str):
        return item, None
    if isinstance(item, dict) and isinstance(item.get("path"), str):
        section = item.get("section")
        return item["path"], None if section is None else str(section)
    raise ValueError("catalog 的 read 项必须是路径或 {path, section}")


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
                or not route["aliases"] or not isinstance(route.get("read"), list) or not route["read"]):
            raise ValueError("catalog 的每个任务需要 id、aliases、read")
        level = route.get("level", "must")
        if level not in {"must", "optional"}:
            raise ValueError(f"catalog 任务 {route['id']} 的 level 必须是 must/optional")
        max_kb = route.get("max_kb", DEFAULT_ROUTE_MAX_KB)
        if not isinstance(max_kb, (int, float)) or max_kb <= 0:
            raise ValueError(f"catalog 任务 {route['id']} 的 max_kb 必须是正数")
        if not strings(route.get("optional", [])):
            raise ValueError(f"catalog 任务 {route['id']} 的 optional 必须是路径列表")
        for item in route["read"]:
            rel, section = _read_item(item)
            path = _safe_path(root, rel)
            if path is None or path.suffix != ".md":
                raise ValueError(f"catalog 必读路径非法：{rel}")
            if section is not None:
                found = any(s["section"].casefold() == section.casefold() for s in markdown_sections(_load_text(path)))
                if not found:
                    raise ValueError(f"catalog 章节不存在：{rel} -> {section}")
    for rel in data["always_read"]:
        path = _safe_path(root, rel)
        if path is None or path.suffix != ".md":
            raise ValueError(f"catalog 必读路径非法：{rel}")
    return data


def _alias_matches(alias: str, query: str) -> bool:
    if re.search(r"[\u3400-\u9fff]", alias):
        return re.sub(r"\s+", "", alias.casefold()) in re.sub(r"\s+", "", query.casefold())
    suffix = "" if alias.endswith("_") else r"(?![A-Za-z0-9_])"
    return bool(re.search(r"(?<![A-Za-z0-9_])" + re.escape(alias) + suffix, query, re.I))


def _item_bytes(path: str, section: str | None, root: Path) -> int:
    content = read_skill_file(path, root=root, section=section)
    return len(content.encode()) if content is not None else 0


def reading_plan(keyword: str, *, root: Path | None = None) -> dict[str, Any]:
    """Match task routes and return a must/optional reading plan under a hard budget."""
    skills_root = root or default_skills_root()
    catalog = load_catalog(skills_root)
    routes = [r for r in catalog["routes"] if any(_alias_matches(a, keyword) for a in r["aliases"])]
    items: list[dict[str, Any]] = []
    required: list[str] = []
    optional: list[str] = []
    seen: set[tuple[str, str | None]] = set()
    warnings: list[str] = []

    def add(path: str, section: str | None, level: str, size: int) -> None:
        key = (path, section)
        if key in seen:
            return
        seen.add(key)
        items.append({"path": path, "section": section, "level": level,
                      "bytes": size, "kb": round(size / 1024, 2)})
        if level == "must":
            if path not in required:
                required.append(path)
        elif path not in required and path not in optional:
            optional.append(path)

    allocated = 0
    for rel in catalog["always_read"]:
        size = _item_bytes(rel, None, skills_root)
        add(rel, None, "must", size)
        allocated += size
    demoted: list[str] = []
    for route in routes:
        route_items = []
        for raw in route["read"]:
            path, section = _read_item(raw)
            route_items.append((path, section, _item_bytes(path, section, skills_root)))
        route_bytes = sum(size for _, _, size in route_items)
        max_kb = route.get("max_kb", DEFAULT_ROUTE_MAX_KB)
        level = route.get("level", "must")
        if level == "must" and route_bytes > max_kb * 1024:
            warnings.append(f"任务 {route['id']} 必读 {route_bytes / 1024:.1f} KB 超过 max_kb={max_kb}")
        if level == "must" and allocated + route_bytes > PLAN_MAX_KB * 1024:
            demoted.append(route["id"])
            warnings.append(f"任务 {route['id']} 超出总必读预算 {PLAN_MAX_KB} KB，其必读项改为可选")
            for path, section, size in route_items:
                add(path, section, "optional", size)
        elif level == "must":
            for path, section, size in route_items:
                add(path, section, "must", size)
            allocated += route_bytes
        else:
            for path, section, size in route_items:
                add(path, section, "optional", size)
        for rel in route.get("optional", []):
            add(rel, None, "optional", _item_bytes(rel, None, skills_root))
    must_kb = round(allocated / 1024, 2)
    optional_kb = round(sum(i["bytes"] for i in items if i["level"] == "optional") / 1024, 2)
    hint = ("必读项为 must 级，需全文读取；optional 与建议章节按需读取。"
            "未匹配时补充实体、效果、Lua 或 UI 关键词。")
    if demoted:
        hint += " 本次命中任务过多，已按预算把部分任务降为可选：" + "、".join(demoted) + "。"
    return {"matched": bool(routes), "topics": [r["id"] for r in routes],
            "required": required, "optional": optional, "items": items,
            "must_kb": must_kb, "optional_kb": optional_kb,
            "budget": {"max_kb": PLAN_MAX_KB, "must_kb": must_kb, "ok": must_kb <= PLAN_MAX_KB,
                       "demoted": demoted},
            "warnings": warnings, "hint": hint}


def _kind(rel: str) -> str:
    if rel in {"RULES.md", "SOURCES.md", "AGENTS.md"} or "checklist" in rel or rel.endswith("code-style.md"):
        return "rule"
    if (rel in {"WORKFLOW.md", "SKILLS_OUTLINE.md", "EXTERNAL_SKILLS.md"}
            or rel.endswith(("INDEX.md", "pipeline.md"))):
        return "workflow"
    if (rel.startswith("guides/") or rel.startswith("reference/entities/")
            or (rel.startswith("packages/") and rel.endswith("SKILL.md"))):
        return "guide"
    if "/cases/" in rel or "lua-workshop-" in rel or "/lua-0" in rel or "/lua-1" in rel:
        return "example"
    return "reference"


_KIND_WEIGHTS = {"rule": 1.3, "workflow": 1.1, "guide": 1.25, "example": .85, "reference": 1}


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
            score *= _KIND_WEIGHTS[doc["kind"]]
            if doc["rel"] in preferred:
                score *= 2.2
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
