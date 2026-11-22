"""R-P1.39 — is identity coverage-gated like events?

Prereg: docs/2026-11-22-PREREG-R-P1.39-identity-coverage.md, registered before this
script existed (claim registered before the run).

A world and its relabelling (the two bodies exchanged) are compared. Without
identity evidence the logs must be identical; with markers that are visible they
differ; with markers that can never be emitted they are identical again; and a
second vantage that exposes the bodies restores the difference.

Usage: .venv/bin/python scripts/identity-coverage-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.sim import Init, SimConfig, run

BODIES = (((20.0, 45.0), (3.0, 0.0)), ((80.0, 51.0), (-3.0, 0.0)))
STILL = (((40.0, 50.0), (0.0, 0.0)), ((60.0, 50.0), (0.0, 0.0)))


def episode(*, o, o2, marker: bool, swapped: bool, bodies=None):
    bodies = bodies or BODIES
    a, b = bodies if not swapped else (bodies[1], bodies[0])
    init = Init(x=(a[0][0], b[0][0]), y=(a[0][1], b[0][1]),
                v=(a[1], b[1]))
    cfg = SimConfig(steps=300, o=o, o2=o2, identity_marker=marker, marker_period=10,
                    allow_hidden_init=True)
    return run(cfg, 0, episode=0, init=init)


def log_of(ep):
    return [(e.kind, e.t, e.subjects, tuple(sorted(e.attrs.items())))
            for e in ep.observable_log()]


def markers(ep):
    return [e for e in ep.observable_log() if e.kind == "marker"]


def case(label: str, *, o, o2, marker: bool, bodies=None) -> dict:
    plain = log_of(episode(o=o, o2=o2, marker=marker, swapped=False, bodies=bodies))
    relabel = log_of(episode(o=o, o2=o2, marker=marker, swapped=True, bodies=bodies))
    ep = episode(o=o, o2=o2, marker=marker, swapped=False, bodies=bodies)
    # Canonical comparison: an identity-free log is a SET of events. Comparing
    # sequences instead measures the ordering leak (see the card's results).
    same = sorted(plain) == sorted(relabel)
    # are the non-marker events still identical (i.e. did only the tags move)?
    stripped_plain = sorted(row for row in plain if row[0] != "marker")
    stripped_relabel = sorted(row for row in relabel if row[0] != "marker")
    return {"label": label, "identical": same, "sequence_identical": plain == relabel,
            "non_marker_identical": stripped_plain == stripped_relabel,
            "markers": len(markers(ep))}


def main() -> int:
    open_world = {"o": (40.0, 60.0, 35.0, 65.0), "o2": (46.0, 54.0, 35.0, 65.0)}
    hidden_world = {"o": (5.0, 95.0, 5.0, 95.0), "o2": (5.0, 95.0, 5.0, 95.0)}
    exposed = {"o": (5.0, 95.0, 5.0, 95.0), "o2": (46.0, 54.0, 5.0, 95.0)}

    rows = [
        case("1 no marker, visible", o=open_world["o"], o2=open_world["o2"], marker=False),
        case("2 marker, visible", o=open_world["o"], o2=open_world["o2"], marker=True),
        case("3 marker, paths hidden", o=hidden_world["o"], o2=hidden_world["o2"],
             marker=True, bodies=STILL),
        case("4 marker, second vantage", o=exposed["o"], o2=exposed["o2"], marker=True),
    ]
    print("| case | canonical log identical | sequence identical | non-marker identical | markers |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['label']} | {r['identical']} | {r['sequence_identical']} | "
              f"{r['non_marker_identical']} | {r['markers']} |")

    m1 = rows[0]["identical"] is True
    m2 = rows[1]["identical"] is False and rows[1]["non_marker_identical"] is True
    m3 = rows[2]["markers"] == 0 and rows[2]["identical"] is True
    m4 = rows[3]["markers"] > 0 and rows[3]["identical"] is False

    print()
    print(f"M1 a relabelling is invisible without identity evidence: "
          f"{'UPHELD' if m1 else 'FALSIFIED'}")
    print(f"M2 a visible marker resolves it (and only the tags move): "
          f"{'UPHELD' if m2 else 'FALSIFIED'}")
    print(f"M3 occluded markers leave identity ambiguous: {'UPHELD' if m3 else 'FALSIFIED'}")
    print(f"M4 a second vantage restores it: {'UPHELD' if m4 else 'FALSIFIED'}")
    ok = all((m1, m2, m3, m4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
