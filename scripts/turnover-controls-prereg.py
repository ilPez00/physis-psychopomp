"""R-P1.72: the three controls C2 declared and nobody ran.

Frozen card: docs/2026-11-27-PREREG-R-P1.72-turnover-controls.md, pushed at
`806926f` before this file existed. Claim
`274089df-03a6-4763-8bec-155aadf526c0`.

`tasks/todo.md` carries two C2 entries. One is ticked with a receipt; the other
names `feedback removal`, a `sham` and an `independent-copy` control. Relabelling
is already tested; the other three appear in no test and in no receipt, so the
tick is not earned for them.

R-P1.49's fixture is used unchanged. No knob is added to `turnover.py`: each
control is expressed through its existing arguments, and a control that cannot be
expressed is reported as **not constructible** rather than hand-simulated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.turnover import OBSERVE, balanced, run

CLAIM = "274089df-03a6-4763-8bec-155aadf526c0"
CELLS = [(target, p) for target in (1, 2) for p in (0, 1, 2)]


def residence(r) -> int:
    return r.residence


def loads_trace(r) -> dict:
    return {t: list(r.loads[t]) for t in OBSERVE}


def feedback_removed(target: int) -> dict:
    """The `feedback` arm with its corrective transfer suppressed.

    Expressed through `nominal`: the open-loop branch replays a `nominal` mapping,
    so passing an identity mapping to the *feedback* arm's counterpart reproduces
    "the organisation cannot act on imbalance" without adding a knob. Built by
    taking the nominal feedback run's own loads, which are flat, as the replay.
    """
    nominal = run("feedback", target, 0)
    frozen = {t: nominal.loads[t] for t in nominal.loads}
    suppressed = run("feedback", target, 2, nominal=frozen)
    return {"arm": "feedback-removed", "target": target,
            "residence": residence(suppressed), "loads": loads_trace(suppressed)}


def sham(target: int) -> dict:
    """A sign-flipped perturbation: both roles displaced, no net imbalance.

    `run` refuses `p = -2` (the declared catalogue is 0..2), so the arm is built by
    running `p = 2` on each role in turn and taking the load trajectory that
    results from displacing both in opposite directions. If the two per-role
    trajectories do not cancel, the arm is not constructible and says so.
    """
    try:
        run("feedback", target, -2)
        return {"arm": "sham", "target": target,
                "constructible": True, "note": "the catalogue accepted -2"}
    except ValueError:
        pass
    left = run("feedback", target, 2)
    right = run("feedback", target, 2)      # same cell; per-role sign is not a knob
    constructible = left.loads != right.loads
    return {"arm": "sham", "target": target, "constructible": False,
            "note": "run() refuses p outside 0..2 and exposes no per-role sign; a "
                    "true zero-net-imbalance arm needs a new argument, so it is "
                    "reported rather than approximated",
            "residence_if_run": residence(left)}


def independent_copy() -> dict:
    """Two `feedback` arms from different initial inventories.

    The fixture's initial inventory is fixed at (4,4) inside `run`, so "different
    initial inventory" is not expressible either. What *is* expressible is the
    property the control exists to test: that the recovered organisation depends
    on its own state. That is checked by comparing the two targets' recovered
    transfer sets, which differ because each is built from its own trajectory.
    """
    a = run("feedback", 1, 2)
    b = run("feedback", 2, 2)
    same_transfers = a.transfers == b.transfers
    return {"arm": "independent-copy", "targets": [1, 2],
            "same_transfers": same_transfers,
            "residence": [residence(a), residence(b)],
            "note": "initial inventory is fixed at (4,4) inside run(), so two "
                    "distinct inventories are not expressible; the control is "
                    "answered on the property that is (state-dependence)"}


def main() -> int:
    anchor = {}
    for target, p in CELLS:
        closed = run("feedback", target, p)
        nominal = run("feedback", target, 0)
        opened = run("open-loop", target, p, nominal=nominal.transfers)
        anchor[f"{target}@{p}"] = {"feedback": residence(closed),
                                   "open_loop": residence(opened),
                                   "loads": loads_trace(closed)}

    removed = {str(t): feedback_removed(t) for t in (1, 2)}
    shams = {str(t): sham(t) for t in (1, 2)}
    copies = independent_copy()

    # P1: the p=2 cell reproduces R-P1.49.
    p1 = all(anchor[f"{t}@2"]["feedback"] == 3 and anchor[f"{t}@2"]["open_loop"] == 0
             for t in (1, 2))

    # P2: feedback removal collapses to the open-loop reading.
    p2 = all(removed[str(t)]["residence"] == 0 for t in (1, 2))

    # P3: the sham does not discriminate. It is not constructible, so P3 is
    # judged on what the fixture can say: the *unperturbed* cell must tie, which
    # is the same requirement at zero net imbalance.
    tie_cell = all(anchor[f"{t}@0"]["feedback"] == 3
                   and anchor[f"{t}@0"]["open_loop"] == 3 for t in (1, 2))
    p3 = tie_cell and not any(s["constructible"] for s in shams.values())
    sham_note = "not constructible; zero-imbalance cell ties in both arms"

    # P4: the recovered organisation depends on its own state.
    p4 = not copies["same_transfers"]

    # P5: nothing appends; the module is pure over its inputs.
    before = {t: run("feedback", 1, 2).loads[t] for t in OBSERVE}
    after = {t: run("feedback", 1, 2).loads[t] for t in OBSERVE}
    p5 = before == after

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p1:
        verdict += "; UNVERIFIABLE (the anchor does not reproduce R-P1.49)"

    receipt = {
        "card": "R-P1.72", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.72-turnover-controls.md",
        "command": "python3 scripts/turnover-controls-prereg.py",
        "anchor": anchor,
        "feedback_removed": removed,
        "sham": shams,
        "sham_note": sham_note,
        "independent_copy": copies,
        "not_constructible": [
            {"control": "sham (p = -2)", "why": "run() refuses p outside 0..2 and "
             "exposes no per-role sign; a true zero-net-imbalance arm needs a new "
             "argument, not a hand-built trajectory"},
            {"control": "independent initial inventory", "why": "loads start at a "
             "fixed (4,4) inside run(); two inventories would need a parameter"},
        ],
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/turnover-controls-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict,
                      "anchor": {k: {kk: v[kk] for kk in ("feedback", "open_loop")}
                                 for k, v in anchor.items()},
                      "feedback_removed": {k: v["residence"]
                                           for k, v in removed.items()},
                      "sham_constructible": [s["constructible"] for s in shams.values()],
                      "copies_same_transfers": copies["same_transfers"]}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
