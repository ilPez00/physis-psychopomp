# Changelog

## 0.3.0 — 2026-11-22

One measured law instead of eight scattered benches. Everything below is
preregistered, measured and pinned in CI by `scripts/research-gates.py`.

**Law.** Identifiability of an intervention is per-event observer coverage:
identifiable iff the event location at the event step is outside the blind
region `o ∩ o2(t)`, observer held fixed across counterfactuals
(`psychopomp/law.py`, `docs/LAW.md`).

- place: 30/30 on a boundary-free grid, 13/30 unique exactly as predicted
  (R-P1.12); blind area shown to be a proxy, not the variable (R-P1.10/R-P1.11).
- time: a moving observer makes coverage time-resolved — 11/11 cells, both
  tie→unique flips (R-P1.17).
- frame: 30/30 covariant under whole-scene symmetries; a bodies-only control
  flips 5 of 22, which explains A4's negative as a world change rather than a
  viewpoint change (R-P1.18).
- noise: 100/100 to σ = 6, breakpoint σ\* = 15, 61% at σ = 40, covered events at
  chance throughout (R-P1.14–R-P1.16). The distances add, they do not compete.
- physics: gravity (closed-form position off by 39.8 units), a collision hidden
  inside the blind region, and three-collision episodes all obey it
  (R-P1.19, R-P1.20).
- agency: a wrong self-model loses 3 of 4 task events, and the cost tracks the
  ranking flip rather than the error size (R-P1.21).

**Method.** Per-cell *capacity checks*: a cell must prove it contains the event
class it claims to test before its result counts. Two design failures were
caught by it and are reported as `DESIGN-FAILED`, not as findings.

**Formalities.** `scripts/research-gates.py` pins every documented outcome,
including the honest negatives, and fails only on drift; CI runs it plus the law
conformance gate. Version surfaces (pyproject, `__version__`, CITATION) agree;
volatile test counts removed from prose so they cannot rot.

**Not claimed.** Non-rectangular occluders, more than two observers, observers
whose motion responds to the world, degraded identity, learned arms (blocked:
deterministic arms are at 100/100 where the rule says they should be).

## 0.2.0 — 2026-11-21

Post-audit CPU prototype: 2D off-axis physics, cross-episode derangement
control, cleared-episode filter contract, recoverability gate, ASP cross-check,
CI, Apache-2.0 + NOTICE.
