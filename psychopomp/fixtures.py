"""Canonical corpora and oracle-truth helpers, shared by scripts and tests.

Cleared-episode contract: every enter has its exit, because C5 needs both
exit velocities (see epec.py). Corpus builders enforce it; a truncated
episode is out of scope, not silently zero-world.
"""
from __future__ import annotations

import random
from typing import List, Tuple

from .epec import summarize
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


def has_hidden_contact(ep: SimEpisode) -> bool:
    return any(
        e.kind == "ball_collide" and not e.observable for e in ep.oracle_log()
    )


def truth_matches(ep: SimEpisode) -> Tuple[Tuple[int, int], ...]:
    """Oracle pairing as (enter_idx, exit_idx) over the observable log order."""
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
                ei = next(i for i, e in enumerate(enters) if e.t == a)
                xi = next(i for i, e in enumerate(exits) if e.t == b)
                pairs.append((ei, xi))
    return tuple(sorted(pairs))
