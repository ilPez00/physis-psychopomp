"""Independent finite-fixture verifier: no simulator or controller imports."""
import hashlib
import json


def _digest(record):
    data = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def verify(calibration, commitment, observation, decision):
    """Return the derived law or None. Raise on invalid record relationships."""
    case, layout = calibration.get("case"), calibration.get("layout")
    if (not isinstance(case, str) or not case or layout not in ("left", "right")
            or _digest(calibration) != _digest({"case": case, "layout": layout, "magnitude_eighths": 45})):
        raise ValueError("calibration does not match the fixture")
    other = "right" if layout == "left" else "left"
    # Analytic sum of semi-implicit unit steps: 1+…+9=45, 1+…+3=6.
    policy = commitment.get("policy")
    if policy not in ("adaptive", "passive", "left", "right"):
        raise ValueError("unknown commitment policy")
    choice = layout if policy == "adaptive" else policy
    expected = {
        "case": case, "layout": layout, "calibration_sha256": _digest(calibration),
        "calibration_predictions": [0, 45, 45], "laws": [-1, 1], "prior": [0.5, 0.5],
        "budget": 1, "predictions": {layout: [-6, 6], other: [None, None]},
        "information_bits": {layout: 1, other: 0}, "policy": policy, "choice": choice,
    }
    plan_hash = _digest(expected)
    if _digest(commitment) != plan_hash:
        raise ValueError("commitment does not match independent predictions")

    resolved, posterior = None, [0.5, 0.5]
    if observation is not None:
        readout = observation.get("readout_eighths")
        acquisition = {"case": case, "plan_sha256": plan_hash, "view": choice,
                       "source": "sim:v0.2", "readout_eighths": readout}
        if (choice == "passive" or _digest(observation) != _digest(acquisition)
                or (readout is not None and type(readout) is not int)):
            raise ValueError("acquisition not bound to committed experiment")
        if readout is not None:
            posterior = None
            if choice == layout and readout in (-6, 6):
                resolved = -1 if readout < 0 else 1
                posterior = [1, 0] if resolved == -1 else [0, 1]

    derived = {"plan_sha256": plan_hash,
               "observation_sha256": _digest(observation) if observation is not None else None,
               "resolved": resolved, "posterior": posterior}
    if _digest(decision) != _digest(derived):
        raise ValueError("decision not supported by acquired evidence")
    return resolved
