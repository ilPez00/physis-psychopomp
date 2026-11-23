"""R-P1.47: replay the frozen finite active-law experiment."""
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_design import EPS, best_probes, information_gain, posterior

ARMS = ("passive", "signed", "magnitude", "shuffled")
STATES = (-3, -1, 1, 3)
EXPECTED = (
    (-3, -1, 7, 1), (-1, -1, 5, 1), (1, -1, 3, -1), (3, -1, 1, -1),
    (-3, 1, 1, -1), (-1, 1, 3, -1), (1, 1, 5, 1), (3, 1, 7, 1),
)
PRIOR = {-1: Fraction(1, 2), 1: Fraction(1, 2)}


def response(law, state):
    y = state + 4 * law
    signed = 1 if y > 0 else -1
    return state, signed, abs(y), -signed if state < 0 else signed


def calibration(reading, nominal_support, rows):
    rivals = posterior(rows, reading)
    if rivals is None:
        return "out_of_support", None
    return ("compatible" if reading in nominal_support else "rejected"), rivals


def main():
    cases = tuple(product((-1, 1), STATES))
    table = tuple(response(*case) for case in cases)
    n = len(cases)

    def catalogue(target):
        return {name: [(case[target], row[col]) for case, row in zip(cases, table)]
                for col, name in enumerate(ARMS)}

    laws, states = catalogue(0), catalogue(1)
    nominal = [response(0, state)[2] for state in STATES]
    cal = [calibration(row[2], nominal, laws["magnitude"]) for row in table]
    rejects = sum(status == "rejected" for status, _ in cal)
    false_alarms = sum(calibration(y, nominal, laws["magnitude"])[0] != "compatible"
                       for y in nominal)
    e1 = (table == EXPECTED and rejects == 4 and false_alarms == 0
          and all(belief == PRIOR for _, belief in cal)
          and calibration(99, nominal, laws["magnitude"]) == ("out_of_support", None))
    print(f"E1: {'UPHELD' if e1 else 'FALSIFIED'}; nominal mismatches {rejects}/{n}, "
          f"false alarms {false_alarms}/{len(nominal)}")
    if not e1:
        print("E2/E3: NOT SCORED")
        return 1

    active = {arm: laws[arm] for arm in ARMS[:3]}
    state = {arm: states[arm] for arm in active}
    # Choosing for readout entropy is choosing for its own information content.
    entropy = {arm: [(y, y) for _, y in rows] for arm, rows in active.items()}
    law_pick, state_pick, entropy_picks = map(best_probes, (active, state, entropy))
    gain = {arm: (information_gain(rows), information_gain(state[arm]))
            for arm, rows in active.items()}
    random_gain = Fraction(sum(round(law) for law, _ in gain.values()), len(active))
    expected = {"passive": (0, 2), "signed": (1, 0), "magnitude": (0, 1)}
    e2 = (all(abs(a - b) <= EPS for name, scores in gain.items()
              for a, b in zip(scores, expected[name]))
          and law_pick == ("signed",) and state_pick == ("passive",)
          and entropy_picks == ("magnitude", "passive") and random_gain == Fraction(1, 3)
          and all(best_probes({name: rows[::-1] for name, rows in reversed(cat.items())})
                  == best_probes(cat) for cat in (active, state, entropy)))
    print(f"E2: {'UPHELD' if e2 else 'FALSIFIED'}; gains {gain}; random={random_gain}")

    updates = {name: [posterior(rows, y) for _, y in rows] for name, rows in laws.items()}
    signed_correct = sum(p is not None and p[law] == 1
                         for (law, _), p in zip(cases, updates["signed"]))
    unchanged = {name: sum(p == PRIOR for p in updates[name])
                 for name in ("passive", "magnitude", "shuffled")}
    no_signed = {name: active[name] for name in ("passive", "magnitude")}
    e3 = (signed_correct == n and all(count == n for count in unchanged.values())
          and not best_probes(no_signed)
          and not best_probes({**no_signed, "signed": laws["shuffled"]})
          and all(posterior(rows, y) is None for rows in laws.values() for y in (None, 99)))
    print(f"E3: {'UPHELD' if e3 else 'FALSIFIED'}; signed correct {signed_correct}/{n}; "
          f"unchanged posteriors {unchanged}/{n}")
    print(f"prereg run: {'PASS' if e2 and e3 else 'FAIL'}")
    return 0 if e2 and e3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
