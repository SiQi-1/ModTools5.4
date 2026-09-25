"""Internal UnitAbilities must stay invisible unless display text is supplied."""
import json
import subprocess
import sys
import unittest
from modgen.modifier_generator import generate_ability
from modgen.modifier_validator import check_ability

class OptionalAbilityTextTests(unittest.TestCase):
    def test_omitted_and_blank_text_is_null_without_warning(self):
        for args in ({}, {"name_zh": None, "description_zh": None}, {"name_zh": "  ", "description_zh": ""}):
            with self.subTest(args=args):
                row = generate_ability(prefix="TEST", infix=1, abbr="INTERNAL", **args)
                self.assertIsNone(row["name_zh"])
                self.assertIsNone(row["description_zh"])
                self.assertEqual(check_ability(row), ([], []))
                self.assertFalse(row["show_float_text_when_earned"])

    def test_name_and_description_are_independently_optional(self):
        for args, expected in [({"name_zh":"名字"},("名字",None)),({"description_zh":"说明"},(None,"说明"))]:
            row=generate_ability(prefix="TEST",infix=1,abbr="VISIBLE",**args)
            self.assertEqual((row["name_zh"],row["description_zh"]),expected)
            self.assertEqual(check_ability(row),([],[]))

    def test_cli_accepts_internal_ability_without_name(self):
        run=subprocess.run([sys.executable,"-X","utf8","-m","modgen.cli","generate-ability","--abbr","INTERNAL"],capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(run.returncode,0,run.stderr)
        row=json.loads(run.stdout)
        self.assertIsNone(row["name_zh"])
        self.assertIsNone(row["description_zh"])

if __name__=="__main__":unittest.main()
