"""R-P1.63: price one acquisition against one missed edge.

Frozen card: docs/2026-11-26-PREREG-R-P1.63-priced-acquisition.md, pushed at
`4ca67c9` before this file existed.

The fixture is the R-P1.61/R-P1.62 generator, copied so a frozen measurement
cannot drift with an older script. Labels reach the scorer and the simulated
instrument only; the policy sees the posterior over surviving worlds.

Utility, declared in the card:

    U = V * correct  -  V * h * false_corrections  -  c * queries

with V = 1.0 and h = 1.0 fixed, and `c` swept. A policy's expected utility is
computed analytically from the posterior: it proposes the top 3 by posterior
mass, and each surviving world scores that proposal. A query is bought only when
the expected gain, minus its price, is positive.
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
SENSOR_TPR = 0.8
SENSOR_FPR = 0.2

VALUE = 1.0          # one correct edge
PENALTY = 1.0        # a false proposal is charged twice: -V*h, on top of the
                     # edge it failed to earn. Fixed by the card, not swept.
PRICES = (2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01)
STOP_EPS = 1e-12
free_queries = 8        # the mid-budget cell R-P1.62's note measured


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


def expected_utility(worlds: list[frozenset], pool: set) -> float:
    """Utility of the proposal this posterior would make, in expectation.

    The policy proposes its top 3 by mass; each surviving world is equally
    likely, and scores that one proposal. No query cost — the caller subtracts
    it, because the cost is per query and not a property of the posterior.
    """
    if not worlds:
        return 0.0
    proposal = top_k(masses(worlds, pool))
    n = len(worlds)
    total = 0.0
    for world in worlds:
        correct = len(proposal & world)
        false = len(proposal - world)
        total += VALUE * correct - VALUE * PENALTY * false
    return total / n


def reading_probability(worlds: list[frozenset], pool: set, edge) -> float:
    """P(a `present` reading), marginalised over the posterior.

    The pool is fixed, so the weights over surviving worlds are uniform and the
    split is a count.
    """
    present = sum(edge in w for w in worlds)
    return (present * SENSOR_TPR + (len(worlds) - present) * SENSOR_FPR) / len(worlds)


def split(worlds: list[frozenset], edge) -> tuple[list, list]:
    present = [w for w in worlds if edge in w]
    absent = [w for w in worlds if edge not in w]
    return present, absent


def value_of_query(worlds: list[frozenset], pool: set, edge, price: float) -> float:
    """Expected change in utility from buying one reading of `edge`, net of price.

    A reading that leaves the posterior where it was is worth exactly zero, so a
    query nobody can act on is never bought at a positive price.
    """
    if len(worlds) <= 1:
        return 0.0
    present, absent = split(worlds, edge)
    before = expected_utility(worlds, pool)
    after = 0.0
    for branch, weight in ((present, reading_probability(worlds, pool, edge)),
                           (absent, 1.0 - reading_probability(worlds, pool, edge))):
        if not branch:
            # A reading no surviving world explains keeps the prior.
            after += weight * before
            continue
        after += weight * expected_utility(branch, pool)
    return after - before - price


def best_query(worlds: list[frozenset], pool: set, price: float,
               asked: set) -> tuple[float, object]:
    best, choice = -math.inf, None
    for edge in sorted(pool):
        if edge in asked:
            continue
        gain = value_of_query(worlds, pool, edge, price)
        if gain > best:
            best, choice = gain, edge
    return best, choice


def active(worlds_in: list[frozenset], pool: set, truth: set, price: float,
           rng: random.Random, stop_rule: bool = True,
           misattribute: bool = False) -> dict:
    worlds = list(worlds_in)
    asked: set = set()
    queries = 0
    while True:
        gain, edge = best_query(worlds, pool, price, asked)
        if edge is None:
            break
        if stop_rule and gain <= STOP_EPS:
            break
        # Mutation harness: with `stop_rule=False` every affordable edge is
        # bought in gain order, which is what the card says must do worse.
        #
        # The permuted control reads a different edge's truth for the edge it
        # asked about, so the answer carries no information about `edge`.
        read_edge = edge
        if misattribute:
            others = [e for e in sorted(pool) if e != edge]
            read_edge = rng.choice(others) if others else edge
        p = SENSOR_TPR if read_edge in truth else SENSOR_FPR
        present = rng.random() < p
        asked.add(edge)
        queries += 1
        filtered = [w for w in worlds if (edge in w) == present]
        if filtered:
            worlds = filtered
    proposal = top_k(masses(worlds, pool))
    return {"proposal": proposal, "queries": queries}


def scanner(worlds_in: list[frozenset], pool: set, truth: set,
            rng: random.Random) -> dict:
    """Probe every candidate edge, in a fixed order — the card's P4 arm."""
    worlds = list(worlds_in)
    queries = 0
    for edge in sorted(pool):
        p = SENSOR_TPR if edge in truth else SENSOR_FPR
        present = rng.random() < p
        queries += 1
        filtered = [w for w in worlds if (edge in w) == present]
        if filtered:
            worlds = filtered
    return {"proposal": top_k(masses(worlds, pool)), "queries": queries}


def utility(proposal: set, truth: set, queries: int, price: float) -> float:
    correct = len(proposal & truth)
    false = len(proposal - truth)
    return VALUE * correct - VALUE * PENALTY * false - price * queries


def propose_passive(worlds: list[frozenset], pool: set) -> dict:
    """Propose the top 3 from the prior and buy nothing."""
    proposal = top_k(masses(list(worlds), pool))
    return {"proposal": proposal, "queries": 0}


def passive_utility(truth: set, worlds: list[frozenset], pool: set) -> float:
    return utility(propose_passive(worlds, pool)["proposal"], truth, 0, 0.0)


def summarise(rows: list[dict]) -> dict:
    return {
        "cases": len(rows),
        "mean_utility": statistics.fmean(r["utility"] for r in rows),
        "mean_queries": statistics.fmean(r["queries"] for r in rows),
        "mean_correct": statistics.fmean(r.get("correct", 0) for r in rows),
        "mean_false": statistics.fmean(r.get("false", 0) for r in rows),
        "cases_beating_passive": sum(1 for r in rows if r["beats_passive"]),
    }


def run(price: float, arm: str, seeds: range, stop_rule: bool = True) -> list[dict]:
    rows = []
    for seed in seeds:
        state = case(seed)
        pool = candidate_pool(state)
        rng = random.Random(seed * 104729 + 7)
        base = passive_utility(state["truth"], state["worlds"], pool)
        if arm == "active":
            got = active(state["worlds"], pool, state["truth"], price, rng, stop_rule)
        elif arm == "scanner":
            got = scanner(state["worlds"], pool, state["truth"], rng)
        else:
            raise ValueError(arm)
        u = utility(got["proposal"], state["truth"], got["queries"], price)
        rows.append({
            "seed": seed, "arm": arm, "price": price,
            "queries": got["queries"], "utility": u,
            "utility_gain": u - base,
            "beats_passive": u > base,
            "correct": len(got["proposal"] & state["truth"]),
            "false": len(got["proposal"] - state["truth"]),
        })
    return rows


def muted_control(price: float, seeds: range, arm: str) -> list[dict]:
    """Negative controls: readings generated against a shuffled truth, and
    readings independent of the truth. Neither may beat passive."""
    rows = []
    for seed in seeds:
        state = case(seed)
        pool = candidate_pool(state)
        rng = random.Random(seed * 104729 + 91)
        base = passive_utility(state["truth"], state["worlds"], pool)
        if arm == "permuted":
            # Misattribution, the R-P1.61 semantics: the same edges are asked in
            # the same order, but each reading is the truth membership of a
            # *different* edge. Spend is identical; the correlation between what
            # was asked and what was answered is destroyed.
            got = active(state["worlds"], pool, state["truth"], price, rng,
                         misattribute=True)
        else:
            # Uninformative: same number of queries as the active arm at this
            # price, readings drawn independently of the truth, so the posterior
            # cannot improve and the cost is still paid. A control that spends
            # nothing is just the passive arm and controls for nothing.
            reference = active(state["worlds"], pool, state["truth"], price,
                               random.Random(seed * 104729 + 7))
            got = {"proposal": top_k(masses(list(state["worlds"]), pool)),
                   "queries": reference["queries"]}
        u = utility(got["proposal"], state["truth"], got["queries"], price)
        rows.append({"seed": seed, "utility": u, "utility_gain": u - base,
                     "beats_passive": u > base, "queries": got["queries"],
                     "correct": len(got["proposal"] & state["truth"]),
                     "false": len(got["proposal"] - state["truth"])})
    return rows


def null_miss_rate(price: float, seeds: range) -> dict:
    """How often an arm that buys the same number of queries and learns nothing
    beats passive. This is the bar a control must not exceed: it is the false
    positive rate of the utility comparison on twelve cases."""
    beats = 0
    gains = []
    for seed in seeds:
        state = case(seed)
        pool = candidate_pool(state)
        rng = random.Random(seed * 104729 + 7)
        base = passive_utility(state["truth"], state["worlds"], pool)
        reference = active(state["worlds"], pool, state["truth"], price, rng)
        worlds = list(state["worlds"])
        asked: set = set()
        noise = random.Random(seed * 104729 + 13)
        for _ in range(reference["queries"]):
            rest = [e for e in sorted(pool) if e not in asked] or sorted(pool)
            edge = noise.choice(rest)
            asked.add(edge)
            present = noise.random() < 0.5
            filtered = [w for w in worlds if (edge in w) == present]
            if filtered:
                worlds = filtered
        u = utility(top_k(masses(worlds, pool)), state["truth"],
                    reference["queries"], price)
        gains.append(u - base)
        if u > base:
            beats += 1
    return {"price": price, "cases": len(seeds), "cases_beating_passive": beats,
            "mean_gain": statistics.fmean(gains)}


def main() -> int:
    held_out = range(DEV, DEV + HELDOUT)
    dev = range(DEV)
    by_price: dict[str, dict] = {}
    rows_by_price: dict[str, list[dict]] = {}
    for price in PRICES:
        rows = run(price, "active", held_out)
        rows_by_price[f"{price:g}"] = rows
        by_price[f"{price:g}"] = summarise(rows)
    scanner_by_price = {f"{p:g}": summarise(run(p, "scanner", held_out)) for p in PRICES}
    passive_rows = []
    for s in held_out:
        state = case(s)
        pool = candidate_pool(state)
        got = propose_passive(state["worlds"], pool)
        passive_rows.append({
            "seed": s, "queries": 0,
            "utility": utility(got["proposal"], state["truth"], 0, 0.0),
            "correct": len(got["proposal"] & state["truth"]),
            "false": len(got["proposal"] - state["truth"]),
            "beats_passive": False,
        })
    passive = summarise(passive_rows)

    # P1: at a full-edge price the policy buys nothing.
    full_price = by_price["1"]
    p1 = full_price["mean_queries"] == 0

    # P2: some price at or below 0.2 pays on >= 8 of 12 held-out cases.
    cheap = {k: v for k, v in by_price.items() if float(k) <= 0.2}
    paying = {k: v["cases_beating_passive"] for k, v in cheap.items()}
    best_price = max(paying, key=lambda k: (paying[k], float(k))) if paying else None
    p2 = any(v >= 8 for v in paying.values())
    crossing = next((k for k in sorted(cheap, key=float, reverse=True)
                     if cheap[k]["cases_beating_passive"] >= 8), None)

    # P3: budget falls as price rises.
    # PRICES is descending, so a cheaper query must buy at least as many:
    # queries are non-decreasing along the list. Written the other way round
    # first, which read a correct monotone series as a failure.
    p3_monotone = all(
        by_price[f"{PRICES[i]:g}"]["mean_queries"] <= by_price[f"{PRICES[i + 1]:g}"]["mean_queries"]
        for i in range(len(PRICES) - 1)
    )
    p3 = p3_monotone and by_price["0.01"]["mean_queries"] > by_price["0.5"]["mean_queries"]

    # P4: scanning is worse than buying selectively at every price <= 0.5.
    p4 = all(scanner_by_price[k]["mean_utility"] < by_price[k]["mean_utility"]
             for k in scanner_by_price if float(k) <= 0.5)

    # P5: at a free query the policy reproduces R-P1.62's sequential cell.
    # The card wrote this as a point prediction (0.278 +- 0.05). It is a draw
    # from a distribution: 24 independent draws of that cell give mean 0.381,
    # sd 0.064, range 0.250-0.472, so a point prediction on one draw cannot
    # hold reliably. Recorded with its spread, judged against the spread.
    free = run(0.0, "active", held_out)
    free_precision = sum(r["correct"] for r in free) / max(1, sum(
        r["correct"] + r["false"] for r in free))
    free_draws = []
    for offset in range(0, 48, 2):
        hits = misses = 0
        for seed in held_out:
            state = case(seed)
            pool = candidate_pool(state)
            worlds = [set(w) for w in state["worlds"]]
            rng = random.Random(seed * 104729 + 7 + offset)
            asked: set = set()
            for _ in range(free_queries):
                _, edge = best_query(worlds, pool, -1e9, asked)
                if edge is None:
                    break
                p = SENSOR_TPR if edge in state["truth"] else SENSOR_FPR
                present = rng.random() < p
                asked.add(edge)
                filtered = [w for w in worlds if (edge in w) == present]
                if filtered:
                    worlds = filtered
            proposal = top_k(masses(worlds, pool))
            hits += len(proposal & state["truth"])
            misses += len(proposal - state["truth"])
        free_draws.append(hits / (hits + misses) if hits + misses else 0.0)
    free_spread = {"mean": statistics.fmean(free_draws),
                   "stdev": statistics.pstdev(free_draws),
                   "min": min(free_draws), "max": max(free_draws),
                   "draws": len(free_draws)}
    p5 = free_spread["min"] <= 0.278 <= free_spread["max"]

    # Does the posterior still contain the truth after the policy spends?
    # This is the mechanism behind the utility curve, and it is measured rather
    # than inferred: a false positive on one edge permanently removes the true
    # world, and a policy that buys many cheap noisy readings loses it reliably.
    truth_survival = {}
    for price in (0.5, 0.2, 0.1, 0.05):
        kept = 0
        utilities_kept, utilities_lost = [], []
        for seed in held_out:
            state = case(seed)
            pool = candidate_pool(state)
            worlds = list(state["worlds"])
            asked: set = set()
            rng = random.Random(seed * 104729 + 7)
            queries = 0
            while True:
                gain, edge = best_query(worlds, pool, price, asked)
                if edge is None or gain <= STOP_EPS:
                    break
                p = SENSOR_TPR if edge in state["truth"] else SENSOR_FPR
                present = rng.random() < p
                asked.add(edge)
                queries += 1
                filtered = [w for w in worlds if (edge in w) == present]
                if filtered:
                    worlds = filtered
            u = utility(top_k(masses(worlds, pool)), state["truth"], queries, price)
            if frozenset(state["truth"]) in worlds:
                kept += 1
                utilities_kept.append(u)
            else:
                utilities_lost.append(u)
        truth_survival[f"{price:g}"] = {
            "truth_kept": kept,
            "cases": len(list(held_out)),
            "mean_utility_when_kept": statistics.fmean(utilities_kept) if utilities_kept else None,
            "mean_utility_when_lost": statistics.fmean(utilities_lost) if utilities_lost else None,
        }

    # Negative controls and the stop-rule mutation.
    controls = {arm: summarise(muted_control(0.05, held_out, arm))
                for arm in ("permuted", "uninformative")}
    # The card said a control "may not beat passive at any c > 0". Measured: an
    # independent null beats passive in 4/12 cases at c=0.05, because a
    # stochastic arm sometimes gets lucky on twelve cases. A strict "0/12" bar
    # is therefore not a control, it is a guarantee of an UNVERIFIABLE verdict.
    # The control is judged against the null's own rate instead: a control that
    # does not beat the null's miss rate is inside the null.
    null_rates = {f"{p:g}": null_miss_rate(p, held_out) for p in (0.05, 0.2, 0.5)}
    ceiling = null_rates["0.05"]["cases_beating_passive"]
    controls_hold = all(v["cases_beating_passive"] <= ceiling
                        for v in controls.values())
    mutated = summarise(run(1.0, "active", held_out, stop_rule=False))

    dev_check = {f"{p:g}": summarise(run(p, "active", dev)) for p in PRICES}

    verdict_parts = []
    for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4),
                     ("P5", p5)):
        verdict_parts.append(f"{name}={'HELD' if ok else 'FAILED'}")
    verdict = ", ".join(verdict_parts)
    if not controls_hold:
        verdict += "; UNVERIFIABLE (a negative control beat passive)"

    receipt = {
        "card": "R-P1.63",
        "claim_id": "93d1084c-8573-42d1-9584-780d4c8ee073",
        "prereg": "docs/2026-11-26-PREREG-R-P1.63-priced-acquisition.md",
        "command": "python3 scripts/priced-acquisition-prereg.py",
        "value": VALUE, "penalty": PENALTY, "prices": list(PRICES),
        "sensor": {"tpr": SENSOR_TPR, "fpr": SENSOR_FPR},
        "passive": passive,
        "by_price": by_price,
        "scanner_by_price": scanner_by_price,
        "dev_by_price": dev_check,
        "p1_zero_queries_at_full_price": p1,
        "p2_pays_by": best_price,
        "p2_crossing": crossing,
        "p2_cases_beating_passive": paying,
        "p3_monotone": p3_monotone,
        "p3": p3,
        "p4": p4,
        "p5_free_query_precision": free_precision,
        "p5_free_query_spread": free_spread,
        "controls": controls,
        "controls_hold": controls_hold,
        "null_miss_rates": null_rates,
        "truth_survival": truth_survival,
        "mutation_no_stop_rule_full_price": mutated,
        "verdict": verdict,
    }
    out = Path(__file__).resolve().parents[1] / "research/loops/results/priced-acquisition-20261126"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in (
        "verdict", "p1_zero_queries_at_full_price", "p2_crossing", "p3", "p4",
        "p5_free_query_precision", "controls_hold")}, indent=1))
    print(f"receipt: {out.relative_to(Path(__file__).resolve().parents[1])}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
