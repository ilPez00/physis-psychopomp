"""Print a planning table so a prereg can quote generated picks, not hand-read ones.

Three preregistered predictions in a row (R-P1.26 P3, R-P1.27 P1/P3, R-P1.28 P1)
were wrong for the same reason: the table was read by eye and a tie-break or a
residual weight decided the pick. This script exists so that number is copied.

Usage: .venv/bin/python scripts/plan-table.py [--harness self-model]
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, ".")

from psychopomp.law import blind_region
from psychopomp.sim import SimConfig

HARNESS = {
    "o": (40.0, 60.0, 35.0, 65.0),
    "o2": (46.0, 54.0, 35.0, 65.0),
    "tasks": (42.0, 46.0, 48.0, 52.0),
    "lane": 45.0,
    "drifts": (-1.0, -0.5, 0.0, 0.5, 1.0),
    "deltas": (-20.0, -10.0, 0.0, 10.0, 20.0),
    "t": 90,
}


def predicted_score(delta: float, drift: float, h: dict) -> int:
    cfg = SimConfig(o=h["o"], o2=h["o2"], o2_velocity=(drift, 0.0))
    base = blind_region(cfg, h["t"])
    if base is None:
        return len(h["tasks"])
    lo = max(h["o"][0], base[0] + delta)
    hi = min(h["o"][1], base[1] + delta)
    if lo >= hi:
        return len(h["tasks"])
    return sum(1 for x in h["tasks"]
               if not (lo <= x <= hi and base[2] <= h["lane"] <= base[3]))


def pick(peak: float | None, mass: float, h: dict) -> float:
    deltas, drifts = h["deltas"], h["drifts"]
    if peak is None:
        return max(drifts, key=lambda v: (min(predicted_score(d, v, h) for d in deltas),
                                          -abs(v), -v))
    rest = (1.0 - mass) / (len(deltas) - 1)
    weights = {d: (mass if d == peak else rest) for d in deltas}
    expected = {v: sum(w * predicted_score(d, v, h) for d, w in weights.items())
                for v in drifts}
    return max(drifts, key=lambda v: (expected[v], -abs(v), -v))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--harness", default="self-model")
    args = ap.parse_args()
    h = HARNESS
    print("predicted score by (delta, drift) — generated, do not transcribe by hand")
    print("| δ \\ drift | " + " | ".join(f"{v:+.1f}" for v in h["drifts"]) + " |")
    print("|---" * (len(h["drifts"]) + 1) + "|")
    for d in h["deltas"]:
        print(f"| {d:+.0f} | " + " | ".join(f"{predicted_score(d, v, h)}"
                                            for v in h["drifts"]) + " |")
    print()
    print("| planner | pick |")
    print("|---|---|")
    print(f"| minimax | {pick(None, 0.0, h):+.1f} |")
    for mass in (0.8, 0.95, 1.0):
        for peak in h["deltas"]:
            print(f"| peak {peak:+.0f} @ {mass:.2f} | {pick(peak, mass, h):+.1f} |")
    _ = args
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
