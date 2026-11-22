"""R-P1.34 — polygon estimation: where does the optimism come from?

Prereg: docs/2026-11-22-PREREG-R-P1.34-polygon-estimation.md, registered before
this script existed (claim registered before the run).

Polygon crossings are labelled with their edge and outward normal. Two rules are
compared on the same evidence: the tightest bound in the outside direction (the
rule that makes rectangles optimistic) and the tightest bound on the inside.

Usage: .venv/bin/python scripts/polygon-estimation-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.law import is_blind
from psychopomp.selfmodel import estimate_polygon_halfplanes, estimate_polygon_point_inside
from psychopomp.sim import Init, SimConfig, inside_polygon, run

O = (40.0, 60.0, 35.0, 65.0)
O2 = (30.0, 92.0, 20.0, 90.0)
DIAMOND = ((75.0, 42.0), (83.0, 50.0), (75.0, 58.0), (67.0, 50.0))
CENTRE = (75.0, 50.0)
CORNERS = ((69.0, 44.0), (81.0, 44.0), (69.0, 56.0), (81.0, 56.0))
STEP = 0.3
PARKED = (3.0, 97.0)


def true_offset(edge: int) -> float:
    """d for the half-plane `n·x <= d` of that edge, from the true diamond."""
    x0, y0 = DIAMOND[edge]
    x1, y1 = DIAMOND[(edge + 1) % len(DIAMOND)]
    nx, ny = -(y1 - y0), (x1 - x0)
    norm = (nx * nx + ny * ny) ** 0.5
    nx, ny = nx / norm, ny / norm
    cx = sum(v[0] for v in DIAMOND) / 4
    cy = sum(v[1] for v in DIAMOND) / 4
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    if nx * (mx - cx) + ny * (my - cy) < 0:
        nx, ny = -nx, -ny
    return nx * x0 + ny * y0


def corpus():
    eps = []
    # horizontal movers on three lanes, from both sides
    for i, lane in enumerate((44.0, 50.0, 56.0)):
        for j, (start, v) in enumerate(((10.0, 3.0), (95.0, -3.0))):
            eps.append(run(SimConfig(steps=400, o=O, o2=O2, poly_o=(DIAMOND,)), 0,
                           episode=10 * i + j,
                           init=Init(x=(start, PARKED[0]), y=(lane, PARKED[1]),
                                     v=((v, 0.0), (0.0, 0.0)))))
    # vertical movers through the diamond's waist, from both sides
    for j, (start, v) in enumerate(((10.0, 3.0), (95.0, -3.0))):
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, poly_o=(DIAMOND,)), 0,
                       episode=50 + j,
                       init=Init(x=(75.0, PARKED[0]), y=(start, PARKED[1]),
                                 v=((0.0, v), (0.0, 0.0)))))
    return eps


def main() -> int:
    episodes = corpus()
    raw = estimate_polygon_halfplanes(episodes, STEP, inner=False)
    inner = estimate_polygon_halfplanes(episodes, STEP, inner=True)

    print("| edge | true d | raw d | raw err | inner d | inner err | samples |")
    print("|---|---|---|---|---|---|---|")
    edges = sorted(set(raw) | set(inner))
    p1 = len(edges) == 4
    p2 = True
    p3 = True
    for edge in edges:
        d_true = true_offset(edge)
        d_raw = raw.get(edge, {}).get("offset")
        d_in = inner.get(edge, {}).get("offset")
        err_raw = None if d_raw is None else d_raw - d_true
        err_in = None if d_in is None else d_in - d_true
        samples = raw.get(edge, {}).get("samples", 0)
        print(f"| {edge} | {d_true:.2f} | "
              f"{'—' if d_raw is None else f'{d_raw:.2f}'} | "
              f"{'—' if err_raw is None else f'{err_raw:+.2f}'} | "
              f"{'—' if d_in is None else f'{d_in:.2f}'} | "
              f"{'—' if err_in is None else f'{err_in:+.2f}'} | {samples} |")
        if err_raw is not None:
            p2 &= err_raw >= -1e-9
            p1 &= abs(err_raw) <= STEP + 1e-9
        if err_in is not None:
            p3 &= err_in <= 1e-9
            p1 &= abs(err_in) <= STEP + 1e-9

    # P4: consequences for prediction
    points = (CENTRE,) + CORNERS
    truth = [is_blind(SimConfig(o=O, o2=O2, poly_o=(DIAMOND,)), p, 0) for p in points]
    inner_pred = [estimate_polygon_point_inside(inner, p) for p in points]
    raw_pred = [estimate_polygon_point_inside(raw, p) for p in points]
    p4 = inner_pred == truth
    raw_errors = [p for p, r, t in zip(points, raw_pred, truth) if r != t]

    print()
    print(f"edges observed: {len(edges)}; truth blind set: diamond at {DIAMOND}")
    print(f"inner rule predictions {inner_pred} vs truth {truth}")
    print(f"raw rule errors {raw_errors}")
    print(f"P1 all four edges, each within one step: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 raw rule over-covers on every edge (pessimistic): "
          f"{'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 inner rule under-covers on every edge (optimistic): "
          f"{'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 inner rule predicts centre and corners correctly (5/5): "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
