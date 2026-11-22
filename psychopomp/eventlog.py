"""Typed event log with timestamps and provenance.

Every event carries: kind, time step, subjects, attributes, an observable
flag, and provenance (producer, config hash, seed, episode).

Leakage discipline: observable events contain only quantities an outside
camera could measure -- no simulator identity labels, no hidden positions.
Oracle events are evaluation-only and are never training inputs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

KINDS = frozenset(
    {"enter_occ", "exit_occ", "wall_bounce", "ball_collide", "kick", "kick_skipped",
     # identity evidence: emitted only while the body is visible (R-P1.39)
     "marker"}
)


@dataclass(frozen=True)
class Provenance:
    source: str
    config_sha256: str
    seed: int
    episode: int


@dataclass(frozen=True)
class Event:
    kind: str
    t: int
    subjects: Tuple[str, ...]
    attrs: Dict[str, Any]
    observable: bool
    provenance: Provenance
    seq: int = -1

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown event kind: {self.kind}")

    def relabel(self, **prov: Provenance) -> "Event":
        return replace(self, provenance=prov["provenance"]) if prov else self


class EventLog:
    def __init__(self, events: Optional[List[Event]] = None) -> None:
        self.events: List[Event] = []
        for e in events or []:
            self.add(e)

    def add(self, ev: Event) -> None:
        seq = ev.seq if ev.seq >= 0 else len(self.events)
        self.events.append(replace(ev, seq=seq) if ev.seq != seq else ev)

    def filter(self, kinds: Tuple[str, ...]) -> "EventLog":
        return EventLog([e for e in self.events if e.kind in kinds])

    def observable(self) -> "EventLog":
        return EventLog([e for e in self.events if e.observable])

    def oracle(self) -> "EventLog":
        return EventLog([e for e in self.events if not e.observable])

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self.events)

    def to_jsonl(self, path: str | Path) -> None:
        with open(path, "w") as f:
            for e in self.events:
                f.write(
                    json.dumps(
                        {
                            "kind": e.kind,
                            "t": e.t,
                            "subjects": list(e.subjects),
                            "attrs": e.attrs,
                            "observable": e.observable,
                            "seq": e.seq,
                            "provenance": {
                                "source": e.provenance.source,
                                "config_sha256": e.provenance.config_sha256,
                                "seed": e.provenance.seed,
                                "episode": e.provenance.episode,
                            },
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )

    @staticmethod
    def from_jsonl(path: str | Path) -> "EventLog":
        out = EventLog()
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                p = d["provenance"]
                out.add(
                    Event(
                        kind=d["kind"],
                        t=d["t"],
                        subjects=tuple(d["subjects"]),
                        attrs=d["attrs"],
                        observable=d["observable"],
                        provenance=Provenance(
                            source=p["source"],
                            config_sha256=p["config_sha256"],
                            seed=p["seed"],
                            episode=p["episode"],
                        ),
                        seq=d["seq"],
                    )
                )
        return out
