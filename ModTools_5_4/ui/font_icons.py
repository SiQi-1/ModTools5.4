"""Civ6 FontIcons (DDS atlas) support for inline icon editing.

This module is intentionally small and self-contained:
- Load icon name -> atlas/index mapping from a generated JSON registry.
- Decode the bundled uncompressed DDS (RGBA32) into a QImage.
- Slice per-index pixmaps for UI usage (picker + inline images).

Scope (per user request): only the baseline 4/6/8 atlases from FontIcons.xml.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import struct
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QPixmap

from ..db.paths import DATA_DIR


LOGGER = logging.getLogger(__name__)


_REGISTRY_FILE = DATA_DIR / "font_icons_registry.json"


@dataclass(frozen=True)
class FontIconSheet:
    sheet_id: str
    filename: str
    icon_size: int
    cols: int
    rows: int
    layout: str = "grid"  # 'grid' (atlas index grid) or 'packed' (ignore sparse holes)


class FontIconRegistry:
    def __init__(
        self,
        *,
        sheets: dict[str, FontIconSheet],
        icons: dict[str, dict[str, object]],
    ) -> None:
        self._sheets = sheets
        self._icons = icons
        self._by_sheet_index: dict[tuple[str, int], list[str]] = {}
        for name, payload in icons.items():
            sheet_id = str(payload.get("sheet") or "").strip()
            try:
                index = int(payload.get("index") or 0)
            except (TypeError, ValueError):
                continue
            if not sheet_id:
                continue
            self._by_sheet_index.setdefault((sheet_id, index), []).append(name)

        # Stable display order when multiple names share one index.
        for names in self._by_sheet_index.values():
            names.sort(key=lambda s: (len(s), s))

    @staticmethod
    def load_default() -> "FontIconRegistry":
        try:
            payload = json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            LOGGER.exception("Failed to load font icon registry: %s", _REGISTRY_FILE)
            return FontIconRegistry(sheets={}, icons={})

        sheets_raw = payload.get("sheets")
        icons_raw = payload.get("icons")
        sheets: dict[str, FontIconSheet] = {}
        if isinstance(sheets_raw, list):
            for item in sheets_raw:
                if not isinstance(item, dict):
                    continue
                sheet_id = str(item.get("id") or "").strip()
                filename = str(item.get("filename") or "").strip()
                if not sheet_id or not filename:
                    continue
                try:
                    icon_size = int(item.get("icon_size") or 22)
                    cols = int(item.get("cols") or 11)
                    rows = int(item.get("rows") or 25)
                except (TypeError, ValueError):
                    continue
                layout = str(item.get("layout") or "grid").strip().lower()
                if layout not in {"grid", "packed"}:
                    layout = "grid"
                sheets[sheet_id] = FontIconSheet(
                    sheet_id=sheet_id,
                    filename=filename,
                    icon_size=icon_size,
                    cols=cols,
                    rows=rows,
                    layout=layout,
                )

        icons: dict[str, dict[str, object]] = {}
        if isinstance(icons_raw, dict):
            for name, entry in icons_raw.items():
                if not isinstance(name, str) or not isinstance(entry, dict):
                    continue
                clean = name.strip()
                if not clean:
                    continue
                icons[clean] = dict(entry)

        return FontIconRegistry(sheets=sheets, icons=icons)

    def has_icons(self) -> bool:
        return bool(self._icons) and bool(self._sheets)

    def sheets_in_order(self) -> list[FontIconSheet]:
        # Future: if multiple sheets exist, preserve JSON order.
        return list(self._sheets.values())

    def resolve(self, icon_name: str) -> tuple[FontIconSheet | None, int | None]:
        payload = self._icons.get(str(icon_name or "").strip())
        if not isinstance(payload, dict):
            return None, None
        sheet_id = str(payload.get("sheet") or "").strip()
        if not sheet_id:
            return None, None
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None, None
        try:
            idx = int(payload.get("index") or 0)
        except (TypeError, ValueError):
            return None, None
        return sheet, idx

    def names_for_cell(self, sheet_id: str, index: int) -> list[str]:
        return list(self._by_sheet_index.get((sheet_id, int(index)), []))

    def defined_indices(self, sheet_id: str) -> list[int]:
        """All atlas indices that have at least one icon name defined."""
        wanted = str(sheet_id or "").strip()
        if not wanted:
            return []
        indices: set[int] = set()
        for (sid, idx) in self._by_sheet_index.keys():
            if sid == wanted:
                indices.add(int(idx))
        return sorted(indices)


class DdsRgba32Atlas:
    """Decodes an uncompressed DDS with 32-bit RGBA masks.

    This matches the tool's own exported format, and the bundled FontIcons.dds in this repo.
    """

    def __init__(self, dds_path: Path) -> None:
        self._path = dds_path
        self._image: QImage | None = None
        self._pix_cache: dict[tuple[int, int], QPixmap] = {}

    def _load_base_image(self) -> QImage | None:
        if self._image is not None:
            return self._image
        try:
            data = self._path.read_bytes()
        except Exception:
            LOGGER.exception("Failed to read DDS: %s", self._path)
            return None

        if len(data) < 128 or data[0:4] != b"DDS ":
            LOGGER.warning("Not a DDS file: %s", self._path)
            return None

        header = data[4:128]
        try:
            height, width = struct.unpack_from("<II", header, 8)
            ddspf_flags = struct.unpack_from("<I", header, 76)[0]
            fourcc = header[80:84]
            rgb_bits = struct.unpack_from("<I", header, 84)[0]
            rmask, gmask, bmask, amask = struct.unpack_from("<IIII", header, 88)
        except Exception:
            LOGGER.exception("Malformed DDS header: %s", self._path)
            return None

        # We only support uncompressed RGBA32 for now.
        DDPF_RGB = 0x40
        DDPF_ALPHAPIXELS = 0x1
        if fourcc != b"\x00\x00\x00\x00":
            LOGGER.warning("Unsupported DDS FourCC=%r for %s", fourcc, self._path)
            return None
        if (ddspf_flags & DDPF_RGB) == 0 or (ddspf_flags & DDPF_ALPHAPIXELS) == 0:
            LOGGER.warning("Unsupported DDS pixel format flags=%#x for %s", ddspf_flags, self._path)
            return None
        if rgb_bits != 32:
            LOGGER.warning("Unsupported DDS rgb_bits=%s for %s", rgb_bits, self._path)
            return None
        if (rmask, gmask, bmask, amask) != (0xFF, 0xFF00, 0xFF0000, 0xFF000000):
            LOGGER.warning(
                "Unexpected DDS channel masks r=%#x g=%#x b=%#x a=%#x for %s",
                rmask,
                gmask,
                bmask,
                amask,
                self._path,
            )
            return None

        base_offset = 128
        needed = int(width) * int(height) * 4
        if len(data) < base_offset + needed:
            LOGGER.warning("DDS payload too small: %s", self._path)
            return None

        raw = data[base_offset : base_offset + needed]
        img = QImage(raw, int(width), int(height), int(width) * 4, QImage.Format.Format_RGBA8888).copy()
        self._image = img
        return img

    def pixmap_for_index(self, *, icon_size: int, cols: int, index: int, scale: int = 1) -> QPixmap | None:
        scale = max(1, int(scale))
        key = (int(index), scale)
        cached = self._pix_cache.get(key)
        if cached is not None:
            return cached

        base = self._load_base_image()
        if base is None:
            return None

        idx = int(index)
        if cols <= 0 or icon_size <= 0:
            return None
        col = idx % int(cols)
        row = idx // int(cols)
        x = col * int(icon_size)
        y = row * int(icon_size)
        if x + icon_size > base.width() or y + icon_size > base.height():
            return None

        sub = base.copy(int(x), int(y), int(icon_size), int(icon_size))
        pix = QPixmap.fromImage(sub)
        if scale != 1:
            pix = pix.scaled(
                QSize(icon_size * scale, icon_size * scale),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._pix_cache[key] = pix
        return pix


def resolve_default_fonticons_dds_path(filename: str) -> Path:
    # Bundled file: ModTools_5_4/data/FontIcons.dds
    return (DATA_DIR / filename).resolve()
