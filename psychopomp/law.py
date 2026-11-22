"""The identifiability law, consolidated (2026-11-22).

Eight preregistered cards reduced to one predicate:

    an intervention is identifiable from the observable log
    **iff** its event location at the event step is outside the blind region
    ``o ∩ o2(t)``, with the observer held fixed across counterfactuals.

Measured by R-P1.12 (30/30 out of sample), R-P1.16 (noise envelope), R-P1.17
(time-resolved coverage), R-P1.18 (frame covariance), R-P1.19/R-P1.20 (gravity,
hidden contacts, multi-contact) and R-P1.21 (self-model cost). Superseded
earlier statements and every falsified prediction are logged in ``docs/LAW.md``.

Validity conditions, measured not assumed:

- noise: 100/100 identification up to ``sigma = 6``; accuracy decays from 0.94 at
  ``sigma = 10`` to 0.61 at ``sigma = 40`` (breakpoint ``sigma* = 15``);
- geometry: axis-aligned rectangular occluders inside a square box, possibly
  several per observer (the blind set is then a union: non-convex, even
  disconnected — R-P1.25);
- observers: one or two, the second may translate at constant velocity;
- physics: constant velocity or constant acceleration, elastic equal-mass
  collisions; the *contact structure must be identical across hypotheses*
  (a kick that displaces a colliding body changes the world, not just the
  hypothesis);
- the predicate is decided by float arithmetic at the boundary: an event within
  1e-6 of a blind edge is *excluded*, never predicted (R-P1.11/R-P1.12).

Out of scope: rotated or curved occluders (would need polygon membership),
more than two observers,
observers whose motion depends on the world, degraded identity, learned
inference.
"""
from __future__ import annotations

import json
import sys
from typing import Optional, Tuple

from .sim import SimConfig, inside_rect, occluder2_at

Rect = Tuple[float, float, float, float]
BOUNDARY_TOL = 1e-6


def blind_cells(config: SimConfig, t: int = 0) -> Tuple[Rect, ...]:
    """The blind set at step `t` as a union of rectangles (authoritative).

    An observer is blocked when the point is inside any of its own rects, so the
    blind set is `(o ∪ extra_o) ∩ o2(t)` — a union, which may be disconnected or
    L-shaped (R-P1.25). Membership, not the bounding box, is what the law means.
    """
    first = (config.o,) + tuple(config.extra_o)
    second = occluder2_at(config, t)
    if second is None:
        return tuple(first)
    cells = []
    for rect in first:
        x0 = max(rect[0], second[0])
        x1 = min(rect[1], second[1])
        y0 = max(rect[2], second[2])
        y1 = min(rect[3], second[3])
        if x0 < x1 and y0 < y1:
            cells.append((x0, x1, y0, y1))
    return tuple(cells)


def blind_region(config: SimConfig, t: int = 0) -> Optional[Rect]:
    """The **envelope** of the blind set, for display; None when nothing is blind.

    Use :func:`blind_cells` for membership — with several cells the envelope
    contains points that are not blind (R-P1.25 P1), so a membership test
    written against this rect is wrong.
    """
    cells = blind_cells(config, t)
    if not cells:
        return None
    return (min(c[0] for c in cells), max(c[1] for c in cells),
            min(c[2] for c in cells), max(c[3] for c in cells))


def boundary_distance(config: SimConfig, point: Tuple[float, float],
                      t: int = 0) -> Optional[float]:
    """Distance from `point` to the nearest blind-region edge, or None if blind.

    Cells within ``BOUNDARY_TOL`` of an edge are decided by floating-point
    accumulation order and must be excluded from any prediction (R-P1.11).
    """
    cells = blind_cells(config, t)
    if not cells:
        return None
    x, y = point
    return min(min(abs(x - c[0]), abs(x - c[1]), abs(y - c[2]), abs(y - c[3]))
               for c in cells)


def predict_identifiable(config: SimConfig, point: Tuple[float, float],
                         t: int = 0) -> bool:
    """The law: identifiable iff the event location is outside every blind cell."""
    return not any(inside_rect(cell, point[0], point[1])
                   for cell in blind_cells(config, t))


def on_boundary(config: SimConfig, point: Tuple[float, float], t: int = 0) -> bool:
    """True when the point sits on a blind perimeter within the declared tolerance."""
    cells = blind_cells(config, t)
    if not cells:
        return False
    x, y = point
    for c in cells:
        on_x = (abs(x - c[0]) <= BOUNDARY_TOL or abs(x - c[1]) <= BOUNDARY_TOL) \
            and c[2] <= y <= c[3]
        on_y = (abs(y - c[2]) <= BOUNDARY_TOL or abs(y - c[3]) <= BOUNDARY_TOL) \
            and c[0] <= x <= c[1]
        if on_x or on_y:
            return True
    return False


# Measured validity envelope (source card in parentheses). Data, not prose, so a
# doc or a test can assert it instead of re-deriving it from a paper.
ENVELOPE = {
    "noise_full_identification_upto_sigma": 6.0,          # R-P1.14, R-P1.15
    "noise_breakpoint_sigma": 15.0,                        # R-P1.16
    "noise_accuracy": {10.0: 0.94, 15.0: 0.84, 20.0: 0.81,
                       30.0: 0.71, 40.0: 0.61},            # R-P1.16
    "covered_accuracy_range": (0.47, 0.58),                # R-P1.14, R-P1.16
    "out_of_sample_cells": {"R-P1.12": "30/30", "R-P1.17": "11/11"},  # geometry, time
    "frame_symmetries_verified": 5,                        # R-P1.18
    "boundary_tolerance": BOUNDARY_TOL,                    # R-P1.11, R-P1.12
}


# --- command-line surface (an identifiability oracle other tools can call) ----
#
#   python -m psychopomp.law '{"config": {"o2": [50,70,35,65]},
#                              "point": [55, 50], "t": 60}'
#
# or the same JSON on stdin. Prints one JSON object, exit 0. Kept tiny on
# purpose: the value is that another process (aion, a renderer, a policy) can
# ask the law a question without importing the research instrument.

_TUPLE_FIELDS = ("o", "o2", "o2_velocity", "accel")


def _config_from(spec: dict) -> SimConfig:
    data = dict(spec)
    for key in _TUPLE_FIELDS:
        if key in data and isinstance(data[key], list):
            data[key] = tuple(data[key])
    return SimConfig(**data)


def main(argv: list) -> int:
    raw = argv[1] if len(argv) > 1 else sys.stdin.read()
    spec = json.loads(raw)
    cfg = _config_from(spec.get("config", {}))
    point = tuple(spec["point"])
    t = int(spec.get("t", 0))
    print(json.dumps({
        "identifiable": predict_identifiable(cfg, point, t),
        "on_boundary": on_boundary(cfg, point, t),
        "blind_region": blind_region(cfg, t),
        "envelope": {"noise_full_identification_upto_sigma":
                     ENVELOPE["noise_full_identification_upto_sigma"],
                     "noise_breakpoint_sigma": ENVELOPE["noise_breakpoint_sigma"]},
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
