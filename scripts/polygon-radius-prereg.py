"""R-P1.45 — partial visibility for polygonal occluders.

Prereg: docs/2026-11-23-PREREG-R-P1.45-polygon-radius.md (amendment 1), claim 5d07b83d
registered before the run.

A body is fully hidden by a polygon only when its whole disc is inside, so the point
predicate over-predicts in a band of width r along each slanted edge. The repair is an
inward erosion of the polygon by r, computed here as the intersection of edges shifted
inward — exact for a convex polygon.

Usage: .venv/bin/python scripts/polygon-radius-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.law import predict_identifiable
from psychopomp.sim import (SimConfig, inside_polygon, observable,
                            polygon_boundary_distance)

O = (40.0, 60.0, 35.0, 65.0)
O2 = (30.0, 92.0, 20.0, 90.0)
DIAMOND = ((75.0, 42.0), (83.0, 50.0), (75.0, 58.0), (67.0, 50.0))
RADII = (0.0, 0.5, 1.0)
POINTS = (("centre", 75.0), ("inner", 82.0), ("band", 82.6), ("vertex", 83.0),
          ("outside", 64.0))
LANE = 50.0


def cfg(r: float) -> SimConfig:
    return SimConfig(o=O, o2=O2, poly_o=(DIAMOND,), visual_radius=r)


def eroded_diamond(r: float):
    """Inward offset of a convex polygon: shift each edge by r along its normal."""
    n = len(DIAMOND)
    cx = sum(p[0] for p in DIAMOND) / n
    cy = sum(p[1] for p in DIAMOND) / n
    import math
    half = []           # (normal pointing inward, offset)
    for i in range(n):
        x0, y0 = DIAMOND[i]
        x1, y1 = DIAMOND[(i + 1) % n]
        nx, ny = -(y1 - y0), (x1 - x0)
        norm = math.hypot(nx, ny)
        nx, ny = nx / norm, ny / norm
        if nx * (cx - x0) + ny * (cy - y0) < 0:      # make it point inward
            nx, ny = -nx, -ny
        half.append(((nx, ny), nx * x0 + ny * y0 + r))
    return half


def eroded_inside(r: float, x: float, y: float) -> bool:
    if r <= 0.0:
        return inside_polygon(DIAMOND, x, y)
    return all(nx * x + ny * y >= d for (nx, ny), d in eroded_diamond(r))


def main() -> int:
    rows = {}
    print("| r | point | law says | eroded says | instrument | law wrong? | boundary dist |")
    print("|---|---|---|---|---|---|---|")
    for r in RADII:
        for label, x in POINTS:
            law = predict_identifiable(cfg(0.0), (x, LANE), 0)   # point-based predicate
            ero = not eroded_inside(r, x, LANE)
            inst = observable(cfg(r), x, LANE)
            dist = (polygon_boundary_distance(DIAMOND, x, LANE)
                    if inside_polygon(DIAMOND, x, LANE) else None)
            rows[(r, label)] = {"law": law, "eroded": ero, "inst": inst,
                                "wrong": law != inst, "dist": dist}
            print(f"| {r} | {label} ({x}) | {'unique' if law else 'tie'} | "
                  f"{'unique' if ero else 'tie'} | {'seen' if inst else 'hidden'} | "
                  f"{'YES' if law != inst else 'no'} | "
                  f"{'-' if dist is None else f'{dist:.3f}'} |")

    p1 = rows[(0.5, "band")]["law"] is False and rows[(0.5, "band")]["inst"] is True
    p2 = all(rows[(0.5, k)]["law"] == rows[(0.5, k)]["inst"]
             for k in ("centre", "inner", "outside"))
    p3 = all(not rows[(0.0, k)]["wrong"] for k in ("centre", "inner", "band", "outside"))
    p4 = all(rows[(r, k)]["eroded"] == rows[(r, k)]["inst"]
             for r in RADII for k in ("centre", "inner", "band", "outside"))

    print()
    print(f"P1 band exists on a slanted edge: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 no misprediction away from the band: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 r=0 is the point model: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 inward erosion by r is exact on every point: "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
