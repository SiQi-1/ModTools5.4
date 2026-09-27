"""Deterministic Civ6 image preparation, independent of Qt and any AI provider.

PSD reading is optional. Rendering baked PNG templates needs only Pillow.
Pixel checks never certify portrait composition or Photoshop effect fidelity.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageOps

KINDS = ('white', 'grayscale', 'leader', 'district', 'moment')
EXPECTED_SIZES = {'leader': (256, 256), 'district': (256, 256), 'moment': (456, 332)}


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _outputs(paths, sources=(), replace=False):
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('输出文件重名')
    for path in resolved:
        if path in {Path(p).resolve() for p in sources}:
            raise ValueError('输出不可覆盖输入素材')
        if path.exists() and not replace:
            raise ValueError(f'输出已存在，使用 --replace 明确覆盖：{path}')
    for path in resolved:
        path.parent.mkdir(parents=True, exist_ok=True)


def _open(path):
    with Image.open(path) as im:
        if im.width * im.height > 40_000_000:
            raise ValueError('源图片超过 4000 万像素')
        return ImageOps.exif_transpose(im).convert('RGBA')


def _size(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('size 必须是 [宽, 高]')
    if any(isinstance(n, bool) or int(n) != n or not 1 <= n <= 4096 for n in value):
        raise ValueError('尺寸必须是 1～4096 的整数')
    return tuple(int(n) for n in value)


def _box(value, size):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('裁切框必须是 [left, top, right, bottom]')
    box = tuple(float(n) for n in value)
    if not all(math.isfinite(n) for n in box):
        raise ValueError('裁切坐标必须是有限数值')
    x1, y1, x2, y2 = box
    if not 0 <= x1 < x2 <= size[0] or not 0 <= y1 < y2 <= size[1]:
        raise ValueError('裁切框必须位于源图片内且宽高大于零')
    return box


def _mask(image, channel):
    if image.mode in ('1', 'L'):
        return image.convert('L')
    rgba = image.convert('RGBA')
    if channel == 'alpha':
        return rgba.getchannel('A')
    if channel == 'luminance':
        return ImageChops.multiply(ImageOps.grayscale(rgba), rgba.getchannel('A'))
    raise ValueError('mask_channel 只能是 alpha 或 luminance')


def _paint(mask, color):
    im = Image.new('RGBA', mask.size, ImageColor.getrgb(color) + (255,))
    im.putalpha(mask)
    return im


def _fit_visible(image, size, box):
    bounds = image.getchannel('A').getbbox()
    if bounds is None:
        raise ValueError('图案完全透明')
    x1, y1, x2, y2 = map(round, _box(box, size))
    glyph = ImageOps.contain(image.crop(bounds), (x2-x1, y2-y1), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', size)
    canvas.alpha_composite(glyph, (x1+(x2-x1-glyph.width)//2, y1+(y2-y1-glyph.height)//2))
    return canvas


def check_image(image, kind, expected_size=None):
    if kind not in KINDS:
        raise ValueError('未知图像类型')
    im = image.convert('RGBA')
    errors, warnings = [], []
    expected_size = expected_size or EXPECTED_SIZES.get(kind)
    if expected_size and im.size != tuple(expected_size):
        errors.append(f'尺寸应为 {list(expected_size)}，实际 {list(im.size)}')
    alpha = im.getchannel('A')
    low, high = alpha.getextrema()
    if high == 0:
        errors.append('图片完全透明')
    if low != 0:
        errors.append('缺少完全透明的背景像素')
    corners = [alpha.getpixel(p) for p in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]]
    if any(corners):
        errors.append('四角存在不透明背景')
    visible_mask = alpha.point(lambda a:255 if a else 0)
    r,g,b,_ = im.split()
    white_error = ImageChops.multiply(ImageChops.invert(ImageChops.darker(ImageChops.darker(r,g),b)),visible_mask)
    gray_error = ImageChops.multiply(ImageChops.lighter(ImageChops.difference(r,g),ImageChops.difference(g,b)),visible_mask)
    if kind == 'white' and white_error.getbbox():
        errors.append('白色图标的所有可见像素 RGB 必须为 255,255,255；边缘用 Alpha 抗锯齿')
    if kind == 'grayscale' and gray_error.getbbox():
        errors.append('灰度图标含彩色像素')
    dark_mask = ImageChops.multiply(r.point(lambda n:255 if n<96 else 0),alpha.point(lambda a:255 if a>=128 else 0))
    if kind == 'grayscale' and dark_mask.getbbox():
        warnings.append('含较暗主体像素；在深色游戏界面上检查辨识度')
    coverage = sum(alpha.histogram()[1:]) / (im.width*im.height)
    if 0 < coverage < .03:
        warnings.append('主体占比低于 3%，缩小后可能难以辨认')
    return {'ok': not errors, 'kind': kind, 'size': list(im.size), 'errors': errors,
            'warnings': warnings, 'alpha_range': [low,high], 'alpha_bbox': alpha.getbbox(),
            'coverage': round(coverage,4), 'visual_review': 'required',
            'unverified': ['主体识别、脸部构图、风格匹配、实际游戏显示未由像素检查验证']}


def preview_image(im):
    """Light/dark/checker backgrounds plus real 64/38/22-pixel thumbnails."""
    w, h = im.size
    out = Image.new('RGB', (w*3, h+110), '#393e46')
    for i, color in enumerate(('#eeeeee','#162334',None)):
        bg = Image.new('RGBA', im.size, color or '#aaaaaa')
        if color is None:
            d = ImageDraw.Draw(bg)
            for y in range(0,h,16):
                for x in range(0,w,16):
                    if (x//16+y//16)%2: d.rectangle((x,y,x+15,y+15), fill='#dddddd')
        out.paste(Image.alpha_composite(bg,im).convert('RGB'),(i*w,0))
        x = i*w+12
        for side in (64,38,22):
            small = ImageOps.contain(im,(side,side),Image.Resampling.LANCZOS)
            out.paste(small,(x,h+16),small);x += side+15
    return out


def render_recipe(recipe_path, output, *, replace=False):
    recipe_path, output = Path(recipe_path), Path(output)
    recipe = json.loads(recipe_path.read_text(encoding='utf-8-sig'))
    if recipe.get('version') != 1 or recipe.get('kind') not in KINDS:
        raise ValueError('配方需要 version: 1 和合法 kind')
    kind = recipe['kind']
    size = _size(recipe.get('size', EXPECTED_SIZES.get(kind,(256,256))))
    sources = [recipe_path]

    def asset(key):
        value = recipe.get(key)
        if not isinstance(value,str) or not value:
            raise ValueError(f'缺少素材路径 {key}')
        path = (recipe_path.parent/value).resolve()
        sources.append(path)
        return _open(path)

    district_psd = None
    district_report = None
    source = asset('source')
    if recipe.get('crop') is not None:
        source = source.crop(_box(recipe['crop'],source.size))

    if kind in ('white','grayscale'):
        channel = recipe.get('mask_channel','alpha')
        mask = _mask(source,channel)
        if mask.getextrema()[0] > 0:
            raise ValueError('源图没有透明轮廓；黑底白图可显式使用 mask_channel: luminance，复杂背景需先抠图')
        if kind == 'white':
            source = _paint(mask,'#ffffff')
        else:
            levels = recipe.get('levels',[128,255])
            if len(levels)!=2 or not 0 <= levels[0] <= levels[1] <= 255:
                raise ValueError('levels 必须是递增的 0～255 灰度范围')
            source = ImageOps.colorize(ImageOps.grayscale(source), tuple([int(levels[0])]*3), tuple([int(levels[1])]*3)).convert('RGBA')
            source.putalpha(mask)
        margin = int(recipe.get('margin',20))
        out = _fit_visible(source,size,[margin,margin,size[0]-margin,size[1]-margin])
        if kind == 'white':
            # Resampling must never leave grey RGB values on translucent edges.
            out = _paint(out.getchannel('A'),'#ffffff')
    elif kind == 'moment':
        mask_path = (recipe_path.parent/recipe['mask']).resolve();sources.append(mask_path)
        with Image.open(mask_path) as m: mask = _mask(m,recipe.get('mask_channel','alpha'))
        if mask.size != size or mask.getextrema()[0] != 0:
            raise ValueError('历史时刻蒙版须与输出同尺寸，且具有透明区域')
        focus = recipe.get('focus',[.5,.5])
        if len(focus)!=2 or any(not 0<=n<=1 for n in focus): raise ValueError('focus 范围为 0～1')
        out = ImageOps.fit(source,size,Image.Resampling.LANCZOS,centering=tuple(focus))
        gray = ImageEnhance.Contrast(ImageOps.grayscale(out)).enhance(float(recipe.get('contrast',1.1)))
        tone = recipe.get('tone',['#35291e','#ddcba7'])
        if len(tone)!=2: raise ValueError('tone 需要暗部和亮部两种颜色')
        toned = ImageOps.colorize(gray,*tone).convert('RGBA')
        toned.putalpha(ImageChops.multiply(out.getchannel('A'),mask));out=toned
    elif kind == 'leader':
        if 'crop' not in recipe:
            raise ValueError('头像必须提供经看图确定的 crop；工具不自动识别人脸')
        background = asset('background')
        if background.size != size: raise ValueError('头像底板必须与输出同尺寸')
        mask_path = (recipe_path.parent/recipe['mask']).resolve();sources.append(mask_path)
        with Image.open(mask_path) as m: mask = _mask(m,recipe.get('mask_channel','alpha'))
        if mask.size != size: raise ValueError('头像蒙版尺寸不一致')
        portrait = ImageOps.fit(source,size,Image.Resampling.LANCZOS)
        portrait.putalpha(ImageChops.multiply(portrait.getchannel('A'),mask))
        out = Image.alpha_composite(background,portrait)
        out.putalpha(ImageChops.multiply(out.getchannel('A'),mask))
        border = int(recipe.get('border',2))
        if not 0<=border<=12: raise ValueError('border 范围为 0～12 像素')
        if border:
            ring = _paint(mask.filter(ImageFilter.MaxFilter(border*2+1)),recipe.get('border_color','#101820'))
            out = Image.alpha_composite(ring,out)
    else:
        check = check_image(source,'white')
        if not check['ok']: raise ValueError('区域核心图片必须先制作为白色透明图：'+ ';'.join(check['errors']))
        if not recipe.get('template_psd'):
            raise ValueError('区域配方须指定 template_psd、alpha_layer、background_layer；旧的底板叠白图配方不符合 Alpha 组处理要求')
        if any(key in recipe for key in ('background','stroke','stroke_color')):
            raise ValueError('区域样式从 PSD Alpha 组读取，请移除旧的 background/stroke/stroke_color 字段')
        from .district_psd import render_district
        template = (recipe_path.parent/recipe['template_psd']).resolve();sources.append(template)
        out,district_psd,district_report = render_district(source,template,recipe,size)

    result = check_image(out,kind,size)
    if not result['ok']: raise ValueError('; '.join(result['errors']))
    sidecar = output.with_suffix('.json');preview = output.with_name(output.stem+'.preview.png')
    psd_output = output.with_suffix('.psd')
    _outputs([output,sidecar,preview]+([psd_output] if district_psd is not None else []),sources,replace)
    out.save(output,format='PNG');preview_image(out).save(preview,format='PNG')
    if district_psd is not None:
        district_psd.save(psd_output)
        result['district'] = district_report
        result['editable_psd'] = {'path':str(psd_output.resolve()),'sha256':_hash(psd_output)}
        result['unverified'].extend(district_report['approximations'])
    result.update({'output':str(output.resolve()),'preview':str(preview.resolve()),'recipe':str(recipe_path.resolve()),
                   'inputs':[{'path':str(p.resolve()),'sha256':_hash(p)} for p in sources], 'sha256':_hash(output)})
    _write_json(sidecar,result)
    return result


def _psd(path):
    try:
        from psd_tools import PSDImage
    except ImportError as exc:
        raise ValueError('读取 PSD 需可选依赖：python -m pip install psd-tools；PNG 配方合成不需要它') from exc
    psd = PSDImage.open(path)
    if psd.width*psd.height > 40_000_000: raise ValueError('PSD 超过 4000 万像素')
    return psd


def _layers(group, prefix=''):
    for i, layer in enumerate(group):
        ident = prefix+str(i)
        yield ident, layer
        if layer.is_group(): yield from _layers(layer,ident+'/')


def inspect_psd(path, out, *, replace=False):
    path,out=Path(path),Path(out)
    psd=_psd(path)
    data={'source':str(path.resolve()),'sha256':_hash(path),'size':list(psd.size),'layers':[],
          'unverified':['PSD 合成预览不证明所有图层样式与 Photoshop 一致；保留原文件作视觉对照']}
    for ident,layer in _layers(psd):
        data['layers'].append({'id':ident,'name':layer.name,'kind':layer.kind,'visible':layer.visible,
            'bbox':list(layer.bbox),'opacity':layer.opacity,'blend_mode':str(layer.blend_mode),
            'effects':str(layer.effects),'has_mask':layer.has_mask()})
    report=out/'layers.json';preview=out/'composite.png'
    _outputs([report,preview],[path],replace)
    # The embedded merged preview is Photoshop's saved reference, not a re-render.
    with Image.open(path) as merged: merged.convert('RGBA').save(preview)
    _write_json(report,data)
    return data


def extract_psd(path, output, layer_ids, *, channel='rgba', mode='pixels', replace=False):
    path,output=Path(path),Path(output)
    psd=_psd(path);layers=dict(_layers(psd))
    if not layer_ids or any(i not in layers for i in layer_ids): raise ValueError('图层编号不存在；先运行 inspect-psd')
    if mode=='pixels':
        if len(layer_ids)!=1: raise ValueError('pixels 模式只接受一个像素图层')
        layer=layers[layer_ids[0]]
        if layer.is_group() or layer.has_mask() or layer.has_vector_mask():
            raise ValueError('组或带蒙版图层请使用 composite 模式并进行视觉复核')
        raw=layer.topil()
        if raw is None: raise ValueError('所选图层没有可读取的像素')
        raw=raw.convert('RGBA')
        raw.putalpha(raw.getchannel('A').point(lambda a:round(a*layer.opacity/255)))
        im=Image.new('RGBA',psd.size);im.paste(raw,layer.offset)
    elif mode=='composite':
        for ident,layer in layers.items():
            ancestor=any(s==ident or s.startswith(ident+'/') for s in layer_ids)
            descendant=any(ident.startswith(s+'/') for s in layer_ids)
            layer.visible = ancestor or (descendant and layer.visible)
        im=psd.composite(force=True,color=(0.,0.,0.),alpha=0.0)
        if im is None: raise ValueError('PSD 合成失败')
    else: raise ValueError('未知 PSD 提取模式')
    if channel!='rgba': im=_mask(im,channel)
    sidecar=output.with_suffix('.json')
    _outputs([output,sidecar],[path],replace)
    im.save(output,format='PNG')
    report={'source':str(path.resolve()),'source_sha256':_hash(path),'layers':layer_ids,'mode':mode,
            'channel':channel,'size':list(im.size),'output':str(output.resolve()),'sha256':_hash(output),
            'unverified':['pixels 不渲染图层样式；composite 对 Photoshop 效果的复现需视觉复核']}
    _write_json(sidecar,report)
    return report
