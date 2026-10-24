"""Compose a leader cover from original artwork and a native PSD curtain layer.

Requires Pillow and psd-tools[composite]. This is deterministic layout, not image
generation or character retouching. All coordinates use the template canvas.
"""
from pathlib import Path
import argparse, hashlib, json
from PIL import Image, ImageDraw, ImageFont, ImageOps
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer


def render(recipe_path, output, replace=False):
    recipe_path = Path(recipe_path).resolve()
    recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
    output = Path(output).resolve()
    resolve = lambda value: (recipe_path.parent / value).resolve()
    template = resolve(recipe['template_psd'])
    background = resolve(recipe['background'])
    foreground = resolve(recipe['foreground'])
    sources = [template, background, foreground]
    psd = PSDImage.open(template)
    width, height = psd.size
    # This workflow handles a designated black rectangular layer, not arbitrary
    # Photoshop effects. Inspect the actual template before choosing the layer.
    layer_index = recipe['curtain_layer']
    curtain = psd[layer_index]
    overlay = curtain.composite(viewport=(0, 0, width, height), force=True, color=0, alpha=0).convert('RGBA')
    pixels = overlay.get_flattened_data() if hasattr(overlay, 'get_flattened_data') else overlay.getdata()
    visible = [pixel for pixel in pixels if pixel[3]]
    # The supplied rectangle has a thin white stroke. Keep the native vector
    # border, while rejecting a colored/image layer selected by mistake.
    if (not visible or any(p[0] != p[1] or p[1] != p[2] for p in visible)
            or sum(p[:3] == (0, 0, 0) for p in visible) / len(visible) < .9):
        raise ValueError('Selected curtain must be predominantly black with only grayscale borders')
    outputs = ['cover.png', 'cover-1024.png', 'cover-256.png', 'cover.psd', 'cover.json']
    output.mkdir(parents=True, exist_ok=True)
    if not replace and any((output/name).exists() for name in outputs):
        raise FileExistsError('Outputs exist; use --replace after preserving a previous version')
    if template in [output/name for name in outputs]:
        raise ValueError('Cannot overwrite the input template')
    bg_source = Image.open(background).convert('RGBA')
    fg_source = Image.open(foreground).convert('RGBA')

    def layers_at(factor):
        size = (round(width*factor), round(height*factor))
        bg = ImageOps.fit(bg_source, size, Image.Resampling.LANCZOS,
                          centering=tuple(recipe.get('background_focus', [.5, .5])))
        fg = Image.new('RGBA', size)
        place = recipe['foreground_transform']
        art = fg_source.resize((round(fg_source.width*place['scale']*factor),
                                round(fg_source.height*place['scale']*factor)), Image.Resampling.LANCZOS)
        fg.alpha_composite(art, (round(place['x']*factor), round(place['y']*factor)))
        layers = [('Background', bg), ('Standing art', fg),
                  ('Template black curtain', overlay.resize(size, Image.Resampling.NEAREST))]
        for item in recipe['text']:
            font_path = resolve(item['font'])
            if font_path not in sources:
                sources.append(font_path)
            font = ImageFont.truetype(str(font_path), round(item['size']*factor))
            text_layer = Image.new('RGBA', size)
            draw = ImageDraw.Draw(text_layer)
            box = draw.textbbox((0, 0), item['value'], font=font)
            if box[2]-box[0] > size[0]-round(2*recipe.get('text_margin', 20)*factor):
                raise ValueError('Text exceeds safe width: '+item['value'])
            x = (size[0]-(box[2]-box[0]))/2-box[0]
            y = item['top']*factor-box[1]
            if y+box[3] > size[1]-recipe.get('text_margin', 20)*factor:
                raise ValueError('Text exceeds safe height: '+item['value'])
            draw.text((round(x), round(y)), item['value'], font=font, fill=item.get('color', '#FFFFFF'))
            layers.append((item['name'], text_layer))
        return layers

    native = layers_at(1)
    for suffix, size in [('cover.png', width), ('cover-1024.png', 1024)]:
        layers = native if size == width else layers_at(size/width)
        result = Image.new('RGBA', layers[0][1].size)
        for _, bitmap in layers:
            result.alpha_composite(bitmap)
        if result.getextrema()[3] != (255, 255):
            raise ValueError('Cover must have an opaque background')
        result.convert('RGB').save(output/suffix)
    Image.open(output/'cover.png').resize((256, round(height*256/width)), Image.Resampling.LANCZOS).save(output/'cover-256.png')
    # Preserve the actual shape/opacity in the PSD. Other template layers are
    # intentionally excluded, so example art or labels cannot leak into output.
    for item in list(psd):
        if item is not curtain:
            psd.remove(item)
    bg_layer = PixelLayer.frompil(native[0][1], psd, 'Background')
    fg_layer = PixelLayer.frompil(native[1][1], psd, 'Standing art')
    psd.remove(bg_layer); psd.insert(0, bg_layer)
    psd.remove(fg_layer); psd.insert(1, fg_layer)
    curtain.name = 'Template black curtain'
    for index, (name, bitmap) in enumerate(native[3:], 1):
        PixelLayer.frompil(bitmap, psd, 'Text '+str(index))
    psd.save(output/'cover.psd')
    # psd-tools' default cache rendering can use the shape's stale raster cache
    # instead of its vector stroke. Save our vector-rendered merged preview too.
    saved = PSDImage.open(output/'cover.psd')
    header = saved._record.header
    if header.depth != 8 or header.channels not in (3, 4) or saved.pil_mode not in ('RGB', 'RGBA'):
        raise ValueError('This cover workflow requires an 8-bit RGB or RGBA template')
    preview = Image.open(output/'cover.png').convert('RGBA' if header.channels == 4 else 'RGB')
    saved._record.image_data.set_data([channel.tobytes() for channel in preview.split()], header)
    saved.save(output/'cover.psd')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'recipe': recipe, 'template_size':[width,height],
              'curtain':{'bbox':list(curtain.bbox),'opacity':curtain.opacity,'kind':curtain.kind},
              'sources':{str(path):sha(path) for path in sources},
              'outputs':{name:sha(output/name) for name in outputs if name!='cover.json'},
              'text_editing':'Text is on separate raster layers in PSD; edit the recipe to regenerate exact text.',
              'visual_review_required':['face placement','text legibility at 256px','crop and curtain placement']}
    (output/'cover.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe')
    parser.add_argument('--out', required=True)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    report = render(args.recipe, args.out, args.replace)
    print(json.dumps({'output':str(Path(args.out).resolve()),'files':list(report['outputs'])}, ensure_ascii=False))
