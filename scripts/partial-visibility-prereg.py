"""R-P1.44 — partial visibility: where the centre-based law stops being exact.

Prereg: docs/2026-11-23-PREREG-R-P1.44-partial-visibility.md, claim f142a2b6
registered before the run.

With a body radius r, a body is fully hidden only when its whole disc is inside a
blocker, so the effective blind region shrinks by r on every edge. The law keeps its
centre-based predicate; the band where the two disagree is what this card measures.

Usage: .venv/bin/python scripts/partial-visibility-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import predict_identifiable
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TRUE_BLIND = (46.0, 54.0, 35.0, 65.0)
T_STAR, DT = 90, 0.1
RADII = (0.0, 0.5, 1.0)
POINTS = (("deep", 50.0), ("band-inside", 53.7), ("band-outside", 54.3), ("far", 60.0))
LANE = 45.0
PARKED = (3.0, 97.0)


def measured(x: float, r: float) -> bool:
    start = 5.0
    speed = (x - start) / (DT * T_STAR)
    cfg = SimConfig(steps=200, o=O, o2=O2, visual_radius=r)
    init = Init(x=(start, PARKED[0]), y=(LANE, PARKED[1]),
                v=((speed, 0.0), (0.0, 0.0)))
    at = run(cfg, 0, episode=0, init=init).trajs[0]
    assert abs(at.x[T_STAR] - x) < 1e-6, (at.x[T_STAR], x)
    true = Intervention(t=T_STAR, ball=0, dv=(0.0, 1.5))
    ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(T_STAR, 0, (0.0, 1.5)),))
    out = attribute(ep, [true, None], cfg, 0, init)
    return bool(out["unique"] and out["best"] is true)


def law_says(x: float) -> bool:
    """Centre-based predicate, blind region as the law sees it."""
    return predict_identifiable(SimConfig(steps=200, o=O, o2=O2), (x, LANE), T_STAR)


def shrunk_says(x: float, r: float) -> bool:
    """The repaired definition: blind only if the whole disc is inside."""
    blind = (TRUE_BLIND[0] + r, TRUE_BLIND[1] - r, TRUE_BLIND[2] + r, TRUE_BLIND[3] - r)
    if blind[0] >= blind[1] or blind[2] >= blind[3]:
        return True
    return not inside_rect(blind, x, LANE)


def main() -> int:
    rows = {}
    print("| r | point | law says | shrunk says | measured | law wrong? |")
    print("|---|---|---|---|---|---|")
    for r in RADII:
        for label, x in POINTS:
            law = law_says(x)
            shrunk = shrunk_says(x, r)
            meas = measured(x, r)
            rows[(r, label)] = {"law": law, "shrunk": shrunk, "measured": meas,
                                "mispredicted": law != meas}
            print(f"| {r} | {label} ({x}) | {'unique' if law else 'tie'} | "
                  f"{'unique' if shrunk else 'tie'} | {'unique' if meas else 'tie'} | "
                  f"{'YES' if law != meas else 'no'} |")

    v1 = rows[(0.5, "band-inside")]["law"] is False and rows[(0.5, "band-inside")]["measured"] is True
    v2 = (rows[(0.5, "deep")]["law"] == rows[(0.5, "deep")]["measured"] and
          rows[(0.5, "band-outside")]["law"] == rows[(0.5, "band-outside")]["measured"] and
          rows[(0.5, "far")]["law"] == rows[(0.5, "far")]["measured"])
    counts = {r: sum(1 for label, _ in POINTS if rows[(r, label)]["mispredicted"])
              for r in RADII}
    v3 = counts[0.0] == 0 and counts[0.5] <= counts[1.0] and counts[0.5] >= 1
    v4 = all(rows[(r, label)]["shrunk"] == rows[(r, label)]["measured"]
             for r in RADII for label, _ in POINTS)

    print()
    print(f"mispredictions by r: {counts}")
    print(f"V1 the band exists at r=0.5 (law blind, instrument sees it): "
          f"{'UPHELD' if v1 else 'FALSIFIED'}")
    print(f"V2 outside the band the law is exact: {'UPHELD' if v2 else 'FALSIFIED'}")
    print(f"V3 the band scales with r and is empty at r=0: "
          f"{'UPHELD' if v3 else 'FALSIFIED'}")
    print(f"V4 shrinking the blind region by r repairs it exactly: "
          f"{'UPHELD' if v4 else 'FALSIFIED'}")
    ok = all((v1, v2, v3, v4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
