"""R-P1.51: what the decoder contract guarantees, arm by arm."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.graph_patch import decode, to_json
from psychopomp.physis_snapshot import Snapshot

ENTITIES = {f"n{i}": "node" for i in range(1, 7)}
TRUE_EDGES = {("n1", "X", "n2"), ("n2", "X", "n3"), ("n3", "X", "n4"),
              ("n4", "X", "n5"), ("n5", "X", "n6"), ("n1", "Y", "n6")}
MISSING = {("n2", "X", "n3"), ("n5", "X", "n6")}
OBSERVED = TRUE_EDGES - MISSING
FABRICATED = ("n2", "X", "n4")
PERMUTATION = {"n1": "n4", "n2": "n5", "n3": "n6", "n4": "n1", "n5": "n2", "n6": "n3"}
EXPERIMENTS = {"passive": 0.0, "perturbed": 1.0}


def snapshot() -> Snapshot:
    from psychopomp.physis_snapshot import Edge
    return Snapshot(entities=dict(ENTITIES), edges=[Edge(*edge) for edge in sorted(OBSERVED)],
                    evidence_seqs=[5, 6, 7], pin="sha256:r-p1.51")


def proposals(plan):
    return [op for op in plan["operations"] if op["op"] == "propose_edge"]


def keys(ops):
    return {(op["source"], op["predicate"], op["target"]) for op in ops}


def arm(worlds):
    return proposals(decode(snapshot(), worlds, experiments=EXPERIMENTS))


def main() -> int:
    snap = snapshot()
    shuffled_world = {(s, p, PERMUTATION[t]) for s, p, t in TRUE_EDGES}
    arms = {
        "exact": [set(TRUE_EDGES)],
        "noisy": [OBSERVED | {FABRICATED}],
        "shuffled": [shuffled_world],
        "empty": [],
    }

    rows = {}
    print("| arm | proposals | true | false | precision | recall | requests | unknown |")
    print("|---|---|---|---|---|---|---|---|")
    for name, worlds in arms.items():
        plan = decode(snap, worlds, experiments=EXPERIMENTS)
        proposed = keys(proposals(plan))
        true = len(proposed & MISSING)
        false = len(proposed - TRUE_EDGES)
        total = len(proposed) or 1
        rows[name] = {
            "plan": plan, "proposed": proposed, "true": true, "false": false,
            "precision": true / total if proposed else 0.0,
            "recall": true / len(MISSING),
            "requests": sum(1 for op in plan["operations"] if op["op"] == "request_evidence"),
            "unknown": sum(1 for op in plan["operations"] if op["op"] == "unknown"),
        }
        r = rows[name]
        print(f"| {name} | {len(proposed)} | {true} | {false} | {r['precision']:.2f} | "
              f"{r['recall']:.2f} | {r['requests']} | {r['unknown']} |")

    disputed_worlds = [set(TRUE_EDGES), OBSERVED | {FABRICATED}]
    disputed = decode(snap, disputed_worlds, experiments=EXPERIMENTS)
    agreement = {tuple(op[key] for key in ("source", "predicate", "target")): op["agreement"]
                 for op in proposals(disputed)}
    disputed_requests = sum(1 for op in disputed["operations"]
                            if op["op"] == "request_evidence")

    deterministic = all(
        to_json(decode(snap, worlds, experiments=EXPERIMENTS))
        == to_json(decode(snap, list(reversed(worlds)), experiments=EXPERIMENTS))
        for worlds in arms.values())

    d1 = (keys(proposals(rows["exact"]["plan"])) == MISSING
          and rows["exact"]["precision"] == 1.0 and rows["exact"]["recall"] == 1.0
          and all(op["status"] == "HYPOTHESIZED"
                  for op in proposals(rows["exact"]["plan"])))
    d2 = (rows["shuffled"]["precision"] <= 0.5
          and rows["shuffled"]["false"] >= rows["shuffled"]["true"])
    d3 = (rows["empty"]["unknown"] == 1 and not rows["empty"]["proposed"]
          and rows["empty"]["requests"] == 0)
    d4 = (agreement.get(("n5", "X", "n6")) == "disputed"
          and agreement.get(FABRICATED) == "disputed"
          and agreement.get(("n2", "X", "n3")) == "all_surviving_worlds"
          and disputed_requests == 1)
    d5 = all(row["plan"]["verifier"]["status"] == "NOT_EVALUATED"
             and row["plan"]["base_revision"] == snap.revision
             and all(op.get("status") in ("HYPOTHESIZED", None)
                     for op in row["plan"]["operations"])
             for row in rows.values()) and deterministic

    print()
    print("disputed-arm map: " + ", ".join(f"{k}:{v}" for k, v in sorted(agreement.items())))
    print(f"D1 exact world: recall 1.0, precision 1.0, still HYPOTHESIZED: {'UPHELD' if d1 else 'FALSIFIED'}")
    print(f"D2 shuffled world: precision <= 0.5 and false >= true: {'UPHELD' if d2 else 'FALSIFIED'} "
          f"({rows['shuffled']['precision']:.2f})")
    print(f"D3 empty admissible set: one UNKNOWN, no proposals: {'UPHELD' if d3 else 'FALSIFIED'}")
    print(f"D4 disputed set: both sides + exactly one REQUEST_EVIDENCE: {'UPHELD' if d4 else 'FALSIFIED'}")
    print(f"D5 nothing applied, base revision named, decodes agree: {'UPHELD' if d5 else 'FALSIFIED'}")
    ok = all((d1, d2, d3, d4, d5))
    print(f"prereg run: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
