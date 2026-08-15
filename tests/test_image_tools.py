"""小工具页与图片操作测试。

- 圆形裁切：边距（非顶边）、黑边环、透明角、无黑边模式
- 灰度图标
- 图标尺寸表
- PSD 总结往返（依赖 psd-tools，未安装时跳过）
- 工具页构造（搜索子页嵌入）
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PyQt6.QtWidgets import QApplication, QTabWidget  # noqa: E402

from ModTools_5_4.ui.image_ops import ICON_SIZE_TABLE, circle_crop, grayscale_icon  # noqa: E402
from ModTools_5_4.ui.psd_summarizer import summarize_psd  # noqa: E402
from ModTools_5_4.ui.pages.search_page import SearchPage  # noqa: E402
from ModTools_5_4.ui.pages.tools_page import ToolsPage  # noqa: E402

try:
    import psd_tools  # noqa: F401
    HAS_PSD_TOOLS = True
except ImportError:
    HAS_PSD_TOOLS = False


class CircleCropTestCase(unittest.TestCase):
    def test_margin_not_edges_crop(self) -> None:
        img = Image.new("RGBA", (256, 256), (255, 0, 0, 255))
        out = circle_crop(img, margin=10, border_px=3)
        self.assertEqual(out.size, (256, 256))
        self.assertEqual(out.getpixel((0, 0))[3], 0, "角落应透明")
        self.assertEqual(out.getpixel((128, 128))[:3], (255, 0, 0), "中心保留原图")
        self.assertEqual(out.getpixel((8, 128))[3], 0, "圆外应透明（边距生效）")

    def test_black_border_ring(self) -> None:
        img = Image.new("RGBA", (256, 256), (255, 0, 0, 255))
        out = circle_crop(img, margin=10, border_px=3)
        self.assertEqual(out.getpixel((11, 128)), (0, 0, 0, 255), "黑边环应纯黑")

    def test_no_border_mode(self) -> None:
        img = Image.new("RGBA", (256, 256), (255, 0, 0, 255))
        out = circle_crop(img, margin=10, border_px=0)
        self.assertEqual(out.getpixel((11, 128))[:3], (255, 0, 0), "无黑边时该处保留原图")
        self.assertEqual(out.getpixel((7, 128))[3], 0)

    def test_margin_scales_with_image_size(self) -> None:
        img = Image.new("RGBA", (128, 128), (255, 0, 0, 255))
        out = circle_crop(img, margin=10, border_px=0)
        self.assertEqual(out.getpixel((3, 64))[3], 0, "边距按尺寸等比缩放（10/256 → 5/128）")


class GrayscaleTestCase(unittest.TestCase):
    def test_grayscale_preserves_alpha(self) -> None:
        img = Image.new("RGBA", (64, 64), (200, 100, 50, 128))
        gray = grayscale_icon(img)
        r, g, b, a = gray.getpixel((32, 32))
        self.assertEqual(r, g)
        self.assertEqual(g, b)
        self.assertEqual(a, 128)


class IconSizeTableTestCase(unittest.TestCase):
    def test_sizes(self) -> None:
        self.assertIn(256, ICON_SIZE_TABLE["文明"])
        self.assertIn(22, ICON_SIZE_TABLE["文明"])
        self.assertIn(256, ICON_SIZE_TABLE["单位"])
        self.assertIn(38, ICON_SIZE_TABLE["改良设施"])
        for sizes in ICON_SIZE_TABLE.values():
            self.assertEqual(len(sizes), len(set(sizes)), "尺寸不应重复")


class ToolsPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_tabs_and_search_embedded(self) -> None:
        page = ToolsPage()
        tabs = page.findChild(QTabWidget)
        self.assertIsNotNone(tabs)
        self.assertEqual(tabs.count(), 3)
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn("搜索", labels)
        self.assertIn("图片工具", labels)
        self.assertIn("PSD模板总结", labels)
        self.assertTrue(any(isinstance(tabs.widget(i), SearchPage) for i in range(tabs.count())))


@unittest.skipUnless(HAS_PSD_TOOLS, "psd-tools 未安装")
class PsdSummarizeTestCase(unittest.TestCase):
    def test_roundtrip(self) -> None:
        from psd_tools import PSDImage

        tmp = Path(tempfile.mkdtemp())
        psd = PSDImage.new("RGBA", (64, 64))
        psd.create_pixel_layer(Image.new("RGBA", (64, 64), (30, 60, 90, 255)), name="bg")
        psd.create_pixel_layer(
            Image.new("RGBA", (32, 32), (200, 0, 0, 255)), name="slot-portrait", left=16, top=16
        )
        psd_path = tmp / "tpl.psd"
        psd.save(psd_path)

        out = tmp / "out"
        recipe = summarize_psd(psd_path, out)
        self.assertEqual(recipe["size"], [64, 64])
        self.assertEqual(len(recipe["layers"]), 2)
        self.assertTrue((out / "recipe.json").exists())
        self.assertTrue((out / "composite.png").exists())
        for entry in recipe["layers"]:
            self.assertTrue(entry["png"])
            self.assertTrue((out / "layers" / entry["png"]).exists())
        json.loads((out / "recipe.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
