# Active discovery: replay the executed observation

From the repository root, with the locked Python environment:

```sh
out=$(mktemp -d)
.venv/bin/python scripts/active-discovery.py --record "$out/cases"
.venv/bin/python scripts/active-discovery.py --replay "$out/cases/law-1-state-3"
```

`--record` requires a new directory. Each adaptive case saves `plan.json`
before acquisition, `events.jsonl` from the simulator's observable stream
before decision recording, and `decision.json` with exact rational posterior,
plan digest and event-file digest. `--replay` checks the frozen plan and
reprojects the same bytes it hashed, without the simulator or the case name.
Exit `0` is `VERIFIED`, `1` is `ABSTAIN`, and `2` is `REFUSED`. The shuffled
arm remains an in-memory control and is not recorded as observed history.

This protects replay against a swapped reading and matching posterior when the
actual event is retained. It does not authenticate a producer, prevent someone
who controls all files from replacing them, or prove crash/power-loss recovery.
The full discovery command uses law and reset-state labels for fixture scoring
only; replay does not consume them. No Physis-store ingest or replay is implied.

Next B3 slice: assign stable run and observation IDs safe for import, bind
replay to exact store rows rather than path labels, and compare a reopened
store verdict to this local replay. Keep the importer on its own branch.
