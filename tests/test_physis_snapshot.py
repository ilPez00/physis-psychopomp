"""E2: parse Physis output without trusting it and without writing to it."""
import pytest

from psychopomp.physis_snapshot import Edge, from_cli

OBJECTS = {"count": 2, "kind": None, "objects": [
    {"id": "file:src/a.txt", "kind": "file", "label": "src/a.txt"},
    {"id": "document:src/a.txt::1", "kind": "document", "label": "alpha"},
]}
DETAILS = [
    {"id": "file:src/a.txt", "evidence": [3, 4],
     "relations": [{"direction": "outgoing", "other": "document:src/a.txt::1",
                    "predicate": "DEFINES"}]},
    {"id": "document:src/a.txt::1", "evidence": [3],
     "relations": [{"direction": "incoming", "other": "file:src/a.txt",
                    "predicate": "DEFINES"}]},
]


def test_edges_are_normalised_and_deduplicated_across_both_directions():
    snap = from_cli(OBJECTS, DETAILS)
    assert snap.edges == [Edge("file:src/a.txt", "DEFINES", "document:src/a.txt::1")]
    assert snap.entities["file:src/a.txt"] == "file"
    assert sorted(set(snap.evidence_seqs)) == [3, 4]


def test_revision_is_a_digest_of_what_was_read_and_a_pin_overrides_it():
    snap = from_cli(OBJECTS, DETAILS)
    assert snap.revision.startswith("sha256:") and snap.revision == snap.digest
    assert from_cli(OBJECTS, DETAILS).revision == snap.revision, "not deterministic"
    assert from_cli(OBJECTS, DETAILS, pin="sha256:packet").revision == "sha256:packet"


def test_changed_world_changes_the_revision():
    more = {"objects": OBJECTS["objects"] + [
        {"id": "file:src/b.txt", "kind": "file", "label": "src/b.txt"}]}
    assert from_cli(more, DETAILS).revision != from_cli(OBJECTS, DETAILS).revision


def test_an_edge_naming_an_unobserved_entity_is_refused():
    orphan = [{"id": "file:src/a.txt", "evidence": [1],
               "relations": [{"source": "file:src/a.txt", "predicate": "CONTAINS",
                              "target": "file:src/ghost.txt"}]}]
    with pytest.raises(ValueError, match="unobserved entity"):
        from_cli(OBJECTS, orphan)


def test_malformed_payloads_are_refused_not_coerced():
    with pytest.raises(ValueError):
        from_cli({"nope": []}, DETAILS)
    with pytest.raises(ValueError):
        from_cli({"objects": [{"id": "a:1", "kind": "a"},
                              {"id": "a:1", "kind": "a"}]}, [])
    with pytest.raises(ValueError):
        from_cli({"objects": [{"id": "a:1"}]}, [])
    with pytest.raises(ValueError):
        from_cli(OBJECTS, [{"id": "file:src/a.txt", "evidence": ["3"]}])
