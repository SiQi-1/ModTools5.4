"""小工具页：搜索（子页）+ 图片工具 + PSD 模板总结。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage
from .search_page import SearchPage
from ..image_ops import ICON_SIZE_TABLE, circle_crop, grayscale_icon
from ..psd_summarizer import summarize_psd

_REGION_BASE_DIR = Path("D:/文明6mod用文件夹/区域底图")


def _preview_label(size: int = 192) -> QLabel:
    label = QLabel("（无图片）")
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        "border:1px dashed #cbd5e1; border-radius:6px; background:#f8fafc; color:#94a3b8; font-size:11px;"
    )
    label.setScaledContents(False)
    return label


def _show_image(label: QLabel, image: Image.Image) -> None:
    img = image.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimage = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
    pixmap = QPixmap.fromImage(qimage)
    label.setPixmap(
        pixmap.scaled(
            label.width(),
            label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


def _status_label() -> QLabel:
    label = QLabel("")
    label.setStyleSheet("color:#64748b; font-size:11px;")
    label.setWordWrap(True)
    return label


class _CircleCropPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("圆形裁切（领袖头像）")
        self._image: Image.Image | None = None
        self._source_path: Path | None = None

        root = QVBoxLayout(self)
        root.setSpacing(8)

        pick_row = QHBoxLayout()
        pick_btn = QPushButton("选择图片")
        pick_btn.clicked.connect(self._pick_image)
        self._path_label = QLabel("未选择")
        self._path_label.setStyleSheet("color:#64748b;")
        pick_row.addWidget(pick_btn)
        pick_row.addWidget(self._path_label, 1)
        root.addLayout(pick_row)

        param_row = QHBoxLayout()
        param_row.addWidget(QLabel("边距（px，基于256）"))
        self._margin_spin = QSpinBox()
        self._margin_spin.setRange(0, 64)
        self._margin_spin.setValue(10)
        self._margin_spin.valueChanged.connect(lambda _v: self._refresh_preview())
        param_row.addWidget(self._margin_spin)
        param_row.addSpacing(12)
        self._border_check = QCheckBox("添加黑边（px，基于256）")
        self._border_check.setChecked(True)
        self._border_check.stateChanged.connect(lambda _s: self._refresh_preview())
        param_row.addWidget(self._border_check)
        self._border_spin = QSpinBox()
        self._border_spin.setRange(0, 16)
        self._border_spin.setValue(3)
        self._border_spin.valueChanged.connect(lambda _v: self._refresh_preview())
        param_row.addWidget(self._border_spin)
        param_row.addStretch(1)
        root.addLayout(param_row)

        preview_row = QHBoxLayout()
        self._before_label = _preview_label()
        self._after_label = _preview_label()
        preview_row.addWidget(self._before_label)
        preview_row.addWidget(QLabel("→"))
        preview_row.addWidget(self._after_label)
        preview_row.addStretch(1)
        root.addLayout(preview_row)

        action_row = QHBoxLayout()
        export_btn = QPushButton("导出 PNG")
        export_btn.clicked.connect(self._export)
        action_row.addWidget(export_btn)
        self._status = _status_label()
        action_row.addWidget(self._status, 1)
        root.addLayout(action_row)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            self._image = Image.open(path).convert("RGBA")
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"无法打开图片：{exc}")
            return
        self._source_path = Path(path)
        self._path_label.setText(path)
        _show_image(self._before_label, self._image)
        self._refresh_preview()

    def _crop_params(self) -> tuple[float, float]:
        margin = float(self._margin_spin.value())
        border = float(self._border_spin.value()) if self._border_check.isChecked() else 0.0
        return margin, border

    def _refresh_preview(self) -> None:
        if self._image is None:
            self._after_label.setPixmap(QPixmap())
            self._after_label.setText("（无图片）")
            return
        margin, border = self._crop_params()
        result = circle_crop(self._image, margin=margin, border_px=border)
        _show_image(self._after_label, result)

    def _export(self) -> None:
        if self._image is None or self._source_path is None:
            self._status.setText("请先选择图片。")
            return
        default_name = f"{self._source_path.stem}_circle.png"
        out_path, _ = QFileDialog.getSaveFileName(self, "导出 PNG", default_name, "PNG (*.png)")
        if not out_path:
            return
        margin, border = self._crop_params()
        circle_crop(self._image, margin=margin, border_px=border).save(out_path)
        self._status.setText(f"已导出：{out_path}")


class _GrayscalePanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("黑白图标（文明/单位/改良设施）")
        self._image: Image.Image | None = None
        self._source_path: Path | None = None

        root = QVBoxLayout(self)
        root.setSpacing(8)

        pick_row = QHBoxLayout()
        pick_btn = QPushButton("选择图片")
        pick_btn.clicked.connect(self._pick_image)
        self._path_label = QLabel("未选择")
        self._path_label.setStyleSheet("color:#64748b;")
        pick_row.addWidget(pick_btn)
        pick_row.addWidget(self._path_label, 1)
        root.addLayout(pick_row)

        param_row = QHBoxLayout()
        param_row.addWidget(QLabel("对象类型"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(list(ICON_SIZE_TABLE.keys()))
        self._type_combo.currentTextChanged.connect(lambda _t: self._refresh_size_hint())
        param_row.addWidget(self._type_combo)
        param_row.addSpacing(12)
        param_row.addWidget(QLabel("对比度"))
        self._contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self._contrast_slider.setRange(50, 200)
        self._contrast_slider.setValue(100)
        self._contrast_slider.setFixedWidth(140)
        self._contrast_value = QLabel("100%")
        self._contrast_slider.valueChanged.connect(
            lambda v: self._contrast_value.setText(f"{v}%")
        )
        param_row.addWidget(self._contrast_slider)
        param_row.addWidget(self._contrast_value)
        param_row.addStretch(1)
        root.addLayout(param_row)

        self._size_hint = QLabel("")
        self._size_hint.setStyleSheet("color:#64748b; font-size:11px;")
        root.addWidget(self._size_hint)
        self._refresh_size_hint()

        preview_row = QHBoxLayout()
        self._before_label = _preview_label()
        self._after_label = _preview_label()
        preview_row.addWidget(self._before_label)
        preview_row.addWidget(QLabel("→"))
        preview_row.addWidget(self._after_label)
        preview_row.addStretch(1)
        root.addLayout(preview_row)

        action_row = QHBoxLayout()
        export_btn = QPushButton("批量导出多尺寸")
        export_btn.clicked.connect(self._export)
        action_row.addWidget(export_btn)
        self._status = _status_label()
        action_row.addWidget(self._status, 1)
        root.addLayout(action_row)

    def _refresh_size_hint(self) -> None:
        sizes = ICON_SIZE_TABLE.get(self._type_combo.currentText(), [])
        self._size_hint.setText("将输出尺寸：" + "、".join(str(s) for s in sizes))

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            self._image = Image.open(path).convert("RGBA")
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"无法打开图片：{exc}")
            return
        self._source_path = Path(path)
        self._path_label.setText(path)
        _show_image(self._before_label, self._image)
        contrast = self._contrast_slider.value() / 100.0
        _show_image(self._after_label, grayscale_icon(self._image, contrast=contrast))

    def _export(self) -> None:
        if self._image is None or self._source_path is None:
            self._status.setText("请先选择图片。")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if not out_dir:
            return
        contrast = self._contrast_slider.value() / 100.0
        base = self._source_path.stem
        sizes = ICON_SIZE_TABLE.get(self._type_combo.currentText(), [])
        written: list[str] = []
        for size in sizes:
            resized = self._image.resize((size, size), Image.LANCZOS)
            gray = grayscale_icon(resized, contrast=contrast)
            out_path = Path(out_dir) / f"{base}_{size}.png"
            gray.save(out_path)
            written.append(str(size))
        self._status.setText(f"已导出 {len(written)} 个尺寸：{'、'.join(written)}")


class _DistrictIconPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("区域图标（六边形检查 + 底图重做）")
        self._icon_path: Path | None = None

        root = QVBoxLayout(self)
        root.setSpacing(8)

        pick_row = QHBoxLayout()
        pick_btn = QPushButton("选择区域图标")
        pick_btn.clicked.connect(self._pick_icon)
        self._path_label = QLabel("未选择")
        self._path_label.setStyleSheet("color:#64748b;")
        pick_row.addWidget(pick_btn)
        pick_row.addWidget(self._path_label, 1)
        root.addLayout(pick_row)

        preview_row = QHBoxLayout()
        self._preview = _preview_label(256)
        preview_row.addWidget(self._preview)
        preview_row.addStretch(1)
        root.addLayout(preview_row)

        check_row = QHBoxLayout()
        check_row.addWidget(QLabel("图标是否符合六边形模板格式？"))
        ok_btn = QPushButton("符合，直接使用")
        ok_btn.clicked.connect(self._confirm_ok)
        redo_btn = QPushButton("不符合 → 用底图重做")
        redo_btn.clicked.connect(self._redo_with_base)
        check_row.addWidget(ok_btn)
        check_row.addWidget(redo_btn)
        check_row.addStretch(1)
        root.addLayout(check_row)

        redo_group = QGroupBox("底图重做")
        redo_layout = QVBoxLayout(redo_group)
        redo_layout.setSpacing(6)
        base_row = QHBoxLayout()
        base_btn = QPushButton("选择底图")
        base_btn.clicked.connect(self._pick_base)
        self._base_label = QLabel("未选择")
        self._base_label.setStyleSheet("color:#64748b;")
        base_row.addWidget(base_btn)
        base_row.addWidget(self._base_label, 1)
        redo_layout.addLayout(base_row)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("目标文件名"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如 DISTRICT_CUSTOM_1（扩展名保持原样）")
        name_row.addWidget(self._name_edit, 1)
        redo_layout.addLayout(name_row)
        copy_row = QHBoxLayout()
        copy_btn = QPushButton("复制并改名")
        copy_btn.clicked.connect(self._copy_base)
        copy_row.addWidget(copy_btn)
        self._status = _status_label()
        copy_row.addWidget(self._status, 1)
        redo_layout.addLayout(copy_row)
        root.addWidget(redo_group)

    def _pick_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择区域图标", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        self._icon_path = Path(path)
        self._path_label.setText(path)
        try:
            _show_image(self._preview, Image.open(path).convert("RGBA"))
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"无法打开图片：{exc}")

    def _confirm_ok(self) -> None:
        if self._icon_path is None:
            QMessageBox.information(self, "提示", "请先选择图标。")
            return
        QMessageBox.information(self, "已确认", "该图标符合六边形模板格式，可继续使用。")

    def _redo_with_base(self) -> None:
        if self._icon_path is None:
            QMessageBox.information(self, "提示", "请先选择图标。")
            return
        default_name = self._icon_path.stem
        self._name_edit.setText(default_name)

    def _pick_base(self) -> None:
        start_dir = str(_REGION_BASE_DIR) if _REGION_BASE_DIR.exists() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择底图", start_dir, "底图 (*.psd *.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        self._base_path = Path(path)
        self._base_label.setText(path)
        if not self._name_edit.text().strip():
            self._name_edit.setText(self._base_path.stem)

    def _copy_base(self) -> None:
        base_path = getattr(self, "_base_path", None)
        if base_path is None:
            self._status.setText("请先选择底图。")
            return
        new_name = self._name_edit.text().strip()
        if not new_name:
            self._status.setText("请填写目标文件名。")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if not out_dir:
            return
        target = Path(out_dir) / f"{new_name}{base_path.suffix}"
        try:
            target.write_bytes(base_path.read_bytes())
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"复制失败：{exc}")
            return
        self._status.setText(f"已复制：{target}")


class _PsdSummarizePanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("PSD 模板总结（图层烘焙 PNG + recipe JSON）")
        self._psd_path: Path | None = None
        self._out_dir: Path | None = None

        root = QVBoxLayout(self)
        root.setSpacing(8)

        psd_row = QHBoxLayout()
        psd_btn = QPushButton("选择 PSD 模板")
        psd_btn.clicked.connect(self._pick_psd)
        self._psd_label = QLabel("未选择")
        self._psd_label.setStyleSheet("color:#64748b;")
        psd_row.addWidget(psd_btn)
        psd_row.addWidget(self._psd_label, 1)
        root.addLayout(psd_row)

        out_row = QHBoxLayout()
        out_btn = QPushButton("输出文件夹（可选，默认在 PSD 旁）")
        out_btn.clicked.connect(self._pick_out)
        self._out_label = QLabel("（默认）")
        self._out_label.setStyleSheet("color:#64748b;")
        out_row.addWidget(out_btn)
        out_row.addWidget(self._out_label, 1)
        root.addLayout(out_row)

        hint = QLabel(
            "将 PSD 的每一层连同特效烘焙导出为 PNG，并生成 recipe.json 描述图层树、"
            "位置与类型。拼合结果与 Photoshop 人工合成一致（特效由渲染引擎烘焙）。"
        )
        hint.setStyleSheet("color:#94a3b8; font-size:11px;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        action_row = QHBoxLayout()
        run_btn = QPushButton("开始总结")
        run_btn.clicked.connect(self._run)
        action_row.addWidget(run_btn)
        self._status = _status_label()
        action_row.addWidget(self._status, 1)
        root.addLayout(action_row)

    def _pick_psd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 PSD 模板", "", "PSD (*.psd)")
        if not path:
            return
        self._psd_path = Path(path)
        self._out_dir = None
        self._out_label.setText("（默认）")
        self._psd_label.setText(path)

    def _pick_out(self) -> None:
        out_dir = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if not out_dir:
            return
        self._out_dir = Path(out_dir)
        self._out_label.setText(str(self._out_dir))

    def _run(self) -> None:
        if self._psd_path is None:
            self._status.setText("请先选择 PSD 模板。")
            return
        out_dir = self._out_dir or (self._psd_path.parent / f"{self._psd_path.stem}_summary")
        try:
            recipe = summarize_psd(self._psd_path, out_dir)
        except Exception as exc:
            QMessageBox.warning(self, "提示", f"总结失败：{exc}")
            return
        layer_count = len(recipe.get("layers", []))
        self._status.setText(
            f"完成：{out_dir}（{layer_count} 个图层，recipe.json + layers/*.png + composite.png）"
        )


class ToolsPage(BasePage):
    """小工具页：搜索 + 图片工具 + PSD 模板总结。"""

    page_id = "tools"
    display_name = "小工具"

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        header = QLabel("小工具")
        header.setObjectName("pageHeaderLabel")
        root.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(SearchPage(), "搜索")
        tabs.addTab(self._build_image_tools_tab(), "图片工具")
        tabs.addTab(self._build_psd_tab(), "PSD模板总结")
        root.addWidget(tabs, 1)

    def _build_image_tools_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        layout.addWidget(_CircleCropPanel())
        layout.addWidget(_GrayscalePanel())
        layout.addWidget(_DistrictIconPanel())
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _build_psd_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        layout.addWidget(_PsdSummarizePanel())
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll
