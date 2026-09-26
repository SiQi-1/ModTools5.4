"""SDK class relationships and AST references inspired by the S7 handover."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

from ModTools_5_4.project.asset_checks import check_assets
from modgen.cli import main


CONFIG = """<Config><m_XLPClasses><m_Classes>
<Element><m_Name text="TileBase"/><m_eInstanceEntityType>ASSET</m_eInstanceEntityType><m_AllowedClasses><Element text="TileBase"/></m_AllowedClasses></Element>
<Element><m_Name text="LeaderFallback"/><m_eInstanceEntityType>TEXTURE</m_eInstanceEntityType><m_AllowedClasses><Element text="Leader_Fallback"/></m_AllowedClasses></Element>
<Element><m_Name text="DynamicGeometry"/><m_eInstanceEntityType>ASSET</m_eInstanceEntityType><m_AllowedClasses><Element text="Clutter"/></m_AllowedClasses></Element>
</m_Classes></m_XLPClasses><m_Classes><m_Classes>
<Element class="AssetObjects..AssetClass"><m_Name text="TileBase"/><m_AllowedGeoClasses><Element text="LandmarkModel"/></m_AllowedGeoClasses></Element>
<Element class="AssetObjects..AssetClass"><m_Name text="Clutter"/><m_AllowedGeoClasses><Element text="LandmarkModel"/></m_AllowedGeoClasses></Element>
<Element class="AssetObjects..GeometryClass"><m_Name text="LandmarkModel"/></Element>
<Element class="AssetObjects..GeometryClass"><m_Name text="Leader"/></Element>
<Element class="AssetObjects..TextureClass"><m_Name text="Leader_Fallback"/></Element>
<Element class="AssetObjects..TextureClass"><m_Name text="UserInterface"/></Element>
<Element class="AssetObjects..AnimationClass"><m_Name text="TileBase"/></Element>
</m_Classes></m_Classes></Config>"""


class CookerClassValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.write("demo.civ6proj", "<Project/>")
        self.config = self.write("Civ6.cfg", CONFIG)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def xlp(self, cls="TileBase", name="Model", entry="DisplayAlias"):
        return self.write("XLPs/demo.xlp", f'<XLP><m_ClassName text="{cls}"/><m_Entries><Element><m_EntryID text="{entry}"/><m_ObjectName text="{name}"/></Element></m_Entries></XLP>')

    def geometry(self):
        self.xlp()
        self.write("Assets/Model.ast", '<Asset><m_ClassName text="TileBase"/><m_GeoName text="Body"/></Asset>')
        self.write("Geometries/Body.geo", '<Geometry><m_ClassName text="LandmarkModel"/></Geometry>')

    def check(self):
        return check_assets(self.project, cooker_config=self.config)

    def test_valid_alias_and_distinct_namespaces_are_read_only(self):
        self.geometry()
        before = {str(p):p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.check()
        self.assertTrue(result["ok"], result)
        self.assertFalse(any("外部 pantry" in item["message"] for item in result["unverified"]))
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertTrue(any("FGX" in item["message"] for item in result["unverified"]))

    def test_leader_fallback_texture_class_mismatch(self):
        self.xlp(cls="LeaderFallback", name="Neutral")
        self.write("Textures/Neutral.tex", '<Texture><m_ClassName text="UserInterface"/></Texture>')
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("LeaderFallback 不允许对象" in item["message"] for item in result["errors"]))
        self.write("Textures/Neutral.tex", '<Texture><m_ClassName text="Leader_Fallback"/></Texture>')
        self.assertTrue(self.check()["ok"])

    def test_xlp_class_cannot_be_used_as_asset_class(self):
        self.xlp(cls="DynamicGeometry")
        self.write("Assets/Model.ast", '<Asset><m_ClassName text="DynamicGeometry"/></Asset>')
        self.assertFalse(self.check()["ok"])
        self.write("Assets/Model.ast", '<Asset><m_ClassName text="Clutter"/></Asset>')
        self.assertTrue(self.check()["ok"])

    def test_registered_geometry_class_can_still_be_disallowed(self):
        self.geometry()
        self.write("Geometries/Body.geo", '<Geometry><m_ClassName text="Leader"/></Geometry>')
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("AST TileBase 不允许几何" in item["message"] for item in result["errors"]))

    def test_external_pantry_and_traversal_are_distinct(self):
        self.xlp()
        result = self.check()
        self.assertTrue(result["ok"],result)
        self.assertTrue(any("外部 pantry" in i["message"] for i in result["unverified"]))
        self.xlp(name="../../secret")
        self.assertFalse(self.check()["ok"])

    def test_ast_blp_reference_checks_entry_id_not_object_name(self):
        self.geometry()
        self.write("Assets/Attachment.ast", '<Asset><m_ClassName text="TileBase"/><Element class="AssetObjects..BLPEntryValue"><m_EntryName text="DisplayAlias"/><m_XLPPath text="demo.xlp"/><m_XLPClass text="TileBase"/></Element></Asset>')
        self.assertTrue(self.check()["ok"],self.check())
        target=self.root/"Assets/Attachment.ast"
        target.write_text(target.read_text().replace("demo.xlp", r"XLPs\demo.xlp"))
        result = self.check()
        self.assertTrue(result["ok"],result)
        self.assertFalse(any("的 XLP 需在外部库" in i["message"] for i in result["unverified"]))
        target.write_text(target.read_text().replace('text="DisplayAlias"','text="Model"'))
        self.assertFalse(self.check()["ok"])

    def test_config_omission_missing_and_invalid_structure(self):
        self.geometry()
        result=check_assets(self.project)
        self.assertTrue(result["ok"],result)
        self.assertTrue(any("--cooker-config" in i["message"] for i in result["unverified"]))
        self.config.write_text("<Config/>")
        self.assertFalse(self.check()["ok"])
        self.config.unlink()
        self.assertFalse(self.check()["ok"])

    def test_cli_json_without_site_packages(self):
        self.geometry()
        command=[sys.executable,"-X","utf8","-S","-B","-m","modgen.cli","assets","check",str(self.project),"--cooker-config",str(self.config),"--json"]
        completed=subprocess.run(command,cwd=Path(__file__).resolve().parents[1],capture_output=True)
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["ok"])
        self.config.write_text("<Config/>")
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(command[7:]),1)
        self.assertFalse(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
