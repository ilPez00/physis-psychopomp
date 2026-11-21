"""Camera-layer degradation (R-P1.3): quantization, jitter, missing auxiliary
observations. Applied to the observable log only; the oracle log is never
read here.

- ``quantize``: every positional/velocity component is rounded to a grid in
  the coordinates the log is already in. A grid is frame-dependent — it does
  not commute with rotation — so quantization after a frame change is a
  different sensor, not the same one. Reported, never smoothed over.
- ``jitter``: independent uniform ``+-magnitude/2`` per component, own seeded
  stream (adding a degradation must not re-roll another one's draws).
- ``drop_aux``: seeded drop of auxiliary events (``wall_bounce``, ``kick``).
  Never touches ``enter_occ``/``exit_occ``: the filter reads only those, so
  the enumeration must be invariant, and a test pins it.
- Identity ambiguity needs no code: observable events carry no labels.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Optional

from .eventlog import Event, EventLog

POINT_KEYS = ("pos", "x", "x_a", "x_b")
VELOCITY_KEYS = ("v", "dv", "v_a_after", "v_b_after")
AUX_KINDS = frozenset({"wall_bounce", "kick"})


@dataclass
class CameraView:
    """An episode as a camera saw it: degraded observable log + the rest."""

    _ep: object
    _log: EventLog

    def observable_log(self) -> EventLog:
        return self._log

    def __getattr__(self, name):
        return getattr(self._ep, name)


def _snap(value: float, unit: float) -> float:
    if unit <= 0:
        return value
    return round(round(value / unit) * unit, 6)


def _transform_value(kind: str, value, fn):
    if value is None:
        return None
    if kind in POINT_KEYS:
        return [fn(value[0]), fn(value[1])] if isinstance(value, (list, tuple)) else value
    if kind in VELOCITY_KEYS:
        return [fn(value[0]), fn(value[1])] if isinstance(value, (list, tuple)) else value
    return value


def quantize(log: EventLog, unit: float) -> EventLog:
    out = EventLog()
    for e in log:
        attrs = dict(e.attrs)
        for key in POINT_KEYS + VELOCITY_KEYS:
            if key in attrs:
                attrs[key] = _transform_value(key, attrs[key], lambda v: _snap(v, unit))
        if attrs.get("track") is not None:
            attrs["track"] = [[_snap(p[0], unit), _snap(p[1], unit)] for p in attrs["track"]]
        out.add(Event(e.kind, e.t, e.subjects, attrs, e.observable, e.provenance, e.seq))
    return out


def jitter(log: EventLog, magnitude: float, seed: int = 0) -> EventLog:
    if magnitude <= 0:
        return EventLog(list(log.events))
    rng = random.Random(seed)
    out = EventLog()
    for e in log:
        attrs = dict(e.attrs)

        def noise(v: float) -> float:
            return round(v + rng.uniform(-magnitude / 2, magnitude / 2), 6)

        for key in POINT_KEYS + VELOCITY_KEYS:
            if key in attrs:
                attrs[key] = _transform_value(key, attrs[key], noise)
        if attrs.get("track") is not None:
            attrs["track"] = [[noise(p[0]), noise(p[1])] for p in attrs["track"]]
        out.add(Event(e.kind, e.t, e.subjects, attrs, e.observable, e.provenance, e.seq))
    return out


def drop_aux(log: EventLog, rate: float, seed: int = 0) -> EventLog:
    if rate <= 0:
        return EventLog(list(log.events))
    rng = random.Random(seed)
    out = EventLog()
    for e in log:
        if e.kind in AUX_KINDS and rng.random() < rate:
            continue
        out.add(e)
    return out


def degrade(
    log: EventLog,
    quantize_unit: float = 0.0,
    jitter_magnitude: float = 0.0,
    drop_rate: float = 0.0,
    seed: int = 0,
) -> EventLog:
    out = quantize(log, quantize_unit)
    out = jitter(out, jitter_magnitude, seed=seed)
    out = drop_aux(out, drop_rate, seed=seed + 1)
    return out
