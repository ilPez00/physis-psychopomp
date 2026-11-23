"""Checkpoint A: record and replay a diagnosis from the actual observable event."""
import argparse
import hashlib
import json
import os
import secrets
import sys
import tempfile
from dataclasses import asdict, replace
from fractions import Fraction
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_loop import BudgetExhausted, Session
from psychopomp.active_exit import readout
from psychopomp.active_receipt import (
    ABSTAIN, REFUSED, VERIFIED, commit, decide, digest, predictions_for, verify,
)
from psychopomp.eventlog import EventLog
from psychopomp.export import SCHEMA

LAWS = (-1, 1)
# The prior, not `run["posterior"]`: a receipt whose prior is already updated
# would look resolved before any evidence arrived.
PRIOR = (Fraction(1, 2), Fraction(1, 2))
STATES = (-3, -1, 1, 3)


def write_record(path: Path, record: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def case_plan(policy: str, selected: str, episode: int | None) -> dict:
    plan = commit(policy=policy, selected=selected, prior=PRIOR,
                  predictions=predictions_for(selected))
    if episode is not None:
        plan["episode"] = episode
        plan["plan_sha256"] = digest(plan)
    return plan


def load_case(case: Path):
    plan = json.loads((case / "plan.json").read_text(encoding="utf-8"))
    decision = json.loads((case / "decision.json").read_text(encoding="utf-8"))
    episode = plan.get("episode")  # older local receipts did not pin an episode
    if episode is not None and (type(episode) is not int or not 0 <= episode < 2**63):
        raise ValueError("invalid episode")
    if plan != case_plan("adaptive", "signed", episode):
        raise ValueError("not the frozen adaptive plan")
    evidence = (case / "events.jsonl").read_bytes()
    if decision["events_sha256"] != hashlib.sha256(evidence).hexdigest():
        raise ValueError("event digest mismatch")
    events = tuple(EventLog.from_jsonl_lines(evidence.decode("utf-8").split("\n")))
    if any(event.observable is not True or not event.provenance.source.startswith("sim:")
           or (episode is not None and event.provenance.episode != episode) for event in events):
        raise ValueError("event is not observed evidence from this episode")
    return plan, decision, events


def replay(case: Path) -> str:
    """Verify persisted adaptive evidence without running the simulator."""
    try:
        plan, decision, events = load_case(case)
        return verify(plan, readout(events, plan["selected"]), decision)["verdict"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return REFUSED


def observation_record(plan, decision, events) -> dict:
    if "episode" not in plan or len(events) != 1:
        raise ValueError("export requires one observed exit with a sealed episode")
    if verify(plan, readout(events, plan["selected"]), decision)["verdict"] != VERIFIED:
        raise ValueError("export requires a verified case")
    event = events[0]
    return {"schema": SCHEMA, "subject": f"episode:{event.provenance.seed}:{plan['episode']}",
            "kind": event.kind, "at": round(event.t * event.attrs["dt"], 6),
            "props": event.attrs, "provenance": asdict(event.provenance),
            "evidence": "OBSERVED", "seq": event.seq}


def export_case(case: Path) -> dict:
    return observation_record(*load_case(case))


def checked_store_evidence(case: Path, log: Path) -> dict:
    plan, decision, events = load_case(case)
    expected = observation_record(plan, decision, events)
    key = f"psychopomp:{expected['subject']}#{expected['seq']}"
    matches = []
    with log.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.endswith("\n"):
                raise ValueError("unterminated store row")
            row = json.loads(line)
            if row.get("produced_by") == key:
                matches.append(row)
    if len(matches) != 1:
        raise ValueError(f"expected one stored row for {key}, found {len(matches)}")
    row = matches[0]
    props = row["props"]
    observed = {
        "schema": props["psychopomp_schema"],
        "subject": row["subject"],
        "kind": props["psychopomp_kind"],
        "at": float(props["at_seconds"]),
        "props": json.loads(props["psychopomp_props"]),
        "provenance": json.loads(props["psychopomp_provenance"]),
        "evidence": props["psychopomp_evidence"],
        "seq": expected["seq"],  # the producer seq is carried by the exact key
    }
    if row["source"] != "psychopomp" or observed != expected:
        raise ValueError("stored payload differs from the captured observation")
    if type(row["seq"]) is not int or row["seq"] < 0:
        raise ValueError("invalid store sequence")
    event = replace(events[0], attrs=observed["props"])
    reading = readout((event,), plan["selected"])
    verdict = verify(plan, reading, decision)["verdict"]
    return {
        "verdict": verdict,
        "resolved": decide(plan, reading)["resolved"] if verdict == VERIFIED else None,
        "store_seq": row["seq"],
        "producer_key": key,
        "store_row_sha256": hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
        "plan_sha256": plan["plan_sha256"],
    }


def replay_store(case: Path, log: Path) -> tuple[str, int]:
    evidence = checked_store_evidence(case, log)
    return evidence["verdict"], evidence["store_seq"]


def propose_belief_revision(case: Path, log: Path, rivals: dict[int, str]) -> dict:
    """Bind a pair of case-scoped rivals to verified evidence; never write either store."""
    if set(rivals) != set(LAWS) or len(set(rivals.values())) != len(LAWS):
        raise ValueError("two distinct rival UUIDs are required for laws -1 and +1")
    if any(str(UUID(value)) != value for value in rivals.values()):
        raise ValueError("rival UUIDs must use canonical notation")
    evidence = checked_store_evidence(case, log)
    if evidence["verdict"] != VERIFIED:
        raise ValueError("a revision requires a resolved, verified observation")
    return {
        "status": "PROPOSED",
        "evidence": evidence,
        "revisions": [
            {"hypothesis": rivals[law],
             "status": "Supported" if law == evidence["resolved"] else "Contradicted"}
            for law in LAWS
        ],
    }


def diagnose_and_verify(law: int, state: int, policy: str, case: Path | None = None, *,
                        episode: int = 0) -> tuple[dict, str]:
    if case is not None:
        if policy != "adaptive":
            raise ValueError("durable replay supports only the adaptive arm")
        case.mkdir()

    def seal(selected: str) -> None:
        plan.update(case_plan(policy, selected, episode if case is not None else None))
        if case is not None:
            write_record(case / "plan.json", plan)

    def capture(events: EventLog) -> None:
        events.to_jsonl(case / "events.jsonl")

    plan = {}
    run = Session().diagnose(law, state, policy=policy, before_acquire=seal,
                             capture=capture if case is not None else None, episode=episode)
    if (run["policy"], run["selected"]) != (plan["policy"], plan["selected"]):
        return run, REFUSED
    decision = {key: run[key] for key in ("reading", "posterior", "resolved")}
    decision["plan_sha256"] = plan["plan_sha256"]
    if case is not None:
        decision["posterior"] = [value.as_integer_ratio() for value in run["posterior"]]
        decision["events_sha256"] = hashlib.sha256((case / "events.jsonl").read_bytes()).hexdigest()
        write_record(case / "decision.json", decision)
        return run, replay(case)
    return run, verify(plan, run["reading"], decision)["verdict"]


def main(root: Path | None = None) -> int:
    if root is None:
        with tempfile.TemporaryDirectory(prefix="psychopomp-discovery-") as directory:
            return main(Path(directory))
    verified = abstained = refused = 0
    episode = secrets.randbits(60) << 3
    print("| law | state | selected | reading | resolved | verdict |")
    print("|---|---|---|---|---|---|")
    for law in LAWS:
        for state in STATES:
            case = root / f"law{law:+d}-state{state:+d}"
            run, verdict = diagnose_and_verify(law, state, "adaptive", case, episode=episode)
            episode += 1
            good = verdict == VERIFIED and run["resolved"] == law
            verified += good
            refused += verdict == REFUSED
            print(f"| {law:+d} | {state:+d} | {run['selected']} | {run['reading']} | "
                  f"{run['resolved']} | {verdict}{'' if good else ' WRONG'} |")
            control, verdict = diagnose_and_verify(law, state, "shuffled")
            abstained += verdict == ABSTAIN and control["resolved"] is None

    session = Session()
    session.diagnose(-1, -3)
    try:
        session.diagnose(-1, -3)
        budget_refused = False
    except BudgetExhausted:
        budget_refused = True

    cells = len(LAWS) * len(STATES)
    ok = verified == cells and refused == 0 and abstained == cells and budget_refused
    print()
    print(f"verified {verified}/{cells}, refused {refused}, shuffled abstained "
          f"{abstained}/{cells}, second action refused: {budget_refused}")
    print(f"discovery run: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--record", type=Path, help="write all cases into a new directory")
    mode.add_argument("--replay", type=Path, help="verify one recorded case without simulation")
    mode.add_argument("--export", type=Path, help="export the verified cases recorded in this directory")
    parser.add_argument("--store-log", type=Path, help="with --replay, cite the matching Physis row")
    parser.add_argument("--rivals", nargs=2, metavar=("NEGATIVE_ID", "POSITIVE_ID"),
                        help="with --store-log, propose revisions for two case-scoped rivals")
    args = parser.parse_args()
    if args.store_log is not None and args.replay is None:
        parser.error("--store-log requires --replay")
    if args.rivals is not None and args.store_log is None:
        parser.error("--rivals requires --store-log")
    if args.export is not None:
        records = [export_case(case) for case in sorted(args.export.iterdir()) if case.is_dir()]
        if not records or len({row["subject"] for row in records}) != len(records):
            parser.error("expected a nonempty set of distinct verified episodes")
        print("\n".join(json.dumps(row, sort_keys=True, allow_nan=False) for row in records))
        raise SystemExit(0)
    if args.replay is not None:
        if args.store_log is None:
            verdict = replay(args.replay)
            print(verdict)
        else:
            try:
                if args.rivals is not None:
                    proposal = propose_belief_revision(
                        args.replay, args.store_log, dict(zip(LAWS, args.rivals)))
                    print(json.dumps(proposal, sort_keys=True))
                    raise SystemExit(0)
                verdict, seq = replay_store(args.replay, args.store_log)
                print(json.dumps({"verdict": verdict, "store_seq": seq}))
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
                verdict = REFUSED
                print(json.dumps({"verdict": verdict, "detail": str(error)}))
        raise SystemExit({"VERIFIED": 0, "ABSTAIN": 1, "REFUSED": 2}[verdict])
    if args.record is not None:
        args.record.mkdir()
    raise SystemExit(main(args.record))
