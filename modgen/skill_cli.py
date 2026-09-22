"""CLI presentation for shared knowledge retrieval; no GUI dependency."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from .skills import default_skills_root, read_skill_file, search_skills, reading_plan


def run(args) -> int:
    root = Path(args.skills_dir) if args.skills_dir else default_skills_root()
    if not root.is_dir():
        raise ValueError(f'技能库目录不存在：{root}')
    if args.section and not args.file:
        raise ValueError('--section 需要配合 --file')
    if args.check:
        from ModTools_5_4.knowledge_check import check_knowledge
        result = check_knowledge(root)
        if args.json:
            print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            print(f"知识检查：{result['files']} 篇，{result.get('retrieval_cases',0)} 个检索用例，{len(result['errors'])} 个问题")
            for error in result['errors']:
                print(f"{error['file']}:{error['line']} [{error['code']}] {error['message']}")
        return 0 if result['ok'] else 1
    if args.file:
        content = read_skill_file(args.file,root=root,section=args.section)
        if content is None:
            raise ValueError('技能文件或章节不存在，或路径非法')
        print(json.dumps({'file':args.file,'section':args.section,'content':content},ensure_ascii=False) if args.json else content.rstrip('\n'))
        return 0
    if not args.keyword:
        raise ValueError('需要关键词，或 --file / --check')
    plan = reading_plan(args.keyword,root=root)
    result = {'reading_plan':plan}
    if not args.plan:
        result['results'] = search_skills(args.keyword,root=root,limit=args.limit)
        result['count'] = len(result['results'])
    if args.json:
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print('必读：'+' → '.join(plan['required']))
        if not plan['matched']:
            print(plan['hint'])
        for item in result.get('results',[]):
            print(f"{item['rel']}:{item['start_line']}-{item['end_line']} [{item['kind']}] {item['section']} ({item['score']:.1f})")
            for snippet in item['snippets']:
                print('  '+snippet)
        if not args.plan and not result['results']:
            print('未命中。请拆词或查主题 INDEX / search / query；零结果不代表能力不存在。')
    return 0 if args.plan or result.get('results') else 1
