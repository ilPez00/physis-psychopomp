"""R-P1.71: a mask with a hole, and the event inside it.

Frozen card: docs/2026-11-27-PREREG-R-P1.71-mask-hole.md, pushed at `5febebd`
before this file existed. Claim `2b0c9ed6-3458-4e3d-9a14-c0139f6ff330`.

R-P1.70 tried to test a reflex mask and did not: `sim.py`'s occluders are a
**union** (`o`, `extra_o`, `poly_o` all add mask), so an L polygon on top of the
default rectangle is a solid rectangle with extra corners. A mask *with a hole*
needs the mandatory first rectangle parked away from the action.

Arms (one mask, different events — the pair R-P1.70 could not form):

  A  solid rectangle, event inside          (control: must tie)
  B  hole, event in the notch               (predicted unique)
  C  hole, event in the solid arm           (predicted tie)
  D  no mask, event where B's notch is      (predicted unique, equal to B)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, observable, run

CLAIM = "2b0c9ed6-3458-4e3d-9a14-c0139f6ff330"
SEEDS = (0, 1, 2, 3, 4)
STEPS = 400
DT = 0.1

# The L: a 20x30 block with its upper-left 12x15 removed, so (46,55) is a notch
# enclosed on three sides and (46,45) is solid mask.
L_POLY = ((40.0, 35.0), (60.0, 35.0), (60.0, 65.0), (52.0, 65.0),
          (52.0, 50.0), (40.0, 50.0))
SOLID = (40.0, 60.0, 35.0, 65.0)
PARKED = (2.0, 4.0, 2.0, 4.0)      # far from the action; see the card's fixture

NOTCH_EVENT = (46.0, 55.0)
SOLID_EVENT = (46.0, 45.0)


def arm_config(arm: str) -> SimConfig:
    if arm == "A":
        return SimConfig(steps=STEPS, o=SOLID)
    if arm in ("B", "C"):
        return SimConfig(steps=STEPS, o=PARKED, poly_o=(L_POLY,))
    if arm == "D":
        return SimConfig(steps=STEPS, o=PARKED)
    raise ValueError(arm)


def event_for(arm: str) -> tuple[float, float]:
    return SOLID_EVENT if arm in ("A", "C") else NOTCH_EVENT


def body_at(x0: float, y0: float, vx: float, vy: float, t: int):
    return (x0 + vx * t * DT, y0 + vy * t * DT)


def make_runner(target: tuple[float, float]):
    """A body that is at `target` when the kick fires, with a parked second body.

    The start is chosen backwards from the target so the event lands where the
    arm needs it without moving the timing.
    """
    return target


def cell(arm: str, seed: int) -> dict:
    cfg = arm_config(arm)
    tx, ty = event_for(arm)
    vx = 3.0
    # solve x0 so that x0 + vx*t*dt == tx at the kick
    t = 60
    x0 = tx - vx * t * DT
    y0 = ty
    init = Init(x=(x0, 3.0), y=(y0, 97.0), v=((vx, 0.0), (0.0, 0.0)))
    kick = Intervention(t=t, ball=0, dv=(0.0, 1.5))
    ep = run(cfg, seed, init=init, kicks=(Kick(t, 0, (0.0, 1.5)),))
    out = attribute(ep, [kick, None], cfg, seed, init)
    return {
        "arm": arm, "seed": seed,
        "event": [round(tx, 3), round(ty, 3)],
        "visible_at_event": bool(observable(cfg, tx, ty)),
        "unique": bool(out["unique"]),
        "ambiguity": len(out["ambiguity"]),
        "margin": out["margin"],
    }


def mutation_cell(seed: int) -> dict:
    """Park the first rectangle ON the notch: B must become a tie."""
    cfg = SimConfig(steps=STEPS, o=(40.0, 60.0, 50.0, 65.0), poly_o=(L_POLY,))
    tx, ty = NOTCH_EVENT
    vx = 3.0
    x0 = tx - vx * 60 * DT
    init = Init(x=(x0, 3.0), y=(ty, 97.0), v=((vx, 0.0), (0.0, 0.0)))
    kick = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    ep = run(cfg, seed, init=init, kicks=(Kick(60, 0, (0.0, 1.5)),))
    out = attribute(ep, [kick, None], cfg, seed, init)
    return {"arm": "mutation", "seed": seed,
            "visible_at_event": bool(observable(cfg, tx, ty)),
            "unique": bool(out["unique"]), "ambiguity": len(out["ambiguity"])}


def main() -> int:
    cells = {arm: [cell(arm, s) for s in SEEDS] for arm in ("A", "B", "C", "D")}
    uniq = {arm: [c["unique"] for c in cells[arm]] for arm in cells}
    vis = {arm: cells[arm][0]["visible_at_event"] for arm in cells}

    p1 = (not any(uniq["A"])) and all(c["ambiguity"] == 2 for c in cells["A"])
    p2 = all(uniq["B"])
    p3 = (not any(uniq["C"]))
    p4 = uniq["B"] == uniq["D"]

    # P5: the bounding box of the mask contains the notch event, so a
    # bbox-keyed rule would call B hidden. Reporting B unique falsifies it.
    bx0 = min(p[0] for p in L_POLY)
    bx1 = max(p[0] for p in L_POLY)
    by0 = min(p[1] for p in L_POLY)
    by1 = max(p[1] for p in L_POLY)
    in_bbox = bx0 <= NOTCH_EVENT[0] <= bx1 and by0 <= NOTCH_EVENT[1] <= by1
    p5 = in_bbox and all(uniq["B"])

    mutants = [mutation_cell(s) for s in SEEDS]
    mutation_ok = all(not m["unique"] for m in mutants)

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not mutation_ok:
        verdict += "; UNVERIFIABLE (parking the rectangle on the notch did not hide it)"

    probes = {}
    for arm in ("A", "B", "C", "D"):
        cfg = arm_config(arm)
        probes[arm] = {
            "notch": bool(observable(cfg, *NOTCH_EVENT)),
            "solid": bool(observable(cfg, *SOLID_EVENT)),
            "outside": bool(observable(cfg, 30.0, 45.0)),
        }

    receipt = {
        "card": "R-P1.71", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.71-mask-hole.md",
        "command": "python3 scripts/mask-hole-prereg.py",
        "mask": {"poly": list(L_POLY), "parked": list(PARKED),
                 "solid": list(SOLID)},
        "events": {"notch": list(NOTCH_EVENT), "solid": list(SOLID_EVENT)},
        "seeds": list(SEEDS),
        "probes": probes,
        "visibility": vis,
        "unique": uniq,
        "cells": cells,
        "bbox_contains_notch": in_bbox,
        "mutation": mutants,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/mask-hole-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "visibility": vis, "unique": uniq,
                      "probes": probes,
                      "mutation_unique": [m["unique"] for m in mutants]}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
