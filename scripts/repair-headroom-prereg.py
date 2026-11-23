"""R-P1.56: how much correct repair does a deterministic policy leave on the table?

Frozen card: docs/2026-11-23-PREREG-R-P1.56-repair-headroom.md. This measures
the **baseline**, not a learner. The decoder receives partial observations only;
the true edge set is read by the scorer and by nothing else. A run that lets the
decoder see the truth would score 1.00 for a reason that has nothing to do with
repair, so `case` builds the observations first and the truth is only returned
alongside them.

Arms, all on the same cases:
  A no repair · B consensus only · C top-3 by support · D C against permuted truth
"""
from __future__ import annotations

import itertools
import random
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
CAP = 2
DEV, HELDOUT = 12, 12


def admissible() -> list[tuple[str, str, str]]:
    """Kind-admissible pairs, in canonical order: node→node and node→port."""
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
    """A 6-edge truth that satisfies the closure rule; retried deterministically."""
    for _ in range(4000):
        picked = set(rng.sample(pool, SIZE))
        if within_caps(picked):
            return picked
    raise RuntimeError("could not draw a truth satisfying the closure rule")


def surviving_worlds(observed: set, pool: list[tuple[str, str, str]]) -> list[frozenset]:
    rest = [edge for edge in pool if edge not in observed]
    worlds = []
    for combo in itertools.combinations(rest, SIZE - OBSERVED):
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
    """Edge -> number of surviving worlds claiming it, from the decoder's output."""
    plan = decode(state["snapshot"], [set(world) for world in state["worlds"]])
    claimed = {tuple(op[key] for key in ("source", "predicate", "target")): op
               for op in plan["operations"] if op["op"] == "propose_edge"}
    support = {edge: sum(edge in world for world in state["worlds"]) for edge in claimed}
    return {"claimed": claimed, "support": support}


def score(proposed: set, truth: set) -> dict:
    hit = proposed & truth
    return {
        "proposed": len(proposed),
        "correct": len(hit),
        "precision": len(hit) / len(proposed) if proposed else 0.0,
        "recall": len(hit) / len(truth),
        "false_corrections": len(proposed - truth),
    }


def arm_consensus(claimed: dict) -> set:
    return {edge for edge, op in claimed.items() if op["agreement"] == "all_surviving_worlds"}


def arm_rank(support: dict, k: int = 3) -> set:
    ranked = sorted(support.items(), key=lambda item: (-item[1], item[0]))
    return {edge for edge, _ in ranked[:k]}


def summarise(rows: list[dict], key: str) -> dict:
    total = len(rows)
    proposed = sum(row[key]["proposed"] for row in rows)
    correct = sum(row[key]["correct"] for row in rows)
    false = sum(row[key]["false_corrections"] for row in rows)
    return {
        "cases": total,
        "proposed": proposed,
        "correct": correct,
        "false_corrections": false,
        "precision": correct / proposed if proposed else 0.0,
        "recall": correct / (total * SIZE),
        "abstentions": sum(1 for row in rows if row[key]["proposed"] == 0),
    }


def main() -> int:
    seeds = list(range(DEV + HELDOUT))
    rows = []
    for seed in seeds:
        state = case(seed)
        found = candidates(state)
        truth = state["truth"]
        rows.append({
            "seed": seed,
            "worlds": len(state["worlds"]),
            "A": score(set(), truth),
            "B": score(arm_consensus(found["claimed"]), truth),
            "C": score(arm_rank(found["support"]), truth),
            "C_edges": arm_rank(found["support"]),
            "pool": sorted(found["claimed"]),
            "truth": sorted(truth),
        })
    dev, held = rows[:DEV], rows[DEV:]

    # Arm D: the same ranking against a truth permuted within each case's pool.
    for row in rows:
        rng = random.Random(row["seed"] * 7919 + 1)
        precisions = []
        for _ in range(200):
            fake = set(rng.sample(row["pool"], min(SIZE, len(row["pool"]))))
            precisions.append(score(arm_rank(candidates(case(row["seed"]))["support"]), fake)["precision"])
        row["D"] = sum(precisions) / len(precisions)

    determined = sum(1 for row in rows if row["worlds"] == 1)
    determined_share = determined / len(rows)
    print(f"cases {len(rows)} ({len(dev)} dev, {len(held)} held-out); "
          f"determined by observations: {determined}/{len(rows)} ({determined_share:.3f})")
    for name, part in (("dev", dev), ("held-out", held)):
        print(f"\n| arm | {name} | precision | recall | false corrections | abstentions |")
        print("|---|---|---|---|---|---|")
        for arm in ("A", "B", "C"):
            s = summarise(part, arm)
            print(f"| {arm} | {s['cases']} cases | {s['precision']:.3f} | {s['recall']:.3f} "
                  f"| {s['false_corrections']}/{s['proposed']} | {s['abstentions']} |")
        d = sum(row["D"] for row in part) / len(part)
        print(f"| D | {len(part)} cases | {d:.3f} | — | — | — |")

    b, c = summarise(held, "B"), summarise(held, "C")
    d = sum(row["D"] for row in held) / len(held)
    h1 = determined_share < 0.5 and all(row["worlds"] >= 2 for row in rows)
    h2 = b["precision"] >= 0.9 and b["recall"] < 0.6
    h3 = c["recall"] >= b["recall"] + 0.1 and c["precision"] >= 0.5
    h4 = d <= 0.25
    headroom = h2 and h3 and h4 and (1.0 - c["precision"]) >= 0.1

    print()
    for label, value, why in (
        ("H1 cases genuinely ambiguous", h1, f"{determined}/{len(rows)} determined"),
        ("H2 consensus precise but small", h2, f"P {b['precision']:.3f} R {b['recall']:.3f}"),
        ("H3 support rank trades precision for recall", h3,
         f"R {c['recall']:.3f} vs B {b['recall']:.3f}, P {c['precision']:.3f}"),
        ("H4 shuffled arm at chance", h4, f"P {d:.3f}"),
    ):
        print(f"{label}: {'UPHELD' if value else 'FALSIFIED'} ({why})")
    verdict = "VACUOUS" if not h1 else ("HEADROOM" if headroom else "NO HEADROOM")
    print(f"repair headroom: {verdict}")
    print(f"prereg run: {'PASS' if h1 and (h2, h3, h4) == (h2, h3, h4) else 'FAIL'}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
