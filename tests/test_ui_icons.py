"""「UI图标」段回归测试：声明 → Icons.xml → IMG/Textures → 校验。

覆盖需求 R1~R6 与验收标准：
1. 单条目（sizes=[32,50]、256×256 源图）生成后 Icons.xml 有 2 行 atlas + 1 行定义；
2. 生成 IMG/ICON_TEST_NEWS_ICON_{32,50}.png 与 Textures 下 DDS+TEX；
3. alias 非空 → 只出 IconAliases 行，不出图集；
4. 老工程（无「UI图标」段）Icons.xml **逐字节一致**（回归，含顺序）；
5. 重名 / 缺源图 / 非法图标名分别给出 ERROR。
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.project.civ_project import save_civ_project  # noqa: E402
from ModTools_5_4.project.ui_icons import (  # noqa: E402
    DEFAULT_UI_ICON_SIZES,
    UI_ICON_SECTION,
    atlas_name_for,
    build_source_state_map,
    build_ui_icons_xml_rows,
    entity_icon_name_patterns,
    parse_sizes,
    read_png_size,
    validate_ui_icons,
)
from ModTools_5_4.ui.main_window import MainWindow  # noqa: E402
from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel  # noqa: E402

from sample_project import build_sample_project, sample_ui_icon_png  # noqa: E402


def _fresh_state() -> dict[str, object]:
    return {
        "alias_map": {}, "source_map": {}, "need_map": {},
        "extra_xlp_flags": {}, "extra_artdef_flags": {},
        "civs": {}, "moments_map": {}, "leader_xlp_flags": {},
        "art_xml_workspace_config": {}, "art_xml_source_config": {},
        "art_xml_source_path": "",
    }


class UIIconPureTestCase(unittest.TestCase):
    """纯函数层（无 Qt）：尺寸解析、图集名、XML 行、校验。"""

    def test_atlas_name_rule_strips_icon_prefix(self) -> None:
        self.assertEqual(atlas_name_for("ICON_SIQI_WUJIU_NEWS_CITY"), "ATLAS_SIQI_WUJIU_NEWS_CITY")
        self.assertEqual(atlas_name_for("icon_lower"), "ATLAS_LOWER")

    def test_parse_sizes_defaults_and_dedupes(self) -> None:
        self.assertEqual(parse_sizes(None), list(DEFAULT_UI_ICON_SIZES))
        self.assertEqual(parse_sizes(""), list(DEFAULT_UI_ICON_SIZES))
        self.assertEqual(parse_sizes("32, 50,32"), [32, 50])
        self.assertEqual(parse_sizes(["50", 32]), [32, 50])
        # 非法项被忽略；全非法 → 回退默认
        self.assertEqual(parse_sizes("abc,32"), [32])
        self.assertEqual(parse_sizes("abc"), list(DEFAULT_UI_ICON_SIZES))

    def test_rows_for_single_entry(self) -> None:
        entry = {
            "icon_name": "ICON_TEST_NEWS_ICON",
            "sizes": [32, 50],
            "images": {"icon": {"path": "D:/art/news.png"}},
        }
        built = build_ui_icons_xml_rows([entry])
        self.assertEqual(built["atlas_rows"], [
            '    <Row Name="ATLAS_TEST_NEWS_ICON" IconSize="32" Filename="ICON_TEST_NEWS_ICON_32"/>',
            '    <Row Name="ATLAS_TEST_NEWS_ICON" IconSize="50" Filename="ICON_TEST_NEWS_ICON_50"/>',
        ])
        self.assertEqual(built["def_rows"], [
            '    <Row Name="ICON_TEST_NEWS_ICON" Atlas="ATLAS_TEST_NEWS_ICON" Index="0"/>',
        ])
        self.assertEqual(built["alias_rows"], [])
        self.assertEqual(built["errors"], [])

    def test_alias_entry_outputs_alias_row_only(self) -> None:
        entry = {
            "icon_name": "ICON_TEST_ALIAS",
            "alias": "ICON_YIELD_PRODUCTION",
            "images": {"icon": {"path": "D:/art/news.png"}},
        }
        built = build_ui_icons_xml_rows([entry])
        self.assertEqual(built["atlas_rows"], [])
        self.assertEqual(built["def_rows"], [])
        self.assertEqual(built["alias_rows"], ['    <Row Name="ICON_TEST_ALIAS" OtherName="ICON_YIELD_PRODUCTION"/>'])

    def test_missing_source_is_warning_and_skipped(self) -> None:
        built = build_ui_icons_xml_rows([{"icon_name": "ICON_TEST_NO_SOURCE"}])
        self.assertEqual(built["atlas_rows"], [])
        self.assertEqual(built["def_rows"], [])
        self.assertEqual([item["kind"] for item in built["warnings"]], ["source_missing"])
        self.assertEqual(built["errors"], [])

    def test_entity_conflict_is_error(self) -> None:
        entry = {"icon_name": "ICON_DISTRICT_SIQI_DEMO", "images": {"icon": {"path": "D:/x.png"}}}
        built = build_ui_icons_xml_rows([entry], entity_icon_names=["ICON_DISTRICT_SIQI_DEMO"])
        self.assertEqual([item["kind"] for item in built["errors"]], ["icon_name_entity_conflict"])
        self.assertEqual(built["def_rows"], [])

    def test_entity_namespace_prefix_conflict_is_error(self) -> None:
        """真实图标名展开出的命名空间同样拦截（换后缀也仍会撞车）。"""
        entity_names = entity_icon_name_patterns([
            "ICON_DISTRICT_SIQI_DEMO", "ICON_UNIT_SIQI_DEMO", "ICON_UNIT_SIQI_DEMO_PORTRAIT",
        ])
        self.assertIn("ICON_DISTRICT", entity_names)
        self.assertIn("ICON_UNIT", entity_names)
        for candidate in ("ICON_DISTRICT_NEWS", "ICON_UNIT_NEWS"):
            with self.subTest(candidate=candidate):
                built = build_ui_icons_xml_rows(
                    [{"icon_name": candidate, "images": {"icon": {"path": "D:/x.png"}}}],
                    entity_icon_names=entity_names,
                )
                self.assertEqual([item["kind"] for item in built["errors"]], ["icon_name_entity_conflict"])

    def test_news_icon_names_are_accepted(self) -> None:
        """需求场景里的图标名（SIQI_WUJIU_*）不属于实体命名空间。"""
        entry = {
            "icon_name": "ICON_SIQI_WUJIU_NEWS_CITY",
            "sizes": [32, 50],
            "images": {"icon": {"path": "D:/x.png"}},
        }
        built = build_ui_icons_xml_rows(
            [entry],
            entity_icon_names=entity_icon_name_patterns([
                "ICON_DISTRICT_SIQI_DEMO", "ICON_UNIT_SIQI_DEMO", "ICON_CIVILIZATION_SIQI_DEMO",
            ]),
        )
        self.assertEqual(built["errors"], [])
        self.assertEqual(built["icon_names"], ["ICON_SIQI_WUJIU_NEWS_CITY"])

    def test_duplicate_and_bad_prefix_are_errors(self) -> None:
        built = build_ui_icons_xml_rows([
            {"icon_name": "ICON_TEST_DUP"},
            {"icon_name": "ICON_TEST_DUP"},
            {"icon_name": "TEST_NO_PREFIX"},
            {"icon_name": ""},
        ])
        kinds = [item["kind"] for item in built["errors"]]
        self.assertEqual(kinds, ["icon_name_duplicate", "icon_name_prefix", "icon_name_missing"])

    def test_validate_reports_missing_and_small_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            small = Path(tmp) / "small.png"
            small.write_bytes(sample_ui_icon_png().read_bytes()[:0] or b"")
            missing_entry = {"icon_name": "ICON_TEST_MISSING", "images": {"icon": {"path": str(Path(tmp) / "nope.png")}}}
            report = validate_ui_icons([missing_entry], output_dir=Path(tmp))
            self.assertEqual([item["kind"] for item in report["errors"]], ["source_not_found"])

    def test_validate_source_too_small_warns(self) -> None:
        src = sample_ui_icon_png()  # 256×256
        if not src.is_file():
            self.skipTest("示例 PNG 不可用")
        entry = {"icon_name": "ICON_TEST_BIG", "sizes": [512], "images": {"icon": {"path": str(src)}}}
        report = validate_ui_icons([entry], output_dir=src.parent)
        self.assertEqual(report["errors"], [])
        self.assertEqual([item["kind"] for item in report["warnings"]], ["source_too_small"])

    def test_source_state_map_skips_alias_and_empty(self) -> None:
        states = build_source_state_map([
            {"icon_name": "ICON_A", "images": {"icon": {"path": "p.png"}}},
            {"icon_name": "ICON_B", "alias": "ICON_YIELD_FOOD"},
            {"icon_name": "ICON_C"},
        ])
        self.assertEqual(states, {"ICON_A": {"path": "p.png"}})

    def test_read_png_size(self) -> None:
        src = sample_ui_icon_png()
        if not src.is_file():
            self.skipTest("示例 PNG 不可用")
        self.assertEqual(read_png_size(src), (256, 256))
        self.assertIsNone(read_png_size(src.parent / "missing.png"))


class UIIconIconsXmlRegressionTestCase(unittest.TestCase):
    """Icons.xml 回归：老工程逐字节一致 + UI 图标只追加。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.panel = ArtWorkspacePanel()

    def setUp(self) -> None:
        self.sections = build_sample_project().sections
        self.panel._state = _fresh_state()
        self.panel.refresh_from_sections(self.sections)

    def _icons_xml(self) -> str:
        return self.panel._build_icons_xml()

    def test_legacy_project_output_is_byte_identical(self) -> None:
        """无「UI图标」段的工程：产物必须与「不声明该段」的历史结果逐字节一致。"""
        self.sections[UI_ICON_SECTION] = []
        self.panel.refresh_from_sections(self.sections)
        without_section = self._icons_xml()

        # 老工程连节点都没有（normalize 会补空列表，这里模拟最老结构）
        legacy_sections = dict(self.sections)
        legacy_sections.pop(UI_ICON_SECTION, None)
        self.panel.refresh_from_sections(legacy_sections)
        missing_section = self._icons_xml()

        self.assertEqual(without_section, missing_section)
        self.assertNotIn("ATLAS_TEST_NEWS_ICON", without_section)

    def test_ui_icon_rows_are_appended_after_entities(self) -> None:
        with_ui = self._icons_xml()

        self.sections[UI_ICON_SECTION] = []
        self.panel.refresh_from_sections(self.sections)
        baseline = self._icons_xml()

        self.assertIn('    <Row Name="ATLAS_TEST_NEWS_ICON" IconSize="32" Filename="ICON_TEST_NEWS_ICON_32"/>', with_ui)
        self.assertIn('    <Row Name="ATLAS_TEST_NEWS_ICON" IconSize="50" Filename="ICON_TEST_NEWS_ICON_50"/>', with_ui)
        self.assertIn('    <Row Name="ICON_TEST_NEWS_ICON" Atlas="ATLAS_TEST_NEWS_ICON" Index="0"/>', with_ui)
        self.assertNotIn("ATLAS_TEST_NEWS_ICON", baseline)

        # 11 类实体的行内容与顺序完全不变：去掉 UI 图标追加的行即等于 baseline
        baseline_lines = baseline.splitlines()
        filtered = [
            line for line in with_ui.splitlines()
            if "TEST_NEWS_ICON" not in line
        ]
        self.assertEqual(filtered, baseline_lines)

    def test_entity_icon_names_cache_matches_definitions(self) -> None:
        self.sections[UI_ICON_SECTION] = []
        self.panel.refresh_from_sections(self.sections)
        names = self.panel.entity_icon_names()
        self.assertIn("ICON_DISTRICT_SIQI_DEMO", names)
        self.assertIn("ICON_UNIT_SIQI_DEMO_PORTRAIT", names)
        self.assertNotIn("ATLAS_DISTRICT_SIQI_DEMO", names)

    def test_missing_source_entry_produces_no_rows(self) -> None:
        self.sections[UI_ICON_SECTION] = [{"icon_name": "ICON_TEST_NO_SOURCE"}]
        self.panel.refresh_from_sections(self.sections)
        xml = self._icons_xml()
        self.assertNotIn("ATLAS_TEST_NO_SOURCE", xml)
        self.assertNotIn("ICON_TEST_NO_SOURCE", xml)


class UIIconPanelEditingTestCase(unittest.TestCase):
    """GUI 编辑流程：美术页「UI图标」区 → 工程分节写回（R5）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.sections: dict[str, object] = {UI_ICON_SECTION: []}
        self.notified: list[list[dict[str, object]]] = []
        self.panel = ArtWorkspacePanel(
            ui_icon_notifier=lambda entries: self.notified.append(entries),
            output_dir_provider=lambda: None,
        )
        self.panel._state = _fresh_state()
        self.panel.refresh_from_sections(self.sections)

    def _rows(self) -> list[dict[str, object]]:
        return list(self.sections.get(UI_ICON_SECTION) or [])

    def _fill_row(self, index: int, *, icon_name: str, sizes: str = "32,50", path: str = "", alias: str = "") -> None:
        from PyQt6.QtWidgets import QLineEdit

        self.panel._handle_ui_icon_name_changed(index, QLineEdit(icon_name))
        self.panel._handle_ui_icon_sizes_changed(index, QLineEdit(sizes))
        if path:
            self.panel._handle_ui_icon_source_changed(index, QLineEdit(path))
        if alias:
            self.panel._handle_ui_icon_alias_changed(index, QLineEdit(alias))

    def test_add_and_delete_row_writes_section(self) -> None:
        self.panel._handle_ui_icon_add()
        self.assertEqual(len(self.panel._ui_icon_rows), 1)
        # 空行不入工程（不留垃圾条目）
        self.assertEqual(self._rows(), [])

        self._fill_row(0, icon_name="ICON_TEST_GUI", path="D:/art/x.png")
        self.assertEqual(self._rows(), [{
            "icon_name": "ICON_TEST_GUI",
            "sizes": [32, 50],
            "images": {"icon": {"path": "D:/art/x.png"}},
        }])
        self.assertTrue(self.notified, "写回应通知 WorkspacePage")
        self.assertEqual(self.notified[-1], self._rows())

        self.panel._ui_icon_table.setCurrentCell(0, 0)
        self.panel._handle_ui_icon_remove()
        self.assertEqual(self._rows(), [])

    def test_icon_name_gets_icon_prefix_automatically(self) -> None:
        self.panel._handle_ui_icon_add()
        self._fill_row(0, icon_name="siqi_news_city", alias="ICON_YIELD_FOOD")
        self.assertEqual(self._rows()[0]["icon_name"], "ICON_SIQI_NEWS_CITY")

    def test_note_and_alias_are_optional_fields(self) -> None:
        from PyQt6.QtWidgets import QLineEdit

        self.panel._handle_ui_icon_add()
        self._fill_row(0, icon_name="ICON_TEST_NOTE", alias="ICON_YIELD_FOOD")
        self.panel._handle_ui_icon_note_changed(0, QLineEdit("城建图标"))
        entry = self._rows()[0]
        self.assertEqual(entry["name_zh"], "城建图标")
        self.assertEqual(entry["alias"], "ICON_YIELD_FOOD")
        # 别名条目不写源图字段
        self.assertNotIn("images", entry)

    def test_default_sizes_are_not_persisted(self) -> None:
        """尺寸留空 = 用默认值，不把默认列表固化进条目（保持 .CIV 精简）。"""
        self.panel._handle_ui_icon_add()
        self._fill_row(0, icon_name="ICON_TEST_DEFAULT_SIZES", sizes="", path="D:/art/x.png")
        entry = self._rows()[0]
        self.assertNotIn("sizes", entry)
        self.assertEqual(self.panel._ui_icon_rows[0].sizes, list(DEFAULT_UI_ICON_SIZES))

    def test_reload_without_sizes_keeps_field_empty(self) -> None:
        self.sections[UI_ICON_SECTION] = [{
            "icon_name": "ICON_TEST_ABSENT_SIZES",
            "images": {"icon": {"path": "D:/art/x.png"}},
        }]
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(self.panel._ui_icon_rows[0].sizes_text, "")
        self.assertEqual(self.panel._ui_icon_rows[0].sizes, list(DEFAULT_UI_ICON_SIZES))

    def test_clear_image_removes_path(self) -> None:
        self.panel._handle_ui_icon_add()
        self._fill_row(0, icon_name="ICON_TEST_CLEAR", path="D:/art/x.png")
        self.assertIn("images", self._rows()[0])
        self.panel._handle_ui_icon_clear_image(0)
        self.assertNotIn("images", self._rows()[0])

    def test_validate_ui_icon_entries_reports_entity_conflict(self) -> None:
        self.panel._ui_icon_entities_provider = lambda: ["ICON_DISTRICT_SIQI_DEMO", "ICON_DISTRICT"]
        self.panel._handle_ui_icon_add()
        self._fill_row(0, icon_name="ICON_DISTRICT_NEWS", alias="ICON_YIELD_FOOD")
        errors = self.panel.validate_ui_icon_entries()
        self.assertEqual([item["kind"] for item in errors], ["icon_name_entity_conflict"])

    def test_refresh_reloads_rows_from_sections(self) -> None:
        src = sample_ui_icon_png()
        self.sections[UI_ICON_SECTION] = [{
            "icon_name": "ICON_TEST_RELOAD",
            "name_zh": "重载",
            "sizes": [50],
            "images": {"icon": {"path": str(src)}},
        }]
        self.panel.refresh_from_sections(self.sections)
        self.assertEqual(self.panel._ui_icon_table.rowCount(), 1)
        row = self.panel._ui_icon_rows[0]
        self.assertEqual(row.icon_name, "ICON_TEST_RELOAD")
        self.assertEqual(row.sizes, [50])
        # 源图存在且 256px ≥ max(sizes) → 状态列显示真实尺寸
        status_text, _tip = self.panel._ui_icon_status_text(row)
        self.assertEqual(status_text, "256×256")


class UIIconGenerationTestCase(unittest.TestCase):
    """端到端：AI 控制接口驱动 generate_all → Icons.xml + IMG + Textures。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.window = MainWindow(config)
        cls.window.show()
        cls.page = cls.window.workspace_page()
        from ModTools_5_4.ai.control_server import ControlContext

        cls.context = ControlContext(cls.window, cls.page)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = build_sample_project()
        civ_path = Path(self._tmp.name) / "ui_icon.CIV"
        save_civ_project(civ_path, self.project)
        self.window.open_project_file(civ_path)

    def _create_and_generate(self) -> Path:
        target_dir = Path(self._tmp.name) / "mod"
        created = self.context.execute(
            "civ6proj_create", {"directory": str(target_dir), "file_name": "Ui_Icon_Mod"}
        )
        self.assertTrue(created["ok"], created)
        generated = self.context.execute("generate_all", {"overwrite": "all"})
        self.assertTrue(generated["ok"], generated)
        return target_dir

    def test_generate_all_outputs_icons_img_and_textures(self) -> None:
        target_dir = self._create_and_generate()

        icons_xml = target_dir / "Icons" / "Ui_Icon_Mod_Icons.xml"
        self.assertTrue(icons_xml.is_file(), "未生成 Icons/<工程名>_Icons.xml")
        text = icons_xml.read_text(encoding="utf-8")
        self.assertIn('Name="ATLAS_TEST_NEWS_ICON" IconSize="32" Filename="ICON_TEST_NEWS_ICON_32"', text)
        self.assertIn('Name="ATLAS_TEST_NEWS_ICON" IconSize="50" Filename="ICON_TEST_NEWS_ICON_50"', text)
        self.assertIn('Name="ICON_TEST_NEWS_ICON" Atlas="ATLAS_TEST_NEWS_ICON" Index="0"', text)

        for size in (32, 50):
            png = target_dir / "IMG" / f"ICON_TEST_NEWS_ICON_{size}.png"
            self.assertTrue(png.is_file(), f"未生成 IMG/ICON_TEST_NEWS_ICON_{size}.png")
            self.assertEqual(read_png_size(png), (size, size), f"{png.name} 尺寸不正确")
            for suffix in (".dds", ".tex"):
                texture = target_dir / "Textures" / f"ICON_TEST_NEWS_ICON_{size}{suffix}"
                self.assertTrue(texture.is_file(), f"未生成 Textures/ICON_TEST_NEWS_ICON_{size}{suffix}")

    def test_generate_all_blocks_on_invalid_ui_icon(self) -> None:
        """源图不存在 → generate_all 返回 ui_icons_invalid，且不写入 Icons.xml。"""
        self.project.sections[UI_ICON_SECTION] = [{
            "icon_name": "ICON_TEST_BROKEN",
            "sizes": [32],
            "images": {"icon": {"path": str(Path(self._tmp.name) / "missing.png")}},
        }]
        civ_path = Path(self._tmp.name) / "broken.CIV"
        save_civ_project(civ_path, self.project)
        self.window.open_project_file(civ_path)

        target_dir = Path(self._tmp.name) / "mod_broken"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "Broken_Mod"})
        result = self.context.execute("generate_all", {"overwrite": "all"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "ui_icons_invalid")
        self.assertTrue(any("ICON_TEST_BROKEN" in str(item.get("message")) for item in result["issues"]))
        self.assertFalse((target_dir / "Icons" / "Broken_Mod_Icons.xml").exists())

    def test_ai_state_exposes_ui_icon_issues(self) -> None:
        state = self.context.execute("get_state", {})
        self.assertIn("ui_icon_issues", state)
        self.assertEqual(state["ui_icon_issues"]["errors"], [])
        self.assertEqual(state["sections"][UI_ICON_SECTION]["kind"], "list")
        self.assertEqual(state["sections"][UI_ICON_SECTION]["count"], 1)

    def test_manifest_preview_includes_ui_icon_img_plan(self) -> None:
        target_dir = Path(self._tmp.name) / "mod_preview"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "Preview_Mod"})
        manifest = self.context.execute("get_manifest", {})
        self.assertIn("Icons/Preview_Mod_Icons.xml", manifest["files"])

        # IMG/Textures 产物不在文本文件清单里，而由 IMG / 纹理输出计划驱动
        img_paths = {str(plan.get("relative_path")) for plan in self.page._build_img_output_plan()}
        self.assertIn("IMG/ICON_TEST_NEWS_ICON_32.png", img_paths)
        self.assertIn("IMG/ICON_TEST_NEWS_ICON_50.png", img_paths)
        texture_names = {str(plan.get("name")) for plan in self.page._build_textures_output_plan()}
        self.assertIn("ICON_TEST_NEWS_ICON_32", texture_names)
        self.assertIn("ICON_TEST_NEWS_ICON_50", texture_names)


if __name__ == "__main__":
    unittest.main()
