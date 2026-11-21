"""Interventions and evidence labels (mission P1 §5, R-P1.5).

Paired episodes share initial conditions and differ only by one **declared
kick**. The counterfactual run carries provenance source
``counterfactual:v0.1``; the executed run carries ``sim:v0.2``. An
``ObservationLedger`` refuses anything that is not an executed-simulation
observation, so no simulated or counterfactual event can silently become
history.

Evidence labels:
  OBSERVED        recorded physical event of the executed episode (the
                  observable/oracle split stays the existing boundary);
  INFERRED        a world/explanation consistent with the observable log;
  COUNTERFACTUAL  an outcome under altered conditions; never history;
  REFUTED         a candidate incompatible with the observable evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .epec import World, consistent_worlds
from .eventlog import Event
from .fixtures import truth_matches
from .sim import Init, Kick, SimConfig, SimEpisode, run

COUNTERFACTUAL_SOURCE = "counterfactual:v0.1"
OBSERVED_SOURCE = "sim:v0.2"


class Evidence(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    REFUTED = "REFUTED"


@dataclass(frozen=True)
class Intervention:
    t: int
    ball: int
    dv: Tuple[float, float]


def paired(
    config: SimConfig,
    seed: int,
    init: Init,
    intervention: Intervention,
    episode: int = 0,
) -> Tuple[SimEpisode, SimEpisode]:
    """Return (observed, counterfactual). Both are simulated; only the first
    may be recorded as history."""
    observed = run(config, seed, episode=episode, init=init)
    counterfactual = run(
        config,
        seed,
        episode=episode,
        init=init,
        kicks=(Kick(intervention.t, intervention.ball, intervention.dv),),
        source=COUNTERFACTUAL_SOURCE,
    )
    return observed, counterfactual


class ObservationLedger:
    """History accepts executed-simulation observations only."""

    def __init__(self) -> None:
        self._events: List[Event] = []

    def record(self, ep: SimEpisode) -> None:
        for e in ep.observable_log():
            if not e.provenance.source.startswith("sim:"):
                raise ValueError(
                    f"refusing to record a {e.provenance.source} event as history"
                )
            self._events.append(e)

    def events(self) -> List[Event]:
        return list(self._events)


def classify(ep: SimEpisode, proposed: Optional[List[World]] = None) -> dict:
    """Label the evidence: OBSERVED episodes, INFERRED worlds, REFUTED candidates."""
    consistent = consistent_worlds(ep.observable_log())
    truth = truth_matches(ep)
    allowed = {(w.matches, w.swaps) for w in consistent}
    refuted = [w for w in (proposed or []) if (w.matches, w.swaps) not in allowed]
    return {
        "OBSERVED": Evidence.OBSERVED,
        "INFERRED": consistent,
        "COUNTERFACTUAL": Evidence.COUNTERFACTUAL,
        "REFUTED": refuted,
        "truth_in_inferred": any(w.matches == truth for w in consistent),
    }
