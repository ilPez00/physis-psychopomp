# P1 execution queue

See [plan](plan.md) for fixed boundaries and proposed numeric fixtures. Tests
and scripts listed below are targets, not commands claimed to exist today.
No step is preregistered until a claim and frozen card are committed.

## A — Local discovery demo

- [ ] **A1: Freeze finite-law card.** Enumerate both law/state tables, balanced
  shuffle and no-signed control; register claim, threshold, and two budgets
  (calibration versus diagnosis). Run `scripts/prereg-checklist.py`; verify
  remote prereg SHA before first run. Depends on plan review.
- [ ] **A2: Exact Bayesian selector.** Implement target-specific scoring and
  abstention in one Python module; unit test `(0,2)`, `(1,0)`, `(0,1)`, `1/3`
  random baseline, shuffled null and candidate-order invariance.
  Depends on A1. Gate: `.venv/bin/python -m pytest -q tests/test_active_design.py`.
- [ ] **A3: Exit-event fixture.** Preregister physical response table. Test
  expected step/position, nominal mismatch, equal rival magnitude likelihood,
  both signed outcomes and no oracle/provenance passthrough. Depends on A1;
  reuse existing `run` and visible log. Gate: `tests/test_active_exit_fixture.py`.
- [ ] **A4: Bounded execute and verify loop.** Reject a second diagnostic action,
  non-allowlisted action and forged receipts. Verify both laws and all reset
  states, losing controls and abstention. Depends on A2/A3. Gate:
  `tests/test_active_discovery.py` and the demo replay in `scripts/research-gates.py`.
- [ ] **Checkpoint A:** Publish local transcript with exact claim, denominators,
  normalized receipts and `scripts/verify-all.py` output. No Physis integration claim.

## B — Real Physis-next evidence

- [ ] **B1: Inspect current store APIs.** Fetch canonical origin to an isolated
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
