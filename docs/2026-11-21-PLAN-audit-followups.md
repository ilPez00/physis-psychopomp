# Plan — audit follow-ups and the identity channel (2026-11-21)

Status: **PLAN**, written top-down before any of it was executed. Precedence when
documents disagree: code > test > receipt > captured artifact > doc > plan.
Executed items get a status line appended here; items are never rewritten into
their own outcome. Predecessor: `2026-11-20-FIXES-AND-IMPROVEMENTS.md`.

Context for the reader: the M2 baseline reached **0.17 top-1 against a 0.50
chance floor** on the targeted family, and that was initially read as "the
endpoint-only reference cannot beat chance". The check that produced this plan
found two things worth separating:

- the baseline is measuring an instrument that **only logs instantaneous
  entry/exit velocity**, so identity is destroyed before any model sees it;
- the oracle-truth helper could return a non-bijective pairing when two balls
  shared timestamps (fixed 2026-11-21); every corpus so far is attributable
  (random 8/8, targeted 6/6), so no published number is retracted.

## P1 — IMP-6: the null arm is a test, not a printout

The shuffled control is currently demonstrated by `scripts/probes.py` output and
one probe test. It must fail if it ever converges to the real arm.

Gate: `tests/test_controls.py` contains a test asserting, on the targeted
corpus, real `contact_required` = 6/6 and null = 0/6 with fixed seed 12345, and
that `worlds` mean falls from 2.00 to 0.00. Mutation: making `shuffle_rules`
the identity must turn it RED.

## P2 — instrument self-check in CI

The oracle-truth defect was latent for two corpus generations. Encode the
property, not the incident: every episode a shipped corpus can produce must have
an **attributable** truth, and that truth must be **contained in** the
enumerated worlds whenever the enumeration is non-empty.

Gate: new `tests/test_instrument.py`; asserts `excluded_ambiguous_truth == 0`
for `random_corpus(8)` and `targeted_corpus(6)`, truth ⊆ worlds for ≤2-ball
logs, and that a synthetic shared-timestamp episode is *excluded*, not scored.
Mutation: reverting `truth_matches` to time-only lookup must turn it RED.

## P3 — REPRO table generated, not typed

`REPRO.md`'s expected-output block is prose that can drift from the code.
Generate it from the scripts and compare.

Gate: `scripts/repro-table.py --check` exits 0 iff the checked-in block equals
regenerated output; a CI step runs it. Mutation: editing one number in REPRO.md
must fail the check.

## P4 — Amendment A2: the pre-contact position channel (novel, pre-registered)

**Question fixed in advance.** Does adding a *physically observable* pre-contact
position to the enter/exit events raise M2 top-1 above the relabeling chance
floor (0.50 on the targeted family; 0.25 on the 4-world symmetric re-crossing
case)?

**Why it may work.** The ball is visible up to the step it crosses the occluder
boundary. Its position there is identity-bearing: with straight-line motion,
`Δy = vy·Δt` must hold along a true pairing, so a world that pairs an entry with
an exit of different `y` (given comparable `vy`) is inconsistent even though its
velocities match. The current log discards that coordinate, which is why two
relabeled worlds tie.

**Falsifier, fixed now.** If top-1 stays ≤ chance after the channel exists,
then identity is **not recoverable from what this instrument observes**, the
honest claim is exactly that, and M2 is withdrawn as a target — not chased with
GPU arms. The reverse (top-1 jumps) makes M2 a real task and the GPU phase
schedulable on evidence rather than hope.

Gate: `scripts/probes.py` prints endpoint-only and position-continuity top-1
side by side; both corpora; the falsifier is recorded verbatim in the receipt.

## P5 — degenerate-corpus generator

Corner entries, shared timestamps, tunneling attempts and truncated episodes
exist as individual tests. A generator makes them continuous so refusals and
exclusions stay exercised.

Gate: generator emits at least one episode of each degenerate class and its
construction is asserted (no silent skip); asserted counts in the test.

## P6 — IMP-4: physis export adapter

Provenance-bearing events exported as typed physis observations, so the
evidence this repo produces is queryable by the world model instead of living
only in JSONL.

Gate: round-trip query on a canonical fixture — export, observe, query back the
typed properties of both worlds and the excluded/support counts. Deferred if the
physis binary/store on this host cannot answer; the receipt must say which.

## Order and stop rule

P1 → P2 → P3 → P4 → P5 → P6. Each lands as its own commit with its gate output
quoted. Stop early if a gate fails twice on the same item: record FAIL, do not
retry a third time. P4's result is the one that decides whether any GPU work is
scheduled; everything before it is instrument hygiene.

## Execution status — 2026-11-21

- **P1 DONE.** `tests/test_controls.py::test_null_arm_does_not_reproduce_the_filter_verdict`:
  real `contact_required` 6/6, null 0/6, worlds mean 2.00 vs 0.00.
  Mutation-checked: an identity shuffle makes null == real and the test fails.
- **P2 DONE.** `tests/test_instrument.py` (3 tests): attributable bijective
  truth per episode, truth ⊆ enumerated worlds for both shipped corpora, and a
  shared-timestamp log excluded rather than scored. Mutation-checked: restoring
  the time-only lookup yields `((0,0),(0,0),(1,1),(1,1))`, exclusion 0, RED.
- **P3 DONE.** `scripts/repro-table.py` + CI step; REPRO's block is generated
  between markers. Drift-checked: editing `2.00` to `2.01` makes `--check` exit
  1 with the diff.
- **P4 DONE, falsifier NOT triggered — and the result changes the GPU plan.**
  The shipped corpora could not answer the question (random: chance 1.00, one
  world; targeted: contact episodes excluded by design), so the family the
  question needs was built: `parallel_recrossing_corpus` (2 balls, parallel,
  both crossing twice → 4 contact-free worlds, attributable truth).
  Measured on 6 such episodes: **endpoint-only 0.00 top-1 vs chance 0.25;
  position continuity 1.00 vs chance 0.25** (excluded 0). Position continuity
  decides every episode.
  Consequence, stated plainly: M2 is no longer "unbeatable by an oracle-free
  method" — a hand-coded physics residual solves it perfectly. A learned model
  therefore has **no headroom** on M2 or M3 (M3 is already 1.00). Scheduling GPU
  arms on these tasks would measure a ceiling, not learning. Proposed A3
  (needs operator sign-off, not implemented here): a harder variant —
  positions quantized to 5 units, occlusion of wall-bounce events, and/or
  observation noise — where the residual is insufficient and a model could add
  something, with its own chance floor measured first.
- **P5 DONE.** `tests/test_degenerate.py` (4 tests) covers truncated, shared
  timestamp, tunneling config and cleared episodes. Writing it exposed a real
  reporting bug: a truncated episode reported `contact_required: False`
  ("confirmed no contact") when the truth is "undecidable"; `summarize` now
  reports `cleared` and `contact_required: None` for uncleared logs.
- **P6 DEFERRED with the measured obstacle.** `physis 1.9.1` offers
  `observe <tree>` (file scan) and `remember <text> --outcome`, with no typed
  observation ingest from JSONL, so "typed props round-trip" cannot be built
  from this repo alone: it needs either the MCP `physis.remember` schema or a
  store writer, which is a cross-repo design decision. Not faked.

Test count: 45 at the end of this plan (36 at its start); see the round-2
plan for what came after. The CI job, not this line, is the authority.
