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
- Fixes below are covered by the test suite (23 tests) and
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

| id | item | gate |
|---|---|---|
| IMP-1 | CI: GitHub Actions running `pytest` on push (public repo). | green run |
| IMP-2 | LICENSE decision. Currently none; publication is not a reuse grant. Operator decision. | operator |
| IMP-3 | clingo/ASP port of the C1–C5 rules + probabilistic weighting (Claim B prerequisite; epec-vanilla is reference only, no license file — ask D'Asaro first). | ASP encoding reproduces C1–C5 worlds on the canonical fixtures |
| IMP-4 | Physis export adapter: observable log → physis observations (typed props, provenance). | round-trip query on a fixture |
| IMP-5 | M2/M3 probe harness on CPU with handcrafted features (stupid-control-first per Rule 2), before any GPU arm. | harness runs end-to-end, shuffled arm first-class |
| IMP-6 | Filter null test: shuffled-event null log must not yield consistent worlds at the same rate (it already yields 0.00 mean on the targeted corpus; formalize as a test). | test fails if null arm converges to the real arm |
| IMP-7 | Filter tightness on re-crossing episodes (multiple intervals per ball): enumeration retry handles only one contact pair. Cleared single-crossing episodes are the supported scope; multi-crossing needs interval segmentation. | test: re-crossing cleared episode yields the truths among worlds with bounded counts |
| IMP-8 | `README` demo script (`scripts/demo.py`) so the quickstart is executable. | script output matches REPRO table |

## Stop rule

No GPU arm runs until IMP-1..IMP-3 are green **and**
`scripts/recoverability.py` prints `truth-in-worlds == episodes` on the
targeted family. Both currently hold; the pre-registered failure criteria in
`2026-11-20-PREREG.md` remain the decision rule for Claim A.
