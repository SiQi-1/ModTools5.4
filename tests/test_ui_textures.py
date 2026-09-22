"""Standalone textures: PNG -> original-size alpha-preserving export -> XLP."""
import json,os,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PIL import Image
from PyQt6.QtWidgets import QApplication
from ModTools_5_4.project.ui_textures import validate_ui_textures,build_ui_texture_plans
from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel
from ModTools_5_4.app.config import load_config
from ModTools_5_4.ui.main_window import MainWindow
from ModTools_5_4.project.civ_project import save_civ_project
from modgen.texture import edit_texture
from sample_project import build_sample_project

class TextureTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.png=self.root/'card.png'
  im=Image.new('RGBA',(117,53),(91,70,143,255));im.putpixel((0,0),(0,0,0,0));im.putpixel((1,0),(200,80,100,128));im.save(self.png)
  self.entry={'name':'UI_TEST_CARD','path':str(self.png)}
 def test_path_names_and_case_insensitive_duplicates(self):
  self.assertEqual(validate_ui_textures([self.entry]),[])
  for name in ['../UI_BAD','UI_A.dds','ICON_SOMETHING','UI_','UI_A/B']:
   self.assertTrue(validate_ui_textures([{**self.entry,'name':name}]))
  self.assertTrue(validate_ui_textures([self.entry,{**self.entry,'name':'UI_test_card'}]))
  self.assertTrue(validate_ui_textures([{**self.entry,'path':str(self.root/'absent.png')}]))
 def test_cli_edit_preserves_project_and_requires_explicit_replace(self):
  project=build_sample_project();civ=self.root/'mod.CIV';save_civ_project(civ,project)
  edit_texture(civ,'add',name='UI_TEST_CARD',source=self.png)
  with self.assertRaises(ValueError):edit_texture(civ,'add',name='UI_TEST_CARD',source=self.png)
  self.assertEqual(len(edit_texture(civ,'add',name='UI_TEST_CARD',source=self.png,replace=True)),1)
  self.assertTrue(civ.with_suffix('.CIV.bak').exists())
  self.assertEqual(json.loads(civ.read_text(encoding='utf-8'))['workspace']['文明'],project.to_dict()['workspace']['文明'])
  self.assertEqual(edit_texture(civ,'remove',name='UI_TEST_CARD'),[])
 def test_cli_parser_and_failure_exit_code(self):
  import io
  from contextlib import redirect_stdout,redirect_stderr
  from modgen.cli import main
  project=build_sample_project();civ=self.root/'cli.CIV';save_civ_project(civ,project)
  with redirect_stdout(io.StringIO()) as output,redirect_stderr(io.StringIO()):
   self.assertEqual(main(['texture','add',str(civ),'--name','UI_TEST_CARD','--source',str(self.png)]),0)
   self.assertEqual(json.loads(output.getvalue())[0]['name'],'UI_TEST_CARD')
   before=civ.read_bytes()
   self.assertEqual(main(['texture','add',str(civ),'--name','UI_TEST_CARD','--source',str(self.png)]),1)
   self.assertEqual(civ.read_bytes(),before)
   self.assertEqual(main(['texture','remove',str(civ),'--name','UI_TEST_CARD']),0)
 def test_gui_import_edit_reload_remove(self):
  panel=ArtWorkspacePanel();self.addCleanup(panel.close)
  with patch('ModTools_5_4.ui.pages.art_workspace.QFileDialog.getOpenFileNames',return_value=([str(self.png)],'')):
   panel._import_ui_textures()
  self.assertEqual(panel._ui_texture_table.rowCount(),1)
  panel._ui_texture_table.item(0,0).setText('UI_RENAMED')
  payload=panel.export_project_payload();self.assertEqual(payload['data']['ui_textures'][0]['name'],'UI_RENAMED')
  panel.import_project_payload(payload);self.assertEqual(panel._ui_texture_table.item(0,0).text(),'UI_RENAMED')
  panel._ui_texture_table.selectRow(0);panel._remove_ui_texture()
  self.assertEqual(panel.export_project_payload()['data']['ui_textures'],[])
 def test_export_preserves_dimensions_alpha_and_xlp_registration(self):
  from ModTools_5_4.ai.control_server import ControlContext
  window=MainWindow(load_config());self.addCleanup(window.close)
  project=build_sample_project();project.sections['美术'].setdefault('data', {})['ui_textures']=[self.entry]
  civ=self.root/'source.CIV';save_civ_project(civ,project);window.open_project_file(civ)
  page=window.workspace_page();ctx=ControlContext(window,page);out=self.root/'export'
  self.assertTrue(ctx.execute('civ6proj_create',{'directory':str(out),'file_name':'Texture_Test'})['ok'])
  result=ctx.execute('generate_all',{'overwrite':'all'});self.assertTrue(result['ok'],result)
  im=Image.open(out/'IMG/UI_TEST_CARD.png').convert('RGBA')
  self.assertEqual(im.size,(117,53));self.assertEqual(im.getpixel((0,0))[3],0)
  self.assertEqual(im.getpixel((1,0))[3],128)
  dds=(out/'Textures/UI_TEST_CARD.dds').read_bytes();self.assertEqual(dds[:4],b'DDS ')
  self.assertEqual(struct.unpack_from('<II',dds,12),(53,117))
  self.assertIn('UISliceTexture',(out/'Textures/UI_TEST_CARD.tex').read_text(encoding='utf-8'))
  self.assertTrue(any('UI_TEST_CARD' in f.read_text(encoding='utf-8') for f in (out/'XLPs').glob('*.xlp')))
  self.assertNotIn('UI_TEST_CARD',(out/'Icons/Texture_Test_Icons.xml').read_text(encoding='utf-8'))
  # Repeat generation must honor overwrite for virtual texture-plan outputs.
  original_dds=(out/'Textures/UI_TEST_CARD.dds').read_bytes()
  original_tex=(out/'Textures/UI_TEST_CARD.tex').read_bytes()
  Image.new('RGBA',(91,47),(12,34,56,78)).save(self.png)
  result=ctx.execute('generate_all',{'overwrite':'none'});self.assertTrue(result['ok'],result)
  self.assertEqual((out/'Textures/UI_TEST_CARD.dds').read_bytes(),original_dds)
  self.assertEqual((out/'Textures/UI_TEST_CARD.tex').read_bytes(),original_tex)
  result=ctx.execute('generate_all',{'overwrite':'all'});self.assertTrue(result['ok'],result)
  with Image.open(out/'Textures/UI_TEST_CARD.dds') as regenerated:
   self.assertEqual(regenerated.size,(91,47))
   self.assertEqual(regenerated.convert('RGBA').getpixel((0,0))[3],78)
   with Image.open(out/'IMG/UI_TEST_CARD.png') as exported:
    self.assertEqual(regenerated.convert('RGBA').tobytes(),exported.convert('RGBA').tobytes())
  self.assertNotEqual((out/'Textures/UI_TEST_CARD.tex').read_bytes(),original_tex)
  # Invalid edits block all generated output instead of being silently skipped.
  page._art_workspace._state['ui_textures']=[{**self.entry,'name':'../bad'}]
  self.assertFalse(ctx.execute('generate_all',{'overwrite':'all'})['ok'])

if __name__=='__main__':unittest.main()
