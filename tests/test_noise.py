"""N1: sensor noise is a world parameter, and it cannot touch the answer key."""
from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import parallel_recrossing_corpus, truth_matches
from psychopomp.probes import m2_baseline, m2_position_continuity
from psychopomp.sim import Init, SimConfig, run

INIT = Init(x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))


def observable_attrs(ep):
    return [dict(e.attrs) for e in ep.observable_log()]


def oracle_attrs(ep):
    return [(e.kind, dict(e.attrs)) for e in ep.oracle_log()]


def test_zero_noise_reproduces_the_exact_log():
    a = run(SimConfig(steps=600), 5, init=INIT)
    b = run(SimConfig(steps=600, noise=0.0), 5, init=INIT)
    assert observable_attrs(a) == observable_attrs(b)
    assert oracle_attrs(a) == oracle_attrs(b)


def test_noise_moves_the_observable_log_and_never_the_oracle():
    clean = run(SimConfig(steps=600), 5, init=INIT)
    noisy = run(SimConfig(steps=600, noise=20.0), 5, init=INIT)
    assert observable_attrs(clean) != observable_attrs(noisy)
    assert oracle_attrs(clean) == oracle_attrs(noisy)


def test_noise_is_deterministic_per_seed_and_episode():
    a = run(SimConfig(steps=600, noise=5.0), 5, init=INIT)
    b = run(SimConfig(steps=600, noise=5.0), 5, init=INIT)
    c = run(SimConfig(steps=600, noise=5.0), 6, init=INIT)
    assert observable_attrs(a) == observable_attrs(b)
    assert observable_attrs(a) != observable_attrs(c)


def test_the_filter_breaks_at_default_tolerance_and_recovers_with_a_stated_one():
    # Measured 2026-11-21: a 2-unit sensor on an otherwise exact world yields
    # ZERO consistent worlds, because continuity/contact are compared at 1e-4.
    # The apparatus does not degrade, it collapses; a tolerance is not optional
    # once the log carries sensor noise.
    offset = Init(x=(30.0, 34.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
    ep = run(SimConfig(steps=600, noise=2.0), 5, init=offset)
    assert truth_matches(ep)  # crossings still separated in t
    assert consistent_worlds(ep.observable_log()) == []          # default 1e-4
    assert consistent_worlds(ep.observable_log(), tol=2.0)       # stated tolerance


def test_sensor_noise_degrades_the_probe_the_same_way_jitter_did():
    # Sanity that the world-level model is the one F3 measured: a noisy world
    # must cost top-1, not leave it untouched.
    clean = m2_position_continuity(parallel_recrossing_corpus(6, noise=0.0))
    noisy = m2_position_continuity(parallel_recrossing_corpus(6, noise=5.0))
    assert clean["top1"] == 1.0
    assert noisy["top1"] <= clean["top1"]


def test_a_coarse_sensor_degrades_the_probe_to_a_plateau_above_chance():
    # Measured with the int-only noise seed (world-level noise, filter tolerance
    # = sensor accuracy): 0 -> 1.00, 2 -> 0.83, 5/10/20 -> 0.33, against a 0.25
    # chance floor. The earlier "below chance at 20" reading was an artifact of
    # hashing a string into the seed (0.17 locally, 0.33 on CI); with a stable
    # seed the residual degrades and then plateaus, and never loses to guessing.
    def corpus(noise):
        eps = []
        for k in range(80):
            init = Init(x=(30.0, 30.0 + 2.0 * (k % 5)), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0)))
            ep = run(SimConfig(steps=600, noise=noise), k, init=init)
            tol = max(noise, 1e-4)
            if not consistent_worlds(ep.observable_log(), tol):
                continue
            try:
                truth_matches(ep)
            except ValueError:
                continue
            eps.append(ep)
            if len(eps) >= 6:
                break
        return eps

    clean = m2_position_continuity(corpus(0.0))
    coarse = m2_position_continuity(corpus(20.0), tol=20.0)
    assert clean["top1"] == 1.0
    assert coarse["top1"] > coarse["chance"]      # degraded, still better than guessing
    assert coarse["top1"] < clean["top1"]
