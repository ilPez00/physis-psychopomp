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
| Tests | **75 upstream green**, +2 local (IMP-7 multi-contact / re-crossing) = 77 | `pytest -q` |
| Perspectives (mission core) | **absent**: no frame/observer module (`psychopomp/` has sim, eventlog, epec, controls, asp, fixtures, probes) | file list |
| GPU arms | unjustified by A3; node offline | round 9; omo last seen 5d |

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
| R-P1.7 | Integration spec for Physis (observable log → typed observations with provenance; IMP-4). | round-trip query on a fixture in a Physis world | **producer side done** (`psychopomp/export.py` + 4 tests, plan `2026-11-21-PLAN-R-P1.7-export-contract.md`): lossless, identity-free, counterfactual-refusing, deterministic JSONL (`psychopomp.observation/1`). Live Physis ingest compatibility **NOT MEASURED** (needs a physis-next branch checkout) |

## Dependencies and stop rules

`R-P1.0 → R-P1.1 → R-P1.2 → R-P1.3 → R-P1.4 → R-P1.5 → R-P1.6 → R-P1.7`

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
