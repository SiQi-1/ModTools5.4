"""Agendas must be assigned through HistoricalAgendas, never normal trait bindings."""
import os,re,sqlite3,unittest,xml.etree.ElementTree as ET
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage
from ModTools_5_4.ui.pages.group_workspace import BINDABLE_SECTION_OPTIONS
from sample_project import build_sample_project

class AgendaBindingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=QApplication.instance() or QApplication([])
  cls.page=WorkspacePage()
 def setUp(self):
  self.page._project=build_sample_project()
  self.leader=self.page._project.sections['领袖'][0]
  self.agenda=self.page._project.sections['议程'][0]
  self.lt=self.leader['type'];self.at=self.agenda['type'];self.trait='TRAIT_'+self.at
 def rows(self,sql,table,columns):
  db=sqlite3.connect(':memory:');db.execute(f'create table {table}({columns})')
  for match in re.finditer(r'INSERT INTO '+table+r'\s*\([^;]+?;',sql,re.S):db.executescript(match.group())
  return db.execute('select * from '+table).fetchall()
 def test_explicit_historical_assignment_preserves_agenda_trait_only(self):
  self.leader['bindings']=[{'section':'议程','type':self.at}]
  self.agenda['historical_agendas']={'LeaderType':self.lt}
  leader_sql,_=self.page._build_leader_sql_pair()
  agenda_sql,_=self.page._build_agenda_sql_pair()
  self.assertNotIn((self.lt,self.trait),self.rows(leader_sql,'LeaderTraits','LeaderType,TraitType'))
  self.assertEqual(self.rows(agenda_sql,'HistoricalAgendas','LeaderType,AgendaType'),[(self.lt,self.at)])
  self.assertEqual(self.rows(agenda_sql,'AgendaTraits','AgendaType,TraitType'),[(self.at,self.trait)])
  xmls=self.page._build_group_data_preview_text('领袖','xml')
  for xml_text in xmls.values() if isinstance(xmls,dict) else [xmls]:
   xml=ET.fromstring(xml_text)
   self.assertFalse(any(row.get('TraitType')==self.trait for row in xml.findall('.//LeaderTraits/Row')))
 def test_legacy_assignment_routes_to_historical_and_preserves_regular_binding(self):
  self.agenda.pop('historical_agendas',None)
  for target in [self.at,self.trait]:
   with self.subTest(target=target):
    self.leader['bindings']=[{'section':'议程','type':target},{'section':'单位','type':'UNIT_DEMO'}]
    leader_sql,_=self.page._build_leader_sql_pair();agenda_sql,_=self.page._build_agenda_sql_pair()
    rows=self.rows(leader_sql,'LeaderTraits','LeaderType,TraitType')
    self.assertNotIn((self.lt,self.trait),rows);self.assertIn((self.lt,'TRAIT_UNIT_DEMO'),rows)
    self.assertEqual(self.rows(agenda_sql,'HistoricalAgendas','LeaderType,AgendaType'),[(self.lt,self.at)])
 def test_explicit_owner_overrides_conflicting_legacy_binding(self):
  self.leader['bindings']=[{'section':'议程','type':self.at}]
  self.agenda['historical_agendas']={'LeaderType':'LEADER_OTHER'}
  agenda_sql,_=self.page._build_agenda_sql_pair()
  self.assertEqual(self.rows(agenda_sql,'HistoricalAgendas','LeaderType,AgendaType'),[('LEADER_OTHER',self.at)])
 def test_civilization_cannot_receive_agenda_trait_and_picker_omits_it(self):
  civ=self.page._project.sections['文明'][0]
  civ['trait_bindings']=[{'section':'议程','type':self.at},self.trait,'TRAIT_UNIT_DEMO']
  sql,_=self.page._build_civilization_sql_pair()
  rows=self.rows(sql,'CivilizationTraits','CivilizationType,TraitType')
  self.assertNotIn((civ['type'],self.trait),rows);self.assertIn((civ['type'],'TRAIT_UNIT_DEMO'),rows)
  self.assertNotIn('议程',dict(BINDABLE_SECTION_OPTIONS))

if __name__=='__main__':unittest.main()
