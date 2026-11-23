"""Replay the frozen R-P1.46 two-producer delivery masks."""
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.eventlog import EventLog
from psychopomp.sim import Init, SimConfig, run

MASKS = ((0, 0), (1, 0), (0, 1), (1, 1))
ARMS = {
    "shared": (MASKS[0], MASKS[3]),
    "independent": MASKS,
    "complementary": (MASKS[1], MASKS[2]),
}


def world(xs):
    cfg = SimConfig(steps=1, o=(10, 30, 40, 60), o2=None, allow_hidden_init=True,
                    identity_marker=True, marker_period=2)
    return run(cfg, 0, init=Init(x=xs, y=(50, 50), v=((0, 0), (0, 0)))).observable_log()


def delivered(log, mask, anonymous=False):
    out = EventLog([e for e in log if e.kind != "marker"])
    for e in log.filter(("marker",)):
        attrs = {**e.attrs, "tag": "anonymous"} if anonymous else e.attrs
        for source, active in zip(("producer:A", "producer:B"), mask):
            if active:
                out.add(replace(e, attrs=attrs, provenance=replace(e.provenance, source=source)))
    return list(out)


def main():
    worlds = world((20, 75)), world((75, 20))
    markers = [list(log.filter(("marker",))) for log in worlds]
    half = Fraction(1, 2)
    capacity = (all(len(row) == 1 for row in markers)
                and all(e.observable for log in worlds for e in log)
                and all(row[0].t == 0 and row[0].attrs.get("pos") == [75, 50]
                        for row in markers)
                and markers[0][0].attrs.get("tag") != markers[1][0].attrs.get("tag")
                and all(Fraction(sum(mask[i] for mask in masks), len(masks)) == half
                        for masks in ARMS.values() for i in (0, 1)))
    print(f"M1: {'UPHELD' if capacity else 'FALSIFIED'} (markers per world: "
          f"{[len(row) for row in markers]})")
    if not capacity:
        print("M2/M3: NOT SCORED")
        return 1

    def resolves(mask, anonymous=False):
        return delivered(worlds[0], mask, anonymous) != delivered(worlds[1], mask, anonymous)

    outcomes = {mask: resolves(mask) for mask in MASKS}
    print("arm | fused | A alone")
    fused, single = {}, {}
    for name, masks in ARMS.items():
        fused[name] = Fraction(sum(outcomes[mask] for mask in masks), len(masks))
        single[name] = Fraction(sum(outcomes[a, 0] for a, _ in masks), len(masks))
        print(f"{name} | {fused[name]} | {single[name]}")
    m2 = (fused == {"shared": half, "independent": Fraction(3, 4), "complementary": 1}
          and all(p == half for p in single.values()))
    ambiguous = sum(not resolves(mask, anonymous=True) for mask in MASKS)
    payload_only = all(
        [replace(e, attrs={**e.attrs, "tag": "anonymous"}) if e.kind == "marker" else e
         for e in delivered(log, mask)] == delivered(log, mask, anonymous=True)
        for log in worlds for mask in MASKS
    )
    m3 = ambiguous == len(MASKS) and payload_only and not outcomes[0, 0]
    print(f"M2: {'UPHELD' if m2 else 'FALSIFIED'}")
    print(f"M3: {'UPHELD' if m3 else 'FALSIFIED'} ({ambiguous}/{len(MASKS)} anonymous ties)")
    print(f"prereg run: {'PASS' if m2 and m3 else 'FAIL'}")
    return 0 if m2 and m3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
