"""Psychopomp v0.4 — CPU research instrument.

Persistent, provenance-bearing world states -> temporal reasoning ->
falsifiable constraints on learned representations.

v0.4 adds self-model inference and planning under self-model error.
v0.3 added a measured law, not a model: identifiability of an intervention is
per-event observer coverage (``psychopomp.law``), measured across place, time,
frame, noise, rich physics and the observer's own self-model. Eight
preregistered cards, seven falsified predictions, two supported claims — see
``docs/LAW.md`` for the statement, the envelope and the falsification log.

Scope: deterministic simulator with strict observable/oracle separation, typed
event log, an event-calculus possible-world filter, counterfactual attribution,
and structure-preserving shuffled-rule controls. No neural components.
"""

__version__ = "0.4.0"
