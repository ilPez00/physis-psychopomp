"""R-P1.10 — preregistered generalisation run for the multi-observer claim.

Prereg: docs/2026-11-22-PREREG-R-P1.10-multi-observer-claim.md (registered
before this script existed). 5 seeds x 5 observer sets, dose-response ordering,
permuted-score control, ceiling rule.

Usage: .venv/bin/python scripts/multi-observer-prereg.py
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

TRUE = Intervention(t=60, ball=0, dv=(0.0, 1.5))     # inside o for every seed
DECOY = Intervention(t=30, ball=0, dv=(0.0, 1.5))    # body visible everywhere
CANDIDATES = [TRUE, None, DECOY]
SEEDS = (24.0, 26.0, 28.0, 30.0, 32.0)               # x0; ball 0 x(60) = x0+18
STEPS = 200
CONTROL_DRAWS = 200

OBSERVER_SETS = [
    ("single", None),
    ("same", (40.0, 60.0, 35.0, 65.0)),
    ("overlap-450", (45.0, 65.0, 35.0, 65.0)),
    ("overlap-300", (50.0, 70.0, 35.0, 65.0)),
    ("disjoint", (0.0, 20.0, 0.0, 20.0)),
]


def init_for(x0: float) -> Init:
    return Init(x=(x0, x0 + 4.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))


def control_recovery(out, rng) -> float:
    """Shuffle score values across the candidates; how often does the truth win?"""
    scores = [d for d, _ in out["scores"]]
    hyps = [h for _, h in out["scores"]]
    hits = 0
    for _ in range(CONTROL_DRAWS):
        perm = scores[:]
        rng.shuffle(perm)
        low = min(perm)
        # ties are real (that is the null-tie being measured): draw among them
        tied = [h for d, h in zip(perm, hyps) if d == low]
        hits += int(rng.choice(tied) is TRUE)
    return hits / CONTROL_DRAWS


def run_cell(label: str, o2, seed: float) -> dict:
    cfg = SimConfig(steps=STEPS, o2=o2)
    init = init_for(seed)
    ep = run(cfg, int(seed), init=init, kicks=(Kick(TRUE.t, TRUE.ball, TRUE.dv),))
    out = attribute(ep, CANDIDATES, cfg, int(seed), init)
    d = {str(h): dist for dist, h in out["scores"]}
    total = sum(len(t.visible) for t in ep.trajs)
    hidden = sum(sum(1 for v in t.visible if not v) for t in ep.trajs)
    return {
        "observer_set": label,
        "seed": seed,
        "unique_correct": bool(out["unique"] and out["best"] is TRUE),
        "ambiguity": len(out["ambiguity"]),
        "margin": out["margin"],
        "d_true": d[str(TRUE)],
        "d_null": d[str(None)],
        "hidden_step_fraction": hidden / total,
        "skipped_kicks": len(ep.skipped_kicks),
        "control": control_recovery(out, random.Random(int(seed * 31 + 7))),
    }


def main() -> int:
    rng = random.Random(20261122)
    rows = []
    print("| observer set | seed x0 | unique | ambiguity | margin | d(true) | d(null) | hidden frac | control |")
    print("|---|---|---|---|---|---|---|---|---|")
    for label, o2 in OBSERVER_SETS:
        for seed in SEEDS:
            row = run_cell(label, o2, seed)
            rows.append(row)
            print(f"| {label} | {seed:.0f} | {'YES' if row['unique_correct'] else 'no'} | "
                  f"{row['ambiguity']} | {row['margin']:.2f} | {row['d_true']:.2f} | "
                  f"{row['d_null']:.2f} | {row['hidden_step_fraction']:.3f} | "
                  f"{row['control']:.3f} |")

    def cell(label: str) -> list:
        return [r for r in rows if r["observer_set"] == label]

    def rate(label: str) -> int:
        return sum(r["unique_correct"] for r in cell(label))

    ceiling = [r for r in cell("single") if r["unique_correct"]]
    strict = ["overlap-450", "overlap-300", "disjoint"]

    h1 = all(rate(c) == len(SEEDS) for c in strict) and rate("single") <= 1 and rate("same") <= 1
    h2 = all(
        (a["unique_correct"], a["ambiguity"], a["d_true"], a["d_null"])
        == (b["unique_correct"], b["ambiguity"], b["d_true"], b["d_null"])
        for a, b in zip(cell("single"), cell("same"))
    )
    order = [rate(c) for c, _ in OBSERVER_SETS]
    hidden_order = [cell(c)[0]["hidden_step_fraction"] for c, _ in OBSERVER_SETS]
    h3 = (all(x <= y for x, y in zip(order, order[1:])) and any(x < y for x, y in zip(order, order[1:]))
          and all(x >= y for x, y in zip(hidden_order, hidden_order[1:]))
          and hidden_order[0] > hidden_order[-1] and hidden_order[1] == hidden_order[0])
    h4 = all(abs(r["control"] - 1 / 3) <= 0.15 for r in rows)

    print()
    print(f"ceiling exclusions (single already unique): {len(ceiling)}/{len(SEEDS)}")
    print(f"unique-correct per observer set {dict((c, rate(c)) for c, _ in OBSERVER_SETS)} of {len(SEEDS)}")
    print(f"hidden step fraction per set {dict((c, round(hidden_order[i], 3)) for i, (c, _) in enumerate(OBSERVER_SETS))}")
    print()
    print(f"H1 main claim (5/5 strict coverage, <=1/5 no gain): {'SUPPORTED' if h1 else 'FALSIFIED'}")
    print(f"H2 observer count alone does nothing (same == single): {'SUPPORTED' if h2 else 'FALSIFIED'}")
    print(f"H3 dose-response monotone in blind area: {'SUPPORTED' if h3 else 'FALSIFIED'}")
    print(f"H4 permuted-score control at chance (1/3 +-0.15): {'SUPPORTED' if h4 else 'FALSIFIED'}")
    ok = all((h1, h2, h3, h4))
    print("prereg run:", "PASS" if ok else "FAIL")
    _ = rng
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
