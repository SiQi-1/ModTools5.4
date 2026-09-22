"""Read-only checks for the published knowledge graph and retrieval scenarios."""
from __future__ import annotations
import difflib
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
from contextlib import redirect_stderr, redirect_stdout
from urllib.parse import unquote, urlsplit
from . import skills_search as search


def markdown_links(text: str):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        mark = re.match(r"^\s*(`{3,}|~{3,})", line)
        if mark:
            if fence is None:
                fence = mark[1][0]
            elif fence == mark[1][0]:
                fence = None
            continue
        if fence:
            continue
        line = re.sub(r"`+[^`]*`+", "", line)
        for match in re.finditer(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", line):
            yield number, match[1].strip().strip("<>")


def heading_anchors(text: str) -> set[str]:
    anchors, seen = set(), {}
    for section in search.markdown_sections(text):
        if section['level'] == 0:
            continue
        slug = re.sub(r"[^\w\- ]", "", section['section'].casefold()).replace(" ", "-")
        count = seen.get(slug, 0)
        anchors.add(slug + (f"-{count}" if count else ""))
        seen[slug] = count + 1
    return anchors


def check_knowledge(root: Path | None = None, *, retrieval: bool = True) -> dict:
    root = (root or search.default_skills_root()).resolve()
    errors = []
    def issue(path, code, message, line=1):
        errors.append({'file':str(path), 'line':line, 'code':code, 'message':message})
    if not root.is_dir():
        issue(str(root), 'missing_root', '知识库目录不存在')
        return {'ok':False,'files':0,'errors':errors}
    docs = search.build_index(root)
    graph = {doc['rel']:set() for doc in docs}
    digests = {}
    long_docs = []
    try:
        catalog = search.load_catalog(root)
        if not (root/'catalog.json').is_file():
            issue('catalog.json', 'catalog', '缺少任务目录')
        routes = catalog['routes']
        ids = [r['id'] for r in routes]
        if len(ids) != len(set(ids)):
            issue('catalog.json', 'catalog', '重复任务 id')
        for rel in catalog['always_read'] + [p for r in routes for p in r['read']]:
            if search.read_skill_file(rel, root=root) is None:
                issue('catalog.json', 'missing_required', f'必读文件不可读：{rel}')
    except (ValueError, KeyError, TypeError) as exc:
        issue('catalog.json','catalog',str(exc))
        catalog = {'always_read':[], 'routes':[]}
    # Use the real argument parser: documentation cannot invent commands or flags.
    from modgen.cli import build_parser
    parser = build_parser()
    for doc in docs:
        rel, text = doc['rel'], doc['text']
        path = root / rel
        digest = hashlib.sha256(text.strip().encode()).hexdigest()
        if digest in digests:
            issue(rel,'duplicate',f'正文与 {digests[digest]} 相同')
        digests[digest] = rel
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) >= 200:
            shingles = {tuple(lines[i:i + 3]) for i in range(len(lines) - 2)}
            for other_rel, other_lines, other_shingles in long_docs:
                if min(len(lines), len(other_lines)) / max(len(lines), len(other_lines)) < .85:
                    continue
                common = len(shingles & other_shingles)
                if common / max(1, len(shingles | other_shingles)) < .7:
                    continue
                ratio = difflib.SequenceMatcher(None, lines, other_lines, autojunk=False).ratio()
                if ratio >= .9:
                    issue(rel, 'near_duplicate', f'与 {other_rel} 行级相似度 {ratio:.1%}；请合并或将草稿归档')
            long_docs.append((rel, lines, shingles))
        if re.search(r'-(?:NEW|OLD|COPY)(?:\.|-)',path.name,re.I):
            issue(rel,'draft','重复草稿不得进入发布知识库')
        for number, target in markdown_links(text):
            parts = urlsplit(target)
            if parts.scheme or target.startswith('//'):
                continue
            dest = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            if not dest.is_relative_to(root.parent):
                issue(rel,'external_path',f'本地链接越出仓库：{target}',number)
                continue
            if not dest.exists():
                issue(rel,'broken_link',f'目标不存在：{target}',number)
                continue
            if dest.is_file() and parts.fragment and dest.suffix == '.md':
                if unquote(parts.fragment) not in heading_anchors(search._load_text(dest)):
                    issue(rel,'broken_anchor',f'章节不存在：{target}',number)
            if dest.is_relative_to(root) and dest.suffix == '.md':
                graph[rel].add(dest.relative_to(root).as_posix())
        for number,line in enumerate(text.splitlines(),1):
            if re.search(r'AGENTS?\.md\s*(?:§\d|陷阱\s*\d)|工作流 [A-I](?:\W|$)|reference/modtools-civ',line):
                issue(rel,'stale_rule','失效的旧规则或外部快照引用',number)
            if re.search(r'python(?:\.exe)?\s+(?:check_civ|modcheck|export_modtools|sync_modtools)\.py',line):
                issue(rel,'stale_command','旧外部命令不可作为当前工作流',number)
            command = re.match(r'^\s*python\s+-m\s+modgen\.cli\s+(.+)$',line)
            if command:
                try:
                    with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                        parser.parse_args(shlex.split(command[1],comments=True))
                except SystemExit as exc:
                    if exc.code:
                        issue(rel,'invalid_command',f'CLI 参数无法解析：{command[1]}',number)
                except ValueError:
                    issue(rel,'invalid_command',f'CLI 参数无法解析：{command[1]}',number)
    seeds = ['AGENTS.md','SKILLS_OUTLINE.md'] + catalog['always_read']
    reached, pending = set(), list(seeds)
    while pending:
        rel = pending.pop()
        if rel in reached:
            continue
        reached.add(rel)
        pending.extend(graph.get(rel,set()) - reached)
    for rel in graph.keys() - reached:
        issue(rel,'unindexed','文档无法从知识入口/INDEX 到达')
    for name in ['RULES.md','WORKFLOW.md']:
        if not (root/name).is_file():
            issue(name,'missing_entry','必读入口不存在')
    scenarios_path = root/'retrieval_cases.json'
    checked = 0
    if retrieval:
        if not scenarios_path.is_file():
            issue('retrieval_cases.json','missing_cases','缺少真实检索质量用例')
        else:
            try:
                cases = json.loads(scenarios_path.read_text(encoding='utf-8'))
                for case in cases:
                    checked += 1
                    results = search.search_skills(case['query'],root=root,limit=case.get('top',3))
                    if case['expected'] not in [r['rel'] for r in results]:
                        issue('retrieval_cases.json','retrieval',f"{case['query']} 未在前 {case.get('top',3)} 条命中 {case['expected']}")
            except (ValueError,KeyError,TypeError) as exc:
                issue('retrieval_cases.json','cases',str(exc))
    return {'ok':not errors,'files':len(docs),'retrieval_cases':checked,'errors':errors}
