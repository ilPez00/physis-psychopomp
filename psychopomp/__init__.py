"""Psychopomp v0.9 — CPU research instrument.

Persistent, provenance-bearing world states -> temporal reasoning ->
falsifiable constraints on learned representations.

v0.8 adds marker reliability, so identity identifiability is 1-(1-p)^N.
v0.7 added coverage-gated identity evidence and closes an ordering leak in the
export contract. v0.6 added the planner (`planning.plan_coverage`, `plan_hedged`) pinned to the
published card numbers. v0.5 exposes the self-model API: blind-region estimation (rect, multi-cell, and
from the evidence's own count), polygon half-planes from labelled edges, and
`law.is_blind` membership for every occluder shape. Two learned arms were tried and
rejected; the deterministic inner bound remains the best self-model here.

v0.4 added self-model inference and planning under self-model error.
v0.3 added a measured law, not a model: identifiability of an intervention is
per-event observer coverage (``psychopomp.law``), measured across place, time,
frame, noise, rich physics and the observer's own self-model. Eight
preregistered cards, seven falsified predictions, two supported claims — see
``docs/LAW.md`` for the statement, the envelope and the falsification log.

Scope: deterministic simulator with strict observable/oracle separation, typed
event log, an event-calculus possible-world filter, counterfactual attribution,
and structure-preserving shuffled-rule controls. No neural components.
"""

__version__ = "0.9.0"
