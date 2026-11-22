"""Research gates — every documented result, pinned against silent change.

Some scripts end in FAIL on purpose: R-P1.19's P3/P4 and R-P1.21's P3 were
falsified and stay falsified. A gate that demanded exit 0 would force someone to
"fix" an honest negative, so each gate declares the outcome the repo *documents*
and this runner fails only on **drift** — a negative turning green, a number
moving, or a positive turning red.

Usage: .venv/bin/python scripts/research-gates.py [--only NAME]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

# (script, expected exit code, a line the output must still contain, what it proves)
GATES = [
    ("scripts/law-conformance.py", 0, "law conformance: PASS",
     "the consolidated law matches attribution on a stratified random grid"),
    ("scripts/attribution-bench.py", 0, "bench: PASS",
     "counterfactual attribution: 12/12 unique, control at chance"),
    ("scripts/per-event-coverage-prereg.py", 0, "prereg run: PASS",
     "R-P1.12: 30/30 boundary-free cells, 13/30 unique exactly as predicted"),
    ("scripts/moving-observer-prereg.py", 0, "prereg run: PASS",
     "R-P1.17: time-resolved coverage, 11/11 cells, both flips"),
    ("scripts/hidden-contact-prereg.py", 1,
     "P2 every cell has the capacity it claims: FALSIFIED",
     "R-P1.20: rule holds wherever capacity passes; gravity cells lack capacity (documented negative)"),
    ("scripts/self-model-cost-prereg.py", 1,
     "P3 and can be free (discrete loss): FALSIFIED",
     "R-P1.21: wrong self-model costs 3 of 4; no error is free (documented negative)"),
    ("scripts/gravity-hidden-prereg.py", 1,
     "P4 the kicked body's coverage class is geometry-independent: FALSIFIED",
     "R-P1.23: gravity AND a hidden contact now both tested; P4 was a self-inconsistent prediction (documented negative)"),
]


def run(script: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, script], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    failures = []
    for script, want_rc, needle, purpose in GATES:
        if args.only and args.only not in script:
            continue
        rc, out = run(script)
        ok_rc = rc == want_rc
        ok_line = needle in out
        status = "OK" if (ok_rc and ok_line) else "DRIFT"
        print(f"[{status}] {script} -> exit {rc} (expected {want_rc})")
        if not ok_rc:
            print(f"         exit code changed; expected {want_rc}, got {rc}")
        if not ok_line:
            print(f"         expected line not found: {needle!r}")
            tail = "\n".join(out.strip().splitlines()[-6:])
            print("         tail:\n" + tail)
        if not (ok_rc and ok_line):
            failures.append((script, purpose))
        else:
            match = re.search(r"^(?:P\d.*|bench|law conformance|prereg run).*$", out, re.M)
            if match:
                print(f"         {match.group(0)[:110]}")

    print()
    if failures:
        print(f"research gates: DRIFT in {len(failures)}/{len(GATES)}")
        for script, purpose in failures:
            print(f"  - {script}: {purpose}")
        return 1
    print(f"research gates: PASS ({len(GATES)} gates, documented outcomes unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
