"""Canonical corpora and oracle-truth helpers, shared by scripts and tests.

Cleared-episode contract: every enter has its exit, because C5 needs both
exit velocities (see epec.py). Corpus builders enforce it; a truncated
episode is out of scope, not silently zero-world.
"""
from __future__ import annotations

import random
from typing import List, Tuple

from .epec import consistent_worlds, summarize
from .sim import Init, SimConfig, SimEpisode, run

RANDOM_CFG = SimConfig(steps=300, speed=3.0)
TARGET_CFG = SimConfig(steps=200)
PASS_CFG = SimConfig(steps=150)

STRAIGHT = Init(x=(20.0, 20.0), y=(50.0, 80.0), v=((3.0, 0.0), (3.0, 0.0)))
OFF_AXIS = Init(x=(20.0, 52.0), y=(45.0, 20.0), v=((3.0, 1.0), (0.0, 3.3)))


def random_corpus(n: int = 8, max_seed: int = 400) -> List[SimEpisode]:
    out: List[SimEpisode] = []
    seed = 0
    while len(out) < n and seed < max_seed:
        ep = run(RANDOM_CFG, seed)
        s = summarize(ep.observable_log())
        if s["enters"] >= 1 and s["enters"] == s["exits"]:
            out.append(ep)
        seed += 1
    return out


def targeted_corpus(n: int = 6, tries: int = 400, seed: int = 7) -> List[SimEpisode]:
    """Aimed near the occluder centre: contains hidden contacts."""
    out: List[SimEpisode] = []
    rng = random.Random(seed)
    k = 0
    while len(out) < n and k < tries:
        k += 1
        init = Init(
            x=(rng.uniform(15, 25), rng.uniform(48, 56)),
            y=(rng.uniform(40, 50), rng.uniform(15, 27)),
            v=((3.0, rng.uniform(0.4, 1.2)), (0.0, rng.uniform(2.8, 4.0))),
        )
        ep = run(TARGET_CFG, 0, init=init)
        hidden = [e for e in ep.oracle_log() if e.kind == "ball_collide" and not e.observable]
        s = summarize(ep.observable_log())
        if hidden and s["enters"] == 2 and s["exits"] == 2:
            out.append(ep)
    return out


def recrossing_episode() -> SimEpisode:
    """One ball crosses twice (wall bounce between crossings), no contact."""
    cfg = SimConfig(steps=520)
    return run(cfg, 0, init=Init(x=(30.0, 30.0), y=(50.0, 85.0), v=((3.0, 0.0), (0.05, 0.0))))


def parallel_lane_corpus(
    sep: float = 6.0, noise: float = 0.0, n: int = 6, max_k: int = 200
) -> List[SimEpisode]:
    """Two parallel lanes separated by ``sep``; attributable episodes only."""
    from .epec import consistent_worlds

    eps: List[SimEpisode] = []
    for k in range(max_k):
        init = Init(
            x=(30.0, 30.0 + 2.0 * (k % 5)),
            y=(45.0, 45.0 + sep),
            v=((3.0, 0.0), (3.0, 0.0)),
        )
        ep = run(SimConfig(steps=600, noise=noise), k, init=init)
        tol = max(noise, 1e-4)
        if not consistent_worlds(ep.observable_log(), tol):
            continue
        try:
            truth_matches(ep)
        except ValueError:
            continue
        eps.append(ep)
        if len(eps) >= n:
            break
    return eps


def parallel_recrossing_corpus(n: int = 6, tries: int = 80, noise: float = 0.0) -> List[SimEpisode]:
    """Two balls on parallel paths, both crossing twice — the A2 family.

    Each episode has four crossing events, four contact-free consistent worlds
    (two velocity classes, two crossings each) and an *attributable* truth: the
    balls start at different x, so their crossing timestamps differ. That makes
    it the only shipped corpus where identity, not physics, is the question.
    """
    out: List[SimEpisode] = []
    cfg = SimConfig(steps=600, noise=noise)
    for k in range(tries):
        init = Init(x=(30.0, 30.0 + 2.0 * (k % 5)), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
        ep = run(cfg, k, init=init)
        worlds = consistent_worlds(ep.observable_log())
        if len(worlds) != 4 or any(w.swaps for w in worlds):
            continue
        try:
            truth_matches(ep)
        except ValueError:
            continue
        out.append(ep)
        if len(out) >= n:
            break
    return out


def has_hidden_contact(ep: SimEpisode) -> bool:
    return any(
        e.kind == "ball_collide" and not e.observable for e in ep.oracle_log()
    )


def _unique_index(events, t: int, what: str) -> int:
    """Index of the single `what` event at time `t`; refuse to guess when shared.

    Two balls on the same trajectory cross at the same timestamps, and an
    identity-free log then cannot say which crossing belongs to which ball.
    Resolving by time alone used to return the same index twice -- a "truth"
    that is not a bijection, so no world can equal it and every score against
    it is fabricated. Measured 2026-11-21: identical trajectories gave
    ((0,0),(0,0),(1,1),(1,1)); offset ones gave a clean bijection.
    """
    hits = [i for i, e in enumerate(events) if e.t == t]
    if len(hits) != 1:
        raise ValueError(
            f"ambiguous oracle truth: {len(hits)} {what} events at t={t} in the "
            "observable log, so this crossing cannot be attributed to a ball. "
            "Exclude the episode (and count the exclusion); do not invent a truth."
        )
    return hits[0]


def truth_matches(ep: SimEpisode) -> Tuple[Tuple[int, int], ...]:
    """Oracle pairing as (enter_idx, exit_idx) over the observable log order.

    Raises ValueError when the pairing is not a bijection over observable
    events: an unusable truth must stop the caller, not score against noise.
    """
    obs = ep.observable_log()
    enters = [e for e in obs if e.kind == "enter_occ"]
    exits = [e for e in obs if e.kind == "exit_occ"]
    pairs = []
    balls = sorted({e.subjects[0] for e in ep.oracle_log() if e.kind == "enter_occ"})
    for ball in balls:
        ent = sorted(e.t for e in ep.oracle_log() if e.kind == "enter_occ" and e.subjects[0] == ball)
        exi = sorted(e.t for e in ep.oracle_log() if e.kind == "exit_occ" and e.subjects[0] == ball)
        for a, b in zip(ent, exi):
            if b > a:
                pairs.append((_unique_index(enters, a, "enter"), _unique_index(exits, b, "exit")))
    used_enters = [a for a, _ in pairs]
    used_exits = [b for _, b in pairs]
    if len(set(used_enters)) != len(used_enters) or len(set(used_exits)) != len(used_exits):
        raise ValueError(
            f"ambiguous oracle truth: pairing {pairs} reuses an event index; "
            "exclude the episode and count the exclusion."
        )
    if len(pairs) != len(exits):
        raise ValueError(
            f"ambiguous oracle truth: {len(pairs)} pairs for {len(exits)} exits; "
            "the oracle and the observable log disagree about this episode."
        )
    return tuple(sorted(pairs))
