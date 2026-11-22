"""Coverage planning: choose an observer motion from the law, not from a model.

The arc's results, made callable:

- the law says identifiability is per-event coverage (`law.is_blind`);
- a wrong self-model costs, and the cost tracks which motion the error prefers
  (R-P1.21, R-P1.28);
- a self-model is learnable from the observer's own log (`selfmodel`);
- calibrating then planning matches an oracle, and the hedge becomes vestigial
  (R-P1.30); hedging still pays when the belief is uncertain and *pure*
  (R-P1.24, R-P1.28).

`plan_coverage` turns those into one function: given a world, a task set and a
grid of candidate drifts, return the drift whose blind region leaves the most
tasks identifiable, optionally under a **believed** geometry or hedged over a set
of beliefs.

This is a planner over a known law, not a model. If the law is wrong here, the
tests that pin the published cards fail.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional, Sequence, Tuple

from .law import is_blind
from .selfmodel import estimate_blind_cells_auto
from .sim import SimConfig

Point = Tuple[float, float]
Rect = Tuple[float, float, float, float]


def _with_drift(config: SimConfig, drift: float) -> SimConfig:
    return replace(config, o2_velocity=(drift, 0.0))


def _shift(rect: Rect, drift: float, dt: float, t: int) -> Rect:
    dx = drift * dt * t
    return (rect[0] + dx, rect[1] + dx, rect[2], rect[3])


def _inside_any(rects: Sequence[Rect], point: Point) -> bool:
    return any(r[0] <= point[0] <= r[1] and r[2] <= point[1] <= r[3] for r in rects)


def predicted_scores(config: SimConfig, tasks: Iterable[Point],
                     drifts: Sequence[float], t: int,
                     belief: Optional[SimConfig] = None) -> dict:
    """Identifiable-task count per drift, under `belief` (default: the truth)."""
    world = belief if belief is not None else config
    return {
        drift: sum(1 for p in tasks
                   if not is_blind(_with_drift(world, drift), p, t))
        for drift in drifts
    }


def plan_coverage(config: SimConfig, tasks: Sequence[Point],
                  drifts: Sequence[float], t: int,
                  belief: Optional[SimConfig] = None) -> dict:
    """The drift with the most identifiable tasks (ties: smallest |v|).

    Returns `{"drift", "score", "scores"}` so a caller can see the whole table
    rather than a bare answer — the arc's lesson is that the *ranking* is what
    matters, and it is cheap to show.
    """
    scores = predicted_scores(config, tasks, drifts, t, belief)
    drift = max(drifts, key=lambda v: (scores[v], -abs(v), -v))
    return {"drift": drift, "score": scores[drift], "scores": scores}


def plan_hedged(config: SimConfig, tasks: Sequence[Point],
                drifts: Sequence[float], t: int,
                belief_rects: Sequence[Rect]) -> dict:
    """Minimax over a set of believed blind regions (R-P1.24's hedge).

    Each believed rect is translated by the candidate drift, so the hedge is over
    *uncertainty about one's own blind region*, exactly as R-P1.24 and R-P1.28
    measured. Returns the same shape as `plan_coverage`, with the worst-case score
    under `worst_case`.
    """
    def worst_case(drift: float) -> int:
        return min(
            sum(1 for p in tasks if not _inside_any([_shift(r, drift, config.dt, t)], p))
            for r in belief_rects
        )

    cases = {drift: worst_case(drift) for drift in drifts}
    drift = max(drifts, key=lambda v: (cases[v], -abs(v), -v))
    return {"drift": drift, "worst_case": cases[drift], "cases": cases}


def plan_coverage_rects(tasks: Sequence[Point], drifts: Sequence[float], t: int,
                        blind_rects: Sequence[Rect], dt: float) -> dict:
    """Plan from blind **rectangles** the observer believes it has.

    This is the semantic the planning cards used: a candidate drift translates the
    believed blind region, and a task is identifiable when the translated region
    misses it. Preferred over `plan_coverage(belief=...)` whenever the belief is an
    estimate rather than a whole configuration, because a config's second occluder
    clips the first and silently changes the set.
    """
    scores = {
        drift: sum(1 for p in tasks
                   if not _inside_any([_shift(r, drift, dt, t) for r in blind_rects], p))
        for drift in drifts
    }
    drift = max(drifts, key=lambda v: (scores[v], -abs(v), -v))
    return {"drift": drift, "score": scores[drift], "scores": scores}


def plan_from_evidence(config: SimConfig, corpus, tasks: Sequence[Point],
                       drifts: Sequence[float], t: int) -> dict:
    """The whole chain in one call: logs -> self-model -> plan (R-P1.29..R-P1.32).

    The observer hands over its own observable logs; the blind cells and their
    count are recovered from them, and the plan is made from that estimate — no
    ground truth. `estimate` is returned so the caller can see what the plan was
    based on, and `known` says whether every recovered edge is determined (an
    uncrossed edge is `None`, and a plan built on it is optimistic by construction).
    """
    cells = estimate_blind_cells_auto(corpus, config.dt * config.speed if
                                      config.speed else 0.3)
    rects = [c.as_rect() for c in cells]
    known = bool(rects) and all(r is not None for r in rects)
    usable = [r for r in rects if r is not None]
    if not usable:
        return {"drift": None, "score": None, "scores": None,
                "estimate": rects, "known": False,
                "reason": "the evidence determines no blind cell"}
    plan = plan_coverage_rects(tasks, drifts, t, usable, config.dt)
    return {**plan, "estimate": rects, "known": known}
