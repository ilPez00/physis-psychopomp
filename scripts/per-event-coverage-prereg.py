"""R-P1.11 — out-of-sample test of the per-event coverage rule.

Prereg: docs/2026-11-22-PREREG-R-P1.11-per-event-coverage.md, registered before
this script existed. 30 cells (5 seeds x 3 fresh observer sets x 2 lanes).

The prediction is ANALYTIC, not measured: the kick is applied iff the body is
observable at the kick step, i.e. iff its position at that step is outside
o ∩ o2. Nothing is read from the simulation to build it.

Usage: .venv/bin/python scripts/per-event-coverage-prereg.py
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

T = 60
DV = (0.0, 1.5)
STEPS = 200
DT = 0.1
V = 3.0
SEEDS = (19.0, 23.0, 27.0, 31.0, 35.0)
LANES = (45.0, 51.0)                      # ball 0 and ball 1
CONTROL_DRAWS = 200

OBSERVER_SETS = [
    ("bv-a", (46.5, 66.5, 34.5, 65.5)),
    ("bv-b", (42.5, 62.5, 34.5, 65.5)),
    ("bv-c", (40.5, 60.5, 46.5, 70.0)),
]
BOUNDARY_TOL = 1e-6


def blind_rect(o, o2):
    x0, x1 = max(o[0], o2[0]), min(o[1], o2[1])
    y0, y1 = max(o[2], o2[2]), min(o[3], o2[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def predicted_hidden(o, o2, x0: float, lane: int) -> bool:
    """Analytic: position at the kick step is inside o ∩ o2 -> the kick is skipped."""
    blind = blind_rect(o, o2)
    if blind is None:
        return False
    x = x0 + (4.0 if lane == 1 else 0.0) + V * DT * T
    y = LANES[lane]
    return inside_rect(blind, x, y)


def control_recovery(out, rng) -> float:
    scores = [d for d, _ in out["scores"]]
    hyps = [h for _, h in out["scores"]]
    truth = hyps[0]
    hits = 0
    for _ in range(CONTROL_DRAWS):
        perm = scores[:]
        rng.shuffle(perm)
        low = min(perm)
        tied = [h for d, h in zip(perm, hyps) if d == low]
        hits += int(rng.choice(tied) is truth)
    return hits / CONTROL_DRAWS


def main() -> int:
    rows = []
    print("| set | x0 | lane | predicted | measured | ambiguity | d(true) | d(null) | control |")
    print("|---|---|---|---|---|---|---|---|---|")
    for label, o2 in OBSERVER_SETS:
        for x0 in SEEDS:
            for lane in (0, 1):
                cfg = SimConfig(steps=STEPS, o2=o2)
                init = Init(x=(x0, x0 + 4.0), y=(LANES[0], LANES[1]),
                            v=((V, 0.0), (V, 0.0)))
                true = Intervention(t=T, ball=lane, dv=DV)
                decoy = Intervention(t=30, ball=lane, dv=DV)
                ep = run(cfg, int(x0), init=init, kicks=(Kick(T, lane, DV),))
                out = attribute(ep, [true, None, decoy], cfg, int(x0), init)
                scores = {str(h): d for d, h in out["scores"]}
                measured_unique = bool(out["unique"] and out["best"] is true)
                hidden = predicted_hidden(cfg.o, o2, x0, lane)
                # declared boundary rule: an event within 1e-6 of a blind edge
                # is excluded from the rule, not counted either way
                blind = blind_rect(cfg.o, o2)
                ex = x0 + (4.0 if lane == 1 else 0.0) + V * DT * T
                on_boundary = blind is not None and any(
                    abs(ex - edge) <= BOUNDARY_TOL for edge in (blind[0], blind[1])
                ) or blind is not None and any(
                    abs(LANES[lane] - edge) <= BOUNDARY_TOL for edge in (blind[2], blind[3])
                )
                predicted_unique = not hidden
                rows.append({
                    "set": label, "x0": x0, "lane": lane,
                    "predicted_unique": predicted_unique,
                    "measured_unique": measured_unique,
                    "match": predicted_unique == measured_unique,
                    "on_boundary": on_boundary,
                    "ambiguity": len(out["ambiguity"]),
                    "d_true": scores[str(true)], "d_null": scores[str(None)],
                    "control": control_recovery(out, random.Random(int(x0 * 17 + lane * 5 + 3))),
                })
                r = rows[-1]
                print(f"| {label} | {x0:.0f} | y={LANES[lane]:.0f} | "
                      f"{'unique' if predicted_unique else 'tie'} | "
                      f"{'unique' if measured_unique else 'tie'} | {r['ambiguity']} | "
                      f"{r['d_true']:.2f} | {r['d_null']:.2f} | {r['control']:.3f} |")

    boundary = [r for r in rows if r["on_boundary"]]
    scored = [r for r in rows if not r["on_boundary"]]
    matches = sum(r["match"] for r in scored)
    h1 = matches == len(scored) and not boundary
    c_lane0 = [r for r in rows if r["set"] == "bv-c" and r["lane"] == 0]
    c_lane1 = [r for r in rows if r["set"] == "bv-c" and r["lane"] == 1]
    h2 = (all(r["measured_unique"] for r in c_lane0)
          and not any(r["measured_unique"] for r in c_lane1))
    h3 = all(abs(r["control"] - 1 / 3) <= 0.15 for r in rows)
    analytic_unique = sum(r["predicted_unique"] for r in scored)
    h4 = sum(r["measured_unique"] for r in scored) == analytic_unique

    print()
    print(f"boundary exclusions (declared rule, 1e-6): {len(boundary)}")
    print(f"per-cell match {matches}/{len(scored)}; unique-correct measured "
          f"{sum(r['measured_unique'] for r in scored)} vs analytic {analytic_unique}")
    print(f"H1 rule holds in every cell: {'SUPPORTED' if h1 else 'FALSIFIED'}")
    print(f"H2 same blind area, opposite outcome (ov-c lanes): "
          f"{'SUPPORTED' if h2 else 'FALSIFIED'}")
    print(f"H3 control at chance: {'SUPPORTED' if h3 else 'FALSIFIED'}")
    print(f"H4 no unexplained ceiling: {'SUPPORTED' if h4 else 'FALSIFIED'}")
    ok = all((h1, h2, h3, h4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
