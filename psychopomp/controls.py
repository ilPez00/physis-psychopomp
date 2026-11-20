"""Structure-preserving shuffled-rule control.

The first version of this module shuffled attributes within (kind, timestamp)
groups. An external audit (2026-11-20) showed that was vacuous: a permutation
of rows leaves the multiset of facts unchanged, so any permutation-invariant
consumer -- and the two-ball observable logs have identical subjects -- saw
exactly the same constraints. `joint_alignment_changed=True` was a false
success signal.

The control now deranges exit-event payloads **across episodes** (Sattolo
cycle: no fixed point for n>=2). Per-episode event counts, kinds, subjects
and timestamps are preserved; corpus-level per-attribute marginals are
preserved exactly (it is still a permutation of the payload multiset); the
enter->exit alignment, which is the EBC rule semantics, is destroyed.

This is the construction-matched control demanded by the Phase 11D lesson
(physis-next PLAN_11: a JEPA-derived latent won on a toy task; the win was a
supervision confound, chance level under a shuffled-label control).
"""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Dict, List, Sequence, Tuple

from .eventlog import Event, EventLog


def _sattolo(rng: random.Random, n: int) -> List[int]:
    """Single-cycle permutation: no fixed point for n >= 2."""
    p = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.randrange(i)
        p[i], p[j] = p[j], p[i]
    return p


def shuffle_rules(
    logs: Sequence[EventLog], seed: int, source: str = "shuffled:v0.1"
) -> List[EventLog]:
    """Derange exit-event payloads across a corpus of observable logs."""
    slots: List[Tuple[int, int]] = []  # (log index, event index)
    payloads: List[dict] = []
    for li, log in enumerate(logs):
        for ei, e in enumerate(log.events):
            if e.kind == "exit_occ":
                slots.append((li, ei))
                payloads.append(dict(e.attrs))
    perm = _sattolo(random.Random(seed), len(payloads))
    out = [EventLog(list(log.events)) for log in logs]
    for k, (li, ei) in enumerate(slots):
        e = out[li].events[ei]
        prov = replace(e.provenance, source=source, seed=seed)
        out[li].events[ei] = Event(
            e.kind, e.t, e.subjects, payloads[perm[k]], e.observable, prov, e.seq
        )
    return out


def control_report(logs: Sequence[EventLog], shuffled: Sequence[EventLog]) -> dict:
    """Denominators: what the control preserved, and whether it bit."""
    assert len(logs) == len(shuffled)
    kinds_times_ok = all(
        sorted((e.kind, e.t) for e in a) == sorted((e.kind, e.t) for e in b)
        for a, b in zip(logs, shuffled)
    )

    def exit_marginals(corpus: Sequence[EventLog]) -> Dict[str, List[str]]:
        cols: Dict[str, List[str]] = {}
        for log in corpus:
            for e in log.events:
                if e.kind == "exit_occ":
                    for k, v in sorted(e.attrs.items()):
                        cols.setdefault(k, []).append(str(v))
        return {k: sorted(v) for k, v in cols.items()}

    marg_ok = exit_marginals(logs) == exit_marginals(shuffled)

    def signatures(corpus: Sequence[EventLog]) -> List[list]:
        """Per-episode (enter.side, exit.side) pairing signature."""
        sigs = []
        for log in corpus:
            ent = [e.attrs.get("side") for e in log.events if e.kind == "enter_occ"]
            exi = [e.attrs.get("side") for e in log.events if e.kind == "exit_occ"]
            sigs.append(sorted(zip(ent, exi)) if len(ent) == len(exi) else None)
        return sigs

    sig_orig, sig_shuf = signatures(logs), signatures(shuffled)
    episodes_changed = sum(1 for a, b in zip(sig_orig, sig_shuf) if a != b)
    return {
        "n_episodes": len(logs),
        "n_events": sum(len(log) for log in logs),
        "kinds_and_times_preserved": kinds_times_ok,
        "exit_marginals_preserved": marg_ok,
        "episodes_with_changed_pairing": episodes_changed,
        "alignment_changed": episodes_changed > 0,
    }
