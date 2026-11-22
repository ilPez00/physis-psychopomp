# Integration contract — `psychopomp.observation/1` into a Physis world

Status: **producer side complete and machine-checked**; consumer side **absent**
(measured 2026-11-22: `physis ingest` is a closed 12-source connector registry with
per-source parsers and byte ceilings, and there is no generic JSONL ingress or
`import` subcommand). This document is what a consumer needs in order to be written,
and it separates what is guaranteed here from what must still be confirmed there.

Checker: `scripts/export-contract-check.py` (also a pinned gate). Sample:
`research/fixtures/observation-v1.sample.jsonl`.

## The record

One JSON line per observable event:

```json
{"schema": "psychopomp.observation/1",
 "subject": "episode:<seed>:<episode>",
 "kind": "enter_occ",
 "at": 6.7,
 "props": {"side": "left", "v": [3.0, 0.0], "pos": [40.0, 45.0], "dt": 0.1},
 "provenance": {"source": "sim:v0.2", "config_sha256": "…", "seed": 0, "episode": 0},
 "evidence": "OBSERVED",
 "seq": 3}
```

## Guaranteed here (checked by the gate, not by prose)

1. **Schema and version** — `schema` is exactly `psychopomp.observation/1`, so a
   consumer can reject a future version rather than mis-parse it.
2. **Identity-free** — no body labels, no hidden positions, no oracle fields. A
   relabelling of two identical bodies produces a byte-identical export, including
   `seq` (R-P1.39 measured the leak that made this false; it is closed).
3. **Canonical order** — records sorted by `(at, kind, props, subject)`, with `seq`
   renumbered to match. Two runs of the same episode export identically
   (bit-for-bit, no wall-clock, no dict iteration order).
4. **Provenance always present** — `source`, `config_sha256`, `seed`, `episode`.
   A consumer can deduplicate, group and re-run from these alone.
5. **No simulated action becomes history** — counterfactual provenance
   (`counterfactual:*`) is *refused at export*; a caller cannot accidentally write a
   possible world into an observation log.
6. **Times are seconds** — `at = step * dt`, carried explicitly as `dt` in `props`
   so the grid is recoverable.

## What a consumer must do (obligations, not suggestions)

- **Namespace the subject.** `episode:<seed>:<episode>` is stable but not global;
  a store with several producers must prefix it (Physis convention: per-root
  namespacing, as `physis roots` does).
- **Treat `evidence: OBSERVED` as evidence, never as a prediction.** The producer
  emits no `PREDICTED` rows; anything a consumer infers must be labelled by the
  consumer.
- **Append-only.** Re-ingesting the same episode must not duplicate: deduplicate on
  `(subject, seq)` or on the provenance tuple.
- **Keep `props` opaque.** They are event-kind-specific by design; a consumer that
  hardcodes a field list will break on the next kind (the producer has already added
  `marker`, `edge` and `normal`).

## The two implementation routes (for the physis-next owner)

1. **A connector** in the declared registry — fits the existing contract (byte
   ceiling, cadence floor, per-source parser) but needs a source that reads from a
   **file or stdin** rather than a network feed, which the registry does not
   currently express.
2. **An `import` subcommand** — `physis import --schema psychopomp.observation/1
   <file>`: validate the schema string, map each record to one observation row,
   append. Smaller surface, and it makes the schema check the consumer's job (which
   is where it belongs).

Route 2 is the smaller change and the one this contract is written for.

## Where this has been raised with the owner

A note for the physis-next side was written on 2026-11-22 at
`~/dev/physis-next/docs/notes/2026-11-22-psychopomp-observations-ingest.md`
(uncommitted, so it sits in that working tree rather than in their history). It
carries the same four open questions as the list below, plus the acceptance test.

Two attempts to answer them from here are recorded so nobody repeats them: the
release tree at `1.8.7` has `crates/` trimmed to three crates, so the store writer is
not in that checkout; and `physis observe .` in a scratch directory was refused by
the sandbox (`permission.rejected: shell`), so the emitted rows could not be
observed either. Guessing the row shape from the query surface would have been the
same error as quoting a benchmark without a receipt.

## Not established here (do not take these as claims)

- **Physis's own observation row shape.** Not read from its Rust log writer; the
  field names above are the producer's, and the mapping is the consumer's to define.
  `physis subject` / `series` / `values` show the *query* surface, not the writer.
- **Bitemporal semantics.** Physis records corrections and supersession; this
  contract says nothing about how repeated ingestion of a corrected re-run should
  fold, because the producer never revises — it only appends.
- **Units beyond time.** `pos`/`v` are box units, not metres; a consumer treating
  them as physical quantities would be wrong, and no unit metadata is emitted.
- **Cadence and size.** 12 events/second of simulated time at the default grid;
  a day of simulated time is ~1 M rows. The producer does not chunk.

## Acceptance test a consumer should pass

Given the sample fixture, after importing it into a fresh world:

1. every record appears exactly once (`count == lines`);
2. re-importing the same file adds **zero** rows;
3. a query for one `subject` returns its records in `seq` order;
4. importing the export of a *counterfactual* episode fails with a refusal (the
   producer never emits one — the consumer must not fabricate provenance).
