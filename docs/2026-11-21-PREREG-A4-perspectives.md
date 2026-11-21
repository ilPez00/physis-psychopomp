# A4 — pre-registered experiment: observer-relative possible worlds

Status: **REGISTERED 2026-11-21**. Written before execution; never edited into
its own outcome (status lines only). Predecessors, all measured:
`2026-11-20-PREREG.md` (claims A/B), A2 amendment, R-P1.1 operating point,
R-P1.2 frames, R-P1.3 degradation matrix, R-P1.5 interventions.

## Question

Does **observer-relative** possible-world analysis add predictive value over
world-frame analysis under partial observability — once the frame is fixed and
the ceiling is respected?

## Measured starting point (must be cited, not re-derived)

- A2 (pre-contact position channel) = top-1 **1.00** at full precision /
  high sep-to-noise ratio; the same probe falls to **0.33–0.00** in a rotated
  frame (`2026-11-21-PLAN-R-P1.3-camera-degradation.md`). A2 is a **high-r,
  axis-bound** result: it cannot serve as a cross-frame baseline.
- Operating point: `sep=6`, sensor noise `1.0` (Bayes/EC) or `0.5` (A2
  channel), from R-P1.1.
- Degradation boundary: exact Bayes decided-rate falls to 0 at jitter ≈
  `sep/2`; EC enumeration stays sound (4 worlds, truth in worlds) in every
  cell.
- Frame invariants: world and randomized (constant rotation + drift) frames
  preserve the EC world set; body frames are inertial only between the body's
  own velocity changes.

## Hypotheses (falsifiers fixed now)

- **H1 — frame-normalized ranking.** For cells where the world-frame exact
  Bayes is not already 1.00, the frame-normalized decision rule (fit/decide
  in the frame's coordinates, with the summed error support) ranks the truth
  world top-1 on **more episodes** than the world-frame arm, with the same
  cost. Falsified if the difference is ≤ 0 over the registered seeds.
- **H2 — no leakage through frames.** Frame transforms add no information:
  EC world sets and truth-in-worlds are identical across inertial frames at
  equal degradation. Falsified by any cell where a frame yields worlds
  inconsistent with the world-frame set.
- **H3 — control bites.** The cross-episode deranged corpus must score at
  or below the losing arm; if the shuffled control matches the winning arm,
  the win is an artifact (Phase 11D lesson).

## Arms (matched, identical probes)

1. world-frame exact Bayes (uniform sensor, summed support);
2. frame-normalized exact Bayes: `random:seed` frames and a body frame
   (inertial windows only), transforms from `psychopomp/perspective.py`;
3. A2 position probe, **reported only at r ≥ 9** as a reference ceiling —
   never compared across frames;
4. shuffled-exit control (`psychopomp/controls.py`), same seeds.

## Metrics

- truth-world top-1 rank per cell (primary), decided rate, worlds count;
- calibration: number of worlds, truth-in-worlds;
- leakage: subjects identity-free; oracle never an input; ledger refusal
  exercised (`ObservationLedger`);
- cost: wall time per matrix (CPU only).

## Seeds, splits, budget

- `seeds = 5` independent frame seeds × 6 episodes per cell; report mean and
  sd, never a single run.
- Splits by episode and physical configuration; never neighbouring frames.
- CPU only. No GPU arm while omo is offline; wall budget ≤ 5 min per full
  matrix (current matrix is ~1 min).

## Success / failure criteria (fixed)

- H1 supported only if the frame-normalized arm beats world-frame on
  **≥ 2 of 5 seeds** on cells where the world arm < 1.00, with mean
  improvement > 0 and sd reported.
- Any cell where the world arm is already 1.00 is a **ceiling**: excluded
  from H1 claims, reported as ceiling.
- The shuffled control must not match the winning arm (H3).
- A negative result is a deliverable: file the receipt; do not tune cells
  until a positive appears.

## Registered claim

Subjective prior **0.4** (not calibrated; registered in the physis-next store,
`physis-check claim`):

> Perspective-normalized possible-world analysis ranks the truth world higher
> than world-frame analysis under camera degradation, without gaining
> information through the frame transform.

Registered 2026-11-21 as hypothesis `1ff62ee2-78c5-4911-a342-145924586c08`.
The store's embedder is random-projection (lexical) — the registration is a
record for later refutation, not a calibrated judgement.

## Non-claims

No claim about human-like imagination, consciousness, or learned models
outperforming the deterministic ceiling. No metric added after results exist.
