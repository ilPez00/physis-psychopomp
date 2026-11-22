"""Counterfactual attribution (R-P1.8).

Given an OBSERVED episode and a finite set of declared intervention
hypotheses, rank the hypotheses by how well a re-simulation reproduces the
observable log. Every candidate is a counterfactual (provenance
``counterfactual:v0.1``); only the observed episode is an execution.

Distance: per kind (enter/exit), velocity distances between aligned events,
plus penalties for side or count mismatches and a light time displacement.
With a deterministic simulator the true hypothesis is at exactly 0.

Limits, stated not hidden: a kick the simulator skips (ball hidden at that
step) is observationally identical to "no kick"; attribution returns an
ambiguity set rather than a point answer. Degraded observations break the
exact-zero property; this card is noise-free by construction.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .interventions import COUNTERFACTUAL_SOURCE, Intervention
from .sim import Init, Kick, SimConfig, SimEpisode, run

Hypothesis = Optional[Intervention]
KINDS = ("enter_occ", "exit_occ")
PENALTY = 10.0


def signature(ep: SimEpisode) -> List[tuple]:
    """Identity-free observable signature, canonical under simultaneous events.

    Events at the same step have no observable order (no labels), so sorting by
    value is the honest representation: an ordering artifact must not
    manufacture a distinction the log does not carry. Position is included:
    without it, a kick applied at two different early times would produce the
    same event summary and be misread as identical.
    """
    events = [e for e in ep.observable_log() if e.kind in KINDS]
    out = []
    for e in events:
        v = e.attrs.get("v")
        p = e.attrs.get("pos")
        out.append(
            (e.kind, e.t, e.attrs.get("side"),
             tuple(v) if v else None, tuple(p) if p else None)
        )
    out.sort(key=lambda s: (s[0], s[1], str(s[2]), str(s[3]), str(s[4])))
    return out


def motion_distance(obs: Sequence[tuple], cand: Sequence[tuple]) -> float:
    d = 0.0
    for kind in KINDS:
        a = [s for s in obs if s[0] == kind]
        b = [s for s in cand if s[0] == kind]
        d += PENALTY * abs(len(a) - len(b))
        for (_, ta, sa, va, pa), (_, tb, sb, vb, pb) in zip(a, b):
            d += 0.5 * abs(ta - tb)
            if sa != sb:
                d += PENALTY
            if va is not None and vb is not None:
                d += math.dist(va, vb)
            elif (va is None) != (vb is None):
                d += PENALTY
            if pa is not None and pb is not None:
                d += math.dist(pa, pb)
            elif (pa is None) != (pb is None):
                d += 1.0
    return d


def candidate_episode(
    config: SimConfig,
    seed: int,
    init: Init,
    hypothesis: Hypothesis,
    episode: int = 0,
) -> SimEpisode:
    kicks: Tuple[Kick, ...] = (
        () if hypothesis is None else (Kick(hypothesis.t, hypothesis.ball, hypothesis.dv),)
    )
    return run(
        config, seed, episode=episode, init=init, kicks=kicks,
        source=COUNTERFACTUAL_SOURCE,
    )


def attribute(
    observed: SimEpisode,
    hypotheses: Sequence[Hypothesis],
    config: SimConfig,
    seed: int,
    init: Init,
    tol: float = 1e-9,
) -> dict:
    obs_sig = signature(observed)
    scored = []
    for h in hypotheses:
        cand = candidate_episode(config, seed, init, h)
        scored.append((motion_distance(obs_sig, signature(cand)), h))
    scored.sort(key=lambda pair: (pair[0], str(pair[1])))
    best = scored[0][0]
    tied = [h for d, h in scored if abs(d - best) <= tol]
    runner_up = next((d for d, _ in scored if d > best + tol), None)
    return {
        "scores": scored,
        "best": scored[0][1],
        "best_distance": best,
        "ambiguity": tied,
        "unique": len(tied) == 1,
        "margin": (runner_up - best) if runner_up is not None else float("inf"),
    }
