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
- geometry: axis-aligned rectangular occluders inside a square box;
- observers: one or two, the second may translate at constant velocity;
- physics: constant velocity or constant acceleration, elastic equal-mass
  collisions; the *contact structure must be identical across hypotheses*
  (a kick that displaces a colliding body changes the world, not just the
  hypothesis);
- the predicate is decided by float arithmetic at the boundary: an event within
  1e-6 of a blind edge is *excluded*, never predicted (R-P1.11/R-P1.12).

Out of scope: non-rectangular or rotated occluders, more than two observers,
observers whose motion depends on the world, degraded identity, learned
inference.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .sim import SimConfig, inside_rect, occluder2_at

Rect = Tuple[float, float, float, float]
BOUNDARY_TOL = 1e-6


def blind_region(config: SimConfig, t: int = 0) -> Optional[Rect]:
    """The region no observer can see at step `t`, or None if every point is seen."""
    second = occluder2_at(config, t)
    if second is None:
        return config.o
    x0 = max(config.o[0], second[0])
    x1 = min(config.o[1], second[1])
    y0 = max(config.o[2], second[2])
    y1 = min(config.o[3], second[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def boundary_distance(config: SimConfig, point: Tuple[float, float],
                      t: int = 0) -> Optional[float]:
    """Distance from `point` to the nearest blind-region edge, or None if blind.

    Cells within ``BOUNDARY_TOL`` of an edge are decided by floating-point
    accumulation order and must be excluded from any prediction (R-P1.11).
    """
    blind = blind_region(config, t)
    if blind is None:
        return None
    x, y = point
    return min(abs(x - blind[0]), abs(x - blind[1]),
               abs(y - blind[2]), abs(y - blind[3]))


def predict_identifiable(config: SimConfig, point: Tuple[float, float],
                         t: int = 0) -> bool:
    """The law: identifiable iff the event location is outside the blind region."""
    blind = blind_region(config, t)
    return blind is None or not inside_rect(blind, point[0], point[1])


def on_boundary(config: SimConfig, point: Tuple[float, float], t: int = 0) -> bool:
    """True when the point sits on a blind perimeter within the declared tolerance."""
    blind = blind_region(config, t)
    if blind is None:
        return False
    x, y = point
    on_x_edge = (abs(x - blind[0]) <= BOUNDARY_TOL or abs(x - blind[1]) <= BOUNDARY_TOL) \
        and blind[2] <= y <= blind[3]
    on_y_edge = (abs(y - blind[2]) <= BOUNDARY_TOL or abs(y - blind[3]) <= BOUNDARY_TOL) \
        and blind[0] <= x <= blind[1]
    return on_x_edge or on_y_edge


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
