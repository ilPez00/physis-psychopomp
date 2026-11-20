"""Structure-preserving shuffled-rule control.

Corrupts a rule set (the observable event predicates that will feed the EBC
arm) while preserving: rule count, predicate vocabulary, per-predicate
counts, per-attribute marginal distributions and temporal positions. Only
the semantic alignment between rules and outcomes is destroyed.

This is the construction-matched control demanded by the Phase 11D lesson
(physis-next PLAN_11: a JEPA-derived latent won on a toy task and the win
was a supervision confound; chance level under a shuffled-label control).
The shuffled arm must be first-class from day one, not a later ablation.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .eventlog import Event, EventLog, Provenance


def shuffle_rules(log: EventLog, seed: int, source: str = "shuffled:v0.1") -> EventLog:
    """Return a corrupted copy of an observable rule/event set.

    Per-kind, per-attribute columns are independently permuted (seeded).
    Timestamps, kinds and provenance config hash are preserved; each column's
    marginal distribution is exactly preserved; the joint alignment with any
    outcome is not.
    """
    rng = random.Random(seed)
    groups: Dict[Tuple[str, int], List[Event]] = {}
    for e in log.events:
        groups.setdefault((e.kind, e.t), []).append(e)

    out = EventLog()
    for (kind, _t), group in sorted(groups.items()):
        if len(group) <= 1:
            for e in group:
                out.add(e)
            continue
        keys = sorted(group[0].attrs)
        cols = {k: [e.attrs.get(k) for e in group] for k in keys}
        perms = {k: _perm(rng, len(group)) for k in keys}
        new_prov = Provenance(
            source=source,
            config_sha256=group[0].provenance.config_sha256,
            seed=seed,
            episode=group[0].provenance.episode,
        )
        for idx, e in enumerate(group):
            attrs = {k: cols[k][perms[k][idx]] for k in keys}
            out.add(
                Event(
                    kind=e.kind,
                    t=e.t,
                    subjects=e.subjects,
                    attrs=attrs,
                    observable=e.observable,
                    provenance=new_prov,
                )
            )
    return out


def _perm(rng: random.Random, n: int) -> List[int]:
    while True:
        p = list(range(n))
        rng.shuffle(p)
        if n < 2 or p != list(range(n)):
            return p


def control_report(original: EventLog, shuffled: EventLog) -> dict:
    """Denominators for the control: what was preserved, what changed."""
    def profile(l: EventLog) -> dict:
        kinds: Dict[str, int] = {}
        cols: Dict[Tuple[str, str], List] = {}
        ts: Dict[str, List[int]] = {}
        for e in l.events:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
            ts.setdefault(e.kind, []).append(e.t)
            for k, v in sorted(e.attrs.items()):
                cols.setdefault((e.kind, k), []).append(v)
        return {
            "kinds": kinds,
            "times": {k: sorted(v) for k, v in ts.items()},
            "marginals": {f"{a}.{b}": sorted(map(str, v)) for (a, b), v in cols.items()},
        }

    po, ps = profile(original), profile(shuffled)
    preserved = po["kinds"] == ps["kinds"] and po["times"] == ps["times"] and po["marginals"] == ps["marginals"]
    joint_o = [(e.kind, e.t, tuple(sorted(e.attrs.items()))) for e in original.events]
    joint_s = [(e.kind, e.t, tuple(sorted(e.attrs.items()))) for e in shuffled.events]
    return {
        "n_events": len(original.events),
        "preserved_marginals_and_times": preserved,
        "joint_alignment_changed": joint_o != joint_s,
    }
