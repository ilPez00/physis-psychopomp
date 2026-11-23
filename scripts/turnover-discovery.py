"""C3: run the R-P1.48 loop and receipt against the turnover pair."""
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_design import best_probes, information_gain
from psychopomp.active_receipt import commit, decide, predictions_from, verify_against
from psychopomp.turnover_evidence import ARMS, acquire, arm_of, rows

PRIOR = (Fraction(1, 2), Fraction(1, 2))
TARGETS = (1, 2)


def main() -> int:
    resolved = abstained = 0
    print("| arm | role | probe | gain (bits) | reading | resolves to | verdict |")
    print("|---|---|---|---|---|---|---|")
    for target in TARGETS:
        catalogue = {probe: rows(probe, target) for probe in ("passive", "perturbed")}
        gains = {probe: information_gain(table) for probe, table in catalogue.items()}
        pick = best_probes(catalogue)
        for arm in ARMS:
            for probe in ("passive", "perturbed"):
                table = catalogue[probe]
                # The receipt names the probe actually observed, not the one the
                # controller preferred; otherwise a passive run would claim the
                # informative plan.
                plan = commit(policy="adaptive" if pick and pick[0] == probe else "fixed",
                              selected=probe, prior=PRIOR,
                              predictions=predictions_from(table))
                reading = acquire(arm, probe, target)
                decision = decide(plan, reading)
                report = verify_against(plan, reading, decision, predictions_from(table))
                good = (arm_of(decision["resolved"]) == arm
                        if probe == "perturbed" else decision["resolved"] is None)
                resolved += bool(good and probe == "perturbed")
                abstained += bool(good and probe == "passive")
                print(f"| {arm} | {target} | {probe} | {gains[probe]:.0f} | {reading} | "
                      f"{arm_of(decision['resolved'])} | {report['verdict']}"
                      f"{'' if good else ' WRONG'} |")

    ok = resolved == 4 and abstained == 4
    print()
    print(f"adaptive pick: {best_probes({p: rows(p) for p in ('passive','perturbed')})}; "
          f"resolved {resolved}/4, abstained {abstained}/4")
    print(f"turnover discovery: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
