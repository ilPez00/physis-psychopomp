"""R-P1.30 — calibrate, then plan: does self-measurement close the gap?

Prereg: docs/2026-11-22-PREREG-R-P1.30-calibrate-then-plan.md, registered before
this script existed (claim 1a0259c2 registered before the run).

Four agents choose one drift: an uncalibrated one with a fixed wrong belief, one
that measures its own blind region with `psychopomp.selfmodel` and plans from the
estimate, one that additionally hedges over its estimate's one-step uncertainty,
and an oracle. The chosen drift is always measured on the true world.

Usage: .venv/bin/python scripts/calibrate-then-plan-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_cells, predict_identifiable
from psychopomp.selfmodel import estimate_blind_region
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

T_STAR, DT, STEPS = 90, 0.1, 200
O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TASKS = (42.0, 46.0, 48.0, 52.0)
LANES = (36.0, 40.0, 44.0, 48.0, 52.0, 56.0, 60.0, 64.0)
COLUMNS = (47.0, 50.0, 53.0)
DRIFTS = (-1.0, -0.5, 0.0, 0.5, 1.0)
LANE = 45.0
BODY_X0 = tuple(x - 27.0 for x in TASKS)
PARKED = (3.0, 97.0)
STEP = 0.3
WRONG_DELTA = -10.0


def config(drift: float) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, o2_velocity=(drift, 0.0),
                     n_balls=len(TASKS))


def calibration_corpus():
    """The observer's own logs: horizontal and vertical sweeps of its blind spot."""
    eps = []
    for i, lane in enumerate(LANES):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2), 0, episode=i,
                       init=Init(x=(start, PARKED[0]), y=(lane, PARKED[1]),
                                 v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate(COLUMNS):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2), 0, episode=100 + i,
                       init=Init(x=(column, PARKED[0]), y=(start, PARKED[1]),
                                 v=((0.0, v), (0.0, 0.0)))))
    return eps


def shifted(rect, drift: float):
    dx = drift * DT * T_STAR
    return (rect[0] + dx, rect[1] + dx, rect[2], rect[3])


def inflate(rect, delta: float):
    return (rect[0] - delta, rect[1] + delta, rect[2] - delta, rect[3] + delta)


def predicted_count(rect, drift: float) -> int:
    r = shifted(rect, drift)
    return sum(1 for x in TASKS if not inside_rect(r, x, LANE))


def pick(believed_rect, hedge: bool = False) -> float:
    if not hedge:
        return max(DRIFTS, key=lambda v: (predicted_count(believed_rect, v), -abs(v), -v))
    variants = [inflate(believed_rect, d) for d in (-STEP, 0.0, STEP)]
    return max(DRIFTS, key=lambda v: (min(predicted_count(r, v) for r in variants),
                                      -abs(v), -v))


def measured_score(drift: float) -> int:
    cfg = config(drift)
    init = Init(x=BODY_X0, y=tuple([LANE] * len(TASKS)),
                v=tuple([(3.0, 0.0)] * len(TASKS)))
    hits = 0
    for i in range(len(TASKS)):
        true = Intervention(t=T_STAR, ball=i, dv=(0.0, 1.5))
        ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(T_STAR, i, (0.0, 1.5)),))
        out = attribute(ep, [true, None], cfg, 0, init)
        hits += int(bool(out["unique"] and out["best"] is true))
    return hits


def main() -> int:
    estimate = estimate_blind_region(calibration_corpus(), STEP)
    est_rect = estimate.as_rect()
    truth_rect = blind_cells(SimConfig(o=O, o2=O2))[0]
    wrong_rect = (O2[0] + WRONG_DELTA, O2[1] + WRONG_DELTA, O2[2], O2[3])

    scores = {v: measured_score(v) for v in DRIFTS}
    oracle = max(DRIFTS, key=lambda v: scores[v])

    plans = {
        "uncalibrated-wrong": pick(wrong_rect),
        "calibrated": pick(est_rect),
        "calibrated-hedged": pick(est_rect, hedge=True),
        "oracle": oracle,
    }
    print(f"true blind {truth_rect}; estimated {est_rect}; "
          f"wrong belief {wrong_rect}")
    print()
    print("| agent | drift | measured | regret |")
    print("|---|---|---|---|")
    for name, drift in plans.items():
        print(f"| {name} | {drift:+.1f} | {scores[drift]}/{len(TASKS)} | "
              f"{scores[oracle] - scores[drift]} |")

    p1 = scores[plans["calibrated"]] == scores[oracle]
    p2 = scores[plans["calibrated"]] > scores[plans["uncalibrated-wrong"]]
    p3 = plans["calibrated-hedged"] == plans["calibrated"]
    p4 = (scores[plans["calibrated"]] ==
          sum(1 for x in TASKS
              if predict_identifiable(config(plans["calibrated"]), (x, LANE), T_STAR)))

    print()
    print(f"P1 calibration recovers the oracle score: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 calibration closes the three-event gap "
          f"({scores[plans['calibrated']]} vs {scores[plans['uncalibrated-wrong']]}): "
          f"{'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 calibration replaces hedging (both pick "
          f"{plans['calibrated']:+.1f}): {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 the law underlies the calibrated plan: {'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
