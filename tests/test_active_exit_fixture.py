"""Pin the simulator-backed sensor capacity and its observation boundary."""
from dataclasses import replace

import pytest

from psychopomp import active_exit
from psychopomp.eventlog import Event, EventLog, Provenance

OBS = Event("exit_occ", 21, ("ball",), {"side": "right", "pos": [60.5, 52.125]},
            True, Provenance("synthetic", "never-forward-this", 0, 0))


@pytest.mark.parametrize(("probe", "command", "expected"), [
    ("passive", 0, 2_125_000), ("signed", 2, 1), ("magnitude", 2, 2_125_000),
])
def test_acquisition_uses_event_scalar_without_oracle_or_metadata(
    monkeypatch, probe, command, expected,
):
    class ObservableOnly:
        def observable_log(self):
            return EventLog([OBS])

    def run(config, *, seed, init):
        assert config.accel == (0, -command)
        assert init.y == (47,)
        return ObservableOnly()

    monkeypatch.setattr(active_exit, "run", run)
    reading = active_exit.acquire(-1, -3, probe)
    assert type(reading) is int
    assert reading == expected


@pytest.mark.parametrize("events", [
    [], [OBS, OBS], [replace(OBS, t=20)], [replace(OBS, observable=False)],
    [replace(OBS, subjects=("b0",))],
    [replace(OBS, attrs={"side": "right"})],
    [replace(OBS, attrs={"side": "right", "pos": [60.5, "52"]})],
    [replace(OBS, attrs={"side": "right", "pos": [60.5, float("nan")]})],
])
def test_bad_visible_log_has_no_readout(events):
    assert active_exit.readout(events, "signed") is None


@pytest.mark.parametrize("args", [(1, 3, "future"), (2, 3, "signed"),
                                  (1, 2, "signed"), (True, 3, "signed")])
def test_out_of_catalogue_acquisition_refuses_before_simulation(monkeypatch, args):
    def forbidden(*args, **kwargs):
        pytest.fail("out-of-catalogue input reached the simulator")

    monkeypatch.setattr(active_exit, "run", forbidden)
    with pytest.raises(ValueError):
        active_exit.acquire(*args)


def test_real_signed_and_magnitude_reads_do_not_reveal_the_same_information():
    assert active_exit.acquire(-1, -3, "signed") == -1
    assert active_exit.acquire(1, 3, "signed") == 1
    assert active_exit.acquire(-1, -3, "magnitude") == \
        active_exit.acquire(1, 3, "magnitude") == 7_620_000


def test_frozen_table_matches_measured_scalars_for_every_cell():
    # `signed` is a projection of the frozen scalar onto its sign, so the table
    # is compared after applying the same projection; the raw table has no
    # sign channel and comparing them directly is a category error.
    from psychopomp.active_exit import expected
    for law in (-1, 0, 1):
        for state in (-3, -1, 1, 3):
            for probe in ("passive", "signed", "magnitude"):
                raw = expected(law, state, probe)
                want = (raw > 0) - (raw < 0) if probe == "signed" else raw
                assert want == active_exit.acquire(law, state, probe), (law, state, probe)
