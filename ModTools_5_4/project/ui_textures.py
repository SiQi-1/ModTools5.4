"""Standalone, original-size UI textures shared by GUI, modgen and export.
Stored at workspace['美术']['data']['ui_textures']; no SQL or icon atlas rows.
"""
from __future__ import annotations
import re
from pathlib import Path
from .ui_icons import read_png_size

NAME_RE = re.compile(r'UI_[A-Za-z0-9_]+\Z')

def texture_entries(art: object) -> object:
    if not isinstance(art, dict):
        return []
    data = art.get('data', art)
    return data.get('ui_textures', []) if isinstance(data, dict) else []

def source_path(entry: dict, base_dir: Path | None = None) -> Path:
    path = Path(str(entry.get('path') or '').strip()).expanduser()
    return path if path.is_absolute() else (base_dir or Path.cwd()) / path

def validate_ui_textures(entries: object, *, base_dir: Path | None = None,
                         reserved_names=()) -> list[str]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        return ['独立 UI 纹理必须是列表']
    errors = []
    names = {str(n).casefold() for n in reserved_names}
    for i, entry in enumerate(entries):
        label = f'独立 UI 纹理[{i}]'
        if not isinstance(entry, dict):
            errors.append(f'{label}: 条目必须是对象'); continue
        name = entry.get('name')
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            errors.append(f'{label}: 名称须以 UI_ 开头，仅含英文字母、数字、下划线（不带扩展名）')
        elif name.casefold() in names:
            errors.append(f'{label}: 纹理名称重复或与已有输出冲突：{name}')
        else:
            names.add(name.casefold())
        raw = entry.get('path')
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f'{label}: 缺少源 PNG'); continue
        path = source_path(entry, base_dir)
        size = read_png_size(path) if path.suffix.lower() == '.png' else None
        if size is None:
            errors.append(f'{label}: 源文件不存在或不是有效 PNG：{path}')
        elif min(size) <= 0 or max(size) > 8192:
            errors.append(f'{label}: PNG 宽高须在 1～8192 像素内：{size}')
    return errors

def build_ui_texture_plans(entries: object, *, base_dir: Path | None = None) -> list[dict]:
    errors = validate_ui_textures(entries, base_dir=base_dir)
    if errors:
        raise ValueError('\n'.join(errors))
    plans = []
    for entry in entries or []:
        name = entry['name']; path = source_path(entry, base_dir).resolve()
        width, height = read_png_size(path)
        state = dict(path=str(path), scale=1.0, offset_x=0.0, offset_y=0.0,
                     canvas_width=width, canvas_height=height, circle_crop=False, add_black_border=False)
        plans.append(dict(name=name, relative_path=f'IMG/{name}.png', source_path=str(path),
                          source_state=state, target_width=width, target_height=height, category='ui_slice'))
    return plans
