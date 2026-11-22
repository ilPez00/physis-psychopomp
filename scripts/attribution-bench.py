"""R-P1.8 benchmark — counterfactual attribution over declared hypotheses.

Two case classes, because they answer different questions:

- asymmetric lanes (different speeds): which ball was kicked is observable, so
  the true hypothesis must win uniquely;
- symmetric lanes (identical bodies): kicking ball A and kicking ball B give
  the same identity-free observable multiset — the true hypothesis must be
  *in the ambiguity set*, and a unique answer would be a fabricated one.

Candidates: true · null · wrong sign · wrong time · hidden-time · small dv ·
large dv · wrong ball. Metric per class: unique top-1, truth-in-ambiguity,
mean ambiguity size, excluded (must be 0). Control: permuted candidate↔score
association must not recover the truth more often than chance.

Usage: .venv/bin/python scripts/attribution-bench.py
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

CFG = SimConfig(steps=200)
TRUE = Intervention(t=30, ball=0, dv=(0.0, 1.5))
CANDIDATES = [
    TRUE,
    None,
    Intervention(t=30, ball=0, dv=(0.0, -1.5)),
    Intervention(t=30, ball=1, dv=(0.0, 1.5)),
    Intervention(t=10, ball=0, dv=(0.0, 1.5)),
    Intervention(t=60, ball=0, dv=(0.0, 1.5)),   # hidden here: skipped
    Intervention(t=30, ball=0, dv=(0.0, 0.3)),
    Intervention(t=30, ball=0, dv=(0.0, 3.0)),
    Intervention(t=30, ball=1, dv=(0.0, -1.5)),
]
EPISODES = 12


def case(label: str, speeds: tuple[float, float]) -> None:
    rng = random.Random(4)
    unique = in_amb = excluded = control_hits = control_n = 0
    sizes = []
    margins = []
    for k in range(EPISODES):
        # x = 20 keeps ball 0 visible at t=30 (x = 29); a hidden true kick is
        # the ambiguity class, measured by the hidden-time candidate instead.
        init = Init(
            x=(20.0, 20.0 + 2.0 * (k % 5)),
            y=(45.0, 51.0),
            v=((speeds[0], 0.0), (speeds[1], 0.0)),
        )
        ep = run(CFG, k, init=init, kicks=(Kick(TRUE.t, TRUE.ball, TRUE.dv),))
        out = attribute(ep, CANDIDATES, CFG, k, init)
        unique += int(out["unique"] and out["best"] == TRUE)
        in_amb += int(TRUE in out["ambiguity"])
        excluded += int(TRUE not in out["ambiguity"])
        sizes.append(len(out["ambiguity"]))
        if out["unique"] and out["margin"] != float("inf"):
            margins.append(out["margin"])
        if out["unique"]:
            # break the candidate↔score association: shuffle score VALUES and
            # re-pair them with the candidate list
            scores = [d for d, _ in out["scores"]]
            rng.shuffle(scores)
            assigned = list(zip(scores, [h for _, h in out["scores"]]))
            control_n += 1
            control_hits += int(min(assigned, key=lambda p: (p[0], str(p[1])))[1] == TRUE)
    n = EPISODES
    print(f"[{label}] episodes {n}  candidates {len(CANDIDATES)}  chance {1/len(CANDIDATES):.3f}")
    print(f"  unique top-1: {unique}/{n}   truth-in-ambiguity: {in_amb}/{n}   "
          f"excluded (must be 0): {excluded}/{n}   mean ambiguity size: {sum(sizes)/n:.2f}")
    print(f"  margin (unique winners, mean): {sum(margins)/len(margins):.2f}"
          if margins else "  margin: none")
    print(f"  permuted-score control (unique episodes only): {control_hits}/{control_n}")
    return unique, in_amb, excluded, control_hits, control_n


def main() -> int:
    a = case("lanes 3.0/3.0 (equal bodies)", (3.0, 3.0))
    b = case("lanes 3.0/2.0 (different speeds)", (3.0, 2.0))
    ok = all(
        unique == EPISODES and excluded == 0 and control_hits <= 2
        for unique, in_amb, excluded, control_hits, control_n in (a, b)
    ) and all(in_amb == EPISODES for _, in_amb, _, _, _ in (a, b))
    print("bench:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
