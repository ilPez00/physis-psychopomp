"""The local verifier cannot turn a missing gate into a pass."""
import runpy
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify-all.py"


def test_missing_uv_fails_lockfile_gate(monkeypatch, tmp_path):
    verifier = runpy.run_path(str(SCRIPT))
    monkeypatch.setenv("PATH", str(tmp_path))
    rc, output, _ = verifier["run"](["uv", "lock", "--check"])
    assert rc != 0
    assert "uv" in output


def test_unsupported_fast_flag_does_not_start_full_run():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--fast"],
        capture_output=True, text=True, timeout=3,
    )
    assert result.returncode == 2
    assert "--fast" in result.stderr
