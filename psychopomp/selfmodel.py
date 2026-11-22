"""Self-model inference: recover the observer's own blind region from its log.

The law (`psychopomp/law.py`) predicts identifiability from a *known* blind
region. An observer does not know its own — it has a log of what it saw and where
it stopped seeing. This module turns that log into an estimate, and reports what
it cannot know (R-P1.29).

Evidence used, and only this:

- `enter_occ` at side `left`: the body was last seen just **outside** `x0`, within
  one step, so `pos.x + step` is an upper bound on `x0`;
- `exit_occ` at side `right`: first seen again just **outside** `x1`, so
  `pos.x - step` is a lower bound on `x1`;
- symmetric for `bottom` / `top` on `y`.

Taking the tightest bound in the corpus gives an estimate that is
**contained in** the true region, correct to one step, and `None` for any edge
the corpus never crossed. An edge never crossed is *unknown*, not guessed: an
observer that reports a blind spot bigger or smaller than the evidence supports is
claiming knowledge it does not have.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple

Rect = Tuple[float, float, float, float]
CROSSINGS = ("enter_occ", "exit_occ")


@dataclass(frozen=True)
class BlindEstimate:
    """What an observer can conclude about its own blind region."""

    step: float
    x0: Optional[float] = None
    x1: Optional[float] = None
    y0: Optional[float] = None
    y1: Optional[float] = None
    samples: Dict[str, int] = field(default_factory=dict)

    def unknown_edges(self) -> Tuple[str, ...]:
        return tuple(name for name in ("x0", "x1", "y0", "y1")
                     if getattr(self, name) is None)

    def as_rect(self) -> Optional[Rect]:
        """The estimate as a rectangle, or None when any edge is unknown."""
        if self.unknown_edges():
            return None
        return (self.x0, self.x1, self.y0, self.y1)  # type: ignore[return-value]

    def blind_membership(self, point: Tuple[float, float]) -> Optional[bool]:
        """True/False when the estimate determines it, None when it does not.

        A point covered by an unknown edge is reported as unknown rather than
        guessed, which is the difference between a calibrated observer and a
        confident one.
        """
        x, y = point
        if self.x0 is not None and x < self.x0:
            return False
        if self.x1 is not None and x > self.x1:
            return False
        if self.y0 is not None and y < self.y0:
            return False
        if self.y1 is not None and y > self.y1:
            return False
        if self.unknown_edges():
            return None
        return True


def _bound(values, upper: bool, quantile: Optional[float]) -> Optional[float]:
    """Tightest bound, or a quantile bound that a single outlier cannot set."""
    if not values:
        return None
    ordered = sorted(values)
    if quantile is None:
        return ordered[-1] if upper else ordered[0]
    q = min(max(quantile, 0.0), 1.0)
    index = int(q * (len(ordered) - 1))
    return ordered[index] if not upper else ordered[min(index, len(ordered) - 1)]


def _spread(values) -> float:
    return (max(values) - min(values)) if values else 0.0


def estimate_blind_region(episodes: Iterable, step: float,
                          quantile: Optional[float] = None,
                          max_spread: Optional[float] = None) -> BlindEstimate:
    """Tightest one-step-conservative estimate of the blind region from logs.

    `episodes` are `SimEpisode`s (or anything exposing `observable_log()`).
    Only observable events are read — an oracle log would be cheating, and is
    never touched here.
    """
    left_in: list = []
    right_out: list = []
    bottom_in: list = []
    top_out: list = []
    samples = {"left": 0, "right": 0, "bottom": 0, "top": 0}

    for episode in episodes:
        for event in episode.observable_log():
            if event.kind not in CROSSINGS:
                continue
            side = event.attrs.get("side")
            pos = event.attrs.get("pos")
            if pos is None:
                continue
            if event.kind == "enter_occ" and side == "left":
                left_in.append(pos[0] + step)
                samples["left"] += 1
            elif event.kind == "exit_occ" and side == "right":
                right_out.append(pos[0] - step)
                samples["right"] += 1
            elif event.kind == "enter_occ" and side == "bottom":
                bottom_in.append(pos[1] + step)
                samples["bottom"] += 1
            elif event.kind == "exit_occ" and side == "top":
                top_out.append(pos[1] - step)
                samples["top"] += 1

    def edge(values, upper: bool, direction: str) -> Optional[float]:
        # x0 and y0 are upper bounds on the near edge, x1 and y1 lower bounds;
        # a quantile bound trades tightness for robustness to a corrupted sample.
        if quantile is None:
            return min(values) if values else None
        low = sorted(values)[int((1.0 - quantile) * (len(values) - 1))] if upper else None
        high = sorted(values)[int(quantile * (len(values) - 1))] if not upper else None
        return low if upper else high

    def guard(values) -> bool:
        if quantile is None or max_spread is None:
            return True
        return _spread(values) <= max_spread

    x0 = edge(left_in, True, "x0") if guard(left_in) else None
    x1 = edge(right_out, False, "x1") if guard(right_out) else None
    y0 = edge(bottom_in, True, "y0") if guard(bottom_in) else None
    y1 = edge(top_out, False, "y1") if guard(top_out) else None
    return BlindEstimate(step=step, x0=x0, x1=x1, y0=y0, y1=y1, samples=samples)


# --- multi-cell self-models (R-P1.31) --------------------------------------
#
# An observer with more than one blocker has a blind set that is a union of
# rectangles (R-P1.25). The same crossing evidence recovers it, provided the
# observer knows HOW MANY blockers it has — that is a structural prior about its
# own hardware, and getting it wrong is a new kind of self-model error (see
# R-P1.31's P4), not a geometric one.


def _cluster(values, tolerance: float):
    """Greedy 1-D clustering: split where consecutive values differ by > tolerance."""
    out = []
    for value in sorted(values):
        if out and value - out[-1][-1] <= tolerance:
            out[-1].append(value)
        else:
            out.append([value])
    return out


def estimate_blind_cells(episodes: Iterable, step: float, n_cells: int) -> Tuple[BlindEstimate, ...]:
    """Estimate each blind cell separately, given how many blockers there are.

    Cells are assumed disjoint and ordered along `x` (the testbed geometry); the
    k-th cluster of left-entry bounds is paired with the k-th cluster of
    right-exit bounds. `y` edges are assigned by whether the crossing's `x` falls
    inside the cell's estimated `x`-range.
    """
    left_in: list = []
    right_out: list = []
    bottom_in: list = []
    top_out: list = []
    samples = {"left": 0, "right": 0, "bottom": 0, "top": 0}

    for episode in episodes:
        for event in episode.observable_log():
            if event.kind not in CROSSINGS:
                continue
            side = event.attrs.get("side")
            pos = event.attrs.get("pos")
            if pos is None:
                continue
            if event.kind == "enter_occ" and side == "left":
                left_in.append(pos[0] + step)
                samples["left"] += 1
            elif event.kind == "exit_occ" and side == "right":
                right_out.append(pos[0] - step)
                samples["right"] += 1
            elif event.kind == "enter_occ" and side == "bottom":
                bottom_in.append((pos[0], pos[1] + step))
                samples["bottom"] += 1
            elif event.kind == "exit_occ" and side == "top":
                top_out.append((pos[0], pos[1] - step))
                samples["top"] += 1

    left_clusters = _cluster(left_in, 2 * step)
    right_clusters = _cluster(right_out, 2 * step)
    if len(left_clusters) < n_cells or len(right_clusters) < n_cells:
        # not enough evidence for the claimed structure: abstain rather than
        # invent cells
        return tuple(
            BlindEstimate(step=step, samples=dict(samples)) for _ in range(n_cells)
        )

    xs = [(min(left_clusters[k]), max(right_clusters[k])) for k in range(n_cells)]
    cells = []
    for x0, x1 in xs:
        ys_bottom = [y for x, y in bottom_in if x0 - step <= x <= x1 + step]
        ys_top = [y for x, y in top_out if x0 - step <= x <= x1 + step]
        cells.append(BlindEstimate(
            step=step, x0=x0, x1=x1,
            y0=min(ys_bottom) if ys_bottom else None,
            y1=max(ys_top) if ys_top else None,
            samples=dict(samples),
        ))
    return tuple(cells)


def estimate_blind_cells_auto(episodes: Iterable, step: float) -> Tuple[BlindEstimate, ...]:
    """Recover the blind cells **and their count** from the crossing evidence.

    Clusters separated by more than `2·step` are distinct cells; the count is
    whatever the evidence supports. `BlindEstimate.samples` carries the crossing
    counts so a caller can see how thin the coverage was — nothing here can invent
    a cell the corpus never crossed, and nothing pretends the model is complete.
    """
    left_in: list = []
    right_out: list = []
    bottom_in: list = []
    top_out: list = []
    samples = {"left": 0, "right": 0, "bottom": 0, "top": 0}

    for episode in episodes:
        for event in episode.observable_log():
            if event.kind not in CROSSINGS:
                continue
            side = event.attrs.get("side")
            pos = event.attrs.get("pos")
            if pos is None:
                continue
            if event.kind == "enter_occ" and side == "left":
                left_in.append(pos[0] + step)
                samples["left"] += 1
            elif event.kind == "exit_occ" and side == "right":
                right_out.append(pos[0] - step)
                samples["right"] += 1
            elif event.kind == "enter_occ" and side == "bottom":
                bottom_in.append((pos[0], pos[1] + step))
                samples["bottom"] += 1
            elif event.kind == "exit_occ" and side == "top":
                top_out.append((pos[0], pos[1] - step))
                samples["top"] += 1

    left_clusters = _cluster(left_in, 2 * step)
    right_clusters = _cluster(right_out, 2 * step)
    n_cells = min(len(left_clusters), len(right_clusters))
    if n_cells == 0:
        return ()

    cells = []
    for k in range(n_cells):
        x0, x1 = min(left_clusters[k]), max(right_clusters[k])
        ys_bottom = [y for x, y in bottom_in if x0 - step <= x <= x1 + step]
        ys_top = [y for x, y in top_out if x0 - step <= x <= x1 + step]
        cells.append(BlindEstimate(
            step=step, x0=x0, x1=x1,
            y0=min(ys_bottom) if ys_bottom else None,
            y1=max(ys_top) if ys_top else None,
            samples=dict(samples),
        ))
    return tuple(cells)


# --- polygon estimation from labelled crossings (R-P1.34) -------------------
#
# A polygon edge is a half-plane `n·x <= d`. A crossing of that edge gives a point
# p within one step of the line, on the **outside**: d <= n·p. Taking the tightest
# bound (min n·p) therefore puts the estimate outside the true polygon — the
# opposite of what the same rule does for a rectangle's `x >= x0`. Subtracting the
# one-step penetration along the normal gives the tightest **inner** bound instead.


def estimate_polygon_halfplanes(episodes: Iterable, step: float,
                                inner: bool = False) -> Dict[int, dict]:
    """Per-edge half-plane estimates from labelled polygon crossings.

    Returns `{edge_index: {"normal": (nx, ny), "offset": d, "samples": n}}`.
    `inner=False` takes the tightest outside bound (pessimistic for polygons);
    `inner=True` subtracts the one-step penetration (optimistic, like the rect
    estimator).
    """
    per_edge: Dict[int, list] = {}
    for episode in episodes:
        for event in episode.observable_log():
            if event.kind not in CROSSINGS:
                continue
            edge = event.attrs.get("edge")
            normal = event.attrs.get("normal")
            pos = event.attrs.get("pos")
            vel = event.attrs.get("v")
            if edge is None or normal is None or pos is None:
                continue
            nx, ny = normal
            projection = nx * pos[0] + ny * pos[1]
            penetration = 0.0
            if vel is not None:
                speed = (vel[0] ** 2 + vel[1] ** 2) ** 0.5
                if speed > 1e-12:
                    towards = abs(nx * vel[0] + ny * vel[1]) / speed
                    penetration = step * towards
            per_edge.setdefault(int(edge), []).append((projection, penetration, (nx, ny)))

    out: Dict[int, dict] = {}
    for edge, samples in per_edge.items():
        best = min(samples, key=lambda s: s[0])
        offset = best[0] - (best[1] if inner else 0.0)
        out[edge] = {"normal": best[2], "offset": offset, "samples": len(samples)}
    return out


def estimate_polygon_point_inside(halfplanes: Dict[int, dict],
                                  point: Tuple[float, float]) -> bool:
    """Membership in the estimated polygon: inside every half-plane."""
    x, y = point
    return all(h["normal"][0] * x + h["normal"][1] * y <= h["offset"]
               for h in halfplanes.values())
