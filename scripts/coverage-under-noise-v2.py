"""R-P1.14 — coverage under noise, independent realizations per sigma.

Prereg: docs/2026-11-22-PREREG-R-P1.14-coverage-under-noise-v2.md, registered
before this script existed. Fixes R-P1.13's two design defects: the noise
realizations are independent per sigma (episode = 1000*sigma_index + r), and the
shared-stream defect is measured where it actually bites (the covered cell).

Usage: .venv/bin/python scripts/coverage-under-noise-v2.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute, motion_distance, signature
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

O2 = (40.5, 60.5, 35.0, 65.0)
T, DV, STEPS = 60, (0.0, 1.5), 200
SIGMAS = (0.0, 0.1, 0.2, 0.3, 0.5)
REALIZATIONS = 100
CELLS = [("uncovered", 19.0), ("covered", 31.0)]
TRUE = Intervention(t=T, ball=0, dv=DV)


def init_for(x0: float) -> Init:
    return Init(x=(x0, x0 + 4.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))


def measure(x0: float, sigma_index: int) -> dict:
    sigma = SIGMAS[sigma_index]
    cfg = SimConfig(steps=STEPS, noise=sigma, o2=O2)
    init = init_for(x0)
    rank_hits = unique_hits = shared_hits = 0
    d_true = d_null = 0.0
    for r in range(REALIZATIONS):
        episode = 1000 * sigma_index + r      # independent draws per sigma
        ep = run(cfg, 0, episode=episode, init=init, kicks=(Kick(T, 0, DV),))
        out = attribute(ep, [TRUE, None], cfg, 0, init)
        scores = {str(h): d for d, h in out["scores"]}
        rank_hits += int(scores[str(TRUE)] < scores[str(None)])
        unique_hits += int(out["unique"] and out["best"] is TRUE)
        d_true += scores[str(TRUE)]
        d_null += scores[str(None)]
        # the defect: every candidate on the observation's own noise stream
        obs = signature(ep)
        shared_true = signature(run(cfg, 0, episode=episode, init=init,
                                    kicks=(Kick(T, 0, DV),), noise_stream=0))
        shared_null = signature(run(cfg, 0, episode=episode, init=init,
                                    noise_stream=0))
        shared_hits += int(motion_distance(obs, shared_true)
                           < motion_distance(obs, shared_null))
    n = REALIZATIONS
    ratio = (d_null / d_true) if d_true > 0 else float("inf")
    return {
        "rank": rank_hits / n, "unique": unique_hits / n,
        "d_true": d_true / n, "d_null": d_null / n,
        "ratio": ratio, "shared": shared_hits / n,
    }


def main() -> int:
    rows = {}
    print("| cell | sigma | rank acc | 95% CI | unique | d(true) | d(null) | ratio | shared-stream acc |")
    print("|---|---|---|---|---|---|---|---|---|")
    for label, x0 in CELLS:
        for si, sigma in enumerate(SIGMAS):
            m = measure(x0, si)
            rows[(label, sigma)] = m
            ci = 1.96 * (m["rank"] * (1 - m["rank"]) / REALIZATIONS) ** 0.5
            print(f"| {label} | {sigma:.1f} | {m['rank']:.2f} | ±{ci:.2f} | "
                  f"{m['unique']:.2f} | {m['d_true']:.2f} | {m['d_null']:.2f} | "
                  f"{m['ratio']:.1f} | {m['shared']:.2f} |")

    unc = [rows[("uncovered", s)] for s in SIGMAS]
    cov = [rows[("covered", s)] for s in SIGMAS]

    # evaluated on sigma >= 0.1: at sigma=0 the covered cell is an exact tie by
    # construction (0.00), which is P4's control, not evidence about the stream
    p1 = (all(m["shared"] <= 0.15 for m in cov[1:])
          and all(abs(m["rank"] - 0.5) <= 0.1 for m in cov[1:]))
    p2 = all(abs(m["rank"] - 0.5) <= 0.10 for m in cov[1:])
    p3 = all(m["rank"] == 1.0 and m["ratio"] >= 10 for m in unc)
    p4 = unc[0]["unique"] == 1.0 and cov[0]["unique"] == 0.0
    spread = max(m["rank"] for m in cov[1:]) - min(m["rank"] for m in cov[1:])
    p5 = spread <= 0.15

    print()
    print(f"P1 shared-stream collapse vs independent chance for sigma >= 0.1 "
          f"(shared {[round(m['shared'], 2) for m in cov[1:]]} vs independent "
          f"{[round(m['rank'], 2) for m in cov[1:]]}): {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 covered cell at chance at every sigma >= 0.1 "
          f"{[round(m['rank'], 2) for m in cov[1:]]}: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 uncovered identifiable with ratio >= 10 "
          f"(ratios {[round(m['ratio'], 1) for m in unc]}): {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 sigma=0 reproduces the exact rule: {'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 covered cell shows no sigma trend (spread {spread:.2f}): "
          f"{'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
