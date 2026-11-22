# Psychopomp

A machine for making possible worlds experimentally accountable: persistent,
provenance-bearing world states → temporal reasoning → falsifiable
constraints on learned representations.

Research instrument, not a validated architecture. **Status: v0.3 (CPU
prototype, post-audit, one measured law).** Design:
`docs/2026-11-20-PREREG.md`. Fix/improve plan after the first public audit:
`docs/2026-11-20-FIXES-AND-IMPROVEMENTS.md`. **The law: `docs/LAW.md`.** One-page findings and the falsification record: `docs/FINDINGS-2026-11-22.md`.

Public: https://github.com/ilPez00/physis-psychopomp. License:
**Apache-2.0** (`LICENSE`, third-party attribution in `NOTICE`), adopted
2026-11-21. Public publication was not a reuse grant before that date; the
Apache grant applies from `cca8220` onward.


> **TL;DR.** Research instrument, not a validated architecture: provenance-bearing world
> states → temporal reasoning → falsifiable constraints. Pre-registered claims and failure
> criteria; a public audit found two experimental blockers (vacuous control, non-identifiable
> target) — both confirmed in code and fixed. **The full suite runs in CI on every push**;
> demo reproduces the two-world result. No claim asserted ahead of evidence;
> licensing **Apache-2.0 since 2026-11-21** (`LICENSE`, `NOTICE`); publication before that was not a reuse grant.

## Standing evidence (kept on purpose)

A prior JEPA-derived latent in this lineage was falsified at scale:
"toy win was a supervision confound; chance-level on 730 entries under a
shuffled-label control" (`physis-next/docs/quarry/physis-pro/docs/PLAN_11.md`,
Phase 11D, receipt `research/perspective-discovery/THESIS_EVALUATION_JEPA_QWEN.md`).
The shuffled-control arm exists because of that result, and any positive here
must beat that control or it is the same trap again.

A first public audit (2026-11-20) found two experimental blockers — a vacuous
control and a non-identifiable 1D target. Both were confirmed in code and
fixed; see the fixes plan.

## Layout

```
psychopomp/eventlog.py   typed events: kind, t, subjects, attrs, provenance
psychopomp/sim.py        2D deterministic sim; observable/oracle separation
psychopomp/epec.py       EPEC-inspired possible-world filter (unweighted, own
                         encoding — epec-vanilla is reference only, no
                         LICENSE file in that repo; ask D'Asaro before reuse)
psychopomp/asp.py        clingo/ASP encoding of C1–C5 (unweighted), numeric
                         facts computed in Python, cross-checked against the
                         Python enumeration
psychopomp/controls.py   cross-episode derangement control (preserves counts,
                         kinds, timestamps, corpus marginals; breaks alignment)
scripts/recoverability.py  observable-only well-posedness baseline + EPEC
                         world accounting + control arm
scripts/demo.py          executable quickstart (two canonical worlds)
docs/2026-11-20-PREREG.md  claims, arms, metrics, failure criteria
docs/2026-11-20-FIXES-AND-IMPROVEMENTS.md  audit response, statuses, gates
REPRO.md                 environment, seeds, canonical scenarios
```

## Quickstart

```bash
uv venv --python 3.12 .venv
uv pip install -e '.[dev]'
.venv/bin/pytest -q          # full suite (incl. ASP cross-check)
.venv/bin/python scripts/research-gates.py   # every documented result, pinned
.venv/bin/python scripts/law-conformance.py  # the law vs attribution, random grid
.venv/bin/python scripts/demo.py
.venv/bin/python scripts/recoverability.py
```

Demo (2D, single-crossing episodes):

```python
from psychopomp.sim import SimConfig, Init, run
from psychopomp.epec import summarize

cfg = SimConfig(steps=150)
straight = run(cfg, 0, init=Init(x=(20.0, 20.0), y=(50.0, 80.0),
                                 v=((3.0, 0.0), (3.0, 0.0))))
swap = run(cfg, 0, init=Init(x=(20.0, 52.0), y=(45.0, 20.0),
                             v=((3.0, 1.0), (0.0, 3.3))))

summarize(straight.observable_log())  # 1 world, no contact required
summarize(swap.observable_log())      # 2 worlds, ALL require a hidden contact
swap.oracle_log()                     # evaluation only, never a training input
```

What the two-world result means: off-axis contacts make a hidden contact
*detectable* (no contact-free world survives), while the identity pairing
(which ball exited where) stays ambiguous from event calculus alone. Truth is
always among the worlds; ranking it higher is the pre-registered JEPA task,
and an oracle-free reference (restart from the observed frame-0 state) solves
it on the CPU baseline — `scripts/recoverability.py` prints all of it.

## Leakage rules (short form)

Observable log = what a camera measures, identity-free. Oracle log = labelled
truth, evaluation only. Actions apply only to visible balls, so no hidden
action exists. Splits by episode and physical config, never by neighbouring
frames. Full rules in the pre-registration.

## The law (v0.3)

Identifiability of an intervention is **per-event observer coverage**:
the intervention is identifiable iff its event location at the event step is
outside the blind region `o ∩ o2(t)`, with the observer held fixed across
counterfactuals. Measured across place (30/30 out of sample), time (11/11, both
flips), frame (30/30 covariant, bodies-only control flips 5 of 22), noise
(100/100 to σ = 6, breakpoint σ\* = 15), rich physics (gravity, a hidden
in-blind collision, three-collision episodes) and the observer's own self-model
(a wrong model loses 3 of 4 task events). Honest ratio: two supported claims,
two contradicted, seven falsified predictions kept on the record. Statement,
envelope and falsification log: `docs/LAW.md`; code: `psychopomp/law.py`.

## v0.2 gate

CPU deliverables pass; the audit's pre-GPU demands are covered by
`scripts/recoverability.py`. GPU phase (three matched arms, ≥3 seeds, on omo)
is **not scheduled** — omo availability unconfirmed. Nothing here claims
Claim A or Claim B evidence yet.

## Commit + push to air's USB storage — always

Work in this repo is not saved until it is in **three** places, not two: a
commit on the local branch, that commit on `origin` (GitHub `ilPez00`), **and a
`git bundle` on air's USB stick** (`/dev/sdb1`, 29.8 G exfat, mounted on air at
`/mnt/sdb1`). The stick is the off-machine copy that survives a dead node and a
dead NAS; `origin` alone is not enough.

`fleet-sync` does this — run it at the end of any session that touched files,
and after any multi-file edit wave:

```bash
fleet-sync            # commit + push + bundle to the NAS and to air's stick
```

When the stick is mounted on air, the bundle is pushed there by the same run
(tier `air-usb`). When it is not mounted, that tier is **skipped with a log
line — never faked, never filled onto `/` instead**. Do not substitute a tarball
of the working tree: the portable, restorable, verifiable artifact is
`git bundle create <repo>.bundle --all`, and `git clone <repo>.bundle` must
restore it.

Details and the rest of the storage tiers: `~/.config/agents/SYNC.md`.


## Verified 2026-11-21

Fresh public checkout/release, run on a clean host (pansa, 12-core Linux):

- `uv venv` + `uv pip install -e ".[dev]"` + `pytest -q`: **75 passed** (README previously said 28 — stale).
- `scripts/demo.py`: PASS — straight world=1/no contact; off-axis world=2, hidden contact required.

Method + full logs: portfolio audit verification log (private hub); reproduction commands in this README.
