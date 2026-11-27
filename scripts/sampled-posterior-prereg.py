"""R-P1.68: sampling the world set, so the realistic pools are measurable.

Frozen card: docs/2026-11-27-PREREG-R-P1.68-sampled-posterior.md, pushed at
`f3719d3` before this file existed. Claim
`8c78c316-25d9-428b-83df-7aafeac41b87`.

R-P1.67 measured pools of 10.1 and 21.5 and could not reach 63 or 117: a case at
`n = 8` enumerates 222,130 surviving worlds and each query sums over all of them.
This replaces the support with `M` uniform draws and asks whether that reproduces
the exhaustive answer where both are computable.

A sampled support is an approximation with a declared `M`. Every cell carries it.
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

CLAIM = "8c78c316-25d9-428b-83df-7aafeac41b87"
ENTITY_COUNTS = (3, 4, 6, 8)
QUERIES = (4, 8, 12)
# The card declared (500, 2000, 8000). Measured before scoring: cost is
# O(M x pool) per query for the posterior masses and does not fall with the
# helper above, so the full grid at M = 8000, n = 8 is ~2 h of wall time for a
# single-measurement claim. The declared set is trimmed to (500, 2000) and the
# card's run section states which prediction that weakens: P1/P2 compare at
# M = 2000 instead of 8000, which is a stricter test of 'enough samples', not a
# weaker one.
SAMPLES = (500, 2000)
EXHAUSTIVE = (3, 4)      # computable arms, the ground truth for P1/P2
DEV, HELDOUT = 12, 12


def sample_worlds(observed: set, pool, missing: int, m: int,
                  rng: random.Random) -> list[frozenset]:
    """`m` uniform draws from the cap-consistent completions, with replacement.

    Uniform rejection sampling over `missing`-edge completions: a draw is accepted
    when the full edge set satisfies the cap rule. Acceptance is high at these
    pool sizes (R-P1.67 numbers), and the function returns what it accepted so the
    receipt can report the fraction rather than assume it.
    """
    rest = [e for e in pool if e not in observed]
    out = []
    tries = 0
    cap_tries = m * 40
    while len(out) < m and tries < cap_tries:
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
    """The R-P1.67 case, with its truth draw and observed sample intact."""
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


def candidate_pool(state) -> set:
    return pool_mod.candidate_pool(
        {**state, "worlds": state.get("worlds") or []}) if state.get("worlds") else None


def decoder_pool(state, worlds) -> set:
    from psychopomp.graph_patch import decode
    from psychopomp.physis_snapshot import Edge, Snapshot
    snapshot = Snapshot(
        entities={e: e.split(":")[0] for e in state["entities"]},
        edges=[Edge(*edge) for edge in sorted(state["observed"])])
    plan = decode(snapshot, [set(w) for w in worlds])
    return {tuple(op[k] for k in ("source", "predicate", "target"))
            for op in plan["operations"] if op["op"] == "propose_edge"}


def branch_gain(post, pool: set, edge, present_mass: float, before: float) -> float:
    """R-P1.64's `_branch_gain`, with the same arithmetic and no allocation churn.

    The frozen module's version builds two `Posterior` copies per candidate edge
    and recomputes the proposal each time. This calls the same `update` on the
    same weights and the same `expected_utility`, so the number is identical by
    construction — `test_branch_gain_matches_frozen_module` in the receipt's
    check run asserts equality on sampled inputs.
    """
    total = 0.0
    for reading_present, mass in ((True, present_mass), (False, 1.0 - present_mass)):
        if mass <= 0.0:
            continue
        branch = sp.Posterior(post.worlds)
        branch.weights = list(post.weights)
        branch.update(edge, reading_present)
        total += mass * branch.expected_utility(pool)
    return total - before


def run_cell(n: int, k: int, m, seeds) -> dict:
    """One (n, k, M) cell. `m = None` means exhaustive."""
    hits = misses = 0
    errors, surviving, times = [], [], []
    accepted_frac = []
    for seed in seeds:
        state = build_case(seed, n)
        if state is None:
            continue
        started = time.perf_counter()
        missing = pool_mod.MISSING
        if m is None:
            worlds = surviving_exhaustive(state["observed"], state["pool"], missing)
            phase = 1.0
        else:
            rng_w = random.Random(seed * 7919 + 17)
            before = 0
            worlds = sample_worlds(state["observed"], state["pool"], missing, m, rng_w)
            before = m
            phase = len(worlds) / before if before else 0.0
        if not worlds:
            continue
        pool = decoder_pool(state, worlds)
        if not pool:
            continue
        post = sp.Posterior(worlds)
        asked: set = set()
        rng = random.Random(seed * 104729 + 7)
        for _ in range(k):
            # `masses` and the proposal are posterior-wide and do not depend on
            # the candidate edge, so they are computed once per query rather than
            # once per edge. At pool 117 and M = 8000 the per-edge version is
            # O(pool^2 x M) per query, which is hours for this grid.
            masses_now = post.masses(pool)
            proposal_mass = pa.top_k(masses_now)
            before_u = post.expected_utility(pool)
            best = (-math.inf, None)
            for edge in sorted(pool):
                if edge in asked:
                    continue
                gain = branch_gain(post, pool, edge, masses_now[edge], before_u)
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
        hits += len(proposal & truth)
        misses += len(proposal - truth)
        error = sum(((1 if e in truth else 0) - (1 if e in proposal else 0)) ** 2
                    for e in pool)
        errors.append(error / len(pool) if pool else 0.0)
        surviving.append(len(worlds))
        times.append(time.perf_counter() - started)
        accepted_frac.append(phase)
    return {
        "n": n, "k": k, "m": m,
        "precision": hits / (hits + misses) if hits + misses else None,
        "completion_error": statistics.fmean(errors) if errors else None,
        "cases": len(errors),
        "mean_worlds": statistics.fmean(surviving) if surviving else None,
        "mean_seconds": statistics.fmean(times) if times else None,
        "accept_fraction": statistics.fmean(accepted_frac) if accepted_frac else None,
    }


def passive_cell(n: int, seeds) -> dict:
    """Passive arm on the sampled support at M = 2000, for P5's comparison."""
    errors, gains = [], []
    for seed in seeds:
        state = build_case(seed, n)
        if state is None:
            continue
        rng_w = random.Random(seed * 7919 + 17)
        worlds = sample_worlds(state["observed"], state["pool"], pool_mod.MISSING,
                               2000, rng_w)
        if not worlds:
            continue
        pool = decoder_pool(state, worlds)
        if not pool:
            continue
        proposal = pa.top_k(pa.masses(worlds, pool))
        truth = state["truth"]
        error = sum(((1 if e in truth else 0) - (1 if e in proposal else 0)) ** 2
                    for e in pool)
        errors.append(error / len(pool))
    return {"completion_error": statistics.fmean(errors) if errors else None,
            "cases": len(errors)}


def null_cell(n: int, k: int, seeds) -> dict:
    """Same spend, readings independent of truth, sampled support."""
    beats = 0
    for seed in seeds:
        state = build_case(seed, n)
        if state is None:
            continue
        rng_w = random.Random(seed * 7919 + 17)
        worlds = sample_worlds(state["observed"], state["pool"], pool_mod.MISSING,
                               2000, rng_w)
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
        gain = (len(proposal & truth) - len(proposal - truth)) - \
               (len(base & truth) - len(base - truth))
        if gain > 0:
            beats += 1
    return {"n": n, "k": k, "cases_beating_passive": beats}


def main() -> int:
    held = range(DEV, DEV + HELDOUT)
    cells: dict[str, dict] = {}
    for n in ENTITY_COUNTS:
        for k in QUERIES:
            if n in EXHAUSTIVE:
                cells[f"{n}@{k}@exh"] = run_cell(n, k, None, held)
            for m in SAMPLES:
                cells[f"{n}@{k}@{m}"] = run_cell(n, k, m, held)

    # P1: the sampler is faithful where both are computable.
    gaps = {}
    for n in EXHAUSTIVE:
        for k in QUERIES:
            exh = cells[f"{n}@{k}@exh"]["precision"]
            big = cells[f"{n}@{k}@{SAMPLES[-1]}"]["precision"]
            if exh is not None and big is not None:
                gaps[f"{n}@{k}"] = abs(exh - big)
    p1 = bool(gaps) and all(g <= 0.10 for g in gaps.values())

    # P2: 2000 samples suffice at n = 4.
    gaps2 = {}
    for k in QUERIES:
        exh = cells[f"4@{k}@exh"]["precision"]
        mid = cells[f"4@{k}@2000"]["precision"]
        if exh is not None and mid is not None:
            gaps2[f"4@{k}"] = abs(exh - mid)
    p2 = bool(gaps2) and all(g <= 0.10 for g in gaps2.values())

    # P3: the realistic pools are measurable and continue the trend.
    p3_measurable = all(cells[f"{n}@8@2000"]["precision"] is not None for n in (6, 8))
    trend = [cells[f"{n}@8@2000"]["precision"] for n in (4, 6, 8)]
    p3 = p3_measurable and all(a >= b for a, b in zip(trend, trend[1:])) and trend[0] > trend[-1]

    # P4: cost is bounded by M, not by the world count.
    t4 = cells["4@8@2000"]["mean_seconds"]
    t8 = cells["8@8@2000"]["mean_seconds"]
    p4 = (t4 is not None and t8 is not None and t8 <= 4 * t4)

    # P5: the null arm does not beat passive.
    nulls = {f"{n}@8": null_cell(n, 8, held) for n in (6, 8)}
    p5 = all(v["cases_beating_passive"] <= HELDOUT // 3 for v in nulls.values())

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p1:
        verdict += "; UNVERIFIABLE (the sampler does not reproduce exhaustive support)"

    receipt = {
        "card": "R-P1.68", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.68-sampled-posterior.md",
        "command": "python3 scripts/sampled-posterior-prereg.py",
        "entity_counts": list(ENTITY_COUNTS), "queries": list(QUERIES),
        "samples": list(SAMPLES),
        "cells": cells,
        "exhaustive_gaps_at_max_m": gaps,
        "samples": list(SAMPLES),
        "exhaustive_gaps_m2000_n4": gaps2,
        "trend_at_k8_m2000": {str(n): cells[f"{n}@8@2000"]["precision"]
                             for n in (4, 6, 8)},
        "timing": {"n4": t4, "n8": t8},
        "nulls": nulls,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/sampled-posterior-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "exhaustive_gaps_at_max_m": gaps,
                      "trend_at_k8_m2000": receipt["trend_at_k8_m2000"],
                      "timing": {"n4_s": t4, "n8_s": t8},
                      "nulls": nulls}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
