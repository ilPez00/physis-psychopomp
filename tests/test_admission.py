"""E4: a proposal is checked, never promoted."""
import pytest

from psychopomp import admission
from psychopomp.graph_patch import decode
from psychopomp.physis_snapshot import Edge, Snapshot

SNAP = Snapshot(entities={"file:a": "file", "file:b": "file"}, edges=[],
                evidence_seqs=[1], pin="sha256:base")
CALLS = ("file:a", "CALLS", "file:b")
DEPENDS = ("file:a", "DEPENDS", "file:b")
PLAN = decode(SNAP, [{CALLS}, {CALLS}])


def scripted(monkeypatch, table):
    def fake(world, source, predicate, target):
        return table[(source, predicate, target)]
    monkeypatch.setattr(admission, "_run", fake)


def test_verified_means_already_known_and_the_proposal_is_retired(monkeypatch):
    scripted(monkeypatch, {CALLS: (0, "VERIFIED: 1 edge(s)")})
    gated = admission.gate(PLAN, "/tmp/world")
    assert [op["op"] for op in gated["operations"]] == []
    assert gated["admission"]["already_known"][0]["verdict"] == "VERIFIED"
    assert gated["admission"]["applied"] is False


def test_no_evidence_keeps_the_proposal_and_says_so(monkeypatch):
    scripted(monkeypatch, {CALLS: (2, "NO_EVIDENCE: absence is not refutation")})
    (op,) = admission.gate(PLAN, "/tmp/world")["operations"]
    assert op["status"] == "HYPOTHESIZED"
    assert op["unverified_by_fold"] is True
    assert "contradicted_by_fold" not in op


def test_refuted_is_kept_and_flagged_not_silently_dropped(monkeypatch):
    scripted(monkeypatch, {CALLS: (1, "REFUTED: contradicts a cited edge")})
    (op,) = admission.gate(PLAN, "/tmp/world")["operations"]
    assert op["contradicted_by_fold"] is True
    assert op["status"] == "HYPOTHESIZED"


def test_an_undocumented_exit_code_fails_closed(monkeypatch):
    scripted(monkeypatch, {CALLS: (7, "something new")})
    with pytest.raises(ValueError, match="undocumented exit code 7"):
        admission.gate(PLAN, "/tmp/world")


def test_gate_does_not_mutate_the_input_plan(monkeypatch):
    scripted(monkeypatch, {CALLS: (2, "NO_EVIDENCE")})
    before = repr(PLAN)
    admission.gate(PLAN, "/tmp/world")
    assert repr(PLAN) == before


def test_the_plan_stays_unapplied_and_keeps_its_base_revision(monkeypatch):
    scripted(monkeypatch, {CALLS: (2, "NO_EVIDENCE"), DEPENDS: (2, "NO_EVIDENCE")})
    gated = admission.gate(decode(SNAP, [{CALLS}, {DEPENDS}]), "/tmp/world")
    assert gated["verifier"]["status"] == "NOT_EVALUATED"
    assert gated["base_revision"] == "sha256:base"
    # decode sorts proposals, so the checks arrive in that order, not the
    # order the worlds were supplied.
    assert [c["edge"] for c in gated["admission"]["checks"]] == [list(CALLS), list(DEPENDS)]
