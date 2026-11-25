"""R-P1.61: what is one noisy diagnostic worth to graph repair?

Frozen card: docs/2026-11-25-PREREG-R-P1.61-one-probe.md. The fixture is the
R-P1.60 generator, copied so a frozen measurement cannot drift with an older
script. Labels reach the scorer and the simulated instrument only; the decoder
sees the partial observations, and a probe reading is an instrument observation,
never truth.

Arms: A none · B passive top-3 · B1 cost-matched passive · C random probe ·
D active probe by expected information gain · E permuted-edge control ·
F uninformative-probe control.
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
K = 3
DEV, HELDOUT = 12, 12
SENSOR_TPR = 0.8
SENSOR_FPR = 0.2
UNINFORMATIVE_DRAWS = 200
LEAK_TOLERANCE = 0.01
PROBE_GAIN = 0.05
PROBE_PRECISION_GAIN = 0.10
ASSOCIATION_MARGIN = 0.05
SELECTION_MARGIN = 0.03
CALIBRATION_TOLERANCE = 0.10
CEILING_MARGIN = 0.10


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


def read(rng: random.Random, truth: set, edge) -> str:
    """The declared sensor. The only place a label reaches the instrument."""
    p = SENSOR_TPR if edge in truth else SENSOR_FPR
    return "present" if rng.random() < p else "absent"


def posterior(worlds: list[frozenset], edge, reading: str) -> list[frozenset]:
    keep = [w for w in worlds if (edge in w) == (reading == "present")]
    return keep or worlds          # a reading consistent with no world: keep the prior


def masses(worlds: list[frozenset], pool: set) -> dict:
    n = len(worlds)
    return {edge: sum(edge in w for w in worlds) / n for edge in pool}


def top_k(weights: dict, k: int = K) -> set:
    ranked = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    return {edge for edge, _ in ranked[:k]}


def active_edge(worlds: list[frozenset], pool: set):
    """Expected information gain over the uniform world posterior."""
    n = len(worlds)
    h0 = math.log(n)
    best, best_gain = None, -1.0
    for edge in sorted(pool):
        k = sum(edge in w for w in worlds)
        if k == 0 or k == n:
            gain = 0.0             # no split, no information
        else:
            p = k / n
            gain = h0 - (p * math.log(k) + (1 - p) * math.log(n - k))
        if gain > best_gain:
            best, best_gain = edge, gain
    return best


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


def summarise(rows: list[dict], arm: str) -> dict:
    picked = [row[arm] for row in rows]
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
        "precision_macro": statistics.fmean(precisions) if precisions else None,
        "recall": correct / (len(rows) * MISSING),
        "abstentions": sum(1 for item in picked if item["proposed"] == 0),
        "completion_error": statistics.fmean(item["completion_error"] for item in picked),
        "queries": statistics.fmean(row["queries"][arm] for row in rows),
    }


def run_case(seed: int) -> dict:
    state = case(seed)
    truth, pool = state["truth"], candidate_pool(state)
    worlds = [set(w) for w in state["worlds"]]
    prior = masses(worlds, pool)
    rng_read = random.Random(seed * 104729 + 7)
    rng_pick = random.Random(seed * 104729 + 11)

    ranked_pool = sorted(pool)
    random_edge = rng_pick.choice(ranked_pool)
    chosen = active_edge(worlds, pool)
    permuted = [e for e in ranked_pool if e != chosen]
    permuted_edge = rng_pick.choice(permuted) if permuted else chosen

    # One reading per probe, drawn in a fixed order so every arm's cost is one
    # query and E reuses D's reading exactly (its marginal is D's).
    random_reading = read(rng_read, truth, random_edge)
    active_reading = read(rng_read, truth, chosen)

    d_worlds = posterior(worlds, chosen, active_reading)
    proposals = {
        "A": set(),
        "B": top_k(prior),
        "B1": top_k(prior),                      # the discarded reading costs nothing else
        "C": top_k(masses(posterior(worlds, random_edge, random_reading), pool)),
        "D": top_k(masses(d_worlds, pool)),
        "E": top_k(masses(posterior(worlds, permuted_edge, active_reading), pool)),
    }
    # F: same query as D, reading independent of the truth, averaged over draws.
    f_errors, f_precisions, f_hits = [], [], []
    for _ in range(UNINFORMATIVE_DRAWS):
        reading = "present" if rng_read.random() < 0.5 else "absent"
        proposed = top_k(masses(posterior(worlds, chosen, reading), pool))
        scored = score(proposed, truth, pool)
        f_errors.append(scored["completion_error"])
        f_precisions.append(scored["precision"] or 0.0)
        f_hits.append(scored["correct"])

    queries = {"A": 0, "B": 0, "B1": 1, "C": 1, "D": 1, "E": 1}
    row = {
        "seed": seed,
        "worlds": len(worlds),
        "pool": len(pool),
        "chosen": list(chosen),
        "random_edge": list(random_edge),
        "permuted_edge": list(permuted_edge),
        "truth": sorted(truth),
        "queries": queries,
        "F": {"completion_error": statistics.fmean(f_errors),
              "precision": statistics.fmean(f_precisions),
              "correct": statistics.fmean(f_hits)},
    }
    for arm, proposed in proposals.items():
        row[arm] = score(proposed, truth, pool)
    # Predicted vs measured hit rate of the proposed edges (D only, declared arm).
    weights = masses(d_worlds, pool)
    row["D_predicted_precision"] = statistics.fmean(weights[edge] for edge in proposals["D"])
    return row


def main() -> int:
    rows = [run_case(seed) for seed in range(DEV + HELDOUT)]
    dev, held = rows[:DEV], rows[DEV:]

    determined = sum(1 for row in rows if row["worlds"] == 1)
    h1 = determined == 0 and all(row["worlds"] >= 2 for row in rows)

    table = {}
    for name, part in (("development", dev), ("held_out", held)):
        table[name] = {arm: summarise(part, arm) for arm in ("A", "B", "B1", "C", "D", "E")}
        draws = [row["F"] for row in part]
        mean_correct = statistics.fmean(draw["correct"] for draw in draws)
        table[name]["F"] = {
            "cases": len(part),
            "queries": 1,
            "proposed": len(part) * K,
            "missing_true_edges": len(part) * MISSING,
            "correct": round(mean_correct * len(part), 2),
            "false_corrections": round(len(part) * K - mean_correct * len(part), 2),
            "recall": mean_correct / (len(part) * MISSING),
            "abstentions": 0,
            "precision": statistics.fmean(draw["precision"] for draw in draws),
            "completion_error": statistics.fmean(draw["completion_error"] for draw in draws),
        }

    print(f"cases {len(rows)} ({DEV} dev, {HELDOUT} held-out); determined {determined}/{len(rows)}; "
          f"pool mean {statistics.fmean(row['pool'] for row in rows):.1f}; missing {MISSING}/case")
    for name in ("development", "held_out"):
        n = len(dev) if name == "development" else len(held)
        print(f"\n{name} ({n} cases) — sensor TPR {SENSOR_TPR}, FPR {SENSOR_FPR}, one query")
        print("| arm | queries | proposed | correct | false | precision | recall | abstentions | completion error |")
        print("|---|---|---|---|---|---|---|---|---|")
        for arm in ("A", "B", "B1", "C", "D", "E", "F"):
            s = table[name][arm]
            precision = "— (0 proposals)" if s["precision"] is None else f"{s['precision']:.3f}"
            print(f"| {arm} | {s['queries']:.0f} | {s['proposed']} | {s['correct']}/{s['missing_true_edges']} "
                  f"| {s['false_corrections']} | {precision} | {s['recall']:.3f} "
                  f"| {s['abstentions']}/{s['cases']} | {s['completion_error']:.3f} |")

    b, d, e, f = (table["held_out"][arm] for arm in ("B", "D", "E", "F"))
    c = table["held_out"]["C"]
    predicted = statistics.fmean(row["D_predicted_precision"] for row in held)
    # Macro, per case: the pooled figure weights a case with three hits the same
    # as three cases with one, which is not what "hit rate of the proposal" means.
    measured = statistics.fmean(row["D"]["precision"] for row in held
                               if row["D"]["precision"] is not None)
    h2 = f["completion_error"] >= b["completion_error"] - LEAK_TOLERANCE
    h3 = (d["completion_error"] <= b["completion_error"] - PROBE_GAIN
          and measured >= (b["precision"] or 0.0) + PROBE_PRECISION_GAIN)
    h4 = d["completion_error"] <= e["completion_error"] - ASSOCIATION_MARGIN
    h5 = d["completion_error"] <= c["completion_error"] - SELECTION_MARGIN
    h6 = abs(predicted - measured) <= CALIBRATION_TOLERANCE
    headroom = h1 and h2 and h3 and h4 and (1.0 - measured) >= CEILING_MARGIN

    print()
    for label, value, why in (
        ("H1 fixture ambiguous", h1, f"{determined}/{len(rows)} determined"),
        ("H2 no leak through probe choice", h2,
         f"F error {f['completion_error']:.3f} vs B {b['completion_error']:.3f}"),
        ("H3 one paired probe pays", h3,
         f"D error {d['completion_error']:.3f} vs B {b['completion_error']:.3f}; "
         f"precision {measured:.3f} vs {b['precision'] or 0.0:.3f}"),
        ("H4 association pays", h4,
         f"D {d['completion_error']:.3f} vs E {e['completion_error']:.3f}"),
        ("H5 choosing the edge matters", h5,
         f"D {d['completion_error']:.3f} vs C {c['completion_error']:.3f}"),
        ("H6 posterior calibrated", h6,
         f"predicted {predicted:.3f} vs measured {measured:.3f}"),
    ):
        print(f"{label}: {'UPHELD' if value else 'FALSIFIED'} ({why})")
    verdict = "VACUOUS" if not h1 else ("INVALID" if not h2
                                       else ("HEADROOM" if headroom else "NO HEADROOM"))
    print(f"one-probe headroom: {verdict}")

    out = Path(__file__).resolve().parents[1] / "research/loops/results/one-probe-20261125"
    out.mkdir(parents=True, exist_ok=True)
    receipt = {
        "card": "R-P1.61",
        "claim_id": "2fdd97c9-c1ee-4870-823f-84219d78f45e",
        "prereg": "docs/2026-11-25-PREREG-R-P1.61-one-probe.md",
        "command": ".venv/bin/python scripts/one-probe-prereg.py",
        "fixture": {"cases": len(rows), "development": DEV, "held_out": HELDOUT,
                    "determined": determined, "missing_per_case": MISSING,
                    "sensor_tpr": SENSOR_TPR, "sensor_fpr": SENSOR_FPR,
                    "uninformative_draws": UNINFORMATIVE_DRAWS},
        "arms": table,
        "checks": {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5, "H6": h6},
        "posterior_calibration": {"predicted": predicted, "measured": measured},
        "verdict": verdict,
        "per_case": [{key: value for key, value in row.items() if key != "queries"}
                     for row in rows],
    }
    (out / "receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    print(f"receipt: {out.relative_to(Path(__file__).resolve().parents[1])}/receipt.json")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
