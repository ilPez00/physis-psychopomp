# W2 — digest-bound receipt and independent verifier (free-pi-cli)

**Model: GLM 5.3 Flash (`z-ai/glm-5.3-flash`). Thinking: high.**
Paste the footer line showing `<model> • high` in your report.

Repo: `/home/gio/dev/physis-psychopomp` (branch `fix/p1-evidence-audit`).
Read `docs/2026-11-23-PREREG-R-P1.48-active-exit-fixture.md` first. This brief
must stand alone: W1 may not exist yet.

## Goal

Make a decision about this fixture **checkable by someone who did not run it**.
A receipt binds the committed plan to the evidence by digest; a verifier
recomputes the posterior from the frozen table and refuses anything that does not
bind. The verifier must not import the session/controller module.

## Files you may touch

- create `psychopomp/active_receipt.py`
- create `tests/test_active_receipt.py`

Nothing else. No edits to `active_exit.py`, `active_design.py`, scripts, docs,
`pyproject.toml`, `uv.lock`. No new dependency.

## API (exact)

```python
def commit(*, policy: str, selected: str, prior: tuple[Fraction, Fraction],
           predictions: dict[int, tuple[Fraction, Fraction]]) -> dict: ...
# -> {"plan": {...all four inputs...}, "plan_sha256": <hex>}

def decide(plan: dict, reading: int | None) -> dict: ...
# -> {"plan_sha256": ..., "reading": ..., "posterior": (Fraction, Fraction),
#     "resolved": int | None}

def verify(plan: dict, reading: int | None, decision: dict) -> dict: ...
# -> {"verdict": "VERIFIED" | "ABSTAIN" | "REFUSED", "reason": str}
```

Rules:

- Digest = SHA-256 of `json.dumps(record, sort_keys=True, separators=(",", ":"))`
  over the record with its own `*_sha256` key **absent**; expose
  `digest(record) -> str`.
- `decide` looks the reading up in `plan["predictions"]`; missing key or
  `reading is None` → prior returned, `resolved is None`.
- `resolved` is the law whose posterior is exactly 1, else `None`.
- `verify` returns `REFUSED` when: `plan_sha256` does not match the plan; the
  decision's `plan_sha256` differs from the plan's; the decision is not the
  recomputation of `(plan, reading)`. Returns `ABSTAIN` when the decision is
  honest but unresolved. `VERIFIED` only when honest and `resolved` is set.
- No exception escaping for malformed input: `verify` answers `REFUSED` with a
  reason. `commit`/`decide` may raise `ValueError` on wrong types.

Fill `predictions` from the frozen table via
`psychopomp.active_design.posterior(psychopomp.active_exit.rows("signed"), y)`
for each attainable `y`, converted to a `(Fraction, Fraction)` tuple. That import
is allowed; importing `active_loop` is not.

## Tests (exact expectations)

`tests/test_active_receipt.py`:

1. `test_honest_decision_verifies` — for all 8 rival cells, commit → decide →
   verify returns `VERIFIED` and `resolved` equals the law.
2. `test_tampered_reading_refused` — change the evidenced reading by ±1: `REFUSED`.
3. `test_swapped_plan_refused` — verify a plan against a decision made from a
   different plan: `REFUSED`.
4. `test_missing_evidence_abstains` — `reading is None`, honest decision:
   `ABSTAIN`, posterior is the prior, `resolved is None`.
5. `test_forged_resolution_refused` — a decision claiming a resolution that the
   reading does not support: `REFUSED`.
6. `test_digest_is_stable_and_key_free` — same record in a different dict order
   gives the same digest; adding the `*_sha256` key to a record does not change it.

Write the failing tests first. If an expectation is wrong, stop and report it;
never edit the expectation to fit the implementation.

## Gate

```
cd /home/gio/dev/physis-psychopomp && .venv/bin/python -m pytest -q tests/test_active_receipt.py
```

Then `.venv/bin/python scripts/verify-all.py` must still print
`verify-all: PASS (9 steps)`.

## Forbidden

`git add/commit/push`, branch changes, dependency installs, network calls,
editing files outside the list, changing existing tests, importing the session
module in the verifier.

## Report

Files created; gate's last two lines verbatim; model/thinking footer line; what
you could not do. If the model or thinking level is unavailable, stop and report
`BLOCKED(model)` — do not substitute another model.
