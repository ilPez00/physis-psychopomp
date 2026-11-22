"""Self-model inference: recover the observer's own blind region from its log.

The law (`psychopomp/law.py`) predicts identifiability from a *known* blind
region. An observer does not know its own — it has a log of what it saw and where
it stopped seeing. This module turns that log into an estimate, and reports what
it cannot know (R-P1.29).

Evidence used, and only this:

- `enter_occ` at side `left`: the body was last seen just **outside** `x0`, within
  one step, so `pos.x + step` is an upper bound on `x0`;
- `exit_occ` at side `right`: first seen again just **outside** `x1`, so
  `pos.x - step` is a lower bound on `x1`;
- symmetric for `bottom` / `top` on `y`.

Taking the tightest bound in the corpus gives an estimate that is
**contained in** the true region, correct to one step, and `None` for any edge
the corpus never crossed. An edge never crossed is *unknown*, not guessed: an
observer that reports a blind spot bigger or smaller than the evidence supports is
claiming knowledge it does not have.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple

Rect = Tuple[float, float, float, float]
CROSSINGS = ("enter_occ", "exit_occ")


@dataclass(frozen=True)
class BlindEstimate:
    """What an observer can conclude about its own blind region."""

    step: float
    x0: Optional[float] = None
    x1: Optional[float] = None
    y0: Optional[float] = None
    y1: Optional[float] = None
    samples: Dict[str, int] = field(default_factory=dict)

    def unknown_edges(self) -> Tuple[str, ...]:
        return tuple(name for name in ("x0", "x1", "y0", "y1")
                     if getattr(self, name) is None)

    def as_rect(self) -> Optional[Rect]:
        """The estimate as a rectangle, or None when any edge is unknown."""
        if self.unknown_edges():
            return None
        return (self.x0, self.x1, self.y0, self.y1)  # type: ignore[return-value]

    def blind_membership(self, point: Tuple[float, float]) -> Optional[bool]:
        """True/False when the estimate determines it, None when it does not.

        A point covered by an unknown edge is reported as unknown rather than
        guessed, which is the difference between a calibrated observer and a
        confident one.
        """
        x, y = point
        if self.x0 is not None and x < self.x0:
            return False
        if self.x1 is not None and x > self.x1:
            return False
        if self.y0 is not None and y < self.y0:
            return False
        if self.y1 is not None and y > self.y1:
            return False
        if self.unknown_edges():
            return None
        return True


def estimate_blind_region(episodes: Iterable, step: float) -> BlindEstimate:
    """Tightest one-step-conservative estimate of the blind region from logs.

    `episodes` are `SimEpisode`s (or anything exposing `observable_log()`).
    Only observable events are read — an oracle log would be cheating, and is
    never touched here.
    """
    left_in: list = []
    right_out: list = []
    bottom_in: list = []
    top_out: list = []
    samples = {"left": 0, "right": 0, "bottom": 0, "top": 0}

    for episode in episodes:
        for event in episode.observable_log():
            if event.kind not in CROSSINGS:
                continue
            side = event.attrs.get("side")
            pos = event.attrs.get("pos")
            if pos is None:
                continue
            if event.kind == "enter_occ" and side == "left":
                left_in.append(pos[0] + step)
                samples["left"] += 1
            elif event.kind == "exit_occ" and side == "right":
                right_out.append(pos[0] - step)
                samples["right"] += 1
            elif event.kind == "enter_occ" and side == "bottom":
                bottom_in.append(pos[1] + step)
                samples["bottom"] += 1
            elif event.kind == "exit_occ" and side == "top":
                top_out.append(pos[1] - step)
                samples["top"] += 1

    return BlindEstimate(
        step=step,
        x0=min(left_in) if left_in else None,
        x1=max(right_out) if right_out else None,
        y0=min(bottom_in) if bottom_in else None,
        y1=max(top_out) if top_out else None,
        samples=samples,
    )
