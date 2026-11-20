# Psychopomp

A machine for making possible worlds experimentally accountable: persistent,
provenance-bearing world states → temporal reasoning → falsifiable
constraints on learned representations.

Research instrument, not a validated architecture. **Status: v0.2 (CPU
prototype, post-audit).** Design: `docs/2026-11-20-PREREG.md`. Fix/improve
plan after the first public audit: `docs/2026-11-20-FIXES-AND-IMPROVEMENTS.md`.

Public: https://github.com/ilPez00/physis-psychopomp. No LICENSE file yet —
public publication is not a reuse grant; licensing is a deliberate operator
decision, deferred.

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
psychopomp/controls.py   cross-episode derangement control (preserves counts,
                         kinds, timestamps, corpus marginals; breaks alignment)
scripts/recoverability.py  observable-only well-posedness baseline + EPEC
                         world accounting + control arm
docs/2026-11-20-PREREG.md  claims, arms, metrics, failure criteria
docs/2026-11-20-FIXES-AND-IMPROVEMENTS.md  audit response, statuses, gates
REPRO.md                 environment, seeds, canonical scenarios
```

## Quickstart

```bash
uv venv --python 3.12 .venv
uv pip install -e '.[dev]'
.venv/bin/pytest -q
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

## v0.2 gate

CPU deliverables pass; the audit's pre-GPU demands are covered by
`scripts/recoverability.py`. GPU phase (three matched arms, ≥3 seeds, on omo)
is **not scheduled** — omo availability unconfirmed. Nothing here claims
Claim A or Claim B evidence yet.
