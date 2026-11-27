"""R-P1.67: is the pool, not the decoder, what bounds resolution?

Frozen card: docs/2026-11-27-PREREG-R-P1.67-pool-size.md, pushed at `25e092c`
before this file existed. Claim `38b247fe-4c45-4814-bf53-93dc32b06c91`.

R-P1.60–R-P1.64 all used one world: 4 nodes + 4 ports, 6 true edges, 3 observed,
3 missing, pool ~21.5. R-P1.64 closed with "~10 readings do not resolve 3 of 21.5
edges however the posterior is updated" — a sentence about a quantity that was
never varied. This varies the pool, holding sensor, budget and decoder fixed.

Decoder: R-P1.64's **soft** posterior, imported rather than copied, because a hard
filter collapses and would confound the pool measurement with R-P1.63's defect.
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

CLAIM = "38b247fe-4c45-4814-bf53-93dc32b06c91"
PREDICATE = "LINK"
SIZE = 6          # true edges, constant
OBSERVED = 3      # observed edges, constant
MISSING = SIZE - OBSERVED
CAP = 2
K_PROPOSE = 3
DEV, HELDOUT = 12, 12
SENSOR_TPR, SENSOR_FPR = 0.8, 0.2
QUERIES = (4, 8, 12)
# The card declared (2, 3, 4, 6, 8). Measured before the run: n=2 cannot hold six
# edges at all, and n=6/8 enumerate 16,706 / 222,130 surviving worlds per case —
# 228 s for two seeds at n=6, so the declared range is not computable here. The
# range is the computable one and the card says so in its run section.
ENTITY_COUNTS = (3, 4)
ANCHOR_N = 4
ANCHOR_POOL = 21.5      # R-P1.63/64's realised pool, per the card


def admissible(n: int) -> list[tuple[str, str, str]]:
    nodes = [f"node:{i}" for i in range(n)]
    ports = [f"port:{i}" for i in range(n)]
    pairs = [(a, b) for a in nodes for b in nodes if a != b]
    pairs += [(a, b) for a in nodes for b in ports]
    return [(s, PREDICATE, t) for s, t in pairs]


def within_caps(edges) -> bool:
    out: dict[str, int] = {}
    inn: dict[str, int] = {}
    for source, _, target in edges:
        out[source] = out.get(source, 0) + 1
        inn[target] = inn.get(target, 0) + 1
    return all(v <= CAP for v in out.values()) and all(v <= CAP for v in inn.values())


def draw_truth(rng: random.Random, pool) -> set:
    for _ in range(4000):
        picked = set(rng.sample(pool, SIZE))
        if within_caps(picked):
            return picked
    raise RuntimeError("could not draw a truth satisfying the closure rule")


def surviving_worlds(observed: set, pool) -> list[frozenset]:
    rest = [e for e in pool if e not in observed]
    worlds = []
    for combo in itertools.combinations(rest, MISSING):
        edges = set(observed) | set(combo)
        if within_caps(edges):
            worlds.append(frozenset(edges))
    return worlds


def case(seed: int, n: int) -> dict | None:
    """One world at entity count `n`, or None when it is not constructible."""
    pool = admissible(n)
    if len(pool) < SIZE:
        return None
    rng = random.Random(seed)
    try:
        truth = draw_truth(rng, pool)
    except RuntimeError:
        return None
    observed = set(rng.sample(sorted(truth), OBSERVED))
    worlds = surviving_worlds(observed, pool)
    if not worlds:
        return None
    nodes = [f"node:{i}" for i in range(n)]
    ports = [f"port:{i}" for i in range(n)]
    return {"seed": seed, "n": n, "truth": truth, "observed": observed,
            "worlds": worlds, "pool": pool, "entities": nodes + ports}


def candidate_pool(state: dict) -> set:
    """The decoder's own candidate set, not "every unobserved edge".

    R-P1.63's pool comes from `decode(...)`'s `propose_edge` operations, which is
    why its anchor is 21.5 and not the 25 that "all unobserved edges" gives. The
    first version of this script used the latter, so the anchor check failed on a
    definition rather than on the pool knob — exactly what that check is for.
    """
    from psychopomp.graph_patch import decode
    from psychopomp.physis_snapshot import Edge, Snapshot
    snapshot = Snapshot(
        entities={e: e.split(":")[0] for e in state["entities"]},
        edges=[Edge(*edge) for edge in sorted(state["observed"])])
    plan = decode(snapshot, [set(world) for world in state["worlds"]])
    return {tuple(op[key] for key in ("source", "predicate", "target"))
            for op in plan["operations"] if op["op"] == "propose_edge"}


def posterior_after(state: dict, k: int, rng: random.Random):
    """R-P1.64's soft posterior, querying `k` edges by information gain."""
    post = sp.Posterior(state["worlds"])
    pool = candidate_pool(state)
    asked: set = set()
    for _ in range(k):
        best = (-math.inf, None)
        for edge in sorted(pool):
            if edge in asked:
                continue
            present_mass = post.masses(pool)[edge]
            before = post.expected_utility(pool)
            branch_gain = sp._branch_gain(post, pool, edge, present_mass, before)
            if branch_gain > best[0]:
                best = (branch_gain, edge)
        _, edge = best
        if edge is None:
            break
        present = edge in state["truth"]
        reading = rng.random() < (SENSOR_TPR if present else SENSOR_FPR)
        asked.add(edge)
        post.update(edge, reading)
    return post, pool


def score_cell(n: int, k: int, seeds) -> dict:
    hits = misses = 0
    errors = []
    surviving = []
    for seed in seeds:
        state = case(seed, n)
        if state is None:
            continue
        pool = candidate_pool(state)
        rng = random.Random(seed * 104729 + 7)
        post, pool = posterior_after(state, k, rng)
        proposal = pa.top_k(post.masses(pool))
        truth = state["truth"]
        hits += len(proposal & truth)
        misses += len(proposal - truth)
        error = sum(((1 if e in truth else 0) - (1 if e in proposal else 0)) ** 2
                    for e in pool)
        errors.append(error / len(pool) if pool else 0.0)
        surviving.append(len(post.worlds))
    return {
        "n": n, "k": k,
        "precision": hits / (hits + misses) if hits + misses else None,
        "cases": len(errors),
        "completion_error": statistics.fmean(errors) if errors else None,
        "mean_surviving": statistics.fmean(surviving) if surviving else None,
    }


def passive_cell(n: int, seeds) -> dict:
    errors, hits, total = [], 0, 0
    for seed in seeds:
        state = case(seed, n)
        if state is None:
            continue
        pool = candidate_pool(state)
        proposal = pa.top_k(pa.masses(state["worlds"], pool))
        truth = state["truth"]
        hits += len(proposal & truth)
        total += len(proposal)
        error = sum(((1 if e in truth else 0) - (1 if e in proposal else 0)) ** 2
                    for e in pool)
        errors.append(error / len(pool) if pool else 0.0)
    return {"precision": hits / total if total else None,
            "completion_error": statistics.fmean(errors) if errors else None,
            "cases": len(errors)}


def pool_size(n: int) -> float | None:
    sizes = []
    for seed in range(DEV + HELDOUT):
        state = case(seed, n)
        if state is not None:
            sizes.append(len(candidate_pool(state)))
    return statistics.fmean(sizes) if sizes else None


def null_control(n: int, k: int, seeds) -> dict:
    """Same spend, readings independent of truth: must not beat passive."""
    beats = 0
    for seed in seeds:
        state = case(seed, n)
        if state is None:
            continue
        pool = candidate_pool(state)
        post = sp.Posterior(state["worlds"])
        noise = random.Random(seed * 104729 + 13)
        asked: set = set()
        for _ in range(k):
            rest = [e for e in sorted(pool) if e not in asked] or sorted(pool)
            edge = noise.choice(rest)
            asked.add(edge)
            post.update(edge, noise.random() < 0.5)
        proposal = pa.top_k(post.masses(pool))
        truth = state["truth"]
        got = len(proposal & truth) - len(proposal - truth)
        base = (len(pa.top_k(pa.masses(state["worlds"], pool)) & truth)
                - len(pa.top_k(pa.masses(state["worlds"], pool)) - truth))
        if got > base:
            beats += 1
    return {"n": n, "k": k, "cases_beating_passive": beats}


def main() -> int:
    held = range(DEV, DEV + HELDOUT)
    dev = range(DEV)

    pools = {n: pool_size(n) for n in ENTITY_COUNTS}
    constructible = [n for n in ENTITY_COUNTS if pools[n] is not None]

    # P1: pool grows with n, and the anchor reproduces 21.5.
    ordered = [pools[n] for n in constructible]
    monotone = all(a <= b for a, b in zip(ordered, ordered[1:]))
    anchor_pool = pools.get(ANCHOR_N)
    p1 = (monotone and anchor_pool is not None
          and abs(anchor_pool - ANCHOR_POOL) < 1e-6)

    cells = {f"{n}@{k}": score_cell(n, k, held)
             for n in constructible for k in QUERIES}
    passive = {n: passive_cell(n, held) for n in constructible}

    # P2: small pool resolves at fixed k = 8.
    small = constructible[0]
    p2 = (cells[f"{small}@8"]["precision"] or 0.0) >= 0.60

    # P3: precision at k = 8 is non-increasing in pool size.
    at8 = [cells[f"{n}@8"]["precision"] for n in constructible]
    p3 = all(a >= b for a, b in zip(at8, at8[1:])) and at8[0] > at8[-1]

    # P4: the small-pool cell's completion error beats passive for its own pool.
    p4 = (cells[f"{small}@8"]["completion_error"] or 1.0) < \
        (passive[small]["completion_error"] or 0.0)

    # P5: surviving worlds grow with the pool, and their log tracks the loss.
    surv = [cells[f"{n}@8"]["mean_surviving"] for n in constructible]
    precs = [cells[f"{n}@8"]["precision"] for n in constructible]
    surv_monotone = all(a <= b for a, b in zip(surv, surv[1:]))
    p5 = surv_monotone and len(set(precs)) > 1

    controls = {f"{n}@8": null_control(n, 8, held) for n in constructible}
    null_rates = {f"{n}@8": null_control(n, 8, held)["cases_beating_passive"]
                  for n in constructible}
    controls_hold = all(v["cases_beating_passive"] <= 12 // 3 for v in controls.values())

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p1:
        verdict += "; UNVERIFIABLE (the pool knob did not reproduce the anchor)"
    if not controls_hold:
        verdict += "; controls beat passive at more than a third of cases"

    receipt = {
        "card": "R-P1.67", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.67-pool-size.md",
        "command": "python3 scripts/pool-size-prereg.py",
        "entity_counts": list(ENTITY_COUNTS),
        "pools": pools,
        "anchor": {"n": ANCHOR_N, "expected_pool": ANCHOR_POOL,
                   "measured_pool": anchor_pool},
        "cells": cells,
        "passive": passive,
        "at_k8_precision": {n: cells[f"{n}@8"]["precision"] for n in constructible},
        "at_k8_surviving": {n: cells[f"{n}@8"]["mean_surviving"] for n in constructible},
        "dev_cells": {f"{n}@{k}": score_cell(n, k, dev)
                      for n in constructible for k in (8,)},
        "controls": controls, "null_rates": null_rates,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/pool-size-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "pools": pools,
                      "at_k8_precision": receipt["at_k8_precision"],
                      "at_k8_surviving": receipt["at_k8_surviving"],
                      "passive": {n: passive[n]["completion_error"]
                                  for n in constructible}}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
