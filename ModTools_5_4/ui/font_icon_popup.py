"""Popup widget for selecting Civ6 FontIcons.

UX requirements (user request):
- Right-click in allowed text boxes shows a floating popup at mouse position.
- Popup layout matches the DDS atlas grid; empty cells are blank.
- Clicking an empty cell or outside closes the popup.
- Hover shows icon Name (tooltip).
- Future extension: multiple sheets are stacked vertically (new images appended below).
- Custom icons: reserved hook (not implemented yet).
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .font_icons import DdsRgba32Atlas, FontIconRegistry, FontIconSheet, resolve_default_fonticons_dds_path


LOGGER = logging.getLogger(__name__)


class _EmptyCell(QWidget):
    def __init__(self, *, cell_size: int, on_click_close) -> None:
        super().__init__()
        self._on_close = on_click_close
        self.setFixedSize(QSize(cell_size, cell_size))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def mousePressEvent(self, event) -> None:
        if callable(self._on_close):
            self._on_close()
        event.accept()


class FontIconPopup(QFrame):
    iconPicked = pyqtSignal(str)

    def __init__(
        self,
        *,
        registry: FontIconRegistry,
        parent: QWidget | None = None,
        scale: int = 1,
        custom_icons_provider=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("fontIconPopup")

        self._registry = registry
        self._scale = max(1, int(scale))
        self._custom_icons_provider = custom_icons_provider  # reserved hook

        self._atlases: dict[str, DdsRgba32Atlas] = {}
        self._sheet_visible_rows: dict[str, int] = {}
        self._sheet_widths: dict[str, int] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # Custom icons hook (not implemented yet).
        # If future custom icons exist, they should be inserted above built-in sheets.

        for sheet in self._registry.sheets_in_order():
            # Skip optional sheets if the DDS is not bundled in data/.
            try:
                if not resolve_default_fonticons_dds_path(sheet.filename).exists():
                    continue
            except Exception:
                continue

            holder = QWidget()
            holder_layout = QGridLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setHorizontalSpacing(1)
            holder_layout.setVerticalSpacing(1)

            visible_rows = self._build_sheet_grid(holder_layout, sheet)
            self._sheet_visible_rows[sheet.sheet_id] = visible_rows
            self._sheet_widths[sheet.sheet_id] = self._grid_pixel_width(sheet)

            # Make the holder width stable so there is never horizontal scrolling.
            holder.setFixedWidth(self._grid_pixel_width(sheet))
            content_layout.addWidget(holder)

        scroll.setWidget(content)
        root.addWidget(scroll)

        # Fixed width = widest sheet + margins. Keep it just enough for current atlas.
        # Reserve space for the vertical scrollbar so it never covers/clips the icon grid.
        # (The bar may appear when the popup height is clamped to screen.)
        try:
            sb_extent = int(scroll.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent, None, scroll))
        except Exception:
            sb_extent = 0
        # root margins: 6 + 6 are already included in _popup_pixel_width().
        self.setFixedWidth(self._popup_pixel_width() + max(0, sb_extent))

        # Fixed height: currently fit all icons (no vertical scrollbar).
        # If future extra sheets exceed screen height, clamp and allow vertical scrolling.
        target_h = self._popup_pixel_height()
        try:
            screen = self.screen()
            if screen is not None:
                avail_h = int(screen.availableGeometry().height())
                # Keep a small margin so positioning logic has room.
                target_h = min(target_h, max(240, avail_h - 24))
        except Exception:
            pass
        self.setFixedHeight(int(target_h))

    def _grid_spacing(self) -> int:
        return 1

    def _grid_pixel_width(self, sheet: FontIconSheet) -> int:
        cols = max(1, int(sheet.cols))
        cell = self._cell_size(sheet)
        spacing = self._grid_spacing()
        return cols * cell + (cols - 1) * spacing

    def _popup_pixel_width(self) -> int:
        if not self._registry.has_icons():
            return 320
        widest = 0
        for sheet in self._registry.sheets_in_order():
            widest = max(widest, self._grid_pixel_width(sheet))
        # root margins: 6 + 6
        return widest + 12

    def _grid_pixel_height(self, *, sheet: FontIconSheet, visible_rows: int) -> int:
        rows = max(0, int(visible_rows))
        if rows <= 0:
            return 0
        cell = self._cell_size(sheet)
        spacing = self._grid_spacing()
        return rows * cell + (rows - 1) * spacing

    def _popup_pixel_height(self) -> int:
        # root margins: 6 + 6
        total = 12
        sheets = self._registry.sheets_in_order()
        if not sheets:
            return 240

        between = 8  # content_layout spacing
        added = 0
        for sheet in sheets:
            rows = int(self._sheet_visible_rows.get(sheet.sheet_id, 0))
            h = self._grid_pixel_height(sheet=sheet, visible_rows=rows)
            if h <= 0:
                continue
            if added:
                total += between
            total += h
            added += 1

        # If everything is empty, keep a minimal height.
        return max(120, total)

    def _atlas_for_sheet(self, sheet: FontIconSheet) -> DdsRgba32Atlas:
        atlas = self._atlases.get(sheet.sheet_id)
        if atlas is not None:
            return atlas
        dds_path = resolve_default_fonticons_dds_path(sheet.filename)
        atlas = DdsRgba32Atlas(dds_path)
        self._atlases[sheet.sheet_id] = atlas
        return atlas

    def _cell_size(self, sheet: FontIconSheet) -> int:
        # Tight layout (user request): keep the grid compact.
        return int(sheet.icon_size * self._scale) + 2

    def _build_sheet_grid(self, layout: QGridLayout, sheet: FontIconSheet) -> int:
        atlas = self._atlas_for_sheet(sheet)
        cell_size = self._cell_size(sheet)
        icon_size = int(sheet.icon_size) * self._scale

        if str(getattr(sheet, "layout", "grid") or "grid").lower() == "packed":
            cols = max(1, int(sheet.cols))
            indices = self._registry.defined_indices(sheet.sheet_id)
            if not indices:
                return 0

            # Re-layout: fill icons sequentially (row-major), ignore sparse holes.
            for pos, atlas_index in enumerate(indices):
                r = pos // cols
                c = pos % cols
                names = self._registry.names_for_cell(sheet.sheet_id, atlas_index)
                if not names:
                    layout.addWidget(_EmptyCell(cell_size=cell_size, on_click_close=self.close), r, c)
                    continue

                btn = QToolButton()
                btn.setAutoRaise(True)
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                btn.setFixedSize(QSize(cell_size, cell_size))
                btn.setIconSize(QSize(icon_size, icon_size))

                pix = atlas.pixmap_for_index(
                    icon_size=sheet.icon_size,
                    cols=sheet.cols,
                    index=atlas_index,
                    scale=self._scale,
                )
                if pix is not None:
                    btn.setIcon(QIcon(pix))

                if len(names) == 1:
                    btn.setToolTip(names[0])
                    btn.clicked.connect(lambda _=False, n=names[0]: self._pick(n))
                else:
                    btn.setToolTip(" / ".join(names))
                    btn.clicked.connect(lambda _=False, n=names, b=btn: self._pick_from_menu(b, n))

                layout.addWidget(btn, r, c)

            # Pad last row with empty cells so the grid keeps a stable width.
            total = len(indices)
            pad = (-total) % cols
            if pad:
                base_pos = total
                for i in range(pad):
                    pos = base_pos + i
                    r = pos // cols
                    c = pos % cols
                    layout.addWidget(_EmptyCell(cell_size=cell_size, on_click_close=self.close), r, c)

            return (total + cols - 1) // cols

        visible_r = 0
        cols = int(sheet.cols)
        rows = int(sheet.rows)
        for r in range(rows):
            row_has_any = False
            base = r * cols
            for idx in range(base, base + cols):
                if self._registry.names_for_cell(sheet.sheet_id, idx):
                    row_has_any = True
                    break
            if not row_has_any:
                continue

            for c in range(cols):
                idx = base + c
                names = self._registry.names_for_cell(sheet.sheet_id, idx)
                if not names:
                    layout.addWidget(_EmptyCell(cell_size=cell_size, on_click_close=self.close), visible_r, c)
                    continue

                btn = QToolButton()
                btn.setAutoRaise(True)
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                btn.setFixedSize(QSize(cell_size, cell_size))
                btn.setIconSize(QSize(icon_size, icon_size))

                pix = atlas.pixmap_for_index(icon_size=sheet.icon_size, cols=sheet.cols, index=idx, scale=self._scale)
                if pix is not None:
                    btn.setIcon(QIcon(pix))

                if len(names) == 1:
                    btn.setToolTip(names[0])
                    btn.clicked.connect(lambda _=False, n=names[0]: self._pick(n))
                else:
                    # Multiple names share one icon cell: show a small menu.
                    btn.setToolTip(" / ".join(names))
                    btn.clicked.connect(lambda _=False, n=names, b=btn: self._pick_from_menu(b, n))

                layout.addWidget(btn, visible_r, c)

            visible_r += 1

        return visible_r

    def _pick_from_menu(self, anchor: QWidget, names: list[str]) -> None:
        menu = QMenu(self)
        for name in names:
            act = QAction(name, menu)
            act.triggered.connect(lambda _=False, n=name: self._pick(n))
            menu.addAction(act)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _pick(self, name: str) -> None:
        clean = str(name or "").strip()
        if not clean:
            self.close()
            return
        self.iconPicked.emit(clean)
        self.close()
