"""First-run launcher bootstrap tests (no real GUI or network)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("modtools_launcher", ROOT / "ModTools5.4.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def make_venv(root: Path) -> Path:
    python = launcher.venv_python(root)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_bytes(b"")
    return python


class LauncherBootstrapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_venv_python_path_is_windows_layout(self) -> None:
        self.assertEqual(launcher.venv_python(self.root), self.root / ".venv" / "Scripts" / "python.exe")

    def test_pyqt_available_skips_any_action(self) -> None:
        calls: list[object] = []
        launcher.ensure_environment(self.root, [], pyqt_ok=True, interactive=True,
                                    confirm=lambda *a, **k: self.fail("must not ask"),
                                    execv=lambda *a: calls.append(a))
        self.assertEqual(calls, [])

    def test_existing_venv_relaunches_with_it(self) -> None:
        python = make_venv(self.root)
        calls: list[tuple] = []
        launcher.ensure_environment(self.root, ["--headless"], pyqt_ok=False, interactive=False,
                                    execv=lambda exe, args: calls.append((exe, args)))
        self.assertEqual(len(calls), 1)
        exe, args = calls[0]
        self.assertEqual(Path(exe), python)
        self.assertEqual(Path(args[0]), python)
        self.assertIn("--headless", args)

    def test_missing_venv_non_interactive_exits_without_install(self) -> None:
        calls: list[tuple] = []
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                launcher.ensure_environment(self.root, [], pyqt_ok=False, interactive=False,
                                            setup_runner=lambda root: self.fail("must not install"),
                                            execv=lambda *a: calls.append(a))
        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(calls, [])

    def test_interactive_decline_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            launcher.ensure_environment(self.root, [], pyqt_ok=False, interactive=True,
                                        confirm=lambda *a, **k: False,
                                        execv=lambda *a: self.fail("must not relaunch"))
        self.assertEqual(ctx.exception.code, 1)

    def test_interactive_accept_installs_then_relaunches(self) -> None:
        calls: list[tuple] = []
        def fake_setup(root: Path) -> bool:
            make_venv(root)
            return True
        launcher.ensure_environment(self.root, [], pyqt_ok=False, interactive=True,
                                    confirm=lambda *a, **k: True,
                                    setup_runner=fake_setup,
                                    execv=lambda exe, args: calls.append((exe, args)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(Path(calls[0][0]), launcher.venv_python(self.root))

    def test_setup_failure_exits_with_message(self) -> None:
        messages: list[str] = []
        original = launcher.notify
        launcher.notify = lambda text, ask=False: messages.append(text) or False
        self.addCleanup(setattr, launcher, "notify", original)
        with self.assertRaises(SystemExit) as ctx:
            launcher.ensure_environment(self.root, [], pyqt_ok=False, interactive=True,
                                        confirm=lambda *a, **k: True,
                                        setup_runner=lambda root: False,
                                        execv=lambda *a: self.fail("must not relaunch"))
        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(messages)


if __name__ == "__main__":
    unittest.main()
