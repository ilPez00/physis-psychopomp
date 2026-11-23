# Psychopomp P1: Active Discovery and Organizational Identity

**Status:** planned, not run. [Task checklist](todo.md) is the execution queue.
**Goal:** demonstrate one independently verifiable result: notice a wrong
model, select and run one safe experiment, then revise competing beliefs with
an explanation that can be replayed.

**Architecture:** Psychopomp produces and scores observations. An exact Bayesian
controller ranks a finite catalogue by expected information about a declared
target. Physis-next stores competing hypotheses and their evidence; an independent
verifier checks that the evidence, not a lucky prediction, licensed the update.
Start with a local CLI and a disposable store, not a new service or UI.

**Sources:** [research/design note](../docs/notes/2026-11-23-active-law-identification.md),
[evidence audit](../docs/notes/2026-11-23-p1-evidence-audit.md),
[observation contract](../docs/INTEGRATION-CONTRACT.md),
[historical importer sketch](../docs/notes/2026-11-22-physis-import-patch-plan.md).
The [project roadmap](../docs/ROADMAP.md) tracks prior cards and open axes.

## Guardrails

- Freeze claim UUIDs, fixtures, estimands, controls, tolerances and stop rules
  in Git before any measurement. Exploratory runs, amendments, and original
  falsifications stay separate. A green reproduction gate is not a claim verdict.
- Only Python 3.12 with the existing locked dev environment; no new dependency
  or learner. Claim A (symbolic constraints) stays separate from Claim B (EPEC
  feedback). Existing learner stop rule remains in force.
- Planner sees readout likelihoods, costs and current beliefs, never truth IDs,
  hidden trajectories, scoring-oracle fields, or future readouts. Counterfactuals
  are not observations. One diagnostic action from a local simulator allowlist;
  no arbitrary commands, production stores, devices or external effects.
- Keep the result relative to the law class, sensor and budget. If data are
  absent, outside every candidate's support, or non-discriminating, report why
  and retain the ambiguity. Do not treat abstention as failed prediction.
- Before a push, run the project's gate, record the checked SHA, and report
  hosted CI and bundle verification separately. CI allocation failure is not
  a code result.

## Phase 1: The one-experiment demo

1. **Finite oracle and two information targets.** Start with declared laws
   `y = s + m·a`, `s ∈ {−3,−1,1,3}`, `m ∈ {−1,1}`; independent uniform priors.
   At equal cost, passive `y` at `a=0`, signed `sign(y)` at `a=4`, and magnitude
   `abs(y)` at `a=4` have predicted `(law bits, state bits)` of `(0,2)`, `(1,0)`,
   and `(0,1)` respectively. Check against an independently enumerated response
   table. Compare both target selectors, maximum readout entropy (which ties on
   passive and magnitude), and uniform random selection (expected `1/3` law
   bit). A balanced shuffle of signed readouts preserves marginals and erases
   their association with laws. Removing the signed arm must cause abstention.
2. **Replace table-only execution with a real exit event.** Proposed fixture:
   `dt=0.1`, 24 steps, `n_balls=1`, body at `(50,50+s)` moving at `(5,0)`,
   blocker `(40,60,35,65)`, `o2=None`, `visual_radius=0`, and
   `allow_hidden_init=True`. Transverse acceleration is
   `m·u`, where `u=0` or `2` and nominal `m=0`. Expected first exit is step 21
   at `x=60.5`; semi-implicit integration gives `y−50=s+4.62m` at `u=2`.
   These are analytic targets, not simulator measurements. Precompute the
   expected sensor table independently; freeze six-decimal quantization,
   a `1e-6` analytic comparison tolerance and capacity tests
   for one visible exit with no wall or corner confound. Measure the sanitized
   exit position only; do not infer from scenario metadata.
3. **Separate surprise from diagnosis.** A magnitude calibration at `u=2`
   lies outside nominal support `{1,3}`, but remains equally likely under
   both rivals. Calibration is a separately budgeted observation; only one
   diagnostic action is allowed on a fresh reset. Rank before execution.
   Signed evidence should resolve both true-law arms; wrong/missing readings,
   passive repetition and shuffled controls must not earn a discovery.
   Check a valid but opposite signed reading against the sealed scorer, not
   by pretending its likelihood is zero.
4. **Receipt and verifier.** Store pre-action scores and candidates; catalogue
   and sensor identifiers; selected action and budget; executed observation ID;
   prior, posterior and rationale; and verification verdict. The scorer checks
   source and ordering, independent response table, both true laws and all
   allowed reset states. A tampered action ID, missing observation, wrong phase,
   or counterfactual source must invalidate a discovery. Human-facing output is
   one reproducible transcript, with machine-readable receipt alongside it.

**Checkpoint:** local transcript proves the loop with negative controls; no
claim of integration until Phase 2 links evidence in a real Physis-next store.

## Phase 2: Physis-next round trip

- **Evidence ledger:** exercise current Physis-next hypothesis/evidence/query
  APIs in a throwaway store. Preserve both rivals and tie/out-of-model states;
  record numerical posterior and rationale as a receipt, not by translating
  entropy into arbitrary registry fitness. Read back observation provenance
  and ordered links. Discover actual CLI/MCP contracts at the implementation
  ref before selecting an interface. No automatic acceptance of claims.
- **Observation importer:** separate Rust branch from canonical
  `ilPez00/physis-next:main`; known source-bearing ref
  `997c6416476727da6fa747dfa31ec79ed30e79db`, recheck before use. Never touch
  the existing rebase or push to `physis-computer`. Validate schema, bounds,
  subject/provenance consistency and `OBSERVED` before writing. Assign UTC ingest
  time explicitly and preserve elapsed simulation seconds in the body. Namespace
  subject IDs and deduplicate stable event keys under the store lock, including
  within a batch. Exact repeats skip; same key with different bytes after canonical
  normalization is a conflict, not a new event or silent overwrite.
- **Acceptance:** five-row fixture imports once and queries in order; concurrent
  repeats, duplicate rows in one batch and repeat imports add no duplicates.
  Wrong schema, forged/unapproved sources, counterfactuals, key conflicts and
  torn tails fail without appending. Dry-run never writes; bounded input and
  explicit receipts carry read/append/skip counts. Then replay Phase 1 using
  stored executed evidence and verify the same verdict after re-opening the store.
  If an existing supported ingress already meets these checks, use it and skip
  a new subcommand. The template mapper is not ingestion.

**Checkpoint:** independent replay reads the same evidence and conclusion from
the reopened store. Only then pitch an integrated demo. If the real path is
blocked, label the local-only transcript as such.

## Phase 3: Identity as organization, not inventory

**Second discriminator.** Two role slots start at `(4,4)` and replace their
initial components at ticks 1 and 2, preserving role state and types. Compare
feedback (transfer one unit from higher to lower role when the gap is at least
two) against open-loop replay of nominal transfers. Freeze a matched `+2`
disturbance to either slot after turnover, at tick 3, then observe the next
update and verify residence through tick 6. Predicted: feedback reaches `(5,5)`;
replay stays at `(6,4)` or `(4,6)`. Balance is the invariant set; total is
conserved by internal transfers, not across external perturbation. These are
preregistration candidates, not measured results.

- Compare passive trajectories and inventories before perturbation; require
  100% replacement and an auditable replacement history in both arms. Component
  ID permutation must not change the recovery verdict, and disabling feedback
  without changing the initial inventory must remove recovery. A sham/no-change
  run must stay ambiguous. Use the same rank/execute/receipt loop from Phase 1.
- Report time-to-recovery and sustained residence separately from turnover.
  If two mechanisms tie under the allowed interventions, keep an equivalence
  class. Separately test that independent copies can share organizational type
  without sharing causal lineage. Do not treat this toy as a biological claim
  or as proof of unique individual identity.
- Only after transfer to this second task, propose a minimal typed uncertainty
  record for Physis: target (`law`, `state`, or sensor reliability), support,
  probability weights or unresolved equivalence class, observation protocol,
  horizon, and provenance. Keep predicted information and realized belief
  change separate. Do not add a general uncertainty schema preemptively.

## Phase 4: Counterfactual reconstruction and further R&D

1. **Paired counterfactual failure witness.** Independent of Phase 2. Compare
   `Y(a)=3a+S` with `Y(a)=3a+(−1)^a S` for `a∈{0,1}` and equiprobable
   `S∈{−2,−1,1,2}`. The single-action marginals agree. On alternative actions,
   compare `3a'`, observed residual transfer, and a hidden-`S` scoring oracle.
   Predicted MAE: baseline `1.5` in both; residual correction `0` additive and
   `3` sign-flip; oracle `0`. When the mechanism is not identified, require
   abstention or a set containing both admissible outcomes. Include a
   shuffled-residual control with the same factual marginals. Report paired
   error, candidate-set coverage and abstention separately from marginal R².
   No training, no oracle in the controller, no counterfactual export as history.
2. **Budget and sensor mismatch.** Test a noisy readout, missing readout and a
   third true mechanism outside the candidate set. Compare budget-matched
   adaptive, fixed, random and shuffled policies. Report model recovery at
   equal cost, false declarations, abstentions, and calibration of predicted
   versus realized information; preserve cases where no affordable probe
   separates the laws. Only compare full expected free energy when a separate
   utility tradeoff is introduced; a pure information objective is not full EFE.
3. **Beyond additive reuse.** Preregister analytic versus simulator
   counterfactual error under clean motion, discontinuous contact, folded
   readout and action-dependent disturbance. Vary duration without retuning;
   compare matched factual means and a shuffled residual control. Require
   measurable headroom before considering another learned arm. The paper's
   reported JEPA improvement is external evidence, not our baseline result.
4. **Instrument validity.** For R-P1.43 use same crossings under timestamp-only,
   true forward snapshot, and outward sampling; compare the same off-boundary
   tasks and per-edge signed error. For R-P1.44–45 test abutting blockers against
   their physical union, convex corner and non-convex notch, point-radius
   limit, and crossing metadata before extending the planner. For rotation,
   separate static frame covariance from a physical observer with time-varying
   coverage. For identity channels, extend R-P1.46 to partially overlapping
   coverage, correlated failures and wrong tags at matched marginals.

## Phase 5: Graph repair — decoder proposals, Physis authority

Design: [graph-patch decoder](../docs/notes/2026-11-23-graph-patch-decoder.md).
Psychopomp predicts; a decoder emits typed `psychopomp.graph-patch/1`
proposals; Physis validates and authorises. **A proposal never mutates the graph
because it passed a structural check**, and no prediction is promoted to an
observation because a model is confident.

Order, each step ending in a gate rather than a paragraph:

1. **E0 — verify the boundary claims first.** `declare` must return
   admitted/refused/unverifiable; `removed:rel|…` allegedly fails to retract host
   relations; retraction preview + authorisation digest + `as_of` allegedly exist.
   Gate: a transcript of one probe each, with exact commands and outputs. If any
   claim is wrong, the decoder plan changes **before** code.
2. **E1 — importer (same work as B2).** Versioned JSONL; simulated seconds kept
   distinct from UTC ingest time; dedup under the store lock; torn-tail refusal.
3. **E2 — revision-pinned adapter.** Read-only Physis snapshot → Psychopomp
   state; every proposal names the revision it was computed against.
4. **E3 — symbolic decoder.** Enumerate admissible worlds, diff against the
   pinned snapshot, emit `HYPOTHESIZED` operations plus an explicit `UNKNOWN`.
   No training. Operations limited to `ADD_EDGE`, `RETRACT`, `CHANGE_TYPE`,
   `RECONCILE_ID`, `SET_VALIDITY`, `REQUEST_EVIDENCE`.
5. **E4 — route through Physis**, never around it. Measured
   ([surfaces](../docs/notes/2026-11-23-e4-admission-and-retraction-surfaces.md)):
   `declare` admits and the fold decides (R-P1.53), `claim` gives a read-only
    verdict against the current fold, not an independent truth check. The tested
    tombstone path filtered host-sourced relations through `is_code_source` and
    the tested `tms`/`whatif` paths were previews. No supported host retraction
    path was demonstrated. So proposals are additive
   (`ADD_EDGE`) plus `REQUEST_EVIDENCE`; `RETRACT`/`CHANGE_TYPE`/`SET_VALIDITY`/
   `RECONCILE_ID` stay blocked on upstream. Forging a code-source provenance to
   smuggle a tombstone is forbidden.
6. **E5 — benchmark** a controlled corrupted graph against **no repair**,
   **deterministic constraints alone**, and **shuffled predictions**. Metrics:
   repair precision, recall, false corrections, true-world coverage, downstream
   prediction change, abstention quality. Success is one sentence: recover more
   correct relationships than it invents, and abstain when the evidence cannot
   decide.
7. **E6 — learned edit-ranker only if E3 leaves measured headroom**, under the
   standing learner stop rule (a shuffled control must lose, a deterministic
   baseline must be named first). Energy-guided reconstruction is a later card.

Non-goals: a second graph database; whole-graph reconstruction from a latent
(representations are not invertible); automatic promotion of a confident
prediction; mutating a production world in this milestone.

**Stop rules:** no bundling four research questions under one verdict. Preregister
and finish one card at a time; if controls fail capacity, withhold the claim and
save the failure. Phase 4 earns complexity only if it changes an existing
decision or reveals a failure the current verifier misses.

## Evidence audit and development order

1. **Repair R-P1.55's instrument.** Preserve the first run as a pilot; keep
   the frozen claim and thresholds. Require both observed true edges before
   writing, exactly one matching provisional operation, and declaration driven
   by that operation in a fresh scratch world. Read back the exact edge and tie
   the fold's citation to the appended assertion. Run `ontology-check` with its
   positional path and report it separately from Z1–Z6. The live replay and a
   missing/wrong-proposal negative control are the acceptance checks.
2. **Fix A4 before B3.** The local transcript now seals the selected action
   before acquisition and verifies the executor's own posterior. Next,
   persist the seal separately before acquiring the observable event; reject
   a jointly fabricated reading and matching decision by reprojecting the
   event. Then reopen an isolated Physis store and recompute from exact
   executed evidence IDs. Two hashes in prose do not prove a replay.
3. **Harden B2/E1 on its existing feature branch.** Freeze key and provenance
   validation before tests. Add ordered readback, mixed overlap and same-key
   conflict controls, including concurrent writers. Cold-check the importer
   locally on omo and verify hosted CI separately; provide a verified restore
   artifact or leave its backup gate open.
4. **Research: ask for evidence that can disprove a plausible edit.** E5 should
   start with held-out observations that produce competing worlds, not an edge
   list containing the answer. Compare provenance-aware abstention with
   lane-only, no-repair, deterministic and shuffled controls at matched
   budgets. Stop if the independent evidence cannot separate rivals. Separately
   preregister D1's matched-marginal additive/sign-flip discriminator; no
   learner without measured headroom. No autonomous writer or retraction
   feature while these gates are open.

Formalities: the local gate is the gate — `scripts/verify-all.py` here,
`scripts/ci-local.sh` in Physis-next — because the hosted workflows start zero
steps on an unpaid account and will not be restored. Pin the live CLI in the
local environment, retain raw evidence or its restorable artifact, and keep the
frozen card, pilot, audited replay, local-gate receipt and backup verdicts
separate.

Operator-approved follow-on: [guarded repair writer and offline ranking](../docs/notes/production-repair-rollout.md).
Start with the existing Physis-next store lock; stage the writer before
deployment, and keep the learner outside the authorization boundary.
