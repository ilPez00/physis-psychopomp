"""Capture one turnover observation per case, then replay from a Physis log."""
import argparse
import hashlib
import json
import secrets
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_receipt import ABSTAIN, VERIFIED, commit, decide, digest, predictions_from
from psychopomp.active_receipt import verify_against
from psychopomp.export import turnover_records
from psychopomp.turnover_evidence import ARMS, PROBES, TICK, arm_of, encode, execute


def frozen(probe, target):
    if type(target) is not int or target not in (1, 2) or probe not in PROBES:
        raise ValueError("unknown turnover probe or role")
    # R-P1.50 at tick 4: nominal (4,4); feedback (5,5);
    # open-loop retains the +2 in the perturbed role. No simulator in replay.
    return predictions_from([(-1, 44), (1, 44)] if probe == "passive"
                            else [(-1, 55), (1, 64 if target == 1 else 46)])


def seal(probe, target, episode):
    plan = commit(policy="adaptive" if probe == "perturbed" else "fixed",
                  selected=probe, prior=(Fraction(1, 2), Fraction(1, 2)),
                  predictions=frozen(probe, target))
    plan.update(target=target, episode=episode)
    plan["plan_sha256"] = digest(plan)
    return plan


def record(root):
    base = secrets.randbits(60) << 3
    with (root / "executed.jsonl").open("x") as output:
        for i, (target, arm, probe) in enumerate(product((1, 2), ARMS, PROBES)):
            episode = base + i
            plan = seal(probe, target, episode)
            with (root / f"{episode}.plan.json").open("x") as handle:
                json.dump(plan, handle, sort_keys=True)
                handle.write("\n")
            row, = turnover_records(execute(arm, probe, target), episode, ticks=(TICK,))
            output.write(json.dumps(row, sort_keys=True) + "\n")
            decision = decide(plan, encode(tuple(row["props"]["loads"])))
            decision["posterior"] = [p.as_integer_ratio() for p in decision["posterior"]]
            expected = arm if probe == "perturbed" else None
            if arm_of(decision["resolved"]) != expected:
                raise ValueError("executed observation did not match the fixture prediction")
            with (root / f"{episode}.decision.json").open("x") as handle:
                json.dump(decision, handle, sort_keys=True)
                handle.write("\n")


def replay(root, store_rows):
    results = []
    executed = [json.loads(line) for line in (root / "executed.jsonl").read_text().splitlines()]
    if len(executed) != 8 or len({row["subject"] for row in executed}) != 8:
        raise ValueError("expected eight distinct captured episodes")
    for expected in executed:
        episode = expected["provenance"]["episode"]
        plan = json.loads((root / f"{episode}.plan.json").read_text())
        decision = json.loads((root / f"{episode}.decision.json").read_text())
        probe, target = plan["selected"], plan["target"]
        if plan != seal(probe, target, episode):
            raise ValueError("sealed probe or predictions changed")
        key = f"psychopomp:{expected['subject']}#{expected['seq']}"
        matches = [row for row in store_rows if row.get("produced_by") == key]
        if len(matches) != 1:
            raise ValueError(f"expected one stored row for {key}, found {len(matches)}")
        row, = matches
        props = row["props"]
        payload = json.loads(props["psychopomp_props"])
        if (row["source"], row["subject"], props["psychopomp_schema"],
            props["psychopomp_kind"], props["psychopomp_evidence"],
            float(props["at_seconds"]), payload, json.loads(props["psychopomp_provenance"])) != (
                "psychopomp", f"episode:0:{episode}", expected["schema"], "loads", "OBSERVED",
                expected["at"], expected["props"], expected["provenance"]):
            raise ValueError(f"stored payload differs for {key}")
        loads = payload["loads"]
        if payload["tick"] != TICK or len(loads) != 2 or any(type(x) is not int or not 0 <= x < 10 for x in loads):
            raise ValueError(f"invalid turnover observation at {key}")
        reading = encode(tuple(loads))
        verdict = verify_against(plan, reading, decision, frozen(probe, target))["verdict"]
        if verdict != (ABSTAIN if probe == "passive" else VERIFIED):
            raise ValueError(f"decision refused for {key}: {verdict}")
        seq = row["seq"]
        if type(seq) is not int or seq < 0 or any(item["store_seq"] == seq for item in results):
            raise ValueError(f"invalid or repeated store sequence {seq!r}")
        results.append({"producer_key": key, "store_seq": seq, "probe": probe, "target": target,
                        "plan_sha256": plan["plan_sha256"],
                        "store_row_sha256": hashlib.sha256(json.dumps(
                            row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                        ).hexdigest(),
                        "verdict": verdict,
                        "resolved": arm_of(decide(plan, reading)["resolved"])})
    if sum(row["verdict"] == VERIFIED for row in results) != 4:
        raise ValueError("expected four resolutions and four abstentions")
    return results


def propose_revision(root, store_rows, seq, rivals):
    """Propose one case's changes; an abstention licenses no ledger action."""
    if len(rivals) != 2 or len(set(rivals)) != 2:
        raise ValueError("expected two distinct rival UUIDs (feedback, replay)")
    if any(str(UUID(rival)) != rival for rival in rivals):
        raise ValueError("rival UUIDs must use canonical notation")
    evidence = next((row for row in replay(root, store_rows) if row["store_seq"] == seq), None)
    if evidence is None:
        raise ValueError(f"seq {seq} is not a captured turnover case")
    abstained = evidence["verdict"] == ABSTAIN
    return {
        "status": ABSTAIN if abstained else "PROPOSED",
        "rivals": dict(zip(ARMS, rivals)),
        "evidence": evidence,
        "revisions": [] if abstained else [
            {"hypothesis": rival, "status": "Supported" if arm == evidence["resolved"]
             else "Contradicted"}
            for arm, rival in zip(ARMS, rivals)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--store-log", type=Path)
    parser.add_argument("--store-seq", type=int, help="select one replayed case for a revision proposal")
    parser.add_argument("--rivals", nargs=2, metavar=("FEEDBACK_UUID", "REPLAY_UUID"))
    args = parser.parse_args()
    if (args.store_seq is not None or args.rivals is not None) and (
            args.store_log is None or args.store_seq is None or args.rivals is None):
        parser.error("a revision proposal requires --store-log, --store-seq and --rivals")
    try:
        if args.store_log is None:
            args.cases.mkdir()
            record(args.cases)
        else:
            with args.store_log.open() as handle:
                rows = []
                for line in handle:
                    if not line.endswith("\n"):
                        raise ValueError("unterminated store row")
                    rows.append(json.loads(line))
            result = (replay(args.cases, rows) if args.rivals is None else
                      propose_revision(args.cases, rows, args.store_seq, args.rivals))
            print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
