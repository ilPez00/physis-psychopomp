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
    o2: Optional[Tuple[float, float, float, float]] = None
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


def observable(cfg: SimConfig, x: float, y: float) -> bool:
    """Visible to at least one observer: hidden only where every occluder covers."""
    if not inside_rect(cfg.o, x, y):
        return True
    return cfg.o2 is not None and not inside_rect(cfg.o2, x, y)


def occluders(cfg: SimConfig) -> Tuple[Tuple[float, float, float, float], ...]:
    return (cfg.o,) if cfg.o2 is None else (cfg.o, cfg.o2)


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
        assert observable(config, px, py), "init must be observable"
    trajs = [
        Trajectory(x=[xs[i]], y=[ys[i]], vx=[vs[i][0]], vy=[vs[i][1]], visible=[True])
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
            trajs[i].visible.append(observable(config, trajs[i].x[-1], trajs[i].y[-1]))

    prov = Provenance(source, config.sha256(), seed, episode)
    oracle, obs = EventLog(), EventLog()

    # Int-only derivation on purpose: hashing a string makes the seed depend on
    # PYTHONHASHSEED, which is randomised per process. Measured 2026-11-21 --
    # the noise arm scored 0.17 locally and 0.33 on CI for identical inputs.
    # The base RNG above is safe because its tuple holds ints only.
    noise_rng = random.Random((seed * 1000003 + episode * 7919 + 17) % (2**63))
    # A separate stream for `track`: sharing one stream means adding an attribute
    # silently re-rolls every later draw, so pinned cross-process numbers move
    # whenever the log schema grows (measured 2026-11-21).
    track_rng = random.Random((seed * 1000033 + episode * 104729 + 29) % (2**63))

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
                rect = next(r for r in occluders(config)
                            if inside_rect(r, tr.x[j - 1], tr.y[j - 1])
                            and not inside_rect(r, tr.x[j], tr.y[j]))
                side = _exit_side(rect, tr.x[j], tr.y[j])
                # `pos` is the ball's position at the first step it is visible
                # again: observable, and the only coordinate pair that can
                # distinguish two relabeled worlds with equal velocities
                # (prereg amendment A2, 2026-11-21).
                attrs = {
                    "side": side,
                    "v": v,
                    "pos": [round(tr.x[j], 6), round(tr.y[j], 6)],
                    "dt": config.dt,
                    # First TRACK_SAMPLES visible steps after the exit: the ball is
                    # visible and its positions are observable, and averaging a
                    # least-squares velocity over them costs the sensor noise by
                    # sqrt(n) (round 9).
                    "track": [[round(tr.x[s], 6), round(tr.y[s], 6)]
                              for s in range(j, min(j + TRACK_SAMPLES, len(tr.x)))],
                }
                emit(oracle, "exit_occ", j, (f"b{i}",), attrs, True)
                emit(obs, "exit_occ", j, ("ball",), attrs, True)
            elif tr.visible[j - 1] and not tr.visible[j]:
                v = _meas_v(tr, config.dt, j - 2, j - 1)
                rect = next(r for r in occluders(config)
                            if inside_rect(r, tr.x[j], tr.y[j])
                            and not inside_rect(r, tr.x[j - 1], tr.y[j - 1]))
                side = _enter_side(rect, tr.x[j - 1], tr.y[j - 1], tr.x[j], tr.y[j])
                if side == "corner":
                    raise AssertionError("corner entry is not supported; pick axis crossings")
                attrs = {
                    "side": side,
                    "v": v,
                    "pos": [round(tr.x[j - 1], 6), round(tr.y[j - 1], 6)],
                    "dt": config.dt,
                    "track": [[round(tr.x[s], 6), round(tr.y[s], 6)]
                              for s in range(max(0, j - TRACK_SAMPLES), j)],
                }
                emit(oracle, "enter_occ", j, (f"b{i}",), attrs, True)
                emit(obs, "enter_occ", j, ("ball",), attrs, True)

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
