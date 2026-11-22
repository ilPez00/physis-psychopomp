"""R-P1.16 — the crossing. R-P1.15 measured sigma 0.75..6 with no breakpoint;

Prereg: docs/2026-11-22-PREREG-R-P1.16-crossing.md, registered before this run.
Grid sigma in {10, 15, 20, 30, 40}, predicted from the R-P1.15 margin line
(25.4 - 0.85*sigma -> zero near sigma 30).

Breakpoint sigma* is the smallest sigma whose rank accuracy < 0.90 (defined in
the prereg, not here).

Usage: .venv/bin/python scripts/noise-envelope.py
"""
from __future__ import annotations

import statistics
import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

O2 = (40.5, 60.5, 35.0, 65.0)
T, DV, STEPS = 60, (0.0, 1.5), 200
SIGMAS = (10.0, 15.0, 20.0, 30.0, 40.0)
REALIZATIONS = 100
CELLS = [("uncovered", 19.0), ("covered", 31.0)]
TRUE = Intervention(t=T, ball=0, dv=DV)


def init_for(x0: float) -> Init:
    return Init(x=(x0, x0 + 4.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))


def measure(x0: float, sigma_index: int) -> dict:
    cfg = SimConfig(steps=STEPS, noise=SIGMAS[sigma_index], o2=O2)
    init = init_for(x0)
    hits = 0
    d_true, d_null = 0.0, 0.0
    for r in range(REALIZATIONS):
        ep = run(cfg, 0, episode=1000 * sigma_index + r, init=init,
                 kicks=(Kick(T, 0, DV),))
        out = attribute(ep, [TRUE, None], cfg, 0, init)
        s = {str(h): d for d, h in out["scores"]}
        hits += int(s[str(TRUE)] < s[str(None)])
        d_true += s[str(TRUE)]
        d_null += s[str(None)]
    n = REALIZATIONS
    return {"acc": hits / n, "d_true": d_true / n, "d_null": d_null / n}


def main() -> int:
    rows = {}
    print("| cell | sigma | rank acc | 95% CI | d(true) | d(null) | ratio |")
    print("|---|---|---|---|---|---|---|")
    for label, x0 in CELLS:
        for si, sigma in enumerate(SIGMAS):
            m = measure(x0, si)
            rows[(label, sigma)] = m
            ci = 1.96 * (m["acc"] * (1 - m["acc"]) / REALIZATIONS) ** 0.5
            ratio = (m["d_null"] / m["d_true"]) if m["d_true"] > 0 else float("inf")
            print(f"| {label} | {sigma:.2f} | {m['acc']:.2f} | ±{ci:.2f} | "
                  f"{m['d_true']:.2f} | {m['d_null']:.2f} | {ratio:.1f} |")

    unc = [rows[("uncovered", s)] for s in SIGMAS]
    cov = [rows[("covered", s)] for s in SIGMAS]

    xs = list(SIGMAS)
    ys = [m["d_true"] for m in unc]
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    k = (sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
         / sum((x - mean_x) ** 2 for x in xs))

    accs = [m["acc"] for m in unc]
    star = next((s for s, m in zip(SIGMAS, unc) if m["acc"] < 0.90), None)

    margins = [m["d_null"] - m["d_true"] for m in unc]
    mean_x, mean_m = statistics.mean(xs), statistics.mean(margins)
    mslope = (sum((x - mean_x) * (y - mean_m) for x, y in zip(xs, margins))
              / sum((x - mean_x) ** 2 for x in xs))
    zero = -mean_m / mslope if mslope != 0 else float("inf")

    p1 = -1.2 <= mslope <= -0.4 and 15.0 <= zero <= 60.0
    p2 = next(m["acc"] for s, m in zip(SIGMAS, unc) if s == 10.0) >= 0.90
    p3 = (next(m["acc"] for s, m in zip(SIGMAS, unc) if s == 40.0) < 0.70
          and all(a >= b for a, b in zip(accs, accs[1:])))
    p4 = star is not None and 15.0 <= star <= 40.0
    p5 = all(abs(m["acc"] - 0.5) <= 0.15 for m in cov)

    print()
    print(f"margin (d_null-d_true): {[round(m, 2) for m in margins]}; "
          f"slope {mslope:.3f}/unit, zero-crossing at sigma {zero:.1f}")
    print(f"breakpoint sigma* (first accuracy < 0.90) = {star}")
    print(f"P1 margin linear with zero-crossing in [15, 60]: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 accuracy >= 0.90 at sigma 10: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 accuracy < 0.70 at sigma 40 and non-increasing "
          f"{[round(a, 2) for a in accs]}: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 breakpoint in [15, 40]: {'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 covered cell stays at chance: {'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
