"""R-P1.62: is the probe's quality or its budget the constraint?

Frozen card: docs/2026-11-26-PREREG-R-P1.62-probe-budget.md. Reuses the frozen
R-P1.61 generator and arms — copied, so a frozen measurement cannot drift — and
sweeps sensor quality `q` and probe count `k` separately.

R-P1.61 concluded "the sensor, not the policy, is the binding constraint" from a
single point (q = 0.8, k = 1). This measures whether that sentence survives.

Labels reach the scorer and the simulated instrument only.
"""
from __future__ import annotations

import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.graph_patch import decode
from psychopomp.physis_snapshot import Edge, Snapshot

NODES = [f"node:{i}" for i in range(4)]
PORTS = [f"port:{i}" for i in range(4)]
ENTITIES = NODES + PORTS
PREDICATE = "LINK"
SIZE = 6
OBSERVED = 3
MISSING = SIZE - OBSERVED
CAP = 2
K_PROPOSE = 3
DEV, HELDOUT = 12, 12
QUALITIES = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
BUDGETS = [1, 2, 3, 4, 6, 8, 12, 21]
P1_EXPECTED = 0.18
P1_TOLERANCE = 0.05


def admissible() -> list[tuple[str, str, str]]:
    pairs = [(a, b) for a in NODES for b in NODES if a != b]
    pairs += [(a, b) for a in NODES for b in PORTS]
    return [(s, PREDICATE, t) for s, t in pairs]


def within_caps(edges) -> bool:
    out: dict[str, int] = {}
    inn: dict[str, int] = {}
    for source, _, target in edges:
        out[source] = out.get(source, 0) + 1
        inn[target] = inn.get(target, 0) + 1
    return all(v <= CAP for v in out.values()) and all(v <= CAP for v in inn.values())


def draw_truth(rng: random.Random, pool: list[tuple[str, str, str]]) -> set:
    for _ in range(4000):
        picked = set(rng.sample(pool, SIZE))
        if within_caps(picked):
            return picked
    raise RuntimeError("could not draw a truth satisfying the closure rule")


def surviving_worlds(observed: set, pool: list[tuple[str, str, str]]) -> list[frozenset]:
    rest = [edge for edge in pool if edge not in observed]
    worlds = []
    for combo in itertools.combinations(rest, MISSING):
        edges = set(observed) | set(combo)
        if within_caps(edges):
            worlds.append(frozenset(edges))
    return worlds


def case(seed: int) -> dict:
    rng = random.Random(seed)
    pool = admissible()
    truth = draw_truth(rng, pool)
    observed = set(rng.sample(sorted(truth), OBSERVED))
    worlds = surviving_worlds(observed, pool)
    assert frozenset(truth) in worlds, "the truth must survive its own closure rule"
    snapshot = Snapshot(entities={e: e.split(":")[0] for e in ENTITIES},
                        edges=[Edge(*edge) for edge in sorted(observed)])
    return {"seed": seed, "truth": truth, "observed": observed,
            "worlds": worlds, "snapshot": snapshot}


def candidate_pool(state: dict) -> set:
    plan = decode(state["snapshot"], [set(world) for world in state["worlds"]])
    return {tuple(op[key] for key in ("source", "predicate", "target"))
            for op in plan["operations"] if op["op"] == "propose_edge"}


def masses(worlds: list[frozenset], pool: set) -> dict:
    n = len(worlds)
    return {edge: sum(edge in w for w in worlds) / n for edge in pool}


def top_k(weights: dict, k: int = K_PROPOSE) -> set:
    ranked = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    return {edge for edge, _ in ranked[:k]}


def best_edges(worlds: list[frozenset], pool: set, k: int) -> list:
    """`k` edges by expected information gain over the uniform world posterior."""
    n = len(worlds)
    h0 = math.log(n)
    scored = []
    for edge in sorted(pool):
        split = sum(edge in w for w in worlds)
        if split == 0 or split == n:
            gain = 0.0
        else:
            p = split / n
            gain = h0 - (p * math.log(split) + (1 - p) * math.log(n - split))
        scored.append((gain, edge))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in scored[:k]]


def probe(worlds: list[frozenset], pool: set, truth: set, k: int, q: float,
          rng: random.Random) -> list[frozenset]:
    """Query `k` edges in information order; filter by every reading."""
    kept = list(worlds)
    for edge in best_edges(worlds, pool, k):
        p = q if edge in truth else 1.0 - q
        present = rng.random() < p
        filtered = [w for w in kept if (edge in w) == present]
        if filtered:                    # a reading no world explains keeps the prior
            kept = filtered
    return kept


def score(proposed: set, truth: set, pool: set) -> dict:
    hit = proposed & truth
    error = sum(((1 if edge in truth else 0) - (1 if edge in proposed else 0)) ** 2
                for edge in pool)
    return {
        "proposed": len(proposed),
        "correct": len(hit),
        "false_corrections": len(proposed - truth),
        "precision": len(hit) / len(proposed) if proposed else None,
        "recall": len(hit) / MISSING,
        "completion_error": error / len(pool) if pool else 0.0,
    }


def summarise(rows: list[dict]) -> dict:
    picked = [row["result"] for row in rows]
    proposed = sum(item["proposed"] for item in picked)
    correct = sum(item["correct"] for item in picked)
    precisions = [item["precision"] for item in picked if item["proposed"]]
    return {
        "cases": len(rows),
        "proposed": proposed,
        "correct": correct,
        "missing_true_edges": len(rows) * MISSING,
        "false_corrections": sum(item["false_corrections"] for item in picked),
        "precision": correct / proposed if proposed else None,
        "recall": correct / (len(rows) * MISSING),
        "completion_error": statistics.fmean(item["completion_error"] for item in picked),
    }


def run_point(q: float, k: int) -> list[dict]:
    """One (quality, budget) cell over every case, posteriors carried forward."""
    rows = []
    for seed in range(DEV + HELDOUT):
        state = case(seed)
        pool = candidate_pool(state)
        worlds = [set(w) for w in state["worlds"]]
        rng = random.Random(seed * 104729 + 7)
        after = probe(state["worlds"], pool, state["truth"], k, q, rng)
        proposed = top_k(masses(after, pool))
        rows.append({"seed": seed,
                     "result": score(proposed, state["truth"], pool)})
    return rows


def main() -> int:
    # The prereg's bar is B_precision + 0.10 where B is the *held-out* passive
    # arm, the same split every swept cell is scored on. My first version built
    # it from all 24 cases (0.167 instead of 0.194), which moved the bar down by
    # 0.027 and would have reported two cells as clearing when they do not.
    passive_rows = [{"result": score(
        top_k(masses([set(w) for w in case(s)["worlds"]], candidate_pool(case(s)))),
        case(s)["truth"], candidate_pool(case(s)))}
        for s in range(DEV + HELDOUT)]
    passive_all = summarise(passive_rows)
    passive = summarise(passive_rows[DEV:])
    bar = (passive["precision"] or 0.0) + 0.10
    print(f"passive top-3 (held-out): precision {passive['precision']:.3f}, "
          f"completion error {passive['completion_error']:.3f}; bar {bar:.3f}")
    print(f"passive top-3 (all {len(passive_rows)} cases, not the bar): "
          f"precision {passive_all['precision']:.3f}")

    print("\n== quality sweep at k = 1 (held-out)")
    print("| q | precision | recall | completion error | clears bar |")
    print("|---|---|---|---|---|")
    by_q = {}
    for q in QUALITIES:
        rows = run_point(q, 1)
        dev, held = rows[:DEV], rows[DEV:]
        by_q[q] = {"held": summarise(held), "all": summarise(rows)}
        h = by_q[q]["held"]
        print(f"| {q} | {h['precision']:.3f} | {h['correct']}/{h['missing_true_edges']} "
              f"| {h['completion_error']:.3f} | "
              f"{'YES' if (h['precision'] or 0) >= bar else 'no'} |")

    print("\n== budget sweep (held-out)")
    print("| q | k | precision | recall | completion error | clears bar |")
    print("|---|---|---|---|---|---|")
    by_k = {}
    for q in (0.8, 1.0):
        for k in BUDGETS:
            rows = run_point(q, k)
            held = summarise(rows[DEV:])
            by_k[(q, k)] = held
            print(f"| {q} | {k} | {held['precision']:.3f} "
                  f"| {held['correct']}/{held['missing_true_edges']} "
                  f"| {held['completion_error']:.3f} | "
                  f"{'YES' if (held['precision'] or 0) >= bar else 'no'} |")

    p1_values = [by_q[q]["held"]["precision"] or 0.0 for q in QUALITIES]
    p1 = all(v < bar for v in p1_values)
    p1_gap = abs(p1_values[-1] - P1_EXPECTED)
    p1_expected = p1_gap <= P1_TOLERANCE
    p2 = all(b >= a - 1e-9 for a, b in zip(p1_values, p1_values[1:]))
    cross_08 = next((k for k in BUDGETS if (by_k[(0.8, k)]["precision"] or 0) >= bar), None)
    cross_10 = next((k for k in BUDGETS if (by_k[(1.0, k)]["precision"] or 0) >= bar), None)
    p3 = (cross_08 is not None and cross_08 <= 8) and (cross_10 is not None and cross_10 <= 4)
    p4_cases = [by_k[(0.8, k)] for k in ([cross_08] if cross_08 else [])] + \
               [by_k[(1.0, k)] for k in ([cross_10] if cross_10 else [])]
    p4 = bool(p4_cases) and all(c["completion_error"] < passive["completion_error"]
                               for c in p4_cases)

    print()
    for label, value, why in (
        ("P1 quality alone never clears the bar", p1,
         f"max {max(p1_values):.3f} vs bar {bar:.3f}"),
        ("P1b q=1.0 near the predicted 0.18", p1_expected,
         f"{p1_values[-1]:.3f} vs {P1_EXPECTED}±{P1_TOLERANCE}"),
        ("P2 monotone in quality", p2, ", ".join(f"{v:.3f}" for v in p1_values)),
        ("P3 budget crosses the bar", p3,
         f"q0.8 first at k={cross_08}, q1.0 first at k={cross_10}"),
        ("P4 crossing also beats silence at completion", p4,
         f"passive {passive['completion_error']:.3f}"),
    ):
        print(f"{label}: {'UPHELD' if value else 'FALSIFIED'} ({why})")

    # Uncertainty, added after the first run and NOT a threshold change: the
    # same declared cell (q 0.8, k 1) read 0.167 in R-P1.61 and 0.083 here,
    # because the two scripts draw their readings in a different order. Twelve
    # held-out cases cannot separate those. So the reported cells are resampled
    # with independent reading draws and the spread is recorded next to them,
    # rather than being presented as point estimates.
    def replicate(q: float, k: int, reps: int = 24) -> dict:
        values = []
        for rep in range(reps):
            rows = []
            for seed in range(DEV, DEV + HELDOUT):
                state = case(seed)
                pool = candidate_pool(state)
                rng = random.Random(seed * 104729 + 7 + rep * 1013)
                after = probe(state["worlds"], pool, state["truth"], k, q, rng)
                proposed = top_k(masses(after, pool))
                rows.append({"result": score(proposed, state["truth"], pool)})
            values.append((summarise(rows)["precision"] or 0.0))
        return {"reps": reps, "mean": statistics.fmean(values),
                "sd": statistics.pstdev(values), "min": min(values),
                "max": max(values),
                "share_clearing_bar": sum(1 for v in values if v >= bar) / reps}

    reps = {f"{q}@{k}": replicate(q, k) for q, k in
            [(0.8, 1), (1.0, 1), (1.0, 3), (1.0, 4), (0.8, 21)]}
    print("\n== reading-draw spread (24 independent draws per cell, held-out)")
    print("| cell | mean | sd | min | max | share clearing bar |")
    print("|---|---|---|---|---|---|")
    for name, r in reps.items():
        print(f"| {name} | {r['mean']:.3f} | {r['sd']:.3f} | {r['min']:.3f} "
              f"| {r['max']:.3f} | {r['share_clearing_bar']:.2f} |")

    verdict = ("BUDGET BINDS" if (p1 and p3 and p4)
               else "QUALITY BINDS" if (not p1 and not p3)
               else "MIXED")
    print(f"binding constraint: {verdict}")

    out = Path(__file__).resolve().parents[1] / "research/loops/results/probe-budget-20261126"
    out.mkdir(parents=True, exist_ok=True)
    receipt = {
        "card": "R-P1.62",
        "claim_id": "8c130cc6-e95d-45b4-b45c-81993bbf4d8e",
        "prereg": "docs/2026-11-26-PREREG-R-P1.62-probe-budget.md",
        "command": ".venv/bin/python scripts/probe-budget-prereg.py",
        "passive_held_out": passive,
        "passive_all_cases": passive_all,
        "bar": bar,
        "by_quality": {str(q): v["held"] for q, v in by_q.items()},
        "by_budget": {f"{q}@{k}": v for (q, k), v in by_k.items()},
        "checks": {"P1": p1, "P1b": p1_expected, "P2": p2, "P3": p3, "P4": p4},
        "cross_k": {"q0.8": cross_08, "q1.0": cross_10},
        "replicates": reps,
        "verdict": verdict,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    print(f"receipt: {out.relative_to(Path(__file__).resolve().parents[1])}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
