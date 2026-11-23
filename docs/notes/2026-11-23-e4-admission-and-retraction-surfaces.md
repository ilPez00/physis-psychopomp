# E4 surfaces: what a proposal can reach, and what it cannot (2026-11-23)

Measured on `physis` 1.9.1 plus the canonical source at
`997c6416476727da6fa747dfa31ec79ed30e79db`. Three surfaces matter, and only two
of them can be used by a decoder today.

## 1. `declare` — writes, and the fold decides (R-P1.53)

Exit codes measured end to end: **1** refusal (persisted, `+1` row), **3** on a
repeat of the same triple, **2** invalid with no row written, **0** for an
already-observed triple with no duplicate edge. Full transcript in
[admission-probe-20261123](../../research/loops/results/admission-probe-20261123/).

## 2. `claim` — read-only verdicts, no write

```
$ physis claim file:src/a.txt DEFINES document:src/a.txt::1
VERIFIED: 1 edge(s) with this direction and predicate                     rc=0

$ physis claim file:src/a.txt CONTAINS file:src/b.txt
NO_EVIDENCE: no cited CONTAINS edge from the first to the second;
absence is not refutation                                                rc=2

$ physis claim file:src/a.txt DEFINES file:src/ghost.txt
NO_EVIDENCE: unknown endpoint `file:src/ghost.txt`: nothing in the world matches it   rc=2

$ physis claim nope:nothing DEFINES document:src/a.txt::1
NO_EVIDENCE: unknown endpoint `nope:nothing`: nothing in the world matches it        rc=2
```

This is the surface E4 should use: a decoder can check a proposed edge **before**
proposing admission, and `2` ("no evidence") is distinct from `1` ("refuted") —
absence does not refute. **Not reached:** a `1` case, so refutation is documented
by the help text, not measured here.

## 3. Retraction — not available to a host-source producer

The design review claimed a retraction path (preview / authorise against a digest
/ exclude / revoke / `as_of`). What the code and CLI actually show:

- **Tombstones only apply to code sources.** `engine.rs` builds `dead_relations`
  from `removed:rel|…` rows filtered through
  `crate::ingest::is_code_source(&o.source.0)`. A row written by `physis declare`
  carries source `host`, so a hand-written tombstone is **ignored by the fold**.
  That is the "`removed:rel|…` does not correctly retract host relations" defect,
  and the reason is a source filter, not a bug in tombstone parsing.
- **Tombstones are produced by rescanning, not by a command.** `ingest.rs` emits
  them from `pending_observations` when a relation disappears between scans, and
  deliberately withholds them when a scan is incomplete or unparsed.
- **The retraction tools are previews only.** `tms` prints
  `counterfactual — nothing is written`; `whatif` prints what a retraction *would*
  take away; `viewspec` renders claims a retraction moved. No command in this
  binary applies one.

**Consequence for the decoder.** `RETRACT`, `CHANGE_TYPE`, `SET_VALIDITY` and
`RECONCILE_ID` remain unavailable; proposals stay additive (`ADD_EDGE`) plus
`REQUEST_EVIDENCE`. Writing a tombstone with a forged code-source provenance to
smuggle it past the filter would fabricate provenance — explicitly forbidden, and
it would be exactly the class of failure this programme keeps recording.

**Exact unblock condition:** an upstream surface that retracts a host-sourced
relation, or a documented tombstone form that `is_code_source` accepts for host
rows. Until one exists, the plan's E4 stays partial and says so.

## What this changes in the plan

- E4 partial is complete for additions: `declare` for admission, `claim` for a
  read-only check before it.
- Retraction-based operations are **blocked on upstream**, not on effort, and the
  blocker names a specific function and filter so a future reader can check it in
  one command.
