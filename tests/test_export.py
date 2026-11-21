import json

import pytest

from psychopomp.export import SCHEMA, observation_records, read_observations, write_observations
from psychopomp.fixtures import OFF_AXIS, PASS_CFG, STRAIGHT
from psychopomp.interventions import Intervention, paired
from psychopomp.sim import run


def test_export_is_lossless_over_observable_events():
    ep = run(PASS_CFG, 0, init=OFF_AXIS)
    records = observation_records(ep)
    assert len(records) == len(ep.observable_log())
    by_seq = {e.seq: e for e in ep.observable_log()}
    for r in records:
        e = by_seq[r["seq"]]
        assert r["schema"] == SCHEMA
        assert r["kind"] == e.kind
        assert abs(r["at"] - e.t * ep.config.dt) < 1e-9
        assert r["props"] == e.attrs
        assert r["subject"] == f"episode:{ep.seed}:{ep.episode}"


def test_export_refuses_counterfactuals():
    _, alt = paired(PASS_CFG, 0, STRAIGHT, Intervention(t=20, ball=0, dv=(0.0, 2.0)))
    with pytest.raises(ValueError):
        observation_records(alt)


def test_export_never_contains_hidden_contacts_or_labels():
    ep = run(PASS_CFG, 0, init=OFF_AXIS)
    records = observation_records(ep)
    assert all(r["evidence"] == "OBSERVED" for r in records)
    assert not [r for r in records if r["kind"] == "ball_collide" and not r["props"].get("x_a")]
    assert all(r["provenance"]["source"].startswith("sim:") for r in records)


def test_export_is_deterministic_and_roundtrips(tmp_path):
    ep = run(PASS_CFG, 0, init=STRAIGHT)
    p1, p2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    n1 = write_observations(ep, str(p1))
    n2 = write_observations(ep, str(p2))
    assert n1 == n2 == len(ep.observable_log())
    assert p1.read_bytes() == p2.read_bytes()
    assert read_observations(str(p1)) == read_observations(str(p2))
    assert all(json.loads(line)["schema"] == SCHEMA for line in p1.read_text().splitlines())
