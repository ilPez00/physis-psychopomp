"""Degenerate classes stay exercised: each refusal is named, none is silent."""
import pytest

from psychopomp.epec import summarize
from psychopomp.eventlog import Event, EventLog, Provenance
from psychopomp.fixtures import truth_matches
from psychopomp.probes import m2_baseline
from psychopomp.sim import Init, SimConfig, run

PROV = Provenance("test", "0", 0, 0)


def test_truncated_episode_reports_contact_as_undecided_not_false():
    log = EventLog(
        [Event("enter_occ", 5, ("ball",), {"side": "left", "v": [3.0, 0.0], "pos": [39.7, 50.0]}, True, PROV)]
    )
    s = summarize(log)
    assert s["cleared"] is False
    assert s["contact_required"] is None  # unknown, not "no contact"
    assert s["n_worlds"] == 1
    assert "still inside" in s["worlds"][0]


def test_shared_timestamps_are_excluded_rather_than_scored():
    ep = run(
        SimConfig(steps=600),
        5,
        init=Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))),
    )
    with pytest.raises(ValueError, match="ambiguous oracle truth"):
        truth_matches(ep)
    assert m2_baseline([ep])["excluded_ambiguous_truth"] == 1


def test_tunneling_config_is_refused_with_its_reason():
    with pytest.raises(AssertionError, match="speed\\*dt"):
        SimConfig(steps=10, speed=200.0, dt=0.1)


def test_cleared_episodes_report_a_decided_contact_field():
    ep = run(SimConfig(steps=150), 0, init=Init(x=(20.0, 20.0), y=(50.0, 80.0), v=((3.0, 0.0), (3.0, 0.0))))
    s = summarize(ep.observable_log())
    assert s["cleared"] is True
    assert s["contact_required"] is False
