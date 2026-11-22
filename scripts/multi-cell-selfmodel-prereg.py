"""R-P1.31 — multi-cell self-models and the structural prior.

Prereg: docs/2026-11-22-PREREG-R-P1.31-multi-cell-selfmodel.md, registered before
this script existed (claim registered before the run).

Two blind cells (an L-band plus an island) with a gap between them. The estimator
recovers each cell given the right count; the same evidence with the wrong count
produces a structural-prior error whose planning cost is measured.

Usage: .venv/bin/python scripts/multi-cell-selfmodel-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_cells
from psychopomp.selfmodel import estimate_blind_cells
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

T_STAR, DT, STEPS = 90, 0.1, 200
O = (40.0, 60.0, 35.0, 65.0)
EXTRA = (70.0, 78.0, 35.0, 65.0)
O2 = (44.0, 84.0, 20.0, 90.0)
TASKS = (42.0, 44.0, 65.0, 74.0)
LANE = 45.0
DRIFTS = (-1.0, -0.5, 0.0, 0.5, 1.0)
STEP = 0.3
PARKED = (3.0, 97.0)
# staggered starts in the free band left of every blind cell, with per-body
# speeds so each is exactly at its task point at t* (and they never close on
# each other, so no collisions)
STARTS = tuple(5.0 + 5.0 * i for i in range(len(TASKS)))
SPEEDS = tuple((x - s) / (DT * T_STAR) for x, s in zip(TASKS, STARTS))


def cfg(drift: float = 0.0) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, extra_o=(EXTRA,),
                     o2_velocity=(drift, 0.0), n_balls=len(TASKS))


def corpus():
    eps = []
    for i, lane in enumerate((38.0, 42.0, 46.0, 50.0, 54.0, 58.0, 72.0, 76.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, extra_o=(EXTRA,)), 0,
                       episode=i, init=Init(x=(start, PARKED[0]), y=(lane, PARKED[1]),
                                            v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((45.0, 50.0, 55.0, 72.0, 76.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, extra_o=(EXTRA,)), 0,
                       episode=200 + i, init=Init(x=(column, PARKED[0]),
                                                  y=(start, PARKED[1]),
                                                  v=((0.0, v), (0.0, 0.0)))))
    return eps


def predicted_identifiable(estimates, point, drift: float) -> bool:
    """The agent's belief: shift each estimated cell by the commanded drift."""
    dx = drift * DT * T_STAR
    for est in estimates:
        rect = est.as_rect()
        if rect is None:
            return False          # unknown geometry: assume the worst
        moved = (rect[0] + dx, rect[1] + dx, rect[2], rect[3])
        if inside_rect(moved, point[0], point[1]):
            return False
    return True


def plan(estimates) -> float:
    scores = {v: sum(1 for x in TASKS
                     if predicted_identifiable(estimates, (x, LANE), v))
              for v in DRIFTS}
    return max(DRIFTS, key=lambda v: (scores[v], -abs(v), -v))


def measured_score(drift: float) -> int:
    config = cfg(drift)
    init = Init(x=STARTS, y=tuple([LANE] * len(TASKS)),
                v=tuple((v, 0.0) for v in SPEEDS))
    hits = 0
    for i in range(len(TASKS)):
        true = Intervention(t=T_STAR, ball=i, dv=(0.0, 1.5))
        ep = run(config, 0, episode=0, init=init, kicks=(Kick(T_STAR, i, (0.0, 1.5)),))
        out = attribute(ep, [true, None], config, 0, init)
        hits += int(bool(out["unique"] and out["best"] is true))
    return hits


def main() -> int:
    episodes = corpus()
    two = estimate_blind_cells(episodes, STEP, n_cells=2)
    one = estimate_blind_cells(episodes, STEP, n_cells=1)
    truth = blind_cells(cfg())
    print(f"true blind cells {truth}")
    for i, est in enumerate(two):
        print(f"  cell {i}: {est.as_rect()}")
    print(f"single-cell estimate (wrong structure): {[e.as_rect() for e in one]}")

    truth_x = sorted((c[0], c[1]) for c in truth)
    contained = all(
        est.x0 is not None and est.x1 is not None
        and any(est.x0 >= tx0 - 1e-9 and est.x1 <= tx1 + 1e-9 for tx0, tx1 in truth_x)
        for est in two
    )
    within_step = all(
        any(0.0 <= est.x0 - tx0 <= STEP and 0.0 <= tx1 - est.x1 <= STEP
            for tx0, tx1 in truth_x)
        for est in two
    )
    p1 = contained and within_step and all(e.as_rect() is not None for e in two)

    gap_two = predicted_identifiable(two, (65.0, LANE), 0.0)
    gap_one = predicted_identifiable(one, (65.0, LANE), 0.0)
    p2 = gap_two is True and gap_one is False

    scores = {v: measured_score(v) for v in DRIFTS}
    oracle = max(DRIFTS, key=lambda v: scores[v])
    two_plan, one_plan = plan(two), plan(one)
    print()
    print("| agent | drift | measured | regret |")
    print("|---|---|---|---|")
    print(f"| two-cell (right structure) | {two_plan:+.1f} | "
          f"{scores[two_plan]}/{len(TASKS)} | {scores[oracle] - scores[two_plan]} |")
    print(f"| one-cell (wrong structure) | {one_plan:+.1f} | "
          f"{scores[one_plan]}/{len(TASKS)} | {scores[oracle] - scores[one_plan]} |")
    print(f"| oracle | {oracle:+.1f} | {scores[oracle]}/{len(TASKS)} | 0 |")

    p3 = scores[two_plan] == scores[oracle]
    p4 = scores[one_plan] < scores[two_plan]

    print()
    print(f"P1 both cells recovered, contained, within one step: "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 the gap is known visible (two-cell) and not (one-cell): "
          f"{'UPHELD' if p2 else 'FALSIFIED'} ({gap_two} vs {gap_one})")
    print(f"P3 two-cell agent plans optimally: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 wrong structural prior costs: {'UPHELD' if p4 else 'FALSIFIED'} "
          f"({scores[one_plan]} vs {scores[two_plan]})")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
