"""Possible-world filter over an identity-free observable event log.

Event-calculus matching in the spirit of EPEC (D'Asaro et al.), unweighted.
This is our own encoding written from the published formalism; D'Asaro's
epec-vanilla implementation is architectural reference only (its repository
carries no license file -- do not copy code until licensing is clarified).

A world = (matching of enter/exit events, hidden contact hypotheses).
Consistency rules:
  C1 coverage   -- every exit matches exactly one enter; an enter may stay
                   unmatched (ball still inside at episode end).
  C2 order      -- enter.t < exit.t for every match.
  C3 overlap    -- at most 2 intervals overlap at once (2-ball sim bound).
  C4 continuity -- without contact, v_exit == v_entry (within tol).
  C5 contact    -- a pair of overlapping intervals may exchange velocities:
                   v_exit(a) == v_entry(b) and v_exit(b) == v_entry(a);
                   each such pair is one hidden ball_collide hypothesis.

consistent_worlds() enumerates every zero-violation world; validate() scores
a proposed world and names the violated rules. Probabilistic weighting and a
clingo/ASP port are deferred to Claim B (v1+).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Dict, List, Optional, Tuple

from .eventlog import EventLog

TOL = 1e-6


@dataclass(frozen=True)
class World:
    matches: Tuple[Tuple[int, int], ...]      # (enter_idx, exit_idx)
    swaps: Tuple[Tuple[int, int], ...]        # enter_idx pairs with hidden contact
    unmatched: Tuple[int, ...]                # enter indices still inside

    def describe(self) -> str:
        parts = []
        for a, b in self.matches:
            parts.append(f"enter{a}->exit{b}")
        if self.swaps:
            parts.append("hidden contact: " + ",".join(f"{a}<->{b}" for a, b in self.swaps))
        if self.unmatched:
            parts.append("still inside: " + ",".join(map(str, self.unmatched)))
        return "; ".join(parts)


def _v(ev) -> Optional[float]:
    return ev.attrs.get("v")


def _close(a: Optional[float], b: Optional[float], tol: float = TOL) -> bool:
    if a is None or b is None:
        return True  # unmeasured velocity cannot falsify; counted in output
    return abs(a - b) <= tol


def _overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def validate(world: World, enters: List, exits: List) -> List[str]:
    """Return the list of violated rule names for a proposed world."""
    bad: List[str] = []
    used = [b for (_, b) in world.matches]
    if len(set(used)) != len(used):
        bad.append("C1")
    for a, b in world.matches:
        if not enters[a].t < exits[b].t:
            bad.append("C2")
    intervals = [(enters[a].t, exits[b].t) for a, b in world.matches]
    for i in range(len(intervals)):
        ov = [j for j in range(len(intervals)) if j != i and _overlaps(intervals[i], intervals[j])]
        if len(ov) > 1:
            bad.append("C3")
            break
    swapped = {frozenset(p) for p in world.swaps}
    # velocity bookkeeping
    for k, (a, b) in enumerate(world.matches):
        pair = next((p for p in world.swaps if a in p), None)
        if pair is None:
            if not _close(_v(exits[b]), _v(enters[a])):
                bad.append("C4")
        else:
            other = next(x for x in pair if x != a)
            mb = next((m for m in world.matches if m[0] == other), None)
            if mb is None:
                bad.append("C5")
                continue
            if not (
                _close(_v(exits[b]), _v(enters[other]))
                and _close(_v(exits[mb[1]]), _v(enters[a]))
            ):
                bad.append("C5")
            if not _overlaps((enters[a].t, exits[b].t), (enters[other].t, exits[mb[1]].t)):
                bad.append("C5")
    if len(swapped) != len(world.swaps):
        bad.append("C5")
    return sorted(set(bad))


def consistent_worlds(log: EventLog) -> List[World]:
    """Enumerate all zero-violation worlds over the log's enter/exit events."""
    enters = [e for e in log.events if e.kind == "enter_occ"]
    exits = [e for e in log.events if e.kind == "exit_occ"]
    worlds: List[World] = []
    n_e, n_x = len(enters), len(exits)
    if n_x > n_e:
        return []  # C1 cannot hold: an exit with no candidate enter
    for chosen in combinations(range(n_e), n_x):
        for perm in permutations(range(n_x)):
            matches = tuple((chosen[k], perm[k]) for k in range(n_x))
            unmatched = tuple(i for i in range(n_e) if i not in chosen)
            w = World(matches, (), unmatched)
            bad = validate(w, enters, exits)
            if not bad:
                worlds.append(w)
                continue
            if "C4" in bad and "C5" not in bad and len(bad) <= 2:
                # try pairing every C4-failing match into one swap hypothesis
                fails = [
                    (a, b)
                    for (a, b) in matches
                    if not _close(_v(exits[b]), _v(enters[a]))
                ]
                if len(fails) == 2:
                    (a1, b1), (a2, b2) = fails
                    w2 = World(matches, ((a1, a2),), unmatched)
                    if not validate(w2, enters, exits):
                        worlds.append(w2)
    return worlds


def summarize(log: EventLog) -> dict:
    ws = consistent_worlds(log)
    return {
        "enters": sum(1 for e in log.events if e.kind == "enter_occ"),
        "exits": sum(1 for e in log.events if e.kind == "exit_occ"),
        "n_worlds": len(ws),
        "worlds": [w.describe() for w in ws],
    }
