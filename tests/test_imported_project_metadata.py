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


class ArtSourceRegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_new_and_existing_project_omit_sources_and_keep_runtime(self):
        source_paths = ['Assets/Tile.ast', './GEOMETRIES/Sub/Shape.fgx', 'Materials/Stone.mtl',
                        'Textures/Image.tex', 'ArtDefs/Landmarks.artdef', 'XLPs/tilebases.xlp']
        runtime = ['Data/Game.sql', 'UI/Panel.xml', 'Platforms/Windows/BLPs/landmarks/tilebases.blp']
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'Test.civ6proj'
            self.page._project = build_sample_project()
            self.page._project.sections['基础信息'] = {'format': 'MODTOOLS54_BASIC_INFO_WORKSPACE', 'schema_version': '0.1.0', 'data': {'project_info': {'file_name': 'Test', 'civ6proj_path': str(project)}}}
            files = dict.fromkeys(source_paths + runtime, 'fixture')
            folders = {p.rsplit('/', 1)[0] for p in files}
            fresh = self.page._build_civ6proj_preview(project.name, files, folders)
            self.assert_sources_absent(fresh, runtime)
            # The old erroneous Content plus manual source None/Folder entries
            # must be removed without deleting the actual source or other items.
            source = Path(temp) / 'Assets/Tile.ast'
            source.parent.mkdir(); source.write_text('preserve-source')
            project.write_text('<Project><PropertyGroup><Guid>keep-guid</Guid></PropertyGroup><ItemGroup>'
                              '<Content Include="Assets\\Tile.ast"/><Folder Include="Assets\\Sub\\"/>'
                              '<None Include="Materials/Stone.mtl"/><Content Include="XLPs/tilebases.xlp"/>'
                              '<Content Include="ArtDefs/Landmarks.artdef"/><Content Include="manual.lua"/>'
                              '<Content Include="Platforms/Windows/BLPs/old.blp"/>'
                              '</ItemGroup></Project>', encoding='utf-8')
            changed = self.page._build_civ6proj_preview(project.name, files, folders)
            self.assert_sources_absent(changed, runtime + ['manual.lua', 'Platforms/Windows/BLPs/old.blp'])
            self.assertIn('keep-guid', changed)
            self.assertEqual(source.read_text(), 'preserve-source')
            project.write_text(changed, encoding='utf-8')
            again = self.page._build_civ6proj_preview(project.name, files, folders)
            self.assert_sources_absent(again, runtime)

    def assert_sources_absent(self, text, runtime):
        includes = {e.get('Include').replace('\\', '/') for e in ET.fromstring(text).iter() if e.get('Include')}
        for path in includes:
            root = path.removeprefix('./').split('/')[0].lower()
            self.assertNotIn(root, {'assets', 'geometries', 'materials', 'textures', 'artdefs', 'xlps'})
        for path in runtime:
            self.assertIn(path, includes)

if __name__=='__main__':unittest.main()
