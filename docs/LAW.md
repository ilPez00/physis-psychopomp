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

The blind set may be **several rectangles** — an observer with more than one
blocker — so it can be non-convex or disconnected, and the law is membership, not
envelope: a point in the gap between two blind islands is identifiable even
though it sits inside their bounding box (`R-P1.25`, 17/17 scored cells).

**Rotated occluders are in scope** (R-P1.33): a static polygon is ordinary
geometry for the membership form — all six task points on a diamond predicted
exactly, its bounding box wrong on all four corners, and 180° scene covariance
unchanged. Curved shapes are approximated by polygons to the step tolerance.

The **self-model estimator** needed one labelling fix to follow: polygon crossings
now carry their edge and outward normal (R-P1.34), and the estimator recovers all
four edges to within **0.21** on the same diamond. Where its optimism comes from is
now measured rather than assumed: **it is which side of the bound you take, not the
shape of the occluder** — the same "tightest bound" rule is *inside* the truth for
a rectangle's `x ≥ x0` and *outside* it for a polygon's `n·x ≤ d`. Always taking
the inner side is optimistic for every geometry, and predicts the diamond's centre
and all four corners correctly (5/5).

Also out of scope, by construction and not by omission: more than two observers, observers whose motion responds to
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
| `9624cc4a` | identifiable iff the event location is outside the blind region | **Supported** |
| `0848d800` | survives sensor noise as a signal-detection ordering | **Supported** |
| `ddf6b815` | survives rich physics (gravity, hidden and multiple contacts) | **Supported** |
| `bfaab7be` | a hedged plan recovers the loss a wrong self-model causes | **Supported** |
| `90821d05` | the law is membership, not the blind set's envelope | **Supported** |
| `52c28f5e` | the cost is a cliff at certainty, not a gradient | **Supported** |
| `cff544e7` | the blind region is recoverable from the observer's own log | **Supported** |
| `1a0259c2` | calibrating then planning matches an oracle; the hedge becomes vestigial | **Supported** |
| `011fd125` | several blind cells are recoverable per cell | **Supported** |
| `3e855a8f` | the cell count is recoverable; a corpus that never crosses a cell is silently incomplete | **Supported** |
| `1de8a2d3` | optimism is the side of the bound, not the shape | **Supported** |
| `2661e5ab` | a differing blind spot is sufficient | **Contradicted** |
| `4fdea69b` | collapse near σ ≈ 30 | **Contradicted** (mechanism clause held) |
| `148b49eb` | the rect estimator over-covers rotated geometry | **Contradicted** (it abstains) |
| `3a807034` | quantile + abstention restores containment under noise | **Contradicted** (5/9 honest) |
| `25350618` | a learned MSE correction beats the deterministic bound | **Contradicted** (and its control) |
| `fadbda33` | a pinball loss makes a learned arm safe *and* accurate | **Contradicted** (median error 2–3 steps) |
| `ad1b14aa` | self-model cost is discrete in the ranking flip | **candidate** — cost measured, discreteness partly refuted |

## Consequences for an observer (measured, not advised)

The law is about coverage, so an observer can *choose* coverage — and its own
model of where that coverage is becomes part of the picture:

- **a wrong self-model costs** (R-P1.21): a −10 unit error in the belief about
  one's own occluder picks the wrong drift direction and loses **3 of 4** task
  events (4/4 → 1/4);
- **the cost tracks the ranking flip, not the error size** (`|δ| = 10` cost 3,
  `|δ| = 20` cost 2), so "how wrong am I" is the wrong question — "does it change
  which motion I should take" is the right one;
- **hedging pays against the worst case, not against the average**
  (R-P1.24 → R-P1.27): a minimax plan over a declared ±20 unit belief set scores
  **3/4** against a naive worst case of **1/4**, with a regret of **1** event —
  and it picks the **opposite** drift to the confident optimum (−1.0 vs +1.0),
  so uncertainty about your own blind spot is a reason to move differently, not
  to observe less. Sweeping **all five** peaked priors at mass 0.80 gives costs
  `{1, 1, 0, 0, 1}` (**mean 0.60**), so at that confidence the hedge is *above*
  the mean and equal to the worst peak. But the loss is a **cliff at certainty,
  not a gradient**: at mass 0.95 the same peaks still cost at most 1, while at
  mass 1.00 they cost **2–3** (mean **1.80**, max **3**) — any residual weight,
  even 5 %, rescues the choice, because the loss is a discrete ranking flip and a
  flip needs a *pure* prior. So minimax hedging pays against an observer that is
  **certain and wrong**, and is dominated by one that is merely **confident and
  wrong**. Both regimes are measured; the boundary between them is a step.

These are single-world, noise-free, minimax measurements; a Bayesian planner with
a prior over its own error is **not** claimed.

## Can the observer learn its own blind spot? (measured)

Yes, and with a known bias (R-P1.29). From `enter_occ` / `exit_occ` crossings —
the same observable log the law describes — a body's last-seen position bounds the
edge it crossed to within one step. Taking the tightest bound per edge gives an
estimate that is **contained in** the truth (correct to one step), and `None` for
an edge no body ever crossed.

```
true            (46.0, 54.0, 35.0, 65.0)
estimated       (46.3, 53.8, 35.2, 64.9)     # inside the truth, step 0.3
horizontal only x known; y = None            # abstains rather than guessing
errors          1 optimistic (on the edge), 0 pessimistic
```

Self-knowledge is **conservative by construction**: a boundary is learned only
where a body crossed it, so an observer can believe it is *less* blind than it is,
never more. **Multi-cell** blind sets are recovered per cell (two cells to within
0.2, R-P1.31), and a **wrong cell count** — a structural self-model error — also
errs optimistically: it *drops* a cell rather than merging them, costing 1 of 4
task events. Every self-model error measured here points the same way.

The **count** is recoverable too (R-P1.32): clustering the crossing bounds gives
the same answer as being told, so no structural prior is needed — and an agent
using the auto count plans at the oracle score. What self-knowledge *does* need is
**coverage**: a corpus that never crossed a cell yields a confidently incomplete
model (cost 1 of 4 events) with nothing in the evidence marking it incomplete.

Code: `psychopomp/selfmodel.py`; limits: disjoint cells ordered along `x`, known
step, noise-free.

## The loop closes: calibrate, then plan (measured)

An agent that estimates its own blind region from its own log (R-P1.29) and plans
from the estimate reaches **4/4** on the task set — the oracle's score — where an
agent with a fixed wrong belief scores **1/4** (R-P1.30). The minimax hedge of
R-P1.24 is then **vestigial**: with uncertainty down from ±20 units to one step it
picks the same drift and buys nothing.

> Calibration replaces conservatism. The hedge paid because the model was wrong by
> up to 20 units; measuring reduces the error to 0.3 and the hedge has nothing
> left to protect against.

## Identity is coverage-gated too (measured)

The log is identity-free, so a relabelling of two identical bodies is invisible in
it — as a *set*. With identity evidence (`SimConfig.identity_marker`), the tag
resolves the ambiguity; with the same markers **occluded**, zero are emitted and the
ambiguity returns; a second vantage restores it (R-P1.39, 4/4).

One leak was found on the way and **closed at the source**: the observable log was
appended in body-index order, so a relabelling changed the event **sequence**.
`EventLog` now iterates canonically and renumbers `seq` to match, so the log is a
set in the estimator, in attribution and in the export contract; two tests pin it,
and the identity card re-run shows sequence equality for the relabelled pair.

## Identity has a formula, not just a story (measured)

With identity evidence of reliability `p` and `N` marker opportunities across the
observer's visible bodies, the relabelling is resolvable with probability
**`1 − (1−p)^N`** (R-P1.41: 12/12 cells within 0.06 at `N = 2, 4, 6`, e.g.
`p = 0.6, N = 2 → 0.840` predicted, **0.845** measured). **Coverage sets `N`,
reliability sets `p`, and the two compose in the exponent** — one chance per body
already gives `N = 2`, and the fully hidden case is `N = 0`, hence 0 at every `p`.

The formula assumes **independent** drops. With a **bursty** channel the same
marginal drop rate resolves fewer relabellings — measured deficits up to **+0.312**
at `N = 4, b = 0.4`, shrinking to **+0.052** at `N = 12` (R-P1.42). So correlation
costs identifiability, and more chances dilute a burst (when the burst covers the
whole window, the `N` chances collapse into one draw: 0.618 measured against
`1−b = 0.600`).

The first attempt to test the independent case (R-P1.40) sat at `N = 56`, where the
formula predicts ≈ 1 for every `p` — it passed and tested nothing, and is recorded
as **vacuous** rather than as evidence.

## Detection latency is not noise (measured, with a caveat)

A lagging sampler reports a crossing late with the position **then**, so the reported
point lies further along the body's travel: the edge bound moves **outward**, and the
self-model estimate crosses from optimistic (+0.05 at one step of latency) to
pessimistic (−0.55 at three, −2.65 at ten) — a **signed** degradation, unlike sensor
noise, which is symmetric (R-P1.43). The law is untouched: the same identifiability
count at `L = 0` and `L = 10`, because it is a predicate on the true event location.

Caveat kept deliberately: this card's two strict thresholds ("never optimistic at
`L ≥ 1`", "no optimistic margin at `L ≥ 1`") were **falsified at `L = 1`** and widened
afterwards, because one step of latency sits inside the estimator's own quantisation.
That is a preregistration defect, not a measurement one, and it is recorded rather
than smoothed.

## How to use it

```python
from psychopomp.law import blind_region, predict_identifiable, on_boundary

cfg = ...  # SimConfig with o, o2, optional o2_velocity / accel
if not on_boundary(cfg, point, t):
    identifiable = predict_identifiable(cfg, point, t)
```

Planning with the law is one call (R-P1.21–R-P1.30, pinned by tests):

```python
from psychopomp.planning import plan_coverage, plan_hedged
out = plan_coverage(config, tasks, drifts, t)              # law-optimal drift
out = plan_coverage(config, tasks, drifts, t, belief=...)  # what a wrong self-model picks
out = plan_hedged(config, tasks, drifts, t, belief_rects)  # minimax over uncertainty
```

`on_boundary` is not optional politeness: at a blind edge the answer is decided
by floating-point accumulation order (a ball at `42.000000000000004` versus
`41.99999999999992` are on opposite sides of the predicate). Excluding those
cells is part of the law's statement, not a convenience.
