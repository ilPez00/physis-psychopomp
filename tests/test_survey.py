"""Unfitted statistics: which ones can rank the true world (rounds 6-7)."""
import pytest
from psychopomp.epec import consistent_worlds
from psychopomp.fixtures import truth_matches
from psychopomp.probes import statistic_survey
from psychopomp.sim import Init, SimConfig, run


def corpus(sep: float, noise: float, n: int = 6):
    eps = []
    for k in range(200):
        init = Init(
            x=(30.0, 30.0 + 2.0 * (k % 5)),
            y=(45.0, 45.0 + sep),
            v=((3.0, 0.0), (3.0, 0.0)),
        )
        ep = run(SimConfig(steps=600, noise=noise), k, init=init)
        if not consistent_worlds(ep.observable_log(), max(noise, 1e-4)):
            continue
        try:
            truth_matches(ep)
        except ValueError:
            continue
        eps.append(ep)
        if len(eps) >= n:
            break
    return eps


def test_the_residual_is_not_the_best_available_statistic():
    # Measured 2026-11-21: at separation 2 / noise 2 the y-continuity residual
    # scores 0.33 while |dy| alone scores 1.00. The "plateau" recorded a round
    # earlier is a property of that estimator, not of the observation -- adding
    # the noisy velocity term to the prediction destroys the signal.
    r = statistic_survey(corpus(2.0, 2.0), tol=2.0)
    assert r["chance"] == 0.25
    assert r["y_order"]["top1"] == 1.0
    assert r["y_residual"]["top1"] <= 0.5


def test_the_ordering_statistic_solves_the_healthy_cell():
    r = statistic_survey(corpus(6.0, 2.0), tol=2.0)
    assert r["y_order"]["top1"] == 1.0


def test_a_coarse_sensor_defeats_every_single_statistic():
    # Ratio 0.4: no single unfitted statistic reaches the ceiling, but the best
    # one still beats chance -- the only cell where a better estimator could win.
    r = statistic_survey(corpus(2.0, 5.0), tol=5.0)
    # Only statistics that decided every episode count as evidence: a 1.00 with
    # one decision is coverage, not accuracy (speed_delta does exactly that).
    covered = [
        r[n]["top1"]
        for n in ("y_residual", "x_residual", "y_order", "speed_delta")
        if r[n]["decided"] == r["episodes"]
    ]
    assert covered, "no statistic covers the corpus"
    assert r["chance"] == 0.25
    assert max(covered) < 1.0
    assert max(covered) > r["chance"]


def test_bounces_can_never_fall_inside_a_matched_interval_in_this_geometry():
    # Round 7's premise, measured: 0 of 96 matched intervals contained a bounce.
    # It is geometric, not accidental -- the occluder occupies x in [40, 60] and
    # the walls are at x = 0 and 100, so a ball inside the occluder cannot touch
    # a wall. The v_bounce statistic therefore never fires on this simulator, and
    # this test fails the moment the geometry changes enough to make it live.
    log_corpora = corpus(2.0, 5.0)
    total = inside = 0
    for ep in log_corpora:
        log = ep.observable_log()
        enters = [e for e in log.events if e.kind == "enter_occ"]
        exits = [e for e in log.events if e.kind == "exit_occ"]
        bounces = [e for e in log.events if e.kind == "wall_bounce"]
        for world in consistent_worlds(log, 5.0):
            for a, b in world.matches:
                total += 1
                if any(enters[a].t < e.t < exits[b].t for e in bounces):
                    inside += 1
    assert total > 0
    assert inside == 0


def test_no_unfitted_combination_beats_the_best_single_statistic_at_ratio_0_4():
    r = statistic_survey(corpus(2.0, 5.0), tol=5.0)
    assert r["borda"]["decided"] == r["episodes"]
    assert r["borda"]["top1"] == pytest.approx(0.5)
    assert r["x_residual"]["top1"] == pytest.approx(2 / 3)
    assert r["borda"]["top1"] < r["x_residual"]["top1"]


def test_exact_bayes_decides_only_where_the_sensor_supports_one_world():
    from psychopomp.probes import m2_bayes_accuracy

    r = m2_bayes_accuracy(corpus(6.0, 2.0), noise=2.0, tol=2.0)
    assert r["decided"] > 0 and r["tied"] > 0
    assert r["top1"] == 1.0          # when it decides, it is right
    assert r["empty"] == 0           # support propagation is not too tight


def test_at_ratio_0_4_the_exact_sensor_supports_every_world():
    # The decisive measurement: with noise 5 on a 2-unit separation, every
    # world is consistent with the sensor readings. The observables carry no
    # identity information there, so any accuracy above chance is a prior
    # artifact -- including the 0.67 of the best unfitted statistic.
    from psychopomp.probes import m2_bayes_accuracy

    r = m2_bayes_accuracy(corpus(2.0, 5.0), noise=5.0, tol=5.0)
    assert r["decided"] == 0
    assert r["tied"] == r["excluded"] == 0 or r["tied"] > 0
    assert r["tied"] >= 6            # every episode ties over its four worlds
    assert r["empty"] == 0


def test_a_gaussian_surrogate_manufactures_a_decision_the_exact_model_refuses():
    # Same episodes, same observables: the surrogate scores 0.67, the exact
    # uniform model abstains. A likelihood choice can invent signal.
    from psychopomp.probes import m2_bayes_accuracy, m2_map_accuracy

    eps = corpus(2.0, 5.0)
    surrogate = m2_map_accuracy(eps, noise=5.0, tol=5.0)
    exact = m2_bayes_accuracy(eps, noise=5.0, tol=5.0)
    assert surrogate["decided"] == 6
    assert surrogate["top1"] > 0.25
    assert exact["decided"] == 0
