from psychopomp.epec import World, consistent_worlds
from psychopomp.fixtures import OFF_AXIS, PASS_CFG, STRAIGHT
from psychopomp.interventions import (
    COUNTERFACTUAL_SOURCE,
    ObservationLedger,
    Intervention,
    classify,
    paired,
)
from psychopomp.sim import Init, run


def test_pair_identical_before_kick_and_diverging_after():
    base, alt = paired(PASS_CFG, 0, STRAIGHT, Intervention(t=20, ball=0, dv=(0.0, 2.0)))
    for k in range(20):
        assert (base.trajs[0].x[k], base.trajs[0].y[k]) == (alt.trajs[0].x[k], alt.trajs[0].y[k])
    assert alt.trajs[0].y[-1] != base.trajs[0].y[-1]


def test_counterfactual_provenance_and_ledger_refusal():
    base, alt = paired(PASS_CFG, 0, STRAIGHT, Intervention(t=20, ball=0, dv=(0.0, 2.0)))
    assert base.observable_log().events[0].provenance.source == "sim:v0.2"
    assert alt.observable_log().events[0].provenance.source == COUNTERFACTUAL_SOURCE
    ledger = ObservationLedger()
    ledger.record(base)
    assert ledger.events()
    try:
        ledger.record(alt)
    except ValueError:
        pass
    else:
        raise AssertionError("ledger accepted a counterfactual as history")


def test_hidden_kick_is_skipped_and_cannot_change_the_counterfactual():
    init = Init(x=(38.0, 80.0), y=(50.0, 50.0), v=((3.0, 0.0), (3.0, 0.0)))
    base, alt = paired(PASS_CFG, 0, init, Intervention(t=10, ball=0, dv=(0.0, 2.0)))
    assert alt.skipped_kicks, "a hidden kick must be skipped, not applied"
    assert [e.attrs for e in alt.observable_log()] == [e.attrs for e in base.observable_log()]


def test_classify_labels_the_truth_and_refutes_a_wrong_world():
    ep = run(PASS_CFG, 0, init=OFF_AXIS)
    consistent = consistent_worlds(ep.observable_log())
    wrong = World(matches=((0, 1), (1, 0)), swaps=(), unmatched=())
    labels = classify(ep, proposed=[wrong] + consistent)
    assert labels["truth_in_inferred"] is True
    assert labels["INFERRED"] == consistent
    assert wrong in labels["REFUTED"] or (wrong.matches, wrong.swaps) in {
        (w.matches, w.swaps) for w in consistent
    }


def test_ledger_contains_only_observable_executed_events():
    ep = run(PASS_CFG, 0, init=OFF_AXIS)
    ledger = ObservationLedger()
    ledger.record(ep)
    assert all(e.observable for e in ledger.events())
    assert all(e.provenance.source.startswith("sim:") for e in ledger.events())
    assert not any(e.kind == "ball_collide" for e in ledger.events() if e.observable is False)
