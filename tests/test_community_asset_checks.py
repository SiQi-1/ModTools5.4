"""Observable checks for source, cooked and publishable asset references."""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ModTools_5_4.project.asset_checks import (
    check_assets, check_audio, compare_art, check_workshop,
)
from modgen.cli import main


class AssetChecksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def modinfo(self, files, actions="", relative="mod.modinfo"):
        body = "".join(f"<File>{f}</File>" for f in files)
        return self.write(relative, f'<Mod id="fa2b2f45-4685-46d0-a430-a8a7e5757927"><Properties><Name>Demo</Name><Description>Demo</Description></Properties><InGameActions>{actions}</InGameActions><Files>{body}</Files></Mod>')

    def audio(self, metadata=True):
        prefix = "Platforms/Windows/Audio/"
        ini = self.write(prefix+"Demo_Banks.ini", b"[InGame]\r\nDemo.bnk\r\n")
        self.write(prefix+"Demo.bnk", b"BKHD")
        files = [prefix+"Demo_Banks.ini", prefix+"Demo.bnk"]
        if metadata:
            self.write(prefix+"Demo.xml", '<SoundBanksInfo><SoundBanks><SoundBank><ShortName>Demo</ShortName><ReferencedStreamedFiles><File Id="42" Language="SFX"><Path>42.wem</Path></File></ReferencedStreamedFiles></SoundBank></SoundBanks></SoundBanksInfo>')
            self.write(prefix+"42.wem", b"RIFF")
            files += [prefix+"Demo.xml", prefix+"42.wem"]
        return self.modinfo(files, '<UpdateAudio id="Audio"><File>'+prefix+'Demo_Banks.ini</File></UpdateAudio>'), ini

    def test_audio_missing_stream_is_error_and_read_only(self):
        project, ini = self.audio()
        before = project.read_bytes(), ini.read_bytes()
        result = check_audio(project)
        self.assertTrue(result["ok"], result)
        self.assertFalse(any("无匹配 SoundBanksInfo" in i["message"] for i in result["unverified"]))
        (ini.parent / "42.wem").unlink()
        self.assertFalse(check_audio(project)["ok"])
        self.assertEqual(before, (project.read_bytes(), ini.read_bytes()))

    def test_no_metadata_is_not_complete_validation(self):
        project, _ = self.audio(metadata=False)
        result = check_audio(project)
        self.assertTrue(result["ok"], result)
        self.assertTrue(any("流式 WEM" in i["message"] for i in result["unverified"]))

    def test_bad_ini_and_direct_media_action(self):
        project, ini = self.audio()
        ini.write_bytes(b"\xef\xbb\xbf[InGame]\r\nDemo.bnk\r\n")
        self.assertFalse(check_audio(project)["ok"])
        project.write_text(project.read_text().replace("Demo_Banks.ini</File></UpdateAudio>", "Demo.bnk</File></UpdateAudio>"))
        self.assertTrue(any("不应直接引用媒体" in i["message"] for i in check_audio(project)["errors"]))

    def test_namespace_cdata_and_self_closing_actions(self):
        self.write("UI/Panel.xml", "<Context/>")
        self.write("Audio/Bank.ini", b"[InGame]\r\nBank.bnk\r\n")
        self.write("Audio/Bank.bnk", b"BKHD")
        path = self.write("test.civ6proj", r'''<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
<PropertyGroup><InGameActionData><![CDATA[<InGameActions>
<UpdateAudio id="Empty"/><ImportFiles id="UI"><File>UI/Panel.xml</File></ImportFiles>
<UpdateAudio id="Sound"><File>Audio/Bank.ini</File></UpdateAudio>
<UpdateArt id="Art"><File>(Mod Art Dependency File)</File></UpdateArt>
</InGameActions>]]></InGameActionData></PropertyGroup>
<ItemGroup><Content Include="UI\Panel.xml"/><Content Include="Audio\Bank.ini"/><Content Include="Audio\Bank.bnk"/></ItemGroup></Project>''')
        result = check_audio(path)
        self.assertTrue(result["ok"], result)
        (self.root/"UI/Panel.xml").unlink()
        self.assertFalse(check_audio(path)["ok"])

    def test_xml_action_escape_and_malformed_cdata(self):
        path = self.write("bad.civ6proj", '<Project><PropertyGroup><InGameActionData><![CDATA[<InGameActions><ImportFiles>]]></InGameActionData></PropertyGroup></Project>')
        self.assertFalse(check_assets(path)["ok"])
        path = self.modinfo(["../secret.sql"], '<UpdateDatabase id="X"><File>../secret.sql</File></UpdateDatabase>')
        result = check_assets(path)
        self.assertFalse(result["ok"])
        self.assertTrue(any("非法文件引用" in i["message"] for i in result["errors"]))

    def test_audio_ini_cannot_escape_its_folder(self):
        project, ini = self.audio()
        ini.write_bytes(b"[InGame]\r\n../elsewhere.bnk\r\n")
        self.assertFalse(check_audio(project)["ok"])

    def test_fallback_link_and_mixed_text(self):
        self.write("Textures/HAPPY.dds", b"DDS ")
        self.write("Textures/HAPPY.tex", '<AssetObjects..Texture><m_RelativePath text="HAPPY.dds"/></AssetObjects..Texture>')
        xlp = self.write("XLPs/LeaderFallback.xlp", '<AssetObjects..XLP><m_Entries><Element><m_EntryID text="HAPPY"/><m_ObjectName text="HAPPY"/></Element></m_Entries></AssetObjects..XLP>')
        art = self.write("ArtDefs/FallbackLeaders.artdef", '<AssetObjects..ArtDefSet><Element class="AssetObjects..BLPEntryValue"><m_EntryName text="HAPPY"/><m_XLPPath text="leaderfallback.xlp"/><m_XLPClass text="LeaderFallback"/></Element></AssetObjects..ArtDefSet>')
        project = self.write("Test.civ6proj", '<Project><ItemGroup><Content Include="XLPs/LeaderFallback.xlp"/><Content Include="ArtDefs/FallbackLeaders.artdef"/></ItemGroup></Project>')
        self.assertTrue(check_assets(project)["ok"], check_assets(project))
        xlp.write_text(xlp.read_text().replace('m_EntryID text="HAPPY"', 'm_EntryID text="OTHER"'))
        self.assertFalse(check_assets(project)["ok"])
        art.write_text(art.read_text().replace('<m_EntryName text="HAPPY"/>','<m_EntryName text="HAPPY"/>中文说明'),encoding="utf-8")
        self.assertTrue(any("标签外" in i["message"] for i in check_assets(project)["errors"]))

    def test_cook_format_semantics_and_order(self):
        left = self.write("source/test.artdef", b'<root>\r\n<!-- note --><x text="A" />\r\n<y/>\r\n</root>')
        right = self.write("cooked/test.artdef", '<root><x text="A"/><y /></root>')
        result = compare_art(left.parent, right.parent)
        self.assertTrue(result["ok"])
        self.assertEqual(result["comparisons"][0]["status"], "format_only")
        for text in ['<root><x text=""/><y/></root>', '<root><y/><x text="A"/></root>', '<root><x text="_MissingArt"/><y/></root>']:
            right.write_text(text)
            self.assertFalse(compare_art(left.parent, right.parent)["ok"])
        right.unlink()
        self.assertFalse(compare_art(left.parent, right.parent)["ok"])

    def test_workshop_multiple_modinfo_and_id(self):
        self.write("workshop.json", json.dumps({"title":"Demo","description":"[b]Demo[/b]","visibility":"private"}))
        self.write("content/Data/demo.sql", "SELECT 1;")
        mod = self.modinfo(["Data/demo.sql"], relative="content/Demo.modinfo")
        self.assertTrue(check_workshop(self.root)["ok"], check_workshop(self.root))
        self.modinfo([], relative="content/Other.modinfo")
        self.assertFalse(check_workshop(self.root)["ok"])
        self.assertTrue(check_workshop(self.root, modinfo="Demo.modinfo")["ok"])
        self.write("mod_id.txt", "0")
        self.assertFalse(check_workshop(self.root, modinfo="Demo.modinfo")["ok"])
        self.write("mod_id.txt", "1234567890")
        (mod.parent/"Data/demo.sql").unlink()
        self.assertFalse(check_workshop(self.root, modinfo="Demo.modinfo")["ok"])

    def test_cli_json_exit_and_no_qt_import(self):
        project, _ = self.audio()
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["audio","check",str(project),"--json"]),0)
        self.assertIn("unverified", json.loads(output.getvalue()))
        # -S disables all site packages, including Qt and Pillow.
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", "-S", "-B", "-m", "modgen.cli", "audio", "check", str(project), "--json"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["ok"])
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["workshop","check",str(self.root),"--json"]),1)
        self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_workshop_uploader_integer_dependencies_and_partial_update(self):
        self.modinfo([], relative="content/Demo.modinfo")
        self.write("mod_id.txt", "1234567890")
        self.write("workshop.json", json.dumps({"dependencies":[123456789012345],"changeNote":"update"}))
        self.assertTrue(check_workshop(self.root)["ok"],check_workshop(self.root))
        for bad in [["1234567890"],[True],[-1],[2**64]]:
            self.write("workshop.json",json.dumps({"dependencies":bad}))
            self.assertFalse(check_workshop(self.root)["ok"],bad)

    def test_audio_orphan_media_needs_manifest(self):
        project, ini = self.audio()
        self.write("Platforms/Windows/Audio/orphan.wem",b"RIFF")
        result=check_audio(project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("未登记" in i["message"] for i in result["errors"]))

    def test_malformed_metadata_returns_diagnostics(self):
        self.modinfo([], relative="content/Demo.modinfo")
        for fields in ({"visibility":[]}, {"changeNote":3}, {"localizations":[{"language":"schinese","title":False}]}):
            self.write("workshop.json",json.dumps(fields))
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["workshop","check",str(self.root),"--json"]),1)
            self.assertTrue(json.loads(output.getvalue())["errors"])
        self.write("workshop.json",json.dumps({"localizations":[{"language":"schinese","title":None}]}))
        self.assertTrue(check_workshop(self.root)["ok"])
        self.write("mod_id.txt","9"*5000)
        self.assertFalse(check_workshop(self.root)["ok"])
        (self.root/"mod_id.txt").unlink()
        (self.root/"image.png").mkdir()
        self.assertFalse(check_workshop(self.root)["ok"])

    def test_comparison_reports_changed_nesting(self):
        left=self.write("source/test.artdef","<root><a><b/></a></root>")
        right=self.write("cooked/test.artdef","<root><a/><b/></root>")
        result=compare_art(left.parent,right.parent)
        self.assertFalse(result["ok"])
        self.assertGreater(result["details"][0]["difference_count"],0)
        self.assertIn("path",result["details"][0]["differences"][0]["source"])

    def test_symlink_escape_is_not_read(self):
        outside = self.write("outside/Secret.sql", "SELECT 1;")
        link = self.root/"workspace/escape.sql"
        link.parent.mkdir()
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        mod = self.modinfo(["escape.sql"], relative="workspace/mod.modinfo")
        self.assertFalse(check_assets(mod)["ok"])


if __name__ == "__main__":
    unittest.main()
