"""One command that says what this repository currently holds.

A future reader (or agent) should not have to grep seventeen preregs to learn the
state. This prints the version, the test count, the pinned-gate result, the
documented claim ledger and the falsification count — all read from the artefacts
themselves, so it cannot claim more than they say.

Usage: .venv/bin/python scripts/status.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*cmd: str) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    version = re.search(r'^version = "([^"]+)"',
                        (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    rc, out = run(sys.executable, "-m", "pytest", "-q", "--collect-only")
    tests = re.search(r"(\d+) tests collected", out)
    rc_gates, gates_out = run(sys.executable, "scripts/research-gates.py")
    gates = re.search(r"research gates: (\w+) \((\d+) gates", gates_out)

    findings = (ROOT / "docs" / "FINDINGS-2026-11-22.md").read_text()
    preregs = sorted((ROOT / "docs").glob("*PREREG*.md"))
    cards = sorted({m.group(0) for m in re.finditer(r"R-P1\.\d+", " ".join(
        p.read_text() for p in preregs))})
    # claims: every short id cited in the law or the findings page
    src = (ROOT / "docs" / "LAW.md").read_text() + findings
    claims = set(re.findall(r"`([0-9a-f]{8})`", src))
    # falsified: authoritative from the receipts, whose status says so
    receipts = list((ROOT / "research" / "loops" / "results").rglob("receipt.json"))
    falsified = sum(1 for r in receipts
                    if re.search(r'"status"\s*:\s*"[^"]*falsified', r.read_text(), re.I))

    print(f"version      {version}")
    print(f"tests        {tests.group(1) if tests else '?'} collected")
    print(f"gates        {gates.group(1) if gates else 'DRIFT'} "
          f"({gates.group(2) if gates else '?'} pinned)")
    print(f"cards        {len(cards)} preregistered R-P1 slices")
    print(f"claims       {len(claims)} short ids cited in LAW/FINDINGS")
    print(f"falsified    {falsified} of {len(receipts)} receipts record a falsified prediction")
    print(f"law          docs/LAW.md, psychopomp/law.py")
    print(f"self-model   docs/LAW.md section 'Can the observer learn its own blind "
          f"spot?', psychopomp/selfmodel.py")
    return 0 if rc_gates == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
