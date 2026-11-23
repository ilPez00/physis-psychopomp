"""R-P1.50: the same one-probe loop, on the turnover pair.

The two hypotheses are `feedback` (a rule reads the imbalance) and `replay`
(nothing reads it). They predict **identical** observations on the undisturbed
world, so a passive observation buys no discrimination no matter how often it is
repeated. One post-disturbance observation separates them exactly.

Readings are integers (`x1 * 10 + x2`) because the receipt encodes readings as
integer keys; the law slots keep `active_receipt.RIVALS` order, where `-1` means
`feedback` and `+1` means `replay`.
"""
from __future__ import annotations

from .turnover import OBSERVE, run

ARMS = ("feedback", "replay")
SLOT = {"feedback": -1, "replay": 1}
PROBES = ("passive", "perturbed")
TICK = OBSERVE[0]


def encode(loads: tuple[int, int]) -> int:
    return loads[0] * 10 + loads[1]


def _observe(arm: str, probe: str, target: int = 1) -> int:
    if arm not in ARMS or probe not in PROBES:
        raise ValueError("arm or probe outside the declared catalogue")
    perturbation = 0 if probe == "passive" else 2
    nominal = run("feedback", target, 0)
    result = (run("feedback", target, perturbation) if arm == "feedback"
              else run("open-loop", target, perturbation, nominal=nominal.transfers))
    return encode(result.loads[TICK])


def rows(probe: str, target: int = 1) -> list[tuple[int, int]]:
    """What each hypothesis predicts for one probe: `(slot, reading)`."""
    readings = {arm: _observe(arm, probe, target) for arm in ARMS}
    return [(SLOT[arm], readings[arm]) for arm in ARMS]


def acquire(arm: str, probe: str, target: int = 1) -> int:
    """Run the true world once and hand back only the selected observation."""
    return _observe(arm, probe, target)


def arm_of(slot: int | None) -> str | None:
    return None if slot is None else {v: k for k, v in SLOT.items()}[slot]
