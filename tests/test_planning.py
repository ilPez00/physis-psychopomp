"""The planner must reproduce the numbers its cards measured.

Each test here pins `psychopomp.planning` to a published result: if the law or the
planner drifts, these fail even if the research scripts still pass.
"""
from psychopomp.law import blind_cells
from psychopomp.planning import plan_coverage, plan_hedged, predicted_scores
from psychopomp.sim import SimConfig

# R-P1.21 / R-P1.24 / R-P1.28 harness
O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TASKS = ((42.0, 45.0), (46.0, 45.0), (48.0, 45.0), (52.0, 45.0))
DRIFTS = (-1.0, -0.5, 0.0, 0.5, 1.0)
T_STAR = 90


def config() -> SimConfig:
    return SimConfig(o=O, o2=O2, steps=200)


def test_planner_picks_the_drift_the_cards_measured():
    # R-P1.24/R-P1.30: drift +1.0 scores 4/4 measured; it is the law's optimum too
    out = plan_coverage(config(), TASKS, DRIFTS, T_STAR)
    assert out["drift"] == 1.0
    assert out["score"] == 4


def test_predicted_scores_match_the_law_including_the_boundary_task():
    # The law predicts 0.0 -> 1 because task x=46 sits exactly on the blind edge.
    # R-P1.24 *measured* 2 there, because the body accumulates to 45.999999...
    # and lands outside — the documented boundary rule, not a discrepancy.
    scores = predicted_scores(config(), TASKS, DRIFTS, T_STAR)
    assert scores == {-1.0: 3, -0.5: 1, 0.0: 1, 0.5: 3, 1.0: 4}
    from psychopomp.law import on_boundary
    assert on_boundary(config(), (46.0, 45.0), T_STAR)


def test_hedge_reproduces_the_minimax_choice_and_its_cost():
    # R-P1.24: minimax over +/-20 unit beliefs picks -1.0 and scores 3/4
    truth = blind_cells(config())[0]
    beliefs = [(truth[0] + d, truth[1] + d, truth[2], truth[3])
               for d in (-20.0, -10.0, 0.0, 10.0, 20.0)]
    out = plan_hedged(config(), TASKS, DRIFTS, T_STAR, beliefs)
    assert out["drift"] == -1.0
    # worst_case is a *belief-space* score; the measured cost of that drift under
    # the truth is separate (R-P1.24: 3 of 4)
    assert out["worst_case"] == 2
    assert predicted_scores(config(), TASKS, DRIFTS, T_STAR)[-1.0] == 3


def test_a_wrong_self_model_changes_the_plan():
    # R-P1.21: a -10 unit belief error picks -0.5, which measures 1/4
    belief = SimConfig(o=O, o2=(O2[0] - 10.0, O2[1] - 10.0, O2[2], O2[3]), steps=200)
    out = plan_coverage(config(), TASKS, DRIFTS, T_STAR, belief=belief)
    assert out["drift"] == -0.5
    # the belief scores it 4/4; under the truth it is 1/4 — the whole point of
    # R-P1.21, and why a planner's own score is not evidence
    assert out["score"] == 4
    assert predicted_scores(config(), TASKS, DRIFTS, T_STAR)[-0.5] == 1


def test_multi_cell_world_keeps_the_gap_visible():
    # R-P1.31/R-P1.32: two blind cells; the planner must not treat the gap as blind
    cfg = SimConfig(o=O, o2=(44.0, 84.0, 20.0, 90.0),
                    extra_o=((70.0, 78.0, 35.0, 65.0),), steps=200)
    tasks = ((42.0, 45.0), (65.0, 45.0), (74.0, 45.0))
    out = plan_coverage(cfg, tasks, DRIFTS, T_STAR)
    assert out["scores"][0.0] >= 2        # 42 and the gap are visible when static


def test_end_to_end_logs_to_plan():
    # R-P1.29..R-P1.32 in one call: the observer's own logs, its own estimate, its
    # own plan — and R-P1.30 measured that this plan scores 4/4 on the task set
    from psychopomp.planning import plan_from_evidence
    from psychopomp.sim import Init, run

    corpus = []
    for i, lane in enumerate((44.0, 48.0, 52.0, 56.0, 40.0, 60.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        corpus.append(run(SimConfig(o=O, o2=O2, steps=400), 0, episode=i,
                          init=Init(x=(start, 3.0), y=(lane, 97.0),
                                    v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((47.0, 50.0, 53.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        corpus.append(run(SimConfig(o=O, o2=O2, steps=400), 0, episode=100 + i,
                          init=Init(x=(column, 3.0), y=(start, 97.0),
                                    v=((0.0, v), (0.0, 0.0)))))

    out = plan_from_evidence(config(), corpus, TASKS, DRIFTS, T_STAR)
    assert out["known"] is True
    assert out["drift"] == 1.0
    assert out["score"] == 4


def test_end_to_end_abstains_on_unseen_edges():
    # a corpus that never crosses the y edges gives a partial estimate; the plan
    # must still be returned, flagged as optimistic by construction
    from psychopomp.planning import plan_from_evidence
    from psychopomp.sim import Init, run

    corpus = []
    for i, lane in enumerate((44.0, 48.0, 52.0, 56.0)):
        corpus.append(run(SimConfig(o=O, o2=O2, steps=400), 0, episode=200 + i,
                          init=Init(x=(10.0, 3.0), y=(lane, 97.0),
                                    v=((3.0, 0.0), (0.0, 0.0)))))
    out = plan_from_evidence(config(), corpus, TASKS, DRIFTS, T_STAR)
    assert out["drift"] is None or out["known"] is False
