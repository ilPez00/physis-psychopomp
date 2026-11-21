"""Where does the deterministic identity probe die? Evidence for an A3 task.

A2 showed the boundary position decides identity perfectly at full precision.
A learned arm only has headroom once that signal is degraded, so this prints
top-1 as the observation is coarsened. Nothing here is a registered claim.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import parallel_recrossing_corpus, truth_matches
from psychopomp.sim import Init, SimConfig, run
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
    print()
    print("World-level sensor noise (SimConfig.noise), filter tolerance set to")
    print("the sensor accuracy; corpus rebuilt per level:")
    print("| noise | episodes | worlds mean | top-1 | chance | decided/ambiguous | excluded |")
    print("|---|---|---|---|---|---|---|")
    for q in [0.0, 2.0, 5.0, 10.0, 20.0]:
        # The corpus builder insists on exactly four worlds, which is a
        # full-precision property; above 0 the velocity classes blur, so build
        # the episodes directly and report whatever world count the filter gives.
        noisy_eps = []
        for k in range(80):
            init = Init(x=(30.0, 30.0 + 2.0 * (k % 5)), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
            ep = run(SimConfig(steps=600, noise=q), k, init=init)
            tol = max(q, 1e-4)
            if not consistent_worlds(ep.observable_log(), tol):
                continue
            try:
                truth_matches(ep)
            except ValueError:
                continue
            noisy_eps.append(ep)
            if len(noisy_eps) >= 6:
                break
        if not noisy_eps:
            print(f"| {q:g} | 0 | - | - | - | - |")
            continue
        r = m2_position_continuity(noisy_eps, tol=max(q, 1e-4))
        worlds_mean = sum(len(consistent_worlds(e.observable_log(), max(q, 1e-4))) for e in noisy_eps) / len(noisy_eps)
        print(
            f"| {q:g} | {len(noisy_eps)} | {worlds_mean:.2f} | {r['top1']:.2f} | "
            f"{r['chance']:.2f} | {r['decided']}/{r['ambiguous']} | {r['excluded']} |"
        )
    print()
    print("Abstention trade-off at noise 20 (does a margin buy accuracy with coverage?):")
    print("| margin | decided | accuracy among decided |")
    print("|---|---|---|")
    heavyweight = []
    for k in range(80):
        init = Init(x=(30.0, 30.0 + 2.0 * (k % 5)), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
        ep = run(SimConfig(steps=600, noise=20.0), k, init=init)
        if not consistent_worlds(ep.observable_log(), 20.0):
            continue
        try:
            truth_matches(ep)
        except ValueError:
            continue
        heavyweight.append(ep)
        if len(heavyweight) >= 6:
            break
    for margin in (0.0, 1.0, 2.0, 5.0, 10.0):
        r = m2_position_continuity(heavyweight, tol=20.0, abstain_margin=margin)
        acc = r["top1"] / (r["decided"] / r["episodes"]) if r["decided"] else 0.0
        print(f"| {margin:g} | {r['decided']}/{r['episodes']} | {acc:.2f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
