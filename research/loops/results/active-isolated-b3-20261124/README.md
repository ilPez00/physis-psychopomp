# B3 acceptance — isolated replay and rival revision, 2026-11-24

Ran from a clean Psychopomp checkout at `7d72b415ad53ba3d670e1c6572e6dc8343a4b64b`.
Input is the [committed capture and real store log](../active-store-replay-20261123/),
imported in the earlier run with Physis-next `62c3a18a0`. This run reopened
those exact bytes. It did not invoke the simulator or re-import observations.
The [receipt](receipt.json) pins both input hashes and the `physis-core` binary.

- **Replay:** all eight capture cases verified and returned distinct store
  seqs `0–7`.
- **Bindings:** registered four distinct rivals in an initially empty
  `PHYSIS_CORE_DIR`. Fresh `hypothesis explain` calls checked that each UUID's
  claim text named the correct case and law before using the pair.
- **Application:** seq `7` resolved `−1`, seq `3` resolved `+1`. Each produced
  one `Supported` and one `Contradicted` transition. Both rivals in a pair
  cited the same producer key, exact seq, canonical row hash and sealed plan
  hash with opposite evidence polarity. Fresh processes read back all four.
- **History:** each rival had no belief before registration, was `Candidate`
  before application, and had the expected verdict after application. An
  initial check incorrectly expected no belief after registration. It failed
  on `Candidate`; the final run checked both time boundaries separately.
- **Unsupported control:** withhold the matching row in a scratch copy of the
  log. Both cases refused before and after application (exit `2`, no proposal).
  Every scratch ledger file was byte-identical across each of the four probes.
  This tests absence of supporting evidence, not an out-of-catalogue readout.

Reproduce from this receipt directory, with `physis-core` 0.3.0 on `PATH`:

```sh
uv sync --project "$CLEAN_CHECKOUT" --locked --extra dev --python 3.12
"$CLEAN_CHECKOUT/.venv/bin/python" replay.py "$CLEAN_CHECKOUT" > rerun.json
```

`CLEAN_CHECKOUT` must be an absolute path at the pinned ref. The runner checks
it is clean and uses a new scratch ledger; UUIDs and timestamps differ on rerun.
This is an operator-side acceptance harness, not a product writer. Sequential
evidence and transition calls are not atomic, and the fixture does not establish
producer authenticity or any permission to change a shared store.
