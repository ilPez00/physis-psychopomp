# R-P1.55 audited replay

[Frozen card](../../../../docs/2026-11-23-PREREG-R-P1.55-laned-but-false.md)
at `bc950c77d5b2b79f9ca073972e318b923e97949b`. The [pilot](pilot.md) is
retained. This replay fixes measurement and execution wiring, not the
predictions, candidate, fixture or thresholds. It is not a blinded replication.

Run `.venv/bin/python scripts/laned-but-false.py` with `physis` 1.9.1.
The [transcript](replay.txt) records Z1–Z6 and the [raw store log](observations.jsonl)
allows independent readback. To reopen it, copy it to
`.physis-next/observations.jsonl` in a new scratch directory. Run
`physis claim --path "$scratch" --json file:src/b.txt DEFINES document:src/a.txt::1`.
Use the first ten rows in a separate scratch world to reproduce `NO_EVIDENCE`.

Both true edges existed before declaration. `declare` admitted the one
provisional edge; `claim` then cited precisely the new `host` row at seq 10.
The original true edge remained. `ontology-check . --json` reported zero
structural violations both times (exploratory, not a frozen prediction).
Controls replacing the decoder output with zero proposals or one different
proposal both stopped before `declare`.

**Meaning:** for this lane, `VERIFIED` is a verdict about evidence in the
fold. The evidence here is the assertion itself, not independent confirmation
from the files. The decoder was fed the candidate; this is not a test of
discovering or ranking repairs. No live or production writer was enabled.
