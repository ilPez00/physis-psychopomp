"""R-P1.49: identity as the organization recovered after total turnover."""
import pytest

from psychopomp.turnover import INVARIANT, OBSERVE, balanced, run

CELLS = [(target, p) for target in (1, 2) for p in (0, 1, 2)]


def residence(run_result):
    return run_result.residence


def test_capacity_every_initial_component_is_retired_and_nominal_trajectories_tie():
    nominal = run("feedback", 1, 0)
    assert nominal.fully_replaced and len(nominal.replaced) == 2
    other = run("open-loop", 1, 0, nominal=nominal.transfers)
    assert other.fully_replaced
    assert nominal.trajectory() == other.trajectory(), "arms differ before any disturbance"
    assert all(nominal.loads[t] == (4, 4) for t in OBSERVE)


@pytest.mark.parametrize("target", [1, 2])
def test_the_discriminating_cell_two_units_on_either_role(target):
    nominal = run("feedback", target, 0)
    closed = run("feedback", target, 2)
    opened = run("open-loop", target, 2, nominal=nominal.transfers)
    assert residence(closed) == 3, closed.loads
    assert residence(opened) == 0, opened.loads
    assert all(balanced(closed.loads[t]) for t in OBSERVE)
    assert not any(balanced(opened.loads[t]) for t in OBSERVE)


@pytest.mark.parametrize("target", [1, 2])
@pytest.mark.parametrize("p", [0, 1])
def test_cells_that_must_not_discriminate(target, p):
    nominal = run("feedback", target, 0)
    closed = run("feedback", target, p)
    opened = run("open-loop", target, p, nominal=nominal.transfers)
    assert residence(closed) == residence(opened) == 3, (p, closed.loads, opened.loads)


@pytest.mark.parametrize("target", [1, 2])
def test_verdict_is_structural_not_nominal(target):
    nominal = run("feedback", target, 0)
    plain = run("feedback", target, 2)
    relabelled = run("feedback", target, 2, relabel=True)
    assert residence(plain) == residence(relabelled) == 3
    opened = run("open-loop", target, 2, nominal=nominal.transfers)
    assert opened.fully_replaced and opened.replaced == plain.replaced
    assert residence(opened) == 0


def test_out_of_catalogue_cells_are_refused():
    with pytest.raises(ValueError):
        run("feedback", 3, 0)
    with pytest.raises(ValueError):
        run("feedback", 1, 3)
    with pytest.raises(ValueError):
        run("otherwise", 1, 0)
