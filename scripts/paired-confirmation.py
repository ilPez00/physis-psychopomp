"""R-P1.59: hold confirmation marginals fixed while breaking episode pairing."""
import json
from collections import Counter
from fractions import Fraction

KNOWN = ("negative", "positive")
ROWS = {
    "negative": ((-2, 0), (-2, 1), (-1, 2), (1, 3)),
    "positive": ((2, 0), (2, 1), (-1, 2), (1, 3)),
    "mimic": ((9, 0), (9, 1), (2, 2), (2, 3)),
    "equivalent": ((2, 0), (2, 1), (-1, 2), (1, 3)),
}


def first_match(first, catalogue):
    matches = [law for law in KNOWN if any(y == first for y, _ in catalogue[law])]
    return ("unique", matches[0]) if len(matches) == 1 else (
        "ambiguous" if matches else "unsupported", None)


def classify(first, confirm, budget, catalogue):
    status, law = first_match(first, catalogue)
    if law is None:
        return status, None, 1
    if budget == 1:
        return "unconfirmed", None, 1
    second = confirm()
    if (first, second) not in catalogue[law]:
        return "mismatch", None, 2
    return "declared", law, 2


def score(episodes, policy):
    counts = Counter()
    for law, first, second in episodes:
        calls = 0

        def confirm():
            nonlocal calls
            calls += 1
            if calls > 1:
                raise ValueError("confirmation budget exceeded")
            return second

        status, declared, cost = policy(first, confirm)
        if cost != 1 + calls:
            raise ValueError("reported cost differs from acquisition count")
        counts["cases"] += 1
        counts["acquisitions"] += cost
        if declared is not None:
            counts["correct" if law == declared else "false"] += 1
        else:
            counts[status] += 1
    return {name: counts[name] for name in ("cases", "acquisitions", "correct", "false",
                                           "ambiguous", "unsupported", "unconfirmed", "mismatch")}


def measure(rows=ROWS):
    catalogue = {law: rows[law] for law in KNOWN}
    episodes = [(law, first, second) for law in (*KNOWN, "mimic") for first, second in rows[law]]
    marginals = {law: sorted(y for _, y in pairs) for law, pairs in rows.items()}
    capacity = Counter(first_match(first, catalogue)[0] for _, first, _ in episodes)
    report = {"marginals": marginals, "first_shot": dict(capacity), "checks": {
        "P1": all(values == list(range(4)) for values in marginals.values())
        and capacity == {"unique": 6, "ambiguous": 4, "unsupported": 2},
    }}
    if not report["checks"]["P1"]:
        return report

    def first_only(first, _confirm):
        status, law = first_match(first, catalogue)
        return status, law, 1

    def strict(budget):
        return lambda first, confirm: classify(first, confirm, budget, catalogue)

    arms = report["arms"] = {
        "first_only": score(episodes, first_only),
        "budget_one": score(episodes, strict(1)),
        "paired": score(episodes, strict(2)),
        "fresh_reset": score([(law, first, second) for law, first, _ in episodes
                              for _, second in rows[law]], strict(2)),
        "equivalent": score([("equivalent", *pair) for pair in rows["equivalent"]], strict(2)),
    }
    first, one, paired, reset, twin = arms.values()
    report["checks"].update({
        "P2": (first["correct"], first["false"], one["correct"], one["false"],
               first["acquisitions"], one["acquisitions"], one["unconfirmed"])
        == (4, 2, 0, 0, 12, 12, 6),
        "P3": (paired["cases"], paired["correct"], paired["false"], paired["mismatch"],
               paired["ambiguous"], paired["unsupported"], paired["acquisitions"])
        == (12, 4, 0, 2, 4, 2, 18),
        "P4": (reset["cases"], reset["correct"], reset["false"], reset["mismatch"],
               reset["ambiguous"], reset["unsupported"]) == (48, 8, 4, 12, 16, 8)
        and Fraction(reset["acquisitions"], reset["cases"]) == Fraction(3, 2),
        "P5": (twin["false"], twin["ambiguous"], twin["cases"], twin["acquisitions"])
        == (2, 2, 4, 6),
    })
    return report


if __name__ == "__main__":
    result = measure()
    print(json.dumps(result, indent=2, sort_keys=True))
    ok = all(result["checks"].values())
    print(f"paired confirmation: {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)
