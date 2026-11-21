"""R-P1.3 degradation matrix (plan: 2026-11-21 PLAN-R-P1.3).

Same operating point as R-P1.1 (sep=6, noise=1), two frames, camera-layer
degradations applied AFTER the frame change: quantization, independent jitter,
and dropping every auxiliary event. Reports where the observable frontier
actually moves, per frame.

Usage: .venv/bin/python scripts/degradation-matrix.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.camera import CameraView, degrade
from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import parallel_lane_corpus, truth_matches
from psychopomp.perspective import random_frame, transform_observable, world_frame
from psychopomp.probes import m2_bayes_accuracy, m2_position_continuity

NOISE = 1.0
CELLS = [
    ("baseline", 0.0, 0.0, 0.0),
    ("q=0.5", 0.5, 0.0, 0.0),
    ("q=1", 1.0, 0.0, 0.0),
    ("q=2", 2.0, 0.0, 0.0),
    ("q=4", 4.0, 0.0, 0.0),
    ("j=0.5", 0.0, 0.5, 0.0),
    ("j=1", 0.0, 1.0, 0.0),
    ("j=2", 0.0, 2.0, 0.0),
    ("j=3", 0.0, 3.0, 0.0),
    ("j=4", 0.0, 4.0, 0.0),
    ("q=1 j=0.5", 1.0, 0.5, 0.0),
    ("drop-aux=all", 0.0, 0.0, 1.0),
]


def main() -> int:
    eps = parallel_lane_corpus()
    tol = max(NOISE, 1e-4)
    print(f"corpus: parallel lanes sep=6 noise={NOISE:g}, episodes {len(eps)}")
    print("| frame | cell | worlds mean | Bayes decided/tie | Bayes top1 | A2 pos top1 | truth-in-worlds |")
    print("|---|---|---|---|---|---|---|")
    for fname, frame in (("world", world_frame()), ("random:1", random_frame(1))):
        for label, q, j, d in CELLS:
            # true error support = sensor + quantization + jitter (all bounded
            # uniform): the filter tolerance and the Bayes model must use the
            # summed support, or cells read as "no consistent world" when they
            # are only under-toleranced.
            eff = max(NOISE + q + j, 1e-4)
            views = [
                CameraView(ep, degrade(transform_observable(ep, frame),
                                       quantize_unit=q, jitter_magnitude=j,
                                       drop_rate=d, seed=7))
                for ep in eps
            ]
            worlds = [len(consistent_worlds(v.observable_log(), eff)) for v in views]
            bayes = m2_bayes_accuracy(views, noise=eff, tol=eff)
            pos = m2_position_continuity(views, tol=eff)
            inside = sum(
                1
                for ep, v in zip(eps, views)
                if any(w.matches == truth_matches(ep) for w in consistent_worlds(v.observable_log(), eff))
            )
            print(
                f"| {fname} | {label} | {sum(worlds) / len(worlds):.2f} | "
                f"{bayes['decided']}/{bayes['tied']} | {bayes['top1']:.2f} | "
                f"{pos['top1']:.2f} | {inside}/{len(eps)} |"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
