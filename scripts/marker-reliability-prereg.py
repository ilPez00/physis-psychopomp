"""R-P1.40 — identity identifiability = 1 - (1-p)^N.

Prereg: docs/2026-11-22-PREREG-R-P1.40-marker-reliability.md, registered before this
script existed (claim registered before the run).

Marker opportunities fire with probability p; identity is resolvable iff at least
one fired. Coverage sets N (how many visible opportunities exist), reliability sets
p, and the two compose in the exponent.

Usage: .venv/bin/python scripts/marker-reliability-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.sim import Init, SimConfig, run

PS = (1.0, 0.9, 0.7, 0.5, 0.2, 0.0)
REALIZATIONS = 200
OPEN = {"o": (40.0, 60.0, 35.0, 65.0), "o2": (46.0, 54.0, 35.0, 65.0)}
HIDDEN = {"o": (5.0, 95.0, 5.0, 95.0), "o2": (5.0, 95.0, 5.0, 95.0)}
NEAR = {"o": (40.0, 60.0, 35.0, 65.0), "o2": (46.0, 54.0, 35.0, 65.0)}
BODIES = (((20.0, 45.0), (3.0, 0.0)), ((80.0, 51.0), (-3.0, 0.0)))
STILL = (((40.0, 50.0), (0.0, 0.0)), ((60.0, 50.0), (0.0, 0.0)))
NEAR_BODIES = (((48.0, 45.0), (3.0, 0.0)), ((56.0, 51.0), (-3.0, 0.0)))


def episode(world, p: float, realization: int, bodies=BODIES, swapped: bool = False):
    a, b = bodies if not swapped else (bodies[1], bodies[0])
    cfg = SimConfig(steps=300, o=world["o"], o2=world["o2"],
                    identity_marker=True, marker_period=10,
                    marker_reliability=p, allow_hidden_init=True)
    return run(cfg, 0, episode=realization,
               init=Init(x=(a[0][0], b[0][0]), y=(a[0][1], b[0][1]), v=(a[1], b[1])))


def log_set(ep):
    return sorted((e.kind, e.t, tuple(sorted(e.attrs.items())))
                  for e in ep.observable_log())


def markers(ep):
    return sum(1 for e in ep.observable_log() if e.kind == "marker")


def measured(world, p: float, bodies=BODIES) -> float:
    differ = 0
    for r in range(REALIZATIONS):
        if log_set(episode(world, p, r, bodies)) != log_set(episode(world, p, r, bodies, True)):
            differ += 1
    return differ / REALIZATIONS


def main() -> int:
    n_open = markers(episode(OPEN, 1.0, 0))
    n_near = markers(episode(NEAR, 1.0, 0, NEAR_BODIES))
    print(f"visible marker opportunities: open geometry N={n_open}, "
          f"short-window geometry N={n_near}")

    print("| p | N | predicted 1-(1-p)^N | measured resolvable |")
    print("|---|---|---|---|")
    rows = {}
    for p in PS:
        m = measured(OPEN, p)
        predicted = 1.0 - (1.0 - p) ** n_open
        rows[p] = {"predicted": predicted, "measured": m}
        print(f"| {p:.1f} | {n_open} | {predicted:.3f} | {m:.3f} |")

    r1 = all(abs(rows[p]["measured"] - rows[p]["predicted"]) <= 0.05 for p in PS)
    r2 = rows[0.0]["measured"] == 0.0
    r3 = all(measured(HIDDEN, p, STILL) == 0.0 for p in PS)

    # R4: the product, not either factor alone — compare the two geometries where
    # their predictions differ most
    diffs = []
    for p in PS:
        pred_open = 1.0 - (1.0 - p) ** n_open
        pred_near = 1.0 - (1.0 - p) ** n_near
        diffs.append((abs(pred_open - pred_near), p, pred_open, pred_near))
    _, p_best, pred_open, pred_near = max(diffs)
    meas_open = measured(OPEN, p_best)
    meas_near = measured(NEAR, p_best, NEAR_BODIES)
    predicted_gap = abs(pred_open - pred_near)
    measured_gap = abs(meas_open - meas_near)
    r4 = abs(measured_gap - predicted_gap) <= 0.10

    print()
    print(f"R1 the formula 1-(1-p)^N holds within 0.05: {'UPHELD' if r1 else 'FALSIFIED'}")
    print(f"R2 zero reliability leaves identity ambiguous exactly: "
          f"{'UPHELD' if r2 else 'FALSIFIED'}")
    print(f"R3 coverage gates it: N=0 gives 0 at every p, including p=1.0: "
          f"{'UPHELD' if r3 else 'FALSIFIED'}")
    print(f"R4 the product predicts, not either factor (p={p_best}: predicted gap "
          f"{predicted_gap:.3f}, measured {measured_gap:.3f}): "
          f"{'UPHELD' if r4 else 'FALSIFIED'}")
    ok = all((r1, r2, r3, r4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
