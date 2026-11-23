"""2D ball-in-box simulator with strict observable/oracle separation.

Box [0, W] x [0, H]; an occluder rectangle hides a ball whose centre is
inside it (x0 <= x <= x1 and y0 <= y <= y1). Physics: constant velocity,
elastic wall reflection, elastic equal-mass 2D ball collisions (velocity
components along the contact normal are exchanged; tangential preserved).
External actions are velocity kicks, applied only to balls visible at that
step, so no action is ever hidden from the camera.

Two visually identical balls: the observable log is identity-free. Off-axis
contacts change the outgoing directions, so unlike the degenerate 1D head-on
case a hidden contact is in principle detectable from observable history
(entry states + known dynamics suffice to continue the motion). The identity
pairing (which ball exits where) remains the genuinely hard part, and is the
JEPA's task; an oracle-free forward reference exists (scripts/recoverability.py).

Data products (oracle-leakage control):
  observable_log()  -- camera-measurable, identity-free events only
  oracle_log()      -- labelled events including hidden contacts;
                       evaluation only, never a training input
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .eventlog import Event, EventLog, Provenance

Vec = Tuple[float, float]

TRACK_SAMPLES = 3  # observable positions kept before/after a crossing (round 9)


@dataclass(frozen=True)
class SimConfig:
    W: float = 100.0
    H: float = 100.0
    o: Tuple[float, float, float, float] = (40.0, 60.0, 35.0, 65.0)  # x0,x1,y0,y1
    # Second observer's own occluder (R-P1.9). A body is observable when at
    # least one observer sees it, so the blind region is o ∩ o2: what is hidden
    # is a property of the observer set, not of the world. None = one observer.
    # Extra blockers for the FIRST observer (R-P1.25). The blind set becomes
    # (o ∪ extra_o) ∩ o2, i.e. a union of rects: non-convex, even disconnected.
    extra_o: Tuple[Tuple[float, float, float, float], ...] = ()
    # Static polygon blockers for the first observer (R-P1.33): each is a tuple of
    # (x, y) vertices, membership by ray casting (convex or not). Rotated occluders
    # are expressible this way without changing the physics.
    poly_o: Tuple[Tuple[Tuple[float, float], ...], ...] = ()
    o2: Optional[Tuple[float, float, float, float]] = None
    # Second observer drift, world units per second (R-P1.17). The occluder
    # translates rigidly and folds inside the box, so it reflects at the walls
    # deterministically. (0, 0) reproduces the fixed observer exactly.
    o2_velocity: Tuple[float, float] = (0.0, 0.0)
    # Constant acceleration (R-P1.19), semi-implicit Euler. (0, 0) keeps every
    # constant-velocity number exactly as it was.
    accel: Tuple[float, float] = (0.0, 0.0)
    # Identity evidence (R-P1.39): when on, each body emits an observable `marker`
    # every `marker_period` steps WHILE VISIBLE, carrying its tag. Off by default,
    # so the identity-free log and every prior number are unchanged.
    identity_marker: bool = False
    marker_period: int = 10
    # Per-opportunity marker reliability (R-P1.40): each visible marker fires with
    # this probability, drawn from its own deterministic stream so `1.0` reproduces
    # R-P1.39 exactly and the draws do not disturb the sensor-noise streams.
    marker_reliability: float = 1.0
    # Correlated loss (R-P1.42): with this probability a fresh outage begins at a
    # marker opportunity and drops the next `marker_outage_len` opportunities.
    marker_outage_prob: float = 0.0
    marker_outage_len: int = 2
    # Detection latency (R-P1.43): a crossing is reported this many steps late,
    # carrying the body's position THEN (a lagging sampler). 0 = instant, and the
    # oracle log is never delayed.
    detect_latency: int = 0
    # Partial visibility (R-P1.44): a body of radius r is FULLY hidden only when its
    # whole disc is inside a blocker, so the blind region shrinks by r on each edge.
    # 0.0 reproduces the point model every prior number was measured with.
    visual_radius: float = 0.0
    # Start a body already occluded (R-P1.39 case 3): models an observer that was
    # created with something hidden, so zero identity evidence exists for it.
    # Off by default; the init-observable guard still applies otherwise.
    allow_hidden_init: bool = False
    r: float = 1.0
    dt: float = 0.1
    steps: int = 600
    speed: float = 2.0
    n_balls: int = 2
    # Sensor noise on the OBSERVABLE log only (uniform +-noise/2 on `pos`/`v`).
    # 0.0 reproduces the exact log, so every corpus and gate built before this
    # field still means what it meant. Oracle attributes are never jittered: a
    # sensor cannot corrupt the answer key.
    noise: float = 0.0

    def __post_init__(self) -> None:
        x0, x1, y0, y1 = self.o
        assert self.r > 0 and 0 < x0 < x1 < self.W - self.r, "occluder x-range"
        assert 0 < y0 < y1 < self.H - self.r, "occluder y-range"
        for poly in self.poly_o:
            assert len(poly) >= 3, "a polygon needs at least three vertices"
            assert poly == tuple(poly) and len(poly) == len(set(poly)), "degenerate polygon"
        for a0, a1, b0, b1 in self.extra_o:
            assert 0 < a0 < a1 < self.W - self.r, "extra occluder x-range"
            assert 0 < b0 < b1 < self.H - self.r, "extra occluder y-range"
        if self.o2_velocity != (0.0, 0.0):
            assert self.o2 is not None, "o2_velocity needs a second occluder"
        if self.o2 is not None:
            a0, a1, b0, b1 = self.o2
            # a second observer's occluder may touch a wall; it only narrows
            # what is hidden, so it never needs the first one's inset guard
            assert 0 <= a0 < a1 <= self.W - self.r, "second occluder x-range"
            assert 0 <= b0 < b1 <= self.H - self.r, "second occluder y-range"
        # one step must never cross the whole occluder (tunneling guard)
        assert self.speed * self.dt < min(x1 - x0, y1 - y0), "speed*dt vs occluder"

    def canonical(self) -> str:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        return json.dumps(d, sort_keys=True)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


@dataclass(frozen=True)
class Init:
    x: Tuple[float, ...]
    y: Tuple[float, ...]
    v: Tuple[Vec, ...]


@dataclass(frozen=True)
class Kick:
    t: int
    ball: int
    dv: Vec


@dataclass
class Trajectory:
    x: List[float]
    y: List[float]
    vx: List[float]
    vy: List[float]
    visible: List[bool]


def inside_rect(rect: Tuple[float, float, float, float], x: float, y: float) -> bool:
    x0, x1, y0, y1 = rect
    return x0 <= x <= x1 and y0 <= y <= y1


def inside(cfg: SimConfig, x: float, y: float) -> bool:
    return inside_rect(cfg.o, x, y)


def crossed_poly_edge(poly: Sequence[Tuple[float, float]],
                      px: float, py: float, cx: float, cy: float):
    """Which polygon edge the segment (p -> c) crosses, and its outward normal.

    Returns `(index, (nx, ny))` or None. The outward normal points away from the
    polygon centroid, so an observer can name the edge it was blocked by instead
    of reporting an unlabelled `sweep` (R-P1.34).
    """
    n = len(poly)
    best = None
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        d1 = (x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)
        d2 = (x1 - x0) * (cy - y0) - (y1 - y0) * (cx - x0)
        if (d1 > 0) == (d2 > 0):
            continue
        t = d1 / (d1 - d2)
        if not 0.0 <= t <= 1.0:
            continue
        best = i
    if best is None:
        return None
    x0, y0 = poly[best]
    x1, y1 = poly[(best + 1) % n]
    ex, ey = x1 - x0, y1 - y0
    norm = math.hypot(ex, ey)
    if norm < 1e-12:
        return None
    nx, ny = -ey / norm, ex / norm
    cxm = sum(v[0] for v in poly) / n
    cym = sum(v[1] for v in poly) / n
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    if nx * (mx - cxm) + ny * (my - cym) < 0:
        nx, ny = -nx, -ny
    return best, (nx, ny)


def distance_to_segment(px: float, py: float, ax: float, ay: float,
                        bx: float, by: float) -> float:
    """Perpendicular distance from a point to a segment (not the infinite line)."""
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def polygon_boundary_distance(poly: Sequence[Tuple[float, float]],
                              x: float, y: float) -> float:
    """Distance from a point to the polygon's boundary (vertex-aware)."""
    n = len(poly)
    return min(distance_to_segment(x, y, poly[i][0], poly[i][1],
                                   poly[(i + 1) % n][0], poly[(i + 1) % n][1])
               for i in range(n))


def inside_polygon(poly: Sequence[Tuple[float, float]], x: float, y: float) -> bool:
    """Ray-casting point-in-polygon; works for convex and non-convex shapes."""
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            x_cross = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < x_cross:
                inside = not inside
    return inside


def observable(cfg: SimConfig, x: float, y: float, t: int = 0) -> bool:
    """Visible to at least one observer at step `t`.

    An observer is blocked when the body is **fully** inside any of its own rects —
    with `visual_radius` the whole disc must be covered, so a sliver of a body is
    still seen (R-P1.44). The body is hidden only when every observer is blocked,
    and the second observer's rect applies the same rule; a patch that shrinks only
    the first observer leaves the second one hiding everything, which is exactly the
    mistake the first run of R-P1.44 measured.
    """
    r = cfg.visual_radius

    def poly_fully_hidden(poly, px: float, py: float, radius: float) -> bool:
        # R-P1.45: fully covered by a polygon means inside AND at least `radius`
        # from the boundary. A distance-to-edge shortcut is wrong near a vertex,
        # where the nearest boundary point is the vertex itself.
        if not inside_polygon(poly, px, py):
            return False
        if radius <= 0.0:
            return True
        return polygon_boundary_distance(poly, px, py) >= radius

    def fully_inside(rect) -> bool:
        # the whole disc is covered when the centre is at least r from every edge
        return inside_rect(rect, x, y) and (x0 := rect[0] + r) <= x <= rect[1] - r \
            and (y0 := rect[2] + r) <= y <= rect[3] - r

    blocked1 = (fully_inside(cfg.o)
                or any(fully_inside(rect) for rect in cfg.extra_o)
                or any(poly_fully_hidden(poly, x, y, r) for poly in cfg.poly_o))
    if not blocked1:
        return True
    second = occluder2_at(cfg, t)
    return second is not None and not fully_inside(second)


def _fold(value: float, lo: float, hi: float) -> float:
    """Triangle-wave fold: keeps a translating rect inside [lo, hi], reflecting."""
    span = hi - lo
    if span <= 0:
        return lo
    p = (value - lo) % (2 * span)
    return lo + (p if p <= span else 2 * span - p)


def occluder2_at(cfg: SimConfig, t: int) -> Optional[Tuple[float, float, float, float]]:
    """Second observer's occluder at step `t` (rigid translation, then folded)."""
    if cfg.o2 is None:
        return None
    x0, x1, y0, y1 = cfg.o2
    if cfg.o2_velocity == (0.0, 0.0):
        return cfg.o2
    dx = cfg.o2_velocity[0] * cfg.dt * t
    dy = cfg.o2_velocity[1] * cfg.dt * t
    nx0 = _fold(x0 + dx, 0.0, cfg.W - (x1 - x0))
    ny0 = _fold(y0 + dy, 0.0, cfg.H - (y1 - y0))
    return (nx0, nx0 + (x1 - x0), ny0, ny0 + (y1 - y0))


def occluders(cfg: SimConfig, t: int = 0) -> Tuple[Tuple[float, float, float, float], ...]:
    """Every blocker in play at step `t`: observer 1's rects, then observer 2's."""
    first = (cfg.o,) + tuple(cfg.extra_o)
    second = occluder2_at(cfg, t)
    return first if second is None else first + (second,)


def _enter_side(rect: Tuple[float, float, float, float],
                px: float, py: float, cx: float, cy: float) -> str:
    x0, x1, y0, y1 = rect
    if px < x0 and cx >= x0 and y0 <= cy <= y1:
        return "left"
    if px > x1 and cx <= x1 and y0 <= cy <= y1:
        return "right"
    if py < y0 and cy >= y0 and x0 <= cx <= x1:
        return "bottom"
    if py > y1 and cy <= y1 and x0 <= cx <= x1:
        return "top"
    return "corner"


def _exit_side(rect: Tuple[float, float, float, float], x: float, y: float) -> str:
    x0, x1, y0, y1 = rect
    if x < x0:
        return "left"
    if x > x1:
        return "right"
    if y < y0:
        return "bottom"
    return "top"


def transition_rect(
    cfg: SimConfig, t: int, px: float, py: float, cx: float, cy: float,
    entering: bool,
) -> Optional[Tuple[float, float, float, float]]:
    """The occluder responsible for a visibility change, if a body crossed one.

    Returns None when no rect explains the change: with a moving occluder the
    rect can sweep onto or off a body without the body crossing an edge
    (measured, R-P1.17).
    """
    for rect in occluders(cfg, t):
        before = inside_rect(rect, px, py)
        after = inside_rect(rect, cx, cy)
        if entering and after and not before:
            return rect
        if not entering and before and not after:
            return rect
    return None


def _lagged_attrs(config: SimConfig, tr, j: int, attrs: dict,
                  entering: bool) -> tuple:
    """A lagging sampler's report for a crossing at step `j` (R-P1.43).

    The detector notices `detect_latency` steps late, so it reports a position that
    lies `L` steps further along the body's travel — *outward* from the crossing:
    backwards (`j - L`) for an entry, forwards (`j + L`) for an exit. Sampling the
    wrong side is not a small error: it moves the reported position back into the
    region and the bound then shrinks inward, which is what the first run of this
    card measured. Returns `(step, attrs)`.
    """
    lag = max(0, config.detect_latency)
    if lag == 0:
        return j, attrs
    k = j - lag if entering else j + lag
    k = min(max(k, 0), len(tr.x) - 1)
    lagged = dict(attrs)
    lagged["pos"] = [round(tr.x[k], 6), round(tr.y[k], 6)]
    return (j + lag if not entering else j), lagged


def _meas_v(tr: Trajectory, dt: float, a: int, b: int) -> Optional[Vec]:
    if a < 0 or b >= len(tr.x) or not tr.visible[a] or not tr.visible[b]:
        return None
    return [round((tr.x[b] - tr.x[a]) / dt, 6), round((tr.y[b] - tr.y[a]) / dt, 6)]


class SimEpisode:
    def __init__(
        self,
        config: SimConfig,
        seed: int,
        episode: int,
        trajs: List[Trajectory],
        applied: Sequence[Kick],
        skipped: Sequence[Kick],
        init: Optional[Init],
        obs: EventLog,
        oracle: EventLog,
    ) -> None:
        self.config = config
        self.seed = seed
        self.episode = episode
        self.trajs = trajs
        self.applied_kicks = list(applied)
        self.skipped_kicks = list(skipped)
        self.init = init
        self._obs = obs
        self._oracle = oracle
        self.prov = Provenance("sim:v0.2", config.sha256(), seed, episode)

    def observable_log(self) -> EventLog:
        return self._obs

    def oracle_log(self) -> EventLog:
        return self._oracle

    def hidden_segments(self) -> dict:
        """Oracle-only: per-ball (enter_frame, exit_frame) occlusion intervals."""
        out = {}
        for i, tr in enumerate(self.trajs):
            segs, cur = [], None
            for j, vis in enumerate(tr.visible):
                if not vis and cur is None:
                    cur = j
                elif vis and cur is not None:
                    segs.append((cur, j))
                    cur = None
            out[f"b{i}"] = segs
        return out


def run(
    config: SimConfig,
    seed: int,
    episode: int = 0,
    init: Optional[Init] = None,
    kicks: Sequence[Kick] = (),
    source: str = "sim:v0.2",
    noise_stream: int = 0,
) -> SimEpisode:
    rng = random.Random(hash((seed, episode)) % (2**63))
    n = config.n_balls
    x0, x1, y0, y1 = config.o

    if init is not None:
        assert len(init.x) == n == len(init.y) == len(init.v)
        xs, ys, vs = list(init.x), list(init.y), list(init.v)
    else:
        xs, ys, vs = [], [], []
        for _ in range(n):
            while True:
                cx, cy = rng.uniform(config.r, config.W - config.r), rng.uniform(
                    config.r, config.H - config.r
                )
                if observable(config, cx, cy) and all(
                    math.hypot(cx - px, cy - py) >= 6 * config.r for px, py in zip(xs, ys)
                ):
                    break
            th = rng.uniform(0.0, 2 * math.pi)
            xs.append(cx)
            ys.append(cy)
            vs.append((config.speed * math.cos(th), config.speed * math.sin(th)))
    for px, py in zip(xs, ys):
        assert config.r <= px <= config.W - config.r and config.r <= py <= config.H - config.r
        assert (config.allow_hidden_init or observable(config, px, py)), \
            "init must be observable"
    # Initial visibility must be computed, not assumed (R-P1.39): with
    # `allow_hidden_init` a body can start occluded, and a hardcoded True used to
    # report it as seen for one step — which emitted an identity marker for a body
    # that was never visible.
    trajs = [
        Trajectory(x=[xs[i]], y=[ys[i]], vx=[vs[i][0]], vy=[vs[i][1]],
                   visible=[observable(config, xs[i], ys[i], 0)])
        for i in range(n)
    ]

    applied: List[Kick] = []
    skipped: List[Kick] = []
    bounces: List[Tuple[int, int, str]] = []
    collisions: List[Tuple[int, int, int]] = []

    for t in range(config.steps):
        for k in kicks:
            if k.t == t:
                if trajs[k.ball].visible[-1]:
                    trajs[k.ball].vx[-1] += k.dv[0]
                    trajs[k.ball].vy[-1] += k.dv[1]
                    applied.append(k)
                else:
                    skipped.append(k)
        for i in range(n):
            tr = trajs[i]
            tr.vx[-1] += config.accel[0] * config.dt
            tr.vy[-1] += config.accel[1] * config.dt
            tr.x.append(tr.x[-1] + tr.vx[-1] * config.dt)
            tr.y.append(tr.y[-1] + tr.vy[-1] * config.dt)
            tr.vx.append(tr.vx[-1])
            tr.vy.append(tr.vy[-1])
        for i in range(n):
            tr = trajs[i]
            if tr.x[-1] < config.r:
                tr.x[-1] = 2 * config.r - tr.x[-1]
                tr.vx[-1] = -tr.vx[-1]
                bounces.append((t + 1, i, "left"))
            elif tr.x[-1] > config.W - config.r:
                tr.x[-1] = 2 * (config.W - config.r) - tr.x[-1]
                tr.vx[-1] = -tr.vx[-1]
                bounces.append((t + 1, i, "right"))
            if tr.y[-1] < config.r:
                tr.y[-1] = 2 * config.r - tr.y[-1]
                tr.vy[-1] = -tr.vy[-1]
                bounces.append((t + 1, i, "top"))
            elif tr.y[-1] > config.H - config.r:
                tr.y[-1] = 2 * (config.H - config.r) - tr.y[-1]
                tr.vy[-1] = -tr.vy[-1]
                bounces.append((t + 1, i, "bottom"))
        for i in range(n):
            for j in range(i + 1, n):
                a, b = trajs[i], trajs[j]
                dx, dy = b.x[-1] - a.x[-1], b.y[-1] - a.y[-1]
                d = math.hypot(dx, dy)
                if d < 2 * config.r:
                    nx, ny = (dx / d, dy / d) if d > 1e-12 else (1.0, 0.0)
                    rn = (a.vx[-1] - b.vx[-1]) * nx + (a.vy[-1] - b.vy[-1]) * ny
                    if rn > 0:  # closing along the a->b normal: exchange normal components
                        a.vx[-1] -= rn * nx
                        a.vy[-1] -= rn * ny
                        b.vx[-1] += rn * nx
                        b.vy[-1] += rn * ny
                        collisions.append((t + 1, i, j))
                    if d < 2 * config.r:  # positional separation
                        push = (2 * config.r - d) / 2
                        a.x[-1] -= push * nx
                        a.y[-1] -= push * ny
                        b.x[-1] += push * nx
                        b.y[-1] += push * ny
        for i in range(n):
            # visibility at step t+1, i.e. of the position just appended
            trajs[i].visible.append(
                observable(config, trajs[i].x[-1], trajs[i].y[-1], t + 1)
            )

    prov = Provenance(source, config.sha256(), seed, episode)
    oracle, obs = EventLog(), EventLog()

    # Int-only derivation on purpose: hashing a string makes the seed depend on
    # PYTHONHASHSEED, which is randomised per process. Measured 2026-11-21 --
    # the noise arm scored 0.17 locally and 0.33 on CI for identical inputs.
    # The base RNG above is safe because its tuple holds ints only.
    # `noise_stream` separates the sensor corruption of one realization from
    # another: a counterfactual world must not inherit the observation's noise
    # draws, or the truth is reproduced exactly under noise (measured defect,
    # R-P1.13). Default 0 keeps every noise-free number unchanged.
    noise_rng = random.Random(
        (seed * 1000003 + episode * 7919 + noise_stream * 104729 + 17) % (2**63)
    )
    # A separate stream for `track`: sharing one stream means adding an attribute
    # silently re-rolls every later draw, so pinned cross-process numbers move
    # whenever the log schema grows (measured 2026-11-21).
    track_rng = random.Random((seed * 1000033 + episode * 104729 + 29) % (2**63))
    marker_rng = random.Random((seed * 1000037 + episode * 130363 + 41) % (2**63))

    def emit(log: EventLog, kind: str, t: int, subjects: Tuple[str, ...],
             attrs: dict, observable: bool) -> None:
        if log is obs and config.noise > 0:
            attrs = dict(attrs)
            for key in ("pos", "v"):
                value = attrs.get(key)
                if value is not None:
                    attrs[key] = [
                        round(component + noise_rng.uniform(-config.noise / 2, config.noise / 2), 6)
                        for component in value
                    ]
            if attrs.get("track") is not None:
                attrs["track"] = [
                    [round(component + track_rng.uniform(-config.noise / 2, config.noise / 2), 6)
                     for component in point]
                    for point in attrs["track"]
                ]
        log.add(Event(kind, t, subjects, attrs, observable, prov))

    for k in applied:
        tr = trajs[k.ball]
        attrs = {"x": [round(tr.x[k.t + 1], 6), round(tr.y[k.t + 1], 6)], "dv": list(k.dv)}
        emit(oracle, "kick", k.t, (f"b{k.ball}",), attrs, True)
        emit(obs, "kick", k.t, ("ball",), attrs, True)
    for k in skipped:
        emit(oracle, "kick_skipped", k.t, (f"b{k.ball}",), {"dv": list(k.dv)}, False)

    for i, tr in enumerate(trajs):
        for j in range(1, len(tr.visible)):
            if tr.visible[j] and not tr.visible[j - 1]:
                v = _meas_v(tr, config.dt, j, j + 1)
                # the occluder that actually hid the body, not always the first
                rect = transition_rect(config, j, tr.x[j - 1], tr.y[j - 1],
                                       tr.x[j], tr.y[j], entering=False)
                # no rectangle crossing: either a polygon edge or a sweep
                side = "sweep" if rect is None else _exit_side(rect, tr.x[j], tr.y[j])
                edge = None
                if rect is None:
                    for poly in config.poly_o:
                        found = crossed_poly_edge(poly, tr.x[j - 1], tr.y[j - 1],
                                                  tr.x[j], tr.y[j])
                        if found is not None:
                            edge = found
                            side = f"poly{found[0]}"
                            break
                # `pos` is the ball's position at the first step it is visible
                # again: observable, and the only coordinate pair that can
                # distinguish two relabeled worlds with equal velocities
                # (prereg amendment A2, 2026-11-21).
                attrs = {
                    "side": side,
                    "v": v,
                    "pos": [round(tr.x[j], 6), round(tr.y[j], 6)],
                    "dt": config.dt,
                    **({} if edge is None else {"edge": edge[0], "normal": list(edge[1])}),
                    # First TRACK_SAMPLES visible steps after the exit: the ball is
                    # visible and its positions are observable, and averaging a
                    # least-squares velocity over them costs the sensor noise by
                    # sqrt(n) (round 9).
                    "track": [[round(tr.x[s], 6), round(tr.y[s], 6)]
                              for s in range(j, min(j + TRACK_SAMPLES, len(tr.x)))],
                }
                emit(oracle, "exit_occ", j, (f"b{i}",), attrs, True)
                t_obs, obs_attrs = _lagged_attrs(config, tr, j, attrs, entering=False)
                emit(obs, "exit_occ", t_obs, ("ball",), obs_attrs, True)
            elif tr.visible[j - 1] and not tr.visible[j]:
                v = _meas_v(tr, config.dt, j - 2, j - 1)
                rect = transition_rect(config, j, tr.x[j - 1], tr.y[j - 1],
                                       tr.x[j], tr.y[j], entering=True)
                side = ("sweep" if rect is None else
                        _enter_side(rect, tr.x[j - 1], tr.y[j - 1], tr.x[j], tr.y[j]))
                edge = None
                if rect is None:
                    for poly in config.poly_o:
                        found = crossed_poly_edge(poly, tr.x[j - 1], tr.y[j - 1],
                                                  tr.x[j], tr.y[j])
                        if found is not None:
                            edge = found
                            side = f"poly{found[0]}"
                            break
                if side == "corner":
                    raise AssertionError("corner entry is not supported; pick axis crossings")
                attrs = {
                    "side": side,
                    "v": v,
                    "pos": [round(tr.x[j - 1], 6), round(tr.y[j - 1], 6)],
                    "dt": config.dt,
                    **({} if edge is None else {"edge": edge[0], "normal": list(edge[1])}),
                    "track": [[round(tr.x[s], 6), round(tr.y[s], 6)]
                              for s in range(max(0, j - TRACK_SAMPLES), j)],
                }
                emit(oracle, "enter_occ", j, (f"b{i}",), attrs, True)
                t_obs, obs_attrs = _lagged_attrs(config, tr, j, attrs, entering=True)
                emit(obs, "enter_occ", t_obs, ("ball",), obs_attrs, True)

    if config.identity_marker:
        channel_down = 0
        for step in range(0, config.steps + 1, config.marker_period):
            outage_here = False
            if channel_down > 0:
                channel_down -= 1
                outage_here = True
            elif config.marker_outage_prob > 0.0 and \
                    marker_rng.random() < config.marker_outage_prob:
                channel_down = config.marker_outage_len - 1
                outage_here = True
            if outage_here:
                continue
            for i, tr in enumerate(trajs):
                if step >= len(tr.visible) or not tr.visible[step]:
                    continue
                if config.marker_reliability < 1.0 and \
                        marker_rng.random() >= config.marker_reliability:
                    continue
                attrs = {"tag": f"B{i}" if i else "A",
                         "pos": [round(tr.x[step], 6), round(tr.y[step], 6)]}
                emit(oracle, "marker", step, (f"b{i}",), attrs, True)
                emit(obs, "marker", step, ("ball",), dict(attrs), True)

    for (t, i, side) in bounces:
        tr = trajs[i]
        k = min(t, len(tr.vx) - 1)
        v = [round(tr.vx[k], 6), round(tr.vy[k], 6)]
        emit(oracle, "wall_bounce", t, (f"b{i}",), {"side": side, "v": v}, True)
        emit(obs, "wall_bounce", t, ("ball",), {"side": side, "v": v}, True)

    for (t, i, j) in collisions:
        a, b = trajs[i], trajs[j]
        both = a.visible[t] and b.visible[t]
        emit(oracle, "ball_collide", t, (f"b{i}", f"b{j}"),
             {"x_a": [round(a.x[t], 6), round(a.y[t], 6)],
              "x_b": [round(b.x[t], 6), round(b.y[t], 6)],
              "v_a_after": [round(a.vx[t], 6), round(a.vy[t], 6)],
              "v_b_after": [round(b.vx[t], 6), round(b.vy[t], 6)]}, both)
        if both:
            emit(obs, "ball_collide", t, ("ball", "ball"),
                 {"x_a": [round(a.x[t], 6), round(a.y[t], 6)],
                  "x_b": [round(b.x[t], 6), round(b.y[t], 6)]}, True)

    return SimEpisode(config, seed, episode, trajs, applied, skipped, init, obs, oracle)
