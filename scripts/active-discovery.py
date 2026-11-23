"""Checkpoint A transcript: one diagnosis, receipted and independently verified."""
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_loop import BudgetExhausted, Session
from psychopomp.active_receipt import (
    ABSTAIN, VERIFIED, commit, decide, predictions_for, verify,
)

LAWS = (-1, 1)
# The prior, not `run["posterior"]`: a receipt whose prior is already updated
# would look resolved before any evidence arrived.
PRIOR = (Fraction(1, 2), Fraction(1, 2))
STATES = (-3, -1, 1, 3)


def main() -> int:
    verified = abstained = refused = 0
    print("| law | state | selected | reading | resolved | verdict |")
    print("|---|---|---|---|---|---|")
    for law in LAWS:
        for state in STATES:
            run = Session().diagnose(law, state)
            # The plan is committed *before* the reading is spent on a decision,
            # so the verification cannot be written after seeing the answer.
            plan = commit(policy=run["policy"], selected=run["selected"],
                          prior=PRIOR,
                          predictions=predictions_for(run["selected"]))
            report = verify(plan, run["reading"], decide(plan, run["reading"]))
            good = (report["verdict"] == VERIFIED and run["resolved"] == law)
            verified += report["verdict"] == VERIFIED
            refused += report["verdict"] == "REFUSED"
            print(f"| {law:+d} | {state:+d} | {run['selected']} | {run['reading']} | "
                  f"{run['resolved']} | {report['verdict']}{'' if good else ' WRONG'} |")

    control = Session().diagnose(-1, -3, policy="shuffled")
    control_plan = commit(policy="shuffled", selected="shuffled", prior=PRIOR,
                          predictions=predictions_for("shuffled"))
    control_report = verify(control_plan, control["reading"],
                            decide(control_plan, control["reading"]))
    abstained += control_report["verdict"] == ABSTAIN

    session = Session()
    session.diagnose(-1, -3)
    try:
        session.diagnose(-1, -3)
        budget_refused = False
    except BudgetExhausted:
        budget_refused = True

    ok = (verified == 8 and refused == 0 and abstained == 1 and budget_refused
          and control["resolved"] is None)
    print()
    print(f"verified {verified}/8, refused {refused}, control verdict "
          f"{control_report['verdict']}, second action refused: {budget_refused}")
    print(f"discovery run: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
