"""Landmark source ownership, state preservation and native export regressions.

Fixtures are original tiny XML; the tests do not require/redistribute SDK art.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from ModTools_5_4.project.landmarks import (
    RECIPE_FORMAT, SDKIndex, bind_entry, build_landmarks, compose, compose_asset,
    load_bundle, merge_artdef, sdk_xml, text_at, validate_assets, xml_text,
)
from modgen.landmark import import_bundle, verify_bundle


class LandmarkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.sdk = self.root / 'sdk'
        pantry = self.sdk / 'Civ6/pantry'
        for folder in ('Assets', 'Geometries', 'Materials'):
            (pantry / folder).mkdir(parents=True)
        self.pantry = pantry
        geo = '''<AssetObjects..GeometryInstance><m_Meshes><Element><m_Name text="Mesh"/><m_Groups><Element><m_Name text="Surface"/></Element></m_Groups></Element></m_Meshes><m_Bones><Element text="Root"/></m_Bones><m_DataFiles><Element><m_RelativePath text="Shape.fgx"/></Element></m_DataFiles></AssetObjects..GeometryInstance>'''
        (pantry / 'Geometries/Shape.geo').write_text(geo)
        (pantry / 'Geometries/Shape.fgx').write_bytes(b'fixture only')
        (pantry / 'Materials/Stone.mtl').write_text('<AssetObjects..MaterialInstance/>')
        root = ET.fromstring('''<AssetObjects..AssetInstance><m_BehaviorData><m_behaviorDataSets><m_animationBindings><m_Bindings/></m_animationBindings><m_timelineBindings><m_Bindings/></m_timelineBindings><m_timelines><m_Timelines/></m_timelines><m_attachmentPoints><m_Points/></m_attachmentPoints><m_stateSet/></m_behaviorDataSets><m_behaviorInstances/><m_dsgName text=""/><m_referenceGeometryNames/></m_BehaviorData><m_GeometrySet><m_ModelInstances><Element><m_Name text="RootInstance"/><m_GeoName text="Shape"/><m_GroupStates/></Element></m_ModelInstances></m_GeometrySet><m_CookParams><m_Values/></m_CookParams><m_Name text="Original"/><m_Description text="fixture"/><m_ClassName text="TileBase"/><m_DataFiles/></AssetObjects..AssetInstance>''')
        states = root.find('./m_GeometrySet/m_ModelInstances/Element/m_GroupStates')
        for name in ('Worked', 'Unworked', 'Pillaged', 'Construction', 'Unbuilt'):
            state = ET.SubElement(states, 'Element')
            values = ET.SubElement(ET.SubElement(state, 'm_Values'), 'm_Values')
            p = ET.SubElement(values, 'Element', {'class': 'AssetObjects..BoolValue'})
            ET.SubElement(p, 'm_bValue').text = 'true' if name in ('Worked', 'Unworked') else 'false'
            ET.SubElement(p, 'm_ParamName', {'text': 'Visible'})
            p = ET.SubElement(values, 'Element', {'class': 'AssetObjects..ObjectValue'})
            ET.SubElement(p, 'm_ObjectName', {'text': 'Stone'})
            ET.SubElement(p, 'm_eObjectType').text = 'MATERIAL'
            ET.SubElement(p, 'm_ParamName', {'text': 'Material'})
            for tag, value in [('m_MeshName', 'Mesh'), ('m_GroupName', 'Surface'), ('m_StateName', name)]:
                ET.SubElement(state, tag, {'text': value})
        self.ast = pantry / 'Assets/Original.ast'; self.ast.write_text(xml_text(root))
        self.spec = {'name': 'TEST_BASE', 'source': 'Original'}
        self.binding = {'kind': 'improvement', 'entity': 'IMPROVEMENT_TEST', 'source': 'IMPROVEMENT_SPHINX', 'landmark': 'LM_TEST', 'base_asset': 'TEST_BASE'}
        self.recipe = {'format': RECIPE_FORMAT, 'assets': [self.spec], 'bindings': [self.binding]}
        self.recipe_path = self.root / 'recipe.json'; self.bundle = self.root / 'bundle'

    def generate(self, recipe=None):
        self.recipe_path.write_text(json.dumps(recipe or self.recipe), encoding='utf-8')
        return compose(self.recipe_path, self.sdk, self.bundle)

    def test_sdk_states_preserved_and_repeated_composition_is_identical(self):
        path = self.generate(); before = load_bundle(path)[1]
        self.generate(); self.assertEqual(before, load_bundle(path)[1])
        root = ET.fromstring(before['Assets/TEST_BASE.ast'])
        states = root.findall('.//m_GroupStates/Element')
        self.assertEqual([s.findtext('./m_Values/m_Values/Element/m_bValue') for s in states], ['true', 'true', 'false', 'false', 'false'])
        self.assertTrue(verify_bundle(path, self.sdk)['ok'])

    def test_cpp_serializer_and_trailing_nul_are_normalized(self):
        raw = self.ast.read_text().replace('AssetObjects..', 'AssetObjects::')
        self.ast.write_bytes((raw + '\x00').encode())
        self.assertEqual(sdk_xml(self.ast).tag, 'AssetObjects..AssetInstance')
        self.assertTrue(verify_bundle(self.generate(), self.sdk)['ok'])

    def test_missing_geometry_material_binary_or_bone_rejected(self):
        for field, value in [('source', 'Absent')]:
            with self.assertRaisesRegex(ValueError, '0 matches'):
                compose_asset({**self.spec, field: value}, SDKIndex(self.sdk))
        (self.pantry / 'Geometries/Shape.fgx').unlink()
        with self.assertRaisesRegex(ValueError, 'missing geometry data'):
            self.generate()
        (self.pantry / 'Geometries/Shape.fgx').write_bytes(b'fixture')
        self.recipe['assets'].append({'name': 'PART', 'source': 'Original'})
        self.spec['attachments'] = [{'asset': 'PART', 'instance': 'RootInstance', 'bone': 'Absent'}]
        with self.assertRaisesRegex(ValueError, 'missing anchor bone'):
            self.generate()
        self.spec['attachments'][0]['bone'] = 'Root'
        (self.pantry / 'Materials/Stone.mtl').unlink()
        with self.assertRaisesRegex(ValueError, 'Stone'):
            self.generate()

    def test_cycle_and_missing_attachment_fail_before_bundle_write(self):
        self.spec['attachments'] = [{'asset': 'TEST_BASE', 'instance': 'RootInstance', 'bone': 'Root'}]
        with self.assertRaisesRegex(ValueError, 'cycle'):
            self.generate()
        self.assertFalse(self.bundle.exists())
        self.spec['attachments'][0]['asset'] = 'MISSING'
        with self.assertRaisesRegex(ValueError, 'missing local attachment'):
            self.generate()

    def test_transform_and_duplicate_names_rejected(self):
        for invalid in (0, -1, float('nan'), True):
            self.spec['attachments'] = [{'asset': 'TEST_BASE', 'instance': 'RootInstance', 'bone': 'Root', 'scale': invalid}]
            with self.assertRaisesRegex(ValueError, 'scale'):
                self.generate()
        self.spec.pop('attachments')
        self.recipe['assets'].append({**self.spec, 'name': 'test_base'})
        with self.assertRaisesRegex(ValueError, 'Duplicate asset'):
            self.generate()

    def test_stale_group_is_not_silently_accepted(self):
        self.ast.write_text(self.ast.read_text().replace('text="Surface"', 'text="DeletedGroup"'))
        with self.assertRaisesRegex(ValueError, 'unknown mesh/group'):
            self.generate()
        self.spec['drop_stale_groups'] = True
        self.assertTrue(verify_bundle(self.generate(), self.sdk)['ok'])

    def test_manifest_tampering_and_path_escape_rejected(self):
        path = self.generate()
        (self.bundle / 'Assets/TEST_BASE.ast').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'changed'):
            load_bundle(path)
        self.generate(); data = json.loads(path.read_text())
        data['files']['../outside.ast'] = 'bad'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'inside'):
            load_bundle(path)
        with self.assertRaisesRegex(ValueError, 'inside'):
            SDKIndex(self.sdk).find('../outside.ast', '.ast')

    def test_unrelated_nonempty_output_directory_is_not_owned(self):
        self.bundle.mkdir(); (self.bundle / 'user.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'not a landmark bundle'):
            self.generate()
        self.assertEqual((self.bundle / 'user.txt').read_text(), 'keep')

    def test_building_sets_cover_all_combinations_without_eras(self):
        binding = {'kind': 'district', 'entity': 'DISTRICT_TEST', 'source': 'DISTRICT_THEATER', 'landmark': 'DISTRICT_TEST', 'base_asset': 'TEST_BASE', 'buildings': [{'type': 'BUILDING_A', 'asset': 'TEST_BASE'}, {'type': 'BUILDING_B', 'asset': 'TEST_BASE'}]}
        self.recipe['bindings'] = [binding]
        data, files = load_bundle(self.generate())
        r = ET.fromstring(files['ArtDefs/Landmarks.artdef'])
        collections = {text_at(e, 'm_CollectionName'): e for e in r.findall('./m_RootCollections/Element/Element/m_ChildCollections/Element')}
        self.assertEqual(len(collections['BaseVariants'].findall('Element')), 4)
        self.assertEqual(len(collections['BuildingSets'].findall('Element')), 4)
        self.assertEqual(len(collections['BuildingVariants'].findall('Element')), 2)
        for p in r.findall('.//Element[@class="AssetObjects..ArtDefReferenceValue"]'):
            if text_at(p, 'm_ParamName') == 'Tag_Era':
                self.assertEqual(text_at(p, 'm_ElementName'), 'DEFAULT')
        self.assertIn('AffectsDistrictBuildingSet', files['ArtDefs/Buildings.artdef'])

    def test_supplemental_buildings_do_not_erase_user_art(self):
        existing = '<AssetObjects..ArtDefSet><m_TemplateName text="Buildings"/><m_RootCollections><Element><m_CollectionName text="Building"/><Element><m_Name text="BUILDING_A"/><m_Fields><m_Values><Element class="AssetObjects..BoolValue"><m_bValue>false</m_bValue><m_ParamName text="KeepMe"/></Element></m_Values></m_Fields><m_ChildCollections/></Element></Element></m_RootCollections></AssetObjects..ArtDefSet>'
        incoming = existing.replace('KeepMe', 'AffectsDistrictBuildingSet').replace('false', 'true')
        result = merge_artdef(existing, incoming)
        self.assertIn('KeepMe', result); self.assertIn('AffectsDistrictBuildingSet', result)
        self.assertEqual(result.count('m_Name text="BUILDING_A"'), 1)

        self.recipe['bindings'] = [{'kind': 'district', 'entity': 'DISTRICT_TEST', 'source': 'DISTRICT_THEATER', 'landmark': 'DISTRICT_TEST', 'base_asset': 'TEST_BASE', 'buildings': [{'type': 'BUILDING_A', 'asset': 'TEST_BASE'}]}]
        manifest = self.generate()
        _, files = load_bundle(manifest)
        project = self.root / 'project'
        for name, content in files.items():
            target = project / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
        report = verify_bundle(manifest, project=project)
        self.assertFalse(any('supplemental building' in error for error in report['errors']))
        building_file = project / 'ArtDefs/Buildings.artdef'
        building_file.write_text(building_file.read_text(encoding='utf-8').replace('<m_bValue>true</m_bValue>', '<m_bValue>false</m_bValue>'), encoding='utf-8')
        report = verify_bundle(manifest, project=project)
        self.assertIn('Invalid supplemental building field: BUILDING_A.AffectsDistrictBuildingSet', report['errors'])

        project_file = project / 'Test.civ6proj'
        project_file.write_text('<Project><ItemGroup><Content Include="Assets/TEST_BASE.ast"/></ItemGroup></Project>')
        self.assertIn('civ6proj must not register art source: Assets/TEST_BASE.ast', verify_bundle(manifest, project=project)['errors'])
        project_file.write_text('<Project/>')
        self.assertFalse(any('civ6proj' in error for error in verify_bundle(manifest, project=project)['errors']))

    def test_import_is_all_or_nothing_and_preserves_gameplay(self):
        path = self.generate(); civ = self.root / 'test.CIV'
        payload = {'workspace': {'改良设施': [{'type': 'IMPROVEMENT_TEST'}], '美术': {'data': {'ui_textures': []}}, '文本': {'keep': True}}}
        civ.write_text(json.dumps(payload)); before = civ.read_bytes()
        import_bundle(civ, path, dry_run=True); self.assertEqual(before, civ.read_bytes())
        import_bundle(civ, path)
        after = json.loads(civ.read_text(encoding='utf-8'))
        self.assertEqual(after['workspace']['文本'], payload['workspace']['文本'])
        self.assertEqual(before, civ.with_suffix('.CIV.bak').read_bytes())
        self.assertEqual(after['workspace']['美术']['data']['source_map']['improvement:IMPROVEMENT_TEST'], 'IMPROVEMENT_SPHINX')
        (self.bundle / 'Assets/TEST_BASE.ast').write_text('changed')
        before = civ.read_bytes()
        with self.assertRaises(ValueError): import_bundle(civ, path)
        self.assertEqual(before, civ.read_bytes())

    def test_gui_roundtrip_previews_ast_and_retains_dependencies(self):
        from PyQt6.QtWidgets import QApplication
        from ModTools_5_4.ui.pages.art_workspace import ArtWorkspacePanel
        from ModTools_5_4.ui.pages.workspace_page import WorkspacePage
        self.app = QApplication.instance() or QApplication([])
        panel = ArtWorkspacePanel(); self.addCleanup(panel.close)
        path = self.generate()
        state = {'landmark_bundle': {'manifest': str(path)}, 'source_map': {'improvement:IMPROVEMENT_TEST': 'IMPROVEMENT_SPHINX'}, 'need_map': {'improvement:IMPROVEMENT_TEST': True}, 'art_xml_source_config': {'required_game_art_ids': [{'name': 'Expansion1', 'id': '7446c8fe-29eb-44f8-801f-098f681cc5c5'}]}}
        panel.import_project_payload({'data': state})
        panel.refresh_from_sections({'改良设施': [{'type': 'IMPROVEMENT_TEST', 'name': 'Test'}]})
        saved = panel.export_project_payload()
        self.assertEqual(saved['data']['landmark_bundle'], state['landmark_bundle'])
        groups = panel.export_preview_file_groups()
        self.assertEqual(groups['AST'][0][0], 'TEST_BASE.ast')
        self.assertIn('LM_TEST', dict(groups['ArtDef'])['Improvements.artdef'])
        self.assertIn('7446c8fe-29eb-44f8-801f-098f681cc5c5', groups['Art.xml'][0][1])
        self.assertTrue(WorkspacePage._is_allowed_project_overview_file('Assets/TEST_BASE.ast'))


if __name__ == '__main__': unittest.main()
