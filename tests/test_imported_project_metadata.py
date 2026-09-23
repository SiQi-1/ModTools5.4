"""Imported ModBuddy metadata survives CIV save and regeneration without the old project."""
import os,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage
from tests.sample_project import build_sample_project

class ImportedProjectMetadataTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=QApplication.instance() or QApplication([])
  cls.page=WorkspacePage()

 def test_import_save_rebuild_and_override_existing_project(self):
  association='<Associations><Dependency type="Mod" title="支持 &amp; 内容" id="core-id" /></Associations>'
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'Imported.civ6proj'
   path.write_text('''<Project><PropertyGroup><Name>LOC_NAME</Name><Description>LOC_DESC</Description>
<Teaser>LOC_TEASER</Teaser><Guid>mod-guid</Guid><ProjectGuid>project-guid</ProjectGuid>
<ModVersion>7</ModVersion><CompatibleVersions>2.0</CompatibleVersions><AssociationData><![CDATA['''+association+''']]></AssociationData>
<LocalizedTextData><![CDATA[<LocalizedText><Text id="LOC_NAME"><zh_Hans_CN>手改名称</zh_Hans_CN></Text>
<Text id="LOC_DESC"><zh_Hans_CN>手改说明</zh_Hans_CN></Text><Text id="LOC_TEASER"><zh_Hans_CN>独立简介</zh_Hans_CN></Text></LocalizedText>]]></LocalizedTextData>
</PropertyGroup></Project>''',encoding='utf-8')
   editor=self.page._basic_info_workspace
   parsed=editor._parse_civ6proj_file(path);editor._apply_parsed_civ6proj(parsed)
   imported=editor.export_project_payload()
   self.assertEqual(imported['project_info']['association_data'],association)
   editor.import_project_payload(imported)
   saved=editor.export_project_payload();info=saved['project_info']
   self.assertEqual(info['mod_name'],'手改名称')
   info['civ6proj_path']=str(path)
   self.page._project=build_sample_project()
   self.page._project.sections['基础信息']={'format':'MODTOOLS54_BASIC_INFO_WORKSPACE','schema_version':'0.1.0','data':saved}
   # Deleting only this test fixture proves generation does not depend on the old .civ6proj.
   path.unlink()
   generated=self.page._build_civ6proj_preview(path.name,{},set())
   def props(text):return {e.tag.split('}')[-1]:e.text for g in ET.fromstring(text) if g.tag.split('}')[-1]=='PropertyGroup' for e in g}
   values=props(generated)
   for key,want in [('ProjectGuid','project-guid'),('ModVersion','7'),('CompatibleVersions','2.0'),('AssociationData',association),('Teaser','LOC_TEASER')]:self.assertEqual(values[key],want)
   loc=ET.fromstring(values['LocalizedTextData'])
   self.assertEqual(loc.find("./Text[@id='LOC_TEASER']/zh_Hans_CN").text,'独立简介')
   path.write_text(generated,encoding='utf-8')
   info['association_data']='<Associations />'
   rebuilt=props(self.page._build_civ6proj_preview(path.name,{},set()))
   self.assertEqual(list(ET.fromstring(rebuilt['AssociationData'])),[])
   self.assertEqual(rebuilt['ProjectGuid'],'project-guid')

if __name__=='__main__':unittest.main()
