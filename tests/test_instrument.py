"""Instrument self-check.

These assertions are about the measuring apparatus, not the science: a corpus
whose oracle truth is unattributable, or a truth that the filter cannot even
enumerate, makes every downstream score meaningless. The oracle-truth defect
found on 2026-11-21 (time-only lookup returning a non-bijective pairing) lived
for two corpus generations because nothing checked this.
"""
from psychopomp.epec import consistent_worlds, summarize
from psychopomp.fixtures import (
    random_corpus,
    targeted_corpus,
    truth_matches,
)
from psychopomp.probes import m2_baseline


def test_shipped_corpora_have_attributable_truth():
    for name, eps in (("random", random_corpus(8)), ("targeted", targeted_corpus(6))):
        for ep in eps:
            pairs = truth_matches(ep)  # raises if unattributable
            # Indices are per-log, so the bijection is asserted per episode.
            enters = [a for a, _ in pairs]
            exits = [b for _, b in pairs]
            assert len(set(enters)) == len(enters), name
            assert len(set(exits)) == len(exits), name
            assert len(pairs) == summarize(ep.observable_log())["exits"], name
        assert m2_baseline(eps)["excluded_ambiguous_truth"] == 0, name


def test_the_enumerated_worlds_contain_the_truth():
    # If the filter cannot enumerate the world that actually happened, the
    # ranking task is measuring the filter's blind spot, not the observation.
    for name, eps in (("random", random_corpus(8)), ("targeted", targeted_corpus(6))):
        for ep in eps:
            log = ep.observable_log()
            worlds = consistent_worlds(log)
            assert worlds, f"{name}: zero worlds for a physically valid episode"
            truth = truth_matches(ep)
            assert any(w.matches == truth for w in worlds), f"{name}: truth {truth} absent"


def test_a_log_the_oracle_cannot_attribute_is_excluded_not_scored():
    from psychopomp.sim import Init, SimConfig, run

    ep = run(
        SimConfig(steps=600),
        5,
        init=Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))),
    )
    # The filter still enumerates worlds (the physics is fine) ...
    assert summarize(ep.observable_log())["n_worlds"] == 4
    # ... but the harness must refuse to score against an invented pairing.
    assert m2_baseline([ep])["excluded_ambiguous_truth"] == 1
