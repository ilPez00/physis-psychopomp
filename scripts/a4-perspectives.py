"""A4 — observer-relative possible worlds (preregistered 2026-11-21).

Arms: world-frame exact Bayes · frame-normalized exact Bayes (random frames
and a body frame, inertial only) · shuffled-exit control. A2 probe is reported
only as a reference at r >= 9, never compared across frames.

Cells are chosen for headroom: where the world-frame arm is already 1.00 the
cell is a ceiling and cannot support an "improvement" (prereg rule).

Usage: .venv/bin/python scripts/a4-perspectives.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.camera import CameraView, degrade
from psychopomp.controls import shuffle_rules
from psychopomp.epec import consistent_worlds, summarize
from psychopomp.fixtures import parallel_lane_corpus, truth_matches
from psychopomp.perspective import ball_frame, random_frame, transform_observable, world_frame
from psychopomp.probes import m2_bayes_accuracy

NOISE = 1.0
SEEDS = (1, 2, 3, 4, 5)
CELLS = [
    ("baseline", 0.0, 0.0),
    ("q=2", 2.0, 0.0),
    ("q=4", 4.0, 0.0),
    ("j=2", 0.0, 2.0),
    ("j=3", 0.0, 3.0),
]


def make_view(ep, frame, q, j):
    eff = max(NOISE + q + j, 1e-4)
    return CameraView(ep, degrade(transform_observable(ep, frame), quantize_unit=q,
                                  jitter_magnitude=j, seed=11)), eff


def main() -> int:
    eps = parallel_lane_corpus()
    frames = [("world", lambda ep: world_frame())]
    frames += [(f"random:{s}", (lambda s: lambda ep: random_frame(s))(s)) for s in SEEDS]
    frames += [("ball:0", lambda ep: ball_frame(ep, 0))]

    print("A4 run 1 — parallel lanes sep=6, sensor noise 1, 6 episodes")
    print("| cell | frame | decided | top1 | worlds | truth-in-worlds |")
    print("|---|---|---|---|---|---|")
    h1_cells = []
    h2_ok = True
    h3_ok = True
    world_top1: dict = {}
    frame_top1: dict = {}

    for label, q, j in CELLS:
        cell_best = 0.0
        for fname, mk in frames:
            views, eff = [], None
            for ep in eps:
                v, eff = make_view(ep, mk(ep), q, j)
                views.append(v)
            bayes = m2_bayes_accuracy(views, noise=eff, tol=eff)
            worlds = [len(consistent_worlds(v.observable_log(), eff)) for v in views]
            inside = sum(
                1 for ep, v in zip(eps, views)
                if any(w.matches == truth_matches(ep) for w in consistent_worlds(v.observable_log(), eff))
            )
            print(f"| {label} | {fname} | {bayes['decided']}/6 | {bayes['top1']:.2f} | "
                  f"{sum(worlds) / len(worlds):.2f} | {inside}/6 |")
            frame_top1[(label, fname)] = bayes["top1"]
            if fname == "world":
                world_top1[label] = bayes["top1"]
                base_worlds = worlds
                base_inside = inside
            else:
                if worlds != base_worlds or inside != base_inside:
                    h2_ok = False
            cell_best = max(cell_best, bayes["top1"])

        # shuffled-exit control on the world frame
        logs = [ep.observable_log() for ep in eps]
        shuf = shuffle_rules(logs, seed=999)
        sviews = []
        for ep, log in zip(eps, shuf):
            deg = degrade(log, quantize_unit=q, jitter_magnitude=j, seed=11)
            sviews.append(CameraView(ep, deg))
        eff = max(NOISE + q + j, 1e-4)
        sbayes = m2_bayes_accuracy(sviews, noise=eff, tol=eff)
        print(f"| {label} | shuffled-control | {sbayes['decided']}/6 | {sbayes['top1']:.2f} | - | - |")
        if sbayes["top1"] >= cell_best and cell_best > 0.0:
            h3_ok = False
        if world_top1[label] < 1.0 and cell_best > world_top1[label]:
            h1_cells.append(label)

    print()
    # Prereg rule: on a cell with headroom (world top1 < 1.0), H1 needs the
    # frame arm to beat the world arm on >= 2 of 5 seeds, mean improvement > 0.
    by_cell: dict = {}
    for (label, fname), value in frame_top1.items():
        if fname == "world":
            continue
        by_cell.setdefault(label, []).append(value)
    headroom = [c for c, w in world_top1.items() if w < 1.0]
    wins: dict = {}
    for label in headroom:
        beats = sum(1 for v in by_cell[label] if v > world_top1[label])
        gains = [v - world_top1[label] for v in by_cell[label] if v > world_top1[label]]
        wins[label] = (beats, sum(gains) / len(gains) if gains else 0.0)
    supported = [c for c, (beats, _) in wins.items() if beats >= 2]
    print(f"H1 frame-normalized beats world on cells with headroom: "
          f"{'SUPPORTED' if supported else 'FALSIFIED'} "
          f"(headroom cells: {headroom or 'none'}; "
          f"seed-beats per cell: {wins or 'none'})")
    print(f"H2 frames add no information (worlds and truth-in-worlds invariant): "
          f"{'UPHELD' if h2_ok else 'FALSIFIED'}")
    print(f"H3 shuffled control does not match the winning arm: {'UPHELD' if h3_ok else 'FALSIFIED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
