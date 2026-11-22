"""R-P1.18 — is identifiability frame-covariant?

Prereg: docs/2026-11-22-PREREG-R-P1.18-frame-covariance.md, registered before
this script existed.

Whole-scene symmetries (bodies, both occluders, velocities, kick) must leave the
tie/unique outcome untouched, the blind region must map exactly, and the
decision margins must be numerically equal. The control transforms the BODIES
ONLY — the comparison A4 implicitly made — and must be sensitive, or covariance
is untested.

Usage: .venv/bin/python scripts/frame-covariance-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.perspective import (
    SYMMETRIES, scene_rect, transform_scene,
)
from psychopomp.sim import Init, Kick, SimConfig, inside_rect, occluder2_at, run

T, DV, STEPS, DT, V = 60, (0.0, 1.5), 200, 0.1, 3.0
LANE = 45.0
O2_BASE = (40.5, 60.5, 35.0, 65.0)
EVENTS = [("E37", 19.0), ("E44", 26.0), ("E55", 37.0)]
DRIFTS = [("static", (0.0, 0.0)), ("right", (1.667, 0.0))]


def base_config(drift) -> SimConfig:
    return SimConfig(steps=STEPS, o2=O2_BASE, o2_velocity=drift)


def base_init(x0: float) -> Init:
    return Init(x=(x0, x0 - 4.0), y=(LANE, LANE), v=((V, 0.0), (V, 0.0)))


def blind_at(cfg: SimConfig, t: int):
    second = occluder2_at(cfg, t)
    if second is None:
        return cfg.o
    x0, x1 = max(cfg.o[0], second[0]), min(cfg.o[1], second[1])
    y0, y1 = max(cfg.o[2], second[2]), min(cfg.o[3], second[3])
    return None if x0 >= x1 or y0 >= y1 else (x0, x1, y0, y1)


def area(rect) -> float:
    return 0.0 if rect is None else (rect[1] - rect[0]) * (rect[3] - rect[2])


def measure(cfg: SimConfig, init: Init, kick: Kick) -> dict:
    true = Intervention(t=kick.t, ball=kick.ball, dv=kick.dv)
    ep = run(cfg, 0, episode=0, init=init, kicks=(kick,))
    out = attribute(ep, [true, None], cfg, 0, init)
    scores = {str(h): d for d, h in out["scores"]}
    return {
        "unique": bool(out["unique"] and out["best"] is true),
        "d_true": scores[str(true)],
        "d_null": scores[str(None)],
    }


def main() -> int:
    rows = []
    print("| drift | event | symmetry | blind | unique | d(true) | d(null) |")
    print("|---|---|---|---|---|---|---|")
    for drift_label, drift in DRIFTS:
        for event_label, x0 in EVENTS:
            cfg0, init0, kick0 = base_config(drift), base_init(x0), Kick(T, 0, DV)
            base_blind = blind_at(cfg0, T)
            for sym in SYMMETRIES:
                cfg, init, kick = transform_scene(cfg0, init0, kick0, sym)
                m = measure(cfg, init, kick)
                blind = blind_at(cfg, T)
                rows.append({
                    "drift": drift_label, "event": event_label, "sym": sym,
                    "unique": m["unique"], "d_true": m["d_true"],
                    "d_null": m["d_null"], "blind": blind,
                    "blind_image_ok": (blind is None and scene_rect(sym, base_blind) is None)
                    or (blind is not None and base_blind is not None
                        and all(abs(a - b) < 1e-9
                                for a, b in zip(blind, scene_rect(sym, base_blind)))),
                    "area_ok": abs(area(blind) - area(base_blind)) < 1e-9,
                })
                print(f"| {drift_label} | {event_label} | {sym} | {blind} | "
                      f"{'unique' if m['unique'] else 'tie'} | {m['d_true']:.2f} | "
                      f"{m['d_null']:.2f} |")

    # P1: outcome identical across symmetries within each (drift, event) cell
    p1 = True
    for drift_label, _ in DRIFTS:
        for event_label, _ in EVENTS:
            cell = [r for r in rows if r["drift"] == drift_label and r["event"] == event_label]
            p1 &= len({r["unique"] for r in cell}) == 1

    # P2: blind region maps exactly, area preserved
    p2 = all(r["blind_image_ok"] and r["area_ok"] for r in rows)

    # P3: CONTROL — bodies transformed, occluders held fixed
    control = []
    unbuildable = 0
    for drift_label, drift in DRIFTS:
        for event_label, x0 in EVENTS:
            cfg0, init0, kick0 = base_config(drift), base_init(x0), Kick(T, 0, DV)
            baseline = measure(cfg0, init0, kick0)
            for sym in SYMMETRIES[1:]:
                _, init, kick = transform_scene(cfg0, init0, kick0, sym)
                try:
                    m = measure(cfg0, init, kick)      # occluders NOT transformed
                except AssertionError:
                    unbuildable += 1
                    continue
                control.append({"sym": sym, "drift": drift_label, "event": event_label,
                                "baseline": baseline["unique"], "control": m["unique"]})
    flips = [c for c in control if c["baseline"] != c["control"]]
    p3 = len(flips) > 0

    # P4: margins numerically covariant
    p4 = all(r["d_true"] == 0.0 for r in rows) and len({
        round(r["d_null"], 6) for r in rows
        if r["drift"] == DRIFTS[0][0] and r["event"] == "E44"
    }) == 1

    print()
    print(f"control (bodies only): {len(control)} buildable cells, {unbuildable} unbuildable "
          f"(body lands inside an occluder), {len(flips)} identifiability flips")
    for c in flips[:4]:
        print(f"  flip: {c['sym']} {c['drift']} {c['event']} "
              f"{'unique' if c['baseline'] else 'tie'} -> {'unique' if c['control'] else 'tie'}")
    print()
    print(f"P1 outcome invariant under whole-scene symmetry: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 blind region maps exactly, area preserved: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 bodies-only control is sensitive: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 decision margins covariant (d(true)=0, d(null) equal): "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
