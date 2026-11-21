import pytest

from psychopomp.fixtures import random_corpus, targeted_corpus, truth_matches
from psychopomp.probes import m2_baseline, m3_accuracy
from psychopomp.sim import Init, SimConfig, run


def test_m2_endpoint_probe_is_chance_on_contact_family():
    tgt = targeted_corpus(3)
    m2 = m2_baseline(tgt)
    assert m2["episodes"] == 3
    assert abs(m2["worlds_mean"] - 2.0) < 1e-9
    # relabeling symmetry: ties, no strict winner -> at or below chance
    assert m2["top1"] <= m2["chance"] + 1e-9
    assert m2["excluded_ambiguous_truth"] == 0


def test_m3_detects_contacts_on_targeted_and_random():
    assert m3_accuracy(targeted_corpus(3)) == 1.0
    assert m3_accuracy(random_corpus(4)) == 1.0


def test_m3_control_breaks_contact_detection():
    tgt = targeted_corpus(3)
    real = m3_accuracy(tgt)
    shuffled = m3_accuracy(tgt, shuffled=True)
    assert real == 1.0
    assert shuffled < real


def test_truth_refuses_shared_timestamps_instead_of_inventing_a_pairing():
    # Two balls on the same trajectory cross at the same t, so an identity-free
    # log cannot attribute the crossing. This used to return ((0,0),(0,0),
    # (1,1),(1,1)) -- not a bijection, so no world could equal it and every
    # score against it was noise.
    ep = run(
        SimConfig(steps=600),
        5,
        init=Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))),
    )
    with pytest.raises(ValueError, match="ambiguous oracle truth"):
        truth_matches(ep)


def test_truth_is_a_bijection_when_trajectories_are_offset():
    ep = run(
        SimConfig(steps=600),
        5,
        init=Init(x=(30.0, 36.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))),
    )
    pairs = truth_matches(ep)
    enters = [a for a, _ in pairs]
    exits = [b for _, b in pairs]
    assert len(set(enters)) == len(enters)
    assert len(set(exits)) == len(exits)


def test_m2_counts_an_unattributable_truth_as_excluded_not_wrong():
    # Same-trajectory episodes are real physics with an unattributable oracle
    # pairing: the harness must shrink the denominator, never score a guess.
    ambiguous = run(
        SimConfig(steps=600),
        5,
        init=Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))),
    )
    m2 = m2_baseline([ambiguous])
    assert m2["excluded_ambiguous_truth"] == 1
    assert m2["episodes"] == 0
    assert m2["top1"] == 0.0


def test_a2_position_continuity_breaks_the_relabeling_tie():
    # Amendment A2, measured on the family built for it: four contact-free
    # worlds, attributable truth. Endpoints cannot decide (0.00 vs chance 0.25);
    # the observable boundary position decides all six (1.00 vs chance 0.25).
    from psychopomp.fixtures import parallel_recrossing_corpus
    from psychopomp.probes import m2_position_continuity

    eps = parallel_recrossing_corpus(6)
    assert len(eps) == 6
    endpoint = m2_baseline(eps)
    a2 = m2_position_continuity(eps)
    assert abs(endpoint["chance"] - 0.25) < 1e-9
    assert endpoint["top1"] == 0.0
    assert a2["excluded"] == 0
    assert abs(a2["chance"] - 0.25) < 1e-9
    assert a2["top1"] == 1.0
