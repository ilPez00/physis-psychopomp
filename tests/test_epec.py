from psychopomp.eventlog import Event, EventLog, Provenance
from psychopomp.epec import World, consistent_worlds, summarize, validate
from psychopomp.sim import Init, SimConfig, run

PROV = Provenance("test", "0", 0, 0)
CFG_LONG = SimConfig(steps=150)
OFF_AXIS = Init(x=(20.0, 52.0), y=(45.0, 20.0), v=((3.0, 1.0), (0.0, 3.3)))


def ev(kind, t, side, v):
    return Event(kind, t, ("ball",), {"side": side, "v": list(v)}, True, PROV)


def log_from(*events):
    return EventLog(list(events))


def halves(log):
    return (
        [e for e in log if e.kind == "enter_occ"],
        [e for e in log if e.kind == "exit_occ"],
    )


def test_straight_pass_single_world():
    log = log_from(
        ev("enter_occ", 67, "left", (3.0, 0.0)),
        ev("exit_occ", 125, "right", (3.0, 0.0)),
    )
    ws = consistent_worlds(log)
    assert len(ws) == 1 and ws[0].matches == ((0, 0),) and ws[0].swaps == ()
    assert validate(ws[0], *halves(log)) == []
    assert summarize(log)["contact_required"] is False


def test_off_axis_contact_identified_pairing_ambiguous():
    ep = run(CFG_LONG, seed=0, init=OFF_AXIS)
    obs = ep.observable_log()
    s = summarize(obs)
    assert s["enters"] == 2 and s["exits"] == 2
    assert s["n_worlds"] == 2
    assert s["contact_required"] is True, "a hidden contact is forced in every world"
    assert s["unconstrained"] == 0
    # truth (which ball exited where) is one of the consistent worlds
    truth = oracle_signature(ep)
    enters = [e for e in obs if e.kind == "enter_occ"]
    exits = [e for e in obs if e.kind == "exit_occ"]
    sigs = [
        tuple(sorted((enters[a].attrs["side"], exits[b].attrs["side"]) for a, b in w.matches))
        for w in consistent_worlds(obs)
    ]
    assert truth in sigs


def oracle_signature(ep) -> tuple:
    """Per-ball (enter side, exit side) pairs, from the *oracle* labels."""
    pairs = {}
    for e in ep.oracle_log():
        if e.kind in ("enter_occ", "exit_occ"):
            ball = e.subjects[0]
            pairs.setdefault(ball, []).append((e.t, e.kind, e.attrs["side"]))
    sides = []
    for ball, evs in pairs.items():
        ent = [s for (t, k, s) in evs if k == "enter_occ"]
        ex = [s for (t, k, s) in evs if k == "exit_occ"]
        sides += list(zip(ent, ex))
    return tuple(sorted(sides))


def test_head_on_1d_degenerate_is_unidentifiable():
    # documented degeneracy: equal-mass head-on exchange is observationally
    # identical to pass-through, so a contact-free world survives
    log = log_from(
        ev("enter_occ", 10, "left", (2.0, 0.0)),
        ev("enter_occ", 10, "right", (-2.0, 0.0)),
        ev("exit_occ", 30, "left", (-2.0, 0.0)),
        ev("exit_occ", 30, "right", (2.0, 0.0)),
    )
    s = summarize(log)
    assert s["n_worlds"] == 2
    assert s["contact_required"] is False


def test_teleport_zero_worlds():
    log = log_from(ev("enter_occ", 0, "left", (2.0, 0.0)), ev("exit_occ", 10, "left", (-2.0, 0.0)))
    assert consistent_worlds(log) == []
    assert summarize(log)["n_worlds"] == 0


def test_exit_without_enter_zero_worlds():
    log = log_from(ev("exit_occ", 5, "right", (2.0, 0.0)))
    assert consistent_worlds(log) == []


def test_validate_c1_rejects_unmatched_exit_and_duplicates():
    enters = [ev("enter_occ", 0, "left", (2.0, 0.0)), ev("enter_occ", 0, "right", (-2.0, 0.0))]
    exits = [ev("exit_occ", 10, "left", (2.0, 0.0)), ev("exit_occ", 10, "right", (-2.0, 0.0))]
    # unmatched exit (only one of two exits used)
    w = World(matches=((0, 0),), swaps=(), unmatched=(1,))
    assert "C1" in validate(w, enters, exits)
    # duplicate enter/exit assignment
    w2 = World(matches=((0, 0), (0, 0)), swaps=(), unmatched=())
    assert "C1" in validate(w2, enters, exits)


def test_validate_names_c4_and_c5():
    enters = [ev("enter_occ", 0, "left", (2.0, 0.0))]
    exits = [ev("exit_occ", 10, "left", (-2.0, 0.0))]
    w = World(matches=((0, 0),), swaps=(), unmatched=())
    assert validate(w, enters, exits) == ["C4"]

    # contact world with consistent momentum sum and relative speed
    # (reflection about n=(1,0): rel (3,-2.3) -> (-3,-2.3))
    enters2 = [ev("enter_occ", 0, "left", (3.0, 1.0)), ev("enter_occ", 1, "bottom", (0.0, 3.3))]
    exits2 = [ev("exit_occ", 10, "bottom", (0.0, 1.0)), ev("exit_occ", 11, "right", (3.0, 3.3))]
    w2 = World(matches=((0, 0), (1, 1)), swaps=((0, 1),), unmatched=())
    assert validate(w2, enters2, exits2) == []
    w3 = World(matches=((0, 0), (1, 1)), swaps=((0, 1),), unmatched=())
    exits3 = [ev("exit_occ", 10, "bottom", (0.0, 1.0)), ev("exit_occ", 11, "right", (9.4, 9.5))]
    assert "C5" in validate(w3, enters2, exits3)
