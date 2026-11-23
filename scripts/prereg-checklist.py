"""Check dated preregs declare a full claim UUID in the preamble.

This checks file structure, not when the claim was registered or measured.
Commit and push the frozen prereg before running its experiment.

Usage: .venv/bin/python scripts/prereg-checklist.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SHORT_ID = re.compile(r"\b[0-9a-f]{8}\b")
CLAIM = re.compile(rf"\b[Cc]laim +`{UUID.pattern}`")
SECTION = re.compile(r"^#{2,6}[ \t]", re.MULTILINE)

# Enforced from this date. Everything registered before it is a dated record:
# several cards registered a claim in the store but did not write the id into the
# prereg file, and back-filling would edit the record rather than fix the process.
ENFORCED_FROM = "2026-11-23"
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def main() -> int:
    preregs = sorted(p for p in DOCS.glob("*PREREG*.md"))
    if not preregs:
        print("no preregistration files found")
        return 1
    missing, listed = [], []
    for path in preregs:
        text = path.read_text()
        stamp = DATE.match(path.name)
        if stamp is None:
            missing.append(f"{path.name}: expected a YYYY-MM-DD prefix")
        elif stamp.group(1) < ENFORCED_FROM:
            if not (UUID.search(text) or SHORT_ID.search(text)):
                listed.append(path.name)
        elif not CLAIM.search(SECTION.split(text, maxsplit=1)[0]):
            missing.append(f"{path.name}: expected Claim `full-uuid` before the first section")

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
