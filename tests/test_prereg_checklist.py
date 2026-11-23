"""A stray hash or receipt UUID is not a preregistered claim."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prereg-checklist.py"
CLAIM = "e1811bf2-f261-4a86-bc7e-ada56a6f1f86"


@pytest.mark.parametrize(("name", "text", "expected"), [
    ("2026-11-23-PREREG-new.md", f"Claim `{CLAIM}`\n\n## Results\n", 0),
    ("2026-11-23-PREREG-new.md", "Base `90593f31`.\n", 1),
    ("2026-11-23-PREREG-new.md", f"## Results\n\nClaim `{CLAIM}`.\n", 1),
    ("PREREG-undated.md", f"Claim `{CLAIM}`.\n", 1),
])
def test_new_prereg_requires_dated_file_and_preamble_claim(tmp_path, name, text, expected):
    scripts, docs = tmp_path / "scripts", tmp_path / "docs"
    scripts.mkdir()
    docs.mkdir()
    script = shutil.copy(SCRIPT, scripts)
    (docs / name).write_text(text)
    outcome = subprocess.run([sys.executable, script], capture_output=True, text=True)
    assert outcome.returncode == expected, outcome.stdout + outcome.stderr
