"""Pre-GPU probe baselines: M2 (world ranking) and M3 (contact detection).

Prints the stupid-control numbers a learned model must beat.

Usage: .venv/bin/python scripts/probes.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.fixtures import parallel_recrossing_corpus, random_corpus, targeted_corpus
from psychopomp.probes import m2_baseline, m2_position_continuity, m3_accuracy


def main() -> int:
    rnd = random_corpus(8)
    tgt = targeted_corpus(6)
    for name, eps in (("random", rnd), ("targeted", tgt)):
        m2 = m2_baseline(eps)
        m3 = m3_accuracy(eps)
        m3s = m3_accuracy(eps, shuffled=True)
        a2 = m2_position_continuity(eps)
        print(
            f"[{name}] episodes {len(eps)}  worlds_mean {m2['worlds_mean']:.2f}  "
            f"M2 top1 {m2['top1']:.2f} (chance {m2['chance']:.2f})  "
            f"M3 acc {m3['accuracy']:.2f}  shuffled {m3s['accuracy']:.2f}  "
            f"excluded {m2['excluded_ambiguous_truth']} "
            f"(M3 scored {m3['scored']}, excluded {m3['excluded']})"
        )
        print(
            f"  A2 position-continuity: top1 {a2['top1']:.2f} "
            f"(chance {a2['chance']:.2f}, scored {a2['episodes']}, "
            f"excluded {a2['excluded']})"
        )
    twin = parallel_recrossing_corpus(6)
    e, a = m2_baseline(twin), m2_position_continuity(twin)
    print(
        f"[parallel x2] episodes {len(twin)}  endpoint top1 {e['top1']:.2f} "
        f"(chance {e['chance']:.2f})  A2 position top1 {a['top1']:.2f} "
        f"(chance {a['chance']:.2f})  excluded {a['excluded']}"
    )
    print("M2 note: endpoint-only ranking is a coin flip on relabeling-symmetric worlds;")
    print("the observable boundary position decides them (amendment A2), so a learned")
    print("model on this task must beat a deterministic 1.00, not a 0.25 coin flip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
