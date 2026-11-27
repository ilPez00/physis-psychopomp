# Addendum — R-P1.64, the "well under any bar" clause

Addendum to `docs/2026-11-26-PREREG-R-P1.64-soft-posterior.md`. Written 2026-11-27
after audit A6 (`physis-next/docs/audits/2026-11-27-a6-rp64-contradiction.md`).

**The original document is not edited.** A frozen prereg is evidence that a claim was
made before the result was known, and rewriting it destroys that. This file records
the correction and points at it; the false clause stays visible where it was
written.

## The clause

`docs/2026-11-26-PREREG-R-P1.64-soft-posterior.md:151`, under
"What this card changes":

> **E6 stays closed.** The remaining gap is that the policy's own proposal quality
> is unchanged at 0.417, **well under any bar that would justify a learner**, and
> the reason is now measured: 10 noisy readings do not resolve three edges out of
> 21.5 candidates, whichever way the posterior is updated.

## Why it is wrong

`0.417` is **above** the only bar in this line of work. R-P1.62 defines it as
`passive_precision + 0.10 = 0.194 + 0.10 = 0.294`
(`scripts/probe-budget-prereg.py:200`; `receipt.json` `bar = 0.29444444444444445`).

```
0.417 > 0.294
```

The clause is numerically false. It is also the clause a later reader takes as
contradicting the receipts, which is what happened: the audit that produced this
addendum exists because that sentence was read against `soft-posterior`'s own
`precision: 0.4166666666666667` and looked like two documents disagreeing.

## What the card actually establishes, and where it says so correctly

The card's own P2 section, nine paragraphs earlier, gives the correct reasoning:

> The difference between 0.361 and 0.417 is draw spread, not the update rule. The
> threshold was written against a single published number and cannot distinguish
> the two decoders. **The soft posterior does not improve accuracy.**

with 24 draws: soft mean `0.453` (sd `0.052`), hard mean `0.438` (sd `0.053`),
ranges `0.333–0.556` for **both**. A decoder that matches its predecessor inside the
draw spread has no headroom, and the passive bar was never the instrument that
decides it — the card says exactly that, and then contradicts itself at line 151.

## Corrected sentence

The claim is unchanged. The justification is replaced with one that is true:

> **E6 stays closed.** The remaining gap is that the policy's own proposal quality
> is unchanged at 0.417: *above* R-P1.62's 0.294 passive bar, so the bar is not what
> closes E6 — the closure rests on soft matching hard inside the 24-draw spread
> (0.453 vs 0.438, sd 0.052 both). The reason is measured: 10 noisy readings do not
> resolve three edges out of 21.5 candidates, whichever way the posterior is
> updated.

That version is both true and **stronger**: it no longer depends on a threshold the
receipts show is passed.

## What this addendum does not change

- **E6's status.** Still closed. Nothing here suggests headroom for a learned arm.
- **R-P1.63's conclusion.** "A price exists at which querying beats silence" stands;
  the soft arm buys fewer queries (`8.00` vs `10.17`) and still beats passive
  (`-1.300` vs `-1.833`).
- **Any measured number.** No receipt was re-read into question; only the sentence
  that summarised them.

## Reproduce the discrepancy

```bash
cd ~/dev/physis-psychopomp
python3 - <<'PY'
import json
pb = json.load(open('research/loops/results/probe-budget-20261126/receipt.json'))
sp = json.load(open('research/loops/results/soft-posterior-20261126/receipt.json'))
print('bar (R-P1.62):      ', pb['bar'])
print('soft precision:     ', sp['hard_control']['precision'])
print('is 0.417 above bar? ', sp['hard_control']['precision'] > pb['bar'])
PY
grep -n "well under any bar" docs/2026-11-26-PREREG-R-P1.64-soft-posterior.md
```

Expected: `True`, and the clause at line 151.

## Ledger note

The claim id for R-P1.64 (`60d8c8af-e65f-4fdf-a482-a659b1077ec2`) is unchanged. This
addendum corrects prose, not a recorded outcome, so it does not amend the ledger
entry — but a reader comparing the card text to the ledger will find line 151 saying
something the ledger's own numbers contradict, and this file is why.
