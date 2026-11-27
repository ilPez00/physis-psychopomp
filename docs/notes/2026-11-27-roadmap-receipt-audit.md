# Roadmap receipt audit — 12 rows assert a verdict with nothing behind it

`scripts/check-roadmap-receipts.py` (2026-11-27) asked every roadmap row the
question A1 had asked of 24: does a row that states a verdict point at an
artefact? Measured at `d7ee729`:

```
roadmap rows: 68  clean: 47  unresolved: 0  unlinked: 0  missing: 12  shipped-surface: 3
```

## What was fixed in this pass

- **12 UNLINKED rows** cited nothing while their receipt existed —
  R-P1.24, 25, 28, 31, 33, 34, 35, 42, 43, 44, 45, 46. Each now carries
  `Receipt \`research/loops/results/<dir>/\``. No verdict changed; the evidence was
  there and the row did not point at it.
- **R-P1.7** now cites `docs/2026-11-26-R-P1.7-ingest-roundtrip.md`. That card's
  gate was met on 2026-11-26, but its receipt lives in this repo's `docs/`, not in
  `research/loops/results/`, so the gate could not see it.

## What is left, and it is a finding rather than a task

Twelve rows state a verdict with **no artefact of any kind** — no
`research/loops/results/` directory, no `docs/` receipt, no run output:

R-P1.1, R-P1.6, R-P1.11, R-P1.13, R-P1.15, R-P1.19, R-P1.23, R-P1.26, R-P1.40,
R-P1.57, R-P1.58, R-P1.59.

They predate the convention "a verdict carries a receipt" and several predate
`research/loops/results/` existing at all. Two honest options, and this note does
not choose:

1. **Reconstruct** — cheap for the ones whose script still runs (R-P1.6's A4
   prereg, R-P1.19's rich-physics cells), expensive for the rest.
2. **Mark them as pre-convention** so the gate can distinguish "no receipt was
   ever made" from "a receipt was lost". That is a schema change to the roadmap
   and needs the operator, because it changes what a row may claim.

Until one is chosen the gate **fails with 12 missing**, which is the correct
behaviour: a gate that passes on its own historical gaps teaches nothing. It is
also why `verify-all` does not yet run it — `scripts/verify-all.py` should include
this check once the count is zero, and that is recorded here so the omission is
not mistaken for an oversight.

## The four conventions the gate learned

Only one is `receipt.json`; the others are a directory with any output, a dated
`docs/*.md`, and a bare repo-relative path. Reading only the first reported 17
missing when 5 were real. A parser that reads one convention and passes is the
failure mode this gate exists to prevent, which is why it exits 2 when it parses
zero rows.
