"""R-P1.76: how far can a counterfactual be trusted?

Frozen card: docs/2026-11-27-PREREG-R-P1.76-horizon.md, pushed at `8666746` and
amended before this file existed. Amendment 1: R-P1.57 is a finite arithmetic
table with no horizon, so this uses the **simulator** path D3 describes.

Two rival kicks of equal magnitude and opposite sign (additive vs sign-flipped).
Each horizon is a shorter episode, so a short `T` is literally less evidence.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.attribution import attribute, candidate_episode, motion_distance, signature
from psychopomp.interventions import Intervention
from psychopomp.sim import Init, Kick, SimConfig, run

CLAIM = "3b085a31-3aae-44ff-a678-71f977904534"
# The kick fires at step 20, so horizons shorter than that contain no events at
# all: separation and control were both 0.0 at T = 10 and 20, which measures the
# absence of an episode rather than a short horizon. Measured before scoring.
HORIZONS = (25, 30, 40, 60, 80, 120, 160, 200)
SEEDS = (0, 1, 2, 3, 4)
DT = 0.1
INIT = Init(x=(28.0, 32.0), y=(45.0, 51.0), v=((3.0, 0.0), (3.0, 0.0)))
T_KICK = 20
ADDITIVE = Intervention(t=T_KICK, ball=0, dv=(0.0, 1.5))
FLIPPED = Intervention(t=T_KICK, ball=0, dv=(0.0, -1.5))


def config(steps: int) -> SimConfig:
    return SimConfig(steps=steps)


def episode(steps: int, seed: int, kick: Intervention):
    return run(config(steps), seed, init=INIT,
               kicks=(Kick(kick.t, kick.ball, kick.dv),))


def rivals(steps: int, seed: int) -> dict:
    """Separation between the two candidates, and whether attribution resolves."""
    obs = episode(steps, seed, ADDITIVE)
    additive_cand = candidate_episode(config(steps), seed, INIT, ADDITIVE,
                                      episode=obs.episode, noise_stream=1)
    flipped_cand = candidate_episode(config(steps), seed, INIT, FLIPPED,
                                     episode=obs.episode, noise_stream=2)
    separation = motion_distance(signature(additive_cand), signature(flipped_cand))
    out = attribute(obs, [ADDITIVE, FLIPPED], config(steps), seed, INIT)
    return {
        "separation": separation,
        "unique": bool(out["unique"]),
        "best_is_true": out["best"] is not None and out["best"].t == ADDITIVE.t
        and out["best"].dv == ADDITIVE.dv,
        "margin": out["margin"],
    }


def control(steps: int, seed: int) -> float:
    """Distance to an UNRELATED episode: the metric must not decay with horizon.

    The first version used the same INIT with a different seed, which is the same
    episode because there is no noise — distance 0 at every horizon, an inert
    control. An unrelated episode has to differ in its geometry.
    """
    unrelated_init = Init(x=(10.0, 20.0), y=(20.0, 80.0), v=((1.0, 0.0), (0.0, 1.0)))
    obs = episode(steps, seed, ADDITIVE)
    unrelated = run(config(steps), seed, init=unrelated_init,
                    kicks=(Kick(T_KICK, 0, (0.0, 1.5)),))
    additive_cand = candidate_episode(config(steps), seed, INIT, ADDITIVE,
                                      episode=obs.episode, noise_stream=1)
    return motion_distance(signature(unrelated), signature(additive_cand))


def main() -> int:
    rows = {}
    for T in HORIZONS:
        cells = [rivals(T, s) for s in SEEDS]
        sep = statistics.fmean(c["separation"] for c in cells)
        rows[str(T)] = {
            "separation": round(sep, 6),
            "decided": sum(1 for c in cells if c["unique"]),
            "correct": sum(1 for c in cells if c["unique"] and c["best_is_true"]),
            "of_seeds": len(SEEDS),
            "control_distance": round(statistics.fmean(control(T, s) for s in SEEDS), 6),
        }

    seps = [rows[str(T)]["separation"] for T in HORIZONS]
    # P1: full horizon resolves uniquely and correctly.
    p1 = rows[str(HORIZONS[-1])]["correct"] == len(SEEDS)

    # P2: separation peaks and then does not exceed the peak at the full horizon.
    peak = max(seps)
    peak_at = HORIZONS[seps.index(peak)]
    p2 = seps[-1] <= peak + 1e-9 and peak_at < HORIZONS[-1]

    # P3: the shortest horizon that decides 5/5 is <= 60.
    sufficient = next((T for T in HORIZONS if rows[str(T)]["correct"] == len(SEEDS)), None)
    p3 = sufficient is not None and sufficient <= 60

    # P4: the unrelated-episode control stays above the rival distance everywhere.
    p4 = all(rows[str(T)]["control_distance"] > rows[str(T)]["separation"] for T in HORIZONS)

    # P5: decidability is monotone up to the sufficient horizon.
    upto = [rows[str(T)]["decided"] for T in HORIZONS
            if sufficient is None or T <= sufficient]
    p5 = all(a <= b for a, b in zip(upto, upto[1:]))

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )

    receipt = {
        "card": "R-P1.76", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.76-horizon.md",
        "amendment": "R-P1.57 is a finite arithmetic table with no horizon; this "
                     "uses the simulator path D3 describes",
        "command": "python3 scripts/horizon-prereg.py",
        "horizons": list(HORIZONS), "seeds": list(SEEDS),
        "kick": {"additive": list(ADDITIVE.dv), "flipped": list(FLIPPED.dv),
                 "t": T_KICK},
        "rows": rows,
        "peak_at": peak_at, "peak": peak,
        "sufficient_horizon": sufficient,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/horizon-20261128"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "rows": rows,
                      "peak_at": peak_at, "sufficient": sufficient}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
