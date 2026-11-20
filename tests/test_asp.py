from psychopomp.asp import compare_worlds, worlds_via_asp
from psychopomp.eventlog import Event, EventLog, Provenance
from psychopomp.epec import consistent_worlds
from psychopomp.sim import Init, SimConfig, run

PROV = Provenance("test", "0", 0, 0)
CFG = SimConfig(steps=150)
OFF_AXIS = Init(x=(20.0, 52.0), y=(45.0, 20.0), v=((3.0, 1.0), (0.0, 3.3)))
STRAIGHT = Init(x=(20.0, 20.0), y=(50.0, 80.0), v=((3.0, 0.0), (3.0, 0.0)))


def ev(kind, t, side, v):
    return Event(kind, t, ("ball",), {"side": side, "v": list(v)}, True, PROV)


def test_asp_matches_python_straight():
    ep = run(CFG, 0, init=STRAIGHT)
    c = compare_worlds(ep.observable_log())
    assert c["equal"] and len(c["asp"]) == 1


def test_asp_matches_python_off_axis():
    ep = run(CFG, 0, init=OFF_AXIS)
    c = compare_worlds(ep.observable_log())
    assert c["equal"] and len(c["asp"]) == 2


def test_asp_matches_python_head_on_degenerate():
    log = EventLog([
        ev("enter_occ", 10, "left", (2.0, 0.0)),
        ev("enter_occ", 10, "right", (-2.0, 0.0)),
        ev("exit_occ", 30, "left", (-2.0, 0.0)),
        ev("exit_occ", 30, "right", (2.0, 0.0)),
    ])
    c = compare_worlds(log)
    assert c["equal"] and len(c["asp"]) == 2


def test_asp_teleport_zero_worlds():
    log = EventLog([
        ev("enter_occ", 0, "left", (2.0, 0.0)),
        ev("exit_occ", 10, "left", (-2.0, 0.0)),
    ])
    assert worlds_via_asp(log) == []
    assert consistent_worlds(log) == []


def test_asp_exit_without_enter_zero_worlds():
    log = EventLog([ev("exit_occ", 5, "right", (2.0, 0.0))])
    assert worlds_via_asp(log) == []
