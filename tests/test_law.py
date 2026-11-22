from psychopomp.law import (
    BOUNDARY_TOL, ENVELOPE, blind_region, boundary_distance, on_boundary,
    predict_identifiable,
)
from psychopomp.sim import SimConfig


def test_blind_region_is_the_observer_intersection():
    cfg = SimConfig(o2=(50.0, 70.0, 35.0, 65.0))
    assert blind_region(cfg) == (50.0, 60.0, 35.0, 65.0)
    # a drifted-away occluder leaves nothing hidden
    far = SimConfig(o2=(50.0, 70.0, 35.0, 65.0), o2_velocity=(2.0, 0.0))
    assert blind_region(far, 200) is None
    assert blind_region(SimConfig()) == (40.0, 60.0, 35.0, 65.0)


def test_predict_identifiable_is_membership():
    cfg = SimConfig(o2=(50.0, 70.0, 35.0, 65.0))
    assert predict_identifiable(cfg, (45.0, 50.0)) is True     # seen by observer 2
    assert predict_identifiable(cfg, (55.0, 50.0)) is False    # blind
    assert predict_identifiable(SimConfig(), (55.0, 50.0)) is False
    assert predict_identifiable(SimConfig(), (10.0, 10.0)) is True


def test_boundary_cells_are_flagged_not_predicted():
    cfg = SimConfig(o2=(50.0, 70.0, 35.0, 65.0))
    assert on_boundary(cfg, (50.0, 50.0)) is True              # on the x edge
    assert on_boundary(cfg, (55.0, 65.0)) is True              # on the y edge
    assert on_boundary(cfg, (55.0, 50.0)) is False             # interior
    assert boundary_distance(cfg, (51.0, 50.0)) == 1.0
    assert BOUNDARY_TOL == 1e-6


def test_envelope_is_data_that_matches_its_sources():
    acc = ENVELOPE["noise_accuracy"]
    assert list(acc) == sorted(acc)                              # monotone in sigma
    assert all(acc[a] >= acc[b] for a, b in zip(list(acc), list(acc)[1:]))
    assert ENVELOPE["noise_breakpoint_sigma"] == 15.0
    assert acc[15.0] == 0.84 < 0.90 <= acc[10.0]                 # breakpoint definition
    assert ENVELOPE["noise_full_identification_upto_sigma"] == 6.0
