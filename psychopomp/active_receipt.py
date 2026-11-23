"""Digest-bound receipts for the R-P1.48 exit fixture.

A receipt binds a *committed plan* to an *evidenced reading* by SHA-256, so a
decision can be checked by someone who never ran the fixture: `verify` recomputes
the posterior from the plan alone and refuses anything that does not bind.

This module reaches only the fixture's frozen table (`active_exit`) and the
exact-rational update (`active_design`). It never imports the session/controller
loop, because the point of a receipt is that the checker does not have to trust
the run.

Record shape (JSON-native, so `digest` is a plain SHA-256 over `json.dumps`):

    {"policy": str,
     "selected": str,
     "prior": [n, d],
     "predictions": {"<reading>": {"<law>": [n, d]}},
     "plan_sha256": hex}

Predictions are labelled by law rather than by slot position so the record names
its own laws; `commit` maps the caller's two-slot pairs onto `RIVALS`.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any

from . import active_design, active_exit

#: Slot order of a `commit(prior=..., predictions=...)` pair: the two rival laws.
RIVALS = (-1, 1)

#: Channels the frozen fixture defines; anything else cannot be verified.
CHANNELS = ("passive", "signed", "magnitude")

VERIFIED = "VERIFIED"
ABSTAIN = "ABSTAIN"
REFUSED = "REFUSED"


def digest(record: dict) -> str:
    """SHA-256 over the canonical JSON of a record, ignoring its own digest key."""
    body = {key: value for key, value in record.items()
            if not (isinstance(key, str) and key.endswith("_sha256"))}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def predictions_from(rows: list[tuple[int, int]]) -> dict[int, tuple[Fraction, Fraction]]:
    """Posterior over the rows' first coordinate, per attainable reading."""
    return {
        reading: tuple(active_design.posterior(rows, reading)[target] for target in RIVALS)
        for reading in {reading for _, reading in rows}
    }


def predictions_for(selected: str) -> dict[int, tuple[Fraction, Fraction]]:
    """The fixture's own posterior per attainable reading for one channel.

    This is what makes a receipt checkable rather than self-consistent: a plan
    that carries a different table is refused, however well its digest closes.
    """
    if selected == "shuffled":
        readings = {reading for _, reading in active_exit.rows("signed")}
        return {reading: (Fraction(1, 2), Fraction(1, 2)) for reading in readings}
    if selected not in CHANNELS:
        raise ValueError(f"unknown channel {selected!r}")
    return predictions_from(active_exit.rows(selected))


def commit(*, policy: str, selected: str, prior: tuple[Fraction, Fraction],
           predictions: dict[int, tuple[Fraction, Fraction]]) -> dict:
    """Freeze a plan and stamp it with its own digest."""
    if type(policy) is not str or not policy:
        raise ValueError("policy must be a non-empty string")
    if type(selected) is not str or not selected:
        raise ValueError("selected must be a non-empty string")
    if not isinstance(predictions, dict) or not predictions:
        raise ValueError("predictions must map at least one reading to posteriors")
    prior_pair = _pair(prior, "prior")
    encoded: dict[str, dict[str, list[int]]] = {}
    for reading, value in predictions.items():
        if type(reading) is not int:
            raise ValueError("a prediction key is not an integer reading")
        pairs = _pair(value, f"predictions[{reading}]")
        encoded[str(reading)] = {str(law): _encode(posterior)
                                 for law, posterior in zip(RIVALS, pairs)}
    record = {
        "policy": policy,
        "selected": selected,
        "prior": [_encode(value) for value in prior_pair],
        "predictions": encoded,
    }
    record["plan_sha256"] = digest(record)
    return record


def decide(plan: dict, reading: int | None) -> dict:
    """The posterior this plan licenses for one reading; no evidence means no update."""
    fields = _fields(plan)
    prior = fields["prior"]
    if reading is None:
        return {"plan_sha256": fields["sha"], "reading": None,
                "posterior": prior, "resolved": None}
    if type(reading) is not int:
        raise ValueError("reading is not an integer")
    entry = _entry(fields["predictions"], reading)
    if entry is None:
        return {"plan_sha256": fields["sha"], "reading": reading,
                "posterior": prior, "resolved": None}
    laws, posterior = _posterior(entry, f"predictions[{reading}]")
    return {"plan_sha256": fields["sha"], "reading": reading,
            "posterior": posterior, "resolved": _resolved(laws, posterior)}


def verify(plan: dict, reading: int | None, decision: dict) -> dict:
    """Recompute from the plan, the reading and this fixture's frozen table."""
    try:
        if plan.get("selected") is None:
            return _refuse("plan names no channel")
        frozen = predictions_for(plan["selected"])
    except (ValueError, TypeError):
        return _refuse("plan names a channel the frozen fixture does not define")
    except AttributeError:
        return _refuse("plan is not a record")
    return verify_against(plan, reading, decision, frozen)


def verify_against(plan: dict, reading: int | None, decision: dict,
                   frozen: dict[int, tuple[Fraction, Fraction]]) -> dict:
    """Same check against a caller-declared table, for a second fixture."""
    try:
        return _verify(plan, reading, decision, frozen)
    except Exception as error:  # a malformed receipt is refused, not a crash
        return _refuse(f"malformed receipt: {type(error).__name__}: {error}")


def _verify(plan: Any, reading: Any, decision: Any, frozen: Any) -> dict:
    if not isinstance(plan, dict):
        return _refuse("plan is not a record")
    declared = plan.get("plan_sha256")
    if type(declared) is not str:
        return _refuse("plan carries no digest")
    if digest(plan) != declared:
        return _refuse("plan digest does not match its contents")
    if not isinstance(decision, dict):
        return _refuse("decision is not a record")
    if decision.get("plan_sha256") != declared:
        return _refuse("decision was not made from this plan")
    if decision.get("reading") != reading or type(decision.get("reading")) is not type(reading):
        return _refuse("decision was not made from this reading")
    if _decoded(plan.get("predictions")) != frozen:
        return _refuse("plan predictions are not the frozen fixture table")
    expected = decide(plan, reading)
    if not _same_decision(expected, decision):
        return _refuse("decision is not the recomputation of the plan and reading")
    resolved = expected["resolved"]
    if resolved is None:
        return {"verdict": ABSTAIN,
                "reason": "honest decision, no law's posterior is exactly 1"}
    return {"verdict": VERIFIED,
            "reason": f"posterior resolves law {resolved} to exactly 1"}


def _refuse(reason: str) -> dict:
    return {"verdict": REFUSED, "reason": reason}


def _encode(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _fraction(value: Any, what: str) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise ValueError(f"{what} is not an exact rational")
    if isinstance(value, int):
        return Fraction(value)
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(type(part) is int for part in value)):
        if value[1] == 0:
            raise ValueError(f"{what} has a zero denominator")
        return Fraction(value[0], value[1])
    raise ValueError(f"{what} is not an exact rational")


def _pair(value: Any, what: str) -> tuple[Fraction, Fraction]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{what} needs exactly two laws")
    first, second = (_fraction(part, what) for part in value)
    return (first, second)


def _posterior(entry: Any, what: str) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Read a stored prediction, whether law-labelled (dict) or slot-ordered (pair)."""
    if isinstance(entry, dict):
        if not entry:
            raise ValueError(f"{what} is empty")
        laws = tuple(sorted(int(key) for key in entry))
        values = tuple(_fraction(entry[str(law)], what) for law in laws)
        return laws, values
    pair = _pair(entry, what)
    return RIVALS, pair


def _entry(predictions: Any, reading: int) -> Any:
    if not isinstance(predictions, dict):
        raise ValueError("plan predictions are not a mapping")
    for key in (str(reading), reading):
        if key in predictions:
            return predictions[key]
    return None


def _resolved(laws: tuple[int, ...], posterior: tuple[Fraction, ...]) -> int | None:
    certain = [law for law, value in zip(laws, posterior) if value == 1]
    return certain[0] if len(certain) == 1 else None


def _fields(plan: Any) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("plan is not a record")
    declared = plan.get("plan_sha256")
    if type(declared) is not str:
        raise ValueError("plan carries no digest")
    if type(plan.get("policy")) is not str or type(plan.get("selected")) is not str:
        raise ValueError("plan is missing its policy or selected channel")
    prior = _pair(plan.get("prior"), "prior")
    if not isinstance(plan.get("predictions"), dict):
        raise ValueError("plan predictions are not a mapping")
    return {"sha": declared, "prior": prior, "predictions": plan["predictions"]}


def _decoded(predictions: Any) -> dict[int, tuple[Fraction, Fraction]]:
    if not isinstance(predictions, dict):
        raise ValueError("plan predictions are not a mapping")
    out = {}
    for key, entry in predictions.items():
        if not isinstance(key, str) or not key.lstrip("-").isdigit():
            raise ValueError("a prediction key is not an integer reading")
        out[int(key)] = _posterior(entry, f"predictions[{key}]")[1]
    return out


def _same_decision(expected: dict, decision: dict) -> bool:
    if decision.get("resolved") != expected["resolved"]:
        return False
    try:
        claimed = _pair(decision.get("posterior"), "decision posterior")
    except ValueError:
        return False
    return claimed == expected["posterior"]
