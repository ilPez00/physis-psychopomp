"""E3 demo: the turnover pair as two graph worlds, decoded into proposals.

Declared worlds, one observed snapshot, no applied edits. The point is the shape:
a disputed edge becomes two `HYPOTHESIZED` proposals **plus** the experiment that
would settle it, and the decoder promotes nothing.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.graph_patch import decode, to_json
from psychopomp.physis_snapshot import Snapshot

REGULATES = ("role:1", "REGULATES", "role:2")


def main() -> int:
    snapshot = Snapshot(entities={"role:1": "role", "role:2": "role"},
                        edges=[], evidence_seqs=[11, 12], pin="sha256:turnover-demo")
    worlds = [set(), {REGULATES}]          # replay asserts nothing; feedback asserts a rule
    experiments = {"passive": 0.0, "perturbed": 1.0}
    plan = decode(snapshot, worlds, experiments=experiments)
    # A second, order-shuffled decode: determinism means two runs agree, not that
    # a string equals itself.
    again = to_json(decode(snapshot, list(reversed(worlds)), experiments=experiments))

    proposals = [op for op in plan["operations"] if op["op"] == "propose_edge"]
    requests = [op for op in plan["operations"] if op["op"] == "request_evidence"]
    ok = (len(proposals) == 1
          and proposals[0]["status"] == "HYPOTHESIZED"
          and proposals[0]["agreement"] == "disputed"
          and len(requests) == 1
          and requests[0]["experiments"] == ["perturbed"]
          and requests[0]["predicted_information_bits"] == 1.0
          and plan["base_revision"] == "sha256:turnover-demo"
          and plan["verifier"]["status"] == "NOT_EVALUATED"
          and to_json(plan) == again)
    print(json.dumps(json.loads(to_json(plan)), indent=2, sort_keys=True))
    print()
    print(f"operations: {[op['op'] for op in plan['operations']]}; "
          f"nothing applied; two decodes agree: {to_json(plan) == again}")
    print(f"graph patch demo: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
