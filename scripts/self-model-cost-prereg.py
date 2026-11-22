"""R-P1.21 — the cost of a wrong self-model for a choosing observer.

Prereg: docs/2026-11-22-PREREG-R-P1.21-self-model-cost.md, registered before this
script existed (claim ad1b14aa registered before the run).

An observer picks a drift from a fixed grid to push its own blind window off the
task events. It plans from a *belief* about its occluder (o2 + delta) and is
measured under the truth. The question is the shape of the loss, not just its
size: discrete (ranking flips) or gradual.

Usage: .venv/bin/python scripts/self-model-cost-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, occluder2_at, run

T_STAR, DT, STEPS = 90, 0.1, 200
O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TASKS = (42.0, 46.0, 48.0, 52.0)      # asymmetric on purpose (three crowded left)
DRIFTS = (-1.0, -0.5, 0.0, 0.5, 1.0)
BELIEF_ERRORS = (0.0, -10.0, 10.0, -20.0, 20.0)
LANE = 45.0
# one body per task point: each body is exactly at its task x at t* (v*dt*t* = 27)
BODY_X0 = tuple(x - 27.0 for x in TASKS)


def config(drift: float) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, o2_velocity=(drift, 0.0),
                     n_balls=len(TASKS))


def believed_blind(delta: float, drift: float):
    """The planner's picture: its occluder shifted by `delta`, intersected with o."""
    second = occluder2_at(config(drift), T_STAR)
    bx0 = second[0] + delta
    bx1 = second[1] + delta
    x0, x1 = max(O[0], bx0), min(O[1], bx1)
    y0, y1 = max(O[2], second[2]), min(O[3], second[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def true_blind(drift: float):
    return believed_blind(0.0, drift)


def predicted_identifiable(blind, tasks) -> int:
    if blind is None:
        return len(tasks)
    return sum(1 for x in tasks if not inside_rect(blind, x, LANE))


def plan(delta: float) -> float:
    """Pick the drift maximising believed identifiability; ties -> smallest |v|."""
    best = None
    for v in DRIFTS:
        score = predicted_identifiable(believed_blind(delta, v), TASKS)
        key = (-score, abs(v), v)
        if best is None or key < best[0]:
            best = (key, v)
    return best[1]


def measured_score(drift: float) -> tuple:
    """Measured identifiability of each task event under the TRUE geometry."""
    cfg = config(drift)
    n = len(TASKS)
    init = Init(
        x=BODY_X0, y=tuple([LANE] * n), v=tuple([(3.0, 0.0)] * n),
    )
    world = run(cfg, 0, episode=0, init=init)
    hits = scored = 0
    seen = []
    for i, x in enumerate(TASKS):
        at = world.trajs[i].x[T_STAR]
        # capacity check: the body must be at its task point, or the task is
        # DESIGN-FAILED rather than counted as a tie
        if abs(at - x) > 1.0:
            seen.append((x, round(at, 2), "unreachable"))
            continue
        scored += 1
        true = Intervention(t=T_STAR, ball=i, dv=(0.0, 1.5))
        ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(T_STAR, i, (0.0, 1.5)),))
        out = attribute(ep, [true, None], cfg, 0, init)
        ok = bool(out["unique"] and out["best"] is true)
        hits += int(ok)
        seen.append((x, round(at, 2), "unique" if ok else "tie"))
    return hits, scored, seen


def main() -> int:
    print("| drift | blind at t* | predicted identifiable | measured |")
    print("|---|---|---|---|")
    measured = {}
    for v in DRIFTS:
        pred = predicted_identifiable(true_blind(v), TASKS)
        hits, n, seen = measured_score(v)
        measured[v] = hits
        unreachable = [s for s in seen if s[2] == "unreachable"]
        print(f"| {v:+.1f} | {true_blind(v)} | {pred}/{len(TASKS)} | {hits}/{n} | "
              f"{'DESIGN-FAILED ' + str(unreachable) if unreachable else ''} |")

    print()
    print("| belief error δ | chosen drift | measured | optimum | cost |")
    print("|---|---|---|---|---|")
    optimum = max(measured.values())
    rows = []
    for delta in BELIEF_ERRORS:
        v = plan(delta)
        hits = measured[v]
        rows.append({"delta": delta, "drift": v, "score": hits, "cost": optimum - hits})
        print(f"| {delta:+.0f} | {v:+.1f} | {hits}/{len(TASKS)} | {optimum}/{len(TASKS)} | "
              f"{optimum - hits} |")

    correct = [r for r in rows if r["delta"] == 0][0]
    p1 = correct["score"] == optimum
    p2 = any(r["cost"] > 0 for r in rows)
    p3 = any(r["delta"] != 0 and r["drift"] == correct["drift"] and r["cost"] == 0 for r in rows)
    p4 = all(measured[v] == predicted_identifiable(true_blind(v), TASKS) for v in DRIFTS)
    static = measured[0.0]
    p5 = optimum > static

    print()
    print(f"optimum over drifts {optimum}/{len(TASKS)}, static {static}/{len(TASKS)}")
    print(f"P1 correct self-model reaches the optimum: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 a wrong self-model can cost: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 and can be free (discrete loss): {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 measured scores are the rule's predictions: {'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 agency matters (optimum > static): {'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
