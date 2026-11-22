"""R-P1.24 — does hedging against your own self-model error pay?

Prereg: docs/2026-11-22-PREREG-R-P1.24-hedged-planning.md, registered before this
script existed (claim bfaab7be registered before the run).

Same world and harness as R-P1.21. Adds a minimax planner that hedges over a
+/-20 unit belief set, and compares it with the naive planner (whose score
depends on how wrong its belief happens to be) and with an oracle upper bound.

Usage: .venv/bin/python scripts/hedged-planning-prereg.py
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
BELIEF_ERRORS = (-20.0, -10.0, 0.0, 10.0, 20.0)
LANE = 45.0
BODY_X0 = tuple(x - 27.0 for x in TASKS)      # each body is at its task on step 90


def config(drift: float) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, o2_velocity=(drift, 0.0),
                     n_balls=len(TASKS))


def believed_blind(delta: float, drift: float):
    """Planner's picture: its own occluder shifted by `delta`, intersected with o."""
    base = blind_region(config(drift), T_STAR)
    if base is None:
        return None
    x0, x1 = base[0] + delta, base[1] + delta
    lo, hi = max(O[0], x0), min(O[1], x1)
    return None if lo >= hi else (lo, hi, base[2], base[3])


def predicted_score(delta: float, drift: float) -> int:
    blind = believed_blind(delta, drift)
    if blind is None:
        return len(TASKS)
    return sum(1 for x in TASKS if not (blind[0] <= x <= blind[1] and blind[2] <= LANE <= blind[3]))


def naive_plan(delta: float) -> float:
    return max(DRIFTS, key=lambda v: (predicted_score(delta, v), -abs(v), -v))


def hedged_plan() -> float:
    """Maximise the worst case over the declared belief set."""
    return max(DRIFTS, key=lambda v: (min(predicted_score(d, v) for d in BELIEF_ERRORS),
                                      -abs(v), -v))


def measured_score(drift: float) -> tuple:
    cfg = config(drift)
    init = Init(x=BODY_X0, y=tuple([LANE] * len(TASKS)),
                v=tuple([(3.0, 0.0)] * len(TASKS)))
    hits = 0
    for i, x in enumerate(TASKS):
        true = Intervention(t=T_STAR, ball=i, dv=(0.0, 1.5))
        ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(T_STAR, i, (0.0, 1.5)),))
        out = attribute(ep, [true, None], cfg, 0, init)
        hits += int(bool(out["unique"] and out["best"] is true))
    return hits, len(TASKS)


def main() -> int:
    scores = {v: measured_score(v)[0] for v in DRIFTS}
    print("| drift | measured |")
    print("|---|---|")
    for v in DRIFTS:
        print(f"| {v:+.1f} | {scores[v]}/{len(TASKS)} |")

    naive = {d: naive_plan(d) for d in BELIEF_ERRORS}
    hedged = hedged_plan()
    oracle = max(DRIFTS, key=lambda v: scores[v])

    print()
    print("| planner | drift | measured |")
    print("|---|---|---|")
    for d in BELIEF_ERRORS:
        print(f"| naive δ={d:+.0f} | {naive[d]:+.1f} | {scores[naive[d]]}/{len(TASKS)} |")
    print(f"| **hedged** | {hedged:+.1f} | **{scores[hedged]}/{len(TASKS)}** |")
    print(f"| oracle | {oracle:+.1f} | {scores[oracle]}/{len(TASKS)} |")

    naive_worst = min(scores[naive[d]] for d in BELIEF_ERRORS)
    hedged_score = scores[hedged]
    regret = scores[oracle] - hedged_score
    consistent = predicted_score(0.0, hedged) == hedged_score

    h1 = hedged_score >= 2 and hedged_score > naive_worst
    h2 = hedged_score <= 4 and regret <= 2
    h3 = hedged != naive[0.0]
    h4 = consistent

    print()
    print(f"naive worst case {naive_worst}/{len(TASKS)}; hedged {hedged_score}/{len(TASKS)}; "
          f"oracle {scores[oracle]}/{len(TASKS)}; regret {regret}")
    print(f"H1 hedging beats being wrong: {'UPHELD' if h1 else 'FALSIFIED'} "
          f"({hedged_score} vs naive worst {naive_worst})")
    print(f"H2 hedging is not free but affordable: {'UPHELD' if h2 else 'FALSIFIED'} "
          f"(regret {regret})")
    print(f"H3 the hedge changes the plan: {'UPHELD' if h3 else 'FALSIFIED'} "
          f"(hedged {hedged:+.1f} vs confident {naive[0.0]:+.1f})")
    print(f"H4 the hedge changes the plan, never the rule: "
          f"{'UPHELD' if h4 else 'FALSIFIED'}")
    ok = all((h1, h2, h3, h4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
