import copy
import unittest

from modgen.modifier_validator import check_binary_yield_limits


class BinaryLimitTests(unittest.TestCase):
    def family(self, highest, effect='EFFECT_ADJUST_CITY_YIELD_CHANGE', sign=1):
        data={'modifiers': [], 'requirements': [], 'requirement_sets': []}
        bit=1
        while bit<=highest:
            rid=f'REQUIREMENT_BIT_{bit}';sid=f'REQSET_BIT_{bit}'
            data['requirements'].append({'requirement_id':rid,'requirement_type':'REQUIREMENT_PLOT_PROPERTY_MATCHES',
                'parameters':[{'name':'PropertyName','value':f'EXAMPLE_YIELD_{bit}'},{'name':'PropertyMinimum','value':1}]})
            data['requirement_sets'].append({'requirement_set_id':sid,'bound_requirements':[rid]})
            data['modifiers'].append({'modifier_id':f'MODIFIER_BIT_{bit}','effect_type':effect,'subject_reqset':sid,
                'parameters':[{'name':'Amount','value':bit*sign},{'name':'YieldType','value':'YIELD_PRODUCTION'}]})
            bit*=2
        return data

    def test_city_1024_allowed_and_31_bit_family_reported_once(self):
        self.assertEqual([],check_binary_yield_limits(self.family(1024)))
        data=self.family(1073741824);before=copy.deepcopy(data)
        warnings=check_binary_yield_limits(data)
        self.assertEqual(1,len(warnings));self.assertIn('1073741824',warnings[0])
        self.assertEqual(before,data)

    def test_effect_and_sign_have_separate_budgets(self):
        for effect,sign,bound in [('EFFECT_ADJUST_CITY_YIELD_CHANGE',-1,64),
                                  ('EFFECT_ADJUST_DISTRICT_BASE_YIELD_CHANGE',1,1024),
                                  ('EFFECT_ADJUST_PLOT_YIELD',1,64),('EFFECT_ADJUST_PLOT_YIELD',-1,8)]:
            with self.subTest(effect=effect,sign=sign):
                self.assertFalse(check_binary_yield_limits(self.family(bound,effect,sign)))
                self.assertEqual(1,len(check_binary_yield_limits(self.family(bound*2,effect,sign))))

    def test_nested_sets_cycles_and_non_binary_effects(self):
        data=self.family(2048)
        for m in data['modifiers']:
            sid=m['subject_reqset'];rid='REQUIREMENT_WRAPPER_'+sid;outer='REQSET_WRAPPER_'+sid
            data['requirements'].append({'requirement_id':rid,'requirement_type':'REQUIREMENT_REQUIREMENTSET_IS_MET',
                'parameters':[{'name':'RequirementSetId','value':sid}]})
            data['requirement_sets'].append({'requirement_set_id':outer,'bound_requirements':[rid]})
            m['subject_reqset']=outer
        self.assertEqual(1,len(check_binary_yield_limits(data)))
        for m in data['modifiers']:m.pop('subject_reqset')
        self.assertFalse(check_binary_yield_limits(data))
        data=self.family(2048)
        data['requirements'][0]={'requirement_id':'REQUIREMENT_BIT_1','requirement_type':'REQUIREMENT_REQUIREMENTSET_IS_MET',
            'parameters':[{'name':'RequirementSetId','value':'REQSET_BIT_1'}]}
        self.assertEqual(1,len(check_binary_yield_limits(data)))

    def test_one_high_constant_is_not_mislabeled_a_binary_family(self):
        data=self.family(2048)
        data['modifiers']=data['modifiers'][-1:]
        self.assertFalse(check_binary_yield_limits(data))

    def test_partial_invalid_workspaces_do_not_break_normal_validation(self):
        self.assertFalse(check_binary_yield_limits({'modifiers':None,'requirements':None,'requirement_sets':None}))
        data=self.family(2048)
        for s in data['requirement_sets']:s['bound_requirements']=None
        self.assertFalse(check_binary_yield_limits(data))


if __name__=='__main__':unittest.main()
