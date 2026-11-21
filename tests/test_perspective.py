import json
import math

from psychopomp.epec import summarize
from psychopomp.fixtures import OFF_AXIS, STRAIGHT, PASS_CFG, recrossing_episode
from psychopomp.perspective import (
    ball_frame,
    origin_at,
    random_frame,
    to_frame_point,
    to_frame_velocity,
    to_world_point,
    to_world_velocity,
    transform_observable,
    world_frame,
)
from psychopomp.sim import run


class _Shim:
    def __init__(self, log):
        self._log = log

    def observable_log(self):
        return self._log


def ep_contact():
    return run(PASS_CFG, 0, init=OFF_AXIS)


def ep_straight():
    return run(PASS_CFG, 0, init=STRAIGHT)


def test_point_and_velocity_roundtrip():
    ep = ep_straight()
    for frame in (world_frame(), random_frame(3), ball_frame(ep, 0), ball_frame(ep, 1)):
        for t in (0.0, 5.0, 9.3):
            p = (12.5, -3.25)
            q = to_frame_point(frame, p, t)
            back = to_world_point(frame, q, t)
            assert abs(back[0] - p[0]) < 1e-9 and abs(back[1] - p[1]) < 1e-9
            v = (3.0, 1.5)
            w = to_frame_velocity(frame, v, t)
            vb = to_world_velocity(frame, w, t)
            assert abs(vb[0] - v[0]) < 1e-9 and abs(vb[1] - v[1]) < 1e-9


def test_world_frame_is_identity():
    ep = ep_straight()
    log = transform_observable(ep, world_frame())
    assert [e.attrs for e in log] == [e.attrs for e in ep.observable_log()]


def test_log_roundtrip_through_random_frame():
    ep = ep_contact()
    frame = random_frame(11)
    moved = transform_observable(ep, frame)
    back = transform_observable(_Shim(moved), frame, inverse=True)
    for a, b in zip(back, ep.observable_log()):
        assert a.kind == b.kind and a.t == b.t
        for key, value in b.attrs.items():
            if isinstance(value, list) and value and isinstance(value[0], (list, tuple)):
                for pa, pb in zip(a.attrs[key], value):
                    assert abs(pa[0] - pb[0]) < 1e-5 and abs(pa[1] - pb[1]) < 1e-5
            elif isinstance(value, list):
                assert abs(a.attrs[key][0] - value[0]) < 1e-5
                assert abs(a.attrs[key][1] - value[1]) < 1e-5
            else:
                assert a.attrs[key] == value


def test_relative_geometry_preserved():
    ep = ep_contact()
    obs = ep.observable_log()
    events = [e for e in obs if e.attrs.get("pos") is not None]
    frame = random_frame(5)
    for i, e1 in enumerate(events):
        for e2 in events[i + 1:]:
            if e1.t != e2.t:
                continue
            p1, p2 = e1.attrs["pos"], e2.attrs["pos"]
            q1 = to_frame_point(frame, p1, e1.t * frame.dt)
            q2 = to_frame_point(frame, p2, e2.t * frame.dt)
            d0 = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            d1 = math.hypot(q1[0] - q2[0], q1[1] - q2[1])
            assert abs(d0 - d1) < 1e-5


def test_random_frame_is_deterministic():
    ep = ep_contact()
    a = transform_observable(ep, random_frame(42))
    b = transform_observable(ep, random_frame(42))
    assert [json.dumps(e.attrs, sort_keys=True) for e in a] == [
        json.dumps(e.attrs, sort_keys=True) for e in b
    ]


def test_oracle_untouched_and_identity_private():
    ep = ep_contact()
    before = [json.dumps(e.attrs, sort_keys=True) for e in ep.oracle_log()]
    for frame in (random_frame(1), ball_frame(ep, 0)):
        log = transform_observable(ep, frame)
        assert all(s == "ball" for e in log for s in e.subjects)
    after = [json.dumps(e.attrs, sort_keys=True) for e in ep.oracle_log()]
    assert before == after


def test_ball_frame_origin_is_proprioceptive():
    ep = ep_contact()
    frame = ball_frame(ep, 0)
    for k in (0, 10, 50):
        (ox, oy), (vx, vy) = origin_at(frame, k * ep.config.dt)
        assert abs(ox - ep.trajs[0].x[k]) < 1e-9
        assert abs(oy - ep.trajs[0].y[k]) < 1e-9


def test_world_count_invariant_under_inertial_frames():
    # world and randomized (constant rotation + linear drift) frames are
    # inertial: the filter's world set must be unchanged on both episodes.
    # A body frame is inertial only between that body's own bounces -- the
    # straight episode's ball 0 never bounces, so it is included there; the
    # re-crossing episode's ball 0 does bounce, and is deliberately not used
    # (the filter is defined for inertial frames; R-P1.3/A4 must state that).
    for ep in (ep_contact(), recrossing_episode()):
        base = summarize(ep.observable_log())
        for frame in (world_frame(), random_frame(8)):
            got = summarize(transform_observable(ep, frame))
            assert got["n_worlds"] == base["n_worlds"], (ep.episode, frame.kind)
            assert got["contact_required"] == base["contact_required"]
    ep = ep_straight()
    base = summarize(ep.observable_log())
    got = summarize(transform_observable(ep, ball_frame(ep, 0)))
    assert got["n_worlds"] == base["n_worlds"]
    assert got["contact_required"] == base["contact_required"]
