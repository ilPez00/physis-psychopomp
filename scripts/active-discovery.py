"""Checkpoint A transcript: one diagnosis, receipted and independently verified."""
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_loop import BudgetExhausted, Session
from psychopomp.active_receipt import (
    ABSTAIN, REFUSED, VERIFIED, commit, predictions_for, verify,
)

LAWS = (-1, 1)
# The prior, not `run["posterior"]`: a receipt whose prior is already updated
# would look resolved before any evidence arrived.
PRIOR = (Fraction(1, 2), Fraction(1, 2))
STATES = (-3, -1, 1, 3)


def diagnose_and_verify(law: int, state: int, policy: str) -> tuple[dict, str]:
    def seal(selected: str) -> None:
        plan.update(commit(policy=policy, selected=selected, prior=PRIOR,
                           predictions=predictions_for(selected)))

    plan = {}
    run = Session().diagnose(law, state, policy=policy, before_acquire=seal)
    if (run["policy"], run["selected"]) != (plan["policy"], plan["selected"]):
        return run, REFUSED
    decision = {key: run[key] for key in ("reading", "posterior", "resolved")}
    decision["plan_sha256"] = plan["plan_sha256"]
    return run, verify(plan, run["reading"], decision)["verdict"]


def main() -> int:
    verified = abstained = refused = 0
    print("| law | state | selected | reading | resolved | verdict |")
    print("|---|---|---|---|---|---|")
    for law in LAWS:
        for state in STATES:
            run, verdict = diagnose_and_verify(law, state, "adaptive")
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
    raise SystemExit(main())
