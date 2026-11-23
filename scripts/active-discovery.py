"""Checkpoint A: record and replay a diagnosis from the actual observable event."""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_loop import BudgetExhausted, Session
from psychopomp.active_exit import readout
from psychopomp.active_receipt import (
    ABSTAIN, REFUSED, VERIFIED, commit, predictions_for, verify,
)
from psychopomp.eventlog import EventLog

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


def replay(case: Path) -> str:
    """Verify persisted adaptive evidence without running the simulator."""
    try:
        plan = json.loads((case / "plan.json").read_text(encoding="utf-8"))
        decision = json.loads((case / "decision.json").read_text(encoding="utf-8"))
        if plan != commit(policy="adaptive", selected="signed", prior=PRIOR,
                          predictions=predictions_for("signed")):
            return REFUSED
        evidence = (case / "events.jsonl").read_bytes()
        if decision["events_sha256"] != hashlib.sha256(evidence).hexdigest():
            return REFUSED
        events = tuple(EventLog.from_jsonl_lines(evidence.decode("utf-8").split("\n")))
        if any(event.observable is not True for event in events):
            return REFUSED
        return verify(plan, readout(events, plan["selected"]), decision)["verdict"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return REFUSED


def diagnose_and_verify(law: int, state: int, policy: str,
                        case: Path | None = None) -> tuple[dict, str]:
    if case is not None:
        if policy != "adaptive":
            raise ValueError("durable replay supports only the adaptive arm")
        case.mkdir()

    def seal(selected: str) -> None:
        plan.update(commit(policy=policy, selected=selected, prior=PRIOR,
                           predictions=predictions_for(selected)))
        if case is not None:
            write_record(case / "plan.json", plan)

    def capture(events: EventLog) -> None:
        events.to_jsonl(case / "events.jsonl")

    plan = {}
    run = Session().diagnose(law, state, policy=policy, before_acquire=seal,
                             capture=capture if case is not None else None)
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
    print("| law | state | selected | reading | resolved | verdict |")
    print("|---|---|---|---|---|---|")
    for law in LAWS:
        for state in STATES:
            case = root / f"law{law:+d}-state{state:+d}"
            run, verdict = diagnose_and_verify(law, state, "adaptive", case)
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
    args = parser.parse_args()
    if args.replay is not None:
        verdict = replay(args.replay)
        print(verdict)
        raise SystemExit({"VERIFIED": 0, "ABSTAIN": 1, "REFUSED": 2}[verdict])
    if args.record is not None:
        args.record.mkdir()
    raise SystemExit(main(args.record))
