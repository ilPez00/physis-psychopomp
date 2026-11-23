"""One-step Bayesian experiment selection over equally weighted outcome rows."""
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from fractions import Fraction
from math import fsum, log2

Rows = Sequence[tuple[int, int]]
EPS = 1e-12


def _entropy(counts: Counter) -> float:
    total = counts.total()
    return fsum(-p * log2(p) for p in (n / total for n in counts.values()))


def information_gain(rows: Rows) -> float:
    """Bits about the first coordinate from observing the second."""
    if not rows:
        raise ValueError("an experiment needs at least one outcome row")
    marginal: Counter = Counter()
    by_readout: dict[int, Counter] = defaultdict(Counter)
    for target, readout in rows:
        marginal[target] += 1
        by_readout[readout][target] += 1
    return _entropy(marginal) - fsum(
        counts.total() / len(rows) * _entropy(counts) for counts in by_readout.values()
    )


def best_probes(catalogue: Mapping[str, Rows]) -> tuple[str, ...]:
    """Return all positive-gain maximizers, sorted; empty means abstain."""
    gains = {name: information_gain(rows) for name, rows in catalogue.items()}
    best = max(gains.values(), default=0.0)
    return tuple(sorted(name for name, gain in gains.items()
                        if gain > EPS and best - gain <= EPS))


def posterior(rows: Rows, observed: int | None) -> dict[int, Fraction] | None:
    """Condition on one readout; missing or unsupported evidence yields no update."""
    if observed is None:
        return None
    hits = Counter(target for target, readout in rows if readout == observed)
    total = hits.total()
    return ({target: Fraction(hits[target], total) for target, _ in rows}
            if total else None)
