# Occluded evidence proof: one experiment, two laws

This offline integration slice follows the [active law proposal](2026-11-23-active-law-identification.md).
It uses an actual Psychopomp exit event. No benchmark adapter, model calls,
robotics, new public API, or production world.

## Frozen fixture and evaluation

- One body starts at `(44, 50)` with velocity `(2, 0)`, step size 1, inside
  the stock occluder. The nominal transverse acceleration is zero. Rival
  laws have accelerations `−1/8` and `+1/8`, with equal priors.
- Calibration exposes only the absolute transverse displacement at the
  late exit (step 9). Nominal prediction is `0`; both rivals predict `45/8`.
  Equal **declared** observations do not mean equal latent paths. Raw exit
  events, configuration hashes, seeds and law labels are not planner inputs.
- Probe a new run with an allowlisted left or right observer and deadline
  step 3. One observer's blocking geometry ends at `x=48`, the other at
  `x=60`; which side works varies by public layout. The early view reads
  signed displacement `−6/8` or `+6/8`; the late view returns no reading
  at the deadline. Geometry must not change the latent trajectory.
- Use all four layout × law cells. Compare passive, fixed-left, fixed-right
  and seeded random with the same one-probe budget. Verify both laws; the
  outcome is not a generalization beyond these four deterministic cells.
- A separately implemented analytic verifier checks the committed plan,
  separately supplied acquisition record, forecast table, and belief update.
  Missing, out-of-support, swapped, or fabricated evidence earns no resolution.
  An evaluator checks truth only after the verified decision. Digests bind
  records; they do not authenticate an untrusted producer.
- Keep proposal and measured evidence separate in a disposable Physis store:
  propose nominal and rival hypotheses; attach contradiction to nominal on
  calibration and attach opposing evidence to the rivals only on verified
  resolution. Read back evidence and trace after reopening. Do not call
  authority-driven `accept` or `reject`.

## Implementation plan

1. Pin the calibration, sensor mask and four cells in `tests/test_occluded_evidence.py`.
   Use `psychopomp/occluded_evidence.py` to acquire scalar readouts through
   the existing simulator, precommit the plan, and produce records.
2. Add a verifier to `psychopomp/verify_occluded_evidence.py`, independent of
   the simulator/controller. Test correct-label-without-evidence, swapped
   acquisition, outside-support and non-informative arms before running the
   comparison. Require `4/4` verified adaptive, `2/4` each fixed, `0/4`
   passive, and `0` false resolutions across every arm.
3. Use `scripts/occluded-evidence.py` to run the comparison and optionally
   round-trip one verified case through the existing Physis stdio MCP.
   CLI writes artifacts only under an explicitly new output directory.
   Run focused tests, `scripts/verify-all.py`, and a real Physis round-trip.
