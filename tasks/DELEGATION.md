# Delegation: freebuff + free-pi-cli, one writer at a time

Both target CLIs are **TUI-only** (no headless mode) and drive a real session in
tmux. Two rules follow, and neither is negotiable:

1. **One writer in this checkout.** Run one brief to completion, verify its gate
   yourself, commit, then start the next. Never two agents in one tree.
2. **A delegate claiming success is not success.** The gate command is the truth.
   Re-run it in the same checkout before staging anything.

## Pinned routing (measured 2026-11-23, re-check with `free-agent status`)

| Brief | CLI | Model to select | Thinking | Why this one |
|---|---|---|---|---|
| W1 | `freebuff` | **DeepSeek V4.1 Flash — not the "fast mode" variant** (freebuff catalog: `deepseek/deepseek-v4-flash`; the fast one is `deepseek/deepseek-v4-flash-fast`, display "fast mode") | **high** | user-pinned |
| W2 | `free-pi-cli` | **GLM 5.3 Flash** (`z-ai/glm-5.3-flash` in `~/.free-pi/agent/models-store.json`) | **not selectable** (`supportsReasoningEffort: false` on this route) | user-pinned model; effort pin impossible here, measured |

Evidence for the freebuff split, so nobody picks the wrong one: the catalog
carries both `deepseek/deepseek-v4-flash` (premium, recommended) and
`deepseek/deepseek-v4-flash-fast` ("Buffy on DeepSeek Flash (fast mode)"). A
"fast" pick is a **different model**, not a speed setting.

### Setting model + thinking in the TUI

Both CLIs: `/model` opens the picker; type to filter; Enter selects. Reasoning
effort is a separate control (freebuff: Tab on the highlighted row, or `/model`
then Tab; free-pi: its model menu). Confirm from the footer line, which prints
`<model> • <effort>` — paste that line into the report.

**STOP and report `BLOCKED(model)`** if the picker has no matching model, or
admission says `Not enough hours …` / a quota banner. Substituting a cheaper or
"fast" model silently is a failed delegation, not a workaround.

**Neither driver pins the model.** `free-agent` types the task into a TUI whose
model is whatever that session last used, so a run can complete on the wrong model
(W2 did, see the run log). Select the model in the TUI *before* the task, or set
`freebuffModelKey` in `~/.config/manicode/settings.json`, and treat a footer that
disagrees with the pinned label as `BLOCKED(model)` even if the gate is green.

## State as of this commit

`free-agent status`: **freebuff EXHAUSTED** — "Not enough hours for DeepSeek V4.1
Flash: an hour on it takes 2 hours". So **W1 is currently unrunnable** and must
not be started until that clears. `freepi` reports YES.

Therefore: run **W2 first** if freepi is available, and queue W1 behind the
freebuff reset. That inverts the plan's dependency (W2's verifier checks W1's
loop), so W2 must be written against the *contract* below, not against W1's
code, and its tests must construct their own records. If that is unacceptable,
run W1 first when freebuff returns and W2 after.

## Launch (bounded, tmux-backed)

`free-agent` is the launcher; it already drives both TUIs.

```bash
cd ~/dev/physis-psychopomp
free-agent run "$(cat tasks/briefs/W2-freepi-receipt-verifier.md)" \
  -w "$PWD" --worker freepi --timeout 1800 --json
```

For the gated variant (recommended; stops on the brief's own gate):

```bash
free-agent loop "$(cat tasks/briefs/W2-freepi-receipt-verifier.md)" \
  -w "$PWD" --check '.venv/bin/python -m pytest -q tests/test_active_receipt.py' \
  --max-iterations 2 --json
```

Then, myself, before anything is staged:

```bash
git status --short                       # only the brief's files may differ
.venv/bin/python -m pytest -q            # full suite
.venv/bin/python scripts/verify-all.py   # all nine gates
git diff --check
```

## What a brief must contain (they start with fresh context)

Goal, the exact files it may create, the exact public API and invariants, the
exact tests with their expected numbers, the gate command, forbidden actions
(no git, no new dependencies, no edits outside its file list, no network), and a
report format. Nothing about "what we discussed".

## Stop conditions — the delegate must abort, not improvise

- quota/login banner, or a model other than the pinned one is selected;
- any file outside its declared list needs changing;
- a test contradicts this document (the delegate reports the contradiction
  rather than editing the test to fit its code);
- the gate cannot run.

`UNVERIFIABLE` is not a pass. A delegate that cannot run its gate has produced
nothing I may commit.

## Run log

### 2026-11-23 — W2 via free-agent / freepi

`free-agent loop … --worker freepi --check 'pytest -q tests/test_active_receipt.py'`
returned `ok=true`, gate exit 0, and created exactly its two files. **The delegate
reported the session was NOT on the pinned model** ("re-run this same brief in a
session whose modelId is `z-ai/glm-5.3-flash`"), so by the rules above the run is
`BLOCKED(model)`, not a delivered brief: free-agent's freepi driver does not set
the model, and the TUI default won. The two files were therefore reviewed by me
as unreviewed work, not accepted as a delegate result.

Review found one **required** defect: `verify` checked only that the record was
self-consistent, so a plan carrying a fabricated prediction table with a matching
digest read as `VERIFIED` — the one thing the module exists to prevent. Fixed in
`psychopomp/active_receipt.py` by recomputing from `active_exit.rows(selected)`
(`predictions_for`) and refusing any plan whose table differs; reproducer
`tests/test_active_receipt.py::test_forged_prediction_table_refused` was written
first and failed (`+ VERIFIED`) before the fix.

Consequence for W1: its brief cannot rely on the driver to pin the model either.
Set the model in the TUI before typing the task, and treat a footer that does not
read `DeepSeek V4.1 Flash • high` (no "fast") as `BLOCKED(model)`.

### 2026-11-23 — W1 delivered inline instead

freebuff stayed `EXHAUSTED` ("Not enough hours"), so W1's scope was implemented
here as `psychopomp/active_loop.py` + `tests/test_active_loop.py` (5 tests) rather
than waiting. The brief stays in the repo as the spec it was built against; its
gate is now part of the suite. Provenance: **mine, not a delegate's.**

The delegate's W2 test `test_verifier_never_imports_the_session_loop` asserted on
`sys.modules` and went red as soon as the loop existed and any sibling test
imported it. Rewritten to check the module's own source — the property it meant
to check. Kept as the example of why a delegate's green gate is a hypothesis.
