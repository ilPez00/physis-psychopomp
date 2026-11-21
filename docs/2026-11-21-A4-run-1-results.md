# A4 run 1 — results (2026-11-21)

Preregistration: `2026-11-21-PREREG-A4-perspectives.md` (registered before the
run; verdicts use its thresholds, not ad-hoc ones). Instrument:
`scripts/a4-perspectives.py`. Corpus: parallel lanes sep=6, sensor noise 1,
6 episodes, 5 frame seeds + a body frame. Cells chosen for headroom per the
prereg rule (a cell where the world arm is already 1.00 is a ceiling).

## Numbers (top-1 over all episodes; decided/6 in brackets)

| cell | world | random seeds 1–5 | ball:0 | shuffled control | worlds | truth-in-worlds |
|---|---|---|---|---|---|---|
| baseline | 1.00 (6/6) | 1.00 ×5 | 1.00 | 0.00 (0/6) | 4.00 | 6/6 |
| q=2 | 1.00 (1/6) | 1.00, 0.00, 0.00, 0.00, 0.00 | 0.00 | 0.00 | 4.00 | 6/6 |
| q=4 | 0.00 (0/6) | 0.00 ×5 | 0.00 | 0.00 | 4.00 | 6/6 |
| j=2 | 0.00 (0/6) | 0.00, **1.00 (1/6)**, 0.00, 0.00, 0.00 | 0.00 | 0.00 | 4.00 | 6/6 |
| j=3 | 0.00 (0/6) | 0.00 ×5 | 0.00 | 0.00 | 4.00 | 6/6 |

## Verdicts (prereg thresholds)

- **H1 — FALSIFIED.** Headroom cells `q=4`, `j=2`, `j=3`. Seed-beats over the
  world arm: `q=4` 0/5, `j=2` 1/5 (seed 2, one episode), `j=3` 0/5. The
  prereg required **≥ 2 of 5 seeds**; a single seed deciding one episode more
  is not a mechanism, it is one realisation.
- **H2 — UPHELD.** World sets (4.00 mean) and truth-in-worlds (6/6) are
  identical across world, random and body frames in every cell: the frame
  transform gains no information.
- **H3 — UPHELD.** The shuffled-exit control scores 0.00 in every cell; the
  winning arm does not match it.

## Interpretation

At this instrument, **perspective normalization adds no predictive value**:
the exact-Bayes decision in frame coordinates is a bijection of the world-frame
decision, so it cannot create a decision that does not exist. The only seed
that "wins" (random:2 at j=2) decides 1/6 episodes — exactly the pattern the
prereg's ≥2-seed rule was written to reject.

This is a **negative receipt**, not a failure of process: the claim was
registered at prior 0.4 before the run, and the prereg's ceiling rule
prevented the q=2/baseline cells from being counted as headroom.

## Consequence

- A mechanism that could change this must use information the endpoints do not
  carry — pre-contact history or interactions — i.e. the learned arm, which
  is blocked twice over: no deterministic headroom on this family (A3/R-P1.1)
  and the GPU node is offline.
- Nothing here touches P2/P3; the export contract (R-P1.7) is unaffected.
- Registry: hypothesis `1ff62ee2-78c5-4911-a342-145924586c08` moved to
  **Contradicted** with this measurement as the contradicting evidence
  (see status line below).

STATUS 2026-11-21: A4 run 1 executed. H1 falsified (0/5, 1/5, 0/5 seed-beats;
threshold ≥2), H2/H3 upheld. Claim recorded contradicted. No retune planned;
the next instrument change, if any, must alter what is observed (resolution,
separation or a second observable), not the coordinate system.
