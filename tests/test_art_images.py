"""Portable pixel invariants, recipe failures and PSD layer isolation."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from ModTools_5_4.project.art_images import check_image, extract_psd, render_recipe


class ArtImagesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def save(self,name,image):
        image.save(self.root/name);return name

    def render(self,recipe):
        p=self.root/'recipe.json';p.write_text(json.dumps({'version':1,**recipe}),encoding='utf-8')
        result=render_recipe(p,self.root/'out.png')
        return Image.open(self.root/'out.png').convert('RGBA'),result

    def white_source(self):
        im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
        d.rectangle((12,12,51,51),fill='white');d.rectangle((28,28,35,35),fill=(0,0,0,0))
        return im

    def test_white_key_preserves_holes_and_antialias_rgb(self):
        im=Image.new('RGB',(64,64),'black');im.paste(self.white_source(),mask=self.white_source())
        self.save('logo.png',im)
        out,report=self.render({'kind':'white','source':'logo.png','mask_channel':'luminance','size':[64,64],'margin':10})
        self.assertEqual(out.getpixel((32,32))[3],0)
        self.assertTrue(check_image(out,'white')['ok'])
        self.assertEqual(report['visual_review'],'required')
        self.assertTrue(Path(report['preview']).is_file())

    def test_opaque_source_cannot_be_blindly_whitened(self):
        self.save('photo.png',Image.new('RGB',(64,64),'red'))
        with self.assertRaisesRegex(ValueError,'透明轮廓'):
            self.render({'kind':'white','source':'photo.png'})
        self.assertFalse((self.root/'out.png').exists())

    def test_moment_mask_preserves_dark_subject_and_source_alpha(self):
        self.save('photo.png',Image.new('RGBA',(456,332),(0,0,0,128)))
        mask=Image.new('L',(456,332));ImageDraw.Draw(mask).rectangle((20,20,435,311),fill=128)
        self.save('mask.png',mask)
        out,_=self.render({'kind':'moment','source':'photo.png','mask':'mask.png'})
        self.assertIn(out.getpixel((228,166))[3],(64,65))
        self.assertEqual(out.getpixel((0,0))[3],0)
        self.assertEqual(out.getpixel((228,166))[:3],(53,41,30))

    def test_leader_requires_explicit_crop(self):
        self.save('photo.png',self.white_source())
        with self.assertRaisesRegex(ValueError,'crop'):
            self.render({'kind':'leader','source':'photo.png'})

    def test_leader_composites_transparent_portrait_over_template(self):
        portrait=Image.new('RGBA',(256,256));ImageDraw.Draw(portrait).rectangle((110,80,145,175),fill='red')
        self.save('portrait.png',portrait)
        mask=Image.new('L',(256,256));ImageDraw.Draw(mask).ellipse((12,12,243,243),fill=255)
        self.save('mask.png',mask)
        bg=Image.new('RGBA',(256,256),'blue');bg.putalpha(mask);self.save('base.png',bg)
        out,_=self.render({'kind':'leader','source':'portrait.png','crop':[0,0,256,256],'background':'base.png','mask':'mask.png'})
        self.assertEqual(out.getpixel((128,128))[:3],(255,0,0))
        self.assertEqual(out.getpixel((70,128))[:3],(0,0,255))
        self.assertEqual(out.getpixel((0,0))[3],0)

    def test_district_rejects_colored_core(self):
        im=self.white_source();im.paste((255,0,0,255),(15,15,20,20));self.save('core.png',im)
        with self.assertRaisesRegex(ValueError,'白色透明'):
            self.render({'kind':'district','source':'core.png'})

    def test_district_rejects_old_flat_white_recipe(self):
        self.save('core.png',self.white_source())
        with self.assertRaisesRegex(ValueError,'Alpha'):
            self.render({'kind':'district','source':'core.png','background':'base.png','stroke':2})

    def district_template(self):
        """Author a tiny independent PSD; never use a user's template in tests."""
        try:
            from psd_tools import PSDImage
            from psd_tools.api.layers import PixelLayer
            from psd_tools.constants import Tag
            from psd_tools.psd.descriptor import Descriptor as D, Bool, Double, Integer, Enumerated as E, List
        except ImportError:
            self.skipTest('optional psd-tools not installed')
        def rgb(r,g,b):
            return D({b'Rd  ':Double(r),b'Grn ':Double(g),b'Bl  ':Double(b)},classID=b'RGBC')
        def gradient(colors):
            return D({b'GrdF':E(enum=b'CstS'),b'Intr':Double(4096),
                b'Clrs':List([D({b'Clr ':rgb(*color),b'Lctn':Integer(i*4096),b'Mdpn':Integer(50)}) for i,color in enumerate(colors)]),
                b'Trns':List([D({b'Opct':Double(100),b'Lctn':Integer(i*4096),b'Mdpn':Integer(50)}) for i in (0,1)])})
        def style(cls):
            return D({b'enab':Bool(True),b'present':Bool(True),b'Md  ':E(enum=b'Nrml'),b'Opct':Double(100)},classID=cls)
        overlay=style(b'GrFl')
        overlay.update({b'Grad':gradient([(240,40,50),(30,70,230)]),b'Angl':Double(-90),
                        b'Type':E(enum=b'Lnr '),b'Algn':Bool(True),b'Scl ':Double(100)})
        stroke=style(b'FrFX');stroke.update({**overlay,b'Styl':E(enum=b'InsF'),b'PntT':E(enum=b'GrFl'),b'Sz  ':Double(3)})
        stroke[b'Grad']=gradient([(50,250,100),(50,250,100)])
        glow=style(b'OrGl');glow.update({b'Md  ':E(enum=b'Mltp'),b'Clr ':rgb(0,0,0),b'Opct':Double(50),
            b'GlwT':E(enum=b'SfBL'),b'Ckmt':Double(100),b'blur':Double(3),b'Inpr':Double(50),
            b'TrnS':D({b'Crv ':List([D({b'Hrzn':Double(n),b'Vrtc':Double(n)}) for n in (0,255)])})})
        p=PSDImage.new('RGB',(256,256))
        p.create_pixel_layer(Image.new('RGB',(256,256),'orange'),name='Import Alpha')
        parent=p.create_group(name='Choose District')
        district=p.create_group(name='Test District');district.move_to_group(parent)
        bg=p.create_group(name='Icon Background');bg.move_to_group(district)
        PixelLayer.frompil(Image.new('RGB',(216,216),(128,128,128)),bg,name='Background',left=20,top=20)
        alpha=p.create_group(name='Alpha');alpha.move_to_group(district)
        PixelLayer.frompil(Image.new('RGB',(20,20),'red'),alpha,name='District Alpha',left=1,top=1)
        alpha.tagged_blocks.set_data(Tag.OBJECT_BASED_EFFECTS_LAYER_INFO,{
            b'masterFXSwitch':Bool(True),b'GrFl':overlay,b'FrFX':stroke,b'OrGl':glow})
        p.save(self.root/'template.psd')
        self.save('core.png',self.white_source())
        return p, {'kind':'district','source':'core.png','template_psd':'template.psd',
                   'alpha_layer':'1/0/1','background_layer':'1/0/0'}

    def test_district_inserts_core_into_alpha_and_renders_all_styles(self):
        from ModTools_5_4.project.district_psd import _plain
        p,recipe=self.district_template()
        before=(self.root/'template.psd').read_bytes()
        styles=[_plain(e.descriptor) for e in p[1][0][1].effects]
        out,report=self.render(recipe)
        self.assertEqual(before,(self.root/'template.psd').read_bytes())
        self.assertEqual(out.getpixel((2,2))[3],0)  # Sample/import excluded.
        self.assertEqual(out.getpixel((128,128))[:3],(128,128,128))  # Hole survives.
        self.assertNotEqual(out.getpixel((90,80))[:3],out.getpixel((90,178))[:3])
        self.assertGreater(out.getpixel((59,100))[1],200)  # Green inside stroke.
        self.assertLess(out.getpixel((56,100))[0],100)  # External multiply glow.
        self.assertEqual({e['effect'] for e in report['district']['effects']},
                         {'GradientOverlay','Stroke','OuterGlow'})
        self.assertFalse(report['district']['photoshop_pixel_match'])
        from psd_tools import PSDImage
        copy=PSDImage.open(self.root/'out.psd')
        group=copy[1][0][1]
        self.assertFalse(group[0].visible)
        self.assertEqual(group[1].name,'ModTools Core')
        self.assertTrue(group[1].visible)
        self.assertEqual(styles,[_plain(e.descriptor) for e in group.effects])

    def test_district_refuses_missing_style_and_foreign_group(self):
        p,recipe=self.district_template()
        from psd_tools.psd.descriptor import Bool
        effect=next(e for e in p[1][0][1].effects if e.name=='Stroke')
        effect.descriptor[b'enab']=Bool(False);p.mark_updated();p.save(self.root/'template.psd')
        with self.assertRaisesRegex(ValueError,'缺少'):
            self.render(recipe)
        recipe['alpha_layer']='1/0/0'
        with self.assertRaisesRegex(ValueError,'不同的组'):
            self.render(recipe)

    def test_district_refuses_unsupported_glow_instead_of_silently_dropping_it(self):
        p,recipe=self.district_template()
        from psd_tools.psd.descriptor import Double
        effect=next(e for e in p[1][0][1].effects if e.name=='OuterGlow')
        effect.descriptor[b'Nose']=Double(25);p.mark_updated();p.save(self.root/'template.psd')
        with self.assertRaisesRegex(ValueError,'发光样式'):
            self.render(recipe)
        self.assertFalse((self.root/'out.png').exists())

    def test_grayscale_check_rejects_color_and_solid_background(self):
        report=check_image(Image.new('RGBA',(256,256),'red'),'grayscale')
        self.assertFalse(report['ok']);self.assertGreaterEqual(len(report['errors']),2)

    def test_overwrite_protection_and_input_preservation(self):
        self.save('glyph.png',self.white_source())
        recipe={'kind':'white','source':'glyph.png'}
        self.render(recipe)
        before=(self.root/'out.png').read_bytes()
        with self.assertRaisesRegex(ValueError,'已存在'):self.render(recipe)
        self.assertEqual(before,(self.root/'out.png').read_bytes())

    def test_invalid_crop_is_rejected(self):
        self.save('glyph.png',self.white_source())
        with self.assertRaisesRegex(ValueError,'裁切框'):
            self.render({'kind':'white','source':'glyph.png','crop':[-1,0,64,64]})

    def test_psd_extract_ignores_black_backdrop_and_preserves_offsets(self):
        try:
            from psd_tools import PSDImage
        except ImportError:
            self.skipTest('optional psd-tools not installed')
        psd=PSDImage.new('RGB',(32,32))
        psd.create_pixel_layer(Image.new('RGBA',(32,32),'black'),name='Backdrop')
        psd.create_pixel_layer(Image.new('RGBA',(8,8),(255,255,255,128)),name='Mask',left=7,top=9)
        src=self.root/'test.psd';psd.save(src)
        out=self.root/'mask.png'
        extract_psd(src,out,['1'],channel='alpha',mode='composite')
        with Image.open(out) as im:
            self.assertEqual(im.size,(32,32));self.assertEqual(im.getpixel((7,9)),128)
            self.assertEqual(im.getpixel((0,0)),0)


if __name__=='__main__': unittest.main()
