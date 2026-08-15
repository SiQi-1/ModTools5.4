"""PSD 模板总结：把 PSD 转成「烘焙图层 PNG + recipe JSON」。

图层连同特效一起渲染导出（特效由 psd-tools 渲染引擎烘焙进像素），
程序/后续合成器只需按 recipe 拼合，不重画特效。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

_ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|\r\n\t]')


def _sanitize(name: str) -> str:
    cleaned = _ILLEGAL_FILENAME.sub("_", name).strip().strip(".")
    return cleaned or "layer"


def _layer_recipe(layer: Any) -> Dict[str, object]:
    bbox = None
    try:
        raw_bbox = layer.bbox
        if raw_bbox is not None:
            bbox = [int(raw_bbox.x1), int(raw_bbox.y1), int(raw_bbox.x2), int(raw_bbox.y2)]
    except Exception:
        bbox = None
    children: List[Dict[str, object]] = []
    if getattr(layer, "is_group", lambda: False)():
        for child in layer:
            children.append(_layer_recipe(child))
    return {
        "name": str(getattr(layer, "name", "")),
        "kind": str(getattr(layer, "kind", "unknown")),
        "visible": bool(getattr(layer, "visible", True)),
        "bbox": bbox,
        "children": children or None,
    }


def summarize_psd(psd_path: str | Path, out_dir: str | Path) -> Dict[str, object]:
    """导出 PSD 的烘焙图层 PNG + recipe JSON，返回 recipe。

    依赖 psd-tools（可选安装：pip install psd-tools）。
    """
    try:
        from psd_tools import PSDImage
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("未安装 psd-tools，请先执行：pip install psd-tools") from exc

    psd_path = Path(psd_path)
    out_dir = Path(out_dir)
    layers_dir = out_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)

    psd = PSDImage.open(psd_path)

    recipe_layers: List[Dict[str, object]] = []
    name_counter: Dict[str, int] = {}

    def walk(layer: Any, prefix: str) -> None:
        base = _sanitize(str(getattr(layer, "name", "")) or "layer")
        count = name_counter.get(base, 0)
        name_counter[base] = count + 1
        filename = f"{prefix}{base}{'' if count == 0 else '_' + str(count)}.png"
        exported = False
        try:
            composite = layer.composite(force=True)
        except Exception:
            composite = None
        if composite is not None:
            try:
                composite.save(layers_dir / filename)
                exported = True
            except Exception:
                exported = False
        entry = _layer_recipe(layer)
        entry["png"] = filename if exported else None
        recipe_layers.append(entry)
        if getattr(layer, "is_group", lambda: False)():
            child_prefix = f"{prefix}{_sanitize(base)}__"
            for child in layer:
                walk(child, child_prefix)

    for top_layer in psd:
        walk(top_layer, "")

    try:
        composite = psd.composite()
        if composite is not None:
            composite.save(out_dir / "composite.png")
    except Exception:
        pass

    recipe: Dict[str, object] = {
        "format": "MODTOOLS54_PSD_TEMPLATE_SUMMARY",
        "schema": "1.0.0",
        "source": str(psd_path),
        "size": [int(psd.width), int(psd.height)],
        "layers": recipe_layers,
    }
    (out_dir / "recipe.json").write_text(
        json.dumps(recipe, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return recipe
