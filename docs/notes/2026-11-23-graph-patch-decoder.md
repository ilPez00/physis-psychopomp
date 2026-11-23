# Graph repair: Psychopomp as a proposal engine for a Physis graph

**Status: proposed, not implemented, not measured.** This is the design that
Phase 5 of the [P1 plan](../tasks/plan.md) implements. Nothing here claims a
capability exists.

## The boundary

Psychopomp **predicts** what the graph should contain; a decoder turns those
predictions into **typed proposals**; Physis **validates and authorises**. The
decoder never rewrites authoritative observations, and no structural check ever
promotes a prediction to fact.

Three distinguishable contents, never conflated:

| layer | meaning | authority |
|---|---|---|
| **observed** | what actually entered the system | source evidence |
| **derived** | what follows under known rules | Physis verifier |
| **hypothesized** | what Psychopomp predicts might hold | explicitly provisional |

A high confidence score is a model output, not proof. `HYPOTHESIZED` becomes
`derived` only through Physis's own verification.

## Proposal schema (illustrative, not an API)

```json
{"schema": "psychopomp.graph-patch/1",
 "base_revision": "sha256:…",
 "operations": [
   {"op": "propose_edge", "source": "entity:A", "predicate": "MOVED_TO",
    "target": "location:B", "status": "HYPOTHESIZED", "confidence": 0.83,
    "evidence_seqs": [41, 45, 49]},
   {"op": "retract_support", "observation_seqs": [32],
    "reason": "contradicted by newer evidence", "requires_authorization": true}
 ],
 "verifier": {"status": "NOT_EVALUATED"}}
```

Operations to support, in this order: `ADD_EDGE`, `RETRACT`, `CHANGE_TYPE`,
`RECONCILE_ID`, `SET_VALIDITY`, `REQUEST_EVIDENCE`. `REQUEST_EVIDENCE` is the
existing one-probe loop pointed at a graph — the experiment picker already
implemented for R-P1.47/48, not a new mechanism.

## What is verified, what is only claimed

Measured on this host (B1, `physis` 1.9.1 / `physis-core` 0.3.0):

- observation log, `subject` readback, `packet` + `packet-verify` (a single
  appended junk line fails the packet with `hash mismatch`);
- `observe` is idempotent on an unchanged tree;
- **no hypothesis ledger in physis-next** — rivals live in physis-core
  (`PHYSIS_CORE_DIR`, not `PHYSIS_DATA_DIR`, is the isolation lever).

Carried in from the design review and **not yet verified here** — each is a
probe to run before the decoder depends on it:

1. relation `declare` returns admitted / refused / unverifiable;
2. `removed:rel|…` does **not** correctly retract host relations in the fold;
3. a separate retraction path exists: preview consequences, authorise against a
   digest, exclude retracted evidence from reconstruction, revoke without
   deleting history, reconstruct `as_of` a past state.

If (3) holds, the decoder is a **client** of existing truth maintenance and no
new truth-maintenance code is written. If (1)–(3) behave differently from this
description, the plan changes before any decoder work starts.

## Implementation order

1. **Importer first (B2).** Versioned `psychopomp.observation/1` JSONL with
   simulation seconds kept distinct from Physis's UTC ingest time — the existing
   sketch risks reading simulated seconds as Unix time. Nothing downstream is
   safe while that is ambiguous.
2. **Read-only, revision-pinned adapter.** Physis snapshot → Psychopomp state,
   pinned to a revision so a proposal names the graph it was computed against.
3. **Symbolic decoder (A).** Enumerate Psychopomp's admissible worlds, diff each
   against the pinned snapshot, emit the differences as `HYPOTHESIZED`
   operations. **No training.** Includes an explicit `UNKNOWN` outcome when the
   admissible set does not determine an answer.
4. **Route proposals through Physis**, never around it: `whatif`, ontology
   admission, retraction preview, authorisation digest. A proposal that passes
   structural checks still does not mutate the graph.
5. **Benchmark** against three controls: no repair, deterministic constraints
   alone, and shuffled predictions. Metrics: repair precision, recall, false
   corrections, true-world coverage, downstream prediction change, and
   abstention quality.
6. **Learned edit-ranker (B) only if (3) leaves measurable headroom**, with the
   same stop rule that closed the earlier learner line: a shuffled control must
   be beaten, and a deterministic baseline must be named first. Energy-guided
   reconstruction (C) is a later card, not this plan.

First success criterion, one sentence: on a controlled corrupted graph, does it
recover more correct relationships than it invents, and does it abstain when the
evidence cannot decide?

## Why the first demo is the occluded object

Two candidate worlds survive behind an obstruction; the identities cannot be
told apart. The decoder emits two competing completions, promotes neither, and
`REQUEST_EVIDENCE` names the one observation that would separate them. That is
the R-P1.48 loop with a graph on the other end, so the demo tests the boundary
rather than a new model.

## Non-goals

No second graph database. No generative whole-graph reconstruction from a latent
(representations are not invertible). No automatic promotion of a confident
prediction. No mutation of a production world in the first milestone.
