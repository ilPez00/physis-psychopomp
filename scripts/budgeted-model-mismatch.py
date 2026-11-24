"""R-P1.58: exhaustive one-probe witness, including in-support model mismatch."""
import json
import sys
from collections import Counter
from fractions import Fraction
from math import fsum, isclose, log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_design import best_probes, information_gain, posterior

LAWS = (-1, 1)
COST = {"passive": 1, "overlap": 1, "clean": 2}
TABLES = {
    "passive": ((0, 0, 0, 0), (0, 0, 0, 0)),
    "overlap": ((-2, -2, -1, 1), (2, 2, -1, 1)),
    "clean": ((-2, -2, -2, -2), (2, 2, 2, 2)),
}
PRIOR = dict.fromkeys(LAWS, Fraction(1, 2))


def run(channel, prediction_rows, episodes):
    counts = dict(cases=0, acquisitions=0, cost=0, correct=0, false=0, abstain=0,
                  prior_unchanged=0)
    drops = []
    for law, acquire in episodes:
        reading = acquire(channel) if channel else None
        belief = posterior(prediction_rows, reading) or PRIOR
        resolved = next((law for law, p in belief.items() if p == 1), None)
        counts["correct"] += resolved is not None and resolved == law
        counts["false"] += resolved is not None and resolved != law
        counts["abstain"] += resolved is None
        counts["prior_unchanged"] += belief == PRIOR
        counts["cases"] += 1
        counts["acquisitions"] += channel is not None
        counts["cost"] += COST.get(channel, 0)
        drops.append(1 + fsum(float(p) * log2(float(p)) for p in belief.values() if p))
    return {**counts, "predicted_bits": information_gain(prediction_rows) if channel else 0,
            "realized_bits": fsum(drops) / counts["cases"]}


def measure(tables=TABLES, third=(9, 9, 2, 2)):
    rows = {probe: [(law, y) for law, ys in zip(LAWS, pair) for y in ys]
            for probe, pair in tables.items()}
    nominal = [(law, lambda probe, slot=slot, mode=mode: tables[probe][slot][mode])
               for slot, law in enumerate(LAWS) for mode in range(4)]
    gains = {probe: information_gain(rows[probe]) for probe in COST}
    picks = [best_probes({probe: rows[probe] for probe in COST if COST[probe] <= budget})
             for budget in range(3)]

    def close(actual, expected):
        return isclose(actual, expected, rel_tol=0, abs_tol=1e-12)

    capacity = (picks == [(), ("overlap",), ("clean",)]
                and all(close(gains[p], v) for p, v in zip(COST, (0, .5, 1))))
    report = {"gains": gains, "picks": picks, "checks": {"B1": capacity}}
    if not capacity:
        return report

    zero = run(None, [], nominal)
    active = run("overlap", rows["overlap"], nominal)
    clean = run("clean", rows["clean"], nominal)
    report["checks"]["B1"] &= (zero["abstain"] == 8
                              and [r["acquisitions"] for r in (zero, active, clean)] == [0, 8, 8]
                              and [r["cost"] for r in (zero, active, clean)] == [0, 8, 16])
    if not report["checks"]["B1"]:
        return report

    fixed = run("passive", rows["passive"], nominal)
    pooled = Counter(y for _, y in rows["overlap"])
    shuffled_rows = [(law, y) for law in LAWS for y, n in pooled.items() for _ in range(n // 2)]
    assert Counter(y for _, y in shuffled_rows) == pooled
    shuffled = run("overlap", shuffled_rows, nominal)
    random = {key: active[key] + fixed[key] for key in
              ("cases", "cost", "acquisitions", "correct", "false", "abstain")}
    missing = run("overlap", rows["overlap"], [(law, lambda _: None) for law, _ in nominal])
    outside = [(None, lambda _, reading=reading: reading) for reading in third]
    unsupported = run("overlap", rows["overlap"], outside[:2])
    mimic = run("overlap", rows["overlap"], outside[2:])
    report["arms"] = dict(zero=zero, active=active, clean=clean, fixed=fixed, random=random,
                          shuffled=shuffled, missing=missing, unsupported=unsupported, mimic=mimic)
    report["checks"].update({
        "B2": all(r["cost"] == r["cases"] for r in (active, fixed, random, shuffled))
        and [(r["correct"], r["cases"], r["false"], r["abstain"])
             for r in (active, fixed, random, shuffled, clean)]
        == [(4, 8, 0, 4), (0, 8, 0, 8), (4, 16, 0, 12), (0, 8, 0, 8), (8, 8, 0, 0)],
        "B3": missing["cost"] == missing["prior_unchanged"] == missing["abstain"] == 8
        and unsupported["prior_unchanged"] == unsupported["abstain"] == 2,
        "B4": third[2:] == (2, 2) and mimic["false"] == mimic["cases"] == 2,
        "B5": all(close(r["predicted_bits"], n) and close(r["realized_bits"], n)
                  for r, n in zip((zero, active, clean), (0, .5, 1)))
        and close(missing["predicted_bits"], .5) and close(missing["realized_bits"], 0),
    })
    return report


if __name__ == "__main__":
    result = measure()
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = all(result["checks"].values())
    print(f"budgeted model mismatch: {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)
