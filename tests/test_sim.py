import json

from psychopomp.sim import Init, Kick, SimConfig, run

CFG = SimConfig()  # L=100, occluder [40,60], dt=.25, speed=4, 2 balls
CFG45 = SimConfig(steps=45)  # single-crossing canonical episodes


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
    a = run(CFG, seed=7)
    b = run(CFG, seed=7)
    assert observable_text(a) == observable_text(b)


def test_observable_log_is_identity_free():
    ep = run(CFG, seed=7)
    for e in ep.observable_log():
        assert all(s == "ball" for s in e.subjects), e
    # oracle carries simulator labels
    assert any(
        any(s.startswith("b") for s in e.subjects) for e in ep.oracle_log()
    )


def test_no_hidden_contacts_in_observable_log():
    ep = run(
        CFG,
        seed=0,
        init=Init(x=(30.0, 70.0), v=(4.0, -4.0)),  # collide inside occluder
    )
    oracle_collides = [e for e in ep.oracle_log() if e.kind == "ball_collide"]
    assert oracle_collides, "scenario must produce a hidden contact"
    assert all(not e.observable for e in oracle_collides)
    assert not [e for e in ep.observable_log() if e.kind == "ball_collide"]


def test_straight_pass_events():
    ep = run(CFG45, seed=0, init=Init(x=(20.0, 80.0), v=(4.0, 4.0)))
    obs = ep.observable_log()
    enters = [e for e in obs if e.kind == "enter_occ"]
    exits = [e for e in obs if e.kind == "exit_occ"]
    assert len(enters) == 1 and len(exits) == 1
    assert enters[0].attrs == {"side": "left", "v": 4.0}
    assert exits[0].attrs["side"] == "right" and exits[0].attrs["v"] == 4.0
    assert enters[0].t < exits[0].t


def test_kick_on_hidden_ball_is_skipped_and_hidden():
    ep = run(
        CFG,
        seed=0,
        init=Init(x=(39.0, 80.0), v=(8.0, 4.0)),
        kicks=(Kick(t=2, ball=0, dv=1.0),),
    )
    assert ep.skipped_kicks and ep.skipped_kicks[0].t == 2
    assert not [e for e in ep.observable_log() if e.kind == "kick"]
    assert [e for e in ep.oracle_log() if e.kind == "kick_skipped"]


def test_kick_on_visible_ball_is_observable():
    ep = run(
        CFG,
        seed=0,
        init=Init(x=(20.0, 80.0), v=(4.0, 4.0)),
        kicks=(Kick(t=0, ball=0, dv=1.0),),
    )
    kicks = [e for e in ep.observable_log() if e.kind == "kick"]
    assert len(kicks) == 1 and kicks[0].attrs["dv"] == 1.0


def test_wall_bounce_observable():
    ep = run(CFG, seed=0, init=Init(x=(20.0, 5.0), v=(4.0, -4.0)))
    bounces = [e for e in ep.observable_log() if e.kind == "wall_bounce"]
    assert bounces and any(b.attrs["side"] == "left" for b in bounces)


def test_no_tunneling_through_occluder():
    ep = run(CFG, seed=1)
    for tr in ep.trajs:
        for j in range(1, len(tr.visible)):
            if tr.visible[j - 1] and not tr.visible[j]:
                assert abs(tr.x[j] - tr.x[j - 1]) < CFG.o_hi - CFG.o_lo
