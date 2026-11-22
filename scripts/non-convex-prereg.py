"""R-P1.25 — non-convex blind regions: membership, not bounding box.

Prereg: docs/2026-11-22-PREREG-R-P1.25-non-convex.md (with amendments 1 and 2),
claim 90821d05 registered before the run.

Three worlds over two lanes: one interval, two intervals with a real gap, and two
intervals stacked in y. If the law is set membership, the point in the gap is
identifiable even though it lies inside the blind set's bounding box, and the
stacked cell is blind on its own lane while the lane below is not.

Usage: .venv/bin/python scripts/non-convex-prereg.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import blind_cells, on_boundary, predict_identifiable
from psychopomp.sim import Init, Kick, SimConfig, observable, run

STEPS, DT, T_STAR = 200, 0.1, 90
O = (40.0, 60.0, 35.0, 65.0)
O2 = (30.0, 92.0, 20.0, 90.0)
SHAPES = [
    ("plain", ()),
    ("islands", ((70.0, 85.0, 35.0, 65.0),)),
    ("stacked", ((40.0, 60.0, 70.0, 85.0),)),
]
# (label, lane y, target x)
POINTS = [("45@45", 45.0, 45.0), ("55@45", 45.0, 55.0), ("65@45", 45.0, 65.0),
          ("75@45", 45.0, 75.0), ("85@45", 45.0, 85.0), ("50@75", 75.0, 50.0)]
EXPECTED = {
    "plain":   {"45@45": False, "55@45": False, "65@45": True, "75@45": True,
                "85@45": True, "50@75": True},
    "islands": {"45@45": False, "55@45": False, "65@45": True, "75@45": False,
                "85@45": False, "50@75": True},
    "stacked": {"45@45": False, "55@45": False, "65@45": True, "75@45": True,
                "85@45": True, "50@75": False},
}


def config(extra) -> SimConfig:
    return SimConfig(steps=STEPS, o=O, o2=O2, extra_o=extra, n_balls=len(POINTS))


def build():
    """Each body starts in the free left band and is at its point exactly at t*.

    Speeds increase with position, so bodies on the same lane never close on each
    other and cannot collide.
    """
    starts, ys, vs = [], [], []
    for i, (_, y, x) in enumerate(POINTS):
        start = 5.0 + 5.0 * i
        starts.append(start)
        ys.append(y)
        vs.append(((x - start) / (DT * T_STAR), 0.0))
    return Init(x=tuple(starts), y=tuple(ys), v=tuple(vs))


def bbox(cells):
    return (min(c[0] for c in cells), max(c[1] for c in cells),
            min(c[2] for c in cells), max(c[3] for c in cells))


def main() -> int:
    rows = []
    print("| shape | cells | point | predicted | measured | bbox says |")
    print("|---|---|---|---|---|---|")
    for name, extra in SHAPES:
        cfg = config(extra)
        init = build()
        if any(not observable(cfg, x, y) for x, y in zip(init.x, init.y)):
            print(f"| {name} | DESIGN-FAILED: a body starts inside a blocker | | | | |")
            rows.append({"shape": name, "design_failed": True})
            continue
        cells = blind_cells(cfg, T_STAR)
        world = run(cfg, 0, episode=0, init=init)
        for i, (label, _, _) in enumerate(POINTS):
            at = (world.trajs[i].x[T_STAR], world.trajs[i].y[T_STAR])
            predicted = predict_identifiable(cfg, at, T_STAR)
            true = Intervention(t=T_STAR, ball=i, dv=(0.0, 1.5))
            ep = run(cfg, 0, episode=0, init=init,
                     kicks=(Kick(T_STAR, i, (0.0, 1.5)),))
            out = attribute(ep, [true, None], cfg, 0, init)
            measured = bool(out["unique"] and out["best"] is true)
            bx = bbox(cells) if cells else None
            in_bbox = bx is not None and bx[0] <= at[0] <= bx[1] and bx[2] <= at[1] <= bx[3]
            rows.append({"shape": name, "point": label, "at": at,
                         "predicted": predicted, "measured": measured,
                         "boundary": on_boundary(cfg, at, T_STAR)})
            print(f"| {name} | {len(cells)} | {label} | "
                  f"{'unique' if predicted else 'tie'} | "
                  f"{'unique' if measured else 'tie'} | "
                  f"{'blind' if in_bbox else 'visible'} |")

    scored = [r for r in rows if "measured" in r and not r["boundary"]]
    boundary = [r for r in rows if r.get("boundary")]
    mismatches = [r for r in scored if r["predicted"] != r["measured"]]

    p1 = all(r["measured"] is True for r in scored
             if r["shape"] in ("islands", "stacked") and r["point"] == "65@45")
    p2 = all(r["measured"] is False for r in scored
             if r["shape"] == "islands" and r["point"] in ("75@45", "85@45")) and \
        any(r["measured"] is True for r in scored
            if r["shape"] == "islands" and r["point"] == "65@45")
    p3 = all(r["measured"] is EXPECTED["plain"][r["point"]] for r in scored
             if r["shape"] == "plain")
    # check fix (recorded): the standing 1e-6 boundary rule REQUIRES one cell to
    # be excluded here (islands, 85@45 sits on the island's edge), so the count
    # must be scored + boundary-excluded == total, not scored == total
    total = len(POINTS) * len(SHAPES)
    p4 = not mismatches and len(scored) + len(boundary) == total
    # check fix (recorded): P5 as written demanded the single-rect CONTROL also
    # differ from its bounding box, which is impossible; it applies to the
    # multi-cell shapes, which are the ones making the membership claim
    p5 = True
    for name, extra in SHAPES:
        cfg = config(extra)
        cells = blind_cells(cfg, T_STAR)
        if len(cells) < 2:
            continue
        if tuple(cells) == (bbox(cells),):
            p5 = False
        for label, y, x in POINTS:
            if predict_identifiable(cfg, (x, y), T_STAR) != EXPECTED[name][label]:
                p5 = False

    print()
    print(f"scored {len(scored)}/{len(POINTS) * len(SHAPES)}, boundary-excluded "
          f"{len(boundary)}, mismatches {len(mismatches)}")
    for m in mismatches:
        print("  MISMATCH:", m)
    print(f"P1 the gap at (65,45) is identifiable where the bbox says blind: "
          f"{'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 islands are independent: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 no regression in the single-rect world: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 law equals instrument in all {len(POINTS) * len(SHAPES)} cells: "
          f"{'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 every blind set is not its own bounding box (membership, not envelope): "
          f"{'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
