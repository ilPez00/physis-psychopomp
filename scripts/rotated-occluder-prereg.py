"""R-P1.33 — rotated occluders: membership survives, the rect estimator is tested.

Prereg: docs/2026-11-22-PREREG-R-P1.33-rotated-occluders.md, registered before
this script existed (claim registered before the run).

A diamond occluder sits outside the rectangle, so its bounding box contains four
corner points that are **not** blind. The membership law should predict all six
task points exactly; a bounding-box rule should fail on the corners. The rect
estimator of R-P1.29 is then asked what it makes of the same geometry, and the
sign of its errors is reported — that is where the one-signed optimism of the last
four cards may stop being true.

Usage: .venv/bin/python scripts/rotated-occluder-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import is_blind, predict_identifiable
from psychopomp.perspective import transform_scene
from psychopomp.selfmodel import estimate_blind_region
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, run

T_STAR, DT, STEPS = 90, 0.1, 200
O = (40.0, 60.0, 35.0, 65.0)
O2 = (30.0, 92.0, 20.0, 90.0)
DIAMOND = ((75.0, 42.0), (83.0, 50.0), (75.0, 58.0), (67.0, 50.0))
BBOX = (67.0, 83.0, 42.0, 58.0)
POINTS = ((75.0, 50.0), (69.0, 44.0), (81.0, 44.0), (69.0, 56.0), (81.0, 56.0), (64.0, 50.0))
CORNERS = POINTS[1:5]
STEP = 0.3
PARKED = (3.0, 97.0)


def cfg(poly=DIAMOND, drift: float = 0.0) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, poly_o=(poly,) if poly else (),
                     o2_velocity=(drift, 0.0))


def measure(point, drift: float = 0.0) -> bool:
    """One body per task point: start left of `o`, reach the point exactly at t*."""
    x, y = point
    start = 5.0
    speed = (x - start) / (DT * T_STAR)
    config = cfg(drift=drift)
    init = Init(x=(start, PARKED[0]), y=(y, PARKED[1]), v=((speed, 0.0), (0.0, 0.0)))
    if not (2.0 <= speed <= 20.0):
        raise SystemExit(f"unreachable task point {point} at speed {speed}")
    true = Intervention(t=T_STAR, ball=0, dv=(0.0, 1.5))
    ep = run(config, 0, episode=0, init=init, kicks=(Kick(T_STAR, 0, (0.0, 1.5)),))
    at = (ep.trajs[0].x[T_STAR], ep.trajs[0].y[T_STAR])
    if abs(at[0] - x) > 1e-6 or abs(at[1] - y) > 1e-6:
        raise SystemExit(f"body did not reach its task point: {point} vs {at}")
    out = attribute(ep, [true, None], config, 0, init)
    return bool(out["unique"] and out["best"] is true)


def bbox_rule(point, drift: float = 0.0) -> bool:
    """The naive alternative: treat the diamond as its bounding rectangle."""
    x, y = point
    return not (inside_rect(O, x, y) or inside_rect(BBOX, x, y))


def main() -> int:
    print("| point | law | bbox rule | measured |")
    print("|---|---|---|---|")
    rows = {}
    for point in POINTS:
        law_pred = predict_identifiable(cfg(), point, 0)
        bbox_pred = bbox_rule(point)
        measured = measure(point)
        rows[point] = {"law": law_pred, "bbox": bbox_pred, "measured": measured}
        print(f"| {point} | {'unique' if law_pred else 'tie'} | "
              f"{'unique' if bbox_pred else 'tie'} | {'unique' if measured else 'tie'} |")

    p1 = all(r["law"] == r["measured"] for r in rows.values())
    bbox_errors = [p for p, r in rows.items() if r["bbox"] != r["measured"]]
    p2 = all(p in bbox_errors for p in CORNERS) and len(bbox_errors) >= 4

    # P3: rotate the whole scene 180 degrees (polygon and bodies together)
    invariance = True
    for point in POINTS:
        scene_cfg, scene_init, _ = transform_scene(
            cfg(), Init(x=(5.0, PARKED[0]), y=(point[1], PARKED[1]),
                        v=(((point[0] - 5.0) / (DT * T_STAR), 0.0), (0.0, 0.0))),
            None, "rot180")
        moved = (100.0 - point[0], 100.0 - point[1])
        law_here = predict_identifiable(cfg(), point, 0)
        law_there = predict_identifiable(scene_cfg, moved, 0)
        invariance &= law_here == law_there
    p3 = invariance

    # P4: what does the rect estimator make of a diamond?
    corpus = []
    for i, (lane, startx, v) in enumerate(((44.0, 10.0, 3.0), (50.0, 10.0, 3.0),
                                           (56.0, 95.0, -3.0), (50.0, 95.0, -3.0))):
        corpus.append(run(SimConfig(steps=400, o=O, o2=O2, poly_o=(DIAMOND,)), 0,
                          episode=i, init=Init(x=(startx, PARKED[0]), y=(lane, PARKED[1]),
                                               v=((v, 0.0), (0.0, 0.0)))))
    for i, (column, starty, v) in enumerate(((75.0, 10.0, 3.0), (75.0, 95.0, -3.0))):
        corpus.append(run(SimConfig(steps=400, o=O, o2=O2, poly_o=(DIAMOND,)), 0,
                          episode=20 + i, init=Init(x=(column, PARKED[0]),
                                                    y=(starty, PARKED[1]),
                                                    v=((0.0, v), (0.0, 0.0)))))
    est = estimate_blind_region(corpus, STEP)
    side_counts = {"sided": 0, "sweep": 0}
    for ep in corpus:
        for event in ep.observable_log():
            if event.kind in ("enter_occ", "exit_occ"):
                if event.attrs.get("side") == "sweep":
                    side_counts["sweep"] += 1
                else:
                    side_counts["sided"] += 1
    est_rect = est.as_rect()
    pessimistic = []
    if est_rect is not None:
        for point in CORNERS:
            est_blind = inside_rect(est_rect, point[0], point[1])
            truth_blind = is_blind(cfg(), point, 0)
            if est_blind and not truth_blind:
                pessimistic.append(point)
    p4 = bool(pessimistic)

    print()
    print(f"estimator: {est_rect} (truth has the diamond {DIAMOND})")
    print(f"crossing labels in the corpus: {side_counts}")
    print(f"P1 membership law matches the instrument on all six points: "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 the bounding box fails on the corners "
          f"({len(bbox_errors)} errors): {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 scene covariance holds for polygons: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 the rect estimator makes PESSIMISTIC errors on corners "
          f"({pessimistic}): {'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
