"""modgen 新命令测试：new-project / query / loc / merge 修改器 / preview / custom-file / skill。"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
repo_root = str(Path(__file__).resolve().parents[2])
if repo_root not in os.sys.path:
    os.sys.path.insert(0, repo_root)

from modgen import rules  # noqa: E402
from modgen.dbquery import (  # noqa: E402
    QueryError,
    format_query_result,
    open_game_db_readonly,
    resolve_loc_tag,
    run_query,
)
from modgen.modifier_generator import (  # noqa: E402
    generate_ability,
    generate_modifier,
    generate_requirement,
    generate_requirement_set,
)
from modgen.modifier_merger import merge_modifier_entry  # noqa: E402
from modgen.project_scaffold import build_project, create_new_project_file  # noqa: E402
from modgen.validator import validate_project  # noqa: E402


def _tiny_game_db(path: Path) -> None:
    """构造最小游戏库（Types 表）。"""
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE Types (Type TEXT, Kind TEXT)")
        conn.execute("INSERT INTO Types VALUES ('TYPE_A', 'KIND_A')")
        conn.execute("INSERT INTO Types VALUES ('TYPE_B', 'KIND_B')")
        conn.commit()
    finally:
        conn.close()


def _tiny_text_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE LocalizedText (Tag TEXT, Language TEXT, Text TEXT)")
        conn.execute("INSERT INTO LocalizedText VALUES ('LOC_TEST_ONE_NAME', 'zh_Hans_CN', '测试一')")
        conn.execute("INSERT INTO LocalizedText VALUES ('LOC_TEST_TWO_NAME', 'zh_Hans_CN', '{LOC_TEST_ONE_NAME} 引用')")
        conn.execute("INSERT INTO LocalizedText VALUES ('LOC_TEST_ONE_NAME', 'en_US', 'English One')")
        conn.commit()
    finally:
        conn.close()


class NewProjectTestCase(unittest.TestCase):
    def test_build_workspace_structure(self) -> None:
        payload = build_project("测试工程", prefix="SIQI", infix=35, file_name="Siqi_Leaders_0035")
        workspace = payload["workspace"]
        # 分节顺序与 CIV_SECTION_ORDER 一致
        expected_order = ["基础信息"] + list(rules.CONTENT_SECTIONS) + ["美术", "UI图标", "文本", "修改器"]
        self.assertEqual(list(workspace.keys()), expected_order)
        for section in rules.CONTENT_SECTIONS:
            self.assertEqual(workspace[section], [])
        self.assertEqual(workspace["UI图标"], [])
        self.assertEqual(payload["meta"]["schema_version"], "0.1.0")

    def test_basic_info_params_applied(self) -> None:
        payload = build_project("测试工程", prefix="SIQI", infix=35, file_name="Siqi_Leaders_0035", mod_name="中文名")
        data = payload["workspace"]["基础信息"]["data"]
        self.assertEqual(data["shared_workspace_params"], {"prefix": "SIQI", "infix": 35, "file_name": "Siqi_Leaders_0035"})
        self.assertEqual(data["global_settings"]["infix"], 35)
        info = data["project_info"]
        self.assertEqual(info["mod_name"], "中文名")
        self.assertEqual(info["file_name"], "Siqi_Leaders_0035")
        self.assertTrue(info["guid"])

    def test_modifier_and_art_sections(self) -> None:
        payload = build_project("测试工程", prefix="SIQI", infix=35)
        modifier = payload["workspace"]["修改器"]
        self.assertEqual(modifier["format"], "MODTOOLS54_MODIFIER_WORKSPACE")
        self.assertEqual(modifier["data"]["prefix1"], "SIQI")
        for key in ("owners", "unit_abilities", "modifiers", "requirement_sets", "requirements"):
            self.assertEqual(modifier["data"][key], [])
        art = payload["workspace"]["美术"]
        self.assertEqual(art["format"], "MODTOOLS54_ART_WORKSPACE")
        self.assertIn("alias_map", art["data"])

    def test_project_validates_clean(self) -> None:
        payload = build_project("测试工程", prefix="SIQI", infix=35)
        self.assertEqual(validate_project(payload), [])

    def test_create_file_refuses_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo.CIV"
            create_new_project_file(out, "demo", prefix="X", infix=1)
            with self.assertRaises(Exception):
                create_new_project_file(out, "demo", prefix="X", infix=1)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["project_name"], "demo")


class QueryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db = Path(self._tmp.name) / "game.sqlite"
        _tiny_game_db(self._db)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_select_works(self) -> None:
        conn = open_game_db_readonly(self._db)
        try:
            result = run_query(conn, "SELECT Type, Kind FROM Types ORDER BY Type")
        finally:
            conn.close()
        self.assertEqual(result["columns"], ["Type", "Kind"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertFalse(result["truncated"])

    def test_limit_truncates(self) -> None:
        conn = open_game_db_readonly(self._db)
        try:
            result = run_query(conn, "SELECT Type FROM Types", limit=1)
        finally:
            conn.close()
        self.assertEqual(len(result["rows"]), 1)
        self.assertTrue(result["truncated"])

    def test_write_statements_rejected(self) -> None:
        conn = open_game_db_readonly(self._db)
        try:
            for sql in ("INSERT INTO Types VALUES ('X','KIND_X')", "UPDATE Types SET Kind='X'", "DROP TABLE Types"):
                with self.assertRaises(QueryError, msg=sql):
                    run_query(conn, sql)
        finally:
            conn.close()

    def test_multi_statements_rejected(self) -> None:
        conn = open_game_db_readonly(self._db)
        try:
            with self.assertRaises(QueryError):
                run_query(conn, "SELECT 1; SELECT 2")
        finally:
            conn.close()

    def test_format_output(self) -> None:
        conn = open_game_db_readonly(self._db)
        try:
            result = run_query(conn, "SELECT Type, Kind FROM Types LIMIT 1")
        finally:
            conn.close()
        text = format_query_result(result)
        self.assertIn("Type", text)
        self.assertIn("TYPE_A", text)
        self.assertIn("(1 行", text)


class LocTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._db = Path(self._tmp.name) / "text.sqlite"
        _tiny_text_db(self._db)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_direct_and_reference(self) -> None:
        conn = sqlite3.connect(f"file:{self._db.as_posix()}?mode=ro", uri=True)
        try:
            self.assertEqual(resolve_loc_tag(conn, "LOC_TEST_ONE_NAME"), "测试一")
            self.assertEqual(resolve_loc_tag(conn, "LOC_TEST_TWO_NAME"), "测试一 引用")
            self.assertIsNone(resolve_loc_tag(conn, "LOC_NOT_EXIST"))
        finally:
            conn.close()


class MergeModifierTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = build_project("测试工程", prefix="SIQI", infix=40)

    def test_merge_modifier(self) -> None:
        entry = generate_modifier(
            prefix="SIQI", infix=40, effect_type="EFFECT_ADJUST_PLOT_YIELD",
            collection_type="COLLECTION_OWNER", desc="ADJ_FARM_FOOD",
            parameters=[{"name": "Amount", "value": 1}, {"name": "YieldType", "value": "YIELD_FOOD"}],
        )
        merge_modifier_entry(self.payload, entry)
        data = self.payload["workspace"]["修改器"]["data"]
        self.assertEqual(len(data["modifiers"]), 1)
        self.assertEqual(data["modifiers"][0]["modifier_id"], entry["modifier_id"])

    def test_merge_requirement_and_set(self) -> None:
        req = generate_requirement(
            prefix="SIQI", infix=40, requirement_type="REQUIREMENT_PLOT_IMPROVEMENT_TYPE_MATCHES",
            desc="ADJ_FARM", parameters=[{"name": "ImprovementType", "value": "IMPROVEMENT_FARM"}],
        )
        reqset = generate_requirement_set(prefix="SIQI", infix=40, desc="PLOT_IS_FARM", requirements=[req["requirement_id"]])
        merge_modifier_entry(self.payload, req)
        merge_modifier_entry(self.payload, reqset)
        data = self.payload["workspace"]["修改器"]["data"]
        self.assertEqual(len(data["requirements"]), 1)
        self.assertEqual(len(data["requirement_sets"]), 1)
        # 合并后整体校验应通过
        from modgen.modifier_validator import check_modifier_data
        errors, _warnings = check_modifier_data(data)
        self.assertEqual(errors, [])

    def test_merge_dedup_by_id(self) -> None:
        entry = generate_modifier(
            prefix="SIQI", infix=40, effect_type="EFFECT_ADJUST_PLOT_YIELD", desc="SAME",
            parameters=[{"name": "Amount", "value": 1}],
        )
        merge_modifier_entry(self.payload, entry)
        entry2 = generate_modifier(
            prefix="SIQI", infix=40, effect_type="EFFECT_ADJUST_PLOT_YIELD", desc="SAME",
            parameters=[{"name": "Amount", "value": 2}],
        )
        merge_modifier_entry(self.payload, entry2)
        data = self.payload["workspace"]["修改器"]["data"]
        self.assertEqual(len(data["modifiers"]), 1)
        self.assertEqual(data["modifiers"][0]["parameters"][0]["value"], 2)

    def test_unknown_kind_rejected(self) -> None:
        with self.assertRaises(Exception):
            merge_modifier_entry(self.payload, {"unrelated": 1})

    def test_invalid_effect_rejected(self) -> None:
        with self.assertRaises(Exception):
            generate_modifier(prefix="SIQI", infix=40, effect_type="EFFECT_NOT_REAL", desc="X")


class PreviewTestCase(unittest.TestCase):
    """preview 需要 PyQt6；不可用时跳过（其余命令不受影响）。"""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from modgen.preview import build_preview_files  # noqa: F401
        except Exception:  # noqa: BLE001
            raise unittest.SkipTest("PyQt6 环境不可用，跳过 preview 测试")
        cls._available = True

    def test_preview_empty_project(self) -> None:
        if not getattr(self, "_available", False):
            self.skipTest("PyQt6 不可用")
        from modgen.preview import build_preview_files

        with tempfile.TemporaryDirectory() as tmp:
            civ = Path(tmp) / "demo.CIV"
            create_new_project_file(civ, "demo", prefix="SIQI", infix=1, file_name="Demo_Project")
            files = build_preview_files(civ)
        self.assertIsInstance(files, dict)
        self.assertTrue(files)
        # 应包含 Data/Modifiers 与 Icons 输出
        self.assertTrue(any("Modifiers.sql" in rel for rel in files), list(files))
        self.assertTrue(any(rel.endswith("_Icons.xml") for rel in files), list(files))


class Civ6ProjCommandTestCase(unittest.TestCase):
    """civ6proj 命令：从 .CIV 基础信息生成 ModBuddy 兼容工程（无需 PyQt）。"""

    def _run(self, *argv: str) -> int:
        from modgen import cli
        parser = cli.build_parser()
        args = parser.parse_args(list(argv))
        return int(args.func(args))

    def test_creates_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = Path(tmp) / "demo.CIV"
            create_new_project_file(civ, "测试工程", prefix="SIQI", infix=1, file_name="Siqi_Demo_0001", mod_name="演示 Mod")
            out_dir = Path(tmp) / "proj"
            code = self._run("civ6proj", str(civ), "--out", str(out_dir))
            self.assertEqual(code, 0)
            proj = out_dir / "Siqi_Demo_0001.civ6proj"
            art = out_dir / "Siqi_Demo_0001.Art.xml"
            self.assertTrue(proj.exists())
            self.assertTrue(art.exists())
            text = proj.read_text(encoding="utf-8")
            self.assertIn("<Name>演示 Mod</Name>", text)
            self.assertIn('$(MSBuildLocalExtensionPath)Civ6.targets', text)
            self.assertIn('<None Include="Siqi_Demo_0001.Art.xml" />', text)

    def test_update_civ_writes_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = Path(tmp) / "demo.CIV"
            create_new_project_file(civ, "测试工程", prefix="SIQI", infix=1, file_name="Siqi_Demo_0001")
            out_dir = Path(tmp) / "proj"
            code = self._run("civ6proj", str(civ), "--out", str(out_dir), "--update-civ")
            self.assertEqual(code, 0)
            payload = json.loads(civ.read_text(encoding="utf-8"))
            info = payload["workspace"]["基础信息"]["data"]["project_info"]
            written = info["civ6proj_path"]
            self.assertEqual(Path(written), (out_dir / "Siqi_Demo_0001.civ6proj").resolve())
            self.assertTrue((civ.with_suffix(civ.suffix + ".bak")).exists())

    def test_update_civ_writes_guid_and_is_stable(self) -> None:
        """ModID：首次生成 GUID 并回写 .CIV；重复运行必须复用同一 GUID（不漂移）。"""
        with tempfile.TemporaryDirectory() as tmp:
            civ = Path(tmp) / "demo.CIV"
            create_new_project_file(civ, "测试工程", prefix="SIQI", infix=1, file_name="Siqi_Demo_0001")
            out_dir = Path(tmp) / "proj"
            self._run("civ6proj", str(civ), "--out", str(out_dir), "--update-civ")
            payload = json.loads(civ.read_text(encoding="utf-8"))
            info = payload["workspace"]["基础信息"]["data"]["project_info"]
            guid_in_civ = str(info.get("guid") or "")
            self.assertEqual(len(guid_in_civ), 36)
            # .civ6proj 里的 <Guid> 与 .CIV 里的 guid 一致
            proj_text = (out_dir / "Siqi_Demo_0001.civ6proj").read_text(encoding="utf-8")
            self.assertIn(f"<Guid>{guid_in_civ}</Guid>", proj_text)
            # 重复运行：guid 不变（同一 Mod 的 ModID 稳定）
            out_dir2 = Path(tmp) / "proj2"
            self._run("civ6proj", str(civ), "--out", str(out_dir2), "--update-civ")
            payload2 = json.loads(civ.read_text(encoding="utf-8"))
            info2 = payload2["workspace"]["基础信息"]["data"]["project_info"]
            self.assertEqual(str(info2.get("guid") or ""), guid_in_civ)
            self.assertIn(f"<Guid>{guid_in_civ}</Guid>", (out_dir2 / "Siqi_Demo_0001.civ6proj").read_text(encoding="utf-8"))

    def test_scaffold_false_flags_fall_back_to_wizard_defaults(self) -> None:
        # scaffold 的 supports_* = false 表示"未配置"，应按 ModBuddy 向导默认 true 输出
        with tempfile.TemporaryDirectory() as tmp:
            civ = Path(tmp) / "demo.CIV"
            create_new_project_file(civ, "测试工程", prefix="SIQI", infix=1, file_name="Siqi_Demo_0001")
            out_dir = Path(tmp) / "proj"
            self._run("civ6proj", str(civ), "--out", str(out_dir))
            text = (out_dir / "Siqi_Demo_0001.civ6proj").read_text(encoding="utf-8")
            self.assertIn("<SupportsSinglePlayer>true</SupportsSinglePlayer>", text)
            self.assertIn("<SupportsMultiplayer>true</SupportsMultiplayer>", text)

    def test_no_art_xml_option(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = Path(tmp) / "demo.CIV"
            create_new_project_file(civ, "测试工程", file_name="Siqi_Demo_0001")
            out_dir = Path(tmp) / "proj"
            self._run("civ6proj", str(civ), "--out", str(out_dir), "--no-art-xml")
            self.assertTrue((out_dir / "Siqi_Demo_0001.civ6proj").exists())
            self.assertFalse((out_dir / "Siqi_Demo_0001.Art.xml").exists())


class CustomFileCommandTestCase(unittest.TestCase):
    """custom-file：自定义 SQL/XML/Lua 文件通道（写工程目录 + 注册文件动作）。"""

    def _run(self, *argv: str) -> int:
        from modgen import cli
        parser = cli.build_parser()
        args = parser.parse_args(list(argv))
        return int(args.func(args))

    def _setup_project(self, tmp: str) -> tuple[Path, Path]:
        civ = Path(tmp) / "demo.CIV"
        create_new_project_file(civ, "测试工程", file_name="CF_Test")
        out_dir = Path(tmp) / "proj"
        self._run("civ6proj", str(civ), "--out", str(out_dir), "--update-civ")
        return civ, out_dir

    def test_write_registers_actions_by_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ, out_dir = self._setup_project(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Scripts/My.lua", "--content", "function Initialize() end")
            self._run("custom-file", "write", str(civ), "--path", "Data/Extra.sql", "--content", "INSERT INTO Types VALUES ('T','K');")
            self._run("custom-file", "write", str(civ), "--path", "Icons/Custom_Icons.xml", "--content", "<GameIcons></GameIcons>")
            self.assertTrue((out_dir / "Scripts" / "My.lua").exists())
            payload = json.loads(civ.read_text(encoding="utf-8"))
            info = payload["workspace"]["基础信息"]["data"]["file_info"]
            in_game = info["in_game_actions"]
            self.assertTrue(any(a["type"] == "AddGameplayScripts" and "Scripts/My.lua" in a["files"] for a in in_game))
            self.assertTrue(any(a["type"] == "UpdateDatabase" and "Data/Extra.sql" in a["files"] for a in in_game))
            front = info["front_end_actions"]
            self.assertTrue(any(a["type"] == "UpdateIcons" and "Icons/Custom_Icons.xml" in a["files"] for a in front))

    def test_write_explicit_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ, out_dir = self._setup_project(tmp)
            self._run("custom-file", "write", str(civ), "--path", "misc.lua", "--content", "x", "--action", "AddGameplayScripts")
            payload = json.loads(civ.read_text(encoding="utf-8"))
            in_game = payload["workspace"]["基础信息"]["data"]["file_info"]["in_game_actions"]
            self.assertTrue(any(a["type"] == "AddGameplayScripts" and "misc.lua" in a["files"] for a in in_game))

    def test_write_no_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ, out_dir = self._setup_project(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Data/X.sql", "--content", "x", "--no-action")
            payload = json.loads(civ.read_text(encoding="utf-8"))
            actions = payload["workspace"]["基础信息"]["data"]["file_info"]["in_game_actions"]
            self.assertFalse(any("Data/X.sql" in a.get("files", []) for a in actions))

    def test_traversal_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ, _out_dir = self._setup_project(tmp)
            code = self._run("custom-file", "write", str(civ), "--path", "../evil.lua", "--content", "x")
            self.assertNotEqual(code, 0)

    def test_list_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ, out_dir = self._setup_project(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Scripts/A.lua", "--content", "x")
            self._run("custom-file", "remove", str(civ), "--path", "Scripts/A.lua")
            payload = json.loads(civ.read_text(encoding="utf-8"))
            in_game = payload["workspace"]["基础信息"]["data"]["file_info"]["in_game_actions"]
            self.assertFalse(any("Scripts/A.lua" in a.get("files", []) for a in in_game))
            self.assertFalse((out_dir / "Scripts" / "A.lua").exists())

    def test_keep_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ, out_dir = self._setup_project(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Scripts/B.lua", "--content", "x")
            self._run("custom-file", "remove", str(civ), "--path", "Scripts/B.lua", "--keep-file")
            self.assertTrue((out_dir / "Scripts" / "B.lua").exists())


class SkillCommandTestCase(unittest.TestCase):
    """modgen skill：本地技能库全文检索（文件名+内容词频评分）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "01-core-tables").mkdir()
        (self.root / "07-techniques").mkdir()
        (self.root / "01-core-tables" / "modifiers.md").write_text(
            "# Modifiers 核心表\n\nTraitModifiers 挂载特质。\n", encoding="utf-8"
        )
        (self.root / "01-core-tables" / "types.md").write_text(
            "# Types 表\n\nTYPE 与 KIND 必须成对出现。\n", encoding="utf-8"
        )
        (self.root / "07-techniques" / "adjacency.md").write_text(
            "# 相邻加成\n\nAdjacency_YieldChanges 表，TilesRequired 每 N 格触发一次。\n相邻加成可被政策卡翻倍。\n",
            encoding="utf-8",
        )
        self.addCleanup(self._tmp.cleanup)

    def test_chinese_substring_search(self) -> None:
        from modgen.skills import search_skills

        results = search_skills("相邻加成", root=self.root)
        self.assertTrue(results)
        self.assertEqual(results[0]["rel"], "07-techniques/adjacency.md")

    def test_english_search_and_filename_boost(self) -> None:
        from modgen.skills import search_skills

        results = search_skills("modifiers", root=self.root)
        self.assertTrue(results)
        top = results[0]
        self.assertTrue(top["name_hit"], f"文件名命中应置顶：{top}")
        self.assertEqual(top["rel"], "01-core-tables/modifiers.md")
        # 内容命中同样可用（文件名的英文关键词命中）
        content_hits = search_skills("TraitModifiers", root=self.root)
        self.assertTrue(content_hits)
        self.assertIn("01-core-tables/modifiers.md", {item["rel"] for item in content_hits})

    def test_snippets_contain_match(self) -> None:
        from modgen.skills import search_skills

        results = search_skills("TilesRequired", root=self.root)
        self.assertTrue(results[0]["snippets"])
        self.assertIn("TilesRequired", results[0]["snippets"][0])

    def test_read_skill_file_full_text(self) -> None:
        from modgen.skills import read_skill_file

        content = read_skill_file("01-core-tables/types.md", root=self.root)
        self.assertEqual(content, "# Types 表\n\nTYPE 与 KIND 必须成对出现。\n")
        self.assertIsNone(read_skill_file("不存在.md", root=self.root))

    def test_traversal_rejected(self) -> None:
        from modgen.skills import read_skill_file

        self.assertIsNone(read_skill_file("../evil.md", root=self.root))
        self.assertIsNone(read_skill_file("01-core-tables/../../evil.md", root=self.root))

    def test_no_match_returns_empty(self) -> None:
        from modgen.skills import search_skills

        self.assertEqual(search_skills("绝不存在的词xyzzy", root=self.root), [])

    def test_missing_dir_returns_empty(self) -> None:
        from modgen.skills import search_skills

        self.assertEqual(search_skills("x", root=Path(self._tmp.name) / "none"), [])

    def test_real_skills_dir_searchable(self) -> None:
        """仓库根 skills/（随发布包分发）应可检索。"""
        from modgen.skills import default_skills_root, read_skill_file, search_skills

        if not default_skills_root().exists():
            self.skipTest("仓库根 skills/ 不存在")
        results = search_skills("Modifier")
        self.assertTrue(results, "真实技能库应能搜到 Modifier 相关文件")
        index = read_skill_file("05-modtools-civ/INDEX.md")
        self.assertIsNotNone(index)
        self.assertIn("ModTools", index)


class UIIconValidateTestCase(unittest.TestCase):
    """「UI图标」段校验：重名 / 缺源图 / 非法图标名分别报 ERROR。"""

    def _project(self, entries: list[dict]) -> dict:
        payload = build_project("测试工程", prefix="SIQI", infix=35)
        payload["workspace"]["UI图标"] = entries
        return payload

    def _errors(self, entries: list[dict], tmp: str = "") -> list[str]:
        output_dir = Path(tmp) if tmp else None
        from modgen.validator import validate_ui_icon_section

        return validate_ui_icon_section(entries, output_dir=output_dir)

    def test_clean_project_has_no_ui_icon_errors(self) -> None:
        payload = self._project([])
        self.assertEqual(validate_project(payload), [])

    def test_missing_source_reports_error_when_output_dir_known(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = self._errors([
                {"icon_name": "ICON_TEST_NEWS", "sizes": [32, 50],
                 "images": {"icon": {"path": str(Path(tmp) / "nope.png")}}},
            ], tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("ICON_TEST_NEWS", errors[0])
        self.assertIn("源 PNG 不存在", errors[0])

    def test_bad_icon_name_prefix_reports_error(self) -> None:
        errors = self._errors([{"icon_name": "TEST_NEWS_ICON"}])
        self.assertEqual(len(errors), 1)
        self.assertIn("必须以 ICON_ 开头", errors[0])

    def test_duplicate_icon_name_reports_error(self) -> None:
        errors = self._errors([
            {"icon_name": "ICON_TEST_DUP", "alias": "ICON_YIELD_FOOD"},
            {"icon_name": "ICON_TEST_DUP", "alias": "ICON_YIELD_FOOD"},
        ])
        self.assertEqual(len(errors), 1)
        self.assertIn("重复", errors[0])

    def test_entity_icon_conflict_reports_error(self) -> None:
        """落在实体内置图标命名空间（ICON_<实体头>_*）必须报 ERROR。"""
        self.assertIn("ICON_UNIT", rules.entity_icon_names())
        for candidate in ("ICON_UNIT", "ICON_UNIT_SIQI_NEWS", "ICON_DISTRICT_NEWS"):
            with self.subTest(candidate=candidate):
                errors = self._errors([{"icon_name": candidate, "alias": "ICON_YIELD_FOOD"}])
                self.assertEqual(len(errors), 1, errors)
                self.assertIn("命名空间", errors[0])

    def test_non_entity_namespace_is_accepted(self) -> None:
        """新闻/动作类图标（不属于实体命名空间）不报错。"""
        errors = self._errors([
            {"icon_name": "ICON_SIQI_WUJIU_NEWS_CITY", "alias": "ICON_YIELD_FOOD"},
            {"icon_name": "ICON_SIQI_WUJIU_ACT_SCOOP", "alias": "ICON_YIELD_FOOD"},
        ])
        self.assertEqual(errors, [])

    def test_missing_source_skipped_when_output_dir_unknown(self) -> None:
        """无法定位工程目录时不做源图存在性判定（避免误报）。"""
        errors = self._errors([{"icon_name": "ICON_TEST_NEWS", "images": {"icon": {"path": "news.png"}}}])
        self.assertEqual(errors, [])

    def test_alias_only_entry_is_valid(self) -> None:
        errors = self._errors([{"icon_name": "ICON_TEST_ALIAS", "alias": "ICON_YIELD_PRODUCTION"}])
        self.assertEqual(errors, [])

    def test_validate_project_includes_ui_icon_errors(self) -> None:
        payload = self._project([{"icon_name": "NO_PREFIX"}])
        errors = validate_project(payload)
        self.assertTrue(any("UI图标" in error and "ICON_ 开头" in error for error in errors), errors)


class CheckConflictsCommandTestCase(unittest.TestCase):
    """check-conflicts：自定义 SQL × 生成 SQL 冲突检测（需 PyQt；不可用则跳过）。"""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from modgen.custom_conflicts import check_conflicts  # noqa: F401
            from modgen.preview import build_preview_manifest  # noqa: F401
        except Exception:  # noqa: BLE001
            raise unittest.SkipTest("PyQt6 环境不可用，跳过 check-conflicts 测试")

    def _run(self, *argv: str) -> int:
        from modgen import cli
        parser = cli.build_parser()
        args = parser.parse_args(list(argv))
        return int(args.func(args))

    def _setup(self, tmp: str) -> Path:
        from ModTools_5_4.project.civ_project import save_civ_project
        from tests.sample_project import build_sample_project

        civ = Path(tmp) / "demo.CIV"
        # 注意：sample fixture 的基础信息是"扁平格式"（GUI 老工程同款），
        # 用于回归 custom-file 动作持久化
        save_civ_project(civ, build_sample_project())
        self._run("civ6proj", str(civ), "--out", str(Path(tmp) / "mod"), "--update-civ")
        return civ

    def test_flat_basic_info_action_persistence(self) -> None:
        """扁平基础信息下 custom-file 的动作必须持久化（回归：曾静默丢失）。"""
        with tempfile.TemporaryDirectory() as tmp:
            civ = self._setup(tmp)
            code = self._run("custom-file", "write", str(civ), "--path", "Data/Custom.sql", "--content", "SELECT 1;")
            self.assertEqual(code, 0)
            payload = json.loads(civ.read_text(encoding="utf-8"))
            section = payload["workspace"]["基础信息"]
            in_game = section["file_info"]["in_game_actions"]
            self.assertTrue(any("Data/Custom.sql" in a.get("files", []) for a in in_game), in_game)

    def test_primary_key_conflict_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = self._setup(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Data/Clash.sql", "--content",
                      "INSERT INTO Units (UnitType, Name) VALUES ('UNIT_SIQI_DEMO','X');")
            from modgen.custom_conflicts import check_conflicts

            result = check_conflicts(civ)
            self.assertTrue(result["errors"], result)
            conflict = result["errors"][0]
            self.assertEqual(conflict["table"], "Units")
            self.assertEqual(str(conflict["pk"]).upper(), "UNIT_SIQI_DEMO")
            self.assertIn("demo_Units.sql", str(conflict.get("generated_file")))

    def test_update_generated_table_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = self._setup(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Data/Patch.sql", "--content",
                      "UPDATE Units SET Cost=1 WHERE UnitType='UNIT_SIQI_DEMO';")
            from modgen.custom_conflicts import check_conflicts

            result = check_conflicts(civ)
            self.assertFalse(result["errors"])
            self.assertTrue(any("UPDATE/DELETE" in w["message"] for w in result["warnings"]), result["warnings"])

    def test_clean_custom_table_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = self._setup(tmp)
            self._run("custom-file", "write", str(civ), "--path", "Data/MyTable.sql", "--content",
                      "CREATE TABLE MyTable (X TEXT); INSERT INTO MyTable (X) VALUES ('A');")
            from modgen.custom_conflicts import check_conflicts

            result = check_conflicts(civ)
            self.assertFalse(result["errors"], result["errors"])
            self.assertFalse(result["warnings"], result["warnings"])
            self.assertIn("Data/MyTable.sql", [item["path"] for item in result["custom_files"]])

    def test_insert_select_inheritance_not_flagged(self) -> None:
        """INSERT...SELECT（CityNames 继承等合法模式）不产生主键对比。"""
        from modgen.custom_conflicts import parse_inserts

        rows = parse_inserts(
            "INSERT INTO CityNames (CivilizationType, CityName) SELECT 'CIV_X', CityName FROM CityNames WHERE CivilizationType='CIVILIZATION_AMERICA';"
        )
        self.assertEqual(rows, [])

    def test_cli_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            civ = self._setup(tmp)
            clean = self._run("check-conflicts", str(civ))
            self.assertEqual(clean, 0)
            self._run("custom-file", "write", str(civ), "--path", "Data/Clash.sql", "--content",
                      "INSERT INTO Units (UnitType, Name) VALUES ('UNIT_SIQI_DEMO','X');")
            bad = self._run("check-conflicts", str(civ))
            self.assertEqual(bad, 1)


if __name__ == "__main__":
    unittest.main()
