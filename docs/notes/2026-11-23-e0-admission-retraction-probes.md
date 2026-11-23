# E0 — admission and retraction probes (2026-11-23)

Scratch world `/tmp/opencode/e0-world` (two text files), `physis` 1.9.1.
Purpose: confirm the boundary the graph-repair phase depends on **before**
writing a decoder. Verbatim outputs; nothing here is inferred.

## 1. `declare` verdicts — CONFIRMED, with one sharp edge

Documented exit codes: `0 admitted, 1 refusal, 2 invalid input (nothing written),
3 recorded but neither edge nor refusal (UNVERIFIABLE)`.

```
$ physis declare file:src/a.txt contains file:src/b.txt
REFUSED: rel|CONTAINS|file:src/a.txt|file:src/b.txt at seq 10
- lane refusal: CONTAINS has no measured lane for file -> file
the declaration stays in the log at seq 10 — a refusal is a record, not a deletion
```

Then the **same triple, one row later**:

```
UNVERIFIABLE: rel|CONTAINS|file:src/a.txt|file:src/b.txt recorded at seq 12,
but the fold shows neither an edge nor a named refusal citing it      (rc=3)
```

- unknown predicate → `INVALID: unknown predicate: frobnicates (not in the
  measured vocabulary)`, **rc=2**, nothing written;
- unobserved target (`file:src/ghost.txt`) → **rc=3 UNVERIFIABLE**, not a refusal.

**Consequence for the decoder:** re-proposing a refused relation does not return
the same answer — the refusal names the row that earned it, so a *repeat* lands as
`UNVERIFIABLE`. A repair loop that retries until `admitted` will spin, and one
that treats `3` as `1` will report a refusal that the fold did not make. Treat
`3` as its own outcome, and never re-propose a triple already refused at a known
seq.

## 2. `tms` — CONFIRMED counterfactual, nothing written

```
$ physis tms 10..13
tms: retracting seqs 10..13 affects 0 derived edges — 0 lost, 0 weakened,
0 now asserted directly, 0 unchanged (counterfactual — nothing written)   (rc=0)
```

The observation log held **14 rows before and 14 rows after**. So the retraction
*analysis* is read-only, as the design review claimed. A decoder can therefore
preview its own proposal's consequences without a copy of the world.

## 3. `as-of` — NOT VERIFIED

```
$ physis as-of --until-seq 9  'what files exist' .
$ physis as-of --until-seq 13 'list entities' .
no results at that sequence
```

The command exists and exits 0, but returned no rows at seq 13 even though the log
holds 14. Most likely the question form does not match the structural matcher
rather than the cut being wrong — **not measured either way**. Do not build on
`as-of` until a query shape that returns known rows is found.

## 4. `removed:rel|…` retraction defect — NOT ATTEMPTED

The claim is that `removed:rel|…` rows do not correctly retract host relations in
the fold, while a separate retraction path does. I did not find the row syntax in
the CLI surface, so this stays **unverified**; `tms`-based preview and `declare`
are enough to start the symbolic decoder, and the defect only matters when
proposals *remove* an edge.

## Net for the plan

- E1/E2/E3 (importer, adapter, symbolic decoder that **adds** proposals) are
  unblocked by what is verified here.
- E4 (routing retractions) must wait for §3 and §4, or be limited to
  `ADD_EDGE` + `REQUEST_EVIDENCE` until they are measured.
- The `1 → 3` flip on a repeated refusal is a decoder design constraint, not a
  footnote.
