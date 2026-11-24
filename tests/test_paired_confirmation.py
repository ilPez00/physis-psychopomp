import runpy
from pathlib import Path


def test_budget_and_conditional_support_can_each_fail():
    script = runpy.run_path(str(Path(__file__).resolve().parents[1]
                               / "scripts/paired-confirmation.py"))
    measure = script["measure"]
    assert all(measure()["checks"].values())
    bad_marginal = {**script["ROWS"], "mimic": ((9, 0), (9, 0), (2, 2), (2, 3))}
    assert measure(bad_marginal)["checks"] == {"P1": False}
    same_marginal = {**script["ROWS"], "mimic": ((9, 2), (9, 3), (2, 0), (2, 1))}
    checks = measure(same_marginal)["checks"]
    assert checks["P1"] and not checks["P3"] and checks["P4"]


def test_second_probe_is_never_called_on_ambiguous_or_unsupported_first_read():
    script = runpy.run_path(str(Path(__file__).resolve().parents[1]
                               / "scripts/paired-confirmation.py"))

    def forbidden():
        raise AssertionError("confirmation consumed")

    classify = script["classify"]
    for first, expected in ((1, "ambiguous"), (9, "unsupported")):
        assert classify(first, forbidden, 2, script["ROWS"]) == (expected, None, 1)
    assert classify(2, forbidden, 1, script["ROWS"]) == ("unconfirmed", None, 1)
