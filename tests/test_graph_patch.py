"""E3: proposals stay proposals."""
import json

import pytest

from psychopomp.graph_patch import HYPOTHESIZED, SCHEMA, decode, to_json
from psychopomp.physis_snapshot import Edge, Snapshot

SNAP = Snapshot(
    entities={"file:a": "file", "file:b": "file", "doc:c": "document"},
    edges=[Edge("file:a", "DEFINES", "doc:c")],
    evidence_seqs=[1, 2, 3],
    pin="sha256:base",
)
CALLS = ("file:a", "CALLS", "file:b")
DEPENDS = ("file:a", "DEPENDS", "file:b")


def ops(plan, name=None):
    return [op for op in plan["operations"] if name is None or op["op"] == name]


def test_agreement_across_worlds_is_still_only_a_hypothesis():
    plan = decode(SNAP, [{CALLS}, {CALLS}])
    (proposal,) = ops(plan, "propose_edge")
    assert proposal["status"] == HYPOTHESIZED
    assert proposal["agreement"] == "all_surviving_worlds"
    assert proposal["evidence_seqs"] == [1, 2, 3]
    assert plan["base_revision"] == "sha256:base"
    assert plan["schema"] == SCHEMA
    assert plan["verifier"]["status"] == "NOT_EVALUATED"


def test_disagreement_emits_both_and_asks_for_the_discriminating_experiment():
    plan = decode(SNAP, [{CALLS}, {DEPENDS}],
                  experiments={"passive": 0.0, "perturbed": 1.0})
    proposals = ops(plan, "propose_edge")
    assert {tuple(p[key] for key in ("source", "predicate", "target")) for p in proposals} == {CALLS, DEPENDS}
    assert all(p["agreement"] == "disputed" and p["status"] == HYPOTHESIZED for p in proposals)
    (request,) = ops(plan, "request_evidence")
    assert request["experiments"] == ["perturbed"]
    assert request["predicted_information_bits"] == pytest.approx(1.0)


def test_no_experiment_is_requested_when_none_is_informative():
    plan = decode(SNAP, [{CALLS}, {DEPENDS}], experiments={"passive": 0.0})
    assert ops(plan, "request_evidence") == []


def test_no_surviving_world_is_unknown_not_empty_success():
    plan = decode(SNAP, [])
    (only,) = ops(plan)
    assert only["op"] == "unknown"
    assert "no world survived" in only["reason"]


def test_an_already_observed_edge_is_not_proposed():
    plan = decode(SNAP, [{("file:a", "DEFINES", "doc:c")}])
    assert ops(plan, "propose_edge") == []


def test_a_refused_triple_is_never_re_proposed():
    plan = decode(SNAP, [{CALLS}], refused={CALLS: 10})
    assert ops(plan, "propose_edge") == []
    (blocked,) = plan["blocked"]
    assert blocked["refused_at_seq"] == 10
    assert "UNVERIFIABLE" in blocked["reason"]


def test_a_world_naming_an_unobserved_entity_is_refused():
    with pytest.raises(ValueError, match="unobserved entity"):
        decode(SNAP, [{("file:a", "CALLS", "file:ghost")}])
    with pytest.raises(ValueError):
        decode({"not": "a snapshot"}, [{CALLS}])


def test_serialisation_is_deterministic_and_round_trips():
    first = to_json(decode(SNAP, [{CALLS}, {DEPENDS}], experiments={"x": 1.0}))
    second = to_json(decode(SNAP, [{DEPENDS}, {CALLS}], experiments={"x": 1.0}))
    assert first == second
    assert json.loads(first)["schema"] == SCHEMA
    assert "HYPOTHESIZED" in first and "VERIFIED" not in first
