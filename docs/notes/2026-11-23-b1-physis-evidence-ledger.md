# B1 — the evidence ledger: two stores, measured (2026-11-23)

Status: **measured**, no importer written. Corrects one assumption in the
[P1 plan](../tasks/plan.md) phase 2 and one in `physis-check`.

## Versions

- `physis` **1.9.1** (physis-next CLI) — observation log, world queries, audit packets.
- `physis-core` **0.3.0** — hypotheses, evidence, transitions, explanations.

## physis-next: observations, readback, verifiable packet

World: a throwaway tree with `src/a.txt`, `src/b.txt` (`/tmp/opencode/b1-world`).

```bash
physis observe /tmp/opencode/b1-world --json      # 10 observations, 2 files
physis observe /tmp/opencode/b1-world --json      # again, and again: still 10
wc -l /tmp/opencode/b1-world/.physis-next/observations.jsonl   # 10
physis subject --path /tmp/opencode/b1-world file:src/a.txt --json
physis packet --path … --out /tmp/opencode/b1-packet --query 'which files were observed'
physis packet-verify /tmp/opencode/b1-packet
```

- **Idempotent**: three `observe` runs leave a 10-row log (`skipped_files: 2` on
  the repeats). Re-running an unchanged tree appends nothing.
- **Readback**: `subject` returns `seq`, `at` (UTC), `body` (`bytes:6 fnv:…`),
  typed `props` (`path`, `bytes`, `fingerprint`), `source: fs`, `superseded_by`.
- **Packet**: `10 observations, sha256 5cd78e09…`; `packet-verify` prints
  `VERIFIED packet: 10 rows parse`. Appending one junk line flips it to
  **exit 1, `FAILED packet: hash mismatch`**. This is the third-party check the
  demo's "traceable explanation" needs, and it already exists — no upstream work.

## There is no hypothesis ledger in physis-next

`physis --help` has no `hypothesis` and no `claim` verb. Competing hypotheses live
in **physis-core**:

```bash
physis-core hypothesis create '<claim>' --confidence 0.6
physis-core hypothesis evidence <uuid> '<measurement>' --polarity supporting --weight 0.9
physis-core hypothesis transition <uuid> Supported --reason '<why>'
physis-core hypothesis explain <uuid>     # status, coherence, fitness, evidence
```

All four worked in this run: status reads back `supported`, the evidence line is
attached, and `explain` shows fitness inputs. So the plan's "Physis maintains the
competing hypotheses" is **two stores, not one**:

| element | store | what it gives |
|---|---|---|
| measured evidence | physis-next observation log + packet | append-only, hash-verified, tamper-fails |
| rivals, support, revision | physis-core hypotheses | named claim, polarity, status, explanation |

Binding them needs one thing: the packet's `sha256` recorded as evidence text on
the hypothesis (or vice versa). That is a receipt, not a new schema.

## Isolation: `PHYSIS_DATA_DIR` is ignored

The first probe set `PHYSIS_DATA_DIR=/tmp/opencode/b1-core`; the directory stayed
empty and the hypothesis was visible **without** the variable. The real lever is
**`PHYSIS_CORE_DIR`**:

```
PHYSIS_CORE_DIR=/tmp/opencode/b1-core3 physis-core hypothesis list   # 1 hypothesis
physis-core hypothesis list                                          # 37 hypotheses
```

Consequence: the probe `61e8b056` is now in the shared `~/.physis` store (append-only;
left in place, named here). And `physis-check` exports `PHYSIS_DATA_DIR` while
claiming isolation — its claim/recall halves are **not** isolated either. Treat any
"isolated" run that did not verify a store path as writing to the shared one.

## What B2 still owes

- The Rust append path (`physis_store::append_observations`) and whether an
  external producer can call it, or whether `observe` is the only writer;
- dedup by stable event key under the store lock (the log's own idempotence
  covers *re-observation of a file*, not *re-import of our events*);
- torn-tail refusal from the write side, and `--branch` scoping for a test world.

None of that is answered by this run, and this run changes no code.
