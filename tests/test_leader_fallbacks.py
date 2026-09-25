"""Leader fallback preservation and actual resource export regression."""
import copy
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PyQt6.QtWidgets import QApplication
from ModTools_5_4.project.leader_fallbacks import fallback_rows, validate_fallbacks
from ModTools_5_4.project.civ_project import save_civ_project, load_civ_project
from ModTools_5_4.ui.pages.group_workspace import LeaderItemEditor
from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel
from ModTools_5_4.ui.main_window import MainWindow
from ModTools_5_4.app.config import load_config
from ModTools_5_4.ai.control_server import ControlContext
from modgen.validator import check_entry
from sample_project import build_sample_project


class LeaderFallbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = []
        for name, color in (("neutral",(220,20,20,255)),("happy",(20,220,20,128)),("sad",(20,20,220,255))):
            path = self.root/f"{name}.png"
            Image.new("RGBA",(32,32),color).save(path)
            self.images.append(str(path))
        self.entry = {"type":"LEADER_TEST", "abbr":"TEST","name":"测试",
                      "images":{"diplo_foreground":{"path":self.images[0]}}}

    def test_legacy_and_no_source_and_state_collision(self):
        self.assertEqual(validate_fallbacks(self.entry),[])
        self.assertEqual([(r["state"],r["name"]) for r in fallback_rows(self.entry)],
                         [("DEFAULT","FALLBACK_NEUTRAL_TEST")])
        entry = copy.deepcopy(self.entry)
        entry["fallback_images"]={"NEUTRAL":{"path":self.images[1]},"HAPPY":{"path":self.images[2]}}
        before = copy.deepcopy(entry)
        rows = fallback_rows(entry)
        self.assertEqual(len({r["name"] for r in rows}),3)
        self.assertEqual(entry,before)
        # State and leader names can share suffixes; their boundary must be unambiguous.
        entry["fallback_images"]={"HAPPY_IDLE":{"path":self.images[1]}}
        other={**entry,"type":"LEADER_IDLE_TEST","fallback_images":{"HAPPY":{"path":self.images[2]}}}
        names=[r["name"] for e in (entry,other) for r in fallback_rows(e)]
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(fallback_rows({"type":"LEADER_TEST"}),[])

    def test_validation_unknown_missing_and_bad_image(self):
        for mapping in ([], {"TYPO":{"path":self.images[1]}}, {"HAPPY":{"path":"missing.png"}}, {"HAPPY":{"path":""}}):
            entry={**self.entry,"fallback_images":mapping}
            self.assertTrue(validate_fallbacks(entry),mapping)
            self.assertTrue(check_entry("领袖",entry)[0],mapping)
        bad=self.root/"bad.png";bad.write_text("not an image")
        self.assertTrue(validate_fallbacks({**self.entry,"fallback_images":{"HAPPY":{"path":str(bad)}}},check_images=True))
        self.assertTrue(validate_fallbacks({"type":"LEADER_TEST","fallback_images":{"HAPPY":{"path":self.images[0]}}}))

    def test_editor_and_civ_roundtrip(self):
        editor=LeaderItemEditor(lambda:{"prefix":"TEST","infix":1},lambda _:[],lambda:[])
        self.addCleanup(editor.close)
        self.entry["fallback_images"]={"DEFAULT":{"path":self.images[1]},"HAPPY":{"path":self.images[2],"crop_rect":[1,2,3,4]}}
        editor.set_entry(self.entry,"测试")
        self.assertEqual(editor.export_entry()["fallback_images"],self.entry["fallback_images"])
        editor._fallback_editor.toggle.setChecked(True)
        with patch("ModTools_5_4.ui.leader_fallback_editor.QFileDialog.getOpenFileName",return_value=(self.images[0],"")):
            editor._fallback_editor._choose("ENRAGED")
        editor._fallback_editor._clear("HAPPY")
        mapping=editor.export_entry()["fallback_images"]
        self.assertIn("ENRAGED",mapping)
        self.assertNotIn("HAPPY",mapping)
        project=build_sample_project();project.sections["领袖"]=[editor.export_entry()]
        civ=self.root/"saved.CIV";save_civ_project(civ,project)
        self.assertEqual(load_civ_project(civ).sections["领袖"][0]["fallback_images"],mapping)

    def test_default_override_has_same_artdef_and_xlp_reference(self):
        entry={**self.entry,"fallback_images":{"DEFAULT":{"path":self.images[1]},"HAPPY":{"path":self.images[2]}}}
        panel=ArtWorkspacePanel();self.addCleanup(panel.close)
        panel.refresh_from_sections({"领袖":[entry]})
        xml=ET.fromstring(panel._build_leader_fallback_artdef_xml())
        self.assertEqual([e.get("text") for e in xml.iter("m_EntryName")],
                         ["FALLBACK_NEUTRAL_TEST","FALLBACK_STATE_HAPPY__LEADER_TEST"])
        xlp=ET.fromstring(panel._build_leader_fallback_xlp_xml())
        self.assertEqual({e.get("text") for e in xlp.iter("m_EntryID")},
                         {e.get("text") for e in xml.iter("m_EntryName")})

    def test_actual_export_and_failed_image_blocks_generation(self):
        project=build_sample_project()
        leader=project.sections["领袖"][0]
        leader["images"]={"diplo_foreground":{"path":self.images[0]}}
        leader["fallback_images"]={"DEFAULT":{"path":self.images[1]},"HAPPY":{"path":self.images[2]},"NEUTRAL":{"path":self.images[0]}}
        civ=self.root/"source.CIV";save_civ_project(civ,project)
        window=MainWindow(load_config());self.addCleanup(window.close)
        window.open_project_file(civ);page=window.workspace_page();ctx=ControlContext(window,page)
        out=self.root/"export"
        self.assertTrue(ctx.execute("civ6proj_create",{"directory":str(out),"file_name":"Fallback_Test","create_art_xml":True})["ok"])
        generated=ctx.execute("generate_all",{"overwrite":"all"})
        self.assertTrue(generated["ok"],generated)
        suffix=leader["type"][7:]
        for row in fallback_rows(leader):
            for folder,ext in (("IMG",".png"),("Textures",".dds"),("Textures",".tex")):
                self.assertTrue((out/folder/(row["name"]+ext)).is_file(),row)
        with Image.open(out/f"Textures/FALLBACK_NEUTRAL_{suffix}.dds") as image:
            pixel=image.convert("RGBA").getpixel((480,480))
            self.assertEqual(pixel[3],128)
            self.assertLessEqual(max(abs(a-b) for a,b in zip(pixel,(20,220,20,128))),1)
        (self.root/"sad.png").write_text("invalid")
        result=ctx.execute("generate_all",{"overwrite":"all"})
        self.assertFalse(result["ok"],result)


if __name__ == "__main__":
    unittest.main()
