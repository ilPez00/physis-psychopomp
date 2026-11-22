"""R-P1.27 — the cost of a confident prior: all five peaks, declared in advance.

Prereg: docs/2026-11-22-PREREG-R-P1.27-prior-sweep.md, registered before this
script existed.

R-P1.26 guessed one misplaced prior and was falsified by it. This card sweeps
every peak in the belief set, so the answer is a distribution instead of a story,
and no peak can be chosen after the fact.

Usage: .venv/bin/python scripts/prior-sweep-prereg.py
"""
from __future__ import annotations

import statistics
import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_region, predict_identifiable
from psychopomp.sim import Init, Kick, SimConfig, run

T_STAR, DT, STEPS = 90, 0.1, 200
O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TASKS = (42.0, 46.0, 48.0, 52.0)
DRIFTS = (-1.0, -0.5, 0.0, 0.5, 1.0)
DELTAS = (-20.0, -10.0, 0.0, 10.0, 20.0)
LANE = 45.0
BODY_X0 = tuple(x - 27.0 for x in TASKS)
PEAK_MASS = 0.8


def config(drift: float) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, o2_velocity=(drift, 0.0),
                     n_balls=len(TASKS))


def predicted_score(delta: float, drift: float) -> int:
    base = blind_region(config(drift), T_STAR)
    if base is None:
        return len(TASKS)
    lo = max(O[0], base[0] + delta)
    hi = min(O[1], base[1] + delta)
    if lo >= hi:
        return len(TASKS)
    return sum(1 for x in TASKS if not (lo <= x <= hi and base[2] <= LANE <= base[3]))


def plan(peak: float | None) -> float:
    if peak is None:      # minimax
        return max(DRIFTS, key=lambda v: (min(predicted_score(d, v) for d in DELTAS),
                                          -abs(v), -v))
    rest = (1.0 - PEAK_MASS) / (len(DELTAS) - 1)
    weights = {d: (PEAK_MASS if d == peak else rest) for d in DELTAS}
    expected = {v: sum(w * predicted_score(d, v) for d, w in weights.items())
                for v in DRIFTS}
    return max(DRIFTS, key=lambda v: (expected[v], -abs(v), -v))


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
    scores = {v: measured_score(v) for v in DRIFTS}
    oracle = max(DRIFTS, key=lambda v: scores[v])
    oracle_score = scores[oracle]

    print("| planner | drift | measured | cost |")
    print("|---|---|---|---|")
    rows = []
    for peak in DELTAS:
        drift = plan(peak)
        cost = oracle_score - scores[drift]
        rows.append({"peak": peak, "drift": drift, "score": scores[drift], "cost": cost})
        print(f"| peak δ={peak:+.0f} | {drift:+.1f} | {scores[drift]}/{len(TASKS)} | {cost} |")
    hedge_drift = plan(None)
    hedge_cost = oracle_score - scores[hedge_drift]
    print(f"| minimax (no prior) | {hedge_drift:+.1f} | {scores[hedge_drift]}/{len(TASKS)} | {hedge_cost} |")
    print(f"| oracle | {oracle:+.1f} | {oracle_score}/{len(TASKS)} | 0 |")

    costs = [r["cost"] for r in rows]
    consistent = all(
        scores[r["drift"]] ==
        sum(1 for x in TASKS if predict_identifiable(config(r["drift"]), (x, LANE), T_STAR))
        for r in rows
    )

    p1 = len(set(costs)) > 1 and max(costs) >= 2 and min(costs) == 0
    p2 = next(r["cost"] for r in rows if r["peak"] == 0.0) == 0
    p3 = min(costs) <= hedge_cost <= statistics.mean(costs)
    p4 = consistent

    print()
    print(f"costs by peak {dict((r['peak'], r['cost']) for r in rows)}; "
          f"mean {statistics.mean(costs):.2f}, spread {max(costs) - min(costs)}; "
          f"hedge cost {hedge_cost}")
    print(f"P1 the sweep has real spread: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 the peak on the truth is free: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 the hedge sits between the best and the mean: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 the law underlies every plan: {'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
