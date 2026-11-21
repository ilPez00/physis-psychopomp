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
