from psychopomp.controls import control_report, shuffle_rules
from psychopomp.eventlog import Event, EventLog, Provenance
from psychopomp.sim import Init, SimConfig, run

PROV = Provenance("test", "0", 0, 0)
CFG = SimConfig()


def t2_rules():
    ep = run(CFG, seed=0, init=Init(x=(30.0, 70.0), v=(4.0, -4.0)))
    return ep.observable_log()


def test_preserves_kinds_and_times():
    orig = t2_rules()
    shuf = shuffle_rules(orig, seed=42)
    o = sorted((e.kind, e.t) for e in orig)
    s = sorted((e.kind, e.t) for e in shuf)
    assert o == s


def test_preserves_marginals_breaks_alignment():
    orig = t2_rules()
    shuf = shuffle_rules(orig, seed=42)
    rep = control_report(orig, shuf)
    assert rep["n_events"] == len(orig)
    assert rep["preserved_marginals_and_times"] is True
    assert rep["joint_alignment_changed"] is True


def test_deterministic_with_seed():
    orig = t2_rules()
    assert sorted(
        (e.kind, e.t, tuple(sorted(e.attrs.items()))) for e in shuffle_rules(orig, seed=9)
    ) == sorted(
        (e.kind, e.t, tuple(sorted(e.attrs.items()))) for e in shuffle_rules(orig, seed=9)
    )


def test_singletons_untouched():
    log = EventLog([Event("enter_occ", 5, ("ball",), {"side": "left", "v": 1.0}, True, PROV)])
    shuf = shuffle_rules(log, seed=3)
    assert shuf.events[0].attrs == log.events[0].attrs
