"""E2: a read-only, revision-pinned view of a Physis world.

Psychopomp proposes graph edits; it must never hold a live handle on the
authoritative graph, and every proposal must name the state it was computed
against. This module is the only place that turns Physis output into something
Psychopomp can reason over, and it is deliberately **parse-only**: no writes, no
inference, no promotion of a parsed edge to "derived".

Shapes come from `physis` 1.9.1 (`object list --json`, `object get <id> --json`).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

OUTGOING = ("out", "outgoing")


@dataclass(frozen=True)
class Edge:
    source: str
    predicate: str
    target: str

    def key(self) -> tuple[str, str, str]:
        return (self.source, self.predicate, self.target)


@dataclass
class Snapshot:
    """Entities, edges and the revision they were read at. Immutable by use."""
    entities: dict[str, str] = field(default_factory=dict)   # id -> kind
    edges: list[Edge] = field(default_factory=list)
    evidence_seqs: list[int] = field(default_factory=list)
    #: Externally established base (e.g. an audit-packet sha256); None = compute.
    pin: str | None = None

    @property
    def revision(self) -> str:
        return self.pin or self.digest

    @property
    def digest(self) -> str:
        """A digest over what was read, so a proposal can name its base."""
        payload = json.dumps(
            {"entities": sorted(self.entities.items()),
             "edges": sorted(edge.key() for edge in self.edges),
             "evidence": sorted(set(self.evidence_seqs))},
            sort_keys=True, separators=(",", ":"),
        )
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

    def has_entity(self, entity_id: str) -> bool:
        return entity_id in self.entities


def from_cli(objects: dict, details: list[dict], *, pin: str | None = None) -> Snapshot:
    """Parse `object list --json` plus one `object get --json` per object.

    `pin` overrides the revision with an externally established one (e.g. an
    audit packet's sha256); otherwise the digest is computed from the parse.
    """
    if not isinstance(objects, dict) or not isinstance(objects.get("objects"), list):
        raise ValueError("objects payload has no 'objects' list")
    snapshot = Snapshot()
    for row in objects["objects"]:
        entity_id, kind = row.get("id"), row.get("kind")
        if not isinstance(entity_id, str) or not entity_id or not isinstance(kind, str):
            raise ValueError("an object row is missing its id or kind")
        if entity_id in snapshot.entities:
            raise ValueError(f"duplicate entity {entity_id!r}")
        snapshot.entities[entity_id] = kind

    seen: set[tuple[str, str, str]] = set()
    for detail in details:
        origin = detail.get("id")
        if origin not in snapshot.entities:
            raise ValueError(f"relation detail for unknown object {origin!r}")
        for seq in detail.get("evidence") or []:
            if type(seq) is not int:
                raise ValueError("evidence seqs must be integers")
            snapshot.evidence_seqs.append(seq)
        for rel in detail.get("relations") or []:
            predicate = rel.get("predicate")
            if not isinstance(predicate, str) or not predicate:
                raise ValueError("a relation has no predicate")
            # `get` reports direction + other; `relations` reports source/target.
            if "source" in rel and "target" in rel:
                edge = Edge(rel["source"], predicate, rel["target"])
            else:
                other, direction = rel.get("other"), rel.get("direction")
                if not isinstance(other, str) or direction not in (*OUTGOING, "in", "incoming"):
                    raise ValueError("a relation has neither endpoints nor direction")
                edge = (Edge(origin, predicate, other) if direction in OUTGOING
                        else Edge(other, predicate, origin))
            for endpoint in (edge.source, edge.target):
                if endpoint not in snapshot.entities:
                    raise ValueError(
                        f"edge {edge.key()} names unobserved entity {endpoint!r}")
            if edge.key() not in seen:
                seen.add(edge.key())
                snapshot.edges.append(edge)

    snapshot.edges.sort(key=Edge.key)
    if pin is not None:
        if not isinstance(pin, str) or not pin:
            raise ValueError("pin must be a non-empty string")
        snapshot.pin = pin
    return snapshot
