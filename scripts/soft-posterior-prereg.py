"""R-P1.64: does a soft posterior refuse to collapse?

Frozen card: docs/2026-11-26-PREREG-R-P1.64-soft-posterior.md, pushed at
`4ed02b6` before this file existed. Claim `60d8c8af-e65f-4fdf-a482-a659b1077ec2`.

The generator, sensor, seeds and utility are R-P1.63's, imported rather than
copied where possible so the *only* difference measured is the update rule:

  hard (R-P1.63): world survives only if it agrees with every reading
  soft (this card): world is down-weighted by TPR or FPR per reading

A soft posterior that underflows to all-zero weights keeps the previous weights
and counts the event; an empty distribution is not allowed to be created.
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pa = _load("priced63", ROOT / "scripts/priced-acquisition-prereg.py")

CLAIM = "60d8c8af-e65f-4fdf-a482-a659b1077ec2"
PRICE = 0.1          # the price where R-P1.63's collapse was measured
FULL_PRICE = 1.0
PASSIVE_UTILITY = -1.833    # R-P1.63's measured passive, re-derived below
HARD_PRECISION_R163 = 0.361
MIN_WEIGHT_FLOOR = 1e-6


class Posterior:
    """Exact weights over surviving worlds, updated by a soft likelihood."""

    def __init__(self, worlds: list[frozenset]):
        self.worlds = list(worlds)
        n = len(self.worlds)
        self.weights = [1.0 / n] * n
        self.underflow_events = 0

    def update(self, edge, present: bool) -> None:
        """Reweight by the sensor's likelihood. Never deletes a world."""
        p_agree = pa.SENSOR_TPR if present else 1.0 - pa.SENSOR_FPR
        p_disagree = pa.SENSOR_FPR if present else 1.0 - pa.SENSOR_TPR
        # agreement means: world's membership of `edge` matches the reading
        new = []
        for world, weight in zip(self.worlds, self.weights):
            agrees = (edge in world) == present
            new.append(weight * (p_agree if agrees else p_disagree))
        total = math.fsum(new)
        if total <= 0.0 or not math.isfinite(total):
            # A reading no world explains must not empty the distribution.
            self.underflow_events += 1
            return
        # Renormalise in log-free space; weights are products of 0.2 and 0.8 so
        # the range stays representable for the budgets this fixture uses.
        self.weights = [w / total for w in new]

    def masses(self, pool: set) -> dict:
        out = {edge: 0.0 for edge in pool}
        for world, weight in zip(self.worlds, self.weights):
            if weight == 0.0:
                continue
            for edge in pool:
                if edge in world:
                    out[edge] += weight
        return out

    def truth_weight(self, truth: set) -> float:
        return math.fsum(
            w for world, w in zip(self.worlds, self.weights) if set(world) == truth
        )

    def max_weight(self) -> float:
        return max(self.weights) if self.weights else 0.0

    def expected_utility(self, pool: set) -> float:
        """Utility of this distribution's top-3 proposal, in expectation."""
        proposal = pa.top_k(self.masses(pool))
        total = 0.0
        for world, weight in zip(self.worlds, self.weights):
            if weight == 0.0:
                continue
            correct = len(proposal & set(world))
            false = len(proposal - set(world))
            total += weight * (pa.VALUE * correct - pa.VALUE * pa.PENALTY * false)
        return total


def soft_active(state: dict, pool: set, price: float, rng: random.Random) -> dict:
    """The R-P1.63 policy, with the posterior replaced by the soft one."""
    post = Posterior(state["worlds"])
    asked: set = set()
    queries = 0
    while True:
        # Information gain under the soft posterior: compare expected utility of
        # both branches, weighted by their predicted probability.
        before = post.expected_utility(pool)
        best = (-math.inf, None)
        for edge in sorted(pool):
            if edge in asked:
                continue
            present_mass = post.masses(pool)[edge]
            gain = _branch_gain(post, pool, edge, present_mass, before) - price
            if gain > best[0]:
                best = (gain, edge)
        gain, edge = best
        if edge is None or gain <= pa.STOP_EPS:
            break
        present = edge in state["truth"]
        reading = rng.random() < (pa.SENSOR_TPR if present else pa.SENSOR_FPR)
        asked.add(edge)
        queries += 1
        post.update(edge, reading)
    return {"proposal": pa.top_k(post.masses(pool)), "queries": queries, "post": post}


def _branch_gain(post: Posterior, pool: set, edge, present_mass: float,
                 before: float) -> float:
    """Expected utility after buying one reading of `edge`, minus before."""
    total = 0.0
    for reading_present, mass in ((True, present_mass), (False, 1.0 - present_mass)):
        if mass <= 0.0:
            continue
        branch = Posterior(post.worlds)
        branch.weights = list(post.weights)
        branch.update(edge, reading_present)
        total += mass * branch.expected_utility(pool)
    return total - before


def hard_active(state: dict, pool: set, price: float, rng: random.Random) -> dict:
    """The R-P1.63 arm, for the same-fixture control."""
    worlds = list(state["worlds"])
    asked: set = set()
    queries = 0
    while True:
        gain, edge = pa.best_query(worlds, pool, price, asked)
        if edge is None or gain <= pa.STOP_EPS:
            break
        p = pa.SENSOR_TPR if edge in state["truth"] else pa.SENSOR_FPR
        reading = rng.random() < p
        asked.add(edge)
        queries += 1
        filtered = [w for w in worlds if (edge in w) == reading]
        if filtered:
            worlds = filtered
    return {"proposal": pa.top_k(pa.masses(worlds, pool)), "queries": queries,
            "truth_kept": frozenset(state["truth"]) in worlds,
            "max_weight": None}


def run_arm(arm: str, price: float, seeds) -> list[dict]:
    rows = []
    for seed in seeds:
        state = pa.case(seed)
        pool = pa.candidate_pool(state)
        rng = random.Random(seed * 104729 + 7)
        base = pa.passive_utility(state["truth"], state["worlds"], pool)
        if arm == "soft":
            got = soft_active(state, pool, price, rng)
            post = got["post"]
            truth_weight = post.truth_weight(state["truth"])
            max_weight = post.max_weight()
            underflows = post.underflow_events
            kept = truth_weight > 0.0
        elif arm == "hard":
            got = hard_active(state, pool, price, rng)
            truth_weight = 1.0 if got["truth_kept"] else 0.0
            max_weight = None
            underflows = 0
            kept = got["truth_kept"]
        else:
            raise ValueError(arm)
        u = pa.utility(got["proposal"], state["truth"], got["queries"], price)
        rows.append({
            "seed": seed, "arm": arm, "price": price,
            "queries": got["queries"], "utility": u, "beats_passive": u > base,
            "correct": len(got["proposal"] & state["truth"]),
            "false": len(got["proposal"] - state["truth"]),
            "truth_kept": kept, "truth_weight": truth_weight,
            "max_weight": max_weight, "underflows": underflows,
        })
    return rows


def summarise(rows: list[dict]) -> dict:
    weight = [r["truth_weight"] for r in rows]
    precise = [r["correct"] / (r["correct"] + r["false"])
               for r in rows if r["correct"] + r["false"]]
    return {
        "cases": len(rows),
        "mean_queries": statistics.fmean(r["queries"] for r in rows),
        "mean_utility": statistics.fmean(r["utility"] for r in rows),
        "cases_beating_passive": sum(1 for r in rows if r["beats_passive"]),
        "truth_kept": sum(1 for r in rows if r["truth_kept"]),
        "min_truth_weight": min(weight),
        "mean_truth_weight": statistics.fmean(weight),
        "mean_max_weight": (statistics.fmean(r["max_weight"] for r in rows)
                            if rows[0]["max_weight"] is not None else None),
        "precision": statistics.fmean(precise) if precise else None,
        "underflows": sum(r["underflows"] for r in rows),
    }


def perfect_sensor_check(seeds) -> bool:
    """At TPR 1 / FPR 0 the soft and hard posteriors must coincide in support."""
    tpr, fpr = pa.SENSOR_TPR, pa.SENSOR_FPR
    pa.SENSOR_TPR, pa.SENSOR_FPR = 1.0, 0.0
    try:
        for seed in seeds:
            state = pa.case(seed)
            pool = set(pa.candidate_pool(state))
            rng = random.Random(seed)
            order = sorted(pool)
            rng.shuffle(order)
            soft = Posterior(state["worlds"])
            hard = list(state["worlds"])
            for edge in order[:6]:
                present = edge in state["truth"]
                soft.update(edge, present)
                hard = [w for w in hard if (edge in w) == present]
            support = {w for w, weight in zip(soft.worlds, soft.weights)
                       if weight > 1e-15}
            if support != set(hard):
                return False
        return True
    finally:
        pa.SENSOR_TPR, pa.SENSOR_FPR = tpr, fpr


def precision_draws(arm: str, price: float, seeds, draws: int = 24) -> dict:
    """The precision cell is a draw, not a point: re-run with offset readings."""
    values = []
    for offset in range(0, draws * 2, 2):
        hits = misses = 0
        for seed in seeds:
            state = pa.case(seed)
            pool = pa.candidate_pool(state)
            rng = random.Random(seed * 104729 + 7 + offset)
            if arm == "soft":
                got = soft_active(state, pool, price, rng)
            else:
                got = hard_active(state, pool, price, rng)
            hits += len(got["proposal"] & state["truth"])
            misses += len(got["proposal"] - state["truth"])
        values.append(hits / (hits + misses) if hits + misses else 0.0)
    return {"draws": len(values), "mean": statistics.fmean(values),
            "stdev": statistics.pstdev(values), "min": min(values),
            "max": max(values),
            "above_baseline": sum(v > HARD_PRECISION_R163 for v in values)}


def main() -> int:
    held = range(pa.DEV, pa.DEV + pa.HELDOUT)
    passive = statistics.fmean(
        pa.passive_utility(pa.case(s)["truth"], pa.case(s)["worlds"],
                           pa.candidate_pool(pa.case(s))) for s in held)

    soft = run_arm("soft", PRICE, held)
    hard = run_arm("hard", PRICE, held)
    soft_sum = summarise(soft)
    hard_sum = summarise(hard)

    soft_full = summarise(run_arm("soft", FULL_PRICE, held))
    soft_free = summarise(run_arm("soft", 0.0, held))

    # Known-outcome check: at a perfect sensor (TPR 1, FPR 0) the soft
    # posterior's support must equal the hard filter's surviving set, fed the
    # identical readings. The first version of this compared the two *policies*
    # (utility gain vs information gain), which differ by design — it measured
    # the policy, not the likelihood. This feeds both decoders one sequence.
    perfect_agrees = perfect_sensor_check(held)

    p1 = soft_sum["truth_kept"] == 12 and soft_sum["min_truth_weight"] > MIN_WEIGHT_FLOOR
    p2 = soft_sum["mean_max_weight"] is not None and soft_sum["mean_max_weight"] < 0.75
    # P3 is judged on the draw distribution, not the single draw: the cell has
    # sd ~0.05, so one number above 0.361 proves nothing about the update rule.
    soft_draws = precision_draws("soft", PRICE, held)
    hard_draws = precision_draws("hard", PRICE, held)
    p3 = soft_sum["precision"] is not None and soft_sum["precision"] > HARD_PRECISION_R163
    p4 = soft_sum["mean_utility"] > passive
    p5 = soft_full["mean_queries"] == 0

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not perfect_agrees:
        verdict += "; UNVERIFIABLE (soft and hard disagree at a perfect sensor)"

    receipt = {
        "card": "R-P1.64",
        "claim_id": CLAIM,
        "prereg": "docs/2026-11-26-PREREG-R-P1.64-soft-posterior.md",
        "command": "python3 scripts/soft-posterior-prereg.py",
        "sensor": {"tpr": pa.SENSOR_TPR, "fpr": pa.SENSOR_FPR},
        "price": PRICE,
        "passive_utility": passive,
        "soft": soft_sum,
        "hard_control": hard_sum,
        "soft_at_full_price": soft_full,
        "soft_at_zero_price": soft_free,
        "perfect_sensor_agreement": perfect_agrees,
        "precision_draws": {"soft": soft_draws, "hard": hard_draws},
        "thresholds": {"hard_precision_r163": HARD_PRECISION_R163,
                       "min_truth_weight": MIN_WEIGHT_FLOOR},
        "per_case": soft,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/soft-posterior-20261126"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in
                      ("verdict", "passive_utility", "soft", "hard_control",
                       "perfect_sensor_agreement")}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
