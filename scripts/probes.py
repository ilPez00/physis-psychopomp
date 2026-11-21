"""Pre-GPU probe baselines: M2 (world ranking) and M3 (contact detection).

Prints the stupid-control numbers a learned model must beat.

Usage: .venv/bin/python scripts/probes.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.fixtures import random_corpus, targeted_corpus
from psychopomp.probes import m2_baseline, m3_accuracy


def main() -> int:
    rnd = random_corpus(8)
    tgt = targeted_corpus(6)
    for name, eps in (("random", rnd), ("targeted", tgt)):
        m2 = m2_baseline(eps)
        m3 = m3_accuracy(eps)
        m3s = m3_accuracy(eps, shuffled=True)
        print(
            f"[{name}] episodes {len(eps)}  worlds_mean {m2['worlds_mean']:.2f}  "
            f"M2 top1 {m2['top1']:.2f} (chance {m2['chance']:.2f})  "
            f"M3 acc {m3:.2f}  shuffled {m3s:.2f}  "
            f"excluded {m2['excluded_ambiguous_truth']}"
        )
    print("M2 note: endpoint-only ranking is a coin flip on relabeling-symmetric worlds;")
    print("a model must beat this using pre-contact history, not endpoints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
