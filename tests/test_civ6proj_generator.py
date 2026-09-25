"""civ6proj_generator 单元测试：ModBuddy 兼容工程文件生成。"""
from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from ModTools_5_4.project.civ6proj_generator import (
    DEFAULT_COMPATIBLE_VERSIONS,
    build_action_data_xml,
    build_civ6proj_xml,
    create_mod_project,
    default_modbuddy_project_dir,
    new_guid,
    sanitize_file_name,
)

MS = "{http://schemas.microsoft.com/developer/msbuild/2003}"

# 官方 EmptyMod 模板中的 PropertyGroup 键集（.vstemplate 向导产物）
OFFICIAL_PROPERTY_KEYS = {
    "Configuration",
    "Name",
    "Guid",
    "ProjectGuid",
    "ModVersion",
    "Teaser",
    "Description",
    "Authors",
    "SpecialThanks",
    "AffectsSavedGames",
    "SupportsSinglePlayer",
    "SupportsMultiplayer",
    "SupportsHotSeat",
    "CompatibleVersions",
}


class SanitizeFileNameTestCase(unittest.TestCase):
    def test_removes_invalid_chars(self) -> None:
        self.assertEqual(sanitize_file_name('a<b>c:"d|e?f*g/h\\i'), "a_b_c_d_e_f_g_h_i")

    def test_whitespace_to_underscore(self) -> None:
        self.assertEqual(sanitize_file_name(" My Mod  001 "), "My_Mod_001")

    def test_empty_falls_back(self) -> None:
        self.assertEqual(sanitize_file_name(""), "MyMod")
        self.assertEqual(sanitize_file_name("///"), "MyMod")


class NewGuidTestCase(unittest.TestCase):
    def test_lowercase_uuid_format(self) -> None:
        value = new_guid()
        self.assertEqual(len(value), 36)
        self.assertEqual(value.lower(), value)
        parts = value.split("-")
        self.assertEqual([len(part) for part in parts], [8, 4, 4, 4, 12])


class BuildCiv6ProjXmlTestCase(unittest.TestCase):
    def _props(self, text: str) -> dict[str, str]:
        root = ET.fromstring(text)
        self.assertEqual(root.tag, f"{MS}Project")
        base_group = None
        for child in list(root):
            if child.tag == f"{MS}PropertyGroup" and "Condition" not in child.attrib:
                base_group = child
                break
        self.assertIsNotNone(base_group)
        props: dict[str, str] = {}
        for node in list(base_group):
            props[node.tag.replace(MS, "")] = "".join(node.itertext()).strip()
        return props

    def test_has_official_property_keys(self) -> None:
        text = build_civ6proj_xml(mod_name="测试 Mod", file_name="TestMod")
        self.assertEqual(set(self._props(text)), OFFICIAL_PROPERTY_KEYS)

    def test_fields_and_defaults(self) -> None:
        text = build_civ6proj_xml(
            mod_name="测试 Mod",
            file_name="TestMod",
            guid="abcd1234-1111-2222-3333-444455556666",
            teaser="预告",
            description="描述",
            authors="作者",
            special_thanks="致谢",
            affects_saved_games=False,
        )
        props = self._props(text)
        self.assertEqual(props["Name"], "测试 Mod")
        self.assertEqual(props["Guid"], "abcd1234-1111-2222-3333-444455556666")
        self.assertEqual(props["Teaser"], "预告")
        self.assertEqual(props["Description"], "描述")
        self.assertEqual(props["Authors"], "作者")
        self.assertEqual(props["SpecialThanks"], "致谢")
        self.assertEqual(props["AffectsSavedGames"], "false")
        self.assertEqual(props["SupportsSinglePlayer"], "true")
        self.assertEqual(props["CompatibleVersions"], DEFAULT_COMPATIBLE_VERSIONS)

    def test_xml_escaping(self) -> None:
        text = build_civ6proj_xml(mod_name="A <B> & 'C'", file_name="TestMod")
        props = self._props(text)
        self.assertEqual(props["Name"], "A <B> & 'C'")

    def test_guid_auto_generated_when_missing(self) -> None:
        text = build_civ6proj_xml(mod_name="测试", file_name="TestMod")
        props = self._props(text)
        self.assertEqual(len(props["Guid"]), 36)
        self.assertNotEqual(props["Guid"], props["ProjectGuid"])

    def test_import_civ6_targets_and_output_path(self) -> None:
        text = build_civ6proj_xml(mod_name="测试", file_name="TestMod")
        root = ET.fromstring(text)
        children = list(root)
        import_node = children[-1]
        self.assertEqual(import_node.tag, f"{MS}Import")
        self.assertEqual(import_node.get("Project"), "$(MSBuildLocalExtensionPath)Civ6.targets")
        self.assertIn(f'Condition=" \'$(Configuration)\' == \'Default\' "', text)
        self.assertIn("<OutputPath>.</OutputPath>", text)

    def test_none_include_and_content_and_folders(self) -> None:
        text = build_civ6proj_xml(
            mod_name="测试",
            file_name="TestMod",
            content_files=["Data/TestMod_Units.sql", "Icons/TestMod_Icons.xml"],
            folder_paths=["Data", "Icons"],
        )
        self.assertIn('<None Include="TestMod.Art.xml" />', text)
        self.assertIn('<Content Include="Data\\TestMod_Units.sql">', text)
        self.assertIn("<SubType>Content</SubType>", text)
        self.assertIn('<Folder Include="Data\\" />', text)

    def test_art_sources_are_not_registered_but_runtime_files_are(self) -> None:
        source_files = ["Assets/Tile.ast", "./gEoMeTrIeS/Sub/Shape.fgx", "Materials/Stone.mtl",
                        "Textures/Image.dds", "XLPs/tilebases.xlp", "ArtDefs/Landmarks.artdef",
                        "Animations/Idle.anm", "Behaviors/B.beh", "DSGs/D.dsg",
                        "EnvironmentLights/E.xml", "FireFX/F.xml", "LightRigs/R.xml",
                        "Lights/L.xml", "ParticleEffects/P.xml", "IMG/portrait.png"]
        runtime = ["Data/Test.sql", "UI/Panel.xml", "AssetsExtra/note.xml",
                   "Platforms/Windows/BLPs/landmarks/tilebases.blp", "Data/Assets/List.xml"]
        text = build_civ6proj_xml(mod_name="Test", file_name="Test",
                                 content_files=source_files + runtime,
                                 folder_paths=[p.rsplit("/", 1)[0] for p in source_files] + ["Data", "Platforms/Windows"])
        items = [e for e in ET.fromstring(text).iter() if e.get('Include')]
        includes = {e.get('Include').replace("\\", "/") for e in items}
        for path in source_files:
            self.assertNotIn(path, includes)
            self.assertNotIn(path.rsplit("/", 1)[0] + "/", includes)
        for path in runtime:
            self.assertIn(path, includes)
        self.assertIn('Test.Art.xml', includes)

    def test_action_data_embedded_as_cdata(self) -> None:
        text = build_civ6proj_xml(
            mod_name="测试",
            file_name="TestMod",
            in_game_actions=[
                {"type": "UpdateDatabase", "id": "UpdateDatabase", "files": ["Data/A.sql"], "load_order": 10},
            ],
        )
        self.assertIn("<InGameActionData><![CDATA[", text)
        self.assertIn("<UpdateDatabase id=\"UpdateDatabase\">", text)
        self.assertIn("<LoadOrder>10</LoadOrder>", text)


class BuildActionDataXmlTestCase(unittest.TestCase):
    def test_update_icons_path_normalization(self) -> None:
        text = build_action_data_xml(
            "InGameActions",
            [{"type": "UpdateIcons", "id": "Icons", "files": ["TestMod_Icons.xml"]}],
        )
        self.assertIn("<File>Icons/TestMod_Icons.xml</File>", text)

    def test_add_user_interfaces_context(self) -> None:
        text = build_action_data_xml(
            "InGameActions",
            [{"type": "AddUserInterfaces", "id": "X", "files": ["UI/a.xml"]}],
        )
        self.assertIn("<Context>InGame</Context>", text)

    def test_skips_non_dict_entries(self) -> None:
        text = build_action_data_xml("InGameActions", [None, "bad", {"type": "", "files": []}])
        self.assertIn("<UpdateDatabase id=\"UpdateDatabase\">", text)


class CreateModProjectTestCase(unittest.TestCase):
    def _read_guids(self, proj: Path) -> tuple[str, str]:
        root = ET.parse(proj).getroot()
        base = None
        for child in list(root):
            if child.tag == f"{MS}PropertyGroup" and "Condition" not in child.attrib:
                base = child
                break
        self.assertIsNotNone(base)
        props = {node.tag.replace(MS, ""): "".join(node.itertext()).strip() for node in list(base)}
        return props["Guid"], props["ProjectGuid"]

    def test_creates_civ6proj_and_art_xml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = create_mod_project(
                directory=Path(tmp),
                file_name="My Mod 001",
                mod_name="我的 Mod",
                guid="11111111-2222-3333-4444-555555555555",
            )
            proj = result["civ6proj"]
            art = result["art_xml"]
            self.assertEqual(proj.name, "My_Mod_001.civ6proj")
            self.assertTrue(proj.exists())
            self.assertIsNotNone(art)
            self.assertEqual(art.name, "My_Mod_001.Art.xml")
            self.assertTrue(art.exists())
            self.assertGreater(art.stat().st_size, 100)
            ET.parse(proj)  # 必须可解析

    def test_guid_and_project_guid_returned_and_match_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = create_mod_project(directory=Path(tmp), file_name="X", mod_name="X")
            mod_guid = str(result["guid"])
            project_guid = str(result["project_guid"])
            self.assertEqual(len(mod_guid), 36)
            self.assertEqual(len(project_guid), 36)
            self.assertNotEqual(mod_guid, project_guid)
            file_guid, file_project_guid = self._read_guids(result["civ6proj"])
            self.assertEqual(file_guid, mod_guid)
            self.assertEqual(file_project_guid, project_guid)

    def test_existing_guid_preserved(self) -> None:
        """同一 Mod 重建：传入原 guid 必须原样保留（ModID 不能漂移）。"""
        fixed = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as tmp:
            first = create_mod_project(directory=Path(tmp), file_name="X", mod_name="X", guid=fixed)
            second = create_mod_project(directory=Path(tmp) / "rebuild", file_name="X", mod_name="X", guid=fixed)
            self.assertEqual(str(first["guid"]), fixed)
            self.assertEqual(str(second["guid"]), fixed)
            self.assertEqual(self._read_guids(first["civ6proj"])[0], fixed)
            self.assertEqual(self._read_guids(second["civ6proj"])[0], fixed)

    def test_no_art_xml_option(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = create_mod_project(directory=Path(tmp), file_name="X", mod_name="X", write_art_xml=False)
            self.assertIsNone(result["art_xml"])
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["X.civ6proj"])


class DefaultModbuddyProjectDirTestCase(unittest.TestCase):
    def test_under_documents(self) -> None:
        expected = Path.home() / "Documents" / "Firaxis ModBuddy" / "Civilization VI" / "MyMod"
        self.assertEqual(default_modbuddy_project_dir("MyMod"), expected)


if __name__ == "__main__":
    unittest.main()
