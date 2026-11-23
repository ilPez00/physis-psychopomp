"""One-probe experiment over public readouts from an inert simulator."""
from __future__ import annotations

import hashlib
import json

from .sim import Init, SimConfig, run

VIEWS = ("left", "right")
LAWS = (-1, 1)


def digest(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _episode(layout, law, view, source):
    if layout not in VIEWS or view not in (*VIEWS, "calibration"):
        raise ValueError("unknown observer or layout")
    if type(law) is not int or law not in (0, *LAWS):
        raise ValueError("unknown simulator law")
    # Visibility changes, not the motion. No kick: kick execution depends on visibility.
    edge = 48 if view == layout else 60
    config = SimConfig(n_balls=1, allow_hidden_init=True, dt=1, steps=12,
                       o2=(0, edge, 0, 99), accel=(0, law / 8))
    return run(config, 0, init=Init((44,), (50,), ((2, 0),)), source=source)


def trajectory(layout: str, law: int, view: str) -> tuple:
    body = _episode(layout, law, view, "counterfactual:v0.1").trajs[0]
    return tuple(zip(body.x, body.y, body.vx, body.vy))


def _read(layout, law, view, source):
    deadline = 9 if view == "calibration" else 3
    exits = [e for e in _episode(layout, law, view, source).observable_log()
             if e.kind == "exit_occ" and e.t <= deadline]
    if len(exits) != 1:
        return None
    eighths = round(8 * (exits[0].attrs["pos"][1] - 50))
    return abs(eighths) if view == "calibration" else eighths


def calibrate(case_id: str, layout: str, law: int) -> dict:
    return {"case": case_id, "layout": layout,
            "magnitude_eighths": _read(layout, law, "calibration", "sim:v0.2")}


def plan(calibration: dict, policy: str) -> dict:
    if (set(calibration) != {"case", "layout", "magnitude_eighths"}
            or not isinstance(calibration["case"], str) or not calibration["case"]
            or calibration["layout"] not in VIEWS
            or type(calibration["magnitude_eighths"]) is not int):
        raise ValueError("invalid calibration record")
    layout = calibration["layout"]
    forecasts = [_read(layout, law, "calibration", "counterfactual:v0.1") for law in (0, *LAWS)]
    measured = calibration["magnitude_eighths"]
    if measured == forecasts[0] or forecasts[1:] != [measured] * 2:
        raise ValueError("calibration does not reject only the nominal model")
    predictions = {view: [_read(layout, law, view, "counterfactual:v0.1") for law in LAWS]
                   for view in VIEWS}
    # For two equiprobable deterministic laws, distinguishable outcomes give exactly one bit.
    gain = {view: int(a != b) for view, (a, b) in predictions.items()}
    if policy not in ("adaptive", "passive", *VIEWS):
        raise ValueError("unknown observation policy")
    choice = max(VIEWS, key=gain.__getitem__) if policy == "adaptive" else policy
    return {"case": calibration["case"], "layout": layout,
            "calibration_sha256": digest(calibration), "calibration_predictions": forecasts,
            "laws": list(LAWS), "prior": [0.5, 0.5], "budget": 1,
            "predictions": predictions, "information_bits": gain, "policy": policy, "choice": choice}


def acquire(commitment: dict, truth: int) -> dict | None:
    choice = commitment["choice"]
    if choice == "passive":
        return None
    if choice not in VIEWS or commitment["budget"] != 1:
        raise ValueError("probe is outside the simulator budget or catalogue")
    return {"case": commitment["case"], "plan_sha256": digest(commitment), "view": choice,
            "source": "sim:v0.2",
            "readout_eighths": _read(commitment["layout"], truth, choice, "sim:v0.2")}


def decide(commitment: dict, observation: dict | None) -> dict:
    choice = commitment["choice"]
    readout = observation["readout_eighths"] if observation is not None else None
    matches = [law for law, y in zip(LAWS, commitment["predictions"].get(choice, [])) if y == readout]
    resolved = matches[0] if type(readout) is int and len(matches) == 1 else None
    posterior = (commitment["prior"] if readout is None else
                 None if resolved is None else [int(law == resolved) for law in LAWS])
    return {"plan_sha256": digest(commitment),
            "observation_sha256": digest(observation) if observation is not None else None,
            "resolved": resolved, "posterior": posterior}
