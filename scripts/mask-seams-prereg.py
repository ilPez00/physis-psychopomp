"""R-P1.70: do non-rectangular masks change the attribution verdict?

Frozen card: docs/2026-11-27-PREREG-R-P1.70-mask-seams.md at `1a2c0c3`, amended
before any run (Amendment 1): the simulator already carries `extra_o` (unions,
R-P1.20/23), `poly_o` (convex polygons, R-P1.45) and `visual_radius` with a
fully-hidden disc rule (R-P1.44). R-P1.45 measured **visibility only**; this card
asks what a non-rectangular mask does to the **verdict**.

Arms, each varying one thing from the control:

  A  single rectangle, point model            (anchor: must reproduce the tie)
  B  union of two rectangles (`extra_o`)      (composite seam)
  C  L-shaped polygon (`poly_o`)              (reflex corner — the open seam)
  D  A's geometry with visual_radius = 1.0    (finite radius, edge estimate)
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.selfmodel import estimate_blind_region
from psychopomp.sim import Init, Kick, SimConfig, observable, run

CLAIM = "4504c1af-eb53-4caf-94f3-1ea5a462c726"
HIDDEN_KICK = Intervention(t=60, ball=0, dv=(0.0, 1.5))
INIT = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
SEEDS = (0, 1, 2, 3, 4)
STEPS = 400   # the vertical columns need to clear the mask top
DT = 0.1

# Control: R-P1.9's single occluder. The event at t=60 is at (46.0, 45.0).
O = (40.0, 60.0, 35.0, 65.0)
# Composite: the same covered area split into two overlapping rectangles.
O_A = (40.0, 52.0, 35.0, 65.0)
O_B = (48.0, 60.0, 35.0, 65.0)
# Reflex: an L whose notch is cut out of the upper-left, so an event in the
# notch is visible through the opening while the mask's area still surrounds it.
L_POLY = ((40.0, 35.0), (60.0, 35.0), (60.0, 65.0), (52.0, 65.0),
          (52.0, 50.0), (40.0, 50.0))


def event_location() -> tuple[float, float]:
    return (INIT.x[0] + INIT.v[0][0] * HIDDEN_KICK.t * DT,
            INIT.y[0] + INIT.v[0][1] * HIDDEN_KICK.t * DT)


def build(arm: str) -> SimConfig:
    if arm == "A":
        return SimConfig(steps=STEPS, o=O)
    if arm == "B":
        return SimConfig(steps=STEPS, o=O_A, extra_o=(O_B,))
    if arm == "C":
        return SimConfig(steps=STEPS, o=O, poly_o=(L_POLY,))
    if arm == "D":
        return SimConfig(steps=STEPS, o=O, visual_radius=1.0)
    raise ValueError(arm)


def area_of(arm: str) -> float:
    def rect(r):
        return (r[1] - r[0]) * (r[3] - r[2])
    if arm == "A":
        return rect(O)
    if arm == "B":
        inter_w = min(O_A[1], O_B[1]) - max(O_A[0], O_B[0])
        inter_h = min(O_A[3], O_B[3]) - max(O_A[2], O_B[2])
        return rect(O_A) + rect(O_B) - max(0.0, inter_w) * max(0.0, inter_h)
    if arm == "C":
        # shoelace over the L polygon
        pts = L_POLY
        s = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            s += x1 * y2 - x2 * y1
        return abs(s) / 2.0
    if arm == "D":
        # disc rule erodes each side by r; reported so "same mask, different
        # effective area" is visible rather than implied
        r = 1.0
        return max(0.0, (O[1] - O[0] - 2 * r)) * max(0.0, (O[3] - O[2] - 2 * r))
    raise ValueError(arm)


def cell(arm: str, seed: int) -> dict:
    cfg = build(arm)
    px, py = event_location()
    ep = run(cfg, seed, init=INIT,
             kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
    out = attribute(ep, [HIDDEN_KICK, None], cfg, seed, INIT)
    est = estimate_blind_region(corpus(arm, seed), DT).as_rect()
    return {
        "arm": arm, "seed": seed,
        "event": [round(px, 4), round(py, 4)],
        "visible_at_event": bool(observable(cfg, px, py)),
        "unique": bool(out["unique"]),
        "ambiguity": len(out["ambiguity"]),
        "margin": out["margin"],
        "estimate": [round(v, 4) for v in est] if est else None,
    }


def corpus(arm: str, seed: int):
    """Two lanes, so the estimator sees a vertical extent.

    A single pair only produces `enter_occ`/`exit_occ` on one horizontal line, so
    `_rect_bounds` gets zero bottom/top samples and `as_rect()` returns None —
    measured before this fix, and the reason every geometry prediction read FAILED
    against a missing estimate rather than against a moved one.
    """
    cfg = build(arm)
    eps = []
    # Horizontal lanes give left/right samples; vertical columns give bottom/top.
    # With only horizontal ones the estimator has zero vertical evidence and
    # `as_rect()` returns None — measured, and the reason the first two attempts
    # produced no estimate at all rather than a wrong one.
    for i, lane in enumerate((45.0, 51.0)):
        start, v = ((5.0, 3.0) if i == 0 else (95.0, -3.0))
        eps.append(run(cfg, seed, episode=i,
                       init=Init(x=(start, 3.0), y=(lane, 97.0),
                                 v=((v, 0.0), (0.0, 0.0)))))
    # Two columns, each crossing one vertical edge: one enters from below
    # (bottom sample), one starts below the mask and exits upward only if it
    # begins outside — so the third starts *inside* the vertical span and exits
    # at the top, which is what produces the `top` sample the estimator needs.
    for i, (column, start, v) in enumerate(((47.0, 3.0, 3.0), (53.0, 3.0, 3.0))):
        eps.append(run(cfg, seed, episode=100 + i,
                       init=Init(x=(column, 3.0), y=(start, 97.0),
                                 v=((0.0, v), (0.0, 0.0)))))
    return eps


def arm_summary(arm: str) -> dict:
    cells = [cell(arm, s) for s in SEEDS]
    ests = [c["estimate"] for c in cells if c["estimate"]]
    return {
        "cells": cells,
        "unique": [c["unique"] for c in cells],
        "visible": [c["visible_at_event"] for c in cells],
        "area": round(area_of(arm), 3),
        "estimate": ([round(statistics.fmean(e[i] for e in ests), 4)
                      for i in range(4)] if len(ests) == len(cells) else None),
        "margins": [c["margin"] for c in cells],
    }


def main() -> int:
    summaries = {arm: arm_summary(arm) for arm in ("A", "B", "C", "D")}

    # P1: the anchor reproduces the single-observer tie on 5/5 seeds.
    p1 = all(not u for u in summaries["A"]["unique"]) and \
         all(c["ambiguity"] == 2 for c in summaries["A"]["cells"])

    # P2: the composite mask changes the inferred geometry, not the verdict.
    a_est, b_est = summaries["A"]["estimate"], summaries["B"]["estimate"]
    geometry_moved = (a_est is not None and b_est is not None
                      and any(abs(x - y) > 1e-6 for x, y in zip(a_est, b_est)))
    verdict_same = summaries["A"]["unique"] == summaries["B"]["unique"]
    p2 = geometry_moved and verdict_same

    # P3 (load-bearing): the reflex notch changes the verdict.
    p3 = summaries["C"]["unique"] != summaries["A"]["unique"]

    # P4: finite radius moves the edge estimate by the radius.
    d_est, a_est2 = summaries["D"]["estimate"], summaries["A"]["estimate"]
    if d_est is None or a_est2 is None:
        p4 = False
        shift = None
    else:
        # near edge upper bounds shrink by r, far lower bounds grow by r
        shift = [round(d_est[0] - a_est2[0], 4), round(a_est2[1] - d_est[1], 4),
                 round(d_est[2] - a_est2[2], 4), round(a_est2[3] - d_est[3], 4)]
        p4 = all(abs(s - 1.0) <= 0.25 for s in shift)

    # P5: no arm touches the oracle.
    oracles = {}
    for arm in ("A", "B", "C", "D"):
        cfg = build(arm)
        ep = run(cfg, 0, init=INIT,
                 kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
        oracles[arm] = [(e.kind, round(e.t, 9)) for e in ep.oracle_log().events]
    p5 = len({tuple(v) for v in oracles.values()}) == 1

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )

    receipt = {
        "card": "R-P1.70", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.70-mask-seams.md",
        "amendment": "Amendment 1: the simulator already carries extra_o/poly_o/"
                     "visual_radius; R-P1.45 measured visibility, not attribution",
        "command": "python3 scripts/mask-seams-prereg.py",
        "event": list(event_location()),
        "seeds": list(SEEDS),
        "arms": {arm: {k: v for k, v in summaries[arm].items() if k != "cells"}
                 for arm in summaries},
        "cells": {arm: summaries[arm]["cells"] for arm in summaries},
        "geometry_moved_B_vs_A": geometry_moved,
        "radius_shift": shift,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/mask-seams-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "A": {"unique": summaries["A"]["unique"],
                            "visible": summaries["A"]["visible"],
                            "area": summaries["A"]["area"]},
                      "B": {"unique": summaries["B"]["unique"],
                            "visible": summaries["B"]["visible"],
                            "area": summaries["B"]["area"]},
                      "C": {"unique": summaries["C"]["unique"],
                            "visible": summaries["C"]["visible"],
                            "area": summaries["C"]["area"]},
                      "D": {"unique": summaries["D"]["unique"],
                            "visible": summaries["D"]["visible"],
                            "area": summaries["D"]["area"]},
                      "radius_shift": shift}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
