"""R-P1.32 — estimate the cell count itself, then plan.

Prereg: docs/2026-11-22-PREREG-R-P1.32-auto-cell-count.md, registered before this
script existed (claim registered before the run).

`estimate_blind_cells_auto` recovers the number of blind cells from the crossing
evidence, so no structural prior is supplied. Three agents plan from it: one on a
corpus that sweeps both cells, one on a corpus that never reaches the second cell,
and — for comparison — R-P1.31's agent that was *told* the count.

Usage: .venv/bin/python scripts/auto-cell-count-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_cells
from psychopomp.selfmodel import estimate_blind_cells, estimate_blind_cells_auto
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
STARTS = tuple(5.0 + 5.0 * i for i in range(len(TASKS)))
SPEEDS = tuple((x - s) / (DT * T_STAR) for x, s in zip(TASKS, STARTS))

# R-P1.29 single-cell world, for the "no invented cells" control
O_SINGLE = (40.0, 60.0, 35.0, 65.0)
O2_SINGLE = (46.0, 54.0, 35.0, 65.0)


def islands_cfg(drift: float = 0.0) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, extra_o=(EXTRA,),
                     o2_velocity=(drift, 0.0), n_balls=len(TASKS))


def full_corpus():
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


def sparse_corpus():
    """Crosses cell 0 completely and never reaches the island at 70."""
    eps = []
    for i, lane in enumerate((38.0, 42.0, 46.0, 50.0)):
        eps.append(run(SimConfig(steps=180, o=O, o2=O2, extra_o=(EXTRA,)), 0,
                       episode=300 + i, init=Init(x=(10.0, PARKED[0]),
                                                  y=(lane, PARKED[1]),
                                                  v=((3.0, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((45.0, 50.0, 55.0)):
        eps.append(run(SimConfig(steps=200, o=O, o2=O2, extra_o=(EXTRA,)), 0,
                       episode=400 + i, init=Init(x=(column, PARKED[0]),
                                                  y=(10.0, PARKED[1]),
                                                  v=((0.0, 3.0), (0.0, 0.0)))))
    return eps


def single_corpus():
    eps = []
    for i, lane in enumerate((40.0, 44.0, 48.0, 52.0, 56.0, 60.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O_SINGLE, o2=O2_SINGLE), 0,
                       episode=500 + i, init=Init(x=(start, PARKED[0]),
                                                  y=(lane, PARKED[1]),
                                                  v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((47.0, 50.0, 53.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O_SINGLE, o2=O2_SINGLE), 0,
                       episode=600 + i, init=Init(x=(column, PARKED[0]),
                                                  y=(start, PARKED[1]),
                                                  v=((0.0, v), (0.0, 0.0)))))
    return eps


def predicted_identifiable(estimates, point, drift: float) -> bool:
    dx = drift * DT * T_STAR
    for est in estimates:
        rect = est.as_rect()
        if rect is None:
            return False
        if inside_rect((rect[0] + dx, rect[1] + dx, rect[2], rect[3]),
                       point[0], point[1]):
            return False
    return True


def plan(estimates) -> float:
    scores = {v: sum(1 for x in TASKS
                     if predicted_identifiable(estimates, (x, LANE), v))
              for v in DRIFTS}
    return max(DRIFTS, key=lambda v: (scores[v], -abs(v), -v))


def measured_score(drift: float) -> int:
    config = islands_cfg(drift)
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
    truth = blind_cells(islands_cfg())
    auto_full = estimate_blind_cells_auto(full_corpus(), STEP)
    auto_sparse = estimate_blind_cells_auto(sparse_corpus(), STEP)
    auto_single = estimate_blind_cells_auto(single_corpus(), STEP)
    given = estimate_blind_cells(full_corpus(), STEP, n_cells=2)

    print(f"true cells (islands) {truth}")
    print(f"auto, full corpus     {[c.as_rect() for c in auto_full]}")
    print(f"auto, sparse corpus   {[c.as_rect() for c in auto_sparse]}")
    print(f"auto, single world    {[c.as_rect() for c in auto_single]}")
    print(f"given n_cells=2       {[c.as_rect() for c in given]}")

    truth_x = sorted((c[0], c[1]) for c in truth)
    p1 = len(auto_full) == 2 and all(
        est.x0 is not None and est.x1 is not None
        and any(0.0 <= est.x0 - tx0 <= STEP and 0.0 <= tx1 - est.x1 <= STEP
                for tx0, tx1 in truth_x)
        for est in auto_full
    )
    p2 = (len(auto_single) == 1 and auto_single[0].as_rect() is not None
          and 0.0 <= auto_single[0].x0 - O2_SINGLE[0] <= STEP)

    scores = {v: measured_score(v) for v in DRIFTS}
    oracle = max(DRIFTS, key=lambda v: scores[v])
    agents = {"auto-count (full corpus)": auto_full,
              "given n_cells=2": given,
              "auto-count (sparse corpus)": auto_sparse}
    print()
    print("| agent | drift | measured | regret |")
    print("|---|---|---|---|")
    picks = {}
    for name, est in agents.items():
        picks[name] = plan(est)
        print(f"| {name} | {picks[name]:+.1f} | {scores[picks[name]]}/{len(TASKS)} | "
              f"{scores[oracle] - scores[picks[name]]} |")
    print(f"| oracle | {oracle:+.1f} | {scores[oracle]}/{len(TASKS)} | 0 |")

    p3 = scores[picks["auto-count (full corpus)"]] == scores[oracle]
    p4 = (scores[picks["auto-count (sparse corpus)"]]
          < scores[picks["auto-count (full corpus)"]])

    print()
    print(f"P1 auto count recovers both cells within one step: "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 no invented cells on the single-cell world: "
          f"{'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 auto-count agent plans at the oracle score: "
          f"{'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 a corpus that never crosses the island costs: "
          f"{'UPHELD' if p4 else 'FALSIFIED'} "
          f"({scores[picks['auto-count (sparse corpus)']]} vs "
          f"{scores[picks['auto-count (full corpus)']]})")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
