"""阶段 2 修复回归测试（2026-08-16）。

覆盖的修复项：
- A2 db/interface LOC 查询缓存（行为不变 + 缓存生效）
- A3 artdef 文件级解析缓存
- B1 delete_requests 路径穿越校验
- B2 必填校验不再改写工程数据
- B3 Type 简称净化（CJK 放行）
- B4 AiFavoredItems int() 兜底 / colors 全空不输出 ''
- C1 复制政策卡/信仰重算 type
- C2 晋升树跨树节点 abbr 全局去重
- C3 _moment_meta/_civ_meta 渲染不写回 state
- C4 批量生成 ModifierId 去重（不排除当前行）
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.ui.pages.workspace_page import WorkspacePage  # noqa: E402
from ModTools_5_4.ui.pages.modifier_workspace import HomePage as ModifierHomePage  # noqa: E402
from ModTools_5_4.ui.pages.great_people_editor import _sanitize_short_token  # noqa: E402
from ModTools_5_4.ui.pages.group_workspace import SectionGroupWorkspacePanel  # noqa: E402

from sample_project import build_sample_project  # noqa: E402


class DeletePathSafetyTestCase(unittest.TestCase):
    """B1：delete_requests 路径穿越校验。"""

    def test_safe_relative_path_normalized(self) -> None:
        self.assertEqual(WorkspacePage._safe_delete_relative_path("Data\\x.sql"), "Data/x.sql")
        self.assertEqual(WorkspacePage._safe_delete_relative_path("./Data/x.sql"), "Data/x.sql")

    def test_unsafe_paths_rejected(self) -> None:
        for bad in ("../evil.sql", "a/../../evil.sql", "/abs/path.sql", "C:/evil.sql", "C:\\evil.sql", ""):
            with self.subTest(path=bad):
                self.assertIsNone(WorkspacePage._safe_delete_relative_path(bad), bad)


class ValidationNoWriteBackTestCase(unittest.TestCase):
    """B2：必填校验不写回工程数据（取消生成后内存不被污染）。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_validate_does_not_mutate_entries(self) -> None:
        self.page._project = build_sample_project()
        # 造一个缺 FormationClass 的单位条目（无 table_data）
        self.page._project.sections["单位"] = [
            {"name": "缺字段单位", "abbr": "BAD", "type": "UNIT_SIQI_BAD"}
        ]
        with mock.patch("ModTools_5_4.ui.pages.workspace_page.QMessageBox.warning") as warn:
            ok = self.page._validate_required_main_table_fields(validate_units=True, validate_districts=False)
        self.assertFalse(ok)
        warn.assert_called_once()
        entry = self.page._project.sections["单位"][0]
        self.assertNotIn("table_data", entry, "校验不应把 table_data 写入工程数据")
        self.assertNotIn("FormationClass", entry, "校验不应把默认值写入工程数据")

    def test_validate_ok_with_default_rule(self) -> None:
        """MilitaryDomain 有默认值（NO_DOMAIN）视为满足且不写回。"""
        self.page._project = build_sample_project()
        self.page._project.sections["区域"] = [
            {"name": "缺字段区域", "abbr": "BADD", "type": "DISTRICT_SIQI_BADD",
             "table_data": {"Name": "缺字段区域"}}
        ]
        ok = self.page._validate_required_main_table_fields(validate_units=False, validate_districts=True)
        self.assertTrue(ok)
        table_data = self.page._project.sections["区域"][0]["table_data"]
        self.assertNotIn("MilitaryDomain", table_data, "默认值不应被写回")


class ShortTokenSanitizeTestCase(unittest.TestCase):
    """B3：Type 简称只允许 ASCII（CJK 不进入 Type）。"""

    def test_cjk_stripped(self) -> None:
        self.assertEqual(_sanitize_short_token("孔子ABC"), "ABC")
        self.assertEqual(_sanitize_short_token("测试_AB"), "_AB")

    def test_ascii_kept(self) -> None:
        self.assertEqual(_sanitize_short_token("abc_123"), "ABC_123")


class LocCacheBehaviorTestCase(unittest.TestCase):
    """A2：LOC 查询缓存不改变查询行为。"""

    def test_repeated_lookup_consistent(self) -> None:
        from ModTools_5_4.db import interface as db_interface

        db_interface._invalidate_caches()
        a = db_interface.get_chinese_text_for_tag("LOC_UNIT_SPECIAL_CAVALRY_NAME")
        b = db_interface.get_chinese_text_for_tag("LOC_UNIT_SPECIAL_CAVALRY_NAME")
        self.assertEqual(a, b)


class ArtdefFileCacheTestCase(unittest.TestCase):
    """A3：artdef 文件级解析缓存。"""

    def test_parse_cache_returns_same_root(self) -> None:
        from ModTools_5_4 import artdef_parser as ap

        candidates = ap._candidate_district_files()
        if not candidates:
            self.skipTest("无 From 参考文件")
        path = candidates[0]
        root1 = ap._parse_file_cached(path)
        root2 = ap._parse_file_cached(path)
        self.assertIsNotNone(root1)
        self.assertIs(root1, root2, "相同文件重复解析应命中缓存")


class AiFavoredIntFallbackTestCase(unittest.TestCase):
    """B4：AiFavoredItems 脏数据不抛异常。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_dirty_favored_values_do_not_crash(self) -> None:
        self.page._project = build_sample_project()
        self.page._project.sections["议程"] = [
            {
                "type": "AGENDA_SIQI_DIRTY",
                "abbr": "DIRTY",
                "name": "脏数据议程",
                "table_data": {"Name": "脏数据议程"},
                "subtables": {
                    "AiLists": [
                        {
                            "ListType": "AI_LIST_DIRTY",
                            "System": "Bias",
                            "AiFavoredItems": [
                                {"Item": "TECH_SAILING", "Favored": "abc", "Value": "xyz"},
                                {"Item": "TECH_CARTOGRAPHY", "Favored": 0, "Value": 2},
                            ],
                        }
                    ]
                },
            }
        ]
        sql = self.page._build_agenda_sql_pair()[0]
        self.assertIn("TECH_SAILING", sql)
        self.assertIn("TECH_CARTOGRAPHY", sql)


class ColorsAllEmptyTestCase(unittest.TestCase):
    """B4：球衣色全空时不输出空颜色引用。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_all_empty_colors_skipped(self) -> None:
        self.page._project = build_sample_project()
        self.page._project.sections["领袖"] = [
            {
                "name": "无配色领袖",
                "abbr": "NOC",
                "type": "LEADER_SIQI_NOC",
                "colors": {"j1_primary": "", "j1_secondary": "", "j2_primary": "", "j2_secondary": "",
                           "j3_primary": "", "j3_secondary": "", "j4_primary": "", "j4_secondary": ""},
            }
        ]
        sql = self.page._build_colors_sql()
        self.assertEqual(sql, "", "球衣色全空不应生成 PlayerColors 行")


class DuplicatePolicyTypeTestCase(unittest.TestCase):
    """C1：复制政策卡后 type 必须重算。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_duplicate_policy_recomputes_type(self) -> None:
        self.page._project = build_sample_project()
        self.page._project.sections["基础信息"] = {
            "format": "MODTOOLS54_BASIC_INFO_WORKSPACE",
            "schema_version": "0.1.0",
            "data": {
                "global_settings": {"prefix": "SIQI", "infix": 99, "language": "简体中文"},
                "project_info": {"mod_name": "测试"},
                "file_info": {},
            },
        }
        # 模拟真实流程：先装载编辑器（基础信息 prefix 进入编辑器状态），再替换为测试条目
        self.page._load_workspace_sections_into_editors()
        self.page._project.sections["政策卡"] = [
            {"name": "测试政策", "abbr": "POL1", "type": "POLICY_SIQI_P0099_POL1",
             "icon_image_name": "ICON_POLICY_SIQI_P0099_POL1"}
        ]
        payload = dict(self.page._project.sections["政策卡"][0])
        self.page._handle_duplicate_section_item("政策卡", 0, payload)
        entries = self.page._project.sections["政策卡"]
        self.assertEqual(len(entries), 2)
        self.assertNotEqual(entries[0]["type"], entries[1]["type"], "复制后 type 必须不同")
        self.assertNotEqual(entries[0]["abbr"], entries[1]["abbr"])
        # 复制条目经编辑器回写后 type 应带前缀且与 abbr 匹配
        self.assertIn("POLICY_SIQI_P0099_", entries[1]["type"])


class PromotionCrossTreeAbbrTestCase(unittest.TestCase):
    """C2：两棵晋升树同 abbr 节点生成不同 Type。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.page = WorkspacePage()

    def test_same_node_abbr_across_trees_unique(self) -> None:
        self.page._project = build_sample_project()
        node = {"abbr": "L1C1", "name_cn": "节点", "desc_cn": "", "level": 1, "column": 1,
                "prereq_indices": [], "modifier_ids": []}
        self.page._project.sections["单位晋升"] = [
            {"type": "PROMOTION_CLASS_SIQI_T1", "name": "树一", "nodes": [dict(node)]},
            {"type": "PROMOTION_CLASS_SIQI_T2", "name": "树二", "nodes": [dict(node)]},
        ]
        parts = self.page._build_promotion_tree_parts()
        types_rows, _classes, promotions_rows, _prereqs, _text = parts
        promotion_types = [
            row for row in types_rows
            if "'KIND_PROMOTION'" in row
        ]
        self.assertEqual(len(promotion_types), 2, "两棵树的节点应有各自的 PROMOTION Type")
        self.assertNotEqual(promotion_types[0], promotion_types[1])


class ArtMetaNoWriteOnRenderTestCase(unittest.TestCase):
    """C3：渲染路径不写回 state。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])

    def test_moment_meta_default_no_persist(self) -> None:
        from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel

        panel = ArtWorkspacePanel()
        meta = panel._moment_meta("k_not_exists")
        self.assertIsNotNone(meta)
        self.assertNotIn("k_not_exists", panel._state.get("moments_map", {}), "只读不应写回 state")

    def test_moment_meta_persist_writes(self) -> None:
        from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel

        panel = ArtWorkspacePanel()
        panel._moment_meta("k_persist", persist=True)
        self.assertIn("k_persist", panel._state.get("moments_map", {}), "persist=True 应写回 state")


class BatchModifierDedupTestCase(unittest.TestCase):
    """C4：批量生成去重不排除当前选中行。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dedup_includes_current_when_requested(self) -> None:
        page = ModifierHomePage()
        page._modifier_editor_index = 0
        page._modifiers = [mock.Mock(modifier_id="MODIFIER_SIQI_0001_TEST")]
        result = page._deduplicate_modifier_id("MODIFIER_SIQI_0001_TEST", exclude_current=False)
        self.assertNotEqual(result, "MODIFIER_SIQI_0001_TEST", "批量场景当前行也应参与去重")

    def test_dedup_excludes_current_by_default(self) -> None:
        page = ModifierHomePage()
        page._modifier_editor_index = 0
        page._modifiers = [mock.Mock(modifier_id="MODIFIER_SIQI_0001_TEST")]
        result = page._deduplicate_modifier_id("MODIFIER_SIQI_0001_TEST")
        self.assertEqual(result, "MODIFIER_SIQI_0001_TEST", "编辑器内改名场景仍排除当前行")


if __name__ == "__main__":
    unittest.main()
