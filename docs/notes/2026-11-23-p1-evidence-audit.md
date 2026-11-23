# P1 evidence audit and continuation

Base: `90593f3`. Goal: make the verification command reproducible from a clean
checkout and separate measured evidence from amended or untested claims.

## Ordered plan

1. Reproduce the CI bootstrap without a pre-existing environment and the verifier
   with `uv` absent. Sync the locked dev extra explicitly; missing executables and
   unsupported flags must fail, not print green. Keep all nine gates.
2. Audit R-P1.43 per task, on the same off-boundary subset at all four lags.
   Record what the channel actually changes; preserve original predictions,
   failures, and the historical reproduction gate.
3. Scope R-P1.44 to kick-vs-null attribution and R-P1.45 to a visibility check
   after a pilot-driven amendment. Separate their receipts from a geometric
   model of multi-blocker coverage. No retrospective promotion of claim status.
4. Follow up with one discriminating research card. Prefer shared versus
   independent producer failures at fixed marginal reliability:
   this tests evidence fusion in the existing marker path. A rotating frame
   tests invariance instead; physically compositing blockers changes the
   observation model and needs a separate design decision.

## Review findings

- **Verification:** the prior CI command failed in a clean directory with
  `No virtual environment found`. `uv sync --locked --extra dev --python 3.12`
  created the environment and installed the locked extras. `verify-all.py`
  previously treated missing `uv` as success and ignored `--fast`. Regression
  checks now reject both. GitHub's last run on the baseline, `45092968840`,
  had zero steps and a billing annotation; local results do not resolve it.
- **Preregistration:** the previous checklist accepted a stray eight-digit
  commit prefix or a UUID first cited in Results. It now checks the dated
  filename and preamble for new cards. Git history, not Markdown lint, is the
  evidence of timing.
- **R-P1.43:** `scripts/audit-detection-latency.py` checks actual trajectory
  locations, then compares the same three off-boundary tasks at lags
  `0/1/3/10`. At every lag: `x=42` unique, `x=48/52` tie (3/3 each).
  Excluded `x=46` was unique at all four lags and explains the second hit.
  `_lagged_attrs` samples `j−L` on entry and `j+L` on exit (clamped);
  only the exit timestamp shifts, and velocity/track stay anchored to the
  crossing. The registered forward-snapshot instrument was not tested.
  L2/L4 fail their original thresholds; negative-only L3 doubles from
  0.150 to 2.650, but pools repeated deterministic geometry. Historical
  `PASS` reproduces amended checks, not the original verdict.
- **R-P1.44/45:** R-P1.44 compared kick-vs-null on four points at three
  radii; an unshrunk second observer broke the first implementation.
  R-P1.45 compared `observable`, not attribution, and the original vertex
  and band predictions failed the pilot before their replacement. Its
  12 off-boundary matches remain useful as an amended geometry check.
  Historical receipts and registry labels remain as recorded.
- **New geometric counterexample:** at centre `(50,50)` and radius `1`, a
  single blocker `(40,60,40,60)` hides the disc. Two abutting blockers
  `(40,50,40,60)` and `(50,60,40,60)` with the same union make it visible:
  neither rectangle alone contains the disc. Erosion distributes over
  intersections, not generally over unions. Distinguish a per-blocker model
  from a physically composited mask before extending radius-aware planning.
  Also: `transition_rect` and the polygon edge labels still follow point
  boundaries; finite-radius labels/estimator bounds need their own check.

## Next

1. R-P1.46 is the bounded continuation: compare shared, independent and
   complementary delivery at fixed marginals; strip the payload for a null.
   Next discriminating extension: partial overlap between producers and
   misleading tags, where “any delivery resolves” no longer applies.
2. For geometry, preregister a seam/control pair and test whether an
   explicitly composited mask changes attribution or estimator decisions,
   before adding a new mask model. A true delay card would compare timestamp
   only, forward snapshots, and the current outward sampler on the same
   crossings; do not reuse R-P1.43's threshold verdict.
3. Consumer path unblocked at the source level: `ilPez00/physis-next:main`
   at `997c6416476727da6fa747dfa31ec79ed30e79db` contains the Rust observation
   and store files. Start a new branch at that ref, not the `physis-computer`
   mirror or the paused rebase. Recheck the exact APIs and add the round-trip,
   repeat-import, dry-run, order and torn-tail checks before any push.

## Scope

No new dependencies, learner arms, changes to simulator behavior, or changes to
Physis-next. Hosted CI and a storage mirror are independent of local verification.
