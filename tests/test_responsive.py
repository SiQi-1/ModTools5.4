"""ResponsiveGrid / ResponsiveSplit 回归测试。

核心：验证切换后子控件真实几何（不重叠、已重新受布局管理），
而非仅检查内部状态——曾出现 deleteLater 异步删除期间 setLayout 冲突，
导致布局从未安装、子控件全部堆叠在原点的 bug。
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget  # noqa: E402

from ModTools_5_4.ui.responsive import ResponsiveGrid, ResponsiveSplit  # noqa: E402


def _children(widget: QWidget) -> list[QWidget]:
    return [w for w in widget.findChildren(QWidget) if w.parentWidget() is widget]


def _geometries_do_not_overlap(widgets: list[QWidget]) -> bool:
    rects = [w.geometry() for w in widgets]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if rects[i].intersects(rects[j]):
                return False
    return True


class ResponsiveGridTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _build(self) -> tuple[ResponsiveGrid, QWidget]:
        labels = [QLabel(f"cell{i}") for i in range(4)]
        grid = ResponsiveGrid(labels, [(1100, 3), (750, 2), (0, 1)])
        root = QWidget()
        root.setLayout(QVBoxLayout())
        root.layout().addWidget(grid)
        root.show()
        return grid, root

    def test_columns_follow_width(self) -> None:
        grid, root = self._build()
        root.resize(1200, 200)
        QApplication.processEvents()
        self.assertEqual(grid._current_cols, 3)
        root.resize(800, 200)
        QApplication.processEvents()
        self.assertEqual(grid._current_cols, 2)
        root.resize(500, 200)
        QApplication.processEvents()
        self.assertEqual(grid._current_cols, 1)

    def test_layout_stays_installed_and_children_managed(self) -> None:
        grid, root = self._build()
        root.resize(1200, 200)
        QApplication.processEvents()
        self.assertIsNotNone(grid.layout())
        self.assertEqual(grid.layout().count(), 4)
        children = _children(grid)
        self.assertEqual(len(children), 4)
        for child in children:
            self.assertGreater(child.width(), 0)
            self.assertGreater(child.height(), 0)

    def test_children_never_overlap_after_reflow(self) -> None:
        grid, root = self._build()
        for width in (1200, 800, 500, 1200, 600):
            root.resize(width, 200)
            QApplication.processEvents()
            self.assertTrue(
                _geometries_do_not_overlap(_children(grid)),
                f"overlap at width {width}",
            )


class ResponsiveSplitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _build(self) -> tuple[ResponsiveSplit, QWidget]:
        left = QLabel("left")
        left.setStyleSheet("background:#a00")
        right = QLabel("right")
        right.setStyleSheet("background:#00a")
        split = ResponsiveSplit(left, right, min_width=750)
        root = QWidget()
        root.setLayout(QVBoxLayout())
        root.layout().addWidget(split)
        root.show()
        return split, root

    def test_side_by_side_then_stacked(self) -> None:
        split, root = self._build()
        root.resize(900, 200)
        QApplication.processEvents()
        self.assertTrue(split._side_by_side)
        root.resize(500, 200)
        QApplication.processEvents()
        self.assertFalse(split._side_by_side)

    def test_layout_stays_installed_and_children_managed(self) -> None:
        split, root = self._build()
        for width in (900, 500, 900):
            root.resize(width, 200)
            QApplication.processEvents()
            self.assertIsNotNone(split.layout())
            self.assertEqual(split.layout().count(), 2)
            self.assertTrue(_geometries_do_not_overlap(_children(split)))

    def test_stacked_mode_children_in_vertical_order(self) -> None:
        split, root = self._build()
        root.resize(500, 300)
        QApplication.processEvents()
        left, right = _children(split)
        self.assertLess(left.geometry().top(), right.geometry().top())
        self.assertLess(left.geometry().bottom(), right.geometry().top())

    def test_side_by_side_children_in_horizontal_order(self) -> None:
        split, root = self._build()
        root.resize(900, 200)
        QApplication.processEvents()
        left, right = _children(split)
        self.assertLess(left.geometry().left(), right.geometry().left())
        self.assertLess(left.geometry().right(), right.geometry().left())


if __name__ == "__main__":
    unittest.main()
