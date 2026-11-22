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


def test_law_is_callable_from_the_command_line():
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    spec = json.dumps({"config": {"o2": [50, 70, 35, 65]}, "point": [55, 50], "t": 60})
    out = subprocess.run([sys.executable, "-m", "psychopomp.law", spec],
                         cwd=root, capture_output=True, text=True, check=True)
    payload = json.loads(out.stdout)
    assert payload["identifiable"] is False
    assert payload["blind_region"] == [50, 60.0, 35.0, 65.0]
    assert payload["envelope"]["noise_breakpoint_sigma"] == 15.0


def test_the_documented_envelope_matches_the_documented_numbers():
    # docs/LAW.md quotes the envelope; if one moves without the other, the doc
    # becomes a claim the code does not support.
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "docs" / "LAW.md").read_text()
    for sigma, accuracy in ENVELOPE["noise_accuracy"].items():
        # the doc states percentages ("94%"), the module states fractions
        assert f"{round(accuracy * 100)}%" in text, f"{sigma} accuracy missing from LAW.md"
    assert str(int(ENVELOPE["noise_full_identification_upto_sigma"])) in text
    assert str(int(ENVELOPE["noise_breakpoint_sigma"])) in text
    assert "boundary" in text.lower()


def test_blind_set_can_be_a_union_and_the_gap_is_identifiable():
    # R-P1.25: two islands with a gap. The law is membership, so a point inside
    # the bounding box but outside every cell is identifiable.
    cfg = SimConfig(o2=(30.0, 92.0, 20.0, 90.0), extra_o=((70.0, 85.0, 35.0, 65.0),))
    from psychopomp.law import blind_cells

    cells = blind_cells(cfg)
    assert len(cells) == 2, cells
    assert predict_identifiable(cfg, (65.0, 45.0)) is True      # in the gap
    assert predict_identifiable(cfg, (75.0, 45.0)) is False     # inside the island
    envelope = blind_region(cfg)
    assert envelope[0] <= 65.0 <= envelope[1]                    # bbox DOES cover it
    assert not on_boundary(cfg, (65.0, 45.0))
