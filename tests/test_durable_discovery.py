import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from psychopomp import active_exit


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "active-discovery.py"


def test_durable_replay_checks_observed_event_not_a_self_consistent_decision(tmp_path, monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    case = tmp_path / "case"
    acquire = active_exit.acquire_events

    def check_seal(*args, **kwargs):
        assert (case / "plan.json").is_file()
        assert not (case / "decision.json").exists()
        return acquire(*args, **kwargs)

    monkeypatch.setattr(active_exit, "acquire_events", check_seal)
    _, verdict = module["diagnose_and_verify"](-1, -3, "adaptive", case)
    assert verdict == "VERIFIED"
    result = subprocess.run([sys.executable, str(SCRIPT), "--replay", str(case)],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "VERIFIED"
    monkeypatch.setattr(active_exit, "acquire_events", lambda *args: pytest.fail("replay simulated"))

    decision = case / "decision.json"
    forged = json.loads(decision.read_text())
    forged.update(reading=1, resolved=1, posterior=[[0, 1], [1, 1]])
    decision.write_text(json.dumps(forged))
    assert module["replay"](case) == "REFUSED"


def test_replay_refuses_rehashed_oracle_event(tmp_path):
    module = runpy.run_path(str(SCRIPT))
    case = tmp_path / "case"
    module["diagnose_and_verify"](1, 3, "adaptive", case)
    path = case / "events.jsonl"
    event = json.loads(path.read_bytes())
    event["observable"] = False
    path.write_text(json.dumps(event) + "\n")
    path = case / "decision.json"
    decision = json.loads(path.read_text())
    decision.update(reading=None, posterior=[[1, 2], [1, 2]], resolved=None,
                    events_sha256=hashlib.sha256((case / "events.jsonl").read_bytes()).hexdigest())
    path.write_text(json.dumps(decision))
    assert module["replay"](case) == "REFUSED"


def test_export_names_the_executed_episode_without_reacquiring(tmp_path, monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    cases = [tmp_path / "a", tmp_path / "b"]
    for index, case in enumerate(cases, 50):
        module["diagnose_and_verify"](-1, -3, "adaptive", case, episode=index)
    monkeypatch.setattr(active_exit, "acquire_events", lambda *args: pytest.fail("export simulated"))
    records = [module["export_case"](case) for case in cases]
    assert [row["subject"] for row in records] == ["episode:0:50", "episode:0:51"]
    for case, row in zip(cases, records):
        event = json.loads((case / "events.jsonl").read_text())
        assert row["provenance"] == event["provenance"]
        assert row["props"] == event["attrs"]
        assert row["at"] == 2.1
        assert row["evidence"] == "OBSERVED"


def test_store_replay_requires_exact_producer_key_and_payload(tmp_path):
    module = runpy.run_path(str(SCRIPT))
    case = tmp_path / "case"
    module["diagnose_and_verify"](-1, -3, "adaptive", case, episode=50)
    record = module["export_case"](case)
    log = tmp_path / "observations.jsonl"
    row = {"seq": 17, "source": "psychopomp", "subject": record["subject"],
           "produced_by": "psychopomp:episode:0:50#0",
           "props": {"psychopomp_schema": record["schema"],
                     "psychopomp_evidence": record["evidence"],
                     "psychopomp_kind": record["kind"], "at_seconds": "2.1",
                     "psychopomp_props": json.dumps(record["props"]),
                     "psychopomp_provenance": json.dumps(record["provenance"])}}
    log.write_text(json.dumps(row) + "\n")
    assert module["replay_store"](case, log) == ("VERIFIED", 17)
    log.write_text((json.dumps(row) + "\n") * 2)
    with pytest.raises(ValueError, match="found 2"):
        module["replay_store"](case, log)
    row["produced_by"] = "other-producer:episode:0:50#0"
    log.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="found 0"):
        module["replay_store"](case, log)
    row["produced_by"] = "psychopomp:episode:0:50#0"
    row["props"]["psychopomp_props"] = json.dumps({**record["props"], "pos": [60.5, 57.62]})
    log.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="payload"):
        module["replay_store"](case, log)
