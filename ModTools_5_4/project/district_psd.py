"""Insert district art under the PSD's Alpha group and render its styles.

The editable PSD preserves Photoshop's original descriptors. The PNG is a
parameter-based rendering: psd-tools draws gradients/strokes, while Pillow
and scipy supply the glows that its compositor does not draw. It is not a
pixel-identical Photoshop export; that distinction is part of every report.
"""
from __future__ import annotations

from PIL import Image, ImageChops, ImageFilter


def _plain(value):
    """Keep the actual style settings in the audit, including enum values."""
    if isinstance(value, bytes):
        return value.decode('ascii', errors='backslashreplace')
    if hasattr(value, 'enum'):
        return _plain(value.enum)
    if hasattr(value, 'items'):
        return {_plain(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)) or type(value).__name__ == 'List':
        return [_plain(v) for v in value]
    return _plain(value.value) if hasattr(value, 'value') else value


def _effects(layer):
    if not layer.effects.enabled:
        return []
    # The library's public list skips unknown effect classes. Reject those
    # explicitly instead of making an apparently successful incomplete PNG.
    from psd_tools.constants import Tag
    for tag in (Tag.OBJECT_BASED_EFFECTS_LAYER_INFO, Tag.OBJECT_BASED_EFFECTS_LAYER_INFO_V0,
                Tag.OBJECT_BASED_EFFECTS_LAYER_INFO_V1):
        if tag not in layer.tagged_blocks:
            continue
        block = layer.tagged_blocks.get_data(tag)
        for value in block.values():
            items = list(value) if type(value).__name__ == 'List' else [value]
            for item in items:
                if (hasattr(item, 'get') and bool(item.get(b'enab', False)) and
                        item.classID not in (b'GrFl', b'FrFX', b'OrGl', b'IrGl')):
                    raise ValueError(f'区域模板包含尚未支持的样式：{item.classID!r}')
        break
    return [e for e in layer.effects if e.enabled]


def _glow_mask(alpha, effect):
    """Approximate the template's smooth, linear-contour, edge glows.

    Size is read from the stored pixel descriptor (not multiplied a second
    time by the fx list's authoring-scale metadata). Photoshop's proprietary
    blur/contour rasterization is deliberately not claimed as exact.
    """
    import numpy as np
    from scipy.ndimage import distance_transform_edt

    size = float(effect.size)
    choke = float(effect.choke) / 100
    inner = effect.name == 'InnerGlow'
    seed = ImageChops.invert(alpha) if inner else alpha
    if size <= 0:
        return Image.new('L', alpha.size)
    spread = size * choke
    if spread:
        field = np.asarray(seed, dtype=float) / 255
        distance = distance_transform_edt(field < .5)
        expanded = np.maximum(field, np.clip(spread + .5 - distance, 0, 1))
        seed = Image.fromarray(np.rint(expanded * 255).astype('uint8'))
    blur = size * (1 - choke) / 3
    if blur:
        seed = seed.filter(ImageFilter.GaussianBlur(blur))
    # At the template's 50% range the default linear contour is unchanged.
    seed = seed.point(lambda n: min(255, round(n * 50 / effect.quality_range)))
    if inner:
        seed = ImageChops.multiply(seed, alpha)
    return seed.point(lambda n: round(n * float(effect.opacity) / 100))


def _apply_glow(backdrop, alpha, effect):
    color = tuple(round(float(effect.color[k])) for k in (b'Rd  ', b'Grn ', b'Bl  '))
    solid = Image.new('RGB', backdrop.size, color)
    base = backdrop.convert('RGB')
    blend = {b'Nrml': lambda a, b: b, b'Mltp': ImageChops.multiply,
             b'SftL': ImageChops.soft_light}[effect.blend_mode](base, solid)
    # A blend mode only blends where the backdrop has coverage.
    blend = Image.composite(blend, solid, backdrop.getchannel('A')).convert('RGBA')
    blend.putalpha(_glow_mask(alpha, effect))
    return Image.alpha_composite(backdrop, blend)


def _validate_effect(effect):
    if effect.name not in ('GradientOverlay', 'Stroke', 'OuterGlow', 'InnerGlow'):
        raise ValueError(f'区域模板包含尚未支持的样式：{effect.name}；请使用原生编辑器导出')
    if effect.name in ('OuterGlow', 'InnerGlow'):
        points = [(float(p[b'Hrzn']), float(p[b'Vrtc'])) for p in effect.contour[b'Crv ']]
        if (effect.glow_type != b'SfBL' or effect.blend_mode not in (b'Nrml', b'Mltp', b'SftL')
                or points != [(0., 0.), (255., 255.)] or effect.noise or effect.quality_jitter
                or effect.gradient is not None or not 0 < effect.quality_range <= 100
                or not 0 <= effect.choke <= 100 or not 0 <= effect.size <= 64
                or (effect.name == 'InnerGlow' and effect.descriptor[b'glwS'].enum != b'SrcE')):
            raise ValueError('发光样式超出已支持的平滑、线性轮廓、无噪点配置；请使用原生编辑器导出')
    else:
        if effect.blend_mode != b'Nrml' or effect.type != b'Lnr ':
            raise ValueError('区域渐变目前只支持 Normal 混合的线性渐变')
        desc = effect.descriptor
        offset = desc.get(b'Ofst')
        if (not bool(desc.get(b'Algn', True)) or
                (offset and any(float(offset[k]) for k in (b'Hrzn', b'Vrtc')))):
            raise ValueError('区域渐变必须与图层对齐且没有偏移')
        if effect.name == 'Stroke' and (effect.position != b'InsF' or desc[b'PntT'].enum != b'GrFl'):
            raise ValueError('区域模板目前只支持内部渐变描边')
        grad = desc[b'Grad']
        if grad[b'GrdF'].enum != b'CstS':
            raise ValueError('区域渐变必须使用明确色标')
        # psd-tools uses linear stop interpolation. Refuse active non-midpoint
        # transitions; the last stop's midpoint has no following interval.
        for key in (b'Clrs', b'Trns'):
            if any(int(stop[b'Mdpn']) != 50 for stop in list(grad[key])[:-1]):
                raise ValueError('区域渐变含非 50% 的有效中点；请使用原生编辑器导出')


def render_district(source, template, recipe, size):
    try:
        from psd_tools.api.layers import PixelLayer
        from psd_tools.constants import BlendMode, ColorMode
        from scipy.ndimage import distance_transform_edt  # noqa: F401 -- early dependency check
    except ImportError as exc:
        raise ValueError('区域 PSD 渲染需可选依赖：python -m pip install "psd-tools[composite]>=1.20"') from exc
    from .art_images import _fit_visible, _layers, _psd

    psd = _psd(template)
    if psd.size != size or psd.color_mode != ColorMode.RGB or psd.depth != 8:
        raise ValueError('区域模板必须为与输出同尺寸的 8 位 RGB PSD')
    layers = dict(_layers(psd))
    alpha_id, background_id = recipe.get('alpha_layer'), recipe.get('background_layer')
    if (alpha_id not in layers or background_id not in layers or
            alpha_id.rsplit('/', 1)[0] != background_id.rsplit('/', 1)[0] or alpha_id == background_id):
        raise ValueError('alpha_layer 与 background_layer 须是同一区域下两个不同的组编号；先 inspect-psd')
    alpha_group, background_group = layers[alpha_id], layers[background_id]
    if not alpha_group.is_group() or not background_group.is_group() or alpha_group.name != 'Alpha':
        raise ValueError('alpha_layer 必须指向模板的 Alpha 组，background_layer 必须指向底板组')
    names = {e.name for e in _effects(alpha_group)}
    if not {'GradientOverlay', 'Stroke', 'OuterGlow'} <= names:
        raise ValueError('Alpha 组缺少已启用的渐变叠加、描边或外发光；不能用平涂替代')

    # Keep only the selected district's background and Alpha hierarchy. Samples,
    # Import Alpha, Reference and every other district stay hidden in the copy.
    for ident, layer in layers.items():
        selected = (alpha_id, background_id)
        ancestor = any(s == ident or s.startswith(ident + '/') for s in selected)
        background_child = ident.startswith(background_id + '/') and layer.visible
        layer.visible = ancestor or background_child
    glyph = _fit_visible(source, size, recipe.get('glyph_box', [58, 58, 200, 200]))
    bounds = glyph.getbbox()
    inserted = PixelLayer.frompil(glyph.crop(bounds), alpha_group, name='ModTools Core',
                                  top=bounds[1], left=bounds[0])
    # Hidden sample bounds must not change the new glyph's gradient alignment.
    if tuple(alpha_group.bbox) != tuple(bounds):
        raise ValueError('Alpha 组存在影响新图案边界的隐藏内容；请检查模板结构')

    active = [(ident, layer) for ident, layer in _layers(psd) if layer.is_visible()]
    audit = []
    for ident, layer in active:
        if (layer.blend_mode not in (BlendMode.NORMAL, BlendMode.PASS_THROUGH) or
                layer.opacity != 255 or layer.fill_opacity != 255 or layer.clipping):
            raise ValueError('区域模板的可见层需使用 Normal/Pass-through 且图层不透明度为 100%')
        if layer.is_group() and (layer.has_mask() or layer.has_vector_mask()):
            raise ValueError('区域模板暂不支持额外的组蒙版')
        for effect in _effects(layer):
            if layer is not alpha_group and not ident.startswith(background_id + '/'):
                raise ValueError('样式应位于 Alpha 组或底板像素层，父组样式需原生编辑器导出')
            _validate_effect(effect)
            if effect.name == 'InnerGlow' and not ident.startswith(background_id + '/'):
                raise ValueError('内发光只支持底板像素层')
            if effect.name == 'OuterGlow' and layer is not alpha_group:
                raise ValueError('外发光只支持 Alpha 组')
            audit.append({'layer': ident, 'layer_name': layer.name, 'effect': effect.name,
                          'fx_scale_metadata': layer.effects.scale, 'parameters': _plain(effect.descriptor),
                          'renderer': 'parameter-glow' if 'Glow' in effect.name else 'psd-tools'})

    def branch(ident):
        states = [(key, layer, layer.visible) for key, layer in _layers(psd)]
        try:
            for key, layer, visible in states:
                layer.visible = (key == ident or ident.startswith(key + '/') or
                                 (key.startswith(ident + '/') and visible))
            return psd.composite(force=True, color=(0., 0., 0.), alpha=0.).convert('RGBA')
        finally:
            for _, layer, visible in states:
                layer.visible = visible

    background = branch(background_id)
    for ident, layer in active:
        for effect in _effects(layer):
            if effect.name == 'InnerGlow':
                background = _apply_glow(background, branch(ident).getchannel('A'), effect)
    for effect in _effects(alpha_group):
        if effect.name == 'OuterGlow':
            background = _apply_glow(background, glyph.getchannel('A'), effect)
    out = Image.alpha_composite(background, branch(alpha_id))
    report = {'renderer': 'psd-alpha-group-v1', 'alpha_layer': alpha_id,
              'background_layer': background_id, 'inserted_layer': inserted.name,
              'glyph_bbox': list(bounds), 'effects': audit,
              'photoshop_pixel_match': False,
              'approximations': ['PNG 发光采用参数化形态扩张与高斯核；并非 Photoshop 原生光栅化',
                                 'PNG 渐变由 psd-tools 插值，不复现 Photoshop 的平滑度、抖动与色彩管理',
                                 '样式使用已存储的像素尺寸；fx scale 元数据保留于 PSD，不再次乘算'],
              'editable_psd': '保留原始样式描述，输入白图位于 Alpha 组内；PSD 缓存预览不作为验收依据'}
    return out, psd, report
