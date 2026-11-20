from psychopomp.eventlog import Event, EventLog, Provenance
from psychopomp.epec import World, consistent_worlds, summarize, validate

PROV = Provenance("test", "0", 0, 0)


def ev(kind, t, side=None, v=None):
    attrs = {}
    if side is not None:
        attrs["side"] = side
    if v is not None:
        attrs["v"] = v
    return Event(kind, t, ("ball",), attrs, True, PROV)


def log_from(*events):
    return EventLog(list(events))


def test_straight_pass_single_world():
    # ball enters left at +4, exits right at +4: one consistent world
    log = log_from(ev("enter_occ", 10, "left", 4.0), ev("exit_occ", 31, "right", 4.0))
    ws = consistent_worlds(log)
    assert len(ws) == 1
    assert ws[0].matches == ((0, 0),)
    assert ws[0].swaps == ()
    assert validate(ws[0], *halves(log)) == []


def test_hidden_collision_two_worlds():
    # sim T2 observable stream: two entries, two exits, velocities exchanged
    log = log_from(
        ev("enter_occ", 10, "left", 4.0),
        ev("enter_occ", 10, "right", -4.0),
        ev("exit_occ", 30, "left", -4.0),
        ev("exit_occ", 31, "right", 4.0),
    )
    ws = consistent_worlds(log)
    assert len(ws) == 2
    no_swap = [w for w in ws if not w.swaps]
    swap = [w for w in ws if w.swaps]
    assert len(no_swap) == 1 and len(swap) == 1
    # swap world pairs the two velocity-flipped matches
    assert swap[0].swaps == ((0, 1),)


def test_teleport_zero_worlds():
    # entry +4, exit -4, no partner to swap with: nothing consistent
    log = log_from(ev("enter_occ", 0, "left", 4.0), ev("exit_occ", 10, "left", -4.0))
    assert consistent_worlds(log) == []
    s = summarize(log)
    assert s["n_worlds"] == 0 and s["enters"] == 1 and s["exits"] == 1


def test_exit_without_enter_zero_worlds():
    log = log_from(ev("exit_occ", 5, "right", 4.0))
    assert consistent_worlds(log) == []


def test_still_inside_enter_may_go_unmatched():
    log = log_from(ev("enter_occ", 10, "left", 4.0), ev("exit_occ", 20, "right", 4.0))
    ws = consistent_worlds(log)
    assert len(ws) == 1 and ws[0].unmatched == ()


def test_validate_names_violations():
    enters = [ev("enter_occ", 0, "left", 4.0)]
    exits = [ev("exit_occ", 10, "left", -4.0)]
    w = World(matches=((0, 0),), swaps=(), unmatched=())
    assert validate(w, enters, exits) == ["C4"]


def test_c3_overlap_bound():
    # three concurrent flights: impossible for a 2-ball world
    log = log_from(
        ev("enter_occ", 0, "left", 4.0),
        ev("enter_occ", 0, "right", -4.0),
        ev("enter_occ", 1, "left", 4.0),
        ev("exit_occ", 10, "left", 4.0),
        ev("exit_occ", 10, "right", -4.0),
        ev("exit_occ", 10, "left", 4.0),
    )
    assert consistent_worlds(log) == []


def halves(log):
    enters = [e for e in log if e.kind == "enter_occ"]
    exits = [e for e in log if e.kind == "exit_occ"]
    return enters, exits
