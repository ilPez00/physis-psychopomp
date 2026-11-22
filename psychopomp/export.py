"""Observable → observation export contract (mission P1, R-P1.7 / IMP-4).

One versioned JSONL record per observable event. The oracle log is never
read, so an export cannot carry hidden state; observable events are
identity-free by construction. Only provenance sources that are executed
simulations (`sim:*`) may be exported — a counterfactual export is refused,
the same rule as `ObservationLedger`.

Schema ``psychopomp.observation/1``::

    {"schema": "psychopomp.observation/1",
     "subject": "episode:<seed>:<episode>",
     "kind": "enter_occ",
     "at": 6.7,                      # seconds = event step * dt
     "props": {"side": "left", "v": [...], "pos": [...], "dt": 0.1, ...},
     "provenance": {"source": "sim:v0.2", "config_sha256": "...",
                    "seed": 0, "episode": 0},
     "evidence": "OBSERVED",
     "seq": 3}

The consumer side is **measured absent** (2026-11-22): `physis ingest` is a
closed 12-source connector registry with per-source parsers and byte ceilings,
and there is no generic JSONL ingress or `import` subcommand. See
`docs/2026-11-22-R-P1.7-ingest-measurement.md`. This module is the producer side
only, and no compatibility is claimed.
"""
from __future__ import annotations

import json
from typing import List

from .sim import SimEpisode

SCHEMA = "psychopomp.observation/1"


def observation_records(ep: SimEpisode, evidence: str = "OBSERVED") -> List[dict]:
    dt = ep.config.dt
    subject = f"episode:{ep.seed}:{ep.episode}"
    records = []
    for e in ep.observable_log():
        if not e.provenance.source.startswith("sim:"):
            raise ValueError(
                f"refusing to export a {e.provenance.source} event as an observation"
            )
        records.append(
            {
                "schema": SCHEMA,
                "subject": subject,
                "kind": e.kind,
                "at": round(e.t * dt, 6),
                "props": dict(e.attrs),
                "provenance": {
                    "source": e.provenance.source,
                    "config_sha256": e.provenance.config_sha256,
                    "seed": e.provenance.seed,
                    "episode": e.provenance.episode,
                },
                "evidence": evidence,
                "seq": e.seq,
            }
        )
    return records


def write_observations(ep: SimEpisode, path: str, evidence: str = "OBSERVED") -> int:
    records = observation_records(ep, evidence)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return len(records)


def read_observations(path: str) -> List[dict]:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
