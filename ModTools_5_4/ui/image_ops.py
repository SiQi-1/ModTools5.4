"""图片工具底层操作（纯 Pillow，供小工具页与 AI 工具共用）。

- 圆形裁切：带边距（非顶边）+ 可选黑边，4x 超采样抗锯齿
- 黑白图标：灰度化 + 对比度
- 图标尺寸表：按对象类型
"""
from __future__ import annotations

from typing import Dict, List

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

# 对象类型 -> 图标尺寸（像素）
ICON_SIZE_TABLE: Dict[str, List[int]] = {
    "文明": [22, 30, 32, 36, 45, 48, 50, 55, 64, 80, 128, 256],
    "单位": [22, 32, 36, 45, 50, 64, 80, 128, 256],
    "改良设施": [38, 50, 80, 128, 256],
}


def _circle_mask(size: tuple[int, int], cx: float, cy: float, radius: float, ss: int = 4) -> Image.Image:
    """超采样圆形蒙版（抗锯齿）。"""
    big = Image.new("L", (size[0] * ss, size[1] * ss), 0)
    draw = ImageDraw.Draw(big)
    draw.ellipse(
        [
            (cx - radius) * ss,
            (cy - radius) * ss,
            (cx + radius) * ss,
            (cy + radius) * ss,
        ],
        fill=255,
    )
    return big.resize(size, Image.BILINEAR)


def circle_crop(
    image: Image.Image,
    *,
    margin: float = 10.0,
    border_px: float = 0.0,
    base_size: int = 256,
) -> Image.Image:
    """居中圆形裁切。

    margin/border_px 以 base_size（默认 256）为基准，按图片实际边长等比缩放；
    圆边距图片边缘 margin 像素（不是顶边裁切）。
    """
    img = image.convert("RGBA")
    w, h = img.size
    side = max(1.0, float(min(w, h)))
    scale = side / float(base_size)
    margin_scaled = margin * scale
    border_scaled = border_px * scale if border_px > 0 else 0.0
    cx, cy = w / 2.0, h / 2.0
    outer_r = side / 2.0 - margin_scaled
    inner_r = max(0.0, outer_r - border_scaled)

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if border_scaled > 0:
        ring = Image.new("RGBA", (w, h), (0, 0, 0, 255))
        ring.putalpha(_circle_mask((w, h), cx, cy, outer_r))
        out = Image.alpha_composite(out, ring)
    out.paste(img, (0, 0), _circle_mask((w, h), cx, cy, inner_r))
    return out


def grayscale_icon(image: Image.Image, *, contrast: float = 1.0) -> Image.Image:
    """灰度化（保留 Alpha），可选对比度增强。"""
    img = image.convert("RGBA")
    gray = ImageOps.grayscale(img)
    if abs(contrast - 1.0) > 1e-6:
        gray = ImageEnhance.Contrast(gray).enhance(max(0.1, contrast))
    rgba = gray.convert("RGBA")
    rgba.putalpha(img.getchannel("A"))
    return rgba
