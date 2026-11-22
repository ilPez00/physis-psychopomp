"""R-P1.29 — can an observer recover its own blind spot?

Prereg: docs/2026-11-22-PREREG-R-P1.29-self-model-inference.md, registered before
this script existed (claim cff544e7 registered before the run).

Two corpora of observable logs are fed to `psychopomp.selfmodel`: a full one whose
bodies cross all four edges, and a horizontal-only one whose bodies never cross
the top or bottom. The estimate is then used to predict identifiability on the
R-P1.21 task points and compared with the truth.

Usage: .venv/bin/python scripts/self-model-inference-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.law import blind_cells, on_boundary, predict_identifiable
from psychopomp.selfmodel import estimate_blind_region
from psychopomp.sim import Init, SimConfig, run

O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TRUE = blind_cells(SimConfig(o=O, o2=O2))[0]
STEP = 0.3
STEPS = 400
PARKED = (3.0, 97.0)
LANES = (36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 64.0)
COLUMNS = (47.0, 50.0, 53.0)
TASKS = ((42.0, 45.0), (46.0, 45.0), (48.0, 45.0), (52.0, 45.0))


def cfg() -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2)


def horizontal():
    eps = []
    for i, lane in enumerate(LANES):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg(), 0, episode=i, init=Init(
            x=(start, PARKED[0]), y=(lane, PARKED[1]), v=((v, 0.0), (0.0, 0.0)))))
    return eps


def vertical():
    eps = []
    for i, column in enumerate(COLUMNS):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg(), 0, episode=100 + i, init=Init(
            x=(column, PARKED[0]), y=(start, PARKED[1]), v=((0.0, v), (0.0, 0.0)))))
    return eps


def main() -> int:
    full = estimate_blind_region(horizontal() + vertical(), STEP)
    horiz = estimate_blind_region(horizontal(), STEP)

    print(f"true blind region: {TRUE}  (step {STEP})")
    print(f"full-corpus estimate: {full.as_rect()}  samples {full.samples}  "
          f"unknown {full.unknown_edges()}")
    print(f"horizontal-only estimate: x0={horiz.x0} x1={horiz.x1} "
          f"y0={horiz.y0} y1={horiz.y1}  unknown {horiz.unknown_edges()}")

    est = full.as_rect()
    p1 = est is not None and all([
        0.0 <= est[0] - TRUE[0] <= STEP,
        0.0 <= TRUE[1] - est[1] <= STEP,
        0.0 <= est[2] - TRUE[2] <= STEP,
        0.0 <= TRUE[3] - est[3] <= STEP,
    ])
    p2 = (horiz.x0 is not None and horiz.x1 is not None
          and horiz.y0 is None and horiz.y1 is None
          and 0.0 <= horiz.x0 - TRUE[0] <= STEP
          and 0.0 <= TRUE[1] - horiz.x1 <= STEP)

    pessimistic = []
    optimistic = []
    for point in TASKS:
        truth = predict_identifiable(SimConfig(o=O, o2=O2), point, 0)
        bound = on_boundary(SimConfig(o=O, o2=O2), point, 0)
        if est is None:
            continue
        claim = not (est[0] <= point[0] <= est[1] and est[2] <= point[1] <= est[3])
        if claim == truth:
            continue
        if claim is False and truth is True:
            pessimistic.append((point, bound))
        else:
            optimistic.append((point, bound))
    p3 = not pessimistic

    clear = [(p, predict_identifiable(SimConfig(o=O, o2=O2), p, 0)) for p in TASKS
             if not on_boundary(SimConfig(o=O, o2=O2), p, 0)
             and min(abs(p[0] - TRUE[0]), abs(p[0] - TRUE[1]),
                     abs(p[1] - TRUE[2]), abs(p[1] - TRUE[3])) >= 1.0]
    p4 = all(
        (not (est[0] <= p[0] <= est[1] and est[2] <= p[1] <= est[3])) == truth
        for p, truth in clear
    ) and bool(clear)

    print()
    print(f"task points (clear of edges by >= 1.0): "
          f"{[(p, t) for p, t in clear]}")
    print(f"direction of errors: optimistic {optimistic}, pessimistic {pessimistic}")
    print(f"P1 estimate within one step and contained in the truth: "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 never-crossed edges are unknown, not guessed: "
          f"{'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 no pessimistic error (estimate subset of truth): "
          f"{'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 good enough to plan with on clear points: "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
