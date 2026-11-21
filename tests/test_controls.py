from psychopomp.controls import control_report, shuffle_rules
from psychopomp.sim import Init, SimConfig, run

CFG = SimConfig(steps=150)
OFF_AXIS = Init(x=(20.0, 52.0), y=(45.0, 20.0), v=((3.0, 1.0), (0.0, 3.3)))
STRAIGHT = Init(x=(20.0, 20.0), y=(50.0, 80.0), v=((3.0, 0.0), (3.0, 0.0)))


def corpus():
    eps = [
        run(CFG, 0, init=OFF_AXIS),
        run(CFG, 0, init=STRAIGHT),
        run(CFG, 11),
        run(CFG, 12),
        run(CFG, 13),
    ]
    return [ep.observable_log() for ep in eps]


def test_preserves_structure_and_marginals():
    logs = corpus()
    shuf = shuffle_rules(logs, seed=42)
    rep = control_report(logs, shuf)
    assert rep["n_episodes"] == len(logs)
    assert rep["kinds_and_times_preserved"] is True
    assert rep["exit_marginals_preserved"] is True
    assert rep["alignment_changed"] is True
    assert rep["episodes_with_changed_pairing"] > 0


def test_derangement_has_no_fixed_points_for_n_ge_2():
    logs = corpus()
    shuf = shuffle_rules(logs, seed=7)
    # every exit payload must have moved to a different (episode, slot)
    orig = [(k, e.t, str(e.attrs)) for k, log in enumerate(logs) for e in log if e.kind == "exit_occ"]
    new = [(k, e.t, str(e.attrs)) for k, log in enumerate(shuf) for e in log if e.kind == "exit_occ"]
    assert len(orig) == len(new) >= 2
    assert orig != new


def test_deterministic_with_seed():
    logs = corpus()
    a = shuffle_rules(logs, seed=9)
    b = shuffle_rules(logs, seed=9)
    assert [str([e.attrs for e in l]) for l in a] == [str([e.attrs for e in l]) for l in b]


def test_single_exit_corpus_is_identity():
    logs = [run(CFG, 0, init=STRAIGHT).observable_log()]
    shuf = shuffle_rules(logs, seed=3)
    assert [e.attrs for e in shuf[0]] == [e.attrs for e in logs[0]]


def test_null_arm_does_not_reproduce_the_filter_verdict():
    # IMP-6: the shuffled control must be a TEST, not a printout. Fixed seed and
    # corpus, so a regression (shuffle becoming identity) fails loudly instead of
    # showing up as a nicer-looking number in scripts/probes.py.
    from psychopomp.epec import summarize
    from psychopomp.fixtures import targeted_corpus

    eps = targeted_corpus(6)
    real = [summarize(ep.observable_log()) for ep in eps]
    null = [
        summarize(l)
        for l in shuffle_rules([ep.observable_log() for ep in eps], seed=12345)
    ]
    assert sum(1 for r in real if r["contact_required"]) == 6
    assert sum(1 for n in null if n["contact_required"]) == 0
    real_mean = sum(r["n_worlds"] for r in real) / len(real)
    null_mean = sum(n["n_worlds"] for n in null) / len(null)
    assert abs(real_mean - 2.0) < 1e-9
    assert null_mean == 0.0
