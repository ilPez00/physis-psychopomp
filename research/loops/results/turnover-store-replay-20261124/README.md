# C3: turnover replay from a real Physis store

Engineering transfer of R-P1.50, not a new preregistered result. The capture
saves a plan before execution and exports only tick 4 for each episode. The
plan fixes the probe and role; the observation does not include the true arm.
The replay uses a fixed prediction table and never runs the simulator.

From Psychopomp's repository root:

```sh
artifact=research/loops/results/turnover-store-replay-20261124
.venv/bin/python scripts/turnover-store-replay.py "$artifact/cases" \
    --store-log "$artifact/store.jsonl"
```

To make a new capture, pass a new directory and omit `--store-log`. Run
`physis --json import psychopomp.observation/1 <capture>/executed.jsonl --path <scratch-world>`
with the importer branch binary, then replay using the scratch world's
`.physis-next/observations.jsonl`.

Measured on omo with `feat/psychopomp-import` at `2773ccbbc` (the smoke-only
commit atop binary source `65e3e02f2`). The first import appended eight rows;
the second appended zero and skipped eight duplicates. A fresh replay process
cited seqs 0–7: four perturbed cases resolved, covering both arms and both
roles; four passive cases abstained. Tests refuse missing, duplicated and
modified observations. No hypothesis transitions were written.

Replay compares the captured payload with the stored row and reports the plan
and row hashes; this does not authenticate the producer. This verifies the one-tick
fixture only, not arbitrary turnover or continuing individual identity.
