"""R-P1.42 — bursty marker loss vs independent loss at matched drop rate.

Prereg: docs/2026-11-22-PREREG-R-P1.42-bursty-markers.md, registered before this run.

The formula 1-(1-p)^N assumes independent drops. Here a block-outage channel is
compared with an independent channel at the SAME marginal drop rate, at N = 2, 4, 6.

Usage: .venv/bin/python scripts/bursty-markers-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.sim import Init, SimConfig, run

WORLD = {"o": (40.0, 60.0, 35.0, 65.0), "o2": (46.0, 54.0, 35.0, 65.0)}
BODIES = (((20.0, 45.0), (3.0, 0.0)), ((80.0, 51.0), (-3.0, 0.0)))
CELLS = (("N2", 15), ("N4", 35), ("N6", 55))
BS = (0.2, 0.4)
REALIZATIONS = 400


def episode(steps: int, realization: int, *, outage=0.0, outage_len=2, p=1.0,
            swapped=False):
    a, b = BODIES if not swapped else (BODIES[1], BODIES[0])
    cfg = SimConfig(steps=steps, o=WORLD["o"], o2=WORLD["o2"], identity_marker=True,
                    marker_period=10, marker_reliability=p,
                    marker_outage_prob=outage, marker_outage_len=outage_len)
    return run(cfg, 0, episode=realization,
               init=Init(x=(a[0][0], b[0][0]), y=(a[0][1], b[0][1]), v=(a[1], b[1])))


def log_set(ep):
    return sorted((e.kind, e.t, tuple(sorted(e.attrs.items())))
                  for e in ep.observable_log())


def resolvable(steps: int, realization: int, **kw) -> bool:
    return log_set(episode(steps, realization, **kw)) != \
        log_set(episode(steps, realization, swapped=True, **kw))


def marker_slots(steps: int) -> int:
    """opportunities that exist if the channel were perfect (both bodies)."""
    return sum(1 for e in episode(steps, 0).observable_log() if e.kind == "marker")


def drop_rate(steps: int, outage: float, outage_len: int) -> float:
    slots = marker_slots(steps)
    kept = sum(1 for r in range(REALIZATIONS)
               for e in episode(steps, r, outage=outage, outage_len=outage_len)
               .observable_log() if e.kind == "marker") / REALIZATIONS
    return max(0.0, 1.0 - kept / slots) if slots else 0.0


def fraction(steps: int, **kw) -> float:
    return sum(1 for r in range(REALIZATIONS) if resolvable(steps, r, **kw)) / REALIZATIONS


def main() -> int:
    rows = {}
    print("| cell | b | N | mean drop rate | bursty | independent at matched p | deficit |")
    print("|---|---|---|---|---|---|---|")
    for label, steps in CELLS:
        n = marker_slots(steps)
        for b in BS:
            dr = drop_rate(steps, b, 2)
            bursty = fraction(steps, outage=b, outage_len=2)
            indep = fraction(steps, p=1.0 - dr)
            rows[(label, b)] = {"bursty": bursty, "indep": indep, "deficit": indep - bursty,
                                "N": n, "drop": dr}
            print(f"| {label} | {b:.1f} | {n} | {dr:.2f} | {bursty:.3f} | {indep:.3f} | "
                  f"{indep - bursty:+.3f} |")

    # B3: outage length covering the window — compare against "no outage begins"
    b3_cell = ("N2", 0.4)
    steps = dict(CELLS)[b3_cell[0]]
    bursty_long = fraction(steps, outage=b3_cell[1], outage_len=3)
    starts_free = (1.0 - b3_cell[1]) ** 2      # two opportunities in the window
    b3_ok = abs(bursty_long - starts_free) <= 0.10

    b1 = sum(1 for v in rows.values() if v["deficit"] > 0.02) >= 4
    b2 = rows[("N6", 0.4)]["deficit"] < rows[("N2", 0.4)]["deficit"]
    print()
    print(f"B1 correlation hurts at matched drop rate (>=4 of 6 cells): "
          f"{'UPHELD' if b1 else 'FALSIFIED'} "
          f"({sum(1 for v in rows.values() if v['deficit'] > 0.02)} cells)")
    print(f"B2 the deficit shrinks with N at b=0.4: {'UPHELD' if b2 else 'FALSIFIED'} "
          f"(N2 {rows[('N2', 0.4)]['deficit']:+.3f} -> N6 {rows[('N6', 0.4)]['deficit']:+.3f})")
    print(f"B3 a burst covering the window collapses the N chances: "
          f"{'UPHELD' if b3_ok else 'FALSIFIED'} "
          f"(bursty {bursty_long:.3f} vs no-outage {starts_free:.3f})")
    ok = all((b1, b2, b3_ok))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
