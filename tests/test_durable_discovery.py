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

    def check_seal(*args):
        assert (case / "plan.json").is_file()
        assert not (case / "decision.json").exists()
        return acquire(*args)

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
