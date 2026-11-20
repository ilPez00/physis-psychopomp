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
