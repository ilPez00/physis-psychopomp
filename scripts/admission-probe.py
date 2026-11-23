"""R-P1.53: what actually happens when a proposal reaches the writer."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.graph_patch import decode
from psychopomp.physis_snapshot import from_cli

if shutil.which("physis") is None:
    print("NOT MEASURED: no physis binary on PATH")
    raise SystemExit(2)

ROC, PRED = {0: "admitted", 1: "refused", 2: "invalid", 3: "unverifiable"}, {}
E = ("file:src/a.txt", "CONTAINS", "file:src/b.txt")
U = ("file:src/a.txt", "frobnicates", "file:src/b.txt")
O = ("file:src/a.txt", "DEFINES", "document:src/a.txt::1")


def run(args, world):
    out = subprocess.run(["physis", *args], cwd=world, capture_output=True, text=True)
    return out.returncode, (out.stdout + out.stderr).strip().splitlines()


def log_rows(world):
    path = Path(world) / ".physis-next" / "observations.jsonl"
    return sum(1 for _ in path.open()) if path.exists() else 0


def relations(world, object_id):
    rc, lines = run(["object", "get", object_id, "--json"], world)
    return len(json.loads("\n".join(lines))["relations"]) if rc == 0 else -1


def main() -> int:
    world = tempfile.mkdtemp(prefix="admission-", dir="/tmp/opencode")
    src = Path(world) / "src"
    src.mkdir()
    (src / "a.txt").write_text("alpha\n")
    (src / "b.txt").write_text("beta\n")
    run(["observe", "."], world)

    objects = json.loads("\n".join(run(["object", "list", "--json"], world)[1]))
    details = [json.loads("\n".join(run(["object", "get", row["id"], "--json"], world)[1]))
               for row in objects["objects"]]
    snapshot = from_cli(objects, details)
    plan = decode(snapshot, [{("file:src/a.txt", "CONTAINS", "file:src/b.txt")}])

    probes = []
    print("| probe | declare | rc | meaning | log rows | after |")
    print("|---|---|---|---|---|---|")
    for label, triple, predicted in (
            ("P1 first refusal", E, 1),
            ("P2 repeat", E, 3),
            ("P3 unknown predicate", U, 2),
            ("P4 already observed", O, 0)):
        before = log_rows(world)
        rc, lines = run(["declare", *triple], world)
        after = log_rows(world)
        probes.append({"probe": label, "rc": rc, "predicted": predicted,
                       "log_delta": after - before, "first_line": lines[0] if lines else ""})
        print(f"| {label} | {triple[1]} | {rc} | {ROC.get(rc, '?')} | {before} | {after} |")

    p1 = probes[0]["rc"] == 1 and probes[0]["log_delta"] == 1
    p2 = probes[1]["rc"] == 3 and probes[1]["log_delta"] == 1
    p3 = probes[2]["rc"] == 2 and probes[2]["log_delta"] == 0
    p4 = probes[3]["rc"] == 0 and relations(world, "file:src/a.txt") == 1
    again = decode(snapshot, [{("file:src/a.txt", "CONTAINS", "file:src/b.txt")}])
    p5 = (all(op.get("status") == "HYPOTHESIZED"
              for op in again["operations"] if op["op"] == "propose_edge")
          and again["verifier"]["status"] == "NOT_EVALUATED"
          and again["base_revision"] == snapshot.revision)

    print()
    print(f"P1 first refusal recorded: {'UPHELD' if p1 else 'FALSIFIED'}")
    print(f"P2 repeat reads UNVERIFIABLE, not a new refusal: {'UPHELD' if p2 else 'FALSIFIED'}")
    print(f"P3 invalid input writes nothing: {'UPHELD' if p3 else 'FALSIFIED'}")
    print(f"P4 already-observed triple leaves one relation: {'UPHELD' if p4 else 'FALSIFIED'}")
    print(f"P5 the decoder never claims an admission: {'UPHELD' if p5 else 'FALSIFIED'}")
    ok = all((p1, p2, p3, p4, p5))
    print(f"scratch world: {world}")
    print(f"admission probe: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
