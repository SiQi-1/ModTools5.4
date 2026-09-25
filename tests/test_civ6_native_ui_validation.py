"""Native UI authoring contracts, independent of Civ6 installation or GUI."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'skills/civ6-html-ui/scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('civ6_native_check',SCRIPTS/'check-native-ui.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

class NativeUIContracts(unittest.TestCase):
    def verify(self, body, textures=None):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'panel.xml';file.write_text('<Context><Container Size="208,316">'+body+'</Container></Context>',encoding='utf8')
            return checker.check(file,textures or {'UI_TEST_BUTTON':[180,160]},{'FontFlair30','FontNormal16'})
    def button(self, **attributes):
        values={'ID':'Action','Size':'180,40','Offset':'14,262','Texture':'UI_TEST_BUTTON','States':'4','StateOffsetIncrement':'0,40'}
        values.update(attributes)
        return '<Button '+' '.join(f'{k}="{v}"' for k,v in values.items())+'/>'
    def test_exact_four_state_button(self):
        self.assertEqual(self.verify(self.button()),([],[]))
    def test_missing_font_style(self):
        errors,_=self.verify('<Label Style="FontFlair32"/>');self.assertTrue(errors)
    def test_frame_width_mismatch(self):
        errors,_=self.verify(self.button(),{'UI_TEST_BUTTON':[256,160]});self.assertTrue(errors)
    def test_out_of_bounds_and_reversed_atlas(self):
        self.assertTrue(self.verify(self.button(Offset='50,262'))[0])
        self.assertTrue(self.verify(self.button(StateOffsetIncrement='0,-40'))[0])
    def test_nine_slice_is_not_claimed_valid(self):
        errors,warnings=self.verify('<GridButton><GridData Texture="UI_TEST_BUTTON"/></GridButton>')
        self.assertFalse(errors);self.assertTrue(warnings)
    def test_starter(self):
        textures={'UI_DEMO_PANEL':[640,400],'UI_DEMO_BUTTON':[256,192],'UI_DEMO_SELECTED':[256,160]}
        errors,_=checker.check(SCRIPTS.parent/'assets/starter/NativePanel.xml',textures)
        self.assertFalse(errors)

if __name__=='__main__':unittest.main()
