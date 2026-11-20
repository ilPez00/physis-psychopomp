"""ASP (clingo) encoding of the possible-world filter — unweighted.

Numeric facts are computed in Python and asserted as facts: velocity
equality (C4) and contact feasibility (C5: momentum sum, relative-speed
preservation, interval overlap). clingo then does the combinatorial search
and the logical constraints (C1 coverage, C2 order, contact pairing). This
mirrors EPEC's split between numeric reasoning and the ASP search and keeps
the ASP layer integer-only (clingo has no floats).

C3 (the 2-ball concurrency bound) is a structural check and is not encoded:
per-world counting stays in `epec.validate`. The cross-check test therefore
compares matchings on fixtures where C3 does not bind.

Cross-check: `worlds_via_asp(log)` and the Python enumeration in
`epec.consistent_worlds` must return the same matchings.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import clingo

from .epec import TOL, _close, _overlaps, _relnorm, _sum, _vel
from .eventlog import EventLog

PROGRAM = """
{ match(E,X) : enter(E) } = 1 :- exit(X).
:- match(E,X1), match(E,X2), X1 != X2.
:- match(E,X), tent(E,T1), texit(X,T2), T1 >= T2.
{ pair(E1,E2) : enter(E1), enter(E2), E1 < E2 }.
:- pair(E1,E2), not match(E1,_).
:- pair(E1,E2), not match(E2,_).
:- pair(E1,E2), pair(E1,E3), E2 != E3.
:- pair(E1,E2), pair(E3,E2), E1 != E3.
:- pair(E1,E2), match(E1,X1), match(E2,X2), not contact_ok(E1,X1,E2,X2).
:- match(E,X), not c4_ok(E,X), not paired(E).
paired(E) :- pair(E,_).
paired(E) :- pair(_,E).
#show match/2.
"""


def _contact_ok(e1, x1, e2, x2) -> bool:
    v1, v2, w1, w2 = _vel(e1), _vel(e2), _vel(x1), _vel(x2)
    if None in (v1, v2, w1, w2):
        return True  # unmeasured: cannot falsify
    return (
        _close(_sum([v1, v2]), _sum([w1, w2]))
        and abs(_relnorm(v1, v2) - _relnorm(w1, w2)) <= TOL
        and _overlaps((e1.t, x1.t), (e2.t, x2.t))
    )


def worlds_via_asp(log: EventLog) -> List[Tuple[Tuple[int, int], ...]]:
    enters = [e for e in log.events if e.kind == "enter_occ"]
    exits = [e for e in log.events if e.kind == "exit_occ"]
    facts: List[str] = []
    for i, e in enumerate(enters):
        facts.append(f"enter({i}). tent({i},{e.t}).")
    for j, x in enumerate(exits):
        facts.append(f"exit({j}). texit({j},{x.t}).")
    for i, e in enumerate(enters):
        for j, x in enumerate(exits):
            if _close(_vel(x), _vel(e)):
                facts.append(f"c4_ok({i},{j}).")
    for i in range(len(enters)):
        for k in range(i + 1, len(enters)):
            for j in range(len(exits)):
                for l in range(len(exits)):
                    if j != l and _contact_ok(enters[i], exits[j], enters[k], exits[l]):
                        facts.append(f"contact_ok({i},{j},{k},{l}).")
    prog = PROGRAM + "\n" + "\n".join(facts)

    ctl = clingo.Control(["--models=0"])
    ctl.add("base", [], prog)
    ctl.ground([("base", [])])
    worlds = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            ms = []
            for sym in model.symbols(shown=True):
                if sym.name == "match":
                    a, b = sym.arguments
                    ms.append((a.number, b.number))
            worlds.append(tuple(sorted(ms)))
    return worlds


def compare_worlds(log: EventLog) -> dict:
    """Cross-check: ASP matchings vs Python enumeration matchings."""
    from .epec import consistent_worlds

    py = sorted({w.matches for w in consistent_worlds(log)})
    asp = sorted(set(worlds_via_asp(log)))
    return {"python": py, "asp": asp, "equal": py == asp}
