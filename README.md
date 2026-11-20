# Psychopomp

A machine for making possible worlds experimentally accountable: persistent,
provenance-bearing world states → temporal reasoning → falsifiable
constraints on learned representations.

Research instrument, not a validated architecture. **Status: v0.1 (CPU
prototype).** Design and pre-registration: `docs/2026-11-20-PREREG.md`.

## Standing evidence (kept on purpose)

A prior JEPA-derived latent in this lineage was falsified at scale:
"toy win was a supervision confound; chance-level on 730 entries under a
shuffled-label control" (`physis-next/docs/quarry/physis-pro/docs/PLAN_11.md`,
Phase 11D, receipt `research/perspective-discovery/THESIS_EVALUATION_JEPA_QWEN.md`).
Psychopomp's shuffled-control arm exists because of that result, and any
positive here must beat that control or it is the same trap again.

## Layout

```
psychopomp/eventlog.py   typed events: kind, t, subjects, attrs, provenance
psychopomp/sim.py        deterministic 1D sim; observable/oracle separation
psychopomp/epec.py       EPEC-inspired possible-world filter (unweighted, own
                         encoding — epec-vanilla is reference only, no
                         LICENSE file in that repo; ask D'Asaro before reuse)
psychopomp/controls.py   structure-preserving shuffled-rule control
docs/2026-11-20-PREREG.md  claims, arms, metrics, failure criteria
REPRO.md                 environment, seeds, commands
```

## Quickstart

```bash
uv venv --python 3.12 .venv
uv pip install -e '.[dev]'
.venv/bin/pytest -q
```

Python script demo (straight pass vs hidden collision):

```python
from psychopomp.sim import SimConfig, Init, run
from psychopomp.epec import summarize

cfg = SimConfig(steps=45)  # single-crossing episodes
straight = run(cfg, seed=0, init=Init(x=(20.0, 80.0), v=(4.0, 4.0)))
swap = run(cfg, seed=0, init=Init(x=(30.0, 70.0), v=(4.0, -4.0)))

summarize(straight.observable_log())   # n_worlds: 1
summarize(swap.observable_log())       # n_worlds: 2 (identity | hidden contact)
summarize(swap.oracle_log())           # evaluation only — never a training input
```

## Leakage rules (short form)

Observable log = what a camera measures, identity-free. Oracle log = labelled
truth, evaluation only. Actions apply only to visible balls, so no hidden
action exists. Splits by episode and physical config, never by neighbouring
frames. Full rules in the pre-registration.

## v0.1 gate

CPU deliverables pass (see pre-registration checklist). GPU phase (three
matched arms, ≥3 seeds, on omo) is **not scheduled** — omo availability is
unconfirmed. Nothing here claims Claim A or Claim B evidence yet.
