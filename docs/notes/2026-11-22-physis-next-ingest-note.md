# Note: ingesting `psychopomp.observation/1` (from physis-psychopomp)

Date: 2026-11-22. From the psychopomp (mission P1) side. **This file is the only
thing I added to that tree; I changed nothing else and committed nothing.**

> **State of that checkout, 2026-11-22 18:45.** `~/dev/physis-next` is **not** a
> buildable physis-next tree right now: it is paused in an *interactive rebase*
> ("onto 201fcc373a", **3941 commits remaining**), `crates/` and `apps/` are emptied
> by that operation, there is no workspace `Cargo.toml`, and its single remote is
> `giveaway → github.com/ilPez00/physis-computer.git` (a different repository). So
> nothing here could be branched, built or pushed from that path, and I did not try —
> the rebase has to be resolved by its owner first. This copy is the canonical one;
> the untracked original sits in that tree.

## What psychopomp wants

The P1 instrument produces an append-only, identity-free event export in
`psychopomp.observation/1` (one JSON line per observable event). It wants those
events to land in a Physis world so they can be queried like any other observation.

Producer side is **complete and machine-checked**:

| artefact | where (on this machine) |
|---|---|
| contract: guarantees, obligations, unknowns | `~/dev/physis-psychopomp/docs/INTEGRATION-CONTRACT.md` |
| checker that asserts every guarantee | `~/dev/physis-psychopomp/scripts/export-contract-check.py` (pinned gate #25) |
| sample fixture | `~/dev/physis-psychopomp/research/fixtures/observation-v1.sample.jsonl` |
| producer code | `~/dev/physis-psychopomp/psychopomp/export.py` |

Example record:

```json
{"schema":"psychopomp.observation/1","subject":"episode:0:0","kind":"enter_occ",
 "at":8.7,"props":{"side":"left","v":[3.0,1.5],"pos":[45.8,54.9],"dt":0.1},
 "provenance":{"source":"sim:v0.2","config_sha256":"…","seed":0,"episode":0},
 "evidence":"OBSERVED","seq":1}
```

Guaranteed by the producer (asserted, not promised): exact schema string; canonical
record order with `seq` as the index; identity-free (a relabelling of two identical
bodies exports byte-identically); deterministic; provenance always present;
counterfactual provenance **refused at export**; times in seconds with `dt` carried.

## What blocks it here

Measured on 2026-11-22 with the installed `physis` 1.8.7:

- `physis ingest-sources` lists **12 declared connectors** (usgs, open-meteo, ecb-fx,
  worldbank, sec-edgar, swpc, crossref, gdacs, celestrak, eurostat, openfda, pubmed),
  each with a fixed emit shape, a cadence floor and a byte ceiling;
- `physis ingest <SOURCE> [PATH]` requires `<provider>/<layer>`; `--url` overrides the
  feed URL for mirror selection, not the parser;
- there is **no** generic JSONL ingress and **no** `import` subcommand anywhere in the
  command list.

So the events cannot be ingested today without a change here.

## Two routes (route 2 is the one the contract is written for)

1. **A connector** in the declared registry — fits the existing contract, but the
   registry currently expresses *network feeds* only; it would need a source that
   reads from a file or stdin.
2. **`physis import --schema psychopomp.observation/1 <file>`** — validate the schema
   string, map one record to one observation row, append. Smaller surface, and the
   schema check lands where it belongs.

## What I could **not** establish (please fill in)

I did not get to a measured answer on your own row shape, and I am not going to guess
it:

- the release tree here is at `1.8.7` with `crates/` trimmed to
  `physis-agent`, `physis-cognition`, `physis-kernel`, so the store/CLI writer is not
  in this checkout;
- `physis observe .` in a scratch directory was **refused by the sandbox**
  (`permission.rejected: shell`), so I could not observe the emitted rows either.

Open questions, in the order that matters for the mapping:

1. What is the exact observation row shape (field names, types, required keys)?
2. How are ids namespaced per root, and would `episode:<seed>:<episode>` need a
   prefix?
3. Does the log fold repeated ingestion (dedup / bitemporal supersession), or is
   append-only duplication the consumer's problem?
4. Any unit metadata convention for numeric props — psychopomp emits box units, not
   metres, and says so in `props` only by omission.

## Acceptance test once the importer exists

Against the sample fixture, in a fresh world:

1. every record appears exactly once (`count == lines`);
2. re-importing the same file adds **zero** rows;
3. a query for one `subject` returns its records in `seq` order;
4. importing a counterfactual export is impossible — the producer refuses to emit
   one, so the importer should never see it, and must not synthesise such provenance.

If the answer to (1)–(4) lands in this file or in `docs/`, the contract can be
completed from your side and I will pick up whatever is still missing on mine.
