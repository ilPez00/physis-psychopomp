"""The assumptions round 8's conclusion rests on, measured rather than stated.

If the sensor is not the uniform +-noise/2 per-attribute model, or if the
`steps + 1` convention is wrong anywhere, then "the exact likelihood cannot
distinguish" is a statement about my model, not about the instrument.
"""
import math

import pytest

from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import parallel_recrossing_corpus
from psychopomp.sim import Init, SimConfig, run


def pair(init, seed, noise):
    clean = run(SimConfig(steps=600), seed, init=init)
    noisy = run(SimConfig(steps=600, noise=noise), seed, init=init)
    return clean, noisy


def perturbed_components(noise: float):
    """Every (observed - clean) component of pos and v across several episodes."""
    diffs = []
    for seed in range(6):
        # Both x starts must stay left of the occluder (x0 = 40).
        init = Init(x=(28.0 + 2.0 * seed, 30.0 + 2.0 * (seed % 4)), y=(45.0, 53.0),
                    v=((3.0, 0.0), (3.0, 0.0)))
        clean, noisy = pair(init, seed, noise)
        clean_events = [e for e in clean.observable_log() if e.kind in ("enter_occ", "exit_occ")]
        noisy_events = [e for e in noisy.observable_log() if e.kind in ("enter_occ", "exit_occ")]
        assert len(clean_events) == len(noisy_events)
        for a, b in zip(clean_events, noisy_events):
            for key in ("pos", "v"):
                for c, d in zip(a.attrs[key], b.attrs[key]):
                    diffs.append(d - c)
    return diffs


def test_the_sensor_is_uniform_within_the_half_width():
    noise = 6.0
    diffs = perturbed_components(noise)
    assert diffs
    assert max(diffs) <= noise / 2 + 1e-9
    assert min(diffs) >= -noise / 2 - 1e-9


def test_the_sensor_is_zero_mean_with_the_uniform_variance():
    noise = 6.0
    diffs = perturbed_components(noise)
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / len(diffs)
    expected = noise**2 / 12
    assert abs(mean) < 0.25                    # zero mean, loose bound
    assert 0.5 * expected < var < 1.5 * expected


def test_the_noise_never_touches_the_oracle_log():
    init = Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
    clean, noisy = pair(init, 5, 20.0)
    assert [(e.kind, e.attrs) for e in clean.oracle_log()] == [
        (e.kind, e.attrs) for e in noisy.oracle_log()
    ]


def test_every_true_match_has_zero_residual_without_noise():
    # The `steps + 1` convention, corpus-wide: where the truth is known and the
    # sensor is exact, the straight-line prediction must be exact.
    eps = parallel_recrossing_corpus(6) + [
        run(SimConfig(steps=300), seed) for seed in range(4)
    ]
    checked = 0
    for ep in eps:
        log = ep.observable_log()
        enters = [e for e in log.events if e.kind == "enter_occ"]
        exits = [e for e in log.events if e.kind == "exit_occ"]
        worlds = consistent_worlds(log)
        if not worlds or any(w.swaps for w in worlds):
            continue
        from psychopomp.fixtures import truth_matches

        for a, b in truth_matches(ep):
            ea, xb = enters[a], exits[b]
            v, dt = ea.attrs["v"], ea.attrs["dt"]
            p_in, p_out = ea.attrs["pos"], xb.attrs["pos"]
            steps = xb.t - ea.t + 1
            # Attributes are logged to 6 decimals, so an exact zero is impossible;
            # the residual must be at rounding scale, not at signal scale (0.3).
            assert abs(p_in[1] + v[1] * dt * steps - p_out[1]) < 1e-5
            assert abs(p_in[0] + v[0] * dt * steps - p_out[0]) < 1e-5
            checked += 1
    assert checked >= 12, f"only {checked} true matches checked"


def test_track_samples_are_logged_with_their_own_noise_stream():
    init = Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
    clean, noisy = pair(init, 5, 5.0)
    for event in noisy.observable_log():
        if event.kind in ("enter_occ", "exit_occ"):
            assert event.attrs.get("track"), "track must be logged"
            assert len(event.attrs["track"]) <= 3
    # The oracle carries the CLEAN track (the truth), not the jittered one: same
    # schema on both logs, different values, exactly like pos and v.
    clean_tracks = [e.attrs.get("track") for e in clean.oracle_log() if e.kind in ("enter_occ", "exit_occ")]
    noisy_tracks = [e.attrs.get("track") for e in noisy.oracle_log() if e.kind in ("enter_occ", "exit_occ")]
    assert clean_tracks and clean_tracks == noisy_tracks


def test_track_does_not_restore_decisions_because_velocity_is_derived():
    # Measured 2026-11-21: least-squares velocity over three track samples makes
    # the feasibility set EMPTY (decided 0, tie 0, empty 6) in every cell, because
    # the logged velocity is itself derived as dpos/dt, so a position error of
    # +-noise/2 becomes +-noise/2/dt on v (10x at dt=0.1). Averaging positions
    # cannot fix a channel whose noise is amplified by 1/dt.
    from psychopomp.epec import consistent_worlds
    from psychopomp.fixtures import truth_matches
    from psychopomp.probes import m2_bayes_accuracy

    eps = []
    for k in range(200):
        init = Init(x=(30.0, 30.0 + 2.0 * (k % 5)), y=(45.0, 47.0), v=((3.0, 0.0), (3.0, 0.0)))
        ep = run(SimConfig(steps=600, noise=5.0), k, init=init)
        if not consistent_worlds(ep.observable_log(), 5.0):
            continue
        try:
            truth_matches(ep)
        except ValueError:
            continue
        eps.append(ep)
        if len(eps) >= 6:
            break
    tracked = m2_bayes_accuracy(eps, noise=5.0, tol=5.0, use_track=True)
    assert tracked["decided"] == 0
    assert tracked["empty"] == 6
