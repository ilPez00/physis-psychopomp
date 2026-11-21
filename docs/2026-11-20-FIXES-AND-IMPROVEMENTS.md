# Fixes and improvements — plan after the first public audit (2026-11-20)

Status: **PLAN**, top-down, fixed at write time. Precedence when documents
disagree: code > test > receipt > captured artifact > doc > plan. This file
records what the external audit found, what was fixed with which evidence,
and what remains. Each open item names its gate.

## Evidence base

- Audit claims were re-derived against the code, not accepted on trust.
  Both blockers were confirmed in the first implementation (commit `9f2b891`):
  the within-`(kind,t)` shuffle was a multiset permutation (vacuous), and the
  1D equal-mass head-on exchange was observationally identical to
  pass-through (EPEC returned an unidentifiable second world).
- Fixes below are covered by the test suite (36 tests as committed on
  2026-11-21: 28 in the five test files that existed, 3 probe tests, 3
  oracle-truth regressions, 2 re-crossing regressions) and
  `scripts/recoverability.py`, whose output is quoted per item.

## Fixes (audit-driven)

| id | issue | status | evidence |
|---|---|---|---|
| FIX-1 | **Shuffled control vacuous.** `shuffle_rules` grouped by `(kind, t)`; permutation of rows leaves the fact multiset unchanged, so permutation-invariant consumers saw identical constraints. | **fixed** | `psychopomp/controls.py` now deranges exit payloads **across episodes** (Sattolo single-cycle, no fixed point for n>=2). `tests/test_controls.py` asserts kinds/times preserved, corpus exit marginals preserved, alignment changed, deterministic. `recoverability.py`: deranged targeted corpus → `worlds mean 0.00, contact_required 0/6` while marginals stay preserved — the control demonstrably removes the constraint content. |
| FIX-2 | **Identifiability.** In 1D equal-mass head-on collisions the velocity exchange is indistinguishable from pass-through; hidden-contact AUC / identity pairing were not identifiable targets. | **fixed** | Simulator moved to **2D free space with off-axis contacts** (`psychopomp/sim.py`, config `SimConfig` W/H + occluder rectangle; equal-mass exchange of normal components). Off-axis contact changes outgoing directions, so control-free worlds die. `recoverability.py` targeted family (6/6 with hidden contacts): `contact_required 6/6` (contact occurrence identifiable), `worlds mean 2.00` (pairing stays ambiguous — reported honestly), `truth-in-worlds 6/6`, reference exit-side accuracy `12/12`. The 1D head-on degeneracy is kept as a documented test (`test_head_on_1d_degenerate_is_unidentifiable`). |
| FIX-3 | **Validator C1 incomplete.** `validate()` did not reject unmatched exits or duplicate entry assignments for externally supplied `World` objects. | **fixed** | `tests/test_epec.py::test_validate_c1_rejects_unmatched_exit_and_duplicates`. C1 requires complete exit coverage and no duplicate assignment; `consistent_worlds` still enforces it by construction. |
| FIX-4 | **Publication cleanup.** README referenced the pre-rename URL. | **fixed** | URL is `https://github.com/ilPez00/physis-psychopomp`; repo renamed, remote updated. |
| FIX-5 | **Truncated episodes yield spurious zero worlds.** A ball still inside at episode end cannot be contact-checked (C5 needs both exits). | **fixed as a documented contract** | `epec.py` docstring states the cleared-episode contract; `recoverability.py` builder conditions on `enters == exits`; zero-world count on the targeted family is now 0/6. |
| FIX-6 | Collision sign convention was inverted (`rn < 0` on the a→b normal); equal-position crossings could never exchange. | **fixed** | Found by tests inside this session; `rn > 0` on the closing normal; off-axis fixture exists only because the physics now fires. |
| FIX-7 | Boundary labels inverted (entering from below reported "top"). | **fixed** | `_enter_side`/`_exit_side`; off-axis fixture asserts `bottom` entries. |
| FIX-8 | Tunneling guard lived in `run()`, not in config validation. | **fixed** | `SimConfig.__post_init__` asserts `speed*dt < min(occluder w,h)`; `test_config_rejects_tunneling`. |

## Improvements (open)

| id | item | gate | status |
|---|---|---|---|
| IMP-1 | CI: GitHub Actions running `pytest` on push (public repo). | green run | workflow landed (`.github/workflows/ci.yml`, uv + pytest + recoverability + demo); run status depends on the account's Actions billing — verify with `gh run list`, never assume |
| IMP-2 | LICENSE decision. Currently none; publication is not a reuse grant. Operator decision. | operator | open |
| IMP-3a | clingo/ASP port of the C1–C5 rules (unweighted). | ASP encoding reproduces the Python worlds on the canonical fixtures | **done** (`psychopomp/asp.py`, clingo 5.8.3; numeric facts computed in Python — clingo is integer-only — combinatorial search in ASP; `tests/test_asp.py` cross-checks straight/off-axis/head-on/teleport) |
| IMP-3b | Probabilistic weighting of worlds (EPEC proper). epec-vanilla is reference only, no license file — ask D'Asaro first. | weighted counts reproduce orderings, sanity controls | open |
| IMP-4 | Physis export adapter: observable log → physis observations (typed props, provenance). | round-trip query on a fixture | open |
| IMP-5 | M2/M3 probe harness on CPU with handcrafted features (stupid-control-first per Rule 2), before any GPU arm. | harness runs end-to-end, shuffled arm first-class | **done** 2026-11-21 — `psychopomp/probes.py` + `psychopomp/fixtures.py` + `scripts/probes.py`, 3 tests. Measured: targeted family M2 top-1 **0.17 vs chance 0.50** (endpoint-only ranking cannot beat chance: the two consistent worlds are relabellings with identical total deflection), M3 contact detection **1.00**, deranged control **0.00**; random family M2 1.00 vs chance 0.94, M3 1.00, shuffled 1.00 (the control does not bite where worlds are near-unique — stated, not hidden). This is the pre-registered gate's second half measured on CPU: the oracle-free reference does not beat chance on M2, and the shuffled control removes the M3 information. |
| IMP-6 | Filter null test: shuffled-event null log must not yield consistent worlds at the same rate (already yields 0.00 mean on the targeted corpus; formalize as a test). | test fails if null arm converges to the real arm | **done** 2026-11-21 — `tests/test_controls.py::test_null_arm_does_not_reproduce_the_filter_verdict`: real 6/6, null 0/6, worlds 2.00 vs 0.00; an identity shuffle fails the test. |
| IMP-7 | Filter tightness on re-crossing episodes (multiple intervals per ball). Original concern: "enumeration retry handles only one contact pair". | a re-crossing episode filters correctly, and a multi-contact search is not single-pair | **premise corrected 2026-11-21, work closed.** Measured: `_pairings` is a *recursive* perfect pairing over every C4-failing match, not a single pair. One ball crossing twice (4 events) filters to exactly the truth in 1 world (`test_single_ball_recrossing_is_filtered_to_the_truth`); two balls crossing twice yields 4 consistent worlds, all contact-free — identity ambiguity, not filter failure (`test_two_ball_symmetric_recrossing_is_ambiguous_not_wrong`). The genuinely unreachable case is an episode needing **two hidden contacts**: 400 random 4-event attempts found 0, so no generator can exercise it. Interval segmentation stays unimplemented by evidence, not by neglect; the gate for it is a reachable generator for two concurrent hidden contacts. |
| IMP-8 | `README` demo script so the quickstart is executable. | script output matches REPRO table | **done** (`scripts/demo.py`, prints PASS on the two canonical worlds) |
| IMP-9 | CI red on `main` after `dcbc611`: `scripts/recoverability.py` imports `psychopomp.fixtures`, which was never committed — 28 tests passed, then the gate died with `ModuleNotFoundError`. | `gh run list` green on `main` | **fixed** 2026-11-21 — the four files that made the imported module exist are committed; a clean-room run of tracked files plus them passes tests/31, recoverability, probes and demo. |
| IMP-10 | A truncated episode reported `contact_required: False` ("confirmed no contact") although C5 cannot be decided without both exits. | reporting layer matches the cleared-episode contract | **fixed** 2026-11-21 — `summarize` reports `cleared` and sets `contact_required: None` for uncleared logs; `test_truncated_episode_reports_contact_as_undecided_not_false`. |
| IMP-11 | physis export adapter (IMP-4). | typed props round-trip on a fixture | **deferred with the measured obstacle** 2026-11-21 — `physis 1.9.1` exposes `observe <tree>` (file scan) and `remember <text> --outcome`; no typed-observation ingest from JSONL. A typed adapter needs the MCP `physis.remember` schema or a store writer: a cross-repo decision, not faked. |

## Blocker: GPU phase

Checked 2026-11-20: `tailscale status` reports **omo offline, last seen 5 days**
(and `ssh omo-ts` times out). The GPU phase therefore **cannot be scheduled**;
it stays blocked until the node is reachable, and this is recorded rather than
worked around. Nothing in this repo has been run on a GPU.

## Stop rule

No GPU arm runs until IMP-1..IMP-3 are green **and**
`scripts/recoverability.py` prints `truth-in-worlds == episodes` on the
targeted family. Both currently hold; the pre-registered failure criteria in
`2026-11-20-PREREG.md` remain the decision rule for Claim A. Independently of
the rule, the GPU node is offline (omo, last seen 5d on 2026-11-20), so the
phase is blocked, not merely unscheduled.

## Status log

- 2026-11-20: audit fixes landed (FIX-1..8). 23→28 tests (ASP port added).
  Recoverability gate reproduces on a fresh public clone. omo offline.
