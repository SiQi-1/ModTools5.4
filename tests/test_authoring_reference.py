import copy
import unittest
import xml.etree.ElementTree as ET

from ModTools_5_4.project.adjacency_reference import reference, audit_project, effective_rows
from ModTools_5_4.project.text_icons import format_text, audit_project as audit_text
from modgen.tools.extract_vanilla_adjacencies import apply_xml, TABLES


class AuthoringReferenceTests(unittest.TestCase):
    def campus(self):
        return {'workspace': {'区域': [{'type':'DISTRICT_TEST',
            'district_replaces':{'ReplacesDistrictType':'DISTRICT_CAMPUS'},
            'adjacencies':reference('DISTRICT_CAMPUS','expansion2')['civ_rows']}]}}

    def test_references_preserve_non_mountain_sources_and_expansion_boundary(self):
        base={r['ID'] for r in reference('DISTRICT_CAMPUS','base')['rules']}
        gs={r['ID'] for r in reference('DISTRICT_CAMPUS','expansion2')['rules']}
        self.assertTrue({'Jungle_Science','District_Science','GBR_Science'} <= base)
        self.assertFalse({'Geothermal_Science','Reef_Science'} & base)
        self.assertTrue({'Geothermal_Science','Reef_Science','Government_Science','Pamukkale_Science'} <= gs)

    def test_missing_bridge_rules_are_reported_but_mountain_override_is_recognized(self):
        p=self.campus();entry=p['workspace']['区域'][0]
        entry['adjacencies']=[{'mode':'custom','id':'Mountain_'+str(i),'yield_type':'YIELD_SCIENCE',
            'yield_change':2,'tiles_required':1,'source_type':'AdjacentTerrain','source_detail':r['AdjacentTerrain']}
            for i,r in enumerate(reference('DISTRICT_CAMPUS')['rules']) if r.get('AdjacentTerrain')]
        report=audit_project(p,'expansion2')
        self.assertFalse(report['ok']);self.assertEqual(len(report['districts'][0]['missing']),7)
        self.assertEqual(len(report['districts'][0]['overridden']),5)

    def test_fully_reused_rules_have_no_gaps_and_subtable_precedence_matches_exporter(self):
        p=self.campus();self.assertTrue(audit_project(p,'expansion2')['ok'])
        p['workspace']['区域'][0]['subtables']={'District_Adjacencies':[]}
        self.assertFalse(audit_project(p,'expansion2')['ok'])
        self.assertEqual(effective_rows(p['workspace']['区域'][0]),[])

    def test_update_delete_cascade_and_unknown_operation(self):
        tables={t:{} for t in TABLES};origins={}
        root=ET.fromstring('''<GameInfo><Adjacency_YieldChanges><Row ID="A" YieldChange="1"/>
          <Update><Where ID="A"/><Set><YieldChange>2</YieldChange></Set></Update></Adjacency_YieldChanges>
          <District_Adjacencies><Row DistrictType="D" YieldChangeId="A"/></District_Adjacencies></GameInfo>''')
        apply_xml(tables,root,'a.xml',origins)
        self.assertEqual(tables['Adjacency_YieldChanges'][('A',)]['YieldChange'],2)
        apply_xml(tables,ET.fromstring('<GameInfo><Adjacency_YieldChanges><Delete ID="A"/></Adjacency_YieldChanges></GameInfo>'),'b.xml',origins)
        self.assertFalse(tables['District_Adjacencies'])
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            apply_xml(tables,ET.fromstring('<GameInfo><Adjacency_YieldChanges><Guess/></Adjacency_YieldChanges></GameInfo>'),'x.xml',origins)

    def test_icons_are_idempotent_preserve_markup_and_leave_names_untouched(self):
        text='+2 食物、+3金币；{1_Amount}[ICON_Science]科技值。[NEWLINE]文化值25%转生产力。'
        result=format_text(text)
        self.assertIn('+2 [ICON_Food]食物',result)
        self.assertIn('{1_Amount}[ICON_Science]科技值',result)
        self.assertEqual(format_text(result),result)
        self.assertEqual(format_text('科技文化中心',role='name'),'科技文化中心')
        self.assertEqual(format_text('文化胜利与科技树'),'文化胜利与科技树')

    def test_project_text_review_excludes_names_and_diplomacy(self):
        p={'workspace':{'领袖':[{'ability_name':'文化之城','ability_description':'+2文化值'}],
                        '文本':{'custom_entries':[{'tag':'LOC_DIPLO_GREETING','text':'我们的文化很独特。'}]}}}
        before=copy.deepcopy(p);report=audit_text(p)
        self.assertEqual(len(report['suggestions']),1)
        self.assertEqual(p,before)


if __name__=='__main__':unittest.main()
