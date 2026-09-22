"""Portable source ownership, dependency planning and GUI/CLI round trips."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from ModTools_5_4.project import extensions as ext
from ModTools_5_4.project.civ_project import CivProject, load_civ_project, save_civ_project
from modgen.project_scaffold import build_project
from modgen.merger import save_civ, load_civ
from modgen.cli import main


class ExtensionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.civ = self.root / "test.CIV"
        self.payload = build_project("test", file_name="TestMod")
        save_civ(self.civ, self.payload)

    def init(self, **kwargs):
        return ext.init_extensions(self.payload, self.civ, **kwargs)

    def test_init_before_binding_roundtrip_and_idempotence(self):
        result = self.init(gameplay=True, ui=True)
        self.assertEqual(len(result["created"]), 4)
        save_civ(self.civ, self.payload)
        project = load_civ_project(self.civ)
        save_civ_project(self.civ, project)
        self.assertEqual(load_civ(self.civ)["extensions"], self.payload["extensions"])
        self.assertEqual(self.init(gameplay=True, ui=True)["created"], [])
        plan = ext.plan_extensions(self.payload, self.civ)
        self.assertFalse(plan["errors"], plan)
        ui = [a for a in plan["in_game_actions"] if a["type"] == "AddUserInterfaces"]
        self.assertEqual(len(ui), 1)
        self.assertEqual(ui[0]["files"], ["UI/TestMod_Panel.xml"])

    def test_invalid_metadata_does_not_write(self):
        self.init()
        with self.assertRaises(ext.ExtensionError):
            ext.write_extension(self.payload, self.civ, "Data/Bad.sql", "bad", scope="bad")
        self.assertFalse((ext.source_root(self.payload, self.civ) / "Data/Bad.sql").exists())

    def test_missing_sources_fail_without_output_fallback(self):
        self.init()
        path = ext.source_root(self.payload, self.civ) / "Data/TestMod_Core.sql"
        path.unlink()
        self.assertTrue(ext.plan_extensions(self.payload, self.civ)["errors"])

    def test_xml_lua_can_be_written_in_either_order(self):
        self.init()
        ext.write_extension(self.payload, self.civ, "UI/P.xml", '<Context Name="P"/>')
        self.assertTrue(ext.plan_extensions(self.payload, self.civ)["errors"])
        ext.write_extension(self.payload, self.civ, "UI/P.lua", "-- ui")
        self.assertFalse(ext.plan_extensions(self.payload, self.civ)["errors"])
        actions = ext.plan_extensions(self.payload, self.civ)["in_game_actions"]
        self.assertFalse(any("UI/P.xml" in a["files"] and a["type"] == "UpdateDatabase" for a in actions))

    def test_scope_and_phase_dependency_validation(self):
        self.init()
        with self.assertRaises(ext.ExtensionError):
            ext.write_extension(self.payload, self.civ, "Data/Before.sql", "-- before",
                                phase="before_generated", depends_on=["core"])
        with self.assertRaises(ext.ExtensionError):
            ext.write_extension(self.payload, self.civ, "Data/Front.sql", "-- front", scope="front", depends_on=["core"])

    def test_cycles_and_unknown_dependencies(self):
        self.init(gameplay=True)
        spec = self.payload["extensions"]
        spec["files"][0]["depends_on"] = ["gameplay"]
        self.assertTrue(any("循环" in e["message"] for e in ext.plan_extensions(self.payload, self.civ)["errors"]))
        spec["files"][0]["depends_on"] = ["absent"]
        self.assertTrue(any("不存在" in e["message"] for e in ext.plan_extensions(self.payload, self.civ)["errors"]))

    def test_separate_action_and_real_existing_orders(self):
        self.init()
        data = ext.basic_data(self.payload)
        data["file_info"]["in_game_actions"] = [
            {"type": "UpdateDatabase", "id": "generated", "load_order": 12345,
             "files": ["Data/TestMod_Units.sql", "Data/TestMod_Core.sql"]}]
        ext.write_extension(self.payload, self.civ, "Data/Before.sql", "-- before", phase="before_generated")
        ext.write_extension(self.payload, self.civ, "Data/After.sql", "-- after", depends_on=["core"])
        plan = ext.plan_extensions(self.payload, self.civ)
        self.assertFalse(plan["errors"], plan)
        actions = plan["in_game_actions"]
        loads = {f: a["load_order"] for a in actions for f in a["files"]}
        self.assertLess(loads["Data/Before.sql"], 12345)
        self.assertGreater(loads["Data/TestMod_Core.sql"], 12345)
        self.assertGreater(loads["Data/After.sql"], loads["Data/TestMod_Core.sql"])
        self.assertEqual(sum("Data/TestMod_Core.sql" in a["files"] for a in actions), 1)

    def test_core_writes_preserve_identity_and_dependency(self):
        self.init(gameplay=True)
        ext.write_extension(self.payload, self.civ, "Data/TestMod_Core.sql", "SELECT 1;", feature="events")
        entry = self.payload["extensions"]["files"][0]
        self.assertEqual(entry["id"], "core")
        self.assertEqual(entry["feature"], "events")
        self.assertFalse(ext.plan_extensions(self.payload, self.civ)["errors"])

    def test_generated_name_collision_and_case_duplicate(self):
        self.init()
        self.assertTrue(ext.plan_extensions(self.payload, self.civ, generated_paths=["DATA/TESTMOD_CORE.SQL"])["errors"])
        duplicate = copy.deepcopy(self.payload["extensions"]["files"][0])
        duplicate["path"] = duplicate["path"].upper()
        duplicate["id"] = "other"
        self.payload["extensions"]["files"].append(duplicate)
        self.assertTrue(ext.plan_extensions(self.payload, self.civ)["errors"])

    def test_paths_and_source_output_overlap(self):
        self.init()
        for path in ("../escape.sql", "C:/outside.sql", "Data/x.sql:stream", "Data/NUL.sql", "Data/foo. /a.sql"):
            with self.subTest(path=path), self.assertRaises(ext.ExtensionError):
                ext.safe_path(self.root, path)
        ext.basic_data(self.payload)["project_info"]["civ6proj_path"] = str(self.root / "output.civ6proj")
        self.assertTrue(ext.plan_extensions(self.payload, self.civ)["errors"])

    def test_symlink_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        inside = self.root / "inside"
        inside.mkdir()
        try:
            (inside / "link").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Windows symlink privilege unavailable")
        with self.assertRaises(ext.ExtensionError):
            ext.safe_path(inside, "link/data.sql")

    def test_remove_dependency_guard_and_deferred_output_delete(self):
        self.init(gameplay=True)
        with self.assertRaises(ext.ExtensionError):
            ext.remove_extension(self.payload, self.civ, "Data/TestMod_Core.sql")
        result = ext.remove_extension(self.payload, self.civ, "Scripts/TestMod_Gameplay.lua", keep_file=True)
        self.assertTrue(result["output_delete_pending"])
        self.assertTrue((ext.source_root(self.payload, self.civ) / result["path"]).exists())
        self.assertFalse(ext.plan_extensions(self.payload, self.civ)["errors"])

    def test_save_as_copies_sources_and_rejects_conflicting_destination(self):
        self.init()
        target = self.root / "moved" / "test.CIV"
        ext.copy_sources_for_save_as(self.payload, self.civ, target)
        self.assertFalse(ext.plan_extensions(self.payload, target)["errors"])
        other = ext.source_root(self.payload, target) / "Data/TestMod_Core.sql"
        other.write_text("changed", encoding="utf-8")
        with self.assertRaises(ext.ExtensionError):
            ext.copy_sources_for_save_as(self.payload, self.civ, target)
        self.assertEqual(other.read_text(), "changed")

    def test_init_adopts_existing_core_instead_of_overwriting(self):
        output = self.root / "output"
        (output / "Data").mkdir(parents=True)
        project = output / "TestMod.civ6proj"
        project.write_text("<Project/>", encoding="utf-8")
        (output / "Data/TestMod_Core.sql").write_text("SELECT 'existing';", encoding="utf-8")
        ext.basic_data(self.payload)["project_info"]["civ6proj_path"] = str(project)
        result = self.init()
        self.assertEqual(result["adopted"], ["Data/TestMod_Core.sql"])
        self.assertEqual((ext.source_root(self.payload, self.civ) / "Data/TestMod_Core.sql").read_text(), "SELECT 'existing';")

    def test_ui_dependency_update_changes_both_members(self):
        self.init(ui=True)
        ext.write_extension(self.payload, self.civ, "UI/TestMod_Panel.xml", '<Context Name="Panel"/>', depends_on=[])
        entries = self.payload["extensions"]["files"]
        self.assertEqual([e["depends_on"] for e in entries if e["role"] == "ui"], [[], []])
        self.assertFalse(ext.plan_extensions(self.payload, self.civ)["errors"])

    def test_readd_clears_deferred_delete(self):
        self.init(gameplay=True)
        path = "Scripts/TestMod_Gameplay.lua"
        ext.remove_extension(self.payload, self.civ, path)
        ext.write_extension(self.payload, self.civ, path, "-- restored")
        self.assertNotIn(path, self.payload["extensions"]["retired_paths"])
        self.assertNotIn(path, ext.basic_data(self.payload)["file_info"]["delete_requests"])

    def test_commands_without_site_packages(self):
        proc = subprocess.run([sys.executable, "-S", "-m", "modgen.cli", "extension", "init", str(self.civ), "--ui", "--json"], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run([sys.executable, "-S", "-m", "modgen.cli", "extension", "check", str(self.civ), "--json"], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_old_project_serialization_unchanged(self):
        project = CivProject.from_dict(self.payload)
        self.assertNotIn("extensions", project.to_dict())

    def test_cli_init_custom_write_check_remove_no_qt_required(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["extension", "init", str(self.civ), "--gameplay", "--ui"]), 0)
            self.assertEqual(main(["custom-file", "write", str(self.civ), "--path", "Data/TestMod_Core.sql", "--content", "SELECT 1;"]), 0)
            self.assertEqual(main(["extension", "check", str(self.civ), "--json"]), 0)
            self.assertEqual(main(["extension", "write", str(self.civ), "--core", "--content", "SELECT 2;"]), 0)
        current = load_civ(self.civ)
        self.assertEqual((ext.source_root(current, self.civ) / "Data/TestMod_Core.sql").read_text(), "SELECT 2;")


class ExtensionGuiTest(unittest.TestCase):
    setUp = ExtensionsTest.setUp
    init = ExtensionsTest.init
    # Integration cases deliberately use real preview/generation and persisted files.
    def test_preview_build_relocation_and_source_wins_over_output(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        self.init(gameplay=True, ui=True)
        save_civ(self.civ, self.payload)
        from modgen.preview import build_preview_manifest, _build_page
        preview = build_preview_manifest(self.civ)
        self.assertIn("Data/TestMod_Core.sql", preview["files"])
        self.assertFalse(preview["extension_errors"])
        self.assertFalse((self.root / "output").exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["civ6proj", str(self.civ), "--out", str(self.root / "output"), "--update-civ"]), 0)
            self.assertEqual(main(["build", str(self.civ), "--overwrite", "all", "--json"]), 0)
        old_output = self.root / "output"
        assert old_output.resolve().is_relative_to(self.root.resolve())
        old_output.rename(self.root / "previous-output")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["build", str(self.civ), "--overwrite", "all", "--json"]), 0)
        output = self.root / "output" / "Data/TestMod_Core.sql"
        source = ext.source_root(self.payload, self.civ) / "Data/TestMod_Core.sql"
        self.assertEqual(output.read_text(), source.read_text())
        output.write_text("output edit must not become source", encoding="utf-8")
        page = _build_page(self.civ)
        try:
            self.assertTrue(page.generate_all_output_files(overwrite_policy="all")["ok"])
            self.assertEqual(output.read_text(), source.read_text())
            # Legacy output still contains the removed source copy; it cannot resurrect.
            removed = page.ai_extension("remove", relative_path="Scripts/TestMod_Gameplay.lua")
            self.assertTrue(removed["ok"], removed)
            self.assertTrue(page.generate_all_output_files(overwrite_policy="all")["ok"])
            self.assertFalse((self.root / "output/Scripts/TestMod_Gameplay.lua").exists())
            self.assertNotIn("Scripts/TestMod_Gameplay.lua", page._project_root_manifest()[0])
            source.unlink()
            result = page.generate_all_output_files(overwrite_policy="all")
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "extensions_invalid")
        finally:
            page.close()
            page.deleteLater()

    def test_ai_initializes_without_binding_and_saves_manifest(self):
        from modgen.preview import _build_page
        page = _build_page(self.civ)
        try:
            result = page.ai_extension("init", gameplay=True, ui=True)
            self.assertTrue(result["ok"], result)
            self.assertIn("extensions", load_civ(self.civ))
            result = page.ai_project_file_write("Data/TestMod_Core.sql", "SELECT 1;")
            self.assertTrue(result["ok"], result)
            self.assertEqual(page.ai_project_file_read("Data/TestMod_Core.sql")["content"], "SELECT 1;")
            listed = page.ai_project_file_list()
            self.assertTrue(listed["ok"], listed)
            self.assertEqual(len(listed["files"]), 4)
            self.assertIn("root", listed)
            saved = self.root / "another" / "saved.CIV"
            saved.parent.mkdir()
            page.save_project(saved)
            self.assertFalse(ext.plan_extensions(load_civ(saved), saved)["errors"])
        finally:
            page.close()
            page.deleteLater()


if __name__ == "__main__":
    unittest.main()
