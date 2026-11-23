import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/loops/results/active-store-replay-20261123"
RIVALS = {-1: "00000000-0000-4000-8000-000000000001",
           1: "00000000-0000-4000-8000-000000000002"}


@pytest.mark.parametrize("case,law", [("law-1-state-3", -1), ("law+1-state-3", 1)])
def test_revision_proposal_binds_exact_row_and_rivals(case, law):
    module = runpy.run_path(str(ROOT / "scripts/active-discovery.py"))
    path = ARTIFACT / "cases" / case
    proposal = module["propose_belief_revision"](path, ARTIFACT / "store.jsonl", RIVALS)
    assert proposal["status"] == "PROPOSED"
    assert proposal["revisions"] == [
        {"hypothesis": RIVALS[-1], "status": "Supported" if law == -1 else "Contradicted"},
        {"hypothesis": RIVALS[1], "status": "Supported" if law == 1 else "Contradicted"},
    ]
    row = [json.loads(line) for line in (ARTIFACT / "store.jsonl").read_text().splitlines()
           if json.loads(line)["seq"] == proposal["evidence"]["store_seq"]][0]
    assert proposal["evidence"]["producer_key"] == row["produced_by"]


def test_missing_evidence_and_duplicate_rivals_emit_no_revision(tmp_path):
    module = runpy.run_path(str(ROOT / "scripts/active-discovery.py"))
    case = ARTIFACT / "cases/law-1-state-3"
    with pytest.raises(OSError):
        module["propose_belief_revision"](case, tmp_path / "missing.jsonl", RIVALS)
    with pytest.raises(ValueError, match="distinct"):
        module["propose_belief_revision"](case, ARTIFACT / "store.jsonl",
                                          {-1: RIVALS[1], 1: RIVALS[1]})
