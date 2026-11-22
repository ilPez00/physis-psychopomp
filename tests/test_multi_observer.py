from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, observable, occluder2_at, run

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


def test_candidates_inherit_the_observation_episode_index():
    # R-P1.14 defect: candidates re-simulated with episode=0 gave every
    # realization the same fixed corruption and biased the comparison.
    cfg = SimConfig(steps=200, noise=0.2, o2=(40.5, 60.5, 35.0, 65.0))
    init = Init(x=(31.0, 35.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
    true = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    scores = []
    for episode in (7, 9):
        ep = run(cfg, 0, episode=episode, init=init,
                 kicks=(Kick(60, 0, (0.0, 1.5)),))
        out = attribute(ep, [true, None], cfg, 0, init)
        scores.append([d for d, _ in out["scores"]])
    assert scores[0] != scores[1]


def _moving_cfg(vx: float) -> SimConfig:
    return SimConfig(steps=200, o2=(40.5, 60.5, 35.0, 65.0), o2_velocity=(vx, 0.0))


def test_moving_observer_makes_coverage_time_resolved():
    # R-P1.17: the same world and occluder, only the drift differs. A kick at
    # x=44 is inside the blind region when the observer is static and outside it
    # once the observer has drifted right by the event step.
    init = Init(x=(26.0, 22.0), y=(45.0, 45.0), v=((3.0, 0.0), (3.0, 0.0)))
    kick = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    results = []
    for vx in (0.0, 1.667):
        cfg = _moving_cfg(vx)
        ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(60, 0, (0.0, 1.5)),))
        out = attribute(ep, [kick, None], cfg, 0, init)
        results.append(out["unique"])
    assert results == [False, True]


def test_folded_occluder_stays_inside_the_box():
    cfg = _moving_cfg(12.4)
    for t in (0, 30, 60, 120, 199):
        rect = occluder2_at(cfg, t)
        assert 0.0 <= rect[0] and rect[1] <= cfg.W      # folded inside the box
        assert rect[1] - rect[0] == 20.0                # width preserved
    # it reflected: the position at t=60 is not the unfolded one
    assert occluder2_at(cfg, 60)[0] != 40.5 + 12.4 * 0.1 * 60


def test_occluder_sweeping_onto_a_body_is_labelled_sweep():
    # body stationary inside o; the second occluder sweeps onto it, so no edge
    # is crossed and the transition is a sweep, not a left/right/top/bottom
    cfg = SimConfig(steps=100, o2=(20.0, 40.0, 35.0, 65.0), o2_velocity=(0.83, 0.0))
    init = Init(x=(45.0, 90.0), y=(50.0, 90.0), v=((0.0, 0.0), (0.0, 0.0)))
    ep = run(cfg, 0, episode=0, init=init)
    sides = [e.attrs.get("side") for e in ep.observable_log()
             if e.kind in ("enter_occ", "exit_occ")]
    assert "sweep" in sides, sides


def test_scene_symmetries_are_exact_and_area_preserving():
    from psychopomp.perspective import SYMMETRIES, scene_point, scene_rect
    rect = (40.0, 60.5, 35.0, 65.0)
    area = lambda r: (r[1] - r[0]) * (r[3] - r[2])
    for sym in SYMMETRIES:
        mapped = scene_rect(sym, rect)
        assert abs(area(mapped) - area(rect)) < 1e-12
        assert 0.0 <= mapped[0] and mapped[1] <= 100.0
    # involutions return the original
    for sym in ("rot180", "reflect-v", "reflect-h"):
        p = scene_point(sym, scene_point(sym, (37.0, 45.0)))
        assert abs(p[0] - 37.0) < 1e-12 and abs(p[1] - 45.0) < 1e-12
    # rot90 four times is the identity
    p = (37.0, 45.0)
    for _ in range(4):
        p = scene_point("rot90", p)
    assert abs(p[0] - 37.0) < 1e-9 and abs(p[1] - 45.0) < 1e-9


def test_identifiability_is_covariant_under_whole_scene_symmetry():
    from psychopomp.perspective import SYMMETRIES, transform_scene
    cfg = SimConfig(steps=200, o2=(40.5, 60.5, 35.0, 65.0))
    init = Init(x=(26.0, 22.0), y=(45.0, 45.0), v=((3.0, 0.0), (3.0, 0.0)))
    kick = Kick(60, 0, (0.0, 1.5))
    true = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    outcomes = set()
    for sym in SYMMETRIES:
        c, i, k = transform_scene(cfg, init, kick, sym)
        ep = run(c, 0, episode=0, init=i, kicks=(k,))
        outcomes.add(attribute(ep, [true, None], c, 0, i)["unique"])
    assert outcomes == {False}, outcomes       # covered event: tie in every frame


def test_bodies_only_transform_is_not_covariant():
    # A4's implicit comparison: moving the bodies without the observers changes
    # the world, so identifiability must be able to change.
    from psychopomp.perspective import transform_scene
    cfg = SimConfig(steps=200, o2=(40.5, 60.5, 35.0, 65.0), o2_velocity=(1.667, 0.0))
    init = Init(x=(26.0, 22.0), y=(45.0, 45.0), v=((3.0, 0.0), (3.0, 0.0)))
    kick = Kick(60, 0, (0.0, 1.5))
    true = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    ep0 = run(cfg, 0, episode=0, init=init, kicks=(kick,))
    assert attribute(ep0, [true, None], cfg, 0, init)["unique"] is True   # baseline
    _, i2, k2 = transform_scene(cfg, init, kick, "rot180")
    ep = run(cfg, 0, episode=0, init=i2, kicks=(k2,))   # occluders NOT transformed
    assert attribute(ep, [true, None], cfg, 0, i2)["unique"] is False


def test_a_narrow_occluder_can_be_relocated_off_the_events():
    # R-P1.21: o2 narrower than o means the blind window can be *moved* inside
    # it, so a chosen drift strictly beats staying still (agency matters).
    tasks = (42.0, 48.0)
    body_x0 = tuple(x - 27.0 for x in tasks)      # at task x on step 90
    cfg0 = SimConfig(steps=200, o2=(46.0, 54.0, 35.0, 65.0), n_balls=2)
    cfg1 = SimConfig(steps=200, o2=(46.0, 54.0, 35.0, 65.0),
                     o2_velocity=(1.0, 0.0), n_balls=2)
    init = Init(x=body_x0, y=(45.0, 45.0), v=((3.0, 0.0), (3.0, 0.0)))
    outcomes = []
    for cfg in (cfg0, cfg1):
        ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(90, 1, (0.0, 1.5)),))
        true = Intervention(t=90, ball=1, dv=(0.0, 1.5))
        outcomes.append(attribute(ep, [true, None], cfg, 0, init)["unique"])
    assert outcomes == [False, True]     # task 48 covered when static, free once moved
