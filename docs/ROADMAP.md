# ROADMAP — physis-psychopomp (P1: observer-relative world models)

Source: `~/dev/project_imagination.md` mission **P1** (2026-11-21).
This file is the authoritative roadmap for this repo. Plan top-down; append
statuses; never rewrite `2026-11-20-PREREG.md` or its amendments into their own
outcomes. Repo state measured 2026-11-21 at `3b3335d` (+2 local tests pending).

## Current state — measured, not narrated

| item | state | evidence |
|---|---|---|
| Claims A/B | registered, bounded; A untested, B not started | `docs/2026-11-20-PREREG.md` + AMENDMENT |
| **A2 result** (pre-contact position channel) | **landed**: deterministic top-1 **1.00** vs **0.25** chance on the parallel family; endpoint-only probe 0.00 | `docs/2026-11-21-PLAN-audit-followups.md` §P4; `scripts/probes.py` |
| **A3** (observation-noise experiments) | **blocked with a measurement**: at noise/gap ratio ≤ 0.4 the observables do not determine the answer (exact Bayes ties); at ≥ 1 a trivial statistic wins; `track(3)` samples make the feasibility set **empty** (velocity noise amplified 1/dt). Binding constraint = position noise vs the 2-unit gap | `docs/2026-11-21-PLAN-round9.md` §W2–W3 |
| License | **Apache-2.0 + NOTICE** landed (portfolio audit) | `cca8220`, `3b3335d` |
| Tests | **116 green** | `pytest -q` |
| Perspectives (mission core) | **present** (`perspective.py`, `camera.py`, `attribution.py`). A4 run 1: frame normalization adds **no** predictive value (H1 falsified). R-P1.9: a second *observer with a different blind spot* does (unique vs null-tie) | `2026-11-21-A4-run-1-results.md`, `2026-11-22-PLAN-R-P1.9-multi-observer.md` |
| GPU arms | **unjustified by A3/R-P1.1** (no deterministic headroom on this family). Availability is no longer the blocker: omo answers over ssh 2026-11-22 (16 cores, `/dev/kfd` present). The blocker is the measurement, not the machine | round 9; ssh omo-ts 2026-11-22 |

Consequences fixed now:

- On any task where a deterministic arm scores 1.00 (A2), a learned arm can
  only match it. **No learned model on that task**, per mission P1 §4.
- A3 cannot be "fixed" by more samples of the same channel; it needs a
  resolution/separation/observable change (round 9 W3).

## Slices (ordered; each ends in a gate, not a paragraph)

| id | slice | gate | status |
|---|---|---|---|
| R-P1.0 | Doc drift: README still says "No LICENSE file yet" after Apache landed. Fix line only; no history rewrite. | `grep -c "No LICENSE file yet" README.md` = 0 | **done** (README aligned with the Apache grant; stale test count corrected by the license-audit round) |
| R-P1.1 | **A3 successor — instrument change.** One of: (a) narrower sensor noise / larger gap so ratio ≤ 0.4 stops tying; (b) a position channel whose noise is not amplified by 1/dt; (c) one additional observable (changes identifiability — must be stated as such). Register the choice in a prereg appendix **before** running. | exact-Bayes decided-rate at the target ratio, with the construction-matched control; abstention counted, not hidden | **done** (plan + sweep, `2026-11-21-PLAN-R-P1.1-instrument-operating-point.md`): monotone decision curve in r=sep/noise; P3 falsified (A2 is a high-r result, not a channel property); operating point **sep=6, noise=1** (Bayes/EC arms) and **sep=6, noise=0.5** (A2-channel arms) |
| R-P1.2 | **Perspectives** (mission core): same episode observed as A. world coords, B. A-relative, C. B-relative, D. randomized rot+trans observer. Moving-frame transform `v' = R(v − v_frame)`; oracle identity private; observables only. | invariant tests: momentum/energy signs under transform; inverse round-trip ≤ 1e-6; **leakage test** (perspective label carries no oracle info) | **done** (`psychopomp/perspective.py`, 8 tests): world/ball/random frames; point+velocity round-trip < 1e-9; world/random frames are inertial → EPEC world count and contact_required invariant; oracle untouched, outputs identity-free; body frames inertial only between the body's own velocity changes (stated + tested contrast) |
| R-P1.3 | Noise/ambiguity injection through the camera layer: quantization, sensor noise, occlusion variation, missing observations, ambiguous identities — applied to observables, never to oracle. | `scripts/recoverability.py` per perspective; A2 channel either survives or the result is reported perspective-specific | **done** (`psychopomp/camera.py` + `scripts/degradation-matrix.py`, plan `2026-11-21-PLAN-R-P1.3-camera-degradation.md`): enumeration invariant (4 worlds, truth 6/6) in every cell; decision boundary at jitter ≈ sep/2; **A2 probe is axis-bound** (1.00 world vs 0.00 rotated) → A4 baseline is exact Bayes, never the y-residual across frames |
| R-P1.4 | Model arms: deterministic world-coords · deterministic normalized observer-relative · EC filter · matched shuffled control. Learned only if deterministic baselines leave headroom. | recoverability + probes table with means/sd; headroom = the only licence to train | open |
| R-P1.5 | Interventions: paired kick/no-kick episodes; labels OBSERVED / INFERRED / COUNTERFACTUAL / REFUTED; no simulated event may become an observation. | log-schema test forbidding promotion of simulated events; paired-episode diff test | **done** (`psychopomp/interventions.py` + 5 tests, plan `2026-11-21-PLAN-R-P1.5-interventions.md`): pairs identical pre-kick, diverge post-kick; counterfactual provenance; hidden kick is a no-op; `ObservationLedger` refuses non-`sim:*` events |
| R-P1.6 | **A4 preregistration** before any run: hypotheses, exact baselines (including A2's 1.00), thresholds, seeds, leakage checks, negative controls, compute budget. Preserve A2/A3 records. | new dated file; old claims untouched | **done** (`2026-11-21-PREREG-A4-perspectives.md`): H1–H3 with falsifiers, 4 matched arms, ceiling exclusion rule, 5 seeds × 6 episodes, CPU budget, claim registered at prior 0.4 |
| R-P1.7 | Integration spec for Physis (observable log → typed observations with provenance; IMP-4). | round-trip query on a fixture in a Physis world | **producer side done** (`psychopomp/export.py` + 4 tests, plan `2026-11-21-PLAN-R-P1.7-export-contract.md`): lossless, identity-free, counterfactual-refusing, deterministic JSONL (`psychopomp.observation/1`). Live Physis ingest **measured absent** (`2026-11-22-R-P1.7-ingest-measurement.md`): `physis ingest` is a closed 12-source connector registry with per-source parsers, no generic JSONL ingress — consumer side does not exist, so the gate is **not met** |
| R-P1.8 | **Counterfactual attribution**: given an observed episode and declared intervention hypotheses, rank which one explains it; ambiguity reported, never guessed. | bench: truth unique top-1 on both lane families, permuted-score control at/below chance, hidden-kick ambiguity test-pinned | **done** (`psychopomp/attribution.py`, 8 tests, plan+results `2026-11-21-PLAN-R-P1.8-counterfactual-attribution.md`, receipt `research/loops/results/attribution-20261121/`): 12/12 unique top-1 both classes, margins 7.94/17.20, control 0/12, ambiguity size 1.00 |
| R-P1.9 | **Multi-observer occlusion**: is a blind spot a property of the world or of the observer set? Second observer's own occluder (`SimConfig.o2`); blind region = `o ∩ o2`. | four observer sets over one world: single/same reproduce the null-tie, overlap/disjoint make a hidden kick identifiable, same-blind-spot control unchanged, trajectories invariant | **done** (`psychopomp/sim.py` `o2`/`observable`, `tests/test_multi_observer.py`, plan+results `2026-11-22-PLAN-R-P1.9-multi-observer.md`, receipt `research/loops/results/multi-observer-20261122/`): hidden kick ties with null under one observer (ambiguity 2, d=0.00) and is **unique with margin 22.00 / 10.00** under two; same blind spot changes nothing; hidden step fraction 0.331 = 0.331 > 0.164 > 0.000; 113 tests green |
| R-P1.10 | **Preregister the multi-observer mechanism claim** (R-P1.9 measured it once, on one geometry): seeds × geometries, permuted-score control, per-cell ceiling rule, pre-declared prior. | new dated prereg file before any run; verdicts at its own thresholds | **done — claim FALSIFIED** (`2026-11-22-PREREG-R-P1.10-multi-observer-claim.md`, `scripts/multi-observer-prereg.py`, receipt `research/loops/results/multi-observer-prereg-20261122/`): 25 cells, unique-correct 0/0/**2**/5/5 for single/same/overlap-450/overlap-300/disjoint. H1 required 5/5 in every strict-coverage geometry → **falsified** on overlap-450. H2 (same ≡ single) / H3 (monotone) / H4 (control 0.295–0.410) upheld. Diagnosis: the failures are exactly the seeds whose kick location stays inside the residual blind region — **identifiability is per-event coverage, not aggregate blind area**. Registered claim `2661e5ab` moved to Contradicted |
| R-P1.11 | **Per-event coverage rule**, preregistered on a fresh geometry grid. | fresh grid, analytic per-cell prediction before the run | **done — 29/30, H1 falsified at its threshold** (`2026-11-22-PREREG-R-P1.11-per-event-coverage.md`): the single miss is cell `ov-c, x0=20, y=51`, where the simulator's accumulated position is `41.99999999999992` against an analytic `42.0` — a 1e-14 boundary artifact, diagnosed from the trajectory, not a rule failure. Control at chance (0.290–0.410). Reported as falsified rather than re-scoped |
| R-P1.12 | **Boundary-free grid**, same rule, boundary cells excluded by a rule declared before the run. | 30/30 per-cell match, unique count equals the analytic count, control at chance | **done — SUPPORTED** (`2026-11-22-PREREG-R-P1.12-boundary-free-grid.md`, `scripts/per-event-coverage-prereg.py`, receipt `research/loops/results/per-event-coverage-20261122/`): **30/30** matches, **13/30** unique exactly as predicted, 0 boundary exclusions, control 0.290–0.410. `bv-c` proves area is not the variable: lane `y=45` 5/5 unique, lane `y=51` 0/5, same blind area 540. Claim `9624cc4a` → **Supported**. 115 tests green |
| R-P1.13 | Does the rule survive **degraded observations**? Sensor noise as a signal-detection problem. | covered events at chance, uncovered above chance, monotone in σ | **done — falsified at its thresholds** (`2026-11-22-PREREG-R-P1.13-coverage-under-noise.md`): P1 mis-specified (the shared-stream defect collapses the covered cell to a tie, it does not inflate the uncovered one) and the σ columns were **not independent** — the same 20 episode indices gave identical noise configurations at every σ (winning set `[2,4,10,11,14,16,17]` at 0.1/0.3/0.5), so the reported 0.35 was one 7/20 sample rescaled. P3/P4 upheld |
| R-P1.14 | Same question, **independent realizations per σ** (100 draws), defect measured where it bites. | covered 0.5 ± 0.10 at every σ ≥ 0.1; uncovered 1.00 with separation ratio ≥ 10 | **done — SUPPORTED** (`2026-11-22-PREREG-R-P1.14-coverage-under-noise-v2.md`, `scripts/coverage-under-noise-v2.py`, receipt `research/loops/results/coverage-under-noise-20261122/`): run 1 exposed a third defect (`attribute()` pinned candidates to `episode=0`, so all realizations shared one fixed corruption → covered cell *below* chance at 0.22–0.35); after the fix, covered 0.47/0.58/0.51/0.50 at σ ≥ 0.1, uncovered **100/100** at every σ ≤ 0.5 with `d(null)/d(true)` 61.6 → 12.7, σ = 0 reproducing R-P1.12. Claim `0848d800` → **Supported**. 116 tests green |
| R-P1.15 | **Noise envelope**: where does identification stop? σ ∈ {0.75…6}. | accuracy ≥ 0.90 to σ = 2, < 0.50 from σ = 4, linear noise term | **done — P2/P3/P4 falsified, model rewritten** (`2026-11-22-PREREG-R-P1.15-noise-envelope.md`): **no breakpoint** — accuracy 100/100 at every σ up to **6**. `d(null)` is not noise-free (27.88 → 44.85), so the two distances **add** rather than compete; the invariant is the additive margin `d(null) − d(true)` ≈ 24.8 → 20.2. Covered cell at chance throughout (P5) |
| R-P1.16 | **The crossing**: σ ∈ {10, 15, 20, 30, 40}, predicted from the R-P1.15 margin line (zero at σ ≈ 30). | breakpoint bracketed in [15, 40]; collapse by σ = 40 | **done — P1 falsified, P2–P5 upheld** (`2026-11-22-PREREG-R-P1.16-crossing.md`, `scripts/noise-envelope.py`, receipt `research/loops/results/noise-envelope-20261122/`): accuracy **0.94 / 0.84 / 0.81 / 0.71 / 0.61**, breakpoint **σ\* = 15**, covered cell 0.47–0.58 throughout. Margin slope −0.22 (predicted −0.4…−1.2) with zero at σ ≈ 67, so the σ ≤ 6 extrapolation was wrong by 2× and the decay is gradual, not a cliff. Claim `4fdea69b` → Contradicted on its quantitative clause |
| R-P1.17 | **Time-resolved coverage**: a moving second observer makes the blind region time-dependent; identifiability should follow coverage **at the event step**, with the observer held fixed across counterfactuals. | 2 event locations × 3 observer drifts (static, right, left) predicted per cell before the run; a kick hidden by the static occluder must become identifiable as it drifts away, and vice versa; reflection case tracked through the fold | **planned** |
| R-P1.17 | **Time-resolved coverage**: a moving second observer makes the blind region time-dependent; identifiability should follow coverage **at the event step**, with the observer held fixed across counterfactuals. | 2+ event locations × drifts predicted per cell before the run; a kick hidden by the static occluder must become identifiable as it drifts away, and vice versa; reflection case tracked through the fold | **done — SUPPORTED** (`2026-11-22-PREREG-R-P1.17-moving-observer.md`, `scripts/moving-observer-prereg.py`, receipt `research/loops/results/moving-observer-20261122/`): **11/11** cells, both flips (x=44 tie→unique with right drift, x=55 tie→unique with left drift), folded occluder tracked through a wall reflection, σ=1.0 pattern intact (1.00 / 0.47), observer asserted fixed across counterfactuals. Found + fixed: motion-caused visibility changes have no edge crossing, so they are now labelled `sweep` instead of raising. 119 tests green |

## Claim ledger — registered, with measure and status

| claim | statement | measure | status |
|---|---|---|---|
| `9624cc4a` | an intervention is identifiable **iff** its event location is outside the blind region `o ∩ o2`; blind area is only a proxy | 29/30 out of sample, then 30/30 on a boundary-free grid (13/30 unique exactly as predicted) | **Supported** (fitness 0.613) |
| `0848d800` | the rule survives sensor noise as a signal-detection ordering | uncovered 100/100 at σ ≤ 0.5 with `d(null)/d(true)` 61.6 → 12.7; covered at chance (0.47–0.58) | **Supported** |
| `2661e5ab` | a *differing* blind spot is sufficient for identifiability | `overlap-450` scored 2/5 where 5/5 was required — the residual blind region still covered the event | **Contradicted** |
| `4fdea69b` | the collapse sits near σ ≈ 30 (linear-margin extrapolation) | breakpoint σ\* = 15; decay 0.94 → 0.61 across σ = 10…40; zero-crossing ≈ 67 | **Contradicted** (mechanism clause held) |

Envelope, measured end to end: **100/100 to σ = 6**, 94% at σ = 10, breakpoint
**σ\* = 15**, 61% at σ = 40 with the covered case at chance throughout. The
distances **add** (a counterfactual corrupts both hypotheses alike), so
identification survives until the noise floor approaches the world's geometry.

## Next axes, in order of value

1. **Time-resolved coverage (R-P1.17)** — a *moving* second observer makes the
   blind region time-dependent. The rule then predicts identifiability from
   coverage **at the event step**, and the counterfactual must hold the observer
   fixed (otherwise an observer change is confounded with a world change). This
   is the cheapest test that the law is about *place and time*, not just place.
2. **Non-convex / rotated occluders (R-P1.18)** — does the rule survive geometry
   that is not an axis-aligned rectangle?
3. **Moving bodies with acceleration / multi-contact (R-P1.19)** — the current
   family is constant-velocity with elastic equal-mass collisions.
4. **Learned arms** — still blocked: deterministic arms are at 100/100 on the
   uncovered family, so no learned model is licensed (mission P1 §4).

## Dependencies and stop rules

`R-P1.0 → R-P1.1 → R-P1.2 → R-P1.3 → R-P1.4 → R-P1.5 → R-P1.6 → R-P1.7`

R-P1.8 and R-P1.9 depend on R-P1.5 (interventions) and R-P1.3 (camera), not on
R-P1.7: the consumer side is absent, so integration cannot gate research.

- No GPU arm until R-P1.4 shows headroom **and** omo is reachable (offline
  2026-11-20, 5 days).
- A positive must beat the corpus-derived shuffled control, not only the
  baseline (Phase 11D lesson).
- A negative is a receipt; never tune until green.

## Backlog mapping (from `2026-11-20-FIXES-AND-IMPROVEMENTS.md`)

IMP-1 CI green · IMP-2 **done** (Apache) · IMP-3b open (probabilistic
weighting; epec-vanilla license question to D'Asaro still open) · IMP-4 folded
into R-P1.7 · IMP-5 **done** (probes baseline; M2 endpoint=chance, A2
position=1.00) · IMP-6 partially covered by the M3 shuffled-control test ·
IMP-7 code generalized, tests added locally (pending commit).

## A4 — executed 2026-11-21

Prereg: `2026-11-21-PREREG-A4-perspectives.md`; results:
`2026-11-21-A4-run-1-results.md`. **H1 falsified** (frame-normalized beats
world-frame on 0/5, 1/5, 0/5 seeds on the headroom cells; threshold ≥2),
**H2 upheld** (worlds and truth-in-worlds invariant across inertial frames),
**H3 upheld** (shuffled control 0.00). Claim `1ff62ee2` contradicted. This is
the fifth slice-closing negative receipt in the repo; the ceiling rule and the
≥2-seed threshold are what kept it honest.

## Non-claims

- A2 is a deterministic result on a constructed task; it is **not** evidence
  of learned-model improvement, human-like imagination, or consciousness.
- No metric is added after results exist.
