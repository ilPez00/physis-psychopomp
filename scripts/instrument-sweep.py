"""R-P1.1 — instrument operating point sweep (plan: 2026-11-21 PLAN-R-P1.1).

Two axes on the parallel-lane family: separation at fixed noise, noise at
fixed separation. Reports exact Bayes (the true uniform sensor), the MAP
Gaussian surrogate, the A2 position-continuity probe, and the best unfitted
single statistic, so the choice of operating point is a measurement rather
than a preference.

Usage: .venv/bin/python scripts/instrument-sweep.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import truth_matches
from psychopomp.probes import (
    m2_bayes_accuracy,
    m2_map_accuracy,
    m2_position_continuity,
    statistic_survey,
)
from psychopomp.sim import Init, SimConfig, run

EPISODES = 6


def corpus(sep: float, noise: float, n: int = EPISODES) -> list:
    eps = []
    for k in range(200):
        init = Init(
            x=(30.0, 30.0 + 2.0 * (k % 5)),
            y=(45.0, 45.0 + sep),
            v=((3.0, 0.0), (3.0, 0.0)),
        )
        ep = run(SimConfig(steps=600, noise=noise), k, init=init)
        tol = max(noise, 1e-4)
        if not consistent_worlds(ep.observable_log(), tol):
            continue
        try:
            truth_matches(ep)
        except ValueError:
            continue
        eps.append(ep)
        if len(eps) >= n:
            break
    return eps


def best_statistic(eps, tol: float) -> float:
    survey = statistic_survey(eps, tol=tol)
    covered = [
        survey[name]["top1"]
        for name in ("y_residual", "x_residual", "y_order", "speed_delta", "v_bounce")
        if survey[name]["decided"] == survey["episodes"]
    ]
    return max(covered) if covered else float("nan")


def main() -> int:
    cells = [(sep, 2.0) for sep in (2.0, 4.0, 6.0, 10.0, 18.0)]
    cells += [(6.0, noise) for noise in (0.5, 1.0, 2.0, 3.0, 6.0)]
    cells += [(2.0, 6.0), (2.0, 8.0)]  # P2: r = 0.33 and 0.25
    print("| sep/noise | r | episodes | worlds mean | exact Bayes decided/tie/empty | "
          "top1 | MAP top1 | A2 pos top1 | best stat | chance |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for sep, noise in cells:
        eps = corpus(sep, noise)
        if not eps:
            print(f"| {sep:g}/{noise:g} | {sep / noise:.2f} | no attributable episodes | - | - | - | - | - | - | - |")
            continue
        tol = max(noise, 1e-4)
        worlds = [len(consistent_worlds(ep.observable_log(), tol)) for ep in eps]
        bayes = m2_bayes_accuracy(eps, noise=noise, tol=tol)
        mp = m2_map_accuracy(eps, noise=noise, tol=tol)
        pos = m2_position_continuity(eps, tol=tol)
        print(
            f"| {sep:g}/{noise:g} | {sep / noise:.2f} | {len(eps)} | "
            f"{sum(worlds) / len(worlds):.2f} | "
            f"{bayes['decided']}/{bayes['tied']}/{bayes.get('empty', 0)} | "
            f"{bayes['top1']:.2f} | {mp['top1']:.2f} | {pos['top1']:.2f} | "
            f"{best_statistic(eps, tol):.2f} | {1.0 / (sum(worlds) / len(worlds)):.2f} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
