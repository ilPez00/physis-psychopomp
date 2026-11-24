import runpy
from pathlib import Path


def test_capacity_gate_and_mimic_control_detect_changed_instruments():
    script = runpy.run_path(str(Path(__file__).resolve().parents[1]
                               / "scripts/budgeted-model-mismatch.py"))
    measure = script["measure"]
    assert all(measure()["checks"].values())
    broken = {**script["TABLES"], "clean": script["TABLES"]["passive"]}
    assert measure(tables=broken)["checks"] == {"B1": False}
    report = measure(third=(9, 9, 9, 9))
    assert report["checks"]["B4"] is False
