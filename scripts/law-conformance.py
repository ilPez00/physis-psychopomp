"""Law conformance — the consolidated predicate against attribution, in bulk.

The cards tested hand-picked cells. This gate samples random geometries and
checks `psychopomp.law.predict_identifiable` against counterfactual attribution
on every one, so a regression in either cannot hide behind a curated grid.

Families:
  A  straight-line bodies: the task point is placed inside `o`, the body starts
     where it must to be there at the event step;
  B  with or without acceleration: the point is wherever the body actually is at
     the event step (the card methodology, generalised).

Cells on a blind boundary are excluded under the declared 1e-6 rule and counted.

Usage: .venv/bin/python scripts/law-conformance.py [--cells N] [--seed S]
Exit 1 on any mismatch off-boundary.
"""
from __future__ import annotations

import argparse
import random
import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_region, on_boundary, predict_identifiable
from psychopomp.sim import Init, Kick, SimConfig, observable, run

DT, V, DV = 0.1, 3.0, (0.0, 1.5)
W = H = 100.0


def random_rect(rng: random.Random):
    x0 = rng.uniform(20.0, 60.0)
    y0 = rng.uniform(20.0, 60.0)
    return (round(x0, 2), round(x0 + rng.uniform(4.0, 20.0), 2),
            round(y0, 2), round(y0 + rng.uniform(4.0, 20.0), 2))


def safe_partner(cfg: SimConfig, rng: random.Random):
    for _ in range(30):
        p = (rng.uniform(5.0, 95.0), rng.uniform(5.0, 95.0))
        if observable(cfg, p[0], p[1]):
            return p
    return None


def make_cell(family: str, rng: random.Random, want_covered: bool):
    """Stratified: half the cells place the event inside the blind region.

    Sampling points uniformly inside `o` gives almost no covered cells (random
    `o2` rarely overlaps), so an unstratified gate would be one-sided and
    prove only that visible events are identified.
    """
    for _ in range(200):
        o = random_rect(rng)
        o2 = random_rect(rng)
        drift = rng.choice((-2.0, -1.0, 0.0, 1.0, 2.0))
        accel = (0.0, 0.0) if family == "A" else rng.choice(((0.0, 0.0), (0.0, -0.5)))
        try:
            cfg = SimConfig(steps=200, o=o, o2=o2, o2_velocity=(drift, 0.0),
                            accel=accel, n_balls=2)
        except AssertionError:
            continue
        t = rng.randrange(20, 181)
        partner = safe_partner(cfg, rng)
        if partner is None:
            continue
        if family == "A":
            blind = blind_region(cfg, t)
            if want_covered:
                # a drifted-away occluder leaves no blind region: retry, never
                # silently degrade the request to an uncovered cell
                if blind is None or blind[1] - blind[0] <= 0.4 or blind[3] - blind[2] <= 0.4:
                    continue
                px = rng.uniform(blind[0] + 0.2, blind[1] - 0.2)
                py = rng.uniform(blind[2] + 0.2, blind[3] - 0.2)
            else:
                px = rng.uniform(o[0] + 1.0, o[1] - 1.0)
                py = rng.uniform(o[2] + 1.0, o[3] - 1.0)
                if not predict_identifiable(cfg, (px, py), t):
                    continue        # keep the uncovered class clean
            start = (px - V * DT * t, py)
            if not (1.0 <= start[0] <= 99.0 and 1.0 <= start[1] <= 99.0):
                continue
            init = Init(x=(start[0], partner[0]), y=(start[1], partner[1]),
                        v=((V, 0.0), (0.0, 0.0)))
            if not observable(cfg, start[0], start[1]):
                continue
            # capacity check (the R-P1.20 lesson, learned the hard way again):
            # a collision with the random partner can deflect the body, so the
            # point must be where the body ACTUALLY is at t, not where the
            # analytic placement intended it to be
            world = run(cfg, 0, episode=0, init=Init(
                x=(start[0], partner[0]), y=(start[1], partner[1]),
                v=((V, 0.0), (0.0, 0.0))))
            actual = (world.trajs[0].x[t], world.trajs[0].y[t])
            if abs(actual[0] - px) > 1e-6 or abs(actual[1] - py) > 1e-6:
                continue
            point = actual
        else:
            start = (rng.uniform(2.0, 60.0), rng.uniform(2.0, 98.0))
            if not observable(cfg, start[0], start[1]):
                continue
            init = Init(x=(start[0], partner[0]), y=(start[1], partner[1]),
                        v=((V, 0.0) if rng.random() < 0.5 else (-V, 0.0), (0.0, 0.0)))
            world = run(cfg, 0, episode=0, init=init)
            point = (world.trajs[0].x[t], world.trajs[0].y[t])
            # rejection sample the required coverage class (acceleration and
            # velocity make the position analytic only in the loop above)
            blind = blind_region(cfg, t)
            inside_blind = blind is not None and not predict_identifiable(cfg, point, t)
            if want_covered != inside_blind:
                continue
        return cfg, init, t, point
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261122)
    ap.add_argument("--min-minority", type=int, default=25,
                    help="fail if either outcome class has fewer cells than this")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    stats = {"scored": 0, "boundary": 0, "skipped": 0,
             "identifiable": 0, "not_identifiable": 0, "mismatch": 0}
    mismatches = []
    for i in range(args.cells):
        family = "A" if i % 2 == 0 else "B"
        # stratify INSIDE each family, not across the interleaved index
        made = make_cell(family, rng, want_covered=((i // 2) % 2 == 1))
        if made is None:
            stats["skipped"] += 1
            continue
        cfg, init, t, point = made
        if on_boundary(cfg, point, t):
            stats["boundary"] += 1
            continue
        predicted = predict_identifiable(cfg, point, t)
        true = Intervention(t=t, ball=0, dv=DV)
        ep = run(cfg, 0, episode=0, init=init, kicks=(Kick(t, 0, DV),))
        out = attribute(ep, [true, None], cfg, 0, init)
        measured = bool(out["unique"] and out["best"] is true)
        stats["scored"] += 1
        stats["identifiable" if measured else "not_identifiable"] += 1
        if predicted != measured:
            stats["mismatch"] += 1
            mismatches.append({
                "family": family, "t": t, "point": point, "predicted": predicted,
                "measured": measured, "blind": blind_region(cfg, t),
                "o": cfg.o, "o2": cfg.o2, "drift": cfg.o2_velocity,
                "accel": cfg.accel,
            })

    print(f"cells requested {args.cells}; scored {stats['scored']}, "
          f"boundary-excluded {stats['boundary']}, unresolvable {stats['skipped']}")
    print(f"outcomes: identifiable {stats['identifiable']}, "
          f"not identifiable {stats['not_identifiable']}")
    print(f"mismatches off-boundary: {stats['mismatch']}")
    for m in mismatches[:5]:
        print("  MISMATCH:", m)
    balanced = min(stats["identifiable"], stats["not_identifiable"]) >= args.min_minority
    if not balanced:
        print(f"  ONE-SIDED: minority class has "
              f"{min(stats['identifiable'], stats['not_identifiable'])} < {args.min_minority} cells")
    ok = stats["mismatch"] == 0 and stats["scored"] >= args.cells // 2 and balanced
    print("law conformance:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
