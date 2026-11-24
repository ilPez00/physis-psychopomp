import json
import runpy
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/turnover-store-replay.py"
ARTIFACT = SCRIPT.parents[1] / "research/loops/results/turnover-store-replay-20261124"


def test_store_replay_uses_bound_rows_and_keeps_passive_abstention(tmp_path):
    script = runpy.run_path(str(SCRIPT))
    script["record"](tmp_path)
    rows = []
    for seq, line in enumerate((tmp_path / "executed.jsonl").read_text().splitlines()):
        record = json.loads(line)
        rows.append({"seq": seq, "subject": record["subject"], "source": "psychopomp",
                     "produced_by": f"psychopomp:{record['subject']}#0",
                     "props": {"psychopomp_schema": record["schema"],
                               "psychopomp_kind": record["kind"],
                               "psychopomp_evidence": record["evidence"],
                               "at_seconds": str(record["at"]),
                               "psychopomp_props": json.dumps(record["props"]),
                               "psychopomp_provenance": json.dumps(record["provenance"])}})
    result = script["replay"](tmp_path, rows)
    assert [item["verdict"] for item in result].count("VERIFIED") == 4
    assert [item["verdict"] for item in result].count("ABSTAIN") == 4
    assert sorted(item["store_seq"] for item in result) == list(range(8))
    with pytest.raises(ValueError, match="one stored row"):
        script["replay"](tmp_path, rows[:-1])
    with pytest.raises(ValueError, match="one stored row"):
        script["replay"](tmp_path, rows + [rows[0]])
    rows[0]["props"]["psychopomp_props"] = json.dumps({"loads": [6, 4], "tick": 4, "dt": 1.0})
    with pytest.raises(ValueError, match="payload"):
        script["replay"](tmp_path, rows)


def test_saved_store_replays_both_roles_without_simulation(monkeypatch):
    from psychopomp import turnover_evidence

    def forbidden(*args):
        pytest.fail("replay executed a simulation")

    monkeypatch.setattr(turnover_evidence, "execute", forbidden)
    script = runpy.run_path(str(SCRIPT))
    rows = [json.loads(line) for line in (ARTIFACT / "store.jsonl").read_text().splitlines()]
    actual = script["replay"](ARTIFACT / "cases", rows)
    assert actual == json.loads((ARTIFACT / "replay.json").read_text())
    assert {(r["target"], r["resolved"]) for r in actual if r["verdict"] == "VERIFIED"} == {
        (1, "feedback"), (1, "replay"), (2, "feedback"), (2, "replay"),
    }
    assert {(target, sum(r["target"] == target and r["verdict"] == "ABSTAIN"
                        and r["resolved"] is None for r in actual))
            for target in (1, 2)} == {(1, 2), (2, 2)}
