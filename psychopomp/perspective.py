"""Observer-relative observation frames (mission P1, R-P1.2).

The world is unchanged; only the OBSERVATION changes. Four frames:

- ``world``          identity (world coordinates);
- ``ball:<i>``       origin on the reference ball's own trajectory -- this is
                     proprioception, not a leak: a body always knows where it
                     is, even while an external camera cannot see it. Other
                     bodies' events are expressed relative to it, so world
                     coordinates remain underdetermined without the frame;
- ``random:<seed>``  seeded rotation + linear drift origin: a declared
                     observer motion, generated from the seed alone;
- (missions P3/P4 may add frames; not here.)

Transform (constant rotation ``theta``, moving origin ``o(t)``):

    p' = R(-theta) (p - o(t))
    v' = R(-theta) (v - o'(t))

Oracle logs are never transformed: identity stays private, and the failed
worlds remain enumerable exactly as before (same-count test in
``tests/test_perspective.py``). No degradation is applied here: sensor noise,
quantization, missing observations and identity ambiguity are R-P1.3.

A body-attached frame is inertial only between that body's own velocity
changes (wall bounces, collisions); across one, velocity continuity changes
and the world set legitimately changes. Inertial frames (world, randomized
constant-rotation/linear-drift) preserve the filter's world count; that is
pinned by tests.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .eventlog import Event, EventLog
from .sim import SimEpisode

Vec = Tuple[float, float]


@dataclass(frozen=True)
class Frame:
    kind: str                       # "world" | "ball" | "random"
    theta: float = 0.0
    ball: Optional[str] = None
    p0: Optional[Vec] = None        # random: origin at t=0
    u: Optional[Vec] = None         # random: origin drift velocity
    xs: Optional[Tuple[float, ...]] = None  # ball: own trajectory samples
    ys: Optional[Tuple[float, ...]] = None
    dt: float = 0.1


def world_frame() -> Frame:
    return Frame("world")


def random_frame(seed: int, theta_span: float = math.pi, speed: float = 1.0) -> Frame:
    rng = random.Random(seed)
    return Frame(
        "random",
        theta=rng.uniform(-theta_span, theta_span),
        p0=(rng.uniform(-20.0, 20.0), rng.uniform(-20.0, 20.0)),
        u=(rng.uniform(-speed, speed), rng.uniform(-speed, speed)),
    )


def ball_frame(ep: SimEpisode, ball: int) -> Frame:
    """Ride on ``ball``: origin is that body's own trajectory (proprioception)."""
    tr = ep.trajs[ball]
    return Frame("ball", ball=f"b{ball}", xs=tuple(tr.x), ys=tuple(tr.y), dt=ep.config.dt)


def origin_at(frame: Frame, t: float) -> Tuple[Vec, Vec]:
    """Return ``(o(t), o'(t))`` for the frame. World frame: ((0,0),(0,0))."""
    if frame.kind == "world":
        return (0.0, 0.0), (0.0, 0.0)
    if frame.kind == "random":
        assert frame.p0 is not None and frame.u is not None
        return (
            (frame.p0[0] + frame.u[0] * t, frame.p0[1] + frame.u[1] * t),
            frame.u,
        )
    if frame.kind == "ball":
        assert frame.xs is not None and frame.ys is not None and frame.xs
        n = len(frame.xs)
        idx = t / frame.dt
        lo = max(0, min(n - 1, int(math.floor(idx))))
        hi = max(0, min(n - 1, lo + 1))
        if hi == lo:
            return (frame.xs[lo], frame.ys[lo]), (0.0, 0.0)
        span = frame.dt * (hi - lo)
        frac = max(0.0, min(1.0, (t - lo * frame.dt) / span))
        px = frame.xs[lo] + (frame.xs[hi] - frame.xs[lo]) * frac
        py = frame.ys[lo] + (frame.ys[hi] - frame.ys[lo]) * frac
        vx = (frame.xs[hi] - frame.xs[lo]) / span
        vy = (frame.ys[hi] - frame.ys[lo]) / span
        return (px, py), (vx, vy)
    raise ValueError(f"unknown frame kind: {frame.kind}")


def _rot(theta: float, v: Vec) -> Vec:
    c, s = math.cos(theta), math.sin(theta)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def to_frame_point(frame: Frame, p: Vec, t: float) -> Vec:
    o, _ = origin_at(frame, t)
    q = _rot(-frame.theta, (p[0] - o[0], p[1] - o[1]))
    return (q[0], q[1])


def to_world_point(frame: Frame, q: Vec, t: float) -> Vec:
    o, _ = origin_at(frame, t)
    r = _rot(frame.theta, q)
    return (r[0] + o[0], r[1] + o[1])


def to_frame_velocity(frame: Frame, v: Vec, t: float) -> Vec:
    _, od = origin_at(frame, t)
    q = _rot(-frame.theta, (v[0] - od[0], v[1] - od[1]))
    return (q[0], q[1])


def to_world_velocity(frame: Frame, q: Vec, t: float) -> Vec:
    _, od = origin_at(frame, t)
    r = _rot(frame.theta, q)
    return (r[0] + od[0], r[1] + od[1])


def transform_observable(ep: SimEpisode, frame: Frame, inverse: bool = False) -> EventLog:
    """Return the observable log as seen from ``frame`` (or invert it).

    Applies to ``pos``/``x``/``x_a``/``x_b`` and track points with the event
    time; applies to ``v``/``dv``/``v_a_after``/``v_b_after`` as velocities.
    Kinds, times, subjects, provenance and scalar attributes (``side``,
    ``dt``) are untouched. The oracle log is not read.
    """
    out = EventLog()
    dtf = frame.dt
    for e in ep.observable_log():
        t = e.t * dtf
        attrs = dict(e.attrs)

        def point(p):
            if p is None:
                return None
            if inverse:
                return _rounded(to_world_point(frame, (p[0], p[1]), t))
            return _rounded(to_frame_point(frame, (p[0], p[1]), t))

        def velocity(v):
            if v is None:
                return None
            if inverse:
                return _rounded(to_world_velocity(frame, (v[0], v[1]), t))
            return _rounded(to_frame_velocity(frame, (v[0], v[1]), t))

        for key in ("pos", "x", "x_a", "x_b"):
            if key in attrs:
                attrs[key] = point(attrs[key])
        for key in ("v", "dv", "v_a_after", "v_b_after"):
            if key in attrs:
                attrs[key] = velocity(attrs[key])
        if attrs.get("track") is not None:
            attrs["track"] = [point(p) for p in attrs["track"]]
        out.add(Event(e.kind, e.t, e.subjects, attrs, e.observable, e.provenance, e.seq))
    return out


def _rounded(p: Vec) -> list:
    return [round(p[0], 6), round(p[1], 6)]
