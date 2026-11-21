"""Where does the deterministic identity probe die? Evidence for an A3 task.

A2 showed the boundary position decides identity perfectly at full precision.
A learned arm only has headroom once that signal is degraded, so this prints
top-1 as the observation is coarsened. Nothing here is a registered claim.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.fixtures import parallel_recrossing_corpus
from psychopomp.probes import m2_position_continuity

UNITS = [0.01, 2.0, 5.0, 8.0, 10.0, 20.0]


def main() -> int:
    eps = parallel_recrossing_corpus(6)
    if not eps:
        print("no attributable 4-world episodes found; nothing to measure")
        return 2
    print(f"[parallel x2] episodes {len(eps)}  chance 0.25")
    print("| q (units) | grid top-1 | jitter top-1 | scored | excluded |")
    print("|---|---|---|---|---|")
    for q in UNITS:
        grid = m2_position_continuity(eps, quantize=q)
        noisy = m2_position_continuity(eps, jitter=q)
        print(
            f"| {q:g} | {grid['top1']:.2f} | {noisy['top1']:.2f} | "
            f"{noisy['episodes']} | {noisy['excluded']} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
