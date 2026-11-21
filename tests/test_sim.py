import json

import pytest

from psychopomp.sim import Init, Kick, SimConfig, run

CFG = SimConfig()          # W=H=100, occluder x[40,60] y[35,65]
CFG_LONG = SimConfig(steps=150)
CFG_PASS = SimConfig(steps=140)

STRAIGHT = Init(x=(20.0, 20.0), y=(50.0, 80.0), v=((3.0, 0.0), (3.0, 0.0)))
OFF_AXIS = Init(x=(20.0, 52.0), y=(45.0, 20.0), v=((3.0, 1.0), (0.0, 3.3)))


def observable_text(ep):
    lines = []
    for e in ep.observable_log().events:
        lines.append(
            json.dumps(
                {"kind": e.kind, "t": e.t, "subjects": list(e.subjects),
                 "attrs": e.attrs, "observable": e.observable, "seq": e.seq},
                sort_keys=True,
            )
        )
    return "\n".join(lines)


def test_determinism_same_seed():
    a = run(CFG_LONG, seed=7)
    b = run(CFG_LONG, seed=7)
    assert observable_text(a) == observable_text(b)


def test_observable_log_is_identity_free():
    ep = run(CFG_LONG, seed=7)
    for e in ep.observable_log():
        assert all(s == "ball" for s in e.subjects), e
    assert any(any(s.startswith("b") for s in e.subjects) for e in ep.oracle_log())


def test_straight_pass_single_crossing():
    ep = run(CFG_PASS, seed=0, init=STRAIGHT)
    obs = ep.observable_log()
    enters = [e for e in obs if e.kind == "enter_occ"]
    exits = [e for e in obs if e.kind == "exit_occ"]
    assert len(enters) == 1 and len(exits) == 1
    # `pos` is the observable boundary position (prereg amendment A2). It is
    # schema, not decoration: it is the only coordinate pair that distinguishes
    # relabeled worlds whose velocities agree.
    assert enters[0].attrs["side"] == "left"
    assert enters[0].attrs["v"] == [3.0, 0.0]
    assert enters[0].attrs["pos"][1] == 50.0
    assert enters[0].attrs["pos"][0] < 40.0  # last visible step before the occluder
    assert exits[0].attrs["side"] == "right"
    assert exits[0].attrs["v"] == [3.0, 0.0]
    assert exits[0].attrs["pos"][1] == 50.0
    assert exits[0].attrs["pos"][0] > 60.0   # first visible step after it
    assert enters[0].t < exits[0].t
    assert not [e for e in ep.oracle_log() if e.kind == "ball_collide"]


def test_off_axis_contact_is_hidden_but_shaped():
    ep = run(CFG_LONG, seed=0, init=OFF_AXIS)
    hidden = [e for e in ep.oracle_log() if e.kind == "ball_collide" and not e.observable]
    assert hidden, "off-axis scenario must contact inside the occluder"
    assert not [
        e for e in ep.oracle_log() if e.kind == "ball_collide" and e.observable
    ], "the contact itself must stay hidden"
    obs = ep.observable_log()
    assert len([e for e in obs if e.kind == "enter_occ"]) == 2
    assert len([e for e in obs if e.kind == "exit_occ"]) == 2


def test_kick_on_hidden_ball_is_skipped_and_hidden():
    ep = run(
        CFG_LONG,
        seed=0,
        init=Init(x=(38.0, 80.0), y=(50.0, 50.0), v=((3.0, 0.0), (3.0, 0.0))),
        kicks=(Kick(t=10, ball=0, dv=(0.3, 0.0)),),
    )
    assert ep.skipped_kicks and ep.skipped_kicks[0].t == 10
    assert not [e for e in ep.observable_log() if e.kind == "kick"]
    assert [e for e in ep.oracle_log() if e.kind == "kick_skipped"]


def test_kick_on_visible_ball_is_observable():
    ep = run(CFG_LONG, seed=0, init=STRAIGHT, kicks=(Kick(t=0, ball=0, dv=(0.2, 0.1)),))
    kicks = [e for e in ep.observable_log() if e.kind == "kick"]
    assert len(kicks) == 1 and kicks[0].attrs["dv"] == [0.2, 0.1]


def test_wall_bounce_observable():
    ep = run(CFG_LONG, seed=0, init=Init(x=(5.0, 90.0), y=(5.0, 90.0), v=((-3.0, -3.0), (3.0, 3.0))))
    bounces = [e for e in ep.observable_log() if e.kind == "wall_bounce"]
    assert bounces and {b.attrs["side"] for b in bounces} >= {"left", "top"}


def test_config_rejects_tunneling():
    with pytest.raises(AssertionError):
        SimConfig(speed=300.0)  # speed*dt = 30 >= occluder width 20
