"""R-P1.54: decode → gate → declare → re-verify, on one world, one run."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.admission import gate
from psychopomp.graph_patch import decode
from psychopomp.physis_snapshot import from_cli

P = ("file:src/a.txt", "CONTAINS", "file:src/b.txt")
Q = ("file:src/b.txt", "CONTAINS", "file:src/c.txt")


def run(args, world):
    out = subprocess.run(["physis", *args], cwd=world, capture_output=True, text=True)
    return out.returncode, (out.stdout + out.stderr).strip().splitlines()


def log_rows(world):
    path = Path(world) / ".physis-next" / "observations.jsonl"
    return sum(1 for _ in path.open()) if path.exists() else 0


def relations(world, object_id):
    rc, lines = run(["object", "get", object_id, "--json"], world)
    return len(json.loads("\n".join(lines))["relations"]) if rc == 0 else -1


def claim(world, edge):
    return run(["claim", *edge], world)[0]


def main() -> int:
    world = tempfile.mkdtemp(prefix="chain-", dir="/tmp/opencode")
    src = Path(world) / "src"
    src.mkdir()
    for name in ("a", "b", "c"):
        (src / f"{name}.txt").write_text(f"{name}\n")
    run(["observe", "."], world)

    objects = json.loads("\n".join(run(["object", "list", "--json"], world)[1]))
    details = [json.loads("\n".join(run(["object", "get", row["id"], "--json"], world)[1]))
               for row in objects["objects"]]
    snapshot = from_cli(objects, details)
    relations_before = relations(world, "file:src/a.txt")
    rows_before = log_rows(world)

    plan = decode(snapshot, [{P, Q}, set()],
                  experiments={"passive": 0.0, "perturbed": 1.0})
    gated = gate(plan, world)
    proposals = [op for op in gated["operations"] if op["op"] == "propose_edge"]

    y1 = (len(proposals) == 2
          and all(op["agreement"] == "disputed" and op["status"] == "HYPOTHESIZED"
                  and op.get("unverified_by_fold") for op in proposals)
          and all(check["verdict"] == "NO_EVIDENCE" for check in gated["admission"]["checks"])
          and not gated["admission"]["already_known"])

    declared = []
    for edge in (P, Q):
        rc, lines = run(["declare", *edge], world)
        declared.append({"edge": edge, "rc": rc, "first_line": lines[0] if lines else ""})
    rows_after = log_rows(world)
    y2 = (all(d["rc"] == 1 for d in declared) and rows_after - rows_before == 2)

    reverified = {"P": claim(world, P), "Q": claim(world, Q)}
    y3 = reverified == {"P": 2, "Q": 2}

    y4 = relations(world, "file:src/a.txt") == relations_before
    y5 = (gated["verifier"]["status"] == "NOT_EVALUATED"
          and all(op.get("status") in ("HYPOTHESIZED", None) for op in gated["operations"]))

    print("| step | edge | rc / verdict |")
    print("|---|---|---|")
    for check in gated["admission"]["checks"]:
        print(f"| gate | {check['edge'][1]} {check['edge'][0]}→{check['edge'][2]} | {check['verdict']} ({check['rc']}) |")
    for entry in declared:
        print(f"| declare | {entry['edge'][1]} {entry['edge'][0]}→{entry['edge'][2]} | rc {entry['rc']} |")
    for name, edge in (("P", P), ("Q", Q)):
        print(f"| re-claim {name} | {edge[1]} {edge[0]}→{edge[2]} | rc {reverified[name]} |")
    print(f"| graph | file:src/a.txt relations | {relations_before} → {relations(world, 'file:src/a.txt')} |")
    print(f"| log | rows | {rows_before} → {rows_after} |")

    print()
    print(f"Y1 gating yields NO_EVIDENCE for both: {'UPHELD' if y1 else 'FALSIFIED'}")
    print(f"Y2 both declarations refused, two rows recorded: {'UPHELD' if y2 else 'FALSIFIED'}")
    print(f"Y3 proposing and declaring does not promote: {'UPHELD' if y3 else 'FALSIFIED'}")
    print(f"Y4 the graph is unchanged: {'UPHELD' if y4 else 'FALSIFIED'}")
    print(f"Y5 the plan stays unapplied: {'UPHELD' if y5 else 'FALSIFIED'}")
    ok = all((y1, y2, y3, y4, y5))
    print(f"scratch world: {world}")
    print(f"patch chain: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
