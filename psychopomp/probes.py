"""Handcrafted CPU probes: M2/M3 baselines before any GPU arm (IMP-5).

M2 — rank the truth world among consistent worlds. Score = total endpoint
deflection sum ||v_exit - v_entry|| over matches. On the 2D contact family the
two consistent worlds are relabelings with identical total deflection, so an
endpoint-only probe is a coin flip. That is the documented stupid control a
learned model must beat; a probe claiming more from endpoints alone would be
an artifact until it explains why.

M3 — hidden-contact detection: the filter's contact_required (decided only
after exit velocities are observed) against the oracle hidden contact. The
deranged control corpus must break this agreement.
"""
from __future__ import annotations

import math
from typing import List

from .controls import shuffle_rules
from .epec import _vel, consistent_worlds, summarize
from .fixtures import has_hidden_contact, truth_matches
from .sim import SimEpisode


def deflection(log, world) -> float:
    enters = [e for e in log.events if e.kind == "enter_occ"]
    exits = [e for e in log.events if e.kind == "exit_occ"]
    total = 0.0
    for a, b in world.matches:
        v, w = _vel(enters[a]), _vel(exits[b])
        if v is None or w is None:
            continue
        total += math.hypot(w[0] - v[0], w[1] - v[1])
    return total


def m2_baseline(eps: List[SimEpisode]) -> dict:
    """Top-1 ranking of the truth world by minimum endpoint deflection."""
    top1 = n = excluded = 0
    worlds: List[int] = []
    for ep in eps:
        log = ep.observable_log()
        ws = consistent_worlds(log)
        worlds.append(len(ws))
        if not ws:
            continue
        try:
            truth = truth_matches(ep)
        except ValueError:
            # Shared timestamps leave the pairing unattributable. Count it as an
            # exclusion so the denominator stays honest; scoring against a
            # fabricated truth is the one thing this baseline must not do.
            excluded += 1
            continue
        scores = sorted(deflection(log, w) for w in ws)
        best = scores[0]
        winners = [w for w in ws if deflection(log, w) == best]
        n += 1
        if len(winners) == 1 and winners[0].matches == truth:
            top1 += 1
    nz = [w for w in worlds if w]
    return {
        "episodes": n,
        "worlds_mean": (sum(worlds) / len(worlds)) if worlds else 0.0,
        "top1": (top1 / n) if n else 0.0,
        "chance": (sum(1.0 / w for w in nz) / len(nz)) if nz else 0.0,
        "excluded_ambiguous_truth": excluded,
    }


def m3_accuracy(eps: List[SimEpisode], shuffled: bool = False) -> dict:
    """Contact detection, with undecided episodes excluded rather than guessed.

    `contact_required` is None when an episode is not cleared (C5 needs both
    exits). Coercing that to bool counted "undecidable" as "no contact" -- the
    same fabrication the oracle-truth fix removed one layer down, so the scorer
    now reports how many episodes it actually scored.
    """
    logs = [ep.observable_log() for ep in eps]
    if shuffled:
        logs = shuffle_rules(logs, seed=12345)
    ok = scored = excluded = 0
    for ep, log in zip(eps, logs):
        decided = summarize(log)["contact_required"]
        if decided is None:
            excluded += 1
            continue
        scored += 1
        ok += int(decided == has_hidden_contact(ep))
    return {
        "accuracy": (ok / scored) if scored else 0.0,
        "scored": scored,
        "excluded": excluded,
    }


def _pos_residual(log, world) -> float:
    """Straight-line residual of `dy` for a contact-free match, in units.

    Amendment A2: a ball entering at (x, y) with velocity v must leave at
    `y + v_y * dt * steps` if nothing acted on it. Contacts are excluded here
    because the residual is only meaningful where no force applied.
    """
    enters = [e for e in log.events if e.kind == "enter_occ"]
    exits = [e for e in log.events if e.kind == "exit_occ"]
    total = 0.0
    for a, b in world.matches:
        ea, xb = enters[a], exits[b]
        v, dt = ea.attrs.get("v"), ea.attrs.get("dt")
        p_in, p_out = ea.attrs.get("pos"), xb.attrs.get("pos")
        # The clock comes from the log: a probe that assumes dt is measuring its
        # own constant, not the episode, and would silently mis-score any config
        # that changed it.
        if v is None or p_in is None or p_out is None or dt is None:
            return float("inf")
        predicted = p_in[1] + v[1] * dt * (xb.t - ea.t)
        total += abs(predicted - p_out[1])
    return total


def m2_position_continuity(eps: List[SimEpisode]) -> dict:
    """Top-1 for the A2 probe: rank worlds by straight-line y residual.

    Only contact-free episodes are scored: where the truth requires a contact
    the residual cannot be zero, so the probe is not applicable and the episode
    is counted as excluded rather than scored against a probe that does not fit.
    """
    top1 = n = excluded = 0
    world_counts: List[int] = []
    for ep in eps:
        log = ep.observable_log()
        ws = consistent_worlds(log)
        if not ws:
            continue
        try:
            truth = truth_matches(ep)
        except ValueError:
            excluded += 1
            continue
        if any(w.swaps for w in ws):
            excluded += 1
            continue
        scores = {w: _pos_residual(log, w) for w in ws}
        best = min(scores.values())
        winners = [w for w, s in scores.items() if s == best]
        n += 1
        world_counts.append(len(ws))
        if len(winners) == 1 and winners[0].matches == truth:
            top1 += 1
    return {
        "episodes": n,
        "top1": (top1 / n) if n else 0.0,
        "chance": (sum(1.0 / w for w in world_counts) / len(world_counts)) if world_counts else 0.0,
        "excluded": excluded,
    }
