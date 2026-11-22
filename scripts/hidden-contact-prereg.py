"""R-P1.20 — hidden and multiple contacts, with per-cell capacity checks.

Prereg: docs/2026-11-22-PREREG-R-P1.20-hidden-multi-contact.md, registered before
this script existed.

Every cell proves it contains the event class it claims to test (a hidden
collision, or two collisions) BEFORE its result is counted. A cell that cannot
produce the event is DESIGN-FAILED, never a verdict on the rule.

Usage: .venv/bin/python scripts/hidden-contact-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, occluder2_at, run

STEPS, DT = 200, 0.1
O2 = (40.5, 60.5, 35.0, 65.0)
DV = (0.0, 1.5)
TIMES = (30, 90)
GRAVITIES = [("no-g", (0.0, 0.0)), ("gravity", (0.0, -0.5))]


def blind_at(cfg: SimConfig, t: int):
    second = occluder2_at(cfg, t)
    x0, x1 = max(cfg.o[0], second[0]), min(cfg.o[1], second[1])
    y0, y1 = max(cfg.o[2], second[2]), min(cfg.o[3], second[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def scenario(name: str, accel) -> tuple:
    # Amendment 1: the kicked body sits on its own lane, so the contact
    # structure is identical in every hypothesis (a kick on a pair member
    # displaces it and silently destroys the collision).
    if name == "H":
        init = Init(x=(30.0, 70.0, 20.0), y=(45.0, 45.0, 51.0),
                    v=((3.0, 0.0), (-3.0, 0.0), (3.0, 0.0)))
    else:
        init = Init(x=(10.0, 38.0, 75.0, 20.0), y=(45.0, 45.0, 45.0, 51.0),
                    v=((3.0, 0.0), (-3.0, 0.0), (-3.0, 0.0), (3.0, 0.0)))
    return SimConfig(steps=STEPS, o2=O2, accel=accel, n_balls=len(init.x)), init


def capacity(name: str, collisions: list) -> bool:
    hidden = [c for c in collisions if not c.observable]
    if name == "H":
        return len(hidden) >= 1
    return len(collisions) >= 2 and len(hidden) >= 1


def cell(name: str, gravity_label: str, accel, t: int, target: int) -> dict:
    cfg, init = scenario(name, accel)
    kick_free = run(cfg, 0, episode=0, init=init)
    pos = (kick_free.trajs[target].x[t], kick_free.trajs[target].y[t])
    blind = blind_at(cfg, t)
    covered = blind is not None and inside_rect(blind, pos[0], pos[1])

    true = Intervention(t=t, ball=target, dv=DV)
    ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(t, target, DV),))
    out = attribute(ep, [true, None], cfg, 0, init)
    measured_unique = bool(out["unique"] and out["best"] is true)
    collisions = [e for e in ep.oracle_log() if e.kind == "ball_collide"]
    return {
        "scenario": name, "gravity": gravity_label, "t": t, "target": target,
        "pos": pos, "covered": covered, "measured_unique": measured_unique,
        "match": (not covered) == measured_unique,
        "collisions": len(collisions),
        "hidden": sum(1 for c in collisions if not c.observable),
        "capacity": capacity(name, collisions),
    }


def main() -> int:
    # (scenario, gravity, time, kick target) chosen to give both coverage classes
    plan = [("H", 30, 2), ("H", 90, 2), ("M", 30, 3), ("M", 90, 3)]
    rows = []
    print("| scenario | gravity | t | target | pos at t | covered | measured | collisions (hidden) | capacity |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name in ("H", "M"):
        for gravity_label, accel in GRAVITIES:
            for t, target in [(t, tg) for sc, t, tg in plan if sc == name]:
                r = cell(name, gravity_label, accel, t, target)
                rows.append(r)
                print(f"| {name} | {gravity_label} | {t} | b{target} | "
                      f"({r['pos'][0]:.1f}, {r['pos'][1]:.1f}) | "
                      f"{'yes' if r['covered'] else 'no'} | "
                      f"{'unique' if r['measured_unique'] else 'tie'} | "
                      f"{r['collisions']} ({r['hidden']}) | "
                      f"{'OK' if r['capacity'] else 'DESIGN-FAILED'} |")

    scored = [r for r in rows if r["capacity"]]
    design_failed = [r for r in rows if not r["capacity"]]
    hidden_cells = [r for r in scored if r["hidden"] >= 1]
    multi_cells = [r for r in scored if r["collisions"] >= 2]
    covered_cells = [r for r in scored if r["covered"]]
    uncovered_cells = [r for r in scored if not r["covered"]]

    p1 = bool(scored) and all(r["match"] for r in scored)
    p2 = not design_failed
    p3 = len(hidden_cells) >= 4 and all(r["match"] for r in hidden_cells)
    p4 = len(multi_cells) >= 2 and all(r["match"] for r in multi_cells)
    p5 = bool(covered_cells) and bool(uncovered_cells)

    print()
    print(f"capacity-passing {len(scored)}/{len(rows)}, design-failed {len(design_failed)}, "
          f"hidden-contact {len(hidden_cells)}, multi-contact {len(multi_cells)}")
    print(f"P1 rule holds in every capacity-passing cell: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 every cell has the capacity it claims: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 hidden-contact cells exist (>=4) and obey: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 multi-contact cells exist (>=2) and obey: {'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 both coverage classes present: {'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("prereg run:", "PASS" if ok else "FAIL")
    for r in design_failed:
        print("  DESIGN-FAILED:", r["scenario"], r["gravity"], r["t"],
              f"collisions {r['collisions']} hidden {r['hidden']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
