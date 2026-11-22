"""R-P1.13 — does the per-event coverage rule survive observation noise?

Prereg: docs/2026-11-22-PREREG-R-P1.13-coverage-under-noise.md (registered
before this script existed).

Two event locations in one geometry (one covered by the blind region, one not),
five noise levels, 20 noise realizations each. Each candidate is re-simulated on
its OWN noise stream, so the observation's corruption is never inherited by the
truth. The shared-stream column is kept only to show the defect that fix
removes.

Metric: rank accuracy = fraction of realizations where d(true) < d(null).
Chance = 0.5 with two candidates.

Usage: .venv/bin/python scripts/coverage-under-noise.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute, motion_distance, signature
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

O2 = (40.5, 60.5, 35.0, 65.0)
LANES = (45.0, 51.0)
T, DV, STEPS = 60, (0.0, 1.5), 200
SIGMAS = (0.0, 0.1, 0.2, 0.3, 0.5)
REALIZATIONS = 20
CELLS = [("uncovered", 19.0), ("covered", 31.0)]   # event x = 37.0 / 49.0
TRUE = Intervention(t=T, ball=0, dv=DV)


def init_for(x0: float) -> Init:
    return Init(x=(x0, x0 + 4.0), y=LANES, v=((3.0, 0.0), (3.0, 0.0)))


def measure(x0: float, sigma: float) -> dict:
    cfg = SimConfig(steps=STEPS, noise=sigma, o2=O2)
    init = init_for(x0)
    rank_hits = unique_hits = shared_hits = 0
    d_true = d_null = 0.0
    for episode in range(REALIZATIONS):
        ep = run(cfg, 0, episode=episode, init=init, kicks=(Kick(T, 0, DV),))
        obs = signature(ep)
        cands = [TRUE, None]
        out = attribute(ep, cands, cfg, 0, init)
        scores = {str(h): d for d, h in out["scores"]}
        rank_hits += int(scores[str(TRUE)] < scores[str(None)])
        unique_hits += int(out["unique"] and out["best"] is TRUE)
        d_true += scores[str(TRUE)]
        d_null += scores[str(None)]
        # the defect: every candidate on the OBSERVATION's own stream
        shared = [
            motion_distance(obs, signature(run(cfg, 0, episode=episode, init=init,
                                               kicks=(Kick(T, 0, DV),) if h else (),
                                               noise_stream=0)))
            for h in (True, False)
        ]
        shared_hits += int(shared[0] < shared[1])
    n = REALIZATIONS
    return {
        "rank_accuracy": rank_hits / n,
        "unique_rate": unique_hits / n,
        "shared_stream_accuracy": shared_hits / n,
        "d_true": d_true / n,
        "d_null": d_null / n,
    }


def main() -> int:
    rows = {}
    print("| cell | sigma | rank acc | unique rate | d(true) | d(null) | shared-stream acc |")
    print("|---|---|---|---|---|---|---|")
    for label, x0 in CELLS:
        for sigma in SIGMAS:
            r = measure(x0, sigma)
            rows[(label, sigma)] = r
            print(f"| {label} | {sigma:.1f} | {r['rank_accuracy']:.2f} | "
                  f"{r['unique_rate']:.2f} | {r['d_true']:.2f} | {r['d_null']:.2f} | "
                  f"{r['shared_stream_accuracy']:.2f} |")

    unc = [rows[("uncovered", s)] for s in SIGMAS]
    cov = [rows[("covered", s)] for s in SIGMAS]

    p1 = (rows[("uncovered", 0.3)]["shared_stream_accuracy"] == 1.0
          and rows[("uncovered", 0.3)]["rank_accuracy"] < 1.0)
    p2 = all(abs(r["rank_accuracy"] - 0.5) <= 0.15 for r in cov[1:])
    acc = [r["rank_accuracy"] for r in unc]
    p3 = (acc[0] > 0.5 and acc[1] > 0.5 and acc[2] > 0.5
          and all(x >= y for x, y in zip(acc, acc[1:])))
    p4 = (unc[0]["unique_rate"] == 1.0 and cov[0]["unique_rate"] == 0.0)

    print()
    print(f"P1 shared-stream artifact reproduced, independent stream not: "
          f"{'UPHELD' if p1 else 'FALSIFIED'} "
          f"(shared {rows[('uncovered', 0.3)]['shared_stream_accuracy']:.2f}, "
          f"independent {rows[('uncovered', 0.3)]['rank_accuracy']:.2f})")
    print(f"P2 covered cell at chance for sigma >= 0.1: {'UPHELD' if p2 else 'FALSIFIED'} "
          f"({[round(r['rank_accuracy'], 2) for r in cov[1:]]})")
    print(f"P3 uncovered cell above chance at sigma <= 0.2 and non-increasing: "
          f"{'UPHELD' if p3 else 'FALSIFIED'} ({[round(a, 2) for a in acc]})")
    print(f"P4 sigma=0 reproduces the exact rule: {'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
