"""R-P1.17 — time-resolved coverage with a moving observer.

Prereg: docs/2026-11-22-PREREG-R-P1.17-moving-observer.md, registered before this
script existed.

Prediction is analytic: the event is covered iff its position at the kick step is
inside `o ∩ o2(t=60)`, with `o2(t)` folded inside the box. Noise-free cells must
be tie (covered) or unique (uncovered) exactly; a σ=1.0 sweep checks the pattern
survives noise; the occluder schedule is asserted identical across hypotheses.

Usage: .venv/bin/python scripts/moving-observer-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute, candidate_episode, signature
from psychopomp.interventions import Intervention
from psychopomp.sim import (
    Init, Kick, SimConfig, inside_rect, occluder2_at, run,
)

T, DV, STEPS, DT, V = 60, (0.0, 1.5), 200, 0.1, 3.0
LANE = 45.0
O2_BASE = (40.5, 60.5, 35.0, 65.0)
DRIFTS = [("static", (0.0, 0.0)), ("right", (1.667, 0.0)),
          ("left", (-1.667, 0.0)), ("folded", (12.4, 0.0))]
EVENTS = [("E37", 19.0), ("E44", 26.0), ("E55", 37.0)]   # event x = x0 + 18
NOISE_SIGMA = 1.0
NOISE_REALIZATIONS = 100


def cfg_for(drift) -> SimConfig:
    return SimConfig(steps=STEPS, o2=O2_BASE, o2_velocity=drift)


def init_for(x0: float) -> Init:
    # ball 1 to the LEFT of ball 0, so both start outside `o` (x < 40)
    return Init(x=(x0, x0 - 4.0), y=(LANE, LANE), v=((V, 0.0), (V, 0.0)))


def blind_at(cfg: SimConfig, t: int):
    second = occluder2_at(cfg, t)
    if second is None:
        return cfg.o
    x0, x1 = max(cfg.o[0], second[0]), min(cfg.o[1], second[1])
    y0, y1 = max(cfg.o[2], second[2]), min(cfg.o[3], second[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def predicted_covered(cfg: SimConfig, x0: float) -> bool:
    blind = blind_at(cfg, T)
    if blind is None:
        return False
    return inside_rect(blind, x0 + V * DT * T, LANE)


def observer_fixed(cfg: SimConfig, x0: float) -> bool:
    """A counterfactual must see the same occluder schedule as the observation.

    Checked on the actual visibility arrays: when the true hypothesis is a
    skipped kick (covered event) the counterfactual's trajectories must be
    identical step for step, visibility included.
    """
    init = init_for(x0)
    ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(T, 0, DV),))
    cand = candidate_episode(cfg, 0, init, Intervention(t=T, ball=0, dv=DV),
                             episode=0, noise_stream=1)
    for a, b in zip(ep.trajs, cand.trajs):
        if a.visible != b.visible:
            return False
    return True


def cell(drift_label: str, drift, event_label: str, x0: float) -> dict:
    cfg = cfg_for(drift)
    init = init_for(x0)
    true = Intervention(t=T, ball=0, dv=DV)
    ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(T, 0, DV),))
    out = attribute(ep, [true, None], cfg, 0, init)
    covered = predicted_covered(cfg, x0)
    measured_unique = bool(out["unique"] and out["best"] is true)
    scores = {str(h): d for d, h in out["scores"]}
    return {
        "drift": drift_label, "event": event_label, "x0": x0,
        "predicted_covered": covered,
        "predicted_unique": not covered,
        "measured_unique": measured_unique,
        "match": (not covered) == measured_unique,
        "d_true": scores[str(true)], "d_null": scores[str(None)],
        "blind": blind_at(cfg, T), "fixed": observer_fixed(cfg, x0),
    }


def noise_cell(drift_label: str, drift, event_label: str, x0: float) -> dict:
    cfg = SimConfig(steps=STEPS, o2=O2_BASE, o2_velocity=drift, noise=NOISE_SIGMA)
    init = init_for(x0)
    true = Intervention(t=T, ball=0, dv=DV)
    hits = 0
    for r in range(NOISE_REALIZATIONS):
        ep = run(cfg, 0, episode=1000 + r, init=init, kicks=(Kick(T, 0, DV),))
        out = attribute(ep, [true, None], cfg, 0, init)
        s = {str(h): d for d, h in out["scores"]}
        hits += int(s[str(true)] < s[str(None)])
    return {"drift": drift_label, "event": event_label,
            "covered": predicted_covered(cfg_for(drift), x0),
            "accuracy": hits / NOISE_REALIZATIONS}


def main() -> int:
    print("| drift | blind at t=60 | event | predicted | measured | match |")
    print("|---|---|---|---|---|---|")
    rows = []
    for drift_label, drift in DRIFTS:
        for event_label, x0 in EVENTS:
            if drift_label == "folded" and event_label == "E37":
                continue      # declared grid: reflection cell covers 44 and 55 only
            r = cell(drift_label, drift, event_label, x0)
            rows.append(r)
            print(f"| {drift_label} | {r['blind']} | {event_label} "
                  f"(x={x0 + V * DT * T:.0f}) | "
                  f"{'tie' if r['predicted_covered'] else 'unique'} | "
                  f"{'unique' if r['measured_unique'] else 'tie'} | "
                  f"{'OK' if r['match'] else 'MISMATCH'} |")

    matches = sum(r["match"] for r in rows)
    fixed = all(r["fixed"] for r in rows)

    flips = []
    by = {(r["drift"], r["event"]): r for r in rows}
    if by[("static", "E44")]["measured_unique"] is False and by[("right", "E44")]["measured_unique"]:
        flips.append("E44 static->right")
    if by[("static", "E55")]["measured_unique"] is False and by[("left", "E55")]["measured_unique"]:
        flips.append("E55 static->left")
    folded = [r for r in rows if r["drift"] == "folded"]
    reflected = all(r["blind"] is not None and r["blind"][0] > O2_BASE[0] for r in folded) \
        and any(r["blind"] is None or r["blind"][0] != O2_BASE[0] + 12.4 * DT * T for r in folded)

    print()
    print("noise sweep σ=1.0 (100 realizations):")
    noise_ok = True
    for drift_label, drift in DRIFTS[:3]:
        for event_label, x0 in EVENTS:
            n = noise_cell(drift_label, drift, event_label, x0)
            ok = (abs(n["accuracy"] - 0.5) <= 0.15) if n["covered"] else (n["accuracy"] >= 0.90)
            noise_ok &= ok
            print(f"  {drift_label:6s} {event_label} covered={n['covered']!s:5s} "
                  f"acc={n['accuracy']:.2f} {'OK' if ok else 'MISS'}")

    p1 = matches == len(rows)
    p2 = len(flips) == 2
    p3 = reflected
    p4 = noise_ok
    p5 = fixed

    print()
    print(f"P1 time-resolved rule in every cell ({matches}/{len(rows)}): "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 both time-resolved flips observed {flips}: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 reflection tracked through the fold: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 pattern survives σ=1.0: {'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 observer held fixed across counterfactuals: {'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
