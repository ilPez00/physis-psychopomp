import pytest

from psychopomp.eventlog import Event, EventLog, Provenance
from psychopomp.sim import Init, Kick, SimConfig, run

CFG = SimConfig()
PROV = Provenance("test", "0", 0, 0)


def test_roundtrip_jsonl(tmp_path):
    log = EventLog()
    log.add(Event("enter_occ", 3, ("ball",), {"side": "left", "v": 4.0}, True, PROV))
    p = tmp_path / "log.jsonl"
    log.to_jsonl(p)
    back = EventLog.from_jsonl(p)
    assert len(back) == 1
    e = back.events[0]
    assert e.kind == "enter_occ" and e.t == 3
    assert e.subjects == ("ball",) and e.attrs == {"side": "left", "v": 4.0}
    assert e.observable and e.provenance.source == "test"


def test_observable_oracle_partition():
    log = EventLog()
    log.add(Event("enter_occ", 1, ("ball",), {}, True, PROV))
    log.add(Event("kick_skipped", 2, ("b0",), {}, False, PROV))
    assert len(log.observable()) == 1 and len(log.oracle()) == 1
    assert log.observable().events[0].kind == "enter_occ"
    assert log.oracle().events[0].kind == "kick_skipped"


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        Event("teleport", 0, (), {}, True, PROV)


def test_seq_assigned_sequentially():
    log = EventLog()
    for t in range(3):
        log.add(Event("kick", t, ("ball",), {}, True, PROV))
    assert [e.seq for e in log] == [0, 1, 2]


def test_iteration_is_canonical_not_insertion_order():
    # R-P1.39: insertion order follows the body loop and encodes body index, so a
    # relabelling changed the sequence even though events are identity-free. The
    # log is a set: two logs with the same events must iterate identically.
    from psychopomp.eventlog import Event, EventLog, Provenance

    def ev(t, kind):
        return Event(kind, t, ("ball",), {"pos": [1.0, 2.0]}, True,
                     Provenance("sim:v0.2", "h", 0, 0))

    events = [ev(2, "exit_occ"), ev(1, "enter_occ"), ev(1, "wall_bounce")]
    a, b = EventLog(), EventLog()
    for e in events:
        a.add(e)
    for e in reversed(events):
        b.add(e)
    assert [(e.kind, e.t, e.seq) for e in a] == [(e.kind, e.t, e.seq) for e in b]
    assert [e.t for e in a] == sorted(e.t for e in a)


def test_observable_log_iteration_survives_a_relabelling():
    from psychopomp.sim import Init, SimConfig, run

    a = ((20.0, 45.0), (3.0, 0.0))
    b = ((80.0, 51.0), (-3.0, 0.0))
    cfg = SimConfig(steps=200, o=(40.0, 60.0, 35.0, 65.0), o2=(46.0, 54.0, 35.0, 65.0))
    plain = run(cfg, 0, episode=0,
                init=Init(x=(a[0][0], b[0][0]), y=(a[0][1], b[0][1]), v=(a[1], b[1])))
    swapped = run(cfg, 0, episode=0,
                  init=Init(x=(b[0][0], a[0][0]), y=(b[0][1], a[0][1]), v=(b[1], a[1])))
    strip = lambda log: [(e.kind, e.t, e.attrs) for e in log.observable_log()]
    assert strip(plain) == strip(swapped)
