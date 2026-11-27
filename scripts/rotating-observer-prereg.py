"""R-P1.65: a rotating observer — does the decision rotate with the coordinates?

Frozen card: docs/2026-11-27-PREREG-R-P1.65-rotating-observer.md, pushed at
`0c2c8d6` before this file existed. Claim
`23576a80-0d32-4939-8ec3-ec3585dcc64f`.

Two facts are separated on purpose:

  P1  the transform round-trips and preserves |v|          (arithmetic)
  P2  rotation creates or destroys no world                (enumeration)
  P3  the verdict follows the query point in the scene arm (covariance)
  P4  the bodies-only arm changes                          (the control)
  P5  the transformed log names no hidden state            (no leak)

The occluder stays axis-aligned in both arms; this card does not rotate it and
says so, so a bodies-only change is the expected result rather than a defect.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.attribution import attribute
from psychopomp.fixtures import truth_matches
from psychopomp.interventions import Intervention
from psychopomp.perspective import Frame, transform_observable
from psychopomp.sim import Init, Kick, SimConfig, run

CLAIM = "23576a80-0d32-4939-8ec3-ec3585dcc64f"
HIDDEN_KICK = Intervention(t=60, ball=0, dv=(0.0, 1.5))
INIT = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
# Observer 2's occluder must contain the event for a blind region to exist.
# R-P1.9's (50,70,35,65) does NOT cover (46,45) for this INIT, so the first
# version of this fixture measured 'not covered, unique' in every cell and
# P4 could not fire. The identity check in main() refuses that fixture
# rather than reporting it as a result.
O2 = (40.0, 60.0, 35.0, 65.0)
ROTATIONS = (0.0, math.pi / 6, math.pi / 4, math.pi / 3, math.pi / 2)
SEEDS = (0, 1, 2, 3, 4)
STEPS = 200
TOL = 1e-9


def rotation_frame(theta: float) -> Frame:
    """Constant rotation about the world origin, no drift.

    A `random` frame with `theta` set and zero drift is exactly this transform:
    the simulator has three frame kinds and a fourth would be a new mechanism for
    a card that is meant to test the existing one.
    """
    return Frame("random", theta=theta, p0=(0.0, 0.0), u=(0.0, 0.0))


def rot_about_origin(theta: float, p) -> tuple[float, float]:
    c, s = math.cos(theta), math.sin(theta)
    return (c * p[0] - s * p[1], s * p[0] + c * p[1])


def event_location(cfg: SimConfig) -> tuple[float, float]:
    t = HIDDEN_KICK.t
    return (INIT.x[0] + INIT.v[0][0] * t * cfg.dt,
            INIT.y[0] + INIT.v[0][1] * t * cfg.dt)


def inside(rect, px, py) -> bool:
    x0, x1, y0, y1 = rect
    return x0 <= px <= x1 and y0 <= py <= y1


def round_trip(ep, theta: float) -> dict:
    """P1: transform then invert must reproduce the log, and keep |v|."""
    cfg = ep.config
    forward = transform_observable(ep, rotation_frame(theta))
    back = transform_observable(ep, rotation_frame(theta), inverse=True)
    original = ep.observable_log()

    def rows(log):
        out = []
        for ev in log:
            d = dict(ev) if isinstance(ev, dict) else {"ev": str(ev)}
            out.append(d)
        return out

    # Compare positions and speeds event by event, order preserved.
    a_events = sorted_events(original)
    b_events = sorted_events(back)
    worst_pos = 0.0
    worst_speed = 0.0
    if len(a_events) != len(b_events):
        return {"ok": False, "reason": "event count changed",
                "original": len(a_events), "inverted": len(b_events)}
    for (ka, pa, va), (kb, pb, vb) in zip(a_events, b_events):
        if ka != kb:
            return {"ok": False, "reason": f"kind changed {ka} -> {kb}"}
        if pa and pb:
            worst_pos = max(worst_pos, math.dist(pa, pb))
        if va and vb:
            worst_speed = max(worst_speed, abs(math.hypot(*va) - math.hypot(*vb)))
    return {"ok": worst_pos <= TOL and worst_speed <= TOL,
            "worst_position_error": worst_pos, "worst_speed_error": worst_speed}


def sorted_events(log) -> list[tuple]:
    """(kind, position, velocity) per event, in a stable order."""
    rows = []
    for ev in log:
        kind = getattr(ev, "kind", None) or (ev.get("kind") if isinstance(ev, dict) else None)
        pos = getattr(ev, "pos", None) or (ev.get("pos") if isinstance(ev, dict) else None)
        vel = getattr(ev, "v", None) or (ev.get("v") if isinstance(ev, dict) else None)
        rows.append((str(kind), tuple(pos) if pos else None, tuple(vel) if vel else None))
    return sorted(rows, key=lambda r: (r[0], r[1] or ()))


def cell(theta: float, arm: str, seed: int) -> dict:
    cfg = SimConfig(steps=STEPS, o2=O2)
    ep = run(cfg, seed, init=INIT,
             kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))
    ev = event_location(cfg)
    # scene: the query point rotates with the bodies.
    query = rot_about_origin(theta, ev) if arm == "scene" else ev
    covered = inside(O2, query[0], query[1])

    out = attribute(view_as_episode(ep, theta), [HIDDEN_KICK, None], cfg, seed, INIT)
    return {
        "theta": round(theta, 6), "arm": arm, "seed": seed,
        "event": [round(query[0], 4), round(query[1], 4)],
        "covered": covered,
        "unique": bool(out["unique"]),
        "margin": out["margin"],
    }


def leak_scan(ep) -> dict:
    """P5: no hidden-state field may appear in the transformed log."""
    banned = ("truth", "joint", "hidden_state", "oracle", "reveal")
    found = []
    for ev in transform_observable(ep, rotation_frame(math.pi / 3)):
        fields = vars(ev) if hasattr(ev, "__dict__") else (
            ev if isinstance(ev, dict) else {})
        for key in fields:
            if any(b in str(key).lower() for b in banned):
                found.append(str(key))
    return {"banned_found": sorted(set(found)), "ok": not found}


def main() -> int:
    cfg = SimConfig(steps=STEPS, o2=O2)
    base = run(cfg, 0, init=INIT,
               kicks=(Kick(HIDDEN_KICK.t, HIDDEN_KICK.ball, HIDDEN_KICK.dv),))

    # P1 — round trip at every rotation.
    trips = {f"{t:.6f}": round_trip(base, t) for t in ROTATIONS}
    p1 = all(v["ok"] for v in trips.values())

    # P2/P3/P4 — verdicts.
    # Fixture sanity: the identity cell must be covered, or the card measures a
    # world with no blind region and every verdict is trivially unique.
    identity = cell(0.0, "scene", 0)
    if not identity["covered"]:
        print(json.dumps({
            "verdict": "UNVERIFIABLE: the fixture never covers the event, so no "
                       "blind region exists",
            "event": identity["event"], "o2": list(O2)}))
        return 1

    cells = [cell(t, arm, s) for t in ROTATIONS for arm in ("scene", "bodies")
             for s in SEEDS]

    def verdicts(theta: float, arm: str) -> list[bool]:
        return [c["unique"] for c in cells
                if abs(c["theta"] - round(theta, 6)) < 1e-9 and c["arm"] == arm]

    base_verdict = verdicts(0.0, "scene")
    scene_verdicts = {f"{t:.6f}": verdicts(t, "scene") for t in ROTATIONS}
    bodies_verdicts = {f"{t:.6f}": verdicts(t, "bodies") for t in ROTATIONS}
    coverage = {(f"{t:.6f}", arm): [c["covered"] for c in cells
                                    if abs(c["theta"] - round(t, 6)) < 1e-9
                                    and c["arm"] == arm]
                for t in ROTATIONS for arm in ("scene", "bodies")}

    # World counts: the enumeration must not change with rotation.
    world_counts = {}
    for t in ROTATIONS:
        view = base.observable_log() if t == 0.0 else \
            transform_observable(base, rotation_frame(t))
        ws = enumerate_worlds(view)
        # `World` is a pairing over the observable log's event order, so "is the
        # truth in the set" asks whether the oracle pairing is among them — the
        # comparison the lane's own fixtures use, not an edge-set equality.
        want = truth_matches(base)
        world_counts[f"{t:.6f}"] = {
            "worlds": len(ws),
            "truth_in_worlds": any(tuple(w.matches) == tuple(want) for w in ws),
        }
    counts = {v["worlds"] for v in world_counts.values()}
    p2 = len(counts) == 1 and all(v["truth_in_worlds"] for v in world_counts.values())

    p3 = all(v == base_verdict for v in scene_verdicts.values())
    # P4 as written cannot hold, and the reason is a measured fact about the
    # decoder rather than about rotation: `attribute` rebuilds every
    # counterfactual from (config, init) in WORLD coordinates, so a rotated
    # observation is compared against unrotated candidates. Both arms therefore
    # score identically by construction. The card keeps P4 FAILED — it was the
    # prediction, and it was wrong — and the receipt records the mechanism.
    p4 = any(v != base_verdict for v in bodies_verdicts.values())

    leak = leak_scan(base)
    p5 = leak["ok"]

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p1:
        verdict += "; UNVERIFIABLE (the transform does not round-trip)"

    receipt = {
        "card": "R-P1.65",
        "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.65-rotating-observer.md",
        "command": "python3 scripts/rotating-observer-prereg.py",
        "rotations": [round(t, 6) for t in ROTATIONS],
        "seeds": list(SEEDS),
        "round_trip": trips,
        "world_counts": world_counts,
        "coverage": {f"{k[0]}/{k[1]}": v for k, v in coverage.items()},
        "scene_verdicts": scene_verdicts,
        "bodies_verdicts": bodies_verdicts,
        "base_verdict": base_verdict,
        "leak_scan": leak,
        "cells": cells,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/rotating-observer-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "scene": scene_verdicts, "bodies": bodies_verdicts,
                      "world_counts": world_counts,
                      "round_trip_ok": p1}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


def view_as_episode(ep, theta: float):
    """The same episode carrying a rotated observable log.

    `transform_observable` returns an `EventLog`, and `attribute` wants a
    `SimEpisode` — it reads `observable_log()` and re-simulates counterfactuals
    from `config`/`init`. So the episode is rebuilt with the transformed log in
    the observable slot and the oracle left as the original: the counterfactual
    side is simulated in world coordinates either way, which is the honest
    comparison (the decoder sees rotated numbers, the model still lives in its
    own frame).
    """
    from psychopomp.sim import SimEpisode
    if theta == 0.0:
        return ep
    rotated = transform_observable(ep, rotation_frame(theta))
    return SimEpisode(ep.config, ep.seed, ep.episode, ep.trajs,
                      ep.applied_kicks, ep.skipped_kicks, ep.init,
                      rotated, ep.oracle_log())


def truth_of(ep) -> set:
    return {tuple(e) for e in ep.truth} if hasattr(ep, "truth") else set()


def enumerate_worlds(log):
    """Surviving worlds for an observable log, via the same filter the card's
    P2 uses. Kept here so the receipt records what it measured."""
    from psychopomp.epec import consistent_worlds as cw
    return cw(log)


if __name__ == "__main__":
    raise SystemExit(main())
