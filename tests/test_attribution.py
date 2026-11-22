import pytest

from psychopomp.attribution import attribute, candidate_episode, motion_distance, signature
from psychopomp.export import observation_records
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

CFG = SimConfig(steps=200)
INIT = Init(x=(30.0, 30.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
TRUE = Intervention(t=30, ball=0, dv=(0.0, 1.5))


def observed_ep():
    return run(CFG, 0, init=INIT, kicks=(Kick(TRUE.t, TRUE.ball, TRUE.dv),))


def test_truth_is_exact_and_unique():
    # asymmetric lanes: the kicked body is observable
    init = Init(x=(30.0, 30.0), y=(45.0, 51.0), v=((3.0, 0.0), (2.0, 0.0)))
    ep = run(CFG, 0, init=init, kicks=(Kick(TRUE.t, TRUE.ball, TRUE.dv),))
    hyp = [None, TRUE, Intervention(t=30, ball=0, dv=(0.0, -1.5)),
           Intervention(t=30, ball=1, dv=(0.0, 1.5))]
    out = attribute(ep, hyp, CFG, 0, init)
    assert out["best_distance"] == 0.0
    assert out["best"] == TRUE
    assert out["unique"] is True


def test_decoys_and_null_are_strictly_farther():
    ep = observed_ep()
    for decoy in (None, Intervention(t=30, ball=0, dv=(0.0, -1.5)),
                  Intervention(t=10, ball=0, dv=(0.0, 1.5)),
                  Intervention(t=30, ball=0, dv=(0.0, 3.0))):
        cand = candidate_episode(CFG, 0, INIT, decoy)
        assert motion_distance(signature(ep), signature(cand)) > 0.0


def test_kicked_lane_is_identifiable_from_path_geometry():
    # identity-free is not permutation-symmetric: the two lanes occupy
    # different positions, so which one took the kick is observable even with
    # identical bodies (a position-free signature would fake a tie here).
    ep = observed_ep()
    wrong_ball = Intervention(t=30, ball=1, dv=(0.0, 1.5))
    out = attribute(ep, [TRUE, wrong_ball], CFG, 0, INIT)
    assert out["unique"] is True and out["best"] == TRUE


def test_hidden_kick_is_the_real_ambiguity():
    # the only unresolvable case: a kicked ball that is not visible when the
    # kick happens (simulator skips it) is indistinguishable from no kick
    ep = run(CFG, 0, init=INIT)
    hidden = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    out = attribute(ep, [None, hidden], CFG, 0, INIT)
    assert out["unique"] is False and TRUE not in out["ambiguity"]


def test_asymmetric_lanes_make_the_kicked_ball_identifiable():
    init = Init(x=(30.0, 30.0), y=(45.0, 51.0), v=((3.0, 0.0), (2.0, 0.0)))
    ep = run(CFG, 0, init=init, kicks=(Kick(TRUE.t, TRUE.ball, TRUE.dv),))
    wrong_ball = Intervention(t=30, ball=1, dv=(0.0, 1.5))
    out = attribute(ep, [TRUE, wrong_ball, None], CFG, 0, init)
    assert out["unique"] is True and out["best"] == TRUE


def test_hidden_kick_ties_with_null_and_is_reported():
    # ball 0 is hidden at step 60 (x = 48); the simulator skips the kick, so
    # the counterfactual equals the no-kick world: ambiguity, not a guess.
    ep = run(CFG, 0, init=INIT)
    hidden = Intervention(t=60, ball=0, dv=(0.0, 1.5))
    out = attribute(ep, [None, hidden], CFG, 0, INIT)
    assert out["unique"] is False
    assert set(map(str, out["ambiguity"])) == {str(None), str(hidden)}


def test_scores_are_deterministic():
    ep = observed_ep()
    a = attribute(ep, [TRUE, None], CFG, 0, INIT)
    b = attribute(ep, [TRUE, None], CFG, 0, INIT)
    assert [d for d, _ in a["scores"]] == [d for d, _ in b["scores"]]


def test_candidates_refuse_export():
    cand = candidate_episode(CFG, 0, INIT, TRUE)
    with pytest.raises(ValueError):
        observation_records(cand)
