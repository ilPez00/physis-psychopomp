"""Reproduce B3's two isolated rival revisions from the committed store capture."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PIN = "7d72b415ad53ba3d670e1c6572e6dc8343a4b64b"
STORE = "750fd1058916bf6837117b816c7f64dded91b09f3c14a5368aa919cc382aa834"
CASES = (("law-1-state-3", -1, 7), ("law+1-state-3", 1, 3))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def run(repo, scratch):
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip() == PIN
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=repo)
    captures = repo / "research/loops/results/active-store-replay-20261123"
    observed = captures / "store.jsonl"
    assert sha(observed.read_bytes()) == STORE
    rows = [(json.loads(line), line) for line in observed.read_bytes().splitlines(keepends=True)]
    assert [row["seq"] for row, _ in rows] == list(range(8))
    ledger = scratch / "ledger"
    ledger.mkdir()
    env = {**os.environ, "PHYSIS_CORE_DIR": str(ledger)}
    core = Path(shutil.which("physis-core")).resolve()

    def invoke(argv, expected=0):
        result = subprocess.run(argv, cwd=scratch, env=env, text=True, capture_output=True)
        assert result.returncode == expected, (argv, result.returncode, result.stdout, result.stderr)
        return result.stdout.strip()

    def snapshot():
        files = {str(f.relative_to(ledger)): f.read_bytes() for f in ledger.rglob("*") if f.is_file()}
        assert files, "scratch ledger stayed empty"
        return files

    def hashes(files):
        return {name: sha(data) for name, data in files.items()}

    assert invoke([core, "hypothesis", "list"]) == "Registered hypotheses: 0"
    replay = [sys.executable, repo / "scripts/active-discovery.py", "--replay"]
    replayed = [json.loads(invoke([*replay, case, "--store-log", observed]))
                for case in sorted((captures / "cases").iterdir())]
    assert {item["store_seq"] for item in replayed if item["verdict"] == "VERIFIED"} == set(range(8))
    receipt = {"psychopomp_ref": PIN, "historical_importer_ref": "62c3a18a0",
               "store_sha256": STORE, "export_sha256": sha((captures / "executed.jsonl").read_bytes()),
               "ledger_cli": invoke([core, "--version"]), "ledger_cli_sha256": sha(core.read_bytes()),
               "replayed_rows": replayed, "cases": []}

    for name, truth, seq in CASES:
        case = captures / "cases" / name
        rivals = []
        unregistered_at = now()
        for law in (-1, 1):
            claim = f"B3 isolated case {name}: diagnostic response follows law m={law:+d}."
            created = invoke([core, "hypothesis", "create", claim, "--confidence", "0.5"])
            identifier = re.fullmatch(r"Registered hypothesis \[([0-9a-f-]{36})\]", created)[1]
            reopened = invoke([core, "hypothesis", "explain", identifier])
            assert f"INTERPRETATION:\n  {claim}\n" in reopened
            assert re.search(r"^  candidate ", reopened, re.M)
            rivals.append({"law": law, "uuid": identifier, "before_explain": reopened})
        ids = [rival["uuid"] for rival in rivals]
        assert len(set(ids + [r["uuid"] for c in receipt["cases"] for r in c["rivals"]])) == (
            len(ids) + 2 * len(receipt["cases"]))
        proposal_args = [*replay, case, "--store-log"]
        withheld = scratch / f"{name}.withheld.jsonl"
        withheld.write_bytes(b"".join(line for row, line in rows if row["seq"] != seq))

        def no_update():
            before = snapshot()
            result = json.loads(invoke([*proposal_args, withheld, "--rivals", *ids], expected=2))
            assert result["verdict"] == "REFUSED" and result["detail"].endswith("found 0")
            after = snapshot()
            assert before == after and "revisions" not in result
            return {"exit": 2, "result": result, "ledger_before": hashes(before), "ledger_after": hashes(after)}

        control_before = no_update()
        proposal = json.loads(invoke([*proposal_args, observed, "--rivals", *ids]))
        row = rows[seq][0]
        plan = json.loads((case / "plan.json").read_bytes())
        row_sha = sha(json.dumps(row, sort_keys=True, separators=(",", ":")).encode())
        assert proposal["status"] == "PROPOSED"
        assert proposal["evidence"] == {"verdict": "VERIFIED", "resolved": truth, "store_seq": seq,
                                        "producer_key": row["produced_by"], "store_row_sha256": row_sha,
                                        "plan_sha256": plan["plan_sha256"]}
        citation = (f"Verified B3 case {name}: store seq {seq}, producer {row['produced_by']}, "
                    f"row sha256 {row_sha}, plan sha256 {plan['plan_sha256']}.")
        before_at = now()
        for rival, proposed in zip(rivals, proposal["revisions"], strict=True):
            identifier = rival["uuid"]
            status = "Supported" if rival["law"] == truth else "Contradicted"
            polarity = "supporting" if status == "Supported" else "contradicting"
            other = "CONTRADICTING" if status == "Supported" else "SUPPORTING"
            assert proposed == {"hypothesis": identifier, "status": status}
            invoke([core, "hypothesis", "evidence", identifier, citation, "--source", "psychopomp:b3-isolated",
                    "--polarity", polarity])
            invoke([core, "hypothesis", "transition", identifier, status, "--reason", "Verified B3 store replay"])
            after_at = now()
            reopened = invoke([core, "hypothesis", "explain", identifier])
            as_of = [core, "replay", "--subject", identifier, "--at"]
            unregistered = invoke([*as_of, unregistered_at])
            past = invoke([*as_of, before_at])
            current = invoke([*as_of, after_at])
            assert "known but had no recorded belief" in unregistered, (unregistered_at, unregistered)
            assert past.endswith(f"[{identifier}]: Candidate"), (before_at, past)
            assert current.endswith(f"[{identifier}]: {status}"), (after_at, current)
            assert f"{polarity.upper()} EVIDENCE (1):" in reopened and f"{other} EVIDENCE (0):" in reopened
            assert citation in reopened and f"  {status.lower()} (" in reopened
            rival.update({"after_explain": reopened,
                          "history_before_registration_at": unregistered_at,
                          "history_before_registration": unregistered,
                          "history_before_at": before_at, "history_before": past,
                          "history_after_at": after_at, "history_after": current})
        receipt["cases"].append({"case": name, "expected_law": truth, "proposal": proposal, "rivals": rivals,
                                 "withheld_before": control_before, "withheld_after": no_update()})
    return receipt


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="psychopomp-b3-") as directory:
        print(json.dumps(run(Path(sys.argv[1]).resolve(), Path(directory)), indent=2))
