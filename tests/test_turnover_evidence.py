"""C3: the one-probe loop transfers to the turnover pair."""
from fractions import Fraction

import pytest

from psychopomp.active_design import best_probes, information_gain
from psychopomp.active_receipt import commit, decide, predictions_from, verify_against
from psychopomp.turnover_evidence import ARMS, PROBES, acquire, arm_of, rows

PRIOR = (Fraction(1, 2), Fraction(1, 2))
TARGETS = (1, 2)


def test_the_two_hypotheses_are_indistinguishable_before_the_disturbance():
    passive = rows("passive")
    assert len({reading for _, reading in passive}) == 1
    assert information_gain(passive) == 0.0
    assert best_probes({"passive": passive}) == ()


@pytest.mark.parametrize("target", TARGETS)
def test_one_post_disturbance_observation_separates_them(target):
    perturbed = rows("perturbed", target)
    assert information_gain(perturbed) == pytest.approx(1.0)
    assert best_probes({"passive": rows("passive", target), "perturbed": perturbed}) == ("perturbed",)


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("target", TARGETS)
def test_a_receipt_resolves_the_true_arm_on_either_role(arm, target):
    perturbed = rows("perturbed", target)
    plan = commit(policy="adaptive", selected="perturbed", prior=PRIOR,
                  predictions=predictions_from(perturbed))
    reading = acquire(arm, "perturbed", target)
    decision = decide(plan, reading)
    assert arm_of(decision["resolved"]) == arm, (arm, target, decision)
    assert verify_against(plan, reading, decision, predictions_from(perturbed))["verdict"] == "VERIFIED"


@pytest.mark.parametrize("arm", ARMS)
def test_the_passive_probe_abstains_rather_than_guessing(arm):
    passive = rows("passive")
    plan = commit(policy="passive", selected="passive", prior=PRIOR,
                  predictions=predictions_from(passive))
    decision = decide(plan, acquire(arm, "passive"))
    assert decision["resolved"] is None
    assert decision["posterior"] == PRIOR
    assert verify_against(plan, acquire(arm, "passive"), decision,
                          predictions_from(passive))["verdict"] == "ABSTAIN"


def test_a_forged_turnover_table_is_refused():
    honest = rows("perturbed")
    forged_rows = [(slot, reading + 1) for slot, reading in honest]
    plan = commit(policy="adaptive", selected="perturbed", prior=PRIOR,
                  predictions=predictions_from(forged_rows))
    report = verify_against(plan, acquire("feedback", "perturbed"), decide(plan, acquire("feedback", "perturbed")),
                            predictions_from(honest))
    assert report["verdict"] == "REFUSED", report


def test_out_of_catalogue_probes_are_refused():
    with pytest.raises(ValueError):
        rows("magnitude")
    with pytest.raises(ValueError):
        acquire("open-loop", "perturbed")
