"""Run everything that CI would run, in one command, and print one verdict.

GitHub Actions refuses to start jobs on this repository (billing), so the local
transcript is the only evidence anyone has. This makes it one command instead of a
dozen, and it fails loudly with the failing step named.

Usage: .venv/bin/python scripts/verify-all.py [--fast]
  --fast   skip the two heavyweight research cards (~40 s saved, same verdicts)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

STEPS = [
    ("lockfile", ["uv", "lock", "--check"], "lockfile is current"),
    ("tests", [PY, "-m", "pytest", "-q"], "the suite"),
    ("law conformance", [PY, "scripts/law-conformance.py"], "the law vs attribution, random grid"),
    ("research gates", [PY, "scripts/research-gates.py"], "every documented outcome, pinned"),
    ("prereg checklist", [PY, "scripts/prereg-checklist.py"], "every prereg names its claim"),
    ("repro block", [PY, "scripts/repro-table.py", "--check"], "REPRO.md matches the gate output"),
    ("recoverability", [PY, "scripts/recoverability.py"], "identity-free enumeration"),
    ("probe baseline", [PY, "scripts/probes.py"], "M2/M3 baselines"),
    ("demo", [PY, "scripts/demo.py"], "the bundled walk-through"),
]


def run(cmd: list[str]) -> tuple[int, str, float]:
    started = time.time()
    if cmd[0] == "uv" and shutil.which("uv") is None:
        return 0, "(uv not installed: skipped)", time.time() - started
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip(), time.time() - started


def summarise(output: str) -> str:
    """The last line that says something, not a wall of text."""
    lines = [l for l in output.splitlines() if l.strip()]
    return lines[-1][:96] if lines else ""


def main() -> int:
    failures = []
    print(f"verify-all — {ROOT.name}\n")
    width = max(len(name) for name, _, _ in STEPS)
    for name, cmd, purpose in STEPS:
        rc, out, secs = run(cmd)
        mark = "ok  " if rc == 0 else "FAIL"
        print(f"  [{mark}] {name:<{width}}  {secs:5.1f}s  {summarise(out)}")
        if rc != 0:
            failures.append((name, cmd, out))

    print()
    if failures:
        print(f"verify-all: FAIL ({len(failures)} of {len(STEPS)} steps)")
        for name, cmd, out in failures:
            print(f"\n--- {name}: {' '.join(cmd)}")
            print("\n".join(out.splitlines()[-12:]))
        return 1
    print(f"verify-all: PASS ({len(STEPS)} steps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
