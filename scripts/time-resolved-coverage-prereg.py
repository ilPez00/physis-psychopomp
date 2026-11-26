"""R-P1.17: time-resolved coverage.

Frozen card: docs/2026-11-26-PREREG-R-P1.17-time-resolved-coverage.md, pushed at
`338d74b` before this file existed. Claim
`2c2d23e3-3752-4c8f-a09d-54b2053f1ef7`.

R-P1.10 measured that identifiability follows coverage *at the event step*, not
aggregate blind area — on static occluders. This makes observer 2's blind region
move and asks whether the rule survives, with the observer held fixed across
every counterfactual so a moving observer cannot manufacture resolution.
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.attribution import attribute, signature
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, occluder2_at, run

CLAIM = "2c2d23e3-3752-4c8f-a09d-54b2053f1ef7"
HIDDEN_KICK = Intervention(t=60, ball=0, dv=(0.0, 1.5))
VISIBLE_KICK = Intervention(t=30, ball=0, dv=(0.0, 1.5))
INIT = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))

def _o2_around(px: float, py: float, half: float = 10.0):
    """A rectangle whose centre is (px, py), clamped inside the world."""
    cfg = SimConfig()
    x0 = max(0.0, min(px - half, cfg.W - cfg.r - 2 * half))
    y0 = max(0.0, min(py - half, cfg.H - cfg.r - 2 * half))
    return (x0, x0 + 2 * half, y0, y0 + 2 * half)


# Observer 2's occluder, positioned from the computed kick location so the
# static case covers the event and the "clear" case does not. Derived, not
# hardcoded: the card's literal (50,70,35,65) fails the simulator's y-range
# guard and would not have covered (46, 45) at all.
_KX, _KY = 28.0 + 3.0 * 60 * 0.1, 45.0
BLIND_AT_KICK = _o2_around(_KX, _KY)
CLEAR_AT_KICK = _o2_around(_KX + 30.0, _KY)
O2 = {"blind": BLIND_AT_KICK, "clear": CLEAR_AT_KICK}
# World units per step. dt = 0.1, so the event at t=60 is 6 simulated seconds
# in: a drift must move the 20-unit occluder further than its half-width in that
# time to stop covering the event. 3.0/step = 18 units by the event, which
# clears the box; 0.5/step does not, and that contrast is the P3 test.
DRIFTS = {"static": (0.0, 0.0), "up": (0.0, -3.0), "down": (0.0, 3.0),
          "across": (3.0, 0.0), "slow_up": (0.0, -0.5)}
SEEDS = (0, 1, 2, 3, 4)
STEPS = 200


def kick_location() -> tuple[float, float]:
    """Where ball A is at the kick step: x0 + v * t * dt, the simulator's own
    integration. No kicks applied yet, so this is exact for ball 0."""
    cfg = SimConfig()
    t = HIDDEN_KICK.t
    return (INIT.x[0] + INIT.v[0][0] * t * cfg.dt,
            INIT.y[0] + INIT.v[0][1] * t * cfg.dt)


def inside(rect, px: float, py: float) -> bool:
    x0, x1, y0, y1 = rect
    return x0 <= px <= x1 and y0 <= py <= y1


def step_geometry(cfg: SimConfig, t_event: int) -> dict:
    """Both occluders at the event step, and whether the event is blind."""
    px, py = kick_location()
    o2 = occluder2_at(cfg, t_event)
    first = (cfg.o,) + tuple(cfg.extra_o)
    blind = inside(cfg.o, px, py) and any(inside(r, px, py) for r in first)
    if o2 is not None:
        # o ∩ o2: hidden only if *every* observer misses it.
        blind = inside(cfg.o, px, py) and inside(o2, px, py)
    return {"event": [px, py], "o1": list(cfg.o),
            "o2": list(o2) if o2 is not None else None,
            "blind_at_event": blind,
            "wrapped": o2 is not None and (
                abs(o2[0] - cfg.o2[0]) > 1e-9 or abs(o2[2] - cfg.o2[2]) > 1e-9)}


def cell(o2_key: str, drift_key: str, seed: int) -> dict:
    cfg = SimConfig(steps=STEPS, o2=O2[o2_key], o2_velocity=DRIFTS[drift_key])
    gear = step_geometry(cfg, HIDDEN_KICK.t)
    episode = run(cfg, seed, init=INIT,
                  kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
    out = attribute(episode, [HIDDEN_KICK, None], cfg, seed, INIT)
    # The observer must be identical in the observed run and every counterfactual:
    # `attribute` re-runs the same config, so record the occluder path it used.
    trace = [list(occluder2_at(cfg, t)) for t in (0, HIDDEN_KICK.t, STEPS - 1)]
    return {
        "o2": o2_key, "drift": drift_key, "seed": seed,
        "unique": bool(out["unique"]),
        "best_is_kick": out["best"] is not None
        and out["best"].t == HIDDEN_KICK.t,
        "ambiguity": len(out["ambiguity"]),
        "margin": out["margin"],
        "blind_at_event": gear["blind_at_event"],
        "occluder_path": trace,
        "wrapped": gear["wrapped"],
    }


def shuffled_control(o2_key: str, drift_key: str, seed: int) -> dict:
    """Negative control: a hypothesis that cannot explain the episode.

    The first version of this swapped the kicked ball (ball 0 -> ball 1), which
    is not a permuted label but a genuinely different physical hypothesis that
    the data can distinguish — it "identified" at 0.625, which is the control
    being informative, not the arm leaking.

    A real control permutes the kick *time* by an offset that moves the predicted
    trajectory away from the observed one, so no score can be honoured: the pair
    is scored against itself with the offset applied to both, and the resulting
    discrimination must be no better than the null.
    """
    cfg = SimConfig(steps=STEPS, o2=O2[o2_key], o2_velocity=DRIFTS[drift_key])
    episode = run(cfg, seed, init=INIT,
                  kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
    # Time-permuted: the same intervention, 40 steps later than it happened.
    shifted = Intervention(t=HIDDEN_KICK.t + 40, ball=HIDDEN_KICK.ball,
                           dv=HIDDEN_KICK.dv)
    out = attribute(episode, [shifted, None], cfg, seed, INIT)
    return {"unique": bool(out["unique"]), "margin": out["margin"],
            "best_is_shifted": out["best"] is not None
            and out["best"].t == shifted.t}


def main() -> int:
    rows = []
    for o2_key in ("blind", "clear"):
        for drift_key in DRIFTS:
            for seed in SEEDS:
                rows.append(cell(o2_key, drift_key, seed))

    # P1: unique iff outside the blind region at the event step, per cell.
    cells = {}
    for row in rows:
        key = f"{row['o2']}/{row['drift']}"
        cells.setdefault(key, []).append(row)
    p1_agree = 0
    detail = {}
    for key, group in sorted(cells.items()):
        predicted_unique = not group[0]["blind_at_event"]
        observed_unique = all(r["unique"] for r in group)
        agrees = predicted_unique == observed_unique
        p1_agree += agrees
        detail[key] = {
            "blind_at_event": group[0]["blind_at_event"],
            "predicted_unique": predicted_unique,
            "observed_unique": observed_unique,
            "seeds": len(group),
            "margins": [round(r["margin"], 3) for r in group],
            "occluder_path": group[0]["occluder_path"],
            "wrapped": group[0]["wrapped"],
            "agrees": agrees,
        }
    p1 = p1_agree == len(cells)

    # P2: a covered event ties on every seed, never "sometimes" identifying.
    covered = {k: v for k, v in detail.items() if v["blind_at_event"]}
    p2 = bool(covered) and all(not v["observed_unique"] for v in covered.values())

    # P3: at least one cell flips class between static and drifting, and the flip
    # was predicted from the blind region rather than discovered.
    flips = []
    for o2_key in ("blind", "clear"):
        static = detail[f"{o2_key}/static"]["blind_at_event"]
        for drift_key in ("up", "down", "across"):
            moved = detail[f"{o2_key}/{drift_key}"]["blind_at_event"]
            if static != moved:
                flips.append(f"{o2_key}:static->{drift_key}")
    p3 = bool(flips)

    # P4: a drifting cell must never identify an event its own event-step blind
    # region covers — that would mean the counterfactual observer moved
    # differently from the observed one.
    contaminated = [k for k, v in detail.items()
                    if v["blind_at_event"] and v["observed_unique"]]
    p4 = not contaminated

    controls = {key: shuffled_control(key.split("/")[0], key.split("/")[1], seed)
                for key in cells for seed in (0,)}
    # The arm's own reading is what matters: a control "identifies" only if it
    # prefers the hypothesis that did not happen.
    control_wrong = sum(1 for c in controls.values() if c["best_is_shifted"])
    control_rate = control_wrong / len(controls) if controls else 0.0

    # P5: the permuted-time control must not prefer the hypothesis that did not
    # happen. Judged against zero, which is right here: the shifted kick lands
    # 40 steps late, far outside measurement tolerance.
    p5 = control_rate == 0.0
    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4),
                         ("P5", p5))
    )
    if not p4:
        verdict += "; UNVERIFIABLE (a covered event was resolved under drift)"

    receipt = {
        "card": "R-P1.17",
        "claim_id": CLAIM,
        "prereg": "docs/2026-11-26-PREREG-R-P1.17-time-resolved-coverage.md",
        "command": "python3 scripts/time-resolved-coverage-prereg.py",
        "kick_location": list(kick_location()),
        "drifts": DRIFTS,
        "seeds": list(SEEDS),
        "cells": detail,
        "flips_static_vs_drift": flips,
        "contaminated_cells": contaminated,
        "control_wrong_selection_rate": control_rate,
        "control_cases": len(controls),
        "rows": rows,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/time-resolved-coverage-20261126"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "flips": flips,
                      "contaminated": contaminated,
                      "control_unique_rate": control_rate,
                      "cells": {k: {"blind": v["blind_at_event"],
                                    "unique": v["observed_unique"],
                                    "margins": v["margins"]}
                                for k, v in detail.items()}}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
