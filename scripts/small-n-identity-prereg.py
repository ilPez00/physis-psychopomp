"""R-P1.41 — the identity formula where it discriminates (small N).

Prereg: docs/2026-11-22-PREREG-R-P1.41-small-N.md, registered before this run.

R-P1.40 was vacuous: N=56 saturates 1-(1-p)^N for every p. Here N is 1, 2 and 3,
so the exponent is visible. Identity is resolvable iff at least one marker fired.

Usage: .venv/bin/python scripts/small-n-identity-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.sim import Init, SimConfig, run

WORLD = {"o": (40.0, 60.0, 35.0, 65.0), "o2": (46.0, 54.0, 35.0, 65.0)}
BODIES = (((20.0, 45.0), (3.0, 0.0)), ((80.0, 51.0), (-3.0, 0.0)))
PS = (1.0, 0.6, 0.3, 0.0)
CELLS = (("A", 5), ("B", 15), ("C", 25))
REALIZATIONS = 400


def episode(steps: int, p: float, realization: int, swapped: bool = False):
    a, b = BODIES if not swapped else (BODIES[1], BODIES[0])
    cfg = SimConfig(steps=steps, o=WORLD["o"], o2=WORLD["o2"],
                    identity_marker=True, marker_period=10, marker_reliability=p)
    return run(cfg, 0, episode=realization,
               init=Init(x=(a[0][0], b[0][0]), y=(a[0][1], b[0][1]), v=(a[1], b[1])))


def log_set(ep):
    return sorted((e.kind, e.t, tuple(sorted(e.attrs.items())))
                  for e in ep.observable_log())


def n_opportunities(steps: int) -> int:
    return sum(1 for e in episode(steps, 1.0, 0).observable_log() if e.kind == "marker")


def measured(steps: int, p: float) -> float:
    differ = 0
    for r in range(REALIZATIONS):
        if log_set(episode(steps, p, r)) != log_set(episode(steps, p, r, True)):
            differ += 1
    return differ / REALIZATIONS


def main() -> int:
    measured_n = {label: n_opportunities(steps) for label, steps in CELLS}
    print(f"opportunities per cell: {measured_n}")
    rows = {}
    print("| cell | N | p | predicted 1-(1-p)^N | measured |")
    print("|---|---|---|---|---|")
    for label, steps in CELLS:
        n = measured_n[label]
        for p in PS:
            m = measured(steps, p)
            predicted = 1.0 - (1.0 - p) ** n
            rows[(label, p)] = {"N": n, "predicted": predicted, "measured": m}
            print(f"| {label} | {n} | {p:.1f} | {predicted:.3f} | {m:.3f} |")

    s1 = all(abs(r["measured"] - r["predicted"]) <= 0.06 for r in rows.values())
    s2 = all(abs(rows[("A", p)]["measured"] - p) <= 0.05 for p in (1.0, 0.6, 0.3)) and \
        rows[("A", 0.0)]["measured"] == 0.0
    s3 = len(set(measured_n.values())) == len(CELLS) and \
        sorted(measured_n.values()) == [1, 2, 3]
    s4 = all(
        rows[("C", p)]["measured"] - rows[("A", p)]["measured"]
        >= (1.0 - p) - (1.0 - p) ** 3 - 0.06
        for p in (0.6, 0.3)
    )

    print()
    print(f"S1 small-N formula within 0.06: {'UPHELD' if s1 else 'FALSIFIED'}")
    print(f"S2 N=1 is linear in p: {'UPHELD' if s2 else 'FALSIFIED'}")
    print(f"S3 the cells really differ in N: {'UPHELD' if s3 else 'FALSIFIED'}")
    print(f"S4 more opportunities help by the predicted amount: "
          f"{'UPHELD' if s4 else 'FALSIFIED'}")
    ok = all((s1, s2, s3, s4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
