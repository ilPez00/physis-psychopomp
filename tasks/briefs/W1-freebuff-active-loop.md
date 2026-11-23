# W1 — bounded diagnostic loop (freebuff)

**Model: DeepSeek V4.1 Flash, NOT the fast-mode variant. Thinking: high.**
Paste the footer line showing `<model> • high` in your report.

Repo: `/home/gio/dev/physis-psychopomp` (branch `fix/p1-evidence-audit`).
Read `tasks/plan.md` phase 1 item 4 and `docs/2026-11-23-PREREG-R-P1.48-active-exit-fixture.md`
before coding. Do not re-derive the fixture.

## Goal

Add one module that spends **exactly one** diagnostic action on the R-P1.48
fixture and reports a posterior, so a second action is refused rather than
silently taken.

## Files you may touch

- create `psychopomp/active_loop.py`
- create `tests/test_active_loop.py`

Nothing else. No edits to `psychopomp/active_exit.py`, `psychopomp/active_design.py`,
the scripts, the docs, `pyproject.toml` or `uv.lock`. No new dependency.

## API (exact)

```python
DIAGNOSTIC_BUDGET = 1
POLICIES = ("adaptive", "passive", "signed", "shuffled")

class BudgetExhausted(RuntimeError): ...

class Session:
    def __init__(self, budget: int = DIAGNOSTIC_BUDGET) -> None: ...
    def diagnose(self, law: int, state: int, *, policy: str = "adaptive") -> dict: ...
```

`diagnose` returns exactly the keys `policy, selected, reading, posterior, resolved`.

- `policy` not in `POLICIES` → `ValueError` **before** any simulator call.
- `adaptive` → `selected` is the single positive-gain arm from
  `psychopomp.active_design.best_probes({arm: psychopomp.active_exit.rows(arm) for arm in ("passive","signed")})`,
  which is `"signed"` on this fixture. Do not hardcode it without that check.
- `passive` / `signed` → `selected` equals the policy; `reading =
  psychopomp.active_exit.acquire(law, state, selected)`.
- `shuffled` → acquisition uses `"signed"`, then the readout is passed through
  the prereg's frozen shuffle: flip its sign when `state < 0`, else keep it.
  `selected` reports `"shuffled"`.
- `posterior` is a 2-tuple of `Fraction` in law order `(-1, +1)`, computed with
  `psychopomp.active_design.posterior(rows, reading)` over
  `psychopomp.active_exit.rows("signed")`. For `shuffled`, return the prior
  `(Fraction(1,2), Fraction(1,2))` regardless of the reading.
- `reading is None` (malformed log) → `posterior` is the prior, `resolved` is `None`.
- `resolved` is `-1` or `1` only when that law's posterior is exactly 1, else `None`.
- Every `diagnose` call consumes one unit of the session budget; when the budget
  is spent the next call raises `BudgetExhausted` **without** running the simulator.

## Tests (exact expectations)

`tests/test_active_loop.py`, using `pytest`:

1. `test_adaptive_resolves_both_laws_and_all_states` — for all 8 `(law, state)`
   rival cells, `resolved == law` and the posterior is `(1, 0)` or `(0, 1)`.
2. `test_passive_and_shuffled_never_resolve` — for all 8 cells each, `resolved is
   None` and posterior is the prior `(1/2, 1/2)`.
3. `test_malformed_log_abstains` — monkeypatch `psychopomp.active_loop`'s
   acquisition entry point to return `None`; `resolved is None`, prior returned.
4. `test_second_diagnostic_is_refused` — one `diagnose`, then
   `pytest.raises(BudgetExhausted)`; also assert the simulator was not called on
   the refused call (monkeypatch a counter).
5. `test_unknown_policy_refuses_before_simulation` — `ValueError`, counter stays 0.

Write the failing test first, run it, then implement. Do not edit an expectation
to make a red test pass; if an expectation is wrong, stop and report it.

## Gate

```
cd /home/gio/dev/physis-psychopomp && .venv/bin/python -m pytest -q tests/test_active_loop.py
```

All tests pass, then `.venv/bin/python scripts/verify-all.py` must still print
`verify-all: PASS (9 steps)` (the full suite includes your new file).

## Forbidden

`git add/commit/push`, branch changes, dependency installs, network calls,
editing files outside the list, changing any existing test.

## Report

Files created; the gate's last two lines verbatim; the model/thinking footer
line; anything you could not do. If admission says `Not enough hours`, stop and
report `BLOCKED(quota)` — do not pick a different model.
