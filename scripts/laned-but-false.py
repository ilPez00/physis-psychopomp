"""R-P1.55 audited replay: does a scratch assertion establish independent truth?"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.graph_patch import decode
from psychopomp.physis_snapshot import from_cli

F = ("file:src/b.txt", "DEFINES", "document:src/a.txt::1")
TRUE_EDGES = {
    (f"file:src/{name}.txt", "DEFINES", f"document:src/{name}.txt::1")
    for name in ("a", "b")
}


def run(args, world):
    return subprocess.run(["physis", *args], cwd=world, capture_output=True,
                          text=True, timeout=30)


def checked_json(args, world):
    out = run([*args, "--json"], world)
    if out.returncode != 0:
        raise RuntimeError(f"{args}: rc {out.returncode}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def claim(world, edge, rc, state):
    out = run(["claim", *edge, "--json"], world)
    result = json.loads(out.stdout)
    return result if (out.returncode, result["state"]) == (rc, state) else None


def selected_edge(plan):
    proposals = [op for op in plan["operations"] if op["op"] == "propose_edge"]
    if len(proposals) != 1 or plan["verifier"]["status"] != "NOT_EVALUATED":
        return None
    op = proposals[0]
    edge = (op["source"], op["predicate"], op["target"])
    return edge if edge == F and op["status"] == "HYPOTHESIZED" else None


def main() -> int:
    world = tempfile.mkdtemp(prefix="laned-", dir="/tmp/opencode")
    src = Path(world) / "src"
    src.mkdir()
    (src / "a.txt").write_text("alpha\n")
    (src / "b.txt").write_text("beta\n")
    print(f"scratch world: {world}", flush=True)
    observed = run(["observe", "."], world)
    if observed.returncode != 0:
        raise RuntimeError(f"observe: {observed.stderr.strip()}")

    objects = checked_json(["object", "list"], world)
    details = [checked_json(["object", "get", row["id"]], world)
               for row in objects["objects"]]
    snapshot = from_cli(objects, details)
    before_edges = {edge.key() for edge in snapshot.edges}
    relations_before = next((len(row["relations"]) for row in details if row["id"] == F[0]), None)
    claim_before = claim(world, F, 2, "no_evidence")
    z1 = (relations_before == 1 and claim_before is not None and F not in before_edges
          and TRUE_EDGES <= before_edges
          and all(snapshot.has_entity(endpoint) for endpoint in (F[0], F[2])))
    if not z1:
        print("Z1 FALSIFIED: capacity missing; no declaration attempted")
        return 1

    log = Path(world) / ".physis-next" / "observations.jsonl"
    before = log.read_bytes()
    onto_before = checked_json(["ontology-check", "."], world)
    plan = decode(snapshot, [{F}])
    edge = selected_edge(plan)
    if edge is None:
        print("Z6 FALSIFIED: expected one matching provisional proposal; no declaration attempted")
        return 1
    declared = run(["declare", *edge], world)
    after = log.read_bytes()
    appended = after[len(before):].splitlines() if after.startswith(before) else []
    row = json.loads(appended[0]) if len(appended) == 1 else {}
    label = f"{edge[0]} --{edge[1]}--> {edge[2]}"
    claim_after = claim(world, edge, 0, "verified")
    detail = checked_json(["object", "get", edge[0]], world)
    true_still = claim(world, next(t for t in TRUE_EDGES if t[0] == edge[0]), 0, "verified")
    onto_after = checked_json(["ontology-check", "."], world)
    z2 = (declared.returncode == 0 and row.get("source") == "host"
          and row.get("produced_by") == "physis declare"
          and row.get("subject") == f"rel|{edge[1]}|{edge[0]}|{edge[2]}"
          and type(row.get("seq")) is int)
    z3 = claim_after is not None and f"{label} (#{row.get('seq')})" in claim_after["rows"]
    z4 = (len(detail["relations"]) == 2
          and any(rel["row"] == label for rel in detail["relations"]))
    z5 = true_still is not None
    # The frozen card treats refusal as a failed admission scenario (Z2–Z5).
    verdicts = dict(zip(("Z1", "Z2", "Z3", "Z4", "Z5", "Z6"),
                        (z1, z2, z3 and declared.returncode == 0,
                         z4 and declared.returncode == 0, z5 and declared.returncode == 0,
                         selected_edge(plan) == edge)))
    print(json.dumps({
        "physis": run(["--version"], world).stdout.strip(),
        "plan": plan, "declare_rc": declared.returncode,
        "rows": [len(before.splitlines()), len(after.splitlines())],
        "claim_before": claim_before, "claim_after": claim_after,
        "assertion": row, "relations": [relations_before, len(detail["relations"])],
        "true_edge_after": true_still,
        "ontology_violations": [onto_before["violation_count"], onto_after["violation_count"]],
        "verdicts": {key: "UPHELD" if value else "FALSIFIED" for key, value in verdicts.items()},
    }, indent=2))
    ok = all(verdicts.values())
    print(f"laned-but-false: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
