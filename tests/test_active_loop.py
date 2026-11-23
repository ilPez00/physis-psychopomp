"""R-P1.48 bounded loop: one diagnostic action, then a refusal."""
from fractions import Fraction

import pytest

from psychopomp import active_loop
from psychopomp.active_loop import BudgetExhausted, Session

PRIOR = (Fraction(1, 2), Fraction(1, 2))
CELLS = [(law, state) for law in (-1, 1) for state in (-3, -1, 1, 3)]


def counted(monkeypatch, reading=None):
    calls = []

    def fake(law, state, probe):
        calls.append((law, state, probe))
        return reading

    monkeypatch.setattr(active_loop, "acquire", fake)
    return calls


def test_adaptive_resolves_both_laws_and_all_states():
    for law, state in CELLS:
        out = Session().diagnose(law, state)
        assert out["selected"] == "signed"
        assert out["resolved"] == law, (law, state, out)
        assert out["posterior"] in ((Fraction(1), Fraction(0)), (Fraction(0), Fraction(1)))


def test_passive_and_shuffled_never_resolve():
    for law, state in CELLS:
        for policy in ("passive", "shuffled"):
            out = Session().diagnose(law, state, policy=policy)
            assert out["resolved"] is None, (policy, law, state, out)
            assert out["posterior"] == PRIOR, (policy, law, state, out)


def test_malformed_log_abstains(monkeypatch):
    counted(monkeypatch, reading=None)
    out = Session().diagnose(-1, -3)
    assert out["reading"] is None
    assert out["posterior"] == PRIOR
    assert out["resolved"] is None


def test_second_diagnostic_is_refused(monkeypatch):
    calls = counted(monkeypatch, reading=-1)
    session = Session()
    session.diagnose(-1, -3)
    assert session.remaining == 0
    with pytest.raises(BudgetExhausted):
        session.diagnose(-1, -3)
    assert len(calls) == 1, "the refused call reached the simulator"


def test_unknown_policy_refuses_before_simulation(monkeypatch):
    calls = counted(monkeypatch, reading=-1)
    with pytest.raises(ValueError):
        Session().diagnose(-1, -3, policy="magnitude")
    assert calls == []


def test_selected_action_is_committed_before_acquisition(monkeypatch):
    order = []
    monkeypatch.setattr(active_loop, "acquire",
                        lambda law, state, probe: order.append(("acquire", probe)) or -1)
    out = Session().diagnose(-1, -3, before_acquire=lambda probe: order.append(("commit", probe)))
    assert order == [("commit", "signed"), ("acquire", "signed")]
    assert out["resolved"] == -1


def test_failed_commit_does_not_acquire_or_spend_budget(monkeypatch):
    calls = counted(monkeypatch, reading=-1)
    session = Session()

    def fail(_):
        raise RuntimeError("could not seal")

    with pytest.raises(RuntimeError, match="could not seal"):
        session.diagnose(-1, -3, before_acquire=fail)
    assert calls == []
    assert session.remaining == 1
