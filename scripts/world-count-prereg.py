"""R-P1.77: why active selection resolved 8/8 there and nothing here.

Frozen card: docs/2026-11-28-PREREG-R-P1.77-world-count.md, pushed at `9ea3549`
before this file existed. Claim `a6f8533c-b57f-4dd5-adde-2aaa1707a9bb`.

E6 has said "the missing ingredient is information the surviving-world counts do
not carry" through five cards, while R-P1.47 resolved 8/8 in the same lane. The
difference this card tests is the size of the surviving set: one query resolves
when it partitions that set completely, and contributes nothing when it does not.

Two generators, both already in the repo's idiom: `SIZE = 6` (three missing edges,
958 worlds at n=4 — the repair regime) and `SIZE = 3` (one missing edge, 12-24
worlds — near R-P1.47's regime).
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pa = _load("priced63", ROOT / "scripts/priced-acquisition-prereg.py")
sp = _load("soft64", ROOT / "scripts/soft-posterior-prereg.py")
pool67 = _load("pool67", ROOT / "scripts/pool-size-prereg.py")

CLAIM = "a6f8533c-b57f-4dd5-adde-2aaa1707a9bb"
ENTITIES = (3, 4)
SIZES = (3, 6)          # true edges; SIZE-1 = missing
OBSERVED_OF = {3: 2, 6: 3}
HELDOUT = 120
DEV = 12
SENSOR_TPR, SENSOR_FPR = 0.8, 0.2
PROPOSE = 3


def build(seed: int, n: int, size: int):
    pool = pool67.admissible(n)
    rng = random.Random(seed)
    for _ in range(4000):
        truth = set(rng.sample(pool, size))
        if pool67.within_caps(truth):
            break
    else:
        return None
    observed = set(rng.sample(sorted(truth), OBSERVED_OF[size]))
    missing = size - len(observed)
    rest = [e for e in pool if e not in observed]
    worlds = [frozenset(observed | set(c))
              for c in itertools.combinations(rest, missing)
              if pool67.within_caps(observed | set(c))]
    if not worlds:
        return None
    nodes = [f"node:{i}" for i in range(n)]
    ports = [f"port:{i}" for i in range(n)]
    return {"seed": seed, "n": n, "size": size, "truth": truth,
            "observed": observed, "worlds": worlds, "entities": nodes + ports}


def decoder_pool(state) -> set:
    from psychopomp.graph_patch import decode
    from psychopomp.physis_snapshot import Edge, Snapshot
    snap = Snapshot(entities={e: e.split(":")[0] for e in state["entities"]},
                    edges=[Edge(*e) for e in sorted(state["observed"])])
    plan = decode(snap, [set(w) for w in state["worlds"]])
    return {tuple(op[k] for k in ("source", "predicate", "target"))
            for op in plan["operations"] if op["op"] == "propose_edge"}


def best_edge(worlds, pool):
    """Highest expected-information edge in the pool, by world split."""
    n = len(worlds)
    best, choice = -1.0, None
    for edge in sorted(pool):
        split = sum(1 for w in worlds if edge in w)
        if split == 0 or split == n:
            continue
        p = split / n
        gain = -(p * math.log(p) + (1 - p) * math.log(1 - p))
        if gain > best:
            best, choice = gain, edge
    return choice


def run_cell(n: int, size: int, arm: str, seeds, shuffle: bool = False) -> dict:
    hits = total = 0
    prec = []
    before, after = [], []
    for seed in seeds:
        state = build(seed, n, size)
        if state is None:
            continue
        pool = decoder_pool(state)
        if not pool:
            continue
        worlds = list(state["worlds"])
        before.append(len(worlds))
        if arm == "active":
            edge = best_edge(worlds, pool)
            if edge is None:
                continue
            present = edge in state["truth"]
            if shuffle:
                present = random.Random(seed).random() < 0.5
            reading = random.Random(seed * 7919 + 3).random() < (
                SENSOR_TPR if present else SENSOR_FPR)
            filtered = [w for w in worlds if (edge in w) == reading]
            if filtered:
                worlds = filtered
        after.append(len(worlds))
        masses = pa.masses(worlds, pool) if False else sp.Posterior(worlds).masses(pool)
        proposal = pa.top_k(masses)
        c = len(proposal & state["truth"])
        f = len(proposal - state["truth"])
        hits += c
        total += c + f
        prec.append(c / (c + f) if c + f else 0.0)
    return {"n": n, "size": size, "arm": arm, "shuffle": shuffle,
            "hits": hits, "proposed": total,
            "precision": hits / total if total else None,
            "mean_precision": statistics.fmean(prec) if prec else None,
            "mean_worlds_before": statistics.fmean(before) if before else None,
            "mean_worlds_after": statistics.fmean(after) if after else None,
            "cases": len(prec)}


def main() -> int:
    held = range(DEV, DEV + HELDOUT)
    cells = {}
    for n in ENTITIES:
        for size in SIZES:
            for arm in ("passive", "active", "shuffle"):
                cells[f"{n}@{size}@{arm}"] = run_cell(
                    n, size, arm, held, shuffle=(arm == "shuffle"))

    def delta(n, size):
        a = cells[f"{n}@{size}@active"]["precision"]
        p = cells[f"{n}@{size}@passive"]["precision"]
        return None if a is None or p is None else a - p

    # P1: the anchor behaves in both regimes.
    big_deltas = [delta(n, 6) for n in ENTITIES if delta(n, 6) is not None]
    small_deltas = [delta(n, 3) for n in ENTITIES if delta(n, 3) is not None]
    p1 = (big_deltas and all(d < 0.10 for d in big_deltas)
          and small_deltas and any(d >= 0.10 for d in small_deltas))

    # P2: resolution is a threshold on worlds after the query.
    resolving = [cells[k] for k in cells if "@active@" in k or k.endswith("@active")]
    p2 = None
    if resolving:
        low = [c for c in resolving if (c["mean_worlds_after"] or 99) <= 4]
        high = [c for c in resolving if (c["mean_worlds_after"] or 0) > 4]
        low_ok = all((c["precision"] or 0) > (cells[f'{c["n"]}@{c["size"]}@passive']["precision"] or 0)
                     for c in low)
        high_ok = all((c["precision"] or 0) <= 1.001 * (cells[f'{c["n"]}@{c["size"]}@passive']["precision"] or 0) + 0.10
                      for c in high)
        p2 = low_ok and high_ok

    # P3: precision, not just hits, improves on the small fixture.
    p3 = any((cells[f"{n}@3@active"]["mean_precision"] or 0)
             > (cells[f"{n}@3@passive"]["mean_precision"] or 0) for n in ENTITIES)

    # P4: the shuffled probe never beats passive.
    p4 = all((cells[f"{n}@{size}@shuffle"]["precision"] or 0)
             <= (cells[f"{n}@{size}@passive"]["precision"] or 0) + 1e-9
             for n in ENTITIES for size in SIZES)

    # P5: the arithmetic predicts which cells resolve.
    predicted, measured = [], []
    for n in ENTITIES:
        for size in SIZES:
            c = cells[f"{n}@{size}@active"]
            if None in (c["mean_worlds_before"], c["mean_worlds_after"]):
                continue
            bits = (math.log2(c["mean_worlds_before"])
                    - math.log2(max(1.0, c["mean_worlds_after"])))
            predicted.append(bits >= math.log2(PROPOSE))
            measured.append((delta(n, size) or 0) >= 0.10)
    p5 = predicted == measured and len(predicted) > 0

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", bool(p1)), ("P2", bool(p2)), ("P3", p3),
                         ("P4", p4), ("P5", p5))
    )
    receipt = {
        "card": "R-P1.77", "claim_id": CLAIM,
        "prereg": "docs/2026-11-28-PREREG-R-P1.77-world-count.md",
        "command": "python3 scripts/world-count-prereg.py",
        "entities": list(ENTITIES), "sizes": list(SIZES),
        "heldout": HELDOUT, "cells": cells,
        "deltas": {f"{n}@{s}": delta(n, s) for n in ENTITIES for s in SIZES},
        "arithmetic": {"predicted": predicted, "measured": measured},
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/world-count-20261128"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "deltas": receipt["deltas"],
                      "worlds": {k: [v["mean_worlds_before"], v["mean_worlds_after"]]
                                 for k, v in cells.items() if k.endswith("@active")},
                      "precision": {k: v["precision"] for k, v in cells.items()}},
                     indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
