"""Exact finite experiment design (R-P1.47)."""
from fractions import Fraction

import pytest

from psychopomp.active_design import best_probes, information_gain, posterior


def test_information_depends_on_the_target_not_readout_entropy():
    degrees = {  # (law, state, passive, signed, magnitude)
        (-1, -3, -3, -1, 7), (-1, -1, -1, -1, 5),
        (-1, 1, 1, -1, 3), (-1, 3, 3, -1, 1),
        (1, -3, -3, 1, 1), (1, -1, -1, 1, 3),
        (1, 1, 1, 1, 5), (1, 3, 3, 1, 7),
    }
    catalogues = [
        {name: [(row[target], row[readout]) for row in degrees]
         for readout, name in enumerate(("passive", "signed", "magnitude"), 2)}
        for target in (0, 1)
    ]
    assert [tuple(map(information_gain, cat.values())) for cat in catalogues] == [
        (0, 1, 0), (2, 0, 1),
    ]
    assert best_probes(catalogues[0]) == ("signed",)
    assert best_probes(catalogues[1]) == ("passive",)


def test_balanced_shuffle_and_missing_arm_have_no_law_gain():
    null = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    assert best_probes({"shuffled": null}) == ()
    assert best_probes({}) == ()
    assert posterior(null, 1) == {-1: Fraction(1, 2), 1: Fraction(1, 2)}


def test_positive_gain_ties_are_order_independent():
    rows = [(-1, 0), (1, 1), (1, 1)]
    first = {"b": rows, "a": rows[::-1]}
    assert best_probes(first) == best_probes(dict(reversed(first.items()))) == ("a", "b")
    assert information_gain(rows) == pytest.approx(0.9182958340544896, abs=1e-12)


def test_supported_opposite_readout_updates_but_unseen_readout_does_not():
    signed = [(-1, -1), (1, 1)]
    assert posterior(signed, 1) == {-1: Fraction(0), 1: Fraction(1)}
    assert posterior(signed, 0) is None
    assert posterior(signed, None) is None
