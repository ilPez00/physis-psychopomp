import pytest

from psychopomp.selfmodel import BlindEstimate, estimate_blind_region
from psychopomp.sim import Init, SimConfig, run

O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
STEP = 0.3          # speed 3 * dt 0.1


PARKED = (3.0, 97.0)      # outside both occluders, away from every mover path


def horizontal_corpus():
    """One mover per episode, from the left or from the right, no collisions."""
    eps = []
    for i, lane in enumerate((40.0, 44.0, 48.0, 52.0, 56.0, 60.0)):
        cfg = SimConfig(steps=400, o=O, o2=O2)
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=i, init=Init(
            x=(start, PARKED[0]), y=(lane, PARKED[1]), v=((v, 0.0), (0.0, 0.0)))))
    return eps


def vertical_corpus():
    """One mover per episode, rising or falling, no collisions."""
    eps = []
    for i, column in enumerate((47.0, 50.0, 53.0)):
        cfg = SimConfig(steps=400, o=O, o2=O2)
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=100 + i, init=Init(
            x=(column, PARKED[0]), y=(start, PARKED[1]), v=((0.0, v), (0.0, 0.0)))))
    return eps


def test_estimate_is_conservative_and_within_one_step():
    est = estimate_blind_region(horizontal_corpus() + vertical_corpus(), STEP)
    assert est.as_rect() is not None, est.unknown_edges()
    x0, x1, y0, y1 = est.as_rect()
    assert 0.0 <= x0 - O2[0] <= STEP
    assert 0.0 <= O2[1] - x1 <= STEP
    assert 0.0 <= y0 - O2[2] <= STEP
    assert 0.0 <= O2[3] - y1 <= STEP


def test_never_crossed_edges_are_unknown_not_guessed():
    est = estimate_blind_region(horizontal_corpus(), STEP)
    assert est.x0 is not None and est.x1 is not None
    assert est.y0 is None and est.y1 is None
    assert set(est.unknown_edges()) == {"y0", "y1"}
    assert est.as_rect() is None
    # a point covered by an unknown edge is reported unknown, not guessed
    assert est.blind_membership((50.0, 45.0)) is None
    assert est.blind_membership((10.0, 45.0)) is False


def test_errors_are_one_signed_never_pessimistic():
    # estimate ⊆ truth, so the estimate can only call a truly blind point
    # visible; it can never call a truly visible point blind
    est = estimate_blind_region(horizontal_corpus() + vertical_corpus(), STEP)
    x0, x1, y0, y1 = est.as_rect()
    for x in (42.0, 45.9, 46.05, 50.0, 53.95, 54.05, 60.0):
        for y in (36.0, 45.0, 64.0):
            truly_inside = O2[0] <= x <= O2[1] and O2[2] <= y <= O2[3]
            est_inside = x0 <= x <= x1 and y0 <= y <= y1
            assert not (est_inside and not truly_inside), (x, y)


def test_empty_log_gives_no_estimate():
    est = estimate_blind_region([], STEP)
    assert est.as_rect() is None and set(est.unknown_edges()) == {"x0", "x1", "y0", "y1"}
    assert est.blind_membership((50.0, 50.0)) is None


def test_estimate_reads_only_observable_events():
    # the oracle log knows where the body went while hidden; the estimator must
    # never consult it, so a corpus whose oracle is unavailable is still usable
    class ObsOnly:
        def __init__(self, ep):
            self._ep = ep

        def observable_log(self):
            return self._ep.observable_log()

        def __getattr__(self, name):
            raise AssertionError(f"estimator touched {name!r}, not the observable log")

    est = estimate_blind_region([ObsOnly(ep) for ep in horizontal_corpus()], STEP)
    assert est.x0 is not None and est.x1 is not None


def test_blind_estimate_round_trips_a_rect():
    est = BlindEstimate(step=STEP, x0=46.0, x1=54.0, y0=35.0, y1=65.0)
    assert est.as_rect() == (46.0, 54.0, 35.0, 65.0)
    assert est.blind_membership((50.0, 50.0)) is True
    assert est.blind_membership((45.0, 50.0)) is False


O_ISLANDS = (40.0, 60.0, 35.0, 65.0)
EXTRA_ISLAND = (70.0, 78.0, 35.0, 65.0)
O2_WIDE = (30.0, 92.0, 20.0, 90.0)


def islands_corpus():
    """Bodies crossing both blind cells, horizontally and vertically."""
    eps = []
    for i, lane in enumerate((38.0, 42.0, 46.0, 50.0, 54.0, 58.0, 72.0, 76.0)):
        cfg = SimConfig(steps=400, o=O_ISLANDS, o2=O2_WIDE,
                        extra_o=(EXTRA_ISLAND,))
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=i, init=Init(
            x=(start, PARKED[0]), y=(lane, PARKED[1]), v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((45.0, 50.0, 55.0, 72.0, 76.0)):
        cfg = SimConfig(steps=400, o=O_ISLANDS, o2=O2_WIDE,
                        extra_o=(EXTRA_ISLAND,))
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=200 + i, init=Init(
            x=(column, PARKED[0]), y=(start, PARKED[1]), v=((0.0, v), (0.0, 0.0)))))
    return eps


def test_two_cells_are_recovered_separately():
    from psychopomp.selfmodel import estimate_blind_cells

    cells = estimate_blind_cells(islands_corpus(), STEP, n_cells=2)
    assert len(cells) == 2
    truth = [(O_ISLANDS[0], O_ISLANDS[1]), (EXTRA_ISLAND[0], EXTRA_ISLAND[1])]
    for cell, (tx0, tx1) in zip(cells, truth):
        assert cell.x0 is not None and cell.x1 is not None
        assert 0.0 <= cell.x0 - tx0 <= STEP
        assert 0.0 <= tx1 - cell.x1 <= STEP


def test_wrong_cell_count_abstains_rather_than_inventing_geometry():
    from psychopomp.selfmodel import estimate_blind_cells

    cells = estimate_blind_cells(islands_corpus(), STEP, n_cells=4)
    assert len(cells) == 4
    assert all(cell.as_rect() is None for cell in cells)


def single_cell_corpus():
    eps = []
    for i, lane in enumerate((40.0, 44.0, 48.0, 52.0, 56.0, 60.0)):
        cfg = SimConfig(steps=400, o=O, o2=O2)
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=i, init=Init(
            x=(start, PARKED[0]), y=(lane, PARKED[1]), v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((47.0, 50.0, 53.0)):
        cfg = SimConfig(steps=400, o=O, o2=O2)
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=100 + i, init=Init(
            x=(column, PARKED[0]), y=(start, PARKED[1]), v=((0.0, v), (0.0, 0.0)))))
    return eps


def test_auto_count_recovers_two_cells_and_does_not_invent_one():
    from psychopomp.selfmodel import estimate_blind_cells_auto

    two = estimate_blind_cells_auto(islands_corpus(), STEP)
    assert len(two) == 2, two
    truth = ((O_ISLANDS[0], O_ISLANDS[1]), (EXTRA_ISLAND[0], EXTRA_ISLAND[1]))
    for cell, (tx0, tx1) in zip(two, truth):
        assert 0.0 <= cell.x0 - tx0 <= STEP
        assert 0.0 <= tx1 - cell.x1 <= STEP

    one = estimate_blind_cells_auto(single_cell_corpus(), STEP)
    assert len(one) == 1, one
    assert 0.0 <= one[0].x0 - O2[0] <= STEP


def test_a_corpus_that_never_crosses_a_cell_under_reports_it():
    # the sparse corpus never reaches the island, so the auto count is 1: the
    # model is incomplete and nothing in the evidence says so
    from psychopomp.selfmodel import estimate_blind_cells_auto

    sparse = []
    for i, lane in enumerate((38.0, 42.0, 46.0, 50.0)):
        # 180 steps of travel = 54 units from x=10 -> reaches 64, crossing cell 0
        # and stopping before the island at 70
        cfg = SimConfig(steps=180, o=O_ISLANDS, o2=O2_WIDE, extra_o=(EXTRA_ISLAND,))
        sparse.append(run(cfg, 0, episode=300 + i, init=Init(
            x=(10.0, PARKED[0]), y=(lane, PARKED[1]), v=((3.0, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((45.0, 50.0, 55.0)):
        cfg = SimConfig(steps=200, o=O_ISLANDS, o2=O2_WIDE, extra_o=(EXTRA_ISLAND,))
        sparse.append(run(cfg, 0, episode=400 + i, init=Init(
            x=(column, PARKED[0]), y=(10.0, PARKED[1]), v=((0.0, 3.0), (0.0, 0.0)))))
    cells = estimate_blind_cells_auto(sparse, STEP)
    assert len(cells) == 1                      # the island is missing
    assert cells[0].as_rect() is not None       # cell 0 is complete
