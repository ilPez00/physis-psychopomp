"""MAP ceiling over the enumerated worlds (round 8).

Answers: is the 0.67 plateau information loss or model error? MAP under a
Gaussian error assumption is the best decision these observables allow.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import truth_matches
from psychopomp.probes import m2_bayes_accuracy, m2_map_accuracy, statistic_survey
from psychopomp.sim import Init, SimConfig, run


def corpus(sep: float, noise: float, n: int = 6) -> list:
    eps = []
    for k in range(200):
        init = Init(x=(30.0, 30.0 + 2.0 * (k % 5)), y=(45.0, 45.0 + sep),
                    v=((3.0, 0.0), (3.0, 0.0)))
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


def main() -> int:
    print("| cell | best unfitted statistic | MAP (Gaussian surrogate) | exact Bayes (uniform) | chance |")
    print("|---|---|---|---|---|")
    for sep, noise in ((6.0, 2.0), (2.0, 2.0), (2.0, 5.0)):
        eps = corpus(sep, noise)
        if not eps:
            print(f"| {sep:g}/{noise:g} | no attributable episodes | - | - |")
            continue
        tol = max(noise, 1e-4)
        survey = statistic_survey(eps, tol=tol)
        covered = [
            survey[n]["top1"]
            for n in ("y_residual", "x_residual", "y_order", "speed_delta", "v_bounce")
            if survey[n]["decided"] == survey["episodes"]
        ]
        best_stat = max(covered) if covered else float("nan")
        oracle = m2_map_accuracy(eps, noise=noise, tol=tol)
        bayes = m2_bayes_accuracy(eps, noise=noise, tol=tol)
        print(f"| {sep:g}/{noise:g} | {best_stat:.2f} | {oracle['top1']:.2f} "
              f"(n={oracle['decided']}) | {bayes['top1']:.2f} "
              f"(n={bayes['decided']}, tie {bayes['tied']}, empty {bayes['empty']}) | "
              f"{bayes['chance']:.2f} |")
    print()
    print("MAP assumption: independent Gaussian error, sigma = noise/sqrt(12) (the SD")
    print("of the uniform sensor). Uniform noise ties under its exact likelihood, so")
    print("this is the best decision under a stated surrogate, not a proof of one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
