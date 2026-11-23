"""The gate. Run every check the repository has, in one command, one verdict.

This is the authoritative gate, not a convenience wrapper. GitHub Actions
refuses to start jobs on this repository — every push failed with "recent
account payments have failed", zero steps run — and the account is not going to
be fixed, so `.github/workflows/ci.yml` is manual-only and this command is what
"verified" means. It runs the same steps the workflow lists, so the two cannot
drift into disagreeing about what a green result is.

Every step is a gate that prints what it measured; the run fails loudly with the
failing step named, because "exit 0" over zero work looks exactly like success.

Usage: .venv/bin/python scripts/verify-all.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

STEPS = [
    ("lockfile", ["uv", "lock", "--check"]),
    ("tests", [PY, "-m", "pytest", "-q"]),
    ("law conformance", [PY, "scripts/law-conformance.py"]),
    ("research gates", [PY, "scripts/research-gates.py"]),
    ("prereg checklist", [PY, "scripts/prereg-checklist.py"]),
    ("repro block", [PY, "scripts/repro-table.py", "--check"]),
    ("recoverability", [PY, "scripts/recoverability.py"]),
    ("probe baseline", [PY, "scripts/probes.py"]),
    ("demo", [PY, "scripts/demo.py"]),
]


def run(cmd: list[str]) -> tuple[int, str, float]:
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    except OSError as exc:
        return 1, str(exc), time.monotonic() - started
    return proc.returncode, (proc.stdout + proc.stderr).strip(), time.monotonic() - started


def summarise(output: str) -> str:
    """The last line that says something, not a wall of text."""
    lines = [l for l in output.splitlines() if l.strip()]
    return lines[-1][:96] if lines else ""


def main() -> int:
    failures = []
    print(f"verify-all — {ROOT.name}\n")
    width = max(len(name) for name, _ in STEPS)
    for name, cmd in STEPS:
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
    argparse.ArgumentParser(description="Run all nine local verification steps.").parse_args()
    raise SystemExit(main())
