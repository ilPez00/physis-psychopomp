"""R-P1.48 bounded loop: spend at most one diagnostic action, then stop.

The budget is the point. A controller that can keep probing will eventually
"resolve" any pair of laws by burning evidence until something separates them,
and that success says nothing about choosing a good experiment. `Session` makes
the spend explicit and refuses the second call rather than quietly taking one.
"""
from fractions import Fraction

from .active_design import best_probes, posterior
from .active_exit import acquire, rows

DIAGNOSTIC_BUDGET = 1
POLICIES = ("adaptive", "passive", "signed", "shuffled")
_PRIOR = (Fraction(1, 2), Fraction(1, 2))
_LAWS = (-1, 1)


class BudgetExhausted(RuntimeError):
    """Raised instead of taking a second diagnostic action."""


def _update(reading, laws=("signed",)):
    """Exact rational posterior over the rival laws for one channel reading."""
    if reading is None:
        return _PRIOR, None
    table = posterior(rows(laws[0]), reading)
    if table is None:
        return _PRIOR, None
    values = tuple(table[law] for law in _LAWS)
    certain = [law for law, value in zip(_LAWS, values) if value == 1]
    return values, (certain[0] if len(certain) == 1 else None)


class Session:
    """One diagnosis per instance; construct a new one per episode."""

    def __init__(self, budget: int = DIAGNOSTIC_BUDGET) -> None:
        if type(budget) is not int or budget < 0:
            raise ValueError("budget must be a non-negative integer")
        self._remaining = budget

    @property
    def remaining(self) -> int:
        return self._remaining

    def diagnose(self, law: int, state: int, *, policy: str = "adaptive") -> dict:
        if policy not in POLICIES:
            raise ValueError(f"unknown policy {policy!r}")
        if self._remaining <= 0:
            raise BudgetExhausted("the diagnostic budget is spent")
        selected = (best_probes({arm: rows(arm) for arm in ("passive", "signed")})[0]
                    if policy == "adaptive" else policy)
        self._remaining -= 1
        reading = acquire(law, state, "signed" if selected == "shuffled" else selected)
        if policy == "shuffled":
            # The prereg's frozen shuffle: exchange the rivals' signs for s < 0.
            # It preserves the readout's entropy and removes its law information.
            values, resolved = _PRIOR, None
            if reading is not None and state < 0:
                reading = -reading
        else:
            values, resolved = _update(reading)
        return {"policy": policy, "selected": selected, "reading": reading,
                "posterior": values, "resolved": resolved}
