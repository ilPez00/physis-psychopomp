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

import hashlib
import json
from typing import List

from .sim import SimEpisode

SCHEMA = "psychopomp.observation/1"


def observation_records(ep: SimEpisode, evidence: str = "OBSERVED") -> List[dict]:
    dt = ep.config.dt
    subject = f"episode:{ep.seed}:{ep.episode}"
    records = []
    # Canonical order (R-P1.39): the observable log is appended in body-index
    # order, which leaks identity through event *sequence* even when every event
    # is identity-free. Sorting here means a consumer never receives that channel.
    events = sorted(ep.observable_log(),
                    key=lambda e: (e.t, e.kind, e.subjects, sorted(e.attrs.items())))
    for e in events:
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


#: Turnover has no simulated clock, so one tick is one second. Stated here
#: rather than left implied: a consumer that assumes milliseconds is wrong by 1000.
TURNOVER_DT = 1.0


def _turnover_config_sha() -> str:
    """Digest of the fixture's declared shape, identical for every episode.

    Deliberately excludes the target, the perturbation and the arm: those are the
    episode's situation and its hidden variable, so folding them in would put the
    answer inside the provenance a consumer is allowed to read.
    """
    from .turnover import INVARIANT, OBSERVE, PERTURB_TICK

    declared = {"invariant": INVARIANT, "observe": list(OBSERVE),
                "perturb_tick": PERTURB_TICK, "loads": [4, 4],
                "components": {"1": [1, 1], "2": [2, 1]}, "dt": TURNOVER_DT}
    payload = json.dumps(declared, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()



def turnover_records(run, episode: int, ticks=None) -> List[dict]:
    """One record per observed tick of a turnover episode.

    The arm is the **hypothesis** under test, so it never reaches the record —
    a consumer that could read it back would be handed the answer. Role order is
    kept because the two roles are the organization's structure, not component
    identity: the fixture replaces every component while each role keeps its
    load, and `relabel=True` exists to ask whether an analysis depends on that
    order. Component generations are deliberately absent for the same reason.
    """
    from .turnover import OBSERVE

    ticks = OBSERVE if ticks is None else ticks
    subject = f"episode:0:{episode}"
    records = []
    for seq, tick in enumerate(ticks):
        if tick not in run.loads:
            raise ValueError(f"tick {tick} is outside the recorded episode")
        records.append(
            {
                "schema": SCHEMA,
                "subject": subject,
                "kind": "loads",
                "at": round(tick * TURNOVER_DT, 6),
                "props": {"loads": list(run.loads[tick]), "tick": tick, "dt": TURNOVER_DT},
                "provenance": {"source": "sim:turnover/v0.1", "config_sha256": "",
                               "seed": 0, "episode": episode},
                "evidence": "OBSERVED",
                "seq": seq,
            }
        )
    return records

