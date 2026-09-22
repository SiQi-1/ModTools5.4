"""Knowledge quality, retrieval behaviour and public CLI regression tests."""
from __future__ import annotations
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ModTools_5_4 import skills_search as search
from ModTools_5_4.knowledge_check import check_knowledge, markdown_links
from modgen.cli import main


class RetrievalBehaviourTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def test_english_boundary_avoids_building_for_ui(self):
        self.put('building.md','# Building\n' + 'Buildings '+ 'building ' * 1000)
        self.put('panel.md','# UI controls\n按钮纹理')
        self.assertEqual([r['rel'] for r in search.search_skills('UI',root=self.root)],['panel.md'])

    def test_repeated_long_reference_does_not_bury_rule(self):
        self.put('RULES.md','# ModifierStrings\n必须填写 preview_text。')
        self.put('large.md','# 参考\n'+('ModifierStrings 是一个表。其他参数说明。\n'*1000))
        self.assertEqual(search.search_skills('ModifierStrings',root=self.root)[0]['rel'],'RULES.md')

    def test_search_usage_examples_do_not_rank_as_answers(self):
        self.put('AGENTS.md', '# 检索\npython -m modgen.cli skill "城市奇观相邻加成"\n')
        self.put('guide.md', '# 奇观与城市相邻\n城市范围和奇观挂载的加成规则。')
        results = search.search_skills('城市奇观相邻加成', root=self.root)
        self.assertEqual([r['rel'] for r in results], ['guide.md'])

    def test_chinese_phrase_and_mixed_spacing(self):
        self.put('textures.md','# 独立 UI 纹理\n按钮背景通过 ui_textures 声明。')
        for query in ['独立UI纹理','独立 UI 纹理','按钮背景','ui_textures']:
            with self.subTest(query=query):
                self.assertEqual(search.search_skills(query,root=self.root)[0]['rel'],'textures.md')

    def test_file_metadata_and_heading_read_exclude_other_sections(self):
        self.put('guide.md','# 指南\n简介\n## 目标\nneedle\n### 子节\nchild\n```python\n# not a heading\n```\n## 其他\nsecret\n')
        result=search.search_skills('needle',root=self.root)[0]
        self.assertEqual(result['section'],'目标')
        self.assertEqual(result['start_line'],3)
        content=search.read_skill_file('guide.md',root=self.root,section=result['section'])
        self.assertIn('child',content)
        self.assertIn('# not a heading',content)
        self.assertNotIn('secret',content)
        self.assertIsNone(search.read_skill_file('guide.md',root=self.root,section='不存在'))

    def test_cache_notices_deletion_and_edits_to_non_newest_file(self):
        old=self.put('old.md','# Old\noldneedle')
        newest=self.put('new.md','# New\nnewneedle')
        os.utime(newest, (2000000000,2000000000))
        self.assertTrue(search.search_skills('oldneedle',root=self.root))
        old.write_text('# Old\nchangedneedle',encoding='utf-8')
        self.assertTrue(search.search_skills('changedneedle',root=self.root))
        old.unlink()
        self.assertFalse(search.search_skills('changedneedle',root=self.root))

    def test_only_published_markdown_is_indexed(self):
        for name in ['run.py','data.json','trace.txt','_draft.md','_archive/notes.md']:
            self.put(name,'needle')
        self.put('guide.md','# needle')
        self.assertEqual([r['rel'] for r in search.search_skills('needle',root=self.root)],['guide.md'])

    def test_read_rejects_absolute_traversal_and_archive(self):
        self.put('guide.md','# Guide')
        self.put('_private.md','private')
        for name in ['../guide.md','/guide.md',str(self.root/'guide.md'),'C:/guide.md','..\\guide.md','_private.md']:
            self.assertIsNone(search.read_skill_file(name,root=self.root),name)

    def test_symlink_cannot_escape_knowledge_root(self):
        with tempfile.TemporaryDirectory() as other:
            outside=Path(other)/'outside.md';outside.write_text('secret',encoding='utf-8')
            try:
                (self.root/'link.md').symlink_to(outside)
            except OSError:
                self.skipTest('本机未授予创建符号链接权限')
            self.assertIsNone(search.read_skill_file('link.md',root=self.root))
            self.assertEqual(search.search_skills('secret',root=self.root),[])


class KnowledgeStructureTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.put('AGENTS.md','# 入口\n[地图](SKILLS_OUTLINE.md)')
        self.put('SKILLS_OUTLINE.md','# 地图\n[参考](guide.md)')
        self.put('RULES.md','# 规则')
        self.put('WORKFLOW.md','# 流程')
        self.put('guide.md','# 指南\n## 实现\n正文')
        self.put('catalog.json',json.dumps({'version':1,'always_read':['RULES.md','WORKFLOW.md'],'routes':[{'id':'ui','aliases':['UI'],'read':['guide.md']}]},ensure_ascii=False))
        self.put('retrieval_cases.json','[]')

    def put(self,name,text):
        (self.root/name).write_text(text,encoding='utf-8')

    def codes(self):
        return {e['code'] for e in check_knowledge(self.root,retrieval=False)['errors']}

    def test_valid_small_knowledge_graph(self):
        self.assertEqual(self.codes(),set())

    def test_links_anchors_orphans_and_old_workflows_are_rejected(self):
        self.put('guide.md','# 指南\n[坏链接](missing.md)\n[坏标题](RULES.md#none)\nAGENTS.md §5\npython export_modtools.py\npython -m modgen.cli missing-command\n')
        self.put('orphan.md','# 没有索引的资料')
        self.assertTrue({'broken_link','broken_anchor','unindexed','stale_rule','stale_command','invalid_command'} <= self.codes())

    def test_markdown_code_is_not_a_link(self):
        text='# 示例\n```lua\nfoo[x](arg)\n```\n`array[x](arg)`\n[规则](RULES.md)'
        self.assertEqual(list(markdown_links(text)),[(6,'RULES.md')])

    def test_catalog_cannot_hide_missing_required_document(self):
        self.put('catalog.json',json.dumps({'version':1,'always_read':['missing.md'],'routes':[]}))
        self.assertIn('missing_required',self.codes())

    def test_malformed_and_escaping_catalog_are_reported(self):
        for data in [{'version':1,'always_read':None,'routes':[]},{'version':1,'always_read':['../outside.md'],'routes':[]}]:
            self.put('catalog.json',json.dumps(data))
            self.assertIn('catalog',self.codes())

    def test_duplicate_documents_are_reported(self):
        self.put('copy.md',(self.root/'guide.md').read_text(encoding='utf-8'))
        self.assertIn('duplicate',self.codes())

    def test_near_duplicate_long_reference_is_reported(self):
        original = "# Reference\n" + "\n".join(f"独立资料条目 {i}" for i in range(220))
        self.put('guide.md', original)
        self.put('variant.md', original.replace('条目 200', '条目 200 已改写'))
        self.assertIn('near_duplicate', self.codes())

    def test_ranking_failure_fails_the_quality_gate(self):
        self.put('retrieval_cases.json',json.dumps([{'query':'no-such-needle','expected':'guide.md','top':1}]))
        result=check_knowledge(self.root)
        self.assertFalse(result['ok'])
        self.assertIn('retrieval',{e['code'] for e in result['errors']})


class PublishedKnowledgeTest(unittest.TestCase):
    def test_published_graph_and_real_queries(self):
        result=check_knowledge()
        self.assertTrue(result['ok'],json.dumps(result['errors'],ensure_ascii=False,indent=2))
        self.assertGreaterEqual(result['retrieval_cases'],15)

    def test_combined_task_requires_lua_ui_and_modifiers(self):
        plan=search.reading_plan('Lua UI 与 EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER')
        self.assertTrue({'lua','ui','modifiers'} <= set(plan['topics']))
        self.assertEqual(len(plan['required']),len(set(plan['required'])))
        self.assertIn('RULES.md',plan['required'])
        self.assertIn('WORKFLOW.md',plan['required'])

    def test_unknown_task_keeps_global_rules_and_reports_unmatched(self):
        result=search.reading_plan('xyzzyquux')
        self.assertFalse(result['matched'])
        self.assertEqual(result['required'],['RULES.md','WORKFLOW.md'])

    def call_cli(self,*args):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=main(['skill',*args])
        return code,stdout.getvalue(),stderr.getvalue()

    def test_cli_plan_search_and_section_json(self):
        code,out,_=self.call_cli('UI','--plan','--json')
        self.assertEqual(code,0)
        self.assertIn('05-modtools-civ/ui-assets.md',json.loads(out)['reading_plan']['required'])
        code,out,_=self.call_cli('独立UI纹理','--json','--limit','1')
        result=json.loads(out)
        self.assertEqual(result['count'],1)
        item=result['results'][0]
        self.assertEqual(item['rel'],'05-modtools-civ/ui-assets.md')
        code,out,_=self.call_cli('--file',item['rel'],'--section',item['section'],'--json')
        self.assertEqual(code,0)
        self.assertTrue(json.loads(out)['content'])

    def test_cli_bad_section_and_bad_mode_fail(self):
        for args in [('UI','--section','无文件'),('--file','RULES.md','--section','无此章节')]:
            code,_,error=self.call_cli(*args)
            self.assertEqual(code,1)
            self.assertIn('ERROR',error)

    def test_cli_check_uses_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,out,_=self.call_cli('--check','--skills-dir',tmp,'--json')
            self.assertEqual(code,1)
            self.assertFalse(json.loads(out)['ok'])

    def test_cli_without_site_packages(self):
        result=subprocess.run([sys.executable,'-S','-B','-m','modgen.cli','skill','UI','--plan','--json'],cwd=Path(__file__).resolve().parents[1],capture_output=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['reading_plan']['matched'])


if __name__=='__main__':
    unittest.main()
