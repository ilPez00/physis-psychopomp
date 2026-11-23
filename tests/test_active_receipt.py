"""R-P1.48 receipts: a decision that someone who did not run the fixture can check.

The readings below are the frozen analytical table of
docs/2026-11-23-PREREG-R-P1.48-active-exit-fixture.md, not simulator output, and
the posteriors are the exact-rational update of `active_design` over that table.
The verifier under test recomputes from the committed plan alone.
"""
import inspect
from fractions import Fraction

from psychopomp import active_design, active_exit
from psychopomp.active_receipt import commit, decide, digest, verify

RIVALS = (-1, 1)
PRIOR = (Fraction(1, 2), Fraction(1, 2))
ROWS = active_exit.rows("signed")
READINGS = sorted({readout for _, readout in ROWS})
CELLS = [
    (law, state, active_exit.expected(law, state, "signed"))
    for law in RIVALS
    for state in active_exit.STATES
]


def predictions() -> dict[int, tuple[Fraction, Fraction]]:
    """The frozen table's posterior per attainable reading, in RIVALS order."""
    table = {}
    for reading in READINGS:
        posterior = active_design.posterior(ROWS, reading)
        table[reading] = tuple(posterior[law] for law in RIVALS)
    return table


def plan(policy: str = "sign-only") -> dict:
    return commit(policy=policy, selected="signed", prior=PRIOR,
                  predictions=predictions())


def test_honest_decision_verifies() -> None:
    assert len(CELLS) == 8
    for law, _state, reading in CELLS:
        receipt = plan()
        decision = decide(receipt, reading)
        assert decision["resolved"] == law
        report = verify(receipt, reading, decision)
        assert report["verdict"] == "VERIFIED", (law, reading, report)


def test_tampered_reading_refused() -> None:
    for _law, _state, reading in CELLS:
        receipt = plan()
        decision = decide(receipt, reading)
        for tampered in (reading + 1, reading - 1):
            report = verify(receipt, tampered, decision)
            assert report["verdict"] == "REFUSED", (reading, tampered, report)


def test_swapped_plan_refused() -> None:
    _law, _state, reading = CELLS[0]
    honest = plan("sign-only")
    other = plan("magnitude-only")
    assert honest["plan_sha256"] != other["plan_sha256"]
    decision = decide(honest, reading)
    report = verify(other, reading, decision)
    assert report["verdict"] == "REFUSED", report


def test_missing_evidence_abstains() -> None:
    receipt = plan()
    decision = decide(receipt, None)
    assert decision["posterior"] == PRIOR
    assert decision["resolved"] is None
    report = verify(receipt, None, decision)
    assert report["verdict"] == "ABSTAIN", report


def test_forged_resolution_refused() -> None:
    receipt = plan()
    decision = decide(receipt, None)
    forged = dict(decision, resolved=-1)
    assert verify(receipt, None, forged)["verdict"] == "REFUSED"
    forged = dict(decision, posterior=(Fraction(1), Fraction(0)))
    assert verify(receipt, None, forged)["verdict"] == "REFUSED"
    _law, _state, reading = CELLS[0]
    supported = decide(receipt, reading)
    forged = dict(supported, resolved=1 if supported["resolved"] == -1 else -1)
    assert verify(receipt, reading, forged)["verdict"] == "REFUSED"


def test_digest_is_stable_and_key_free() -> None:
    record = {"policy": "sign-only", "selected": "signed",
              "prior": [[1, 2], [1, 2]],
              "predictions": {"1": {"-1": [0, 1], "1": [1, 1]},
                              "-1": {"-1": [1, 1], "1": [0, 1]}}}
    reordered = dict(reversed(list(record.items())))
    assert digest(record) == digest(reordered)
    stamped = dict(record, plan_sha256=digest(record))
    assert digest(stamped) == digest(record)
    assert digest(record) != digest(dict(record, policy="magnitude-only"))


def test_verifier_never_imports_the_session_loop() -> None:
    # Property of this module's source, not of the process: asserting on
    # sys.modules made the test order-dependent — any sibling test importing the
    # loop first turned it red without the verifier changing.
    from psychopomp import active_receipt

    assert "active_loop" not in inspect.getsource(active_receipt)
