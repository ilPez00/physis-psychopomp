from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, observable, run

HIDDEN_KICK = Intervention(t=60, ball=0, dv=(0.0, 1.5))
VISIBLE_KICK = Intervention(t=30, ball=0, dv=(0.0, 1.5))
INIT = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
DISJOINT = (0.0, 20.0, 0.0, 20.0)


def test_blind_region_is_the_intersection_of_occluders():
    cfg = SimConfig(o2=(50.0, 70.0, 35.0, 65.0))
    # inside the first occluder only -> observer 2 sees it
    assert observable(cfg, 45.0, 50.0) is True
    # inside both -> blind
    assert observable(cfg, 55.0, 50.0) is False
    # outside both -> visible
    assert observable(cfg, 10.0, 10.0) is True
    assert observable(SimConfig(), 45.0, 50.0) is False


def test_single_observer_cannot_identify_a_hidden_kick():
    cfg = SimConfig(steps=200)
    ep = run(cfg, 0, init=INIT, kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
    out = attribute(ep, [HIDDEN_KICK, None], cfg, 0, INIT)
    assert out["unique"] is False
    assert len(out["ambiguity"]) == 2


def test_second_observer_with_a_different_blind_spot_identifies_it():
    cfg = SimConfig(steps=200, o2=DISJOINT)
    ep = run(cfg, 0, init=INIT, kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
    out = attribute(ep, [HIDDEN_KICK, None], cfg, 0, INIT)
    assert out["unique"] is True and out["best"] == HIDDEN_KICK
    assert out["margin"] > 0.0


def test_second_observer_with_the_same_blind_spot_changes_nothing():
    a = SimConfig(steps=200)
    b = SimConfig(steps=200, o2=a.o)
    ea = run(a, 0, init=INIT, kicks=(Kick(HIDDEN_KICK.t, 0, HIDDEN_KICK.dv),))
    eb = run(b, 0, init=INIT, kicks=(Kick(HIDDEN_KICK.t, 0, HIDDEN_KICK.dv),))
    assert ea.skipped_kicks == eb.skipped_kicks
    assert [(e.kind, e.t, e.attrs) for e in ea.observable_log()] == \
           [(e.kind, e.t, e.attrs) for e in eb.observable_log()]


def test_observation_does_not_change_physics():
    a = run(SimConfig(steps=200), 0, init=INIT)
    b = run(SimConfig(steps=200, o2=DISJOINT), 0, init=INIT)
    for ta, tb in zip(a.trajs, b.trajs):
        assert (ta.x, ta.y, ta.vx, ta.vy) == (tb.x, tb.y, tb.vx, tb.vy)


def test_crossing_side_is_labelled_against_the_occluder_that_hid_the_body():
    # a body already inside the first occluder crosses into the overlapping
    # second one: the transition is caused by o2, so its side must be labelled
    # against o2 (run 1 raised "corner entry is not supported" here)
    cfg = SimConfig(steps=120, o2=(50.0, 70.0, 35.0, 65.0))
    init = Init(x=(45.0, 10.0), y=(50.0, 80.0), v=((3.0, 0.0), (0.0, 0.0)))
    ep = run(cfg, 0, init=init)
    kinds = [(e.kind, e.attrs.get("side")) for e in ep.observable_log()
             if e.kind in ("enter_occ", "exit_occ")]
    assert ("enter_occ", "left") in kinds


def test_identifiability_tracks_event_location_not_blind_area():
    # R-P1.10: the same observer set (overlap-450, blind x >= 45) resolves a
    # kick at x=42 and ties at x=46. Blind area is a proxy, not the variable.
    cfg = SimConfig(steps=200, o2=(45.0, 65.0, 35.0, 65.0))
    visible_init = Init(x=(24.0, 28.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
    blind_init = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
    for init, expect_unique in ((visible_init, True), (blind_init, False)):
        ep = run(cfg, 0, init=init, kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
        out = attribute(ep, [HIDDEN_KICK, None], cfg, 0, init)
        scores = {str(h): d for d, h in out["scores"]}
        assert out["unique"] is expect_unique
        if expect_unique:
            assert scores[str(None)] > 0.0 and out["margin"] > 0.0
        else:
            assert scores[str(None)] == 0.0 == scores[str(HIDDEN_KICK)]
            assert len(out["ambiguity"]) == 2


def test_per_event_coverage_rule_on_a_boundary_free_cell():
    # R-P1.12: bv-c blinds only lane y=51 (x in [40.5,60], y in [46.5,65]).
    # Same blind area for both lanes, opposite outcome: coverage is per event.
    cfg = SimConfig(steps=200, o2=(40.5, 60.5, 46.5, 70.0))
    init = Init(x=(23.0, 27.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
    for lane, expect_unique in ((0, True), (1, False)):
        true = Intervention(t=60, ball=lane, dv=(0.0, 1.5))
        ep = run(cfg, 23, init=init, kicks=(Kick(60, lane, (0.0, 1.5)),))
        out = attribute(ep, [true, None], cfg, 23, init)
        assert out["unique"] is expect_unique
