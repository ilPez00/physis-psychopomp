"""R-P1.52: the decoder contract, with capacity gates and a closure baseline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.graph_patch import decode, to_json
from psychopomp.physis_snapshot import Edge, Snapshot

ENTITIES = {f"n{i}": "node" for i in range(1, 7)}
T = {("n1", "X", "n2"), ("n2", "X", "n3"), ("n3", "X", "n4"),
     ("n4", "X", "n5"), ("n5", "X", "n6"), ("n1", "Y", "n6")}
MISSING = {("n2", "X", "n3"), ("n5", "X", "n6")}
OBSERVED = T - MISSING
F = ("n2", "X", "n4")
PERMUTATION = {"n1": "n4", "n2": "n5", "n3": "n6", "n4": "n1", "n5": "n2", "n6": "n3"}
SHUFFLED = {(s, p, PERMUTATION[t]) for s, p, t in T}
EXPERIMENTS = {"passive": 0.0, "perturbed": 1.0}


def snapshot() -> Snapshot:
    return Snapshot(entities=dict(ENTITIES),
                    edges=[Edge(*edge) for edge in sorted(OBSERVED)],
                    evidence_seqs=[5, 6, 7], pin="sha256:r-p1.52")


def closure(edges) -> set:
    """Transitive closure of the observed X-edges — a deterministic baseline."""
    out = set(edges)
    x_edges = {(s, t) for s, p, t in edges if p == "X"}
    changed = True
    while changed:
        changed = False
        for a, b in list(x_edges):
            for c, d in list(x_edges):
                if b == c and (a, d) not in x_edges:
                    x_edges.add((a, d))
                    out.add((a, "X", d))
                    changed = True
    return out


def proposals(plan):
    return [op for op in plan["operations"] if op["op"] == "propose_edge"]


def keys(ops):
    return {(op["source"], op["predicate"], op["target"]) for op in ops}


def main() -> int:
    snap = snapshot()
    agreed_worlds = [set(T), T | {F}]
    arms = {
        "no-repair": set(),
        "closure": closure(OBSERVED) - OBSERVED,
        "exact": keys(proposals(decode(snap, [set(T)], experiments=EXPERIMENTS))),
        "shuffled": keys(proposals(decode(snap, [SHUFFLED], experiments=EXPERIMENTS))),
        "agreed": keys(proposals(decode(snap, agreed_worlds, experiments=EXPERIMENTS))),
    }

    # Capacity gates score nothing unless the arms have the structure they claim.
    c1 = (set(ENTITIES) >= {e for edge in T for e in (edge[0], edge[2])}
          and len(OBSERVED) == 4 and len(MISSING) == 2)
    agreed_arm = proposals(decode(snap, agreed_worlds, experiments=EXPERIMENTS))
    agreed_edges = keys(op for op in agreed_arm if op["agreement"] == "all_surviving_worlds")
    disputed_edges = keys(op for op in agreed_arm if op["agreement"] == "disputed")
    c2 = agreed_edges == MISSING and disputed_edges == {F}
    c3 = not (SHUFFLED & T)
    c4 = not (arms["closure"] & MISSING) and bool(arms["closure"])

    print("| arm | proposals | true | false | precision | recall |")
    print("|---|---|---|---|---|---|")
    rows = {}
    for name, proposed in arms.items():
        true = len(proposed & MISSING)
        false = len(proposed - T)
        rows[name] = (len(proposed), true, false)
        precision = f"{true / len(proposed):.2f}" if proposed else "n/a"
        print(f"| {name} | {len(proposed)} | {true} | {false} | {precision} | "
              f"{true / len(MISSING):.2f} |")

    requests = [op for op in decode(snap, agreed_worlds, experiments=EXPERIMENTS)["operations"]
                if op["op"] == "request_evidence"]
    every_plan = [(worlds, decode(snap, worlds, experiments=EXPERIMENTS))
                  for worlds in ([], [set(T)], [SHUFFLED], agreed_worlds)]
    d1 = rows["no-repair"] == (0, 0, 0)
    d2 = rows["closure"][0] > 0 and rows["closure"][1] == 0
    d3 = rows["exact"] == (2, 2, 0)
    d4 = rows["shuffled"][1] == 0 and rows["shuffled"][2] >= rows["shuffled"][1] and (
        rows["shuffled"][0] == 0 or rows["shuffled"][1] / rows["shuffled"][0] <= 0.5)
    d5 = (agreed_edges == MISSING and disputed_edges == {F}
          and len(requests) == 1 and requests[0]["experiments"] == ["perturbed"])
    d6 = all(plan["verifier"]["status"] == "NOT_EVALUATED"
             and plan["base_revision"] == snap.revision
             and all(op.get("status") in ("HYPOTHESIZED", None) for op in plan["operations"])
             for _, plan in every_plan) and all(
        to_json(decode(snap, worlds, experiments=EXPERIMENTS))
        == to_json(decode(snap, list(reversed(worlds)), experiments=EXPERIMENTS))
        for worlds in ([], [set(T)], [SHUFFLED], agreed_worlds))

    print()
    print(f"C1 entity coverage and snapshot shape: {'PASS' if c1 else 'FAIL'}")
    print(f"C2 agreed arm has exactly the two missing edges agreed, one disputed: "
          f"{'PASS' if c2 else 'FAIL'} (agreed {len(agreed_edges)}, disputed {len(disputed_edges)})")
    print(f"C3 shuffled world shares nothing with the truth: {'PASS' if c3 else 'FAIL'}")
    print(f"C4 closure proposes something and touches no missing edge: {'PASS' if c4 else 'FAIL'}")
    if not all((c1, c2, c3, c4)):
        print("prereg run: FAIL (capacity); nothing scored")
        return 1

    print(f"D1 no-repair proposes nothing: {'UPHELD' if d1 else 'FALSIFIED'}")
    print(f"D2 closure recovers no missing edge: {'UPHELD' if d2 else 'FALSIFIED'}")
    print(f"D3 exact world: precision 1.0, recall 1.0: {'UPHELD' if d3 else 'FALSIFIED'}")
    print(f"D4 shuffled world: precision <= 0.5: {'UPHELD' if d4 else 'FALSIFIED'}")
    print(f"D5 agreed edges agreed, one probe requested: {'UPHELD' if d5 else 'FALSIFIED'}")
    print(f"D6 nothing applied, decodes agree: {'UPHELD' if d6 else 'FALSIFIED'}")
    ok = all((d1, d2, d3, d4, d5, d6))
    print(f"prereg run: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
