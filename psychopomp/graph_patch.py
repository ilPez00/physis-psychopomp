"""E3: turn surviving worlds into typed graph proposals. Nothing is applied.

A decoder here does one thing: compare what each surviving world says the graph
should contain with a pinned snapshot, and describe the difference as proposals.
It never chooses a winner, never writes, and never emits anything stronger than
`HYPOTHESIZED` — promotion is Physis's decision, not this module's.

Two constraints come from the E0 probes, not from taste:

* a triple refused at a known seq is **not** re-proposed (repeating it returns
  `UNVERIFIABLE`, and a retry-until-admitted loop spins);
* disagreement is reported as disagreement plus the experiment that would settle
  it, rather than as the average of the two worlds.
"""
from __future__ import annotations

import json

from .physis_snapshot import Snapshot

SCHEMA = "psychopomp.graph-patch/1"
HYPOTHESIZED = "HYPOTHESIZED"
EdgeKey = tuple[str, str, str]


def decode(snapshot: Snapshot, worlds: list[set[EdgeKey]], *,
           experiments: dict[str, float] | None = None,
           refused: dict[EdgeKey, int] | None = None) -> dict:
    """Proposals for `worlds` against `snapshot`; `experiments` gives probe gains."""
    if not isinstance(snapshot, Snapshot):
        raise ValueError("snapshot must be a parsed Snapshot")
    if not isinstance(worlds, list) or any(not isinstance(w, set) for w in worlds):
        raise ValueError("worlds must be a list of edge sets")
    refused = refused or {}
    operations: list[dict] = []
    blocked: list[dict] = []

    if not worlds:
        operations.append({
            "op": "unknown",
            "reason": "no world survived the evidence; nothing is proposed",
        })
        return _plan(snapshot, operations, blocked)

    claimed = sorted(set().union(*worlds))
    agreed = {key for key in claimed if all(key in world for world in worlds)}
    for key in claimed:
        if key in {(e.source, e.predicate, e.target) for e in snapshot.edges}:
            continue                       # already observed; not a proposal
        if key in refused:
            blocked.append({"edge": list(key), "refused_at_seq": refused[key],
                            "reason": "already refused; a repeat reads UNVERIFIABLE"})
            continue
        source, predicate, target = key
        for endpoint in (source, target):
            if not snapshot.has_entity(endpoint):
                raise ValueError(f"world names unobserved entity {endpoint!r}")
        operations.append({
            "op": "propose_edge", "source": source, "predicate": predicate,
            "target": target, "status": HYPOTHESIZED,
            "agreement": "all_surviving_worlds" if key in agreed else "disputed",
            "evidence_seqs": sorted(set(snapshot.evidence_seqs)),
        })

    disputed = any(op.get("agreement") == "disputed" for op in operations)
    if disputed and experiments:
        ranked = sorted(experiments.items(), key=lambda item: (-item[1], item[0]))
        name, gain = ranked[0]
        if gain > 1e-12:
            operations.append({
                "op": "request_evidence", "experiments": [name],
                "discriminates": sorted(
                    [op["source"], op["predicate"], op["target"]]
                    for op in operations if op.get("agreement") == "disputed"),
                "predicted_information_bits": gain,
            })
    return _plan(snapshot, operations, blocked)


def _plan(snapshot: Snapshot, operations: list[dict], blocked: list[dict]) -> dict:
    return {
        "schema": SCHEMA,
        "base_revision": snapshot.revision,
        "operations": operations,
        "blocked": blocked,
        "verifier": {"status": "NOT_EVALUATED"},
    }


def to_json(plan: dict) -> str:
    """Deterministic serialisation: same worlds, same bytes."""
    return json.dumps(plan, sort_keys=True, separators=(",", ":"))
