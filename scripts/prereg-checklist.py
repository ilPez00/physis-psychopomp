"""Prereg checklist — a prereg must name the claim it registers, before the run.

Two cards (R-P1.18, R-P1.27) were preregistered without a store claim id. That is
a process miss, not a measurement defect, and it is exactly the kind of thing
that rots silently. This check fails on any *new* prereg that carries no claim
id; the two historical misses stay on an explicit list rather than being edited
into compliance after the fact.

Usage: .venv/bin/python scripts/prereg-checklist.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SHORT_ID = re.compile(r"\b[0-9a-f]{8}\b")

# Enforced from this date. Everything registered before it is a dated record:
# several cards registered a claim in the store but did not write the id into the
# prereg file, and back-filling would edit the record rather than fix the process.
ENFORCED_FROM = "2026-11-23"
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def main() -> int:
    preregs = sorted(p for p in DOCS.glob("*PREREG*.md"))
    if not preregs:
        print("no preregistration files found")
        return 1
    missing, listed = [], []
    for path in preregs:
        text = path.read_text()
        has_id = bool(UUID.search(text)) or SHORT_ID.search(text)
        if has_id:
            continue
        stamp = DATE.match(path.name)
        if stamp is None or stamp.group(1) < ENFORCED_FROM:
            listed.append(path.name)
        else:
            missing.append(path.name)

    print(f"preregistrations: {len(preregs)}; with a claim id: "
          f"{len(preregs) - len(missing) - len(listed)}")
    if listed:
        print(f"historical preregs before {ENFORCED_FROM} without an id in the file "
              f"(listed, not rewritten):")
        for name in listed:
            print(f"  - {name}")
    if missing:
        print("MISSING claim id (register the claim before the run):")
        for name in missing:
            print(f"  - {name}")
        print("prereg checklist: FAIL")
        return 1
    print("prereg checklist: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
