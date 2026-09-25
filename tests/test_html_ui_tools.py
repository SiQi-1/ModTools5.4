"""Portable HTML UI bundle, all-or-nothing texture import and CLI regressions."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from modgen.cli import main
from modgen import html_ui
from modgen.texture import import_manifest


class HtmlUIFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='html-ui-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.png_dir = self.root / '设计 纹理'
        self.png_dir.mkdir()
        self.manifest = self.png_dir / 'texture_manifest.json'
        self.civ = self.root / 'sample.CIV'
        self.original = {'meta': {'schema_version': '0.1.0'}, 'workspace': {
            '美术': {'data': {'other_art': {'preserve': True}}},
            '文本': {'custom_entries': [{'tag': 'LOC_KEEP', 'text': '保留'}]},
            '文明': [{'name': '保留文明'}]}, 'extensions': {'version': 1, 'files': []}}
        self.civ.write_text(json.dumps(self.original, ensure_ascii=False), encoding='utf-8')
        self.put_manifest({'UI_ALPHA': [19, 13], 'UI_BETA': [12, 8]})

    def put_manifest(self, entries):
        for name, size in entries.items():
            Image.new('RGBA', size, (45, 70, 95, 140)).save(self.png_dir / f'{name}.png')
        self.manifest.write_text(json.dumps(entries), encoding='utf-8')

    def cli(self, *args):
        with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
            code = main([str(arg) for arg in args])
        return code, output.getvalue(), error.getvalue()

    def declarations(self):
        data = json.loads(self.civ.read_text(encoding='utf-8'))
        return data['workspace']['美术']['data']['ui_textures']


class TextureManifestImportTest(HtmlUIFixture):
    def test_batch_preserves_unrelated_data_and_original_backup(self):
        before = self.civ.read_bytes()
        result = import_manifest(self.civ, self.manifest)
        self.assertEqual(result['added'], ['UI_ALPHA', 'UI_BETA'])
        self.assertEqual(self.civ.with_suffix('.CIV.bak').read_bytes(), before)
        after = json.loads(self.civ.read_text(encoding='utf-8'))
        for section in ('文本', '文明'):
            self.assertEqual(after['workspace'][section], self.original['workspace'][section])
        self.assertEqual(after['extensions'], self.original['extensions'])
        self.assertEqual(after['workspace']['美术']['data']['other_art'], {'preserve': True})
        for entry in self.declarations():
            self.assertTrue(Path(entry['path']).is_absolute())
            self.assertTrue(Path(entry['path']).is_file())

    def test_failure_in_last_png_makes_no_partial_edit_or_backup(self):
        before = self.civ.read_bytes()
        (self.png_dir / 'UI_BETA.png').unlink()
        with self.assertRaises(OSError):
            import_manifest(self.civ, self.manifest)
        self.assertEqual(self.civ.read_bytes(), before)
        self.assertFalse(self.civ.with_suffix('.CIV.bak').exists())

    def test_wrong_size_or_non_png_is_rejected(self):
        target = self.png_dir / 'UI_BETA.png'
        Image.new('RGB', (1, 1)).save(target)
        before = self.civ.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Wrong dimensions'):
            import_manifest(self.civ, self.manifest)
        target.write_text('not a PNG', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Invalid PNG'):
            import_manifest(self.civ, self.manifest)
        self.assertEqual(self.civ.read_bytes(), before)

    def test_case_replacement_and_dry_run_preserve_unlisted_texture(self):
        import_manifest(self.civ, self.manifest)
        before = self.civ.read_bytes()
        self.put_manifest({'UI_alpha': [19, 13], 'UI_GAMMA': [4, 5]})
        with self.assertRaisesRegex(ValueError, '--replace'):
            import_manifest(self.civ, self.manifest)
        backup = self.civ.with_suffix('.CIV.bak').read_bytes()
        result = import_manifest(self.civ, self.manifest, replace=True, dry_run=True)
        self.assertEqual(result['replaced'], ['UI_alpha'])
        self.assertEqual(result['added'], ['UI_GAMMA'])
        self.assertEqual(self.civ.read_bytes(), before)
        self.assertEqual(self.civ.with_suffix('.CIV.bak').read_bytes(), backup)
        import_manifest(self.civ, self.manifest, replace=True)
        self.assertEqual([e['name'] for e in self.declarations()], ['UI_alpha', 'UI_BETA', 'UI_GAMMA'])

    def test_replace_can_relink_missing_old_sources_after_project_move(self):
        import_manifest(self.civ, self.manifest)
        payload = json.loads(self.civ.read_text(encoding='utf-8'))
        for entry in payload['workspace']['美术']['data']['ui_textures']:
            entry['path'] = str(self.root / 'missing-old-directory' / (entry['name'] + '.png'))
        self.civ.write_text(json.dumps(payload), encoding='utf-8')
        result = import_manifest(self.civ, self.manifest, replace=True)
        self.assertEqual(result['replaced'], ['UI_ALPHA', 'UI_BETA'])
        self.assertTrue(all(Path(entry['path']).is_file() for entry in self.declarations()))

    def test_invalid_manifest_variants_never_write(self):
        before = self.civ.read_bytes()
        for text in ('{}', '[]', '{"../escape":[1,1]}', '{"UI_A":[true,1]}',
                     '{"UI_A":[8193,1]}', '{"UI_A":[1,1],"UI_a":[1,1]}',
                     '{"UI_A":[1,1],"UI_A":[1,1]}'):
            with self.subTest(text=text):
                self.manifest.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    import_manifest(self.civ, self.manifest)
                self.assertEqual(self.civ.read_bytes(), before)

    def test_cli_success_and_error_status_are_machine_readable(self):
        code, output, error = self.cli('texture', 'import-manifest', self.civ, '--manifest', self.manifest, '--dry-run')
        self.assertEqual((code, error), (0, ''))
        self.assertTrue(json.loads(output)['dry_run'])
        self.assertFalse(self.civ.with_suffix('.CIV.bak').exists())
        self.manifest.write_text('{broken', encoding='utf-8')
        code, output, error = self.cli('texture', 'import-manifest', self.civ, '--manifest', self.manifest)
        self.assertEqual((code, output), (1, ''))
        self.assertIn('ERROR:', error)

    def test_explicit_png_directory_and_bom_manifest(self):
        other = self.root / 'manifest.json'
        other.write_text(self.manifest.read_text(encoding='utf-8'), encoding='utf-8-sig')
        result = import_manifest(self.civ, other, png_dir=self.png_dir)
        self.assertEqual(result['count'], 2)

    def test_import_needs_no_qt_pillow_browser_or_personal_skill(self):
        # -S removes site-packages; a generic Python subprocess only needs this repo.
        script = 'import sys;from modgen.texture import import_manifest;import_manifest(sys.argv[1],sys.argv[2])'
        result = subprocess.run([sys.executable, '-S', '-c', script, str(self.civ), str(self.manifest)],
                                capture_output=True, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))


class TextureVerificationTest(HtmlUIFixture):
    def make_export(self):
        project = self.root / 'export'
        for folder in ('Textures', 'IMG', 'XLPs'):
            (project / folder).mkdir(parents=True)
        entries = []
        for name, size in json.loads(self.manifest.read_text()).items():
            with Image.open(self.png_dir / f'{name}.png') as image:
                image.save(project / 'Textures' / f'{name}.dds')
                image.save(project / 'IMG' / f'{name}.png')
            (project / 'Textures' / f'{name}.tex').write_text(
                f'<Texture><m_Name text="{name}"/><m_Width>{size[0]}</m_Width><m_Height>{size[1]}</m_Height>'
                f'<m_DataFiles><Element><m_ID text="DDS"/><m_RelativePath text="{name}.dds"/></Element></m_DataFiles></Texture>')
            entries.append(f'<Element><m_EntryID text="{name}"/><m_ObjectName text="{name}"/></Element>')
        (project / 'XLPs' / 'demo.xlp').write_text('<XLP><m_ClassName text="UITexture"/>'
            '<m_PackageName text="demo"/><m_Entries>' + ''.join(entries) + '</m_Entries></XLP>')
        (project / 'demo.Art.xml').write_text('<Art><Libraries><Element><libraryName text="UITexture"/>'
            '<relativePackagePaths><Element text="demo"/></relativePackagePaths></Element></Libraries></Art>')
        return project

    def test_export_chain_and_visible_pixels_and_registration_failures(self):
        project = self.make_export()
        report = html_ui.verify_textures(self.manifest, project=project)
        self.assertTrue(report['ok'])
        self.assertTrue(all(row['dds_max_visible_delta'] == 0 for row in report['textures']))
        dds = project / 'Textures/UI_BETA.dds'
        original = dds.read_bytes()
        Image.new('RGBA', (12, 8), (255, 0, 0, 255)).save(dds)
        with self.assertRaisesRegex(ValueError, 'Visible pixels/alpha differ'):
            html_ui.verify_textures(self.manifest, project=project)
        dds.write_bytes(original)
        (project / 'demo.Art.xml').unlink()
        with self.assertRaisesRegex(ValueError, 'Art.xml'):
            html_ui.verify_textures(self.manifest, project=project)

    def test_cli_verify_defaults_source_dir_and_rejects_bad_tolerance(self):
        code, output, error = self.cli('texture', 'verify', '--manifest', self.manifest)
        self.assertEqual((code, error), (0, ''))
        self.assertEqual(json.loads(output)['scope'], 'source-png')
        code, output, error = self.cli('texture', 'verify', '--manifest', self.manifest, '--tolerance', '256')
        self.assertEqual((code, output), (1, ''))
        self.assertIn('Tolerance', error)


class RuntimeDiscoveryTest(unittest.TestCase):
    def test_explicit_invalid_path_does_not_silently_fall_back(self):
        with patch.dict(os.environ, {'CIV6_UI_NODE': 'alternative-node', 'CIV6_UI_BROWSER': 'alternative-browser'}):
            with self.assertRaises(ValueError):
                html_ui.find_node('/missing/program/node-not-found')
            with self.assertRaises(ValueError):
                html_ui.find_browser('/missing/program/browser-not-found')

    def test_environment_and_cli_path_precedence(self):
        with patch.dict(os.environ, {'CIV6_UI_NODE': 'env-node', 'CIV6_UI_BROWSER': 'env-browser'}):
            with patch.object(html_ui, '_resolve_executable', side_effect=lambda value: value):
                self.assertEqual(html_ui.find_node(), 'env-node')
                self.assertEqual(html_ui.find_node('cli-node'), 'cli-node')
                self.assertEqual(html_ui.find_browser(), 'env-browser')
                self.assertEqual(html_ui.find_browser('cli-browser'), 'cli-browser')


@unittest.skipUnless(os.environ.get('CIV6_UI_BROWSER_TESTS') == '1', 'Set CIV6_UI_BROWSER_TESTS=1 to run a real local Chromium')
class RealBrowserPortabilityTest(HtmlUIFixture):
    def test_cli_render_then_detached_bundle_and_failed_overwrite(self):
        output = self.root / 'render output'
        html = html_ui.skill_root() / 'assets/starter/index.html'
        code, stdout, stderr = self.cli('texture', 'render', '--html', html, '--out', output)
        self.assertEqual((code, stderr), (0, ''))
        report = json.loads(stdout)
        self.assertEqual(report['count'], 3)
        self.assertTrue(html_ui.verify_textures(report['manifest'])['ok'])
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        code, stdout, stderr = self.cli('texture', 'render', '--html', html, '--out', output)
        self.assertEqual((code, stdout), (1, ''))
        self.assertIn('Output exists', stderr)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)
        code, stdout, stderr = self.cli('texture', 'render', '--html', html, '--out', output, '--replace')
        self.assertEqual((code, stderr), (0, ''))
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)
        # A later render failure must not replace the earlier textures in an existing batch.
        broken = self.root / 'broken.html'
        script = "const original=window.renderTexture;window.renderTexture=async name=>{if(name==='UI_DEMO_BUTTON')throw Error('intentional late failure');await original(name);document.querySelector('.panel').style.background='red';};"
        broken.write_text(html.read_text(encoding='utf-8').replace('</script>', script + '</script>'), encoding='utf-8')
        code, stdout, stderr = self.cli('texture', 'render', '--html', broken, '--out', output, '--replace')
        self.assertEqual((code, stdout), (1, ''))
        self.assertIn('intentional late failure', stderr)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)
        # Copied folder works without importing modgen or locating ~/.codex.
        detached = self.root / '共享技能'
        shutil.copytree(html_ui.skill_root(), detached, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        detached_out = self.root / 'detached-output'
        result = subprocess.run([html_ui.find_node(), str(detached / 'scripts/render-textures.cjs'),
            '--html', str(detached / 'assets/starter/index.html'), '--out', str(detached_out),
            '--browser', html_ui.find_browser()], cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        result = subprocess.run([sys.executable, str(detached / 'scripts/verify-textures.py'),
            '--manifest', str(detached_out / 'texture_manifest.json'), '--png-dir', str(detached_out)],
            cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        self.assertTrue(json.loads(result.stdout)['ok'])
        with Image.open(detached_out / 'UI_DEMO_SELECTED.png') as image:
            self.assertEqual(image.getpixel((128, 80))[3], 0)
        with Image.open(detached_out / 'UI_DEMO_BUTTON.png') as image:
            self.assertEqual(len({image.getpixel((128, 24 + n * 48)) for n in range(4)}), 4)


if __name__ == '__main__':
    unittest.main()
