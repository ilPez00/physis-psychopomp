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
| W2 | `free-pi-cli` | **GLM 5.3 Flash** (`z-ai/glm-5.3-flash` in `~/.free-pi/agent/models-store.json`) | **high** | user-pinned |

Evidence for the freebuff split, so nobody picks the wrong one: the catalog
carries both `deepseek/deepseek-v4-flash` (premium, recommended) and
`deepseek/deepseek-v4-flash-fast` ("Buffy on DeepSeek Flash (fast mode)"). A
"fast" pick is a **different model**, not a speed setting.

### Setting model + thinking in the TUI

Both CLIs: `/model` opens the picker; type to filter; Enter selects. Reasoning
effort is a separate control (freebuff: Tab on the highlighted row, or `/model`
then Tab; free-pi: its model menu). Confirm from the footer line, which prints
`<model> • <effort>` — paste that line into the report.

**STOP and report `BLOCKED(model)`** if the picker has no matching model, no
thinking selector, or admission says `Not enough hours …` / a quota banner.
Substituting a cheaper or "fast" model silently is a failed delegation, not a
workaround.

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
