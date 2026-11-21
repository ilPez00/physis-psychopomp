"""Which observable statistics can rank the true world? Unfitted survey.

Round-6 evidence for the A3 decision: if no cheap statistic beats the y-residual
in the plateau cell, a learned arm has no observable handle there.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import truth_matches
from psychopomp.probes import statistic_survey
from psychopomp.sim import Init, SimConfig, run

NAMES = ("y_residual", "x_residual", "y_order", "speed_delta", "v_bounce", "borda", "vote")


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
    for sep, noise in ((6.0, 2.0), (2.0, 2.0), (2.0, 5.0)):
        eps = corpus(sep, noise)
        if not eps:
            print(f"sep {sep:g} noise {noise:g}: no attributable episodes")
            continue
        r = statistic_survey(eps, tol=max(noise, 1e-4))
        ratio = sep / noise if noise else float("inf")
        cells = "  ".join(
            f"{n} {r[n]['top1']:.2f} (n={r[n]['decided']})" for n in NAMES
        )
        print(f"sep {sep:g} noise {noise:g} ratio {ratio:.1f}: episodes {r['episodes']} "
              f"chance {r['chance']:.2f} | {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
