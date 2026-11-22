"""R-P1.23 — the conjunction: gravity AND a hidden contact.

Prereg: docs/2026-11-22-PREREG-R-P1.23-gravity-hidden-contact.md, registered
before this script existed.

R-P1.20 could not test this: under gravity the pair met at y ~ 33.8, below its
occluder's y >= 35, so the contact was observable. Here the first occluder is
extended downward (o = (40, 60, 20, 65)) so the blind region reaches the contact,
and P3 verifies that the geometry — not a coincidence — is what hides it.

Usage: .venv/bin/python scripts/gravity-hidden-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_region, predict_identifiable
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

STEPS, DT = 200, 0.1
O_EXTENDED = (40.0, 60.0, 20.0, 65.0)
O_R_P1_20 = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 20.0, 65.0)
DV = (0.0, 1.5)
TIMES = (30, 90)
GRAVITY = (0.0, -0.5)


def world_o(o):
    return o


def build(o, accel) -> tuple:
    init = Init(x=(30.0, 70.0, 20.0), y=(45.0, 45.0, 51.0),
                v=((3.0, 0.0), (-3.0, 0.0), (3.0, 0.0)))
    cfg = SimConfig(steps=STEPS, o=o, o2=O2, accel=accel, n_balls=3)
    return cfg, init


def cell(o, accel, t: int) -> dict:
    cfg, init = build(o, accel)
    world = run(cfg, 0, episode=0, init=init)
    point = (world.trajs[2].x[t], world.trajs[2].y[t])
    predicted = predict_identifiable(cfg, point, t)

    true = Intervention(t=t, ball=2, dv=DV)
    ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(t, 2, DV),))
    out = attribute(ep, [true, None], cfg, 0, init)
    measured = bool(out["unique"] and out["best"] is true)

    collisions = [e for e in ep.oracle_log() if e.kind == "ball_collide"]
    hidden = [e for e in collisions if not e.observable]
    return {
        "o": o, "t": t, "point": point, "blind": blind_region(cfg, t),
        "predicted": predicted, "measured": measured, "match": predicted == measured,
        "collisions": len(collisions), "hidden": len(hidden),
        "contact_y": point if False else None,
    }


def contact_coords(o, accel) -> tuple:
    """Where the pair actually meets, and whether that contact is hidden."""
    cfg, init = build(o, accel)
    ep = run(cfg, 0, episode=0, init=init)
    ev = [e for e in ep.oracle_log() if e.kind == "ball_collide"]
    if not ev:
        return None, None, 0, 0
    e = ev[0]
    x = (e.attrs["x_a"][0] + e.attrs["x_b"][0]) / 2.0
    y = (e.attrs["x_a"][1] + e.attrs["x_b"][1]) / 2.0
    return (x, y), e.observable, len(ev), sum(1 for c in ev if not c.observable)


def main() -> int:
    print("| cell | o | t | kick point | blind | predicted | measured | collisions (hidden) |")
    print("|---|---|---|---|---|---|---|---|")
    rows = []
    for accel_label, accel in (("gravity", GRAVITY), ("no-g", (0.0, 0.0))):
        for t in TIMES:
            r = cell(O_EXTENDED, accel, t)
            r["accel"] = accel_label
            rows.append(r)
            print(f"| {accel_label} | extended | {t} | "
                  f"({r['point'][0]:.1f}, {r['point'][1]:.1f}) | {r['blind']} | "
                  f"{'unique' if r['predicted'] else 'tie'} | "
                  f"{'unique' if r['measured'] else 'tie'} | "
                  f"{r['collisions']} ({r['hidden']}) |")

    grav = [r for r in rows if r["accel"] == "gravity"]
    nog = [r for r in rows if r["accel"] == "no-g"]

    geom, obs_ext, n_ext, hid_ext = contact_coords(O_EXTENDED, GRAVITY)
    geomr, obs_r, n_r, hid_r = contact_coords(O_R_P1_20, GRAVITY)

    p1 = all(r["capacity"] if "capacity" in r else r["hidden"] >= 1 for r in grav) \
        and all(r["match"] for r in grav)
    p2 = all(r["match"] for r in nog)
    p3 = (geom is not None and geom[1] <= 65.0 and not obs_ext
          and obs_r is True and geomr is not None and geomr[1] < 35.0)
    p4 = all(
        predict_identifiable(SimConfig(steps=STEPS, o=o, o2=O2, accel=GRAVITY, n_balls=3),
                             r["point"], r["t"])
        == r["predicted"]
        for r in grav for o in (O_EXTENDED, O_R_P1_20)
    )

    print()
    print(f"contact under gravity, extended occluder: {geom}  hidden={not obs_ext}  "
          f"collisions={n_ext} (hidden {hid_ext})")
    print(f"contact under gravity, R-P1.20 occluder:  {geomr}  hidden={not obs_r}  "
          f"collisions={n_r} (hidden {hid_r})")
    print(f"P1 gravity cells have a hidden contact and obey the rule: "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 no-gravity controls obey the rule: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 the geometry is why it is hidden: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 the kicked body's coverage class is geometry-independent: "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
