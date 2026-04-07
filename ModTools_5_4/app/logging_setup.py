"""Logging setup helpers."""
from __future__ import annotations

import logging
from pathlib import Path
import sys


def configure_logging(log_dir: Path, debug: bool = False) -> None:
    """Configure file-only logging for the GUI process.

    Notes:
    - Intentionally does NOT attach any console/stream handler (keeps terminal silent).
    - By default logs go to a user-writable directory (e.g. %LOCALAPPDATA%/ModTools5.4/logs).
    - When running from source (not frozen), also attempts to mirror logs into the
      workspace package directory (ModTools_5_4/logs) for easier debugging.
    """

    level = logging.DEBUG if debug else logging.INFO
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    handlers: list[logging.Handler] = []

    # Primary log location (user-writable)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "modtools_5_4.log"
        h = logging.FileHandler(log_file, encoding="utf-8")
        h.setFormatter(fmt)
        handlers.append(h)
    except OSError:
        pass

    # Mirror into workspace when running from source (best-effort)
    is_frozen = bool(getattr(sys, "frozen", False))
    if not is_frozen:
        try:
            package_root = Path(__file__).resolve().parent.parent
            workspace_log_dir = package_root / "logs"
            if workspace_log_dir.resolve() != log_dir.resolve():
                workspace_log_dir.mkdir(parents=True, exist_ok=True)
                workspace_log_file = workspace_log_dir / "modtools_5_4.log"
                h2 = logging.FileHandler(workspace_log_file, encoding="utf-8")
                h2.setFormatter(fmt)
                handlers.append(h2)
        except OSError:
            pass

    root = logging.getLogger()
    for old in list(root.handlers):
        root.removeHandler(old)
    root.setLevel(level)
    for h in handlers:
        root.addHandler(h)

    logging.getLogger("asyncio").setLevel(logging.WARNING)
