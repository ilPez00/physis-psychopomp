# P1 execution queue

See [plan](plan.md) for fixed boundaries and proposed numeric fixtures. Tests
and scripts listed below are targets, not commands claimed to exist today.
No step is preregistered until a claim and frozen card are committed.

## A — Local discovery demo

- [x] **A1: Freeze finite-law card.** [R-P1.47](../docs/2026-11-23-PREREG-R-P1.47-active-law-selection.md)
  fixes the law/state table, balanced shuffle, separate budgets and gates.
  Calibration values `1` and `3` are nominal-compatible; only `5` and `7`
  reject the nominal model.
  Frozen and pushed at `38b5d70` before implementation or measurement.
- [x] **A2: Exact Bayesian selector.** R-P1.47 replays all eight rows with
  target-specific information gain, positive-gain selection and abstention.
  Run `.venv/bin/python -m pytest -q tests/test_active_design.py` and
  `.venv/bin/python scripts/active-law-selection-prereg.py`; see the
  [receipt](../research/loops/results/active-law-selection-20261123/receipt.json).
- [x] **A3: Exit-event fixture.** [R-P1.48](../docs/2026-11-23-PREREG-R-P1.48-active-exit-fixture.md)
  frozen at `d48206f`; actual exits and scalar-only acquisition passed.
  Gates: `scripts/active-exit-prereg.py`, `tests/test_active_exit_fixture.py`.
  [Receipt](../research/loops/results/active-exit-20261123/receipt.json).
Delegation: [routing and stop rules](DELEGATION.md). A4 and the receipt work
are split into two TUI-sized briefs —
[W1 freebuff](briefs/W1-freebuff-active-loop.md) (DeepSeek V4.1 Flash, high;
**superseded** — implemented inline while freebuff was out of hours) and
[W2 free-pi](briefs/W2-freepi-receipt-verifier.md) (GLM 5.3 Flash, high).
One writer at a time; a delegate's claim is not a gate.

- [x] **A4: Bounded execute and verify loop.** `psychopomp/active_loop.py`:
  one diagnostic per `Session`, second call raises `BudgetExhausted` without
  touching the simulator, unknown policy refused before any simulation,
  malformed log abstains, shuffled control never resolves. Gates:
  `tests/test_active_loop.py` (5) + receipts in `tests/test_active_receipt.py` (7).
  Three mutations were run against the guards (budget, shuffle, adaptive pick)
  and each turned a test red before the restore.
- [~] **A4 (half): receipts.** `psychopomp/active_receipt.py` binds a decision to
  the frozen fixture (`predictions_for`) and refuses a self-consistent lie;
  8 tests. Written by the W2 delegate on an **unpinned model**, then reviewed and
  fixed here — not a delegate result. The loop half is still open.
- [x] **A4: Bounded execute and verify loop.** Reject a second diagnostic action,
  non-allowlisted action and forged receipts. Verify both laws and all reset
  states, losing controls and abstention. Depends on A2/A3. Gate:
  `tests/test_active_discovery.py` and the demo replay in `scripts/research-gates.py`.
  First review `work/occluded-evidence-proof` (`2f08e49`) for reusable receipt
  and verifier code. Its four-cell early/late-observer fixture is separate
  from R-P1.48; neither card's results substitute for A4 on this fixture.
  **CLOSED 2026-11-27 — each named guard already had a test, 17 across three
  files:** second diagnostic → `test_second_diagnostic_is_refused`;
  non-allowlisted policy → `test_unknown_policy_refuses_before_simulation`;
  forged receipt → 11 assertions in `tests/test_active_receipt.py`;
  abstention on a malformed log → `test_malformed_log_abstains`. Both laws and
  all reset states →
  `test_adaptive_resolves_both_laws_and_all_states`; losing controls →
  `test_passive_and_shuffled_never_resolve`. Run:
  `.venv/bin/python -m pytest tests/test_active_{loop,discovery,receipt}.py`
  → **17 passed**. The item was stale, like D4 and D6 before it: the work
  existed and the checkbox did not.
- [x] **Checkpoint A (local half).** `scripts/active-discovery.py` — selected
  action sealed before acquisition; verifier checks the executor's actual
  8/8 decisions against the frozen fixture; 8/8 shuffled abstentions; second
  action refused. A wrong posterior or a reading swapped after the update
  now fails the gate. Adaptive cases also save separate plan, observable log
  and decision files; `--replay` reprojects the saved event without simulation.

## B — Real Physis-next evidence

- [x] **B1: Inspect current store APIs.** [Measured](../docs/notes/2026-11-23-b1-physis-evidence-ledger.md)
  against `physis` 1.9.1 + `physis-core` 0.3.0: `observe` is idempotent (10 rows
  after three runs), `subject` reads back typed props, `packet` + `packet-verify`
  verify and fail on one appended junk line. **Correction:** physis-next has no
  hypothesis ledger — rivals live in physis-core, so the demo binds two stores by
  a packet hash. **Trap:** `PHYSIS_DATA_DIR` is ignored; `PHYSIS_CORE_DIR` isolates.
- [ ] **B1 (superseded note): Inspect current store APIs.** Fetch canonical origin to an isolated
  source-bearing branch; prove both hypotheses and a revision can be queried
  in a temporary store. Record exact ref, store path and readback command.
  Independent of A; no edits in the paused rebase.
- [x] **B2: Import fixture under lock.** Store-level half landed (see E1). CLI half remains.
- [x] **B2 (CLI): import subcommand.** `physis import` at `4f0ce96d8`: 5 rows in, re-import 0/5 dup, `subject` readback 5, torn tail refused, and two concurrent imports leave **5 rows / 5 unique keys** with one process aborting by design. `cargo test -p physis-cli` green (1 + 6 tests); smoke committed upstream as `scripts/psychopomp-import-smoke.sh`. In Physis-next, prove five-row import,
  order, repeat/concurrent/in-batch dedup and collision handling; reject bad
  provenance, counterfactuals and torn tails; confirm dry-run has zero writes.
  Depends on B1. Gate: targeted Rust importer tests, CLI import/query smoke
  and repo-prescribed Rust checks on omo after resource checks.
- [x] **B2/E1: importer hardened.** `f015751f3c` on `feat/psychopomp-import`:
  approved-source, provenance-typed validation, canonical subject, digest and
  input bounds, conflict refusal on same-key/different-payload, unterminated-tail
  and redaction refusal — all before the append and re-checked under the lock.
  14 module tests (4 red first), 52 store tests, workspace fmt, store and CLI
  clippy clean, smoke PASS including a two-process overlap. The 8-row executed
  export still imports 8 then re-imports 0 with 8 duplicates, and replays
  `VERIFIED` at seqs 0–7 with rows identical to the saved capture except ingest
  time. [Receipt](../docs/notes/2026-11-23-e1-importer.md#hardening-pass-at-f015751f3c-2026-11-24).
  **Open:** no producer-authentication claim; `ci-local.sh` not rerun (three of
  its steps already fail on base `f2b319cb8`).
- [x] **A4 local replay:** Persist the plan before acquisition and the observed
  event before recording the decision. Reopened replay rejects a jointly
  fabricated reading and decision if the original event is retained.
  [Run instructions and limits](../docs/notes/active-discovery-replay.md).
- [x] **B3: Link real evidence.** Feed executed rows into the isolated store and
  link hypotheses/revision; reopen and recompute from receipt IDs. Compare to
  A4 across both laws and verify no unsupported update. Depends on A4/B2.
  **Store replay measured:** eight executed rows imported and replayed by
  exact producer key and store seq at importer `62c3a18a0`. Revision proposals
  bind two rivals to the verified row; applying them at `40f8a80e`/`3fc720f1`
  produced opposite polarities on the same cited evidence, and `replay --at`
  shows no belief before the transition and `Supported` after.
  **Acceptance:** [isolated replay receipt](../research/loops/results/active-isolated-b3-20261124/)
  verified both law directions, four UUID-to-law assignments, exact citations
  and historical verdicts. Withholding each row before and after revision
  refused all four probes without changing ledger bytes.
- [x] **Checkpoint B (saved store):** Replayed the real imported observations
  and reopened the isolated rival histories from a clean, pinned checkout.
  No new Rust import in this run; current importer gates stay under B2/E1.

## C — Organizational identity

- [x] **C1: Freeze turnover card.** Frozen at `2d8299`; see [R-P1.49](../docs/2026-11-23-PREREG-R-P1.49-turnover-identity.md).
- [x] **C2: Run feedback versus replay.** 12 cells, O1–O4 upheld, two mutations caught; [receipt](../research/loops/results/turnover-identity-20261123/receipt.json). Fix tick order, role update, perturbation,
  recovery horizon, persistent-residence metric and loss controls. Register
  claim, seal before execution; record lineage separately. Depends on A4.
- [ ] **C2: Run feedback versus replay.** Require full component turnover and
  identical passive logs, then test both one-role perturbations, relabelling,
  feedback removal, sham and independent-copy controls. Gate:
  `tests/test_turnover_identity.py` plus prereg replay. Depends on C1.
- [x] **C3: Transfer evidence loop (local half).** `psychopomp/turnover_evidence.py`: passive probe buys 0 bits, one post-disturbance observation buys 1, receipts verify 4/4 and abstain 4/4. Gate `scripts/turnover-discovery.py`.
  **Store replay measured:** eight one-tick `loads` observations imported at
  Physis-next `2773ccbbc`; 4/4 perturbed resolutions and 4/4 passive
  abstentions after reopen. See [receipt](../research/loops/results/turnover-store-replay-20261124/).
- [x] **C3: Turnover rival revision smoke.** One role-1 pair in an isolated
  `physis-core` ledger. Passive seq 0 left ledger bytes unchanged before
  and after revision; perturbed seq 1 drove opposite revisions, verified
  in fresh processes. The replay command itself remains read-only.

## D — Further research cards

- [x] **D1:** [R-P1.57](../docs/2026-11-24-PREREG-R-P1.57-paired-counterfactual.md)
  frozen at `ae1cba8`. All five checks matched: equal marginals, paired
  residual-reuse MAE `0` versus `3`, and two-candidate coverage `8/8` per law.
  Next D2: noise, budget, and out-of-catalogue abstention.
- [x] **D2 finite witness:** [R-P1.58](../docs/2026-11-24-PREREG-R-P1.58-budgeted-model-mismatch.md).
  Missing/out-of-support readings abstained; in-support mimics falsely
  declared a known law in 2/2 cases. Not empirical noise calibration.
- [x] **D2 confirmation follow-up:** [R-P1.59](../docs/2026-11-24-PREREG-R-P1.59-paired-confirmation.md).
  Same-episode confirmation catches 2/2 eligible mimics. A fresh reset at
  equal mean cost falsely accepts 4/8; a paired-equivalent unseen law still
  falsely resolves in 2/2 eligible cases.
- [ ] **D3:** Contact/fold/action-disturbance counterfactuals and horizon sweep.
  Depends on D1 and a preregistered discriminating instrument.
- [x] **D4:** True delay versus outward sampler on identical crossing tasks.
  Independent. Preserve R-P1.43 historical verdict.
  [R-P1.66](../docs/2026-11-27-PREREG-R-P1.66-true-delay.md): the true delay is
  an **exact null for this estimator** (margin `0.200` at every lag, to twelve
  decimals) while the lagging sampler moves it (`0.200 → −0.550`). R-P1.43's
  Amendment 1 was right; the card's own P2 prediction was wrong and is recorded
  as failed. The instruments *are* distinguishable as logs, so this is a result
  about the estimator, not about a missing implementation.
- [ ] **D5:** Composite masks, non-convex/reflex corners, finite-radius
  crossing labels and calibration. Independent. Gate seam/control pair before
  expanding the planner.
- [x] **D6:** Rotating-observer frames; separately test coordinate invariance
  and physical coverage changes. Independent.
  [R-P1.65](../docs/2026-11-27-PREREG-R-P1.65-rotating-observer.md): coordinate
  invariance **holds** (round trip error `0.0`, no world created or destroyed,
  scene verdict invariant 5/5, no hidden field). Physical coverage under a
  rotating *occluder* is **out of scope by declaration** — the simulator has
  axis-aligned rectangles only. The card's P4 failed for a decoder reason:
  `attribute` rebuilds counterfactuals in world coordinates, so a rotated
  observation is scored against unrotated candidates.
- [ ] **D7:** Partially overlapping producers plus incorrect tags at matched
  marginal delivery. Independent; require matched anonymous and tag-shuffled
  controls before claiming a fusion rule.

## E — Graph repair (proposals only)

- [~] **E0: Verify the admission/retraction claims.** [Probed](../docs/notes/2026-11-23-e0-admission-retraction-probes.md).
  **Confirmed:** `declare` codes 0/1/2/3, refusals persist in the log, `tms` is
  counterfactual (14 rows before and after), unknown predicate writes nothing.
  **Sharp edge:** repeating a refused triple returns **3 (UNVERIFIABLE)**, not 1 —
  a retry-until-admitted loop spins. **Still open:** `as-of` returned no rows at a
  seq that exists (query shape unknown), and `removed:rel|…` was not attempted.
  Consequence: E4 limited to `ADD_EDGE` + `REQUEST_EVIDENCE` until those two land.
- [x] **E1: Importer module.** `physis-store/src/psychopomp.rs` on branch `feat/psychopomp-import` at `9520ea6e8`: UTC ingest explicit, `at_seconds` preserved, OBSERVED-only, counterfactual refused, dedup key `psychopomp:<subject>#<seq>` with a final condition inside `append_observations_if`. 8 tests, 2 mutations caught on omo. [Note](../docs/notes/2026-11-23-e1-importer.md). CLI + smoke committed (`62c3a18a0`), `cargo test -p physis-cli` green, two-process concurrency leaves 5 rows / 5 unique keys, and the **round trip measured on 24 real simulator rows** (24 appended, re-import 0/24 duplicate). Evidence linked: claim `26f1ebc3` Supported, citing the producer export hash and the consumer audit-packet hash (`7badfc82…`, `91f3236b…`).
  **Defect found and fixed** at `65e3e02f2`: a batch whose rows were partly
  already imported aborted with "observation log changed while importing" — the
  predicate judged all read keys, not the pending ones — so a retry could never
  converge. Now appends only the unknown rows; pinned by a unit test and a smoke
  step (`2773ccbbc`). The store module had also been committed unformatted.
- [x] **E2: Revision-pinned adapter.** `psychopomp/physis_snapshot.py`: parses
  `object list --json` + `object get --json`, normalises both edge directions,
  refuses edges naming unobserved entities, and pins a revision (own digest, or
  an external packet hash). 5 tests; two mutations caught; verified on a real
  scratch world (9 entities, 2 edges, 10 evidence seqs, deterministic revision).
- [x] **E3: Symbolic decoder (first cut).** `psychopomp/graph_patch.py`: agreed edges stay `HYPOTHESIZED`, disputed ones emit both sides plus `REQUEST_EVIDENCE` with the best-gain probe, an empty admissible set is `UNKNOWN`, refused triples are never re-proposed, unobserved endpoints refused. 8 tests, three mutations caught, demo gated. **Still open:** the controlled corrupted-graph benchmark vs no-repair/deterministic/shuffled.
- [x] **E4 (partial): Route through Physis — proposals only.** R-P1.53 measured `declare` end to end: 1/3/2/0 with log deltas, refusal persisted, repeat `UNVERIFIABLE`, nothing written on invalid. Still blocked for retraction: `as-of` and `removed:rel|…`.
- [x] **E4: Route through Physis — additions complete, retraction blocked.** Pre-admission check available read-only (`physis claim`: 0/2, absence is not refutation). RETRACT is blocked upstream: tombstones apply only to code sources (`engine.rs` `is_code_source` filter) and `tms`/`whatif` never write. See [surfaces note](../docs/notes/2026-11-23-e4-admission-and-retraction-surfaces.md).
- [x] **E4 boundary probes:** R-P1.54 tested two direct refusals, not a
  plan-driven executor. R-P1.55's audited replay took exactly one proposal from
  the decoder and verified that the fold cited the newly written assertion.
  Production authorisation remains deliberately unbuilt.
- [ ] **E4 (retraction): blocked upstream.** `whatif` + retraction preview + authorisation;
  a structurally valid proposal still does not mutate the graph.
- [x] **E5: Benchmark.** R-P1.52 (frozen `5dc9897`) capacity 4/4, D1–D6 upheld: exact `1.00/1.00`, closure baseline `0.00`, shuffled `0.00`, agreed arm abstains into one probe. [Receipt](../research/loops/results/decoder-capacity-20261123/). Supersedes R-P1.51's D4. **Remaining:** the agreed arm's overall precision is 0.67 — a repair-quality claim needs a predictor arm, not this benchmark.
- [~] **E5 (first cut, superseded).** R-P1.51 froze at `308dae`, **failed on D4**: exact precision/recall 1.00, shuffled 0.00, empty `UNKNOWN`, nothing applied — all upheld; D4's arm omitted both missing edges, so its predicted agreement was unsatisfiable. Pinned as failing. **Next:** follow-up card with the agreed-case arm defined correctly, plus a genuine no-repair and deterministic-only baseline (this run had neither, so it is a contract benchmark only).
- [ ] **E6: Learned ranker** only with valid measured E5 headroom. The
  [R-P1.56](../docs/2026-11-23-PREREG-R-P1.56-repair-headroom.md) result is
  exploratory (null sized to 6 edges against a 3-edge decision, recall divided
  by the whole truth set). [R-P1.60](../docs/2026-11-25-PREREG-R-P1.60-repair-eval.md)
  re-measured on a calibrated null: **no headroom** — top-3 support is at
  chance on development (0.139 vs 0.141), 0.057 above it held-out, and its
  completion error is worse than silence (0.230 vs 0.143). E6 stays closed; the
  missing ingredient is information the surviving-world counts do not carry.
  [R-P1.61](../docs/2026-11-25-PREREG-R-P1.61-one-probe.md) then bought one:
  a correctly paired probe at TPR 0.8 / FPR 0.2 scores 0.238 against passive
  0.230, its permuted-edge control 0.232 and an uninformative control 0.235.
  The probe replaced 2.5 of 3 proposed edges on 21/24 cases and raised accuracy
  on none. R-P1.61 concluded "the sensor, not the policy, is the binding
  constraint". [R-P1.62](../docs/2026-11-26-PREREG-R-P1.62-probe-budget.md)
  swept quality and budget separately and **falsified that reading both ways**:
  no single probe clears passive+0.10 at any quality — even a perfect sensor
  gives 0.222 against a 0.294 bar — while budget alone needs k=21 at q=0.8 and
  k=3 at q=1.0. The two multiply. No headroom: nobody has priced a query yet,
  and probing the whole pool is a scanner. E6 stays closed.

### Guarded repair rollout

- [x] **Writer foundation:** Physis-next `1da2aefeab` fails closed before
  appending to unreadable or unterminated observation logs.
- [x] **Guarded verb (staged):** `physis repair` at `27da5323a` in PR #315 —
  world-side evidence, an approval bound to the exact state, one use checked
  under the store lock; 6 integration tests (including two writers racing one
  approval in separate runtimes in one process) plus a CLI refusal receipt.
  The digest binds content; it does not authenticate an operator.
- [x] **Withdrawal surface:** `physis retract` / `physis revoke` at
  `d3d7627e0`, preview-by-default over the runtime's append-only records; the
  five-step shell flow runs. **Finding:** the preview reported `0 lost, 0
  weakened` for a withdrawal that removed an entity and its edge. Block
  approval until the preview is truthful or refuses, and its digest binds the
  exact range and fold inputs.
- [ ] **Writer staging:** release needs the repo's local gate
  (`scripts/ci-local.sh`) at the exact head, a restorable backup and an approval
  separate from the preview. Hosted CI is permanently unavailable (unpaid
  account, zero steps) and is not a gate anywhere on this fleet.
- [ ] **E5 acceptance:** held-out observation-generated candidates, independent
  labels, matched no-repair/deterministic/shuffled controls, and missing-edge
  denominators. [R-P1.60](../docs/2026-11-25-PREREG-R-P1.60-repair-eval.md)
  supplies the corrected measurement and returns **NO HEADROOM**; the gate is
  still open for a fixture whose candidates carry signal, because this one has
  no non-vacuous precise arm (consensus 1.0 and 0.9 both abstain on all 24
  cases) and its recall arm is worse than silence under squared error. See
  [rollout](../docs/notes/production-repair-rollout.md).
