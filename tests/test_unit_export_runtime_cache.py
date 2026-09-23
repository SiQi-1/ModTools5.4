import os,tempfile,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage
from ModTools_5_4.ui.pages.entity_table_form import UnitReplacesSingleEditor,_SingleRowTableEditor,_ColumnSpec
from tests.sample_project import build_sample_project

class UnitExportRegressionTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.page=WorkspacePage()
 def test_empty_replacement_and_capture_never_become_zero(self):
  for widget,field in [(UnitReplacesSingleEditor(),'ReplacesUnitType'),(_SingleRowTableEditor(table_name='UnitCaptures',hint_text='',owner_key='CapturedUnitType',columns=[_ColumnSpec('BecomesUnitType','BecomesUnitType','template','unit_search')]),'BecomesUnitType')]:
   widget.set_owner_type('UNIT_TEST');widget.set_payload({});self.assertIsNone(widget.export_payload()[field])
   widget.set_payload({field:'UNIT_WARRIOR'});self.assertEqual(widget.export_payload()[field],'UNIT_WARRIOR')
   widget.set_payload({field:None});self.assertIsNone(widget.export_payload()[field])
 def test_custom_tags_export_when_runtime_cache_already_has_them(self):
  self.page._project=build_sample_project();entry=self.page._project.sections['单位'][0]
  entry['subtables']['TypeTags']=[{'Tag':'CLASS_TEST_CACHE_CUSTOM'},{'Tag':'CLASS_MELEE'}]
  with tempfile.TemporaryDirectory() as temp:
   db=Path(temp)/'runtime.sqlite'
   with sqlite3.connect(db) as c:
    c.execute('create table Tags(Tag text,Vocabulary text)');c.execute("insert into Tags values('CLASS_TEST_CACHE_CUSTOM','ABILITY_CLASS')")
   c.close()
   with patch.object(self.page,'_resolve_preview_game_db_path',return_value=db):
    data,ability,text=self.page._build_unit_sql_bundle()
   self.assertIn("('CLASS_TEST_CACHE_CUSTOM', 'ABILITY_CLASS')",data)
   self.assertNotIn("('CLASS_MELEE', 'ABILITY_CLASS')",data)

if __name__=='__main__':unittest.main()
