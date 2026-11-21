from psychopomp.fixtures import random_corpus, targeted_corpus
from psychopomp.probes import m2_baseline, m3_accuracy


def test_m2_endpoint_probe_is_chance_on_contact_family():
    tgt = targeted_corpus(3)
    m2 = m2_baseline(tgt)
    assert m2["episodes"] == 3
    assert abs(m2["worlds_mean"] - 2.0) < 1e-9
    # relabeling symmetry: ties, no strict winner -> at or below chance
    assert m2["top1"] <= m2["chance"] + 1e-9


def test_m3_detects_contacts_on_targeted_and_random():
    assert m3_accuracy(targeted_corpus(3)) == 1.0
    assert m3_accuracy(random_corpus(4)) == 1.0


def test_m3_control_breaks_contact_detection():
    tgt = targeted_corpus(3)
    real = m3_accuracy(tgt)
    shuffled = m3_accuracy(tgt, shuffled=True)
    assert real == 1.0
    assert shuffled < real
