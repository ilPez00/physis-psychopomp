# The law — identifiability is per-event observer coverage

Consolidated 2026-11-22 from eight preregistered cards (R-P1.12 … R-P1.21).
Code: `psychopomp/law.py`. Enforced in CI by `scripts/research-gates.py`
(pinned outcomes) and `scripts/law-conformance.py` (random-grid conformance).

## Statement

> An intervention is identifiable from the observable log **iff** its event
> location at the event step lies outside the blind region `o ∩ o2(t)`, with the
> observer held fixed across counterfactuals.

Three consequences, each measured rather than argued:

- **place**: a second observer whose blind spot differs removes the blind spot
  where the event is (`R-P1.12`, 30/30 on a boundary-free grid);
- **time**: with a moving observer, coverage is evaluated **at the event step**,
  not over the history (`R-P1.17`, 11/11; both tie→unique flips);
- **frame**: any exact symmetry of the scene that carries the observers with it
  leaves the answer unchanged — while moving only the bodies changes it
  (`R-P1.18`, 30/30 covariant; bodies-only control flipped 5 of 22).

## What it does *not* say (scope, stated honestly)

The instrument emits an observable `kick` event when an intervention **lands**.
So for the pair "this intervention" vs "no intervention", the law's bite is:
coverage decides whether the action lands at all, and a landed action is
signalled. That is precise but narrow. The deeper identifiability question —
*which body*, *what velocity*, *when* — is measured separately and rests on
trajectory differences, which coverage also governs: 12/12 unique top-1 on both
lane families with nine declared hypotheses, permuted-score control 0/12
(`R-P1.8`). Both results come from the same geometry; neither implies the other.

Also out of scope, by construction and not by omission: non-rectangular or
rotated occluders, more than two observers, observers whose motion responds to
the world, degraded object identity, and every learned arm (blocked: the
deterministic arms are at 100/100 on the uncovered family, so a model could only
match them).

## Validity envelope (measured)

| condition | measured behaviour | source |
|---|---|---|
| noise σ ≤ 6 | **100/100** identification | R-P1.14, R-P1.15 |
| noise σ = 10 | 94% | R-P1.16 |
| noise σ = 15 | 84% — breakpoint σ\\* | R-P1.16 |
| noise σ = 20 | 81% | R-P1.16 |
| noise σ = 30 | 71% | R-P1.16 |
| noise σ = 40 | 61% (covered events stay at 50% throughout) | R-P1.16 |
| gravity | rule holds; closed-form position off by 39.8 units | R-P1.19 |
| one or three collisions, one hidden | rule holds | R-P1.20 |
| event on a blind edge (≤ 1e-6) | **excluded, never predicted** | R-P1.11, R-P1.12 |

σ is uniform `±σ/2` per coordinate on `pos`/`v`. The noise model is abstract —
σ = 40 means ±20 units in a 100-unit box on a 2-unit body — so the envelope is
about robustness to *relative* noise, not about any real camera.

## Why the noise envelope is wide (model correction)

Two distances are compared: the observed log against the true hypothesis and
against the null. They **add**, they do not compete: a counterfactual corrupts
both hypotheses alike, so the structural difference rides on a shared noise
floor. Hence 100/100 up to σ = 6 and no cliff — a gradual decay
(`R-P1.15` falsified "no breakpoint to σ = 6"; `R-P1.16` falsified "zero crossing
near σ = 30", measured ≈ 67).

## Falsified along the way (kept, not deleted)

| prediction | card | outcome |
|---|---|---|
| frame-normalized analysis beats world-frame | A4 (pre-law) | **falsified** — a frame change is a bijection on observables |
| "a differing blind spot is *sufficient*" | R-P1.10 | **falsified** — `overlap-450` scored 2/5 where 5/5 was required |
| 30/30 on the first fresh grid | R-P1.11 | **falsified** at 29/30 by a 1e-14 float boundary |
| no breakpoint up to σ = 6 | R-P1.15 | **falsified** — there is none; the knee model was wrong |
| zero crossing near σ = 30 | R-P1.16 | **falsified** — ≈ 67, decay is gradual |
| gravity grid tests hidden contacts | R-P1.19 | **falsified** as a design: 0 hidden collisions, 0 second contacts |
| every capacity check passes | R-P1.20 | **falsified** — 4 gravity cells cannot produce a hidden contact |
| some self-model errors are free | R-P1.21 | **falsified** — every tested δ cost ≥ 1; cost tracks the ranking flip, not the error size |

Seven falsifications against five supported claims is the honest ratio, and the
falsifications did the work: `2661e5ab` (area suffices) → the per-event rule;
R-P1.19's empty cells → the capacity-check method; R-P1.15's missing knee → the
additive-margin model.

## Registered claims (physis store)

| claim id | statement | status |
|---|---|---|
| `9624cc4a` | identifiable iff the event location is outside `o ∩ o2` | **Supported** (fitness 0.613) |
| `0848d800` | survives sensor noise as a signal-detection ordering | **Supported** |
| `2661e5ab` | a differing blind spot is sufficient | **Contradicted** |
| `4fdea69b` | collapse near σ ≈ 30 | **Contradicted** (mechanism clause held) |
| `ddf6b815` | survives rich physics (gravity, hidden and multiple contacts) | **candidate** — hidden/multi-contact supported, the conjunction gravity ∧ hidden contact untested |
| `ad1b14aa` | wrong self-model cost is discrete in the ranking flip | **candidate** — cost measured, discreteness partly refuted |

## Consequences for an observer (measured, not advised)

The law is about coverage, so an observer can *choose* coverage — and its own
model of where that coverage is becomes part of the picture:

- **a wrong self-model costs** (R-P1.21): a −10 unit error in the belief about
  one's own occluder picks the wrong drift direction and loses **3 of 4** task
  events (4/4 → 1/4);
- **the cost tracks the ranking flip, not the error size** (`|δ| = 10` cost 3,
  `|δ| = 20` cost 2), so "how wrong am I" is the wrong question — "does it change
  which motion I should take" is the right one;
- **hedging pays** (R-P1.24): a minimax plan over a declared ±20 unit belief set
  scores **3/4** against a naive worst case of **1/4**, with a regret of **1**
  event against an oracle. The hedge picks the **opposite** drift to the
  confident optimum (−1.0 vs +1.0) — uncertainty about your own blind spot is a
  reason to move differently, not to observe less.

These are single-world, noise-free, minimax measurements; a Bayesian planner with
a prior over its own error is **not** claimed.

## How to use it

```python
from psychopomp.law import blind_region, predict_identifiable, on_boundary

cfg = ...  # SimConfig with o, o2, optional o2_velocity / accel
if not on_boundary(cfg, point, t):
    identifiable = predict_identifiable(cfg, point, t)
```

`on_boundary` is not optional politeness: at a blind edge the answer is decided
by floating-point accumulation order (a ball at `42.000000000000004` versus
`41.99999999999992` are on opposite sides of the predicate). Excluding those
cells is part of the law's statement, not a convenience.
