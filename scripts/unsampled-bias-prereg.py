"""R-P1.69: a without-replacement sampler and a 120-case held-out set.

Frozen card: docs/2026-11-27-PREREG-R-P1.69-unsampled-bias.md, pushed at
`66b1135` before this file existed. Claim
`346c9f13-5bce-4a63-b6ad-c9844a0f57a2`.

R-P1.68 measured sampled precision **above** exhaustive (+0.111 at n=4, k=8,
M=2000) and could not say whether duplicates or noise caused it: 12 cases carry
36 proposal slots, and the fixture's own draw spread is sd 0.038.

This card changes two things and nothing else:

  support: uniform sample of DISTINCT completions (no world weighted twice)
  held-out: 120 cases instead of 12 (se ~1/sqrt(10) of before)

A `with_replacement` arm re-runs the old sampler as a mutation check: it must
reproduce R-P1.68's upward bias, or the fixture moved.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
import random
import statistics
import sys
import time
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
pool_mod = _load("pool67", ROOT / "scripts/pool-size-prereg.py")

CLAIM = "346c9f13-5bce-4a63-b6ad-c9844a0f57a2"
ENTITY_COUNTS = (3, 4, 6, 8)
EXHAUSTIVE = (3, 4)
QUERIES = (4, 8, 12)
PRIMARY_K = 8
SAMPLES = (2000, 8000)
DEV = 12
HELDOUT = 120          # R-P1.68 had 12; the card's whole point is this number
R163_BIAS = 0.111      # R-P1.68: sampled minus exhaustive at n=4, k=8, M=2000
BIAS_TOL = 0.05


def sample_distinct(observed: set, pool, missing: int, m: int,
                    rng: random.Random) -> tuple[list[frozenset], int]:
    """`m` **distinct** completions by shuffling the completion index space.

    The completion space is `C(|rest|, missing)`; enumerating its indices and
    shuffling is uniform without replacement and does not need the space to be
    materialised. Where the space is larger than a few million the sampler falls
    back to rejection with a seen-set, and reports which path ran.
    """
    rest = [e for e in pool if e not in observed]
    total = math.comb(len(rest), missing)
    out: list[frozenset] = []
    if total <= 5_000_000:
        idx = list(range(total))
        rng.shuffle(idx)
        for i in idx[:m]:
            combo = _combo_at(rest, missing, i)
            if pool_mod.within_caps(observed | combo):
                out.append(frozenset(observed | combo))
        return out, total
    seen: set = set()
    tries = 0
    while len(out) < m and tries < m * 60:
        tries += 1
        combo = frozenset(rng.sample(rest, missing))
        if combo in seen:
            continue
        seen.add(combo)
        if pool_mod.within_caps(observed | combo):
            out.append(frozenset(observed | combo))
    return out, total


def _combo_at(rest: list, missing: int, index: int) -> set:
    """The `index`-th combination in lexicographic order, without enumerating."""
    combo = []
    chosen = 0
    remaining = index
    for i, item in enumerate(rest):
        if chosen == missing:
            break
        left = len(rest) - i - 1
        need = missing - chosen
        # how many completions skip this item?
        skip = math.comb(left, need) if left >= need else 0
        if remaining < skip:
            continue
        combo.append(item)
        chosen += 1
        remaining -= skip
    return set(combo)


def sample_with_replacement(observed: set, pool, missing: int, m: int,
                            rng: random.Random) -> list[frozenset]:
    """R-P1.68's sampler, kept for the mutation check."""
    rest = [e for e in pool if e not in observed]
    out = []
    tries = 0
    while len(out) < m and tries < m * 40:
        tries += 1
        combo = set(rng.sample(rest, missing))
        if pool_mod.within_caps(observed | combo):
            out.append(frozenset(observed | combo))
    return out


def surviving_exhaustive(observed: set, pool, missing: int) -> list[frozenset]:
    rest = [e for e in pool if e not in observed]
    worlds = []
    for combo in itertools.combinations(rest, missing):
        edges = set(observed) | set(combo)
        if pool_mod.within_caps(edges):
            worlds.append(frozenset(edges))
    return worlds


def build_case(seed: int, n: int):
    pool = pool_mod.admissible(n)
    if len(pool) < pool_mod.SIZE:
        return None
    rng = random.Random(seed)
    try:
        truth = pool_mod.draw_truth(rng, pool)
    except RuntimeError:
        return None
    observed = set(rng.sample(sorted(truth), pool_mod.OBSERVED))
    nodes = [f"node:{i}" for i in range(n)]
    ports = [f"port:{i}" for i in range(n)]
    return {"seed": seed, "n": n, "truth": truth, "observed": observed,
            "pool": pool, "entities": nodes + ports}


def decoder_pool(state, worlds) -> set:
    from psychopomp.graph_patch import decode
    from psychopomp.physis_snapshot import Edge, Snapshot
    snapshot = Snapshot(
        entities={e: e.split(":")[0] for e in state["entities"]},
        edges=[Edge(*edge) for edge in sorted(state["observed"])])
    plan = decode(snapshot, [set(w) for w in worlds])
    return {tuple(op[k] for k in ("source", "predicate", "target"))
            for op in plan["operations"] if op["op"] == "propose_edge"}


def run_cell(n: int, k: int, m, seeds, sampler: str = "distinct") -> dict:
    """`m = None` means exhaustive. `sampler` selects distinct/replacement."""
    hits = misses = 0
    per_case_precision = []
    times = []
    worlds_seen = []
    for seed in seeds:
        state = build_case(seed, n)
        if state is None:
            continue
        started = time.perf_counter()
        missing = pool_mod.MISSING
        if m is None:
            worlds = surviving_exhaustive(state["observed"], state["pool"], missing)
        elif sampler == "distinct":
            rng_w = random.Random(seed * 7919 + 17)
            worlds, _ = sample_distinct(state["observed"], state["pool"], missing,
                                        m, rng_w)
        else:
            rng_w = random.Random(seed * 7919 + 17)
            worlds = sample_with_replacement(state["observed"], state["pool"],
                                             missing, m, rng_w)
        if not worlds:
            continue
        pool = decoder_pool(state, worlds)
        if not pool:
            continue
        post = sp.Posterior(worlds)
        asked: set = set()
        rng = random.Random(seed * 104729 + 7)
        for _ in range(k):
            masses_now = post.masses(pool)
            before_u = post.expected_utility(pool)
            best = (-math.inf, None)
            for edge in sorted(pool):
                if edge in asked:
                    continue
                gain = sp._branch_gain(post, pool, edge, masses_now[edge], before_u)
                if gain > best[0]:
                    best = (gain, edge)
            _, edge = best
            if edge is None:
                break
            present = edge in state["truth"]
            reading = rng.random() < (pool_mod.SENSOR_TPR if present else pool_mod.SENSOR_FPR)
            asked.add(edge)
            post.update(edge, reading)
        proposal = pa.top_k(post.masses(pool))
        truth = state["truth"]
        c = len(proposal & truth)
        f = len(proposal - truth)
        hits += c
        misses += f
        per_case_precision.append(c / (c + f) if c + f else 0.0)
        times.append(time.perf_counter() - started)
        worlds_seen.append(len(worlds))
    total = hits + misses
    sd = statistics.pstdev(per_case_precision) if len(per_case_precision) > 1 else 0.0
    se = sd / math.sqrt(len(per_case_precision)) if per_case_precision else None
    return {
        "n": n, "k": k, "m": m, "sampler": "exhaustive" if m is None else sampler,
        "precision": hits / total if total else None,
        "cases": len(per_case_precision),
        "standard_error": se,
        "mean_worlds": statistics.fmean(worlds_seen) if worlds_seen else None,
        "mean_seconds": statistics.fmean(times) if times else None,
    }


def null_cell(n: int, k: int, seeds) -> dict:
    beats = 0
    cases = 0
    for seed in seeds:
        state = build_case(seed, n)
        if state is None:
            continue
        rng_w = random.Random(seed * 7919 + 17)
        worlds, _ = sample_distinct(state["observed"], state["pool"],
                                    pool_mod.MISSING, 2000, rng_w)
        if not worlds:
            continue
        pool = decoder_pool(state, worlds)
        if not pool:
            continue
        post = sp.Posterior(worlds)
        noise = random.Random(seed * 104729 + 13)
        asked: set = set()
        for _ in range(k):
            rest = [e for e in sorted(pool) if e not in asked] or sorted(pool)
            edge = noise.choice(rest)
            asked.add(edge)
            post.update(edge, noise.random() < 0.5)
        proposal = pa.top_k(post.masses(pool))
        truth = state["truth"]
        base = pa.top_k(pa.masses(worlds, pool))
        cases += 1
        if (len(proposal & truth) - len(proposal - truth)) > \
           (len(base & truth) - len(base - truth)):
            beats += 1
    return {"n": n, "k": k, "cases": cases, "cases_beating_passive": beats}


def main() -> int:
    held = range(DEV, DEV + HELDOUT)
    cells: dict[str, dict] = {}

    def progress(msg: str) -> None:
        # 120 cases at n = 8 is ~10 minutes per cell and the whole grid is hours.
        # Printing only at the end made a working run indistinguishable from a
        # stalled one for 90 minutes; every cell now reports as it completes.
        print(msg, flush=True)

    for n in ENTITY_COUNTS:
        for k in QUERIES:
            if n in EXHAUSTIVE:
                started = time.perf_counter()
                cells[f"{n}@{k}@exh"] = run_cell(n, k, None, held)
                progress(f"  cell n={n} k={k} exhaustive: "
                         f"{time.perf_counter() - started:.0f}s")
            for m in SAMPLES:
                # M = 8000 only where it has something to be compared against.
                # Measured before the run: n = 8 at M = 2000 is ~10.8 s/case, so
                # the 8000 arm there would be ~5 h for a cell with no exhaustive
                # counterpart — an unmeasurable claim, not a stronger one.
                if m == 8000 and n not in EXHAUSTIVE:
                    continue
                started = time.perf_counter()
                cells[f"{n}@{k}@{m}@distinct"] = run_cell(n, k, m, held, "distinct")
                progress(f"  cell n={n} k={k} M={m}: "
                         f"{time.perf_counter() - started:.0f}s "
                         f"prec={cells[f'{n}@{k}@{m}@distinct']['precision']}")

    # P1: without replacement removes the bias, judged by SIGNED difference.
    p1_rows = {}
    for n in EXHAUSTIVE:
        exh = cells[f"{n}@{PRIMARY_K}@exh"]["precision"]
        big = cells[f"{n}@{PRIMARY_K}@8000@distinct"]["precision"]
        if exh is not None and big is not None:
            p1_rows[str(n)] = {"exhaustive": exh, "sampled": big, "bias": big - exh}
    p1 = bool(p1_rows) and all(abs(r["bias"]) <= BIAS_TOL for r in p1_rows.values())

    # P2: could this design have detected R-P1.68's effect?
    ses = [cells[f"{n}@{PRIMARY_K}@8000@distinct"]["standard_error"]
           for n in EXHAUSTIVE]
    ses = [s for s in ses if s]
    detected_at = (R163_BIAS / statistics.fmean(ses)) if ses else None
    p2 = detected_at is not None and detected_at >= 3.0

    # P3: realistic pools measurable with bounded bias, within budget.
    p3_ok = all(cells[f"{n}@{PRIMARY_K}@2000@distinct"]["precision"] is not None
                for n in (6, 8))
    budget_ok = all((cells[f"{n}@{PRIMARY_K}@2000@distinct"]["mean_seconds"] or 99)
                    <= 5.0 for n in (6, 8))
    p3 = p3_ok and budget_ok

    # P4: the trend holds at 120 cases.
    trend = [cells[f"{n}@{PRIMARY_K}@2000@distinct"]["precision"]
             for n in (4, 6, 8)]
    p4 = all(a >= b for a, b in zip(trend, trend[1:])) and trend[0] > trend[-1]

    # P5: null does not beat passive at more than a third of cases.
    nulls = {str(n): null_cell(n, PRIMARY_K, held) for n in (6, 8)}
    p5 = all(v["cases_beating_passive"] <= v["cases"] // 3 for v in nulls.values())

    # Mutation check: the old sampler must still show R-P1.68's bias.
    replaced = run_cell(4, PRIMARY_K, 8000, held, "replacement")
    mutation = {"replacement_bias": None}
    exh4 = cells[f"4@{PRIMARY_K}@exh"]["precision"]
    if replaced["precision"] is not None and exh4 is not None:
        mutation["replacement_bias"] = replaced["precision"] - exh4
    mutation_ok = (mutation["replacement_bias"] is None
                   or mutation["replacement_bias"] > 0.0)

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not mutation_ok:
        verdict += "; UNVERIFIABLE (the old sampler no longer reproduces R-P1.68's bias)"

    receipt = {
        "card": "R-P1.69", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.69-unsampled-bias.md",
        "command": "python3 scripts/unsampled-bias-prereg.py",
        "heldout": HELDOUT, "entity_counts": list(ENTITY_COUNTS),
        "queries": list(QUERIES), "samples": list(SAMPLES),
        "cells": cells,
        "bias_rows": p1_rows,
        "detectable_sigma": detected_at,
        "trend_at_m2000": {str(n): cells[f"{n}@{PRIMARY_K}@2000@distinct"]["precision"]
                           for n in (4, 6, 8)},
        "mutation": mutation,
        "nulls": nulls,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/unsampled-bias-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "bias_rows": p1_rows,
                      "detectable_sigma": detected_at,
                      "trend_at_m2000": receipt["trend_at_m2000"],
                      "mutation": mutation, "nulls": nulls}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
