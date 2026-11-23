"""R-P1.49: does the organization survive complete turnover?

Two roles, one invariant (|x1 - x2| <= 1), every initial component replaced, then
a perturbation. The `feedback` arm restores the invariant; the `open-loop` arm
replays the nominal transfer sequence, which on a balanced world is empty. The
only difference between the arms is whether anything reads the current imbalance —
not the inventory, the schedule, or the perturbation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

INVARIANT = 1
OBSERVE = (4, 5, 6)
PERTURB_TICK = 3


def balanced(loads: tuple[int, int]) -> bool:
    return abs(loads[0] - loads[1]) <= INVARIANT


def _feedback(loads: tuple[int, int]) -> tuple[int, int]:
    high, low = (0, 1) if loads[0] > loads[1] else (1, 0)
    if loads[high] - loads[low] >= 2:
        out = list(loads)
        out[high] -= 1
        out[low] += 1
        return tuple(out)
    return loads


@dataclass
class Run:
    arm: str
    target: int
    perturbation: int
    loads: dict[int, tuple[int, int]] = field(default_factory=dict)
    components: dict[int, tuple[int, int]] = field(default_factory=dict)
    transfers: dict[int, tuple[int, int] | None] = field(default_factory=dict)
    replaced: set[tuple[int, int]] = field(default_factory=set)

    @property
    def residence(self) -> int:
        return sum(balanced(self.loads[t]) for t in OBSERVE)

    @property
    def fully_replaced(self) -> bool:
        """True when both initial components were retired."""
        return self.replaced == {(1, 1), (2, 1)}

    def trajectory(self) -> tuple:
        return tuple(self.loads[t] for t in sorted(self.loads))


def run(arm: str, target: int = 1, perturbation: int = 0, *,
        relabel: bool = False, nominal: tuple | None = None) -> Run:
    """One episode. `nominal` is the feedback arm's undisturbed transfers."""
    if arm not in ("feedback", "open-loop"):
        raise ValueError("arm must be feedback or open-loop")
    if target not in (1, 2) or perturbation not in (0, 1, 2):
        raise ValueError("target/perturbation outside the declared cells")
    loads = (4, 4)
    components = {1: (1, 1), 2: (2, 1)}
    generation = {1: 1, 2: 1}
    out = Run(arm=arm, target=target, perturbation=perturbation)

    for tick in range(1, max(OBSERVE) + 1):
        if tick <= 2:
            # `replaced` holds the components that are *retired*, so the audit
            # can state "every initial component is gone" rather than "new ones
            # arrived" — the two are not the same claim.
            out.replaced.add(components[tick])
            generation[tick] += 1
            components[tick] = (tick, generation[tick])
        if tick == PERTURB_TICK and perturbation:
            bumped = list(loads)
            bumped[target - 1] += perturbation
            loads = tuple(bumped)

        if arm == "feedback":
            moved = _feedback(loads)
        else:
            replay = nominal.get(tick) if nominal else None
            moved = replay if replay is not None else loads
        out.transfers[tick] = moved if moved != loads else None
        loads = moved
        out.loads[tick] = loads

    if relabel:
        out.loads = {t: (x[1], x[0]) for t, x in out.loads.items()}
    return out
