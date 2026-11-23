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
Delegation: [routing and stop rules](../DELEGATION.md). A4 and the receipt work
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
- [ ] **A4: Bounded execute and verify loop.** Reject a second diagnostic action,
  non-allowlisted action and forged receipts. Verify both laws and all reset
  states, losing controls and abstention. Depends on A2/A3. Gate:
  `tests/test_active_discovery.py` and the demo replay in `scripts/research-gates.py`.
  First review `work/occluded-evidence-proof` (`2f08e49`) for reusable receipt
  and verifier code. Its four-cell early/late-observer fixture is separate
  from R-P1.48; neither card's results substitute for A4 on this fixture.
- [x] **Checkpoint A (local half).** `scripts/active-discovery.py` — 8/8 diagnoses
  receipted and independently verified, shuffled control abstains, second action
  refused; now a research gate. **Still open:** the transcript is local only, and
  Phase 2 has not replayed it from a Physis-next store.

## B — Real Physis-next evidence

- [x] **B1: Inspect current store APIs.** [Measured](notes/2026-11-23-b1-physis-evidence-ledger.md)
  against `physis` 1.9.1 + `physis-core` 0.3.0: `observe` is idempotent (10 rows
  after three runs), `subject` reads back typed props, `packet` + `packet-verify`
  verify and fail on one appended junk line. **Correction:** physis-next has no
  hypothesis ledger — rivals live in physis-core, so the demo binds two stores by
  a packet hash. **Trap:** `PHYSIS_DATA_DIR` is ignored; `PHYSIS_CORE_DIR` isolates.
- [ ] **B1 (superseded note): Inspect current store APIs.** Fetch canonical origin to an isolated
  source-bearing branch; prove both hypotheses and a revision can be queried
  in a temporary store. Record exact ref, store path and readback command.
  Independent of A; no edits in the paused rebase.
- [ ] **B2: Import fixture under lock.** In Physis-next, prove five-row import,
  order, repeat/concurrent/in-batch dedup and collision handling; reject bad
  provenance, counterfactuals and torn tails; confirm dry-run has zero writes.
  Depends on B1. Gate: targeted Rust importer tests, CLI import/query smoke
  and repo-prescribed Rust checks on omo after resource checks.
- [ ] **B3: Link real evidence.** Feed executed rows into the isolated store and
  link hypotheses/revision; reopen and recompute from receipt IDs. Compare to
  A4 across both laws and verify no unsupported update. Depends on A4/B2.
- [ ] **Checkpoint B:** End-to-end replay from clean checkouts, exact refs and
  run instructions; record CI and bundle states separately.

## C — Organizational identity

- [ ] **C1: Freeze turnover card.** Fix tick order, role update, perturbation,
  recovery horizon, persistent-residence metric and loss controls. Register
  claim, seal before execution; record lineage separately. Depends on A4.
- [ ] **C2: Run feedback versus replay.** Require full component turnover and
  identical passive logs, then test both one-role perturbations, relabelling,
  feedback removal, sham and independent-copy controls. Gate:
  `tests/test_organizational_identity.py` plus prereg replay. Depends on C1.
- [ ] **C3: Transfer evidence loop.** Use target-specific planner and receipt
  from A4/B3 with the same abstention rules. Only then review typed uncertainty
  proposal. Depends on B3/C2. Gate: both discovery transcripts and reopened
  store replay.

## D — Further research cards

- [ ] **D1:** Same-disturbance counterfactuals: exact additive vs sign-flip
  card, matched marginals, paired error/coverage, shuffle and scoring oracle.
  Independent of B/C; preregister before fixture implementation.
- [ ] **D2:** Cost/noise/out-of-model stress tests and adaptive vs fixed/random
  policies. Depends on A4. Require decision and abstention metrics per cell.
- [ ] **D3:** Contact/fold/action-disturbance counterfactuals and horizon sweep.
  Depends on D1 and a preregistered discriminating instrument.
- [ ] **D4:** True delay versus outward sampler on identical crossing tasks.
  Independent. Preserve R-P1.43 historical verdict.
- [ ] **D5:** Composite masks, non-convex/reflex corners, finite-radius
  crossing labels and calibration. Independent. Gate seam/control pair before
  expanding the planner.
- [ ] **D6:** Rotating-observer frames; separately test coordinate invariance
  and physical coverage changes. Independent.
- [ ] **D7:** Partially overlapping producers plus incorrect tags at matched
  marginal delivery. Independent; require matched anonymous and tag-shuffled
  controls before claiming a fusion rule.
