"""Run a frozen four-cell experiment; optionally keep one case in Physis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.occluded_evidence import acquire, calibrate, decide, plan
from psychopomp.verify_occluded_evidence import verify


def write(path, record):
    with path.open("x") as file:
        json.dump(record, file, indent=2, sort_keys=True)
        file.write("\n")


def run_cell(path, case, layout, truth, policy, physis=None):
    path.mkdir()
    c = calibrate(case, layout, truth)
    p = plan(c, policy)
    write(path / "calibration.json", c)
    write(path / "commitment.json", p)
    anchors = physis.before(c, p) if physis else None
    o = acquire(p, truth)
    write(path / "acquisition.json", o)
    d = decide(p, o)
    write(path / "decision.json", d)
    records = [json.loads((path / name).read_text())
               for name in ("calibration.json", "commitment.json", "acquisition.json", "decision.json")]
    resolved = verify(*records)
    if physis:
        write(path / "physis.json", physis.after(anchors, o, d, resolved))
    return {"case": case, "expected_law": truth, "verified_law": resolved,
            "probes": int(o is not None)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory, never overwritten")
    parser.add_argument("--physis", type=Path, help="local Physis binary for a disposable round-trip")
    args = parser.parse_args()
    out = args.output.resolve()
    try:
        out.mkdir()
    except FileExistsError:
        parser.error(f"output exists: {out}")

    cells = (("left", -1), ("left", 1), ("right", -1), ("right", 1))
    rng = Random(4)
    arms = {}
    for arm in ("adaptive", "passive", "left", "right", "random"):
        rows = []
        for i, (layout, truth) in enumerate(cells, 1):
            case = f"{arm}-{i}"
            policy = rng.choice(("left", "right")) if arm == "random" else arm
            rows.append(run_cell(out / case, case, layout, truth, policy))
        arms[arm] = {
            "verified": sum(row["verified_law"] == row["expected_law"] for row in rows),
            "false_resolutions": sum(row["verified_law"] is not None
                                     and row["verified_law"] != row["expected_law"] for row in rows),
            "abstentions": sum(row["verified_law"] is None for row in rows),
            "probes": sum(row["probes"] for row in rows),
            "cells": rows,
        }
    expected = {"adaptive": 4, "passive": 0, "left": 2, "right": 2, "random": 2}
    ok = all(arms[arm]["verified"] == n and arms[arm]["false_resolutions"] == 0
             for arm, n in expected.items())
    report = {"scope": "four frozen deterministic simulator cells", "verdict": "PASS" if ok else "FAIL",
              "random_seed": 4, "random_expected_verified": 2, "arms": arms}
    if args.physis and ok:
        from psychopomp.occluded_physis import Physis
        report["physis_case"] = run_cell(out / "physis-case", "physis-case", "right", 1,
                                         "adaptive", Physis(args.physis.resolve(strict=True), out))
        if report["physis_case"]["verified_law"] != 1:
            report["verdict"] = "FAIL"
    write(out / "comparison.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
