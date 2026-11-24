import runpy
from pathlib import Path


def test_witness_detects_collapsed_laws_and_wrong_residual_direction():
    script = runpy.run_path(str(Path(__file__).resolve().parents[1]
                               / "scripts/paired-counterfactual.py"))
    measure, outcome = script["measure"], script["outcome"]
    assert measure()["checks"] == dict.fromkeys(("D1", "D2", "D3", "D4", "D5"), True)
    collapsed = measure(world=lambda law, action, s: outcome("additive", action, s))
    assert collapsed["checks"] == {"D1": False}
    reversed_reuse = measure(reuse=lambda action, observed: 3 * (1 - action) - (observed - 3 * action))
    assert reversed_reuse["checks"]["D2"] is False
    assert reversed_reuse["checks"]["D5"] is True
