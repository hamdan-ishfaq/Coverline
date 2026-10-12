"""Import-linter gates the TRD Section 3 dependency rules (also run in CI).

A real run fails loudly the day someone violates the contracts, e.g. `engine`
importing `agent` — that is the negative check from PLAN M0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_import_linter_passes() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "import_linter.cli"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr