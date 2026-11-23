# Active discovery: replay the executed observation

From the repository root, with the locked Python environment:

```sh
out=$(mktemp -d)
.venv/bin/python scripts/active-discovery.py --record "$out/cases"
.venv/bin/python scripts/active-discovery.py --replay "$out/cases/law-1-state-3"
```

`--record` requires a new directory. Each adaptive case saves `plan.json`
before acquisition, `events.jsonl` from the simulator's observable stream
before decision recording, and `decision.json` with exact rational posterior,
plan digest and event-file digest. `--replay` checks the frozen plan and
reprojects the same bytes it hashed, without the simulator or the case name.
Exit `0` is `VERIFIED`, `1` is `ABSTAIN`, and `2` is `REFUSED`. The shuffled
arm remains an in-memory control and is not recorded as observed history.

This protects replay against a swapped reading and matching posterior when the
actual event is retained. It does not authenticate a producer, prevent someone
who controls all files from replacing them, or prove crash/power-loss recovery.
The full discovery command uses law and reset-state labels for fixture scoring
only; replay does not consume them. No Physis-store ingest or replay is implied.

## B3: replay from imported evidence

New captures seal the episode number before execution. It is recorded by
the simulator, not relabelled by the exporter. One invocation allocates a
random block of eight episode numbers; repeated exports of the same capture
keep the same keys. This is not a global namespace for arbitrary producers.

```sh
.venv/bin/python scripts/active-discovery.py --export "$out/cases" > "$out/executed.jsonl"
mkdir "$out/world"
# Set PHYSIS_BIN to a binary built from the importer branch.
"$PHYSIS_BIN" --json import psychopomp.observation/1 "$out/executed.jsonl" --path "$out/world"
.venv/bin/python scripts/active-discovery.py --replay "$out/cases/law-1-state-3" \
  --store-log "$out/world/.physis-next/observations.jsonl"
```

The verifier requires one exact producer key and compares its stored
provenance, observation payload and simulation time with the captured event.
It projects the stored payload and reports the store's own sequence number.
It reads the raw observation log because the importer branch's `subject`
view omits `produced_by`. Older captures still replay locally but cannot be
exported without a sealed episode.

Measured on omo: fresh default-feature `physis-cli` binary from
`feat/psychopomp-import` at `62c3a18a0`. Fresh scratch world: eight appended,
zero appended and eight skipped on repeat, eight independent processes
verified against store seqs 0–7. The export SHA-256 was
`690fd735f4064389b3558e258d6cfab325d21ebb16417783a2b13aaee904441e`;
the reopened log SHA-256 was
`750fd1058916bf6837117b816c7f64dded91b09f3c14a5368aa919cc382aa834`.
The [captured cases, export and store log](../../research/loops/results/active-store-replay-20261123/)
are committed together. Replay them with `--store-log` without an importer
or a simulator.
This is an engineering check, not a new research card or a general importer
correctness claim.

## Propose belief revisions without writing

Pass `--rivals "$negative_id" "$positive_id"` with `--replay` and
`--store-log`. Use two distinct, case-scoped hypothesis UUIDs, in law order
`-1`, `+1`. The proposal cites the exact producer key, store sequence,
canonical store row hash, and sealed plan hash. It recomputes the resolved law
from the stored reading and proposes `Supported` for one rival and
`Contradicted` for the other. A refusal produces no revision.

`PROPOSED` is not a persisted revision or an authorization. The caller must
verify the UUID-to-law assignments in the target ledger. Shuffled decisions
remain controls, not history. Importer hardening stays on its own branch.

## Applied and reopened

Rivals `40f8a80e` (negative law) and `3fc720f1` (positive law) were created in
the programme ledger, because a `physis-core` write is refused under an
env-prefixed `PHYSIS_CORE_DIR` in this harness while reads are allowed. The
proposal for `law-1-state-3` was produced first and is recorded verbatim in
[`belief-revision.json`](../../research/loops/results/active-store-replay-20261123/belief-revision.json),
then applied: supporting evidence to the negative rival, contradicting evidence
to the positive one, both citing producer key
`psychopomp:episode:0:1159617891002457984#0`, store seq **7**, row sha256
`d61732c8…` and plan sha256 `611de9f4…`.

Reopened in fresh processes:

| check | result |
|---|---|
| `hypothesis explain 40f8a80e` | `supported`, SUPPORTING EVIDENCE (1), conf 0.90 |
| `hypothesis explain 3fc720f1` | `contradicted`, CONTRADICTING EVIDENCE (1), conf 0.90 |
| `replay --subject 40f8a80e --at 17:11:00Z` | *known but had no recorded belief* |
| `replay --subject 40f8a80e --at 17:12:30Z` | `Belief … Supported` |

So the revision is a **temporal record**, not a mutable status: the ledger
distinguishes before from after, and both rivals carry the same cited evidence
with opposite polarity.

What this does not establish: that the UUID-to-law assignment is correct (the
caller asserts it and the ledger cannot check it), that the store row is
authentic beyond exact key/payload/digest matching, that the proposal was
written before the transition (one session; the ordering is this receipt), or
that any of it transfers to the turnover pair — a different fixture, untested.
