"""R-P1.60: corrected E5 repair evaluation.

Frozen card: docs/2026-11-25-PREREG-R-P1.60-repair-eval.md. Same fixture as
R-P1.56 (copied here so the frozen generator cannot drift with the old script),
with three scoring corrections: recall divides by missing true edges, the null
draws exactly |missing| edges from the same candidate pool, and every arm is
also scored by completion error over the whole candidate pool so that silent
denial is not free.

The decoder sees partial observations only. Truth edge sets are read by the
scorer and by nothing else.
"""
from __future__ import annotations

import itertools
import json
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
DEV, HELDOUT = 12, 12
DRAWS = 200
NULL_TOLERANCE = 0.05
SIGNAL_MARGIN = 0.10
CEILING_MARGIN = 0.10
PAIRED_SHARE = 2 / 3
CLOSURE_SHARE = 0.9


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


def candidates(state: dict) -> dict:
    plan = decode(state["snapshot"], [set(world) for world in state["worlds"]])
    claimed = {tuple(op[key] for key in ("source", "predicate", "target")): op
               for op in plan["operations"] if op["op"] == "propose_edge"}
    support = {edge: sum(edge in world for world in state["worlds"]) for edge in claimed}
    return {"claimed": claimed, "support": support}


def arm_consensus(claimed: dict) -> set:
    return {edge for edge, op in claimed.items() if op["agreement"] == "all_surviving_worlds"}


def arm_closure(support: dict, worlds: int, share: float = CLOSURE_SHARE) -> set:
    return {edge for edge, count in support.items() if count >= share * worlds}


def arm_rank(support: dict, k: int = MISSING) -> set:
    ranked = sorted(support.items(), key=lambda item: (-item[1], item[0]))
    return {edge for edge, _ in ranked[:k]}


def score(proposed: set, truth: set, pool: set) -> dict:
    hit = proposed & truth
    error = sum(((1 if edge in truth else 0) - (1 if edge in proposed else 0)) ** 2
                for edge in pool)
    return {
        "proposed": len(proposed),
        "correct": len(hit),
        "false_corrections": len(proposed - truth),
        "precision": len(hit) / len(proposed) if proposed else 0.0,
        "recall": len(hit) / MISSING,
        "completion_error": error / len(pool) if pool else 0.0,
    }


def null_precisions(state: dict, proposed: set) -> list[float]:
    """C's proposals against |missing|-edge pseudo-truths from the same pool."""
    pool = sorted(set().union(*state["worlds"]) - state["observed"])
    rng = random.Random(state["seed"] * 7919 + 1)
    draws = min(MISSING, len(pool))
    values = []
    for _ in range(DRAWS):
        fake = set(rng.sample(pool, draws))
        values.append(score(proposed, fake, set(pool))["precision"])
    return values


def summarise(rows: list[dict], arm: str) -> dict:
    picked = [row[arm] for row in rows]
    proposed = sum(item["proposed"] for item in picked)
    correct = sum(item["correct"] for item in picked)
    false = sum(item["false_corrections"] for item in picked)
    return {
        "cases": len(rows),
        "proposed": proposed,
        "correct": correct,
        "false_corrections": false,
        "missing_true_edges": len(rows) * MISSING,
        "precision": correct / proposed if proposed else 0.0,
        "recall": correct / (len(rows) * MISSING),
        "abstentions": sum(1 for item in picked if item["proposed"] == 0),
        "completion_error": sum(item["completion_error"] for item in picked) / len(picked),
    }


def main() -> int:
    rows = []
    for seed in range(DEV + HELDOUT):
        state = case(seed)
        found = candidates(state)
        truth, pool = state["truth"], set(found["support"])
        proposals = {
            "A": set(),
            "B": arm_consensus(found["claimed"]),
            "C": arm_rank(found["support"]),
            "E": arm_closure(found["support"], len(state["worlds"])),
        }
        row = {"seed": seed, "worlds": len(state["worlds"]), "pool": len(pool),
               "analytic_null": min(MISSING, len(pool)) / len(pool) if pool else 0.0,
               "pool_edges": sorted(pool), "truth": sorted(truth)}
        for arm, proposed in proposals.items():
            row[arm] = score(proposed, truth, pool)
        nulls = null_precisions(state, proposals["C"])
        row["D_draws"] = nulls
        row["D"] = statistics.fmean(nulls)
        row["D_median"] = statistics.median(nulls)
        rows.append(row)
    dev, held = rows[:DEV], rows[DEV:]

    determined = sum(1 for row in rows if row["worlds"] == 1)
    h1 = determined == 0 and all(row["worlds"] >= 2 for row in rows)

    table = {}
    for name, part in (("development", dev), ("held_out", held)):
        table[name] = {arm: summarise(part, arm) for arm in ("A", "B", "C", "E")}
        table[name]["D"] = {
            "cases": len(part),
            "precision": statistics.fmean(row["D"] for row in part),
            "analytic_null": statistics.fmean(row["analytic_null"] for row in part),
        }

    print(f"cases {len(rows)} ({DEV} dev, {HELDOUT} held-out); "
          f"determined by observations: {determined}/{len(rows)}")
    print(f"candidate pool: mean {statistics.fmean(row['pool'] for row in rows):.1f} "
          f"edges; missing true edges per case: {MISSING}")
    for name in ("development", "held_out"):
        print(f"\n{name} ({len(dev) if name == 'development' else len(held)} cases)")
        print("| arm | proposed | correct | false | precision | recall | abstentions | completion error |")
        print("|---|---|---|---|---|---|---|---|")
        for arm in ("A", "B", "C", "E"):
            s = table[name][arm]
            print(f"| {arm} | {s['proposed']} | {s['correct']}/{s['missing_true_edges']} "
                  f"| {s['false_corrections']}/{s['proposed']} | {s['precision']:.3f} "
                  f"| {s['recall']:.3f} | {s['abstentions']}/{s['cases']} "
                  f"| {s['completion_error']:.3f} |")
        d = table[name]["D"]
        print(f"| D null | — | — | — | {d['precision']:.3f} | — | — | — |")
        print(f"| D analytic | — | — | — | {d['analytic_null']:.3f} | — | — | — |")

    c, a = table["held_out"]["C"], table["held_out"]["A"]
    d = table["held_out"]["D"]
    paired = [row for row in held if row["C"]["proposed"]]
    wins = sum(1 for row in paired if row["C"]["precision"] > row["D_median"])
    h2 = abs(d["precision"] - d["analytic_null"]) <= NULL_TOLERANCE
    h3 = (c["precision"] - d["precision"] >= SIGNAL_MARGIN
          and wins / len(paired) >= PAIRED_SHARE)
    h4 = c["completion_error"] < a["completion_error"]
    h5 = h3 and h4 and (1.0 - c["precision"]) >= CEILING_MARGIN

    print()
    for label, value, why in (
        ("H1 fixture ambiguous", h1, f"{determined}/{len(rows)} determined"),
        ("H2 null calibrated", h2,
         f"D {d['precision']:.3f} vs analytic {d['analytic_null']:.3f}"),
        ("H3 support beats null", h3,
         f"margin {c['precision'] - d['precision']:.3f}, paired {wins}/{len(paired)}"),
        ("H4 proposing beats denial", h4,
         f"error C {c['completion_error']:.3f} vs A {a['completion_error']:.3f}"),
        ("H5 headroom", h5, f"unused precision {1.0 - c['precision']:.3f}"),
    ):
        print(f"{label}: {'UPHELD' if value else 'FALSIFIED'} ({why})")
    verdict = "VACUOUS" if not h1 else ("INVALID" if not h2
                                        else ("HEADROOM" if h5 else "NO HEADROOM"))
    print(f"repair headroom: {verdict}")

    out = Path(__file__).resolve().parents[1] / "research/loops/results/repair-eval-20261125"
    out.mkdir(parents=True, exist_ok=True)
    receipt = {
        "card": "R-P1.60",
        "claim_id": "07acc2b8-a5ad-4d6d-871a-7b21626f6506",
        "prereg": "docs/2026-11-25-PREREG-R-P1.60-repair-eval.md",
        "command": ".venv/bin/python scripts/repair-eval-prereg.py",
        "fixture": {"cases": len(rows), "development": DEV, "held_out": HELDOUT,
                    "determined": determined, "missing_per_case": MISSING,
                    "null_draws": DRAWS},
        "arms": table,
        "checks": {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5},
        "paired_wins": f"{wins}/{len(paired)}",
        "verdict": verdict,
        "per_case": rows,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(f"receipt: {out.relative_to(Path(__file__).resolve().parents[1])}/receipt.json")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
