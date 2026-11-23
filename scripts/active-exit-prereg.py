"""R-P1.48: check actual exits against the frozen analytical response table."""
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.active_design import posterior
from psychopomp.active_exit import SHIFTED, STATES, _run_case, readout

PRIOR = {-1: Fraction(1, 2), 1: Fraction(1, 2)}


def main():
    reads = {}
    failures = []
    cells = tuple(product((-1, 0, 1), enumerate(STATES), (0, 2)))
    for m, (i, s), u in cells:
        events = tuple(_run_case(m, s, u).observable_log())
        probes = ("passive",) if u == 0 else ("magnitude", "signed")
        scalars = {probe: readout(events, probe) for probe in probes}
        d = s if u == 0 else SHIFTED[m][i]
        if (None in scalars.values()
                or abs(events[0].attrs["pos"][0] - 60.5) > 1e-6
                or abs(events[0].attrs["pos"][1] - (50 + d)) > 1e-6):
            failures.append((m, s, u, [(e.kind, e.t, e.attrs.get("pos")) for e in events]))
        else:
            reads[m, s, u] = scalars
    n = len(cells)
    print(f"X1: {'FALSIFIED' if failures else 'UPHELD'}; right exits matched "
          f"{n - len(failures)}/{n}")
    if failures:
        print(f"capacity failures: {failures}; X2/X3 NOT SCORED")
        return 1

    rivals = tuple(product((-1, 1), STATES))
    arms = {probe: [(m, reads[m, s, u][probe]) for m, s in rivals]
            for probe, u in (("passive", 0), ("signed", 2), ("magnitude", 2))}
    nominal = [reads[0, s, 2]["magnitude"] for s in STATES]
    rival_mags = arms["magnitude"]
    expected_nominal = {1_000_000, 3_000_000}
    expected_rival = {1_620_000, 3_620_000, 5_620_000, 7_620_000}
    rejects = sum(y in expected_rival and y not in nominal for _, y in rival_mags)
    false_alarms = sum(y not in expected_nominal for y in nominal)
    x2 = (rejects == 8 and false_alarms == 0 and set(nominal) == expected_nominal
          and {y for _, y in rival_mags} == expected_rival
          and all(posterior(rival_mags, y) == PRIOR for _, y in rival_mags)
          and all(posterior(rival_mags, y) is None for y in (*nominal, 99)))
    print(f"X2: {'UPHELD' if x2 else 'FALSIFIED'}; rival nominal rejections "
          f"{rejects}/{len(rivals)}; nominal false rejections {false_alarms}/{len(nominal)}")

    signed = dict(zip(rivals, (y for _, y in arms["signed"])))
    arms["shuffled"] = [(m, signed[(-m if s < 0 else m), s]) for m, s in rivals]
    resolved = {probe: sum(posterior(rows, y) == {-m: Fraction(0), m: Fraction(1)}
                           for m, y in rows) for probe, rows in arms.items()}
    x3 = (resolved == {"passive": 0, "signed": 8, "magnitude": 0, "shuffled": 0}
          and all(posterior(arms[probe], y) == PRIOR for probe in ("passive", "magnitude", "shuffled")
                  for _, y in arms[probe])
          and sorted(y for _, y in arms["shuffled"]) == sorted(signed.values()))
    print(f"X3: {'UPHELD' if x3 else 'FALSIFIED'}; correct resolutions out of {len(rivals)}: {resolved}")
    # X4 (malformed/duplicate/forged logs) needs surrogate events this script
    # cannot build without the fixture's own shape: tests/ covers it and this
    # run does NOT score it.
    print("X4: NOT SCORED by this script (covered by tests/test_active_exit_fixture.py)")
    print(f"prereg run: {'PASS' if x2 and x3 else 'FAIL'} (X1-X3)")
    return 0 if x2 and x3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
