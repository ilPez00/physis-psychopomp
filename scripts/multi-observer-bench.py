"""R-P1.9 — multi-observer occlusion: is a blind spot a property of the world
or of the observer set?

Four observer sets over the same world and the same two episodes:

  single   — one observer, occluder o                      (R-P1.8 instrument)
  same     — second observer with the SAME occluder         (control: blind = o)
  overlap  — second observer with a partly overlapping one  (blind = o ∩ o2)
  disjoint — second observer with a disjoint occluder       (blind = ∅)

Episode A: the true kick happens while the body is VISIBLE (t=30).
Episode B: the true kick happens while the body is inside o (t=60).

For B the identifiability question is exact: does the re-simulation of the true
kick differ from the no-kick world at all? If it does not, no observer can tell
them apart — the truth ties with the null (`null_tie`). That is the limit
R-P1.8 measured; this card asks whether a second observer removes it.

P5 check: with no interventions, single and disjoint produce identical
observable logs (visibility unchanged where it was already visible).

Usage: .venv/bin/python scripts/multi-observer-bench.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

VISIBLE_KICK = Intervention(t=30, ball=0, dv=(0.0, 1.5))   # body 0 visible at t=30
HIDDEN_KICK = Intervention(t=60, ball=0, dv=(0.0, 1.5))    # body 0 inside o at t=60
INIT = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
STEPS = 200

CELLS = [
    ("single", None),
    ("same", (40.0, 60.0, 35.0, 65.0)),
    ("overlap", (50.0, 70.0, 35.0, 65.0)),
    ("disjoint", (0.0, 20.0, 0.0, 20.0)),
]


def blind_rect(o, o2):
    if o2 is None:
        return o
    x0, x1 = max(o[0], o2[0]), min(o[1], o2[1])
    y0, y1 = max(o[2], o2[2]), min(o[3], o2[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def episode_row(cfg, true: Intervention, decoy: Intervention, label: str) -> dict:
    ep = run(cfg, 0, init=INIT, kicks=(Kick(true.t, true.ball, true.dv),))
    out = attribute(ep, [true, None, decoy], cfg, 0, INIT)
    scores = {id(h): d for d, h in out["scores"]}
    d_true = scores[id(true)]
    d_null = scores[id(None)]
    null_tie = abs(d_true - d_null) <= 1e-12
    print(f"  [{label}] truth {'UNIQUE' if out['unique'] else 'ambiguous'} "
          f"best={'TRUE' if out['best'] == true else out['best']} "
          f"ambiguity={len(out['ambiguity'])} margin={out['margin']:.2f} "
          f"d(true)={d_true:.2f} d(null)={d_null:.2f} null_tie={null_tie}")
    return {
        "label": label,
        "unique": out["unique"],
        "best_is_true": out["best"] == true,
        "ambiguity": len(out["ambiguity"]),
        "margin": out["margin"],
        "d_true": d_true,
        "d_null": d_null,
        "null_tie": null_tie,
    }


def cell(label: str, o2) -> dict:
    cfg = SimConfig(steps=STEPS, o2=o2)
    blind = blind_rect(cfg.o, o2)
    total = sum(len(t.visible) for t in run(cfg, 0, init=INIT).trajs)
    hidden = sum(
        sum(1 for v in t.visible if not v) for t in run(cfg, 0, init=INIT).trajs
    )
    hidden_events = sum(1 for e in run(cfg, 0, init=INIT).oracle_log() if not e.observable)
    print(f"[{label}] blind {blind} hidden step fraction {hidden / total:.3f} "
          f"hidden in-blind events {hidden_events}")
    vis = episode_row(cfg, VISIBLE_KICK, HIDDEN_KICK, "kick while visible")
    hid = episode_row(cfg, HIDDEN_KICK, VISIBLE_KICK, "kick while hidden")
    return {
        "label": label,
        "blind": blind,
        "hidden_step_fraction": round(hidden / total, 3),
        "hidden_events": hidden_events,
        "visible_kick": vis,
        "hidden_kick": hid,
    }


def no_side_effect_invariance() -> bool:
    """Observation must not change physics, and must only ever reveal more.

    The second observer does change *which* events are reported (that is the
    point), so the honest invariants are: identical trajectories, and every
    event the disjoint observer reports is also reported by the single one
    with identical content (it can only un-hide, never invent).
    """
    a = run(SimConfig(steps=STEPS), 0, init=INIT)
    b = run(SimConfig(steps=STEPS, o2=(0.0, 20.0, 0.0, 20.0)), 0, init=INIT)
    same_physics = all(
        ta.x == tb.x and ta.y == tb.y and ta.vx == tb.vx and ta.vy == tb.vy
        for ta, tb in zip(a.trajs, b.trajs)
    )
    ea = [(e.kind, e.t, e.subjects, e.attrs) for e in a.observable_log()]
    eb = [(e.kind, e.t, e.subjects, e.attrs) for e in b.observable_log()]
    subset = all(e in ea for e in eb)
    print(f"P5 physics identical under a second observer: {same_physics}; "
          f"disjoint events are a subset of single ({len(eb)} ⊆ {len(ea)}): {subset}")
    return same_physics and subset


def main() -> int:
    print("R-P1.9 multi-observer occlusion — same world, four observer sets")
    rows = {label: cell(label, o2) for label, o2 in CELLS}
    single, same, overlap, dis = (rows[k] for k in ("single", "same", "overlap", "disjoint"))

    p1 = (single["hidden_kick"]["null_tie"] and not single["hidden_kick"]["unique"]
          and single["visible_kick"]["unique"] and single["visible_kick"]["best_is_true"])
    p2 = all(rows[c]["hidden_kick"]["unique"] and rows[c]["hidden_kick"]["best_is_true"]
             and not rows[c]["hidden_kick"]["null_tie"] for c in ("overlap", "disjoint"))
    p3 = all(same[k]["null_tie"] == single[k]["null_tie"]
             and same[k]["unique"] == single[k]["unique"]
             and same[k]["d_true"] == single[k]["d_true"]
             for k in ("visible_kick", "hidden_kick"))
    order = [rows[c]["hidden_step_fraction"] for c in ("single", "same", "overlap", "disjoint")]
    p4 = order[0] == order[1] > order[2] > order[3] and order[3] == 0.0
    p5 = no_side_effect_invariance()

    print()
    print(f"P1 single observer: hidden kick ties with the null (limit reproduced): "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 second observer with a different blind spot makes it identifiable: "
          f"{'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 same blind spot changes nothing (control): {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 hidden step fraction falls with blind coverage {order}: "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 observation changes nothing physical and only ever reveals: "
          f"{'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("bench:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
