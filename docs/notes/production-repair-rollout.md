# Guarded graph repair and read-only ranking

## Capability map

| Capability | Owner | Depends on |
|---|---|---|
| `repair-write` | Physis-next: validate and apply one approved addition | Existing observation store and graph fold; independent evidence |
| `repair-eval` | Psychopomp: build held-out cases and measure headroom | Frozen observations, independent labels and deterministic controls |
| `repair-rank` | Psychopomp: rank proposals or abstain | Passing `repair-eval`; no dependency on write access |

Build writer guard first. The evaluation can proceed without a production
writer; the writer must not depend on learner output.

## Writer: staging first

1. **Pin the observation state.** Digest the ordered canonical observations,
   not just row count or last seq. Test under Physis's existing observation lock:
   same-length changes, stale state, duplicate/concurrent attempts and torn
   tails cannot change the log. This is a prefix precondition, not by itself a
   graph revision or approval.
2. **Read-only preview.** Accept one typed `ADD_EDGE`. Resolve the canonical
   store and branch from trusted operator input, not a proposal. Pin the
   observation state and any other fold inputs used to make the decision. Reuse
   canonical fold validation; if mutable inputs cannot be pinned and checked
   together, restrict staging to a fixture with fixed inputs and refuse release.
   Preview cites exact pre-existing evidence and its producer. Self-citations,
   earlier repair assertions and model output are never independent evidence.
   Start with one evidence adapter and one predicate; if no defensible pair
   exists, stop before adding an apply command.
3. **Operator approval and apply.** Explicit invocation under a distinct local
   operator identity with write access to an allowlisted world; no agent or
   learner credential, no HTTP/MCP endpoint. An approval binds the exact
   canonical world/branch, revision, edge, evidence identities and operation
   version. A digest identifies the approval payload; knowing it is **not**
   authorization. Check binding, current state, evidence and prior use under
   the same lock as the single append. Store attribution and approval identity
   on the assertion. Refuse stale or changed inputs, repeat/wrong-world
   approvals, unsupported lanes and malformed evidence without adding rows.
4. **Cold staging acceptance.** Run two concurrent applies (one append), try
   wrong world/evidence and R-P1.55's false edge (no append), simulate a torn
   tail, and reopen the same store with a fresh process. Match the exact edge
   and audit seq. A lost response means inspect by approval identity, not
   blind retry. Keep `declare`'s existing operator semantics unchanged.
5. **Release gate.** Require separate operator approval of the target and
   permission separation, exact-head verification, a restorable backup, and
   a demonstrated containment/correction path. No claim of retraction until
   measured. Until then no live-world writes, deployment or permission grants.

## Learner: headroom before training

1. Preregister cases, split by independent world/lineage before feature
   extraction, and freeze scoring and stop thresholds. Generate candidates
   from partial observations. Keep hidden labels for scoring only and keep
   counterfactuals out of observed history.
2. Use the same cases, candidates and observation budgets for no-repair,
   deterministic evidence rules and a label-shuffled control. Report correct
   recoveries, false corrections, abstentions and downstream prediction error
   per held-out world. Show where the deterministic baseline leaves recoverable
   cases; stop if observations cannot distinguish the rivals.
3. Only with measured headroom, trial a small offline ranker against the
   frozen baseline and shuffle. Promote to read-only shadow mode only if it
   improves held-out correct recoveries without increasing false corrections,
   under preregistered thresholds. Output is order, confidence and abstention,
   never an approval, assertion or tool call.

No new graph store, network write service, learner-controlled execution,
retraction, or broad ontology change in this rollout. Importer hardening and
durable A4/B3 evidence binding remain separate prerequisites wherever this
writer or benchmark consumes those evidence sources.

## First implementation slice

[Physis-next draft PR #315](https://github.com/ilPez00/physis-next/pull/315),
branch `feat/guarded-repair-writer`, commit `1da2aefeab`, contains
the staging plan and a shared append fix. Both single and batched writes refuse
a missing final newline, even when the final JSON parses. Read failures other
than a missing log abort before the condition callback. A test shows that the
existing lock callback can compare exact rows and refuse a same-length change.
This slice does not add an approval payload or apply command.

Canonical Physis-next's append-only `Runtime::retract` and `Runtime::revoke`
are separate from the historical `removed:rel|…` test. At writer-branch
`b17a83045c`, a fresh-world runtime test retracts the exact `host` assertion
behind the R-P1.55 false edge. On reopen, the edge disappears; revoking the
retraction restores it. The original byte prefix and both history rows stay
intact. `cargo test --locked -j 2 -p physis-runtime --test retraction_revoke`
passed six tests. This validates runtime recovery for the fixture, not
production recovery permissions or the future writer's approval transaction.
