from psychopomp.camera import CameraView, degrade, drop_aux, jitter, quantize
from psychopomp.epec import summarize
from psychopomp.fixtures import OFF_AXIS, PASS_CFG, STRAIGHT
from psychopomp.perspective import random_frame, transform_observable
from psychopomp.sim import run


def ep_contact():
    return run(PASS_CFG, 0, init=OFF_AXIS)


def ep_straight():
    return run(PASS_CFG, 0, init=STRAIGHT)


def test_quantize_lands_on_grid():
    log = quantize(ep_contact().observable_log(), 1.0)
    for e in log:
        for key in ("pos", "v"):
            if e.attrs.get(key) is not None:
                for component in e.attrs[key]:
                    assert abs(component - round(component)) < 1e-9
        for p in e.attrs.get("track") or []:
            for component in p:
                assert abs(component - round(component)) < 1e-9


def test_jitter_bounded_and_deterministic():
    log = ep_contact().observable_log()
    a = jitter(log, 0.5, seed=3)
    b = jitter(log, 0.5, seed=3)
    assert [e.attrs for e in a] == [e.attrs for e in b]
    for orig, moved in zip(log, a):
        if orig.attrs.get("pos") is not None:
            for i in (0, 1):
                assert abs(moved.attrs["pos"][i] - orig.attrs["pos"][i]) <= 0.25 + 1e-6


def test_drop_aux_preserves_ec_enumeration():
    for ep in (ep_contact(), ep_straight()):
        base = summarize(ep.observable_log())
        dropped = drop_aux(ep.observable_log(), 1.0, seed=1)
        got = summarize(dropped)
        assert got["n_worlds"] == base["n_worlds"]
        assert got["contact_required"] == base["contact_required"]
        assert not [e for e in dropped if e.kind in ("wall_bounce", "kick")]


def test_degrade_composition_and_delegation():
    ep = ep_contact()
    view = CameraView(ep, degrade(transform_observable(ep, random_frame(2)), quantize_unit=1.0, jitter_magnitude=0.5))
    assert view.observable_log() is not ep.observable_log()
    assert view.config is ep.config  # CameraView delegates
    assert all(s == "ball" for e in view.observable_log() for s in e.subjects)


def test_oracle_untouched_by_camera():
    ep = ep_contact()
    before = [e.attrs for e in ep.oracle_log()]
    degrade(ep.observable_log(), quantize_unit=1.0, jitter_magnitude=1.0, drop_rate=1.0, seed=0)
    assert [e.attrs for e in ep.oracle_log()] == before
