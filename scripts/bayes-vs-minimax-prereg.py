"""R-P1.26 — Bayesian vs minimax planning under self-model error.

Prereg: docs/2026-11-22-PREREG-R-P1.26-bayes-vs-minimax.md, registered before this
script existed (claim 5511f071 registered before the run).

Three priors over the planner's own belief error (flat, peaked-and-honest,
peaked-and-wrong), each choosing a drift by expected predicted score. The choice
is measured on the true world by counterfactual attribution, exactly as
R-P1.21/R-P1.24 did.

Usage: .venv/bin/python scripts/bayes-vs-minimax-prereg.py
"""
from __future__ import annotations

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


def config(drift: float) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, o2_velocity=(drift, 0.0),
                     n_balls=len(TASKS))


def predicted_score(delta: float, drift: float) -> int:
    """Tasks the planner believes identifiable, under its own shifted occluder."""
    base = blind_region(config(drift), T_STAR)
    if base is None:
        return len(TASKS)
    lo = max(O[0], base[0] + delta)
    hi = min(O[1], base[1] + delta)
    if lo >= hi:
        return len(TASKS)
    return sum(1 for x in TASKS if not (lo <= x <= hi and base[2] <= LANE <= base[3]))


def plan(weights: dict) -> float:
    expected = {v: sum(w * predicted_score(d, v) for d, w in weights.items())
                for v in DRIFTS}
    return max(DRIFTS, key=lambda v: (expected[v], -abs(v), -v))


def minimax_plan() -> float:
    return max(DRIFTS, key=lambda v: (min(predicted_score(d, v) for d in DELTAS),
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
    flat = {d: 1.0 / len(DELTAS) for d in DELTAS}
    peaked = {d: 0.2 / (len(DELTAS) - 1) for d in DELTAS}
    peaked[0.0] = 0.8
    wrong = {d: 0.2 / (len(DELTAS) - 1) for d in DELTAS}
    wrong[-20.0] = 0.8

    planners = [("bayes-flat", plan(flat)), ("bayes-peaked", plan(peaked)),
                ("bayes-wrong", plan(wrong)), ("minimax", minimax_plan()),
                ("oracle", None)]
    scores = {v: measured_score(v) for v in DRIFTS}
    oracle = max(DRIFTS, key=lambda v: scores[v])

    print("| planner | drift | measured | regret vs oracle |")
    print("|---|---|---|---|")
    chosen = {}
    for name, drift in planners:
        if drift is None:
            drift = oracle
        chosen[name] = drift
        print(f"| {name} | {drift:+.1f} | {scores[drift]}/{len(TASKS)} | "
              f"{scores[oracle] - scores[drift]} |")

    consistent = all(
        measured_score(chosen[n]) ==
        sum(1 for x in TASKS if predict_identifiable(config(chosen[n]), (x, LANE), T_STAR))
        for n in ("bayes-flat", "bayes-peaked", "bayes-wrong")
    )

    p1 = chosen["bayes-flat"] == -1.0 and scores[-1.0] == 3
    p2 = chosen["bayes-peaked"] == 1.0 and scores[1.0] == 4
    p3 = chosen["bayes-wrong"] == 0.0 and scores[0.0] == 2 < scores[chosen["minimax"]]
    p4 = consistent

    print()
    print(f"P1 flat prior lands on the hedge (3/4): {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 honest confident prior skips the hedge at no cost (4/4): "
          f"{'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 misplaced confident prior is worse than minimax "
          f"({scores[chosen['bayes-wrong']]}/{len(TASKS)} vs "
          f"{scores[chosen['minimax']]}/{len(TASKS)}): {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 the law underlies all three plans: {'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
