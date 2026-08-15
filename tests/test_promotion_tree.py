"""晋升树编辑器测试。

覆盖：
- 模版节点导出时自动补全 abbr（L{级}C{列}，冲突加后缀）
- 已有手动 abbr 原样保留
- 卡片直接编辑（无需双击/Enter）：改字即存到节点并反映到导出
- 拖拽条拖动改 Level/Column
- 随机模式卡片直接编辑
- set_entry 重载文本
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.ui.pages.group_workspace import (  # noqa: E402
    _PromotionNodeCard,
    _PromotionNode,
    PromotionTreeEditor,
    _build_entity_type,
)


def _build_editor() -> PromotionTreeEditor:
    shared = lambda: {"prefix": "SIQI", "infix": 35}
    type_builder = lambda s, h, m, n: _build_entity_type(s, head=h, midfix_code=m, short_name=n)
    editor = PromotionTreeEditor(shared, type_builder)
    editor.resize(980, 700)
    editor.show()
    QApplication.processEvents()
    return editor


class PromotionTreeTemplateAbbrTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_template_nodes_get_position_abbr(self) -> None:
        editor = _build_editor()
        editor._apply_template("2221")
        payload = editor.export_entry()
        abbrs = [n["abbr"] for n in payload["nodes"]]
        self.assertEqual(len(abbrs), 7)
        self.assertTrue(all(abbrs))
        self.assertEqual(len(set(abbrs)), 7)
        self.assertEqual(abbrs[:2], ["L1C1", "L1C3"])

    def test_template_2212_abbr(self) -> None:
        editor = _build_editor()
        editor._apply_template("2212")
        payload = editor.export_entry()
        abbrs = [n["abbr"] for n in payload["nodes"]]
        self.assertEqual(abbrs[4], "L3C2")
        self.assertEqual(abbrs[5], "L4C1")
        self.assertEqual(abbrs[6], "L4C3")

    def test_manual_abbr_preserved(self) -> None:
        editor = _build_editor()
        editor.set_entry(
            {"abbr": "CT", "name": "树", "mode": "tree", "nodes": [
                {"abbr": "DEMO_A", "name_cn": "老晋升", "desc_cn": "老描述", "level": 1, "column": 1},
            ]},
            "fallback",
        )
        payload = editor.export_entry()
        self.assertEqual(payload["nodes"][0]["abbr"], "DEMO_A")
        self.assertEqual(payload["nodes"][0]["name_cn"], "老晋升")

    def test_auto_abbr_avoids_collision_with_manual(self) -> None:
        editor = _build_editor()
        editor._nodes = []
        editor._nodes.append(_PromotionNode(abbr="L1C1", level=1, column=1))
        editor._nodes.append(_PromotionNode(level=1, column=1))
        payload = editor.export_entry()
        abbrs = [n["abbr"] for n in payload["nodes"]]
        self.assertEqual(abbrs[0], "L1C1")
        self.assertEqual(abbrs[1], "L1C1_2")


class PromotionTreeDirectEditTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_cards_created_and_edit_saves_immediately(self) -> None:
        editor = _build_editor()
        editor._apply_template("2221")
        cards = editor.findChildren(_PromotionNodeCard)
        self.assertEqual(len(cards), 7)
        card0 = editor._tree_canvas._cards[0]
        card0._name_edit.setText("攻城术")
        card0._desc_edit.setText("近战单位攻城加成 +7")
        QApplication.processEvents()
        self.assertEqual(editor._nodes[0].name_cn, "攻城术")
        self.assertEqual(editor._nodes[0].desc_cn, "近战单位攻城加成 +7")
        payload = editor.export_entry()
        self.assertEqual(payload["nodes"][0]["name_cn"], "攻城术")
        self.assertEqual(payload["nodes"][0]["abbr"], "L1C1")

    def test_drag_strip_moves_node(self) -> None:
        editor = _build_editor()
        editor._apply_template("2221")
        canvas = editor._tree_canvas
        card0 = canvas._cards[0]
        start = card0.mapToGlobal(QPoint(50, 8))
        canvas._on_card_drag_pressed(0, start)
        canvas._on_card_drag_moved(0, card0.mapToGlobal(QPoint(50 + 230, 8)))
        canvas._on_card_drag_released(0)
        self.assertEqual((editor._nodes[0].level, editor._nodes[0].column), (1, 2))

    def test_card_click_selects_node(self) -> None:
        editor = _build_editor()
        editor._apply_template("2221")
        canvas = editor._tree_canvas
        canvas._on_card_selected(3)
        self.assertEqual(canvas.selected_index(), 3)
        self.assertTrue(editor._node_edit_bar.isVisible())

    def test_random_mode_cards_edit_directly(self) -> None:
        editor = _build_editor()
        editor._apply_template("2221")
        editor._mode_random_btn.setChecked(True)
        QApplication.processEvents()
        random_cards = [
            c for c in editor.findChildren(_PromotionNodeCard)
            if c.parentWidget() is not editor._tree_canvas
        ]
        self.assertTrue(random_cards)
        random_cards[0]._name_edit.setText("随机晋升名")
        QApplication.processEvents()
        self.assertEqual(editor._nodes[0].name_cn, "随机晋升名")

    def test_set_entry_reloads_card_texts(self) -> None:
        editor = _build_editor()
        editor.set_entry(
            {"abbr": "CT", "name": "树", "mode": "tree", "nodes": [
                {"abbr": "DEMO_A", "name_cn": "老晋升", "desc_cn": "老描述", "level": 1, "column": 1},
            ]},
            "fallback",
        )
        QApplication.processEvents()
        card0 = editor._tree_canvas._cards[0]
        self.assertEqual(card0._name_edit.text(), "老晋升")
        self.assertEqual(card0._desc_edit.text(), "老描述")
        self.assertEqual(card0._type_label.text(), "DEMO_A")

    def test_delete_selected_updates_cards(self) -> None:
        editor = _build_editor()
        editor._apply_template("2221")
        canvas = editor._tree_canvas
        canvas._select(2)
        editor._delete_selected()
        self.assertEqual(len(editor._nodes), 6)
        self.assertEqual(len(canvas._cards), 6)


if __name__ == "__main__":
    unittest.main()
