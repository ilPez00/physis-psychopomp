"""R-P1.19 — does the per-event coverage rule survive rich physics?

Prereg: docs/2026-11-22-PREREG-R-P1.19-rich-physics.md, registered before this
script existed (claim ddf6b815 registered before the run).

12 cells: {separated lanes, same-lane head-on} x {no gravity, gravity} x
{event t = 30, 60, 90}. The prediction is the rule applied to the position at
the event step read from a KICK-FREE run (world trajectory, not the attribution
outcome), and the closed-form predictor is checked against it to show that
gravity actually changes the world.

Usage: .venv/bin/python scripts/rich-physics-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

STEPS, DT, V = 200, 0.1, 3.0
O2 = (40.5, 60.5, 35.0, 65.0)
DV = (0.0, 1.5)
TIMES = (30, 60, 90)
GRAVITIES = [("no-g", (0.0, 0.0)), ("gravity", (0.0, -0.5))]
SCENARIOS = ["lanes", "head-on"]


def build(scenario: str, accel, x0: float):
    if scenario == "lanes":
        init = Init(x=(x0, x0 + 4.0), y=(45.0, 51.0), v=((V, 0.0), (V, 0.0)))
    else:
        # amendment 1: both start outside o, meet inside the blind region, and
        # the -9 speed makes a second contact reachable within 200 steps
        init = Init(x=(15.0, 85.0), y=(45.0, 45.0), v=((V, 0.0), (-9.0, 0.0)))
    return SimConfig(steps=STEPS, o2=O2, accel=accel), init


def blind_at(cfg: SimConfig, t: int):
    from psychopomp.sim import occluder2_at
    second = occluder2_at(cfg, t)
    x0, x1 = max(cfg.o[0], second[0]), min(cfg.o[1], second[1])
    y0, y1 = max(cfg.o[2], second[2]), min(cfg.o[3], second[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def cell(scenario: str, gravity_label: str, accel, t: int) -> dict:
    x0 = 26.0 if scenario == "lanes" else 15.0
    cfg, init = build(scenario, accel, x0)
    kick_free = run(cfg, 0, episode=0, init=init)          # world trajectory
    pos = (kick_free.trajs[0].x[t], kick_free.trajs[0].y[t])
    blind = blind_at(cfg, t)
    predicted_covered = blind is not None and inside_rect(blind, pos[0], pos[1])
    closed_form_x = x0 + V * DT * t
    closed_form_covered = blind is not None and inside_rect(blind, closed_form_x, 45.0)

    true = Intervention(t=t, ball=0, dv=DV)
    ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(t, 0, DV),))
    out = attribute(ep, [true, None], cfg, 0, init)
    measured_unique = bool(out["unique"] and out["best"] is true)

    collisions = [e for e in ep.oracle_log() if e.kind == "ball_collide"]
    hidden = [e for e in collisions if not e.observable]
    skipped = [k for k in ep.skipped_kicks if k.t == t]

    return {
        "scenario": scenario, "gravity": gravity_label, "t": t,
        "pos": pos, "blind": blind,
        "predicted_covered": predicted_covered,
        "measured_unique": measured_unique,
        "match": (not predicted_covered) == measured_unique,
        "closed_form_covered": closed_form_covered,
        "closed_form_gap": abs(closed_form_x - pos[0]),
        "collisions": len(collisions), "hidden_collisions": len(hidden),
        "skipped": len(skipped),
    }


def main() -> int:
    rows = []
    print("| scenario | gravity | t | pos at t | covered? | predicted | measured | collisions (hidden) |")
    print("|---|---|---|---|---|---|---|---|")
    for scenario in SCENARIOS:
        for gravity_label, accel in GRAVITIES:
            for t in TIMES:
                r = cell(scenario, gravity_label, accel, t)
                rows.append(r)
                print(f"| {scenario} | {gravity_label} | {t} | "
                      f"({r['pos'][0]:.1f}, {r['pos'][1]:.1f}) | "
                      f"{'yes' if r['predicted_covered'] else 'no'} | "
                      f"{'tie' if r['predicted_covered'] else 'unique'} | "
                      f"{'unique' if r['measured_unique'] else 'tie'} | "
                      f"{r['collisions']} ({r['hidden_collisions']}) |")

    matches = sum(r["match"] for r in rows)
    gravity_rows = [r for r in rows if r["gravity"] == "gravity"]
    multi = [r for r in rows if r["collisions"] >= 2]
    hidden = [r for r in rows if r["hidden_collisions"] >= 1]

    p1 = matches == len(rows)
    p2 = any(r["closed_form_gap"] > 1.0 for r in gravity_rows) and any(
        r["closed_form_covered"] != r["predicted_covered"] for r in gravity_rows
    )
    p3 = bool(hidden) and all(r["match"] for r in hidden)
    p4 = bool(multi) and all(r["match"] for r in multi)

    print()
    print(f"cells matched {matches}/{len(rows)}; gravity cells {len(gravity_rows)}, "
          f"multi-contact {len(multi)}, hidden-collision {len(hidden)}")
    print(f"closed-form gap (max, gravity): {max(r['closed_form_gap'] for r in gravity_rows):.2f} units")
    print(f"P1 rule holds in every cell: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 closed form is not enough under gravity: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 hidden contacts do not break the rule: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 multi-contact does not break the rule: {'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    if not p1:
        for r in rows:
            if not r["match"]:
                print("  MISMATCH:", r)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
