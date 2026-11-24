"""R-P1.57: exhaustive finite witness, no observations written to history."""
import json
from fractions import Fraction
from itertools import permutations, product

LAWS = ("additive", "sign-flip")
ACTIONS = (0, 1)
DISTURBANCES = (-2, -1, 1, 2)


def outcome(law, action, s):
    return 3 * action + (s if law == "additive" or action == 0 else -s)


def residual_reuse(action, observed):
    return 3 * (1 - action) + (observed - 3 * action)


def candidates(action, observed):
    residual = observed - 3 * action
    return {3 * (1 - action) + residual, 3 * (1 - action) - residual}


def measure(world=outcome, reuse=residual_reuse):
    paired = {law: {(a, world(law, a, s)): (world(law, 1 - a, s), s)
                    for a, s in product(ACTIONS, DISTURBANCES)} for law in LAWS}
    marginals = {law: [sorted(world(law, a, s) for s in DISTURBANCES) for a in ACTIONS]
                 for law in LAWS}
    additive, flipped = (paired[law] for law in LAWS)
    disagreement = sum(additive[key][0] != flipped[key][0]
                       for key in additive.keys() & flipped.keys())
    capacity = (marginals["additive"] == marginals["sign-flip"]
                and len(additive) == len(flipped) == disagreement == 8)
    report = {"marginals": marginals, "paired_disagreements": disagreement,
              "checks": {"D1": capacity}}
    if not capacity:
        return report

    metrics = {}
    for law, table in paired.items():
        errors = {"mean": [], "reuse": [], "oracle": [], "shuffled": []}
        covered = two_candidates = 0
        marginal_match = True
        for action in ACTIONS:
            observations = [y for a, y in table if a == action]
            residuals = [y - 3 * action for y in observations]
            alternative_mean = 3 * (1 - action)
            actual = [table[action, y][0] for y in observations]
            reused = [reuse(action, y) for y in observations]
            marginal_match &= sorted(reused) == sorted(actual)
            for observed, truth in zip(observations, actual):
                s = table[action, observed][1]
                errors["mean"].append(abs(alternative_mean - truth))
                errors["reuse"].append(abs(reuse(action, observed) - truth))
                errors["oracle"].append(abs(outcome(law, 1 - action, s) - truth))
                values = candidates(action, observed)
                covered += truth in values
                two_candidates += len(values) == 2
            for shuffled in permutations(residuals):
                if all(before != after for before, after in zip(residuals, shuffled)):
                    errors["shuffled"].extend(abs(alternative_mean + r - truth)
                                              for r, truth in zip(shuffled, actual))
        metrics[law] = {
            "mae": {arm: str(Fraction(sum(values), len(values))) for arm, values in errors.items()},
            "counts": {arm: len(values) for arm, values in errors.items()},
            "covered": covered, "two_candidates": two_candidates,
            "alternative_marginals_match": marginal_match,
        }
    report["metrics"] = metrics
    first, second = (metrics[law] for law in LAWS)
    report["checks"].update({
        "D2": all(m["mae"]["mean"] == "3/2" and m["mae"]["oracle"] == "0"
                  for m in metrics.values()) and (first["mae"]["reuse"], second["mae"]["reuse"]) == ("0", "3"),
        "D3": all(m["counts"]["shuffled"] == 72 for m in metrics.values())
        and (first["mae"]["shuffled"], second["mae"]["shuffled"]) == ("7/3", "4/3"),
        "D4": all(m["covered"] == m["two_candidates"] == 8 for m in metrics.values()),
        "D5": all(m["alternative_marginals_match"] for m in metrics.values()),
    })
    return report


if __name__ == "__main__":
    result = measure()
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = all(result["checks"].values())
    print(f"paired counterfactual: {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)
