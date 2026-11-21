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


def test_multiple_contact_pairs_enumerated():
    # two independent reflection-consistent contact pairs (IMP-7)
    log = log_from(
        ev("enter_occ", 0, "left", (3.0, 1.0)),
        ev("enter_occ", 1, "bottom", (0.0, 3.3)),
        ev("enter_occ", 20, "left", (-3.0, -1.0)),
        ev("enter_occ", 21, "bottom", (0.0, -3.3)),
        ev("exit_occ", 10, "bottom", (0.0, 1.0)),
        ev("exit_occ", 11, "right", (3.0, 3.3)),
        ev("exit_occ", 30, "bottom", (0.0, -1.0)),
        ev("exit_occ", 31, "right", (-3.0, -3.3)),
    )
    worlds = consistent_worlds(log)
    assert [w for w in worlds if len(w.swaps) == 2], [w.describe() for w in worlds]


def test_recrossing_episode_has_single_identity_world():
    from psychopomp.fixtures import recrossing_episode, truth_matches

    ep = recrossing_episode()
    obs = ep.observable_log()
    s = summarize(obs)
    assert s["enters"] == 2 and s["exits"] == 2
    assert s["n_worlds"] == 1
    assert s["contact_required"] is False
    assert consistent_worlds(obs)[0].matches == truth_matches(ep)


def test_single_ball_recrossing_is_filtered_to_the_truth():
    # One ball crosses the occluder twice (wall bounce in between). Four events,
    # one consistent world, no contact: continuity alone decides it.
    from psychopomp.fixtures import recrossing_episode, truth_matches

    ep = recrossing_episode()
    worlds = consistent_worlds(ep.observable_log())
    assert len(worlds) == 1
    assert worlds[0].matches == truth_matches(ep)
    assert worlds[0].swaps == ()


def test_two_ball_symmetric_recrossing_is_ambiguous_not_wrong():
    # Two balls on parallel paths both cross twice: four events, two velocity
    # classes, so four consistent worlds. The ambiguity is identity, not a
    # filter failure -- and the truth for such an episode is unattributable
    # (see tests/test_probes.py), which is why it is excluded, not scored.
    ep = run(
        SimConfig(steps=600),
        5,
        init=Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))),
    )
    log = ep.observable_log()
    worlds = consistent_worlds(log)
    assert summarize(log)["enters"] == 4
    assert len(worlds) == 4
    assert all(w.swaps == () for w in worlds)


def test_zero_worlds_is_undecidable_not_no_contact():
    # A teleport/inconsistent log has no consistent world at all. Reading that as
    # contact_required False turned "nothing explains this" into a negative label.
    from psychopomp.eventlog import Provenance

    prov = Provenance("test", "0", 0, 0)
    log = EventLog([
        ev("enter_occ", 1, "left", (3.0, 0.0)),
        ev("exit_occ", 2, "right", (-9.0, 7.0)),
    ])
    s = summarize(log)
    assert s["n_worlds"] == 0
    assert s["cleared"] is True
    assert s["contact_required"] is None
