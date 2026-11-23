"""R-P1.49: replay the frozen turnover card and print every cell."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.turnover import OBSERVE, balanced, run

TARGETS = (1, 2)
PERTURBATIONS = (0, 1, 2)


def main() -> int:
    rows, verdicts = {}, []
    print("| target | p | arm | loads at observe ticks | residence |")
    print("|---|---|---|---|---|")
    for target in TARGETS:
        nominal = run("feedback", target, 0)
        for p in PERTURBATIONS:
            for arm in ("feedback", "open-loop"):
                result = (run("feedback", target, p) if arm == "feedback"
                          else run("open-loop", target, p, nominal=nominal.transfers))
                rows[target, p, arm] = result
                seen = " ".join(str(result.loads[t]) for t in OBSERVE)
                print(f"| {target} | {p} | {arm} | {seen} | {result.residence}/3 |")

    nominal = rows[1, 0, "feedback"]
    o1 = (nominal.fully_replaced
          and rows[1, 0, "open-loop"].fully_replaced
          and nominal.trajectory() == rows[1, 0, "open-loop"].trajectory()
          and rows[1, 0, "open-loop"].residence == 3
          and all(balanced(nominal.loads[t]) for t in OBSERVE))
    o2 = all(rows[t, 2, "feedback"].residence == 3
             and rows[t, 2, "open-loop"].residence == 0 for t in TARGETS)
    o3 = all(rows[t, p, arm].residence == 3
             for t in TARGETS for p in (0, 1) for arm in ("feedback", "open-loop"))
    o4 = all(
        run("feedback", t, 2, relabel=True).residence == 3
        and rows[t, 2, "open-loop"].replaced == rows[t, 2, "feedback"].replaced
        for t in TARGETS)

    print()
    print(f"O1 capacity and identical undisturbed trajectories: {'UPHELD' if o1 else 'FALSIFIED'}")
    print(f"O2 +2 on either role separates feedback from open-loop: {'UPHELD' if o2 else 'FALSIFIED'}")
    print(f"O3 +1 and the sham must not discriminate: {'UPHELD' if o3 else 'FALSIFIED'}")
    print(f"O4 the verdict is structural, not nominal: {'UPHELD' if o4 else 'FALSIFIED'}")
    ok = all((o1, o2, o3, o4))
    print(f"prereg run: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
