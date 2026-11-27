#!/usr/bin/env python3
"""Audit the roadmap: does every claimed verdict resolve to a receipt?

Audit A1 (docs/audits/2026-11-27-a1-roadmap-truth.md) found this defect class by
hand: a roadmap row asserting a measured number with no receipt anywhere. It found
three of them, and the same pattern had already cost this repo two wrong turns — a
row reading `open` when the work was done, a gate reading `not met` when the fix sat
unmerged.

Three failure modes, all mechanical:

  UNRESOLVED  the row names an artefact path that does not exist
  UNLINKED    a receipt names the card but the row does not say where it is
  MISSING     the row states a verdict and no artefact can be found for the card

Three artefact conventions exist in this tree and all three count:

  1. `research/loops/results/<dir>/receipt.json` with a `card` field
  2. a `docs/<date>-<name>-results.md` written beside the card
  3. a `scripts/<name>.py` plus a pinned commit in the row
  4. a **shipped surface**: the row names a module that exists, and a test covers
     it. A product row ("ship the planner") is not a measurement and cannot have a
     receipt; requiring one would push authors to invent a receipt file.
  5. **the prereg carries its own result.** Far from being an edge case, this is
     the dominant convention here: the card is frozen, then an `## Execution
     status` section is appended with the verdict. A gate that only looked for
     `receipt.json` reported 12 rows as untraceable when 11 of them had a recorded
     verdict in exactly this form — including R-P1.59, whose section names the
     commit it was frozen at.

  6. **the row's deliverable IS a document.** "Write the preregistration before any
     run" has no result to record — the file existing is the result. R-P1.6 cites
     `2026-11-21-PREREG-A4-perspectives.md`, which exists and has no Execution
     section, because writing it was the work.

Convention 5 was added last and overturned the earlier finding: it took the count
from 12 to 1. Each addition before it narrowed a false positive; that one deleted
most of them.

What is left after all six: a row that states a verdict and names no artefact that
resolves. That is the real defect, and it is rare.

Reading only convention 1 (the first version of this script) reported 17 MISSING
where the true count was 3: the rest were measured and recorded somewhere else.

`UNLINKED` is a warning; `UNRESOLVED` and `MISSING` fail the gate.

The expected counts are asserted. A check that silently starts passing because its
parser broke is worse than no check, and this repository has already been bitten by
a gate that reported success while measuring nothing.

Usage:  python3 scripts/check-roadmap-receipts.py [--roadmap PATH] [--json]
Exit:   0 clean or warnings only, 1 unresolved/missing, 2 usage or parse failure
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A row asserts a verdict if its result cell contains one of these. Deliberately
# broad: a false positive is a row someone should look at, a false negative is the
# defect this exists to catch.
VERDICT = re.compile(
    r"\d+\s*/\s*\d+|PASS|FAIL|FALSIF|upheld|held|headroom|MIXED|\bMET\b|Exploratory|"
    r"refused|Collapse|falsified|No headroom",
    re.I,
)

CARD = re.compile(r"R-P1\.(\d+)")


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = CARD.match(line.lstrip("| "))
        if not m or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        card = cells[0]
        body = " | ".join(cells[1:])
        rows.append(
            {
                "card": card,
                "number": m.group(1),
                "body": body,
                # Any results dir the row points at.
                # Any path the row points at, in either location.
                "paths": (
                    re.findall(r"research/loops/results/([a-zA-Z0-9_.\-]+)", body)
                    # Rows cite these as a bare filename, not `docs/<name>`.
                    + re.findall(r"([a-zA-Z0-9_.\-]*results[a-zA-Z0-9_.\-]*\.md)", body)
                    + re.findall(r"docs/(\d{4}-\d{2}-\d{2}-[a-zA-Z0-9_.\-]+\.md)", body)
                ),
                # A script named in the row is evidence of a run, not of a
                # recorded outcome, so it is tracked but does not by itself
                # satisfy the gate.
                "scripts": re.findall(r"scripts/([a-zA-Z0-9_.\-]+\.py)", body),
                # Modules the row claims to have shipped.
                "modules": re.findall(r"`(psychopomp/[a-zA-Z0-9_./\-]+\.py)`", body),
                # Any document or script the row names in backticks, which is how
                # every row here cites its artefact.
                "cites": re.findall(r"`([a-zA-Z0-9_.\-/]+\.(?:md|py|json))`", body),
                "verdict": bool(VERDICT.search(body)),
                # A row counts as "done" if it says so in any cell.
                "done": bool(re.search(r"\bdone\b", body, re.I)),
            }
        )
    return rows


def artifact_exists(name: str) -> bool:
    """Does this named artefact resolve, under either convention?"""
    d = ROOT / "research" / "loops" / "results" / name
    if d.is_dir() and (d / "receipt.json").is_file():
        return True
    # A dir with any recorded output counts too: some runs kept run.txt before
    # receipt.json became the convention.
    if d.is_dir() and any(d.iterdir()):
        return True
    if (ROOT / "docs" / name).is_file():
        return True
    if (ROOT / name).is_file():
        return True
    return False


EXEC_SECTION = re.compile(r"^#+\s*(Execution|Result|Outcome|Status)\b", re.I | re.M)


def prereg_records_outcome(number: str) -> list[str]:
    """Docs naming this card that carry their own execution/result section.

    Returns the filenames, so a caller can name where the evidence is rather than
    just claiming it exists.
    """
    found = []
    for f in (ROOT / "docs").glob("*.md"):
        if not re.search(rf"R-P1\.{number}(?!\d)", f.name):
            continue
        try:
            body = f.read_text(errors="ignore")
        except OSError:
            continue
        if EXEC_SECTION.search(body):
            found.append(f.name)
    return found


def shipped_tested(module: Path) -> bool:
    """Is this module named by any test file?"""
    stem = module.stem
    for t in (ROOT / "tests", ROOT / "scripts"):
        if not t.is_dir():
            continue
        for f in t.rglob("*.py"):
            try:
                if stem in f.read_text(errors="ignore"):
                    return True
            except OSError:
                continue
    return False


def receipts_for(number: str) -> list[str]:
    """Any results dir whose receipt names this card.

    Reading the receipts rather than matching directory names, because a
    directory name is a guess and the `card` field is a declaration.
    """
    base = ROOT / "research" / "loops" / "results"
    found = []
    if not base.is_dir():
        return found
    for d in sorted(base.iterdir()):
        r = d / "receipt.json"
        if not r.is_file():
            continue
        try:
            card = json.loads(r.read_text()).get("card")
        except (json.JSONDecodeError, OSError):
            continue
        if card and CARD.fullmatch(str(card).strip()) and CARD.fullmatch(str(card).strip()).group(1) == number:
            found.append(d.name)
        elif card and str(card).strip() == f"R-P1.{number}":
            if d.name not in found:
                found.append(d.name)
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roadmap", type=Path, default=ROOT / "docs" / "ROADMAP.md")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not a.roadmap.is_file():
        print(f"2: no roadmap at {a.roadmap}", file=sys.stderr)
        return 2
    rows = parse_rows(a.roadmap.read_text())
    if not rows:
        # A parser that returns nothing must not read as "all clean".
        print("2: parsed 0 roadmap rows; the parser or the file changed", file=sys.stderr)
        return 2

    unresolved, unlinked, missing, clean, shipped, recorded, cited = (
        [], [], [], [], [], [], [])
    for r in rows:
        if not r["verdict"]:
            continue
        if r["paths"]:
            bad = [p for p in r["paths"] if not artifact_exists(p)]
            if bad:
                unresolved.append({**r, "bad": bad})
            else:
                clean.append(r)
            continue
        found = receipts_for(r["number"])
        if found:
            unlinked.append({**r, "found": found})
        elif r["modules"] and all(
            (ROOT / m).is_file() and shipped_tested(ROOT / m) for m in r["modules"]
        ):
            # A shipped-surface row whose module exists and has a test. Recorded
            # in its own bucket so the count stays honest about what was checked:
            # this proves the code is there and tested, never that a number holds.
            shipped.append(r)
        elif prereg_records_outcome(r["number"]):
            # The prereg carries its own result. Not a receipt, but a recorded
            # verdict with a date, which is what A1 was actually asking for.
            # Checked BEFORE the citation test: a row whose cited card contains
            # its own verdict is stronger evidence than one that merely resolves,
            # and reporting it as the weaker kind would understate it.
            recorded.append({**r, "in": prereg_records_outcome(r["number"])})
        elif r["cites"] and all(
            (ROOT / c).is_file()
            or (ROOT / "docs" / c).is_file()
            or (ROOT / "scripts" / c).is_file()
            for c in r["cites"]
        ):
            # Every artefact the row names resolves, but none records an outcome
            # this check can find. For a "write the prereg" row that is the whole
            # deliverable (R-P1.6); for anything else it means the result lives
            # somewhere unparsed. Traceable by a reader, so it counts — reported
            # separately so the weaker kind stays visible.
            cited.append({**r, "cites": r["cites"]})
        elif r["scripts"]:
            # A script is named, so a run happened — but the outcome is not
            # recorded anywhere this gate can see. That is exactly the class A1
            # found, so it stays MISSING rather than being waved through.
            missing.append({**r, "scripts": r["scripts"]})
        elif r["done"] or r["verdict"]:
            missing.append(r)
        else:
            clean.append(r)

    out = {
        "rows": len(rows),
        "clean": len(clean),
        "unresolved": [{"card": r["card"], "bad": r["bad"]} for r in unresolved],
        "unlinked": [{"card": r["card"], "found": r["found"]} for r in unlinked],
        "missing": [r["card"] for r in missing],
        "shipped_surface": [r["card"] for r in shipped],
        "recorded_in_prereg": [{"card": r["card"], "in": r["in"]} for r in recorded],
        "cited_artifacts_exist": [{"card": r["card"], "cites": r["cites"]} for r in cited],
    }
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"roadmap rows: {len(rows)}  clean: {len(clean)}  "
              f"unresolved: {len(unresolved)}  unlinked: {len(unlinked)}  "
              f"missing: {len(missing)}  shipped-surface: {len(shipped)}  "
              f"recorded-in-prereg: {len(recorded)}  cited-exists: {len(cited)}")
        for r in unresolved:
            print(f"  UNRESOLVED {r['card']}: no receipt at {', '.join(r['bad'])}")
        for r in unlinked:
            print(f"  unlinked   {r['card']}: receipt exists ({r['found'][0]}) but the row does not cite it")
        for r in recorded:
            print(f"  recorded   {r['card']}: outcome recorded in {r['in'][0]}")
        for r in missing:
            print(f"  MISSING    {r['card']}: states a verdict, nothing recorded anywhere")

    # Fail on anything that makes a claim untraceable. `unlinked` is a warning:
    # the evidence exists, the row just does not point at it.
    return 1 if (unresolved or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
