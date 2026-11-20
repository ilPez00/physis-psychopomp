"""Ball-in-corridor simulator with strict observable/oracle separation.

1D corridor [0, L]. An occluder hides a ball while its centre is inside
[o_lo, o_hi]. Physics: constant velocity, elastic wall bounces, elastic
identical-mass ball collisions (velocity exchange). External actions are
velocity kicks, applied only to balls that are visible at that step, so no
action is ever hidden from the camera.

Two visually identical balls: the observable log is identity-free. Which
invisible trajectory connects which entry to which exit is exactly the
possible-world question the downstream filter enumerates.

Data products (oracle-leakage control):
  observable_log()  -- camera-measurable, identity-free events only
  oracle_log()      -- labelled events including hidden contacts;
                       evaluation only, never a training input
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .eventlog import Event, EventLog, Provenance


@dataclass(frozen=True)
class SimConfig:
    L: float = 100.0
    o_lo: float = 40.0
    o_hi: float = 60.0
    r: float = 1.0
    dt: float = 0.25
    steps: int = 400
    speed: float = 4.0
    n_balls: int = 2

    def __post_init__(self) -> None:
        assert self.r > 0 and 0 < self.o_lo < self.o_hi < self.L - self.r, (
            "occluder must sit strictly inside the walls (no bounce inside)"
        )

    def canonical(self) -> str:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        return json.dumps(d, sort_keys=True)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


@dataclass(frozen=True)
class Init:
    """Scripted initial state (positions, velocities). Overrides random init."""

    x: Tuple[float, ...]
    v: Tuple[float, ...]


@dataclass(frozen=True)
class Kick:
    t: int
    ball: int
    dv: float


@dataclass
class Trajectory:
    x: List[float]
    v: List[float]
    visible: List[bool]


class SimEpisode:
    def __init__(
        self,
        config: SimConfig,
        seed: int,
        episode: int,
        trajs: List[Trajectory],
        applied_kicks: Sequence[Kick],
        skipped_kicks: Sequence[Kick],
        init: Optional[Init],
        obs: EventLog,
        oracle: EventLog,
    ) -> None:
        self.config = config
        self.seed = seed
        self.episode = episode
        self.trajs = trajs
        self.applied_kicks = list(applied_kicks)
        self.skipped_kicks = list(skipped_kicks)
        self.init = init
        self._obs = obs
        self._oracle = oracle
        self.prov = Provenance(
            source="sim:v0.1",
            config_sha256=config.sha256(),
            seed=seed,
            episode=episode,
        )

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


def _meas_v(tr: Trajectory, dt: float, before: int, after: int) -> Optional[float]:
    """Velocity a camera would measure from two visible frames; None if lacking."""
    a, b = before, after
    if a < 0 or b >= len(tr.x) or not tr.visible[a] or not tr.visible[b]:
        return None
    return round((tr.x[b] - tr.x[a]) / dt, 6)


def run(
    config: SimConfig,
    seed: int,
    episode: int = 0,
    init: Optional[Init] = None,
    kicks: Sequence[Kick] = (),
) -> SimEpisode:
    rng = random.Random(hash((seed, episode)) % (2**63))
    n = config.n_balls

    if init is not None:
        assert len(init.x) == n and len(init.v) == n
        xs, vs = list(init.x), list(init.v)
    else:
        xs, vs = [], []
        for _ in range(n):
            if rng.random() < 0.5:
                lo, hi = config.r + 1.0, config.o_lo - 2.0
            else:
                lo, hi = config.o_hi + 2.0, config.L - config.r - 1.0
            xs.append(rng.uniform(lo, hi))
            vs.append(config.speed * (1 if rng.random() < 0.5 else -1))
    for x in xs:
        assert config.r <= x <= config.L - config.r, "init outside corridor"
        assert not (config.o_lo <= x <= config.o_hi), "init must be visible"

    trajs = [Trajectory(x=[xs[i]], v=[vs[i]], visible=[True]) for i in range(n)]

    applied: List[Kick] = []
    skipped: List[Kick] = []
    bounces: List[Tuple[int, int, str]] = []
    collisions: List[Tuple[int, int, int]] = []

    for t in range(config.steps):
        for k in kicks:
            if k.t == t:
                if trajs[k.ball].visible[-1]:
                    trajs[k.ball].v[-1] += k.dv
                    applied.append(k)
                else:
                    skipped.append(k)
        for i in range(n):
            tr = trajs[i]
            tr.x.append(tr.x[-1] + tr.v[-1] * config.dt)
            tr.v.append(tr.v[-1])
        for i in range(n):
            tr = trajs[i]
            x, v = tr.x[-1], tr.v[-1]
            if x < config.r:
                tr.x[-1] = 2 * config.r - x
                tr.v[-1] = -v
                bounces.append((t + 1, i, "left"))
            elif x > config.L - config.r:
                tr.x[-1] = 2 * (config.L - config.r) - x
                tr.v[-1] = -v
                bounces.append((t + 1, i, "right"))
        for i in range(n):
            for j in range(i + 1, n):
                a, b = trajs[i], trajs[j]
                if abs(a.x[-1] - b.x[-1]) < 2 * config.r:
                    # equal masses: exchange velocities on any overlap where
                    # they differ (handles exact-meet crossings)
                    if a.v[-1] != b.v[-1]:
                        a.v[-1], b.v[-1] = b.v[-1], a.v[-1]
                        collisions.append((t + 1, i, j))
                    if abs(a.x[-1] - b.x[-1]) < 2 * config.r:
                        d = (2 * config.r - abs(a.x[-1] - b.x[-1])) / 2
                        if a.x[-1] <= b.x[-1]:
                            a.x[-1] -= d
                            b.x[-1] += d
                        else:
                            a.x[-1] += d
                            b.x[-1] -= d
        for i in range(n):
            x = trajs[i].x[-1]
            trajs[i].visible.append(not (config.o_lo <= x <= config.o_hi))

    # ---- event logs (identity discipline: observable = camera-measurable) --
    oracle, obs = EventLog(), EventLog()

    def emit(log: EventLog, kind: str, t: int, subjects: Tuple[str, ...],
             attrs: dict, observable: bool) -> None:
        log.add(Event(kind, t, subjects, attrs, observable, _prov))

    _prov = Provenance("sim:v0.1", config.sha256(), seed, episode)

    for k in applied:
        tr = trajs[k.ball]
        attrs = {"x": round(tr.x[k.t + 1], 6), "dv": k.dv}
        emit(oracle, "kick", k.t, (f"b{k.ball}",), attrs, True)
        emit(obs, "kick", k.t, ("ball",), attrs, True)
    for k in skipped:
        emit(oracle, "kick_skipped", k.t, (f"b{k.ball}",), {"dv": k.dv}, False)

    for i, tr in enumerate(trajs):
        for j in range(1, len(tr.visible)):
            if tr.visible[j] and not tr.visible[j - 1]:  # exit: first visible frame
                v = _meas_v(tr, config.dt, j, j + 1)
                side = "left" if tr.x[j] < config.o_lo else "right"
                emit(oracle, "exit_occ", j, (f"b{i}",), {"side": side, "v": v}, True)
                emit(obs, "exit_occ", j, ("ball",), {"side": side, "v": v}, True)
            elif tr.visible[j - 1] and not tr.visible[j]:  # enter: first hidden frame
                assert abs(tr.x[j] - tr.x[j - 1]) < (config.o_hi - config.o_lo), (
                    "tunneling: one step crossed the whole occluder"
                )
                v = _meas_v(tr, config.dt, j - 2, j - 1)
                side = "left" if tr.x[j - 1] < config.o_lo else "right"
                emit(oracle, "enter_occ", j, (f"b{i}",), {"side": side, "v": v}, True)
                emit(obs, "enter_occ", j, ("ball",), {"side": side, "v": v}, True)

    for (t, i, side) in bounces:
        tr = trajs[i]
        v = round(tr.v[min(t, len(tr.v) - 1)], 6)
        emit(oracle, "wall_bounce", t, (f"b{i}",), {"side": side, "v": v}, True)
        emit(obs, "wall_bounce", t, ("ball",), {"side": side, "v": v}, True)

    for (t, i, j) in collisions:
        a, b = trajs[i], trajs[j]
        both_vis = a.visible[t] and b.visible[t]
        emit(oracle, "ball_collide", t, (f"b{i}", f"b{j}"),
             {"x_a": round(a.x[t], 6), "x_b": round(b.x[t], 6),
              "v_a_after": round(a.v[t], 6), "v_b_after": round(b.v[t], 6)},
             both_vis)
        if both_vis:
            emit(obs, "ball_collide", t, ("ball", "ball"),
                 {"x_a": round(a.x[t], 6), "x_b": round(b.x[t], 6)}, True)

    return SimEpisode(config, seed, episode, trajs, applied, skipped, init, obs, oracle)
