"""The turnover exporter must not hand a consumer the hypothesis it is testing."""
import json

import pytest

from psychopomp import export
from psychopomp.turnover import OBSERVE, run


def test_records_are_schema_valid_and_carry_the_observed_window():
    records = export.turnover_records(run("feedback", 1, 0), episode=7)
    assert [row["props"]["tick"] for row in records] == list(OBSERVE)
    for seq, row in enumerate(records):
        assert row["schema"] == export.SCHEMA
        assert row["subject"] == "episode:0:7"
        assert row["kind"] == "loads"
        assert row["evidence"] == "OBSERVED"
        assert row["seq"] == seq
        assert row["at"] == float(OBSERVE[seq]) * export.TURNOVER_DT
        assert row["props"]["dt"] == export.TURNOVER_DT
        assert len(row["props"]["loads"]) == 2


def test_the_arm_never_reaches_the_record():
    for arm in ("feedback", "open-loop"):
        text = "".join(json.dumps(row, sort_keys=True)
                       for row in export.turnover_records(run(arm, 1, 2), episode=1))
        assert arm not in text, "the hypothesis under test leaked into its own evidence"
        assert "components" not in text and "replaced" not in text


def test_an_uninformative_observation_cannot_tell_the_rivals_apart():
    # R-P1.50: on the undisturbed world both arms predict identical loads, so the
    # passive reading buys no discrimination. The export must preserve that.
    feedback = export.turnover_records(run("feedback", 1, 0), episode=1)
    open_loop = export.turnover_records(run("open-loop", 1, 0), episode=1)
    assert feedback == open_loop


def test_a_post_disturbance_observation_does_separate_them():
    feedback = export.turnover_records(run("feedback", 1, 2), episode=1)
    nominal = run("feedback", 1, 0).transfers
    open_loop = export.turnover_records(
        run("open-loop", 1, 2, nominal=nominal), episode=1)
    assert feedback != open_loop


def test_a_tick_outside_the_episode_is_refused():
    with pytest.raises(ValueError, match="outside"):
        export.turnover_records(run("feedback", 1, 0), episode=1, ticks=(1, 99))


def test_config_digest_identifies_the_fixture_not_the_episode():
    # The provenance a consumer may read must not disclose the target, the
    # perturbation or the arm — those are the episode and its hidden variable.
    digests = {
        export.turnover_records(run("feedback", 1, 0), episode=1)[0]["provenance"]["config_sha256"],
        export.turnover_records(run("open-loop", 1, 2), episode=1)[0]["provenance"]["config_sha256"],
        export.turnover_records(run("feedback", 2, 1), episode=99)[0]["provenance"]["config_sha256"],
    }
    assert len(digests) == 1
    assert len(digests.pop()) == 64
