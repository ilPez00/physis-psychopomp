"""R-P1.48 fixture: reduce one observable exit to the selected sensor scalar."""
from collections.abc import Iterable

from .eventlog import Event
from .sim import Init, SimConfig, run

STATES = (-3, -1, 1, 3)
LAWS = (-1, 0, 1)
COMMAND = {"passive": 0, "signed": 2, "magnitude": 2}
MICRO = 1_000_000

# R-P1.48's frozen analytical table, in millionths of the displacement
# y(21)-50. Single source for the sensors' decision arms and the research
# script; `readout` above never consults it, so comparing the two is a real
# check rather than a tautology.
SHIFTED = {-1: (-7.62, -5.62, -3.62, -1.62), 0: STATES, 1: (1.62, 3.62, 5.62, 7.62)}


def expected(law: int, state: int, probe: str) -> int:
    """The frozen scalar this fixture predicts for one cell (millionths)."""
    command = _command(probe)
    d = state if command == 0 else SHIFTED[law][STATES.index(state)]
    value = round(d * MICRO)
    return abs(value) if probe == "magnitude" else value


def rows(probe: str) -> list[tuple[int, int]]:
    """(law, scalar) over the two rivals and four reset states."""
    return [(law, expected(law, state, probe)) for law in (-1, 1) for state in STATES]


def _command(probe: str) -> int:
    if type(probe) is not str or probe not in COMMAND:
        raise ValueError("probe is outside the exit fixture catalogue")
    return COMMAND[probe]


def readout(events: Iterable[Event], probe: str) -> int | None:
    """Expose one scalar only; no readout if the visible log is not well formed.

    The well-formedness test is **fixture-specific** (one right-side exit at
    step 21). A different world needs its own constants before this sensor can
    read it; it is not a general exit parser.
    """
    _command(probe)
    rows = tuple(events)
    if len(rows) != 1:
        return None
    event = rows[0]
    if (not event.observable or event.kind != "exit_occ" or event.t != 21
            or event.subjects != ("ball",) or event.attrs.get("side") != "right"):
        return None
    pos = event.attrs.get("pos")
    if (not isinstance(pos, (list, tuple)) or len(pos) != 2
            or any(type(p) not in (int, float) or not 1 <= p <= 99 for p in pos)):
        return None
    displacement = round((pos[1] - 50) * MICRO)
    if probe == "magnitude":
        return abs(displacement)
    if probe == "signed":
        return (displacement > 0) - (displacement < 0)
    return displacement


def _run_case(law: int, state: int, command: int):
    if (type(law) is not int or law not in LAWS
            or type(state) is not int or state not in STATES
            or type(command) is not int or command not in (0, 2)):
        raise ValueError("law, reset state or command is outside the exit fixture")
    config = SimConfig(o=(40, 60, 35, 65), o2=None, n_balls=1, dt=0.1, steps=24,
                       visual_radius=0.0, allow_hidden_init=True, accel=(0, law * command))
    return run(config, seed=0, init=Init(x=(50,), y=(50 + state,), v=((5, 0),)))


def acquire(law: int, state: int, probe: str) -> int | None:
    """Run this fixture once; the caller receives only the chosen scalar."""
    return readout(_run_case(law, state, _command(probe)).observable_log(), probe)
