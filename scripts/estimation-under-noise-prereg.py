"""R-P1.35 — self-knowledge under sensor noise.

Prereg: docs/2026-11-22-PREREG-R-P1.35-estimation-under-noise.md, registered before
this script existed (claim registered before the run).

The estimator's containment ("always optimistic") was measured on exact crossings.
Here the crossings carry sensor noise. Three estimators on the same noisy logs:
the shipped min/max, a 10% quantile bound, and the quantile bound with a
spread-based abstention.

Usage: .venv/bin/python scripts/estimation-under-noise-prereg.py
"""
from __future__ import annotations

import statistics
import sys

sys.path.insert(0, ".")

from psychopomp.selfmodel import estimate_blind_region, estimate_blind_cells_auto
from psychopomp.sim import Init, SimConfig, run

O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TRUE = (46.0, 54.0, 35.0, 65.0)
STEP = 0.3
PARKED = (3.0, 97.0)
SIGMAS = (0.0, 0.1, 0.3, 1.0)
REALIZATIONS = 20
LANES = (40.0, 44.0, 48.0, 52.0, 56.0, 60.0)
COLUMNS = (47.0, 50.0, 53.0)


def corpus(noise: float, realization: int):
    eps = []
    for i, lane in enumerate(LANES):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, noise=noise), 0,
                       episode=1000 * realization + i,
                       init=Init(x=(start, PARKED[0]), y=(lane, PARKED[1]),
                                 v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate(COLUMNS):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, noise=noise), 0,
                       episode=1000 * realization + 100 + i,
                       init=Init(x=(column, PARKED[0]), y=(start, PARKED[1]),
                                 v=((0.0, v), (0.0, 0.0)))))
    return eps


def edges(est):
    rect = est.as_rect()
    if rect is None:
        return {}
    x0, x1, y0, y1 = rect
    return {"x0": x0 - TRUE[0], "x1": TRUE[1] - x1,
            "y0": y0 - TRUE[2], "y1": TRUE[3] - y1}


def pessimistic(e) -> bool:
    return any(v < -1e-9 for v in e.values())


def summarize(kind: str, sigma: float) -> dict:
    abs_errors, pens, reported, contained = [], 0, 0, 0
    for r in range(REALIZATIONS):
        eps = corpus(sigma, r)
        if kind == "shipped":
            est = estimate_blind_region(eps, STEP)
        elif kind == "robust":
            est = estimate_blind_region(eps, STEP, quantile=0.1)
        else:
            est = estimate_blind_region(eps, STEP, quantile=0.1, max_spread=2 * STEP)
        e = edges(est)
        if not e:
            continue
        reported += 1
        abs_errors.extend(abs(v) for v in e.values())
        if pessimistic(e):
            pens += 1
        if not pessimistic(e):
            contained += 1
    return {"kind": kind, "sigma": sigma, "mean_abs": statistics.mean(abs_errors) if abs_errors else None,
            "pessimistic": pens, "reported": reported, "contained": contained}


def main() -> int:
    print("| estimator | sigma | mean abs edge error | pessimistic realizations | reported |")
    print("|---|---|---|---|---|")
    rows = {}
    for kind in ("shipped", "robust", "abstaining"):
        for sigma in SIGMAS:
            row = summarize(kind, sigma)
            rows[(kind, sigma)] = row
            mean = "—" if row["mean_abs"] is None else f"{row['mean_abs']:.3f}"
            print(f"| {kind} | {sigma:.1f} | {mean} | "
                  f"{row['pessimistic']}/{row['reported']} | {row['reported']}/{REALIZATIONS} |")

    shipped = [rows[("shipped", s)] for s in SIGMAS]
    p1 = all(a["mean_abs"] <= b["mean_abs"] for a, b in zip(shipped, shipped[1:]))
    p2 = shipped[-1]["pessimistic"] >= 1 and all(
        rows[("shipped", s)]["pessimistic"] == 0 for s in SIGMAS[:2])
    p3 = rows[("robust", SIGMAS[-1])]["pessimistic"] < rows[("shipped", SIGMAS[-1])]["pessimistic"]
    abst = [rows[("abstaining", s)] for s in SIGMAS]
    p4 = all((r["reported"] == 0) or
             (r["contained"] / r["reported"] >= 0.95) for r in abst) and \
        abst[-1]["reported"] <= abst[0]["reported"]

    print()
    print(f"P1 error grows with noise: {'UPHELD' if p1 else 'FALSIFIED'} "
          f"({[None if r['mean_abs'] is None else round(r['mean_abs'], 3) for r in shipped]})")
    print(f"P2 containment breaks at high noise (first pessimistic edges): "
          f"{'UPHELD' if p2 else 'FALSIFIED'} "
          f"(pessimistic {[r['pessimistic'] for r in shipped]})")
    print(f"P3 a quantile bound is more robust than min/max at sigma=1.0: "
          f"{'UPHELD' if p3 else 'FALSIFIED'} "
          f"({rows[('robust', SIGMAS[-1])]['pessimistic']} vs {shipped[-1]['pessimistic']})")
    print(f"P4 abstention preserves containment when it reports: "
          f"{'UPHELD' if p4 else 'FALSIFIED'} "
          f"(reported {[r['reported'] for r in abst]}, contained {[r['contained'] for r in abst]})")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
