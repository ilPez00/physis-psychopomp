"""R-P1.73: finite-radius crossing labels, and what a sliver costs.

Frozen card: docs/2026-11-27-PREREG-R-P1.73-radius-labels.md, pushed at
`4f1ec40` before this file existed. Claim
`969e3ade-530c-4d53-9851-9cbe0e0a0c3c`.

D5's last unmeasured clause. The mask half of D5 is R-P1.70/71; this measures what
`visual_radius` does to the **labels**, using the corpus shape that gives the
estimator all four edges (two horizontal lanes, two vertical columns).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.selfmodel import estimate_blind_region
from psychopomp.sim import Init, SimConfig, run

CLAIM = "969e3ade-530c-4d53-9851-9cbe0e0a0c3c"
O = (40.0, 60.0, 35.0, 65.0)
DT = 0.1
STEPS = 400
RADII = (0.0, 0.5, 1.0, 2.0)
SEEDS = (0, 1, 2, 3, 4)
ANCHOR = (39.9, 60.1, 34.9, 65.0)      # R-P1.70's point-model estimate


def cfg_for(radius: float) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, visual_radius=radius)


def corpus(radius: float, seed: int):
    """Two horizontal lanes and two vertical columns.

    Both orientations are needed: horizontal lanes give left/right samples,
    vertical columns give bottom/top, and without either the estimator returns
    None rather than a biased rectangle (measured in R-P1.70).
    """
    cfg = cfg_for(radius)
    eps = []
    for i, lane in enumerate((45.0, 51.0)):
        start, v = ((5.0, 3.0) if i == 0 else (95.0, -3.0))
        eps.append(run(cfg, seed, episode=i,
                       init=Init(x=(start, 3.0), y=(lane, 97.0),
                                 v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((47.0, 53.0)):
        eps.append(run(cfg, seed, episode=100 + i,
                       init=Init(x=(column, 3.0), y=(3.0, 97.0),
                                 v=((0.0, 3.0), (0.0, 0.0)))))
    return eps


def corner_clip(radius: float, seed: int):
    """A single path that grazes the top-right corner.

    At radius 0 the centre enters the mask, so a crossing is emitted. At a radius
    larger than the graze depth the disc never fits inside and no crossing is
    emitted — the sliver.
    """
    cfg = cfg_for(radius)
    # a diagonal that clips the corner (60, 65) by ~1.5 units
    return run(cfg, seed, episode=7,
               init=Init(x=(35.0, 3.0), y=(40.0, 97.0), v=((1.5, 0.0), (1.5, 0.0))))


def crossings(ep) -> int:
    return sum(1 for e in ep.observable_log().events
               if e.kind in ("enter_occ", "exit_occ"))


def estimate(radius: float, seed: int):
    return estimate_blind_region(corpus(radius, seed), DT).as_rect()


def main() -> int:
    per_radius = {}
    for r in RADII:
        rects = [estimate(r, s) for s in SEEDS]
        rects = [x for x in rects if x is not None]
        mean = ([round(statistics.fmean(x[i] for x in rects), 4) for i in range(4)]
                if rects else None)
        counts = [crossings(e) for s in SEEDS for e in corpus(r, s)]
        per_radius[str(r)] = {
            "estimate": mean,
            "estimates_seen": len(rects),
            "of_seeds": len(SEEDS),
            "crossings": counts,
            "mean_crossings": statistics.fmean(counts) if counts else None,
        }

    # P1: the point model reproduces R-P1.70's rectangle.
    a = per_radius["0.0"]["estimate"]
    p1 = a is not None and all(abs(x - y) <= 0.05 for x, y in zip(a, ANCHOR))

    # P2: each edge moves inward by the radius.
    deltas = {}
    for r in RADII[1:]:
        est = per_radius[str(r)]["estimate"]
        if est is None or a is None:
            deltas[str(r)] = None
            continue
        # near edges (x0, y0) increase; far edges (x1, y1) decrease
        deltas[str(r)] = [round(est[0] - a[0], 4), round(a[1] - est[1], 4),
                          round(est[2] - a[2], 4), round(a[3] - est[3], 4)]
    p2 = all(d is not None and all(abs(v - float(r)) <= 0.35 for v in d)
             for r, d in ((r, deltas[str(r)]) for r in RADII[1:]))

    # P3: calibration is monotone across radii, so one r cannot be extrapolated.
    widths = {}
    for r in RADII:
        est = per_radius[str(r)]["estimate"]
        widths[str(r)] = round(est[1] - est[0], 4) if est else None
    vals = [widths[str(r)] for r in RADII if widths[str(r)] is not None]
    p3 = all(x >= y for x, y in zip(vals, vals[1:])) and len(vals) == len(RADII)

    # P4: a sliver costs a label.
    clip_low = crossings(corner_clip(0.0, 0))
    clip_high = crossings(corner_clip(2.0, 0))
    p4 = clip_high < clip_low

    # P5: the oracle does not move with the radius.
    oracles = {}
    for r in RADII:
        ep = corner_clip(r, 0)
        oracles[str(r)] = [(e.kind, round(e.t, 6)) for e in ep.oracle_log().events]
    p5 = len({tuple(v) for v in oracles.values()}) == 1

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )

    receipt = {
        "card": "R-P1.73", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.73-radius-labels.md",
        "command": "python3 scripts/radius-labels-prereg.py",
        "radii": list(RADII), "seeds": list(SEEDS), "anchor": list(ANCHOR),
        "per_radius": per_radius,
        "edge_deltas": deltas,
        "widths": widths,
        "corner_clip_crossings": {"r=0": clip_low, "r=2": clip_high},
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/radius-labels-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "estimates": {k: v["estimate"] for k, v in per_radius.items()},
                      "edge_deltas": deltas, "widths": widths,
                      "corner_clip": receipt["corner_clip_crossings"]}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
