"""Possible-world filter over an identity-free observable event log.

Event-calculus matching in the spirit of EPEC (D'Asaro et al.), unweighted.
This is our own encoding written from the published formalism; D'Asaro's
epec-vanilla implementation is architectural reference only (its repository
carries no license file -- do not copy code until licensing is clarified).

A world = (matching of enter/exit events, hidden contact hypotheses).
Velocity attributes are 2D vectors. Contact physics for equal masses:
  * momentum is preserved:   v_exit(b1) + v_exit(b2) == v_enter(a1) + v_enter(a2)
  * relative speed is preserved: |v_enter(a1) - v_enter(a2)| == |v_exit(b1) - v_exit(b2)|
which is exactly the equal-mass exchange of the normal component for some
contact normal (tangential components preserved), without solving for n.

Consistency rules:
  C1 coverage   -- every exit matches exactly one enter; unmatched exits and
                   duplicate assignments are violations. An enter may stay
                   unmatched (ball still inside at episode end).
  C2 order      -- enter.t < exit.t for every match.
  C3 overlap    -- at most 2 life-intervals overlap at once (2-ball sim bound;
                   unmatched enters count as open intervals).
  C4 continuity -- without contact, exit velocity == entry velocity.
  C5 contact    -- a pair of overlapping intervals may exchange normal
                   components: momentum sum and relative speed preserved.

consistent_worlds() enumerates every zero-violation world; validate() scores
a proposed world and names the violated rules. Probabilistic weighting and a
clingo/ASP port are deferred to Claim B (v1+).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations, permutations
from typing import List, Optional, Tuple

from .eventlog import EventLog

TOL = 1e-4
OPEN_END = 10**9


@dataclass(frozen=True)
class World:
    matches: Tuple[Tuple[int, int], ...]      # (enter_idx, exit_idx)
    swaps: Tuple[Tuple[int, int], ...]        # enter_idx pairs with hidden contact
    unmatched: Tuple[int, ...]                # enter indices still inside

    def describe(self) -> str:
        parts = [f"enter{a}->exit{b}" for a, b in self.matches]
        if self.swaps:
            parts.append("hidden contact: " + ",".join(f"{a}<->{b}" for a, b in self.swaps))
        if self.unmatched:
            parts.append("still inside: " + ",".join(map(str, self.unmatched)))
        return "; ".join(parts)


def _vec(v):
    return v if isinstance(v, (list, tuple)) else None


def _close(a, b, tol: float = TOL) -> bool:
    if a is None or b is None:
        return True  # unmeasured velocity cannot falsify; counted in summarize()
    va, vb = _vec(a), _vec(b)
    if va is not None and vb is not None:
        return all(abs(u - v) <= tol for u, v in zip(va, vb))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return False


def _sum(vs: List) -> List[float]:
    s = [0.0, 0.0]
    for v in vs:
        s[0] += v[0]
        s[1] += v[1]
    return s


def _relnorm(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _vel(ev) -> Optional[List[float]]:
    return _vec(ev.attrs.get("v"))


def validate(world: World, enters: List, exits: List) -> List[str]:
    """Return the list of violated rule names for a proposed world."""
    bad: List[str] = []
    used_exits = [b for (_, b) in world.matches]
    used_enters = [a for (a, _) in world.matches]
    # C1: complete exit coverage, no duplicate assignments
    if sorted(used_exits) != list(range(len(exits))):
        bad.append("C1")
    if len(set(used_exits)) != len(used_exits) or len(set(used_enters)) != len(used_enters):
        bad.append("C1")
    for a, b in world.matches:
        if not enters[a].t < exits[b].t:
            bad.append("C2")

    # C3: at most 2 concurrent life-intervals; unmatched enters are open ones
    intervals = [(enters[a].t, exits[b].t) for a, b in world.matches]
    intervals += [(enters[u].t, OPEN_END) for u in world.unmatched]
    for i in range(len(intervals)):
        conc = sum(1 for j in range(len(intervals)) if j != i and _overlaps(intervals[i], intervals[j]))
        if conc >= 2:
            bad.append("C3")
            break

    # C4/C5
    pair_of = {}
    for pa, pb in world.swaps:
        pair_of.setdefault(pa, pb)
        pair_of.setdefault(pb, pa)
    if len(pair_of) != 2 * len(world.swaps):
        bad.append("C5")  # a swap member used twice
    match_of = {a: b for (a, b) in world.matches}
    for a, b in world.matches:
        if a not in pair_of:
            if not _close(_vel(exits[b]), _vel(enters[a])):
                bad.append("C4")
    for pa, pb in world.swaps:
        if pa not in match_of or pb not in match_of:
            bad.append("C5")
            continue
        ea, eb = _vel(enters[pa]), _vel(enters[pb])
        xa, xb = _vel(exits[match_of[pa]]), _vel(exits[match_of[pb]])
        if ea is None or eb is None or xa is None or xb is None:
            continue  # unmeasured: cannot falsify
        if not _close(_sum([ea, eb]), _sum([xa, xb])):
            bad.append("C5")
        if abs(_relnorm(ea, eb) - _relnorm(xa, xb)) > TOL:
            bad.append("C5")
        if not _overlaps((enters[pa].t, exits[match_of[pa]].t),
                         (enters[pb].t, exits[match_of[pb]].t)):
            bad.append("C5")
    return sorted(set(bad))


def consistent_worlds(log: EventLog) -> List[World]:
    """Enumerate all zero-violation worlds over the log's enter/exit events."""
    enters = [e for e in log.events if e.kind == "enter_occ"]
    exits = [e for e in log.events if e.kind == "exit_occ"]
    worlds: List[World] = []
    n_e, n_x = len(enters), len(exits)
    if n_x > n_e:
        return []  # C1 impossible: exits with no candidate enters
    # C1: every exit matched -> choose exactly n_x enters and permute them
    for chosen in combinations(range(n_e), n_x):
        for perm in permutations(range(n_x)):
            matches = tuple((chosen[k], perm[k]) for k in range(n_x))
            unmatched = tuple(i for i in range(n_e) if i not in chosen)
            w = World(matches, (), unmatched)
            bad = validate(w, enters, exits)
            if not bad:
                worlds.append(w)
                continue
            if bad == ["C4"]:
                fails = [
                    (a, b) for (a, b) in matches
                    if not _close(_vel(exits[b]), _vel(enters[a]))
                ]
                if len(fails) == 2:
                    (a1, _), (a2, _) = fails
                    w2 = World(matches, ((a1, a2),), unmatched)
                    if not validate(w2, enters, exits):
                        worlds.append(w2)
    return worlds


def summarize(log: EventLog) -> dict:
    ws = consistent_worlds(log)
    enters = [e for e in log.events if e.kind == "enter_occ"]
    exits = [e for e in log.events if e.kind == "exit_occ"]
    unconstrained = 0
    for w in ws:
        for a, b in w.matches:
            if _vel(enters[a]) is None or _vel(exits[b]) is None:
                unconstrained += 1
    return {
        "enters": len(enters),
        "exits": len(exits),
        "n_worlds": len(ws),
        "contact_required": bool(ws) and all(w.swaps for w in ws),
        "unconstrained": unconstrained,
        "worlds": [w.describe() for w in ws],
    }
