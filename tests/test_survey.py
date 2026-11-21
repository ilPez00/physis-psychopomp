"""Unfitted statistics: which ones can rank the true world (round 6)."""
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
