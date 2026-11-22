# Changelog

## 0.8.1 — 2026-11-22

**Integration contract, producer side machine-checked.** `docs/INTEGRATION-CONTRACT.md`
states what `psychomomp.observation/1` guarantees and what a consumer must do, and
`scripts/export-contract-check.py` asserts every one of those guarantees against a
real export (schema string, canonical order, `seq` as index, identity-free subjects,
no oracle fields, deterministic, relabelling-invariant, counterfactual-refusing). A
sample fixture is committed at `research/fixtures/observation-v1.sample.jsonl`.

The consumer side is **absent by measurement** (no generic ingress in `physis
ingest`); the document names the two routes for its owner and, separately, what is
**not** established here — Physis's own row shape, its bitemporal folding, units,
and chunking.

## 0.7.0 — 2026-11-22

**Identity evidence** (`SimConfig.identity_marker`, `marker_period`,
`allow_hidden_init`): bodies emit an observable `marker` carrying their tag while
visible. Measured (R-P1.39): identity ambiguity is **coverage-gated** — a
relabelling is invisible in the identity-free log as a set, becomes visible once a
marker is observed, and returns to invisible when the markers are occluded
(0 / 56 / 0 / 56 markers across four cases, set-equality following).

**Fixed on the way:** the observable log was appended in body-index order, so a
relabelling changed the event **sequence** — an identity leak the export contract
now closes by sorting canonically (`test_a_relabelling_exports_identically`); and
the initial visibility flag was hardcoded `True`, so a body that started occluded
emitted a marker for a body never seen.

**Also:** `planning.plan_from_evidence` — logs → self-model → plan in one call.

## 0.6.0 — 2026-11-22

**`psychopomp/planning.py`** — the arc's result as a callable planner:
`plan_coverage` picks the observer drift whose blind region leaves the most tasks
identifiable, optionally under a *believed* geometry; `plan_hedged` is the minimax
version over a set of believed blind regions. Five tests pin it to the published
numbers (drift +1.0 → 4/4; the ±20 hedge → −1.0; a −10 belief error → −0.5 with a
measured cost of 1/4), so the planner cannot drift from the cards silently.

One of those tests also documents a distinction the program keeps having to make:
the planner predicts **1** identifiable task for drift 0.0 where the instrument
**measured 2**, because task `x = 46` sits exactly on the blind edge and the body
accumulates to `45.999999…`. Predicted and measured are different quantities and
the tests now say which is which.

## 0.5.0 — 2026-11-22

**Public API for the self-model** (`psychopomp/law.py`, `psychopomp/selfmodel.py`):
`law.is_blind` / `blind_cells` (membership, polygons included),
`selfmodel.estimate_blind_region` (rect, with `quantile`/`max_spread`),
`estimate_blind_cells` / `estimate_blind_cells_auto` (multi-cell, count from
evidence), `estimate_polygon_halfplanes` (labelled polygon edges) and
`collect_edge_bounds` (the raw evidence, so a model reads what the estimator reads).

**Findings this release records:** rotated occluders are ordinary membership and a
bounding box fails on their corners; the estimator's optimism is the **side of the
bound**, not the shape; under noise containment **goes** (14/20 pessimistic at
σ = 1.0) and abstention does not restore it; and **two learned arms were rejected** —
MSE spends the conservative tail, pinball spends the honest estimate (median error
0.62–0.80) while its control recovers a third of the gain as pure bias. The
deterministic inner bound remains the best self-model here.

**Internal:** one event scan for every estimator (was five copies), dead helper
removed, `scripts/status.py` reports the repo's state in one command.

## 0.4.0 — 2026-11-22

**Self-model inference** (`psychopomp/selfmodel.py`): an observer recovers its own
blind region from its own observable log, to within one simulation step, as a
**subset** of the truth, and **abstains** on any edge no body crossed. Measured
accuracy 0.3 units on all four edges; errors are one-signed (1 optimistic on an
edge, 0 pessimistic); good enough to plan with on points ≥ 1 unit clear.

**Planning under self-model error** (R-P1.21, R-P1.24, R-P1.26–R-P1.28): a wrong
self-model loses up to 3 of 4 task events; a minimax hedge recovers 3/4 where the
naive worst case is 1/4 and picks the *opposite* drift; a flat prior lands on the
hedge, an honest confident prior reaches the oracle with zero regret; and the cost
is a **cliff at certainty** (mean 0.60 / 0.60 / 1.80 across prior mass
0.8 / 0.95 / 1.0), not a gradient — a 5 % residual weight rescues what 20 % does.

**Process.** Plan tables are generated (`scripts/plan-table.py`) instead of read
by hand — three consecutive wrong predictions came from transcription. A prereg
checklist enforces a claim id from 2026-11-23. 14 pinned research gates.

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
