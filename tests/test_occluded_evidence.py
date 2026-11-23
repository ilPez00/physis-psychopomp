from copy import deepcopy

import pytest

from psychopomp.occluded_evidence import (
    acquire, calibrate, decide, plan, trajectory,
)
from psychopomp.verify_occluded_evidence import verify


def case(layout, law, policy="adaptive", case_id="case-17"):
    calibration = calibrate(case_id, layout, law)
    commitment = plan(calibration, policy)
    observation = acquire(commitment, law)
    return calibration, commitment, observation, decide(commitment, observation)


@pytest.mark.parametrize("layout", ["left", "right"])
def test_calibration_rejects_nominal_but_does_not_separate_rivals(layout):
    assert calibrate("case-17", layout, -1) == calibrate("case-17", layout, 1)
    calibration = calibrate("case-17", layout, 1)
    assert calibration == {"case": "case-17", "layout": layout, "magnitude_eighths": 45}
    assert plan(calibration, "adaptive")["calibration_predictions"] == [0, 45, 45]
    with pytest.raises(ValueError, match="calibration"):
        plan(calibrate("case-17", layout, 0), "adaptive")


@pytest.mark.parametrize("layout", ["left", "right"])
@pytest.mark.parametrize("law", [-1, 1])
def test_selected_view_distinguishes_and_does_not_change_path(layout, law):
    assert trajectory(layout, law, "left") == trajectory(layout, law, "right")
    assert trajectory(layout, -1, "left") != trajectory(layout, 1, "left")
    c, p, o, d = case(layout, law)
    assert p["choice"] == layout
    assert p["information_bits"] == {
        "left": int(layout == "left"), "right": int(layout == "right"),
    }
    assert o["readout_eighths"] == 6 * law
    assert d["resolved"] == law
    assert verify(c, p, o, d) == law


@pytest.mark.parametrize("policy", ["passive", "left"])
def test_missing_or_non_discriminating_readout_can_only_abstain(policy):
    c, p, o, d = case("right", 1, policy)
    assert o is None or o["readout_eighths"] is None
    assert d["posterior"] == [0.5, 0.5]
    assert verify(c, p, o, d) is None
    d["resolved"] = 1  # right label, no evidence
    with pytest.raises(ValueError, match="decision"):
        verify(c, p, o, d)


def test_out_of_support_readout_does_not_force_winner():
    c, p, o, _ = case("left", 1)
    o["readout_eighths"] = 99
    decision = decide(p, o)
    assert decision["posterior"] is None
    assert verify(c, p, o, decision) is None


def test_wrong_case_or_predicted_readout_is_not_acquisition():
    c, p, _, _ = case("left", 1)
    _, _, swapped, _ = case("left", -1, case_id="case-18")
    with pytest.raises(ValueError, match="acquisition"):
        verify(c, p, swapped, decide(p, swapped))
    o = acquire(p, 1)
    o["source"] = "counterfactual"
    with pytest.raises(ValueError, match="acquisition"):
        verify(c, p, o, decide(p, o))


def test_tampered_forecast_or_truth_leakage_is_refused():
    c, p, o, d = case("left", -1)
    forged = deepcopy(p)
    forged["predictions"]["left"] = [-6, -6]
    with pytest.raises(ValueError, match="commitment"):
        verify(c, forged, o, d)
    with pytest.raises(ValueError, match="calibration"):
        plan({**c, "truth": -1}, "adaptive")
    with pytest.raises(ValueError, match="observer"):
        trajectory("left", -1, "outside-catalogue")
