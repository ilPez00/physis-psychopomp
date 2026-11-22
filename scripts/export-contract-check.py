"""Check the producer side of the integration contract (docs/INTEGRATION-CONTRACT.md).

Every guarantee that document makes about `psychopomp.observation/1` is asserted
here against a real export, so the contract cannot drift from the code. The consumer
side is absent upstream; this is the half that can be owned locally.

Usage:
  .venv/bin/python scripts/export-contract-check.py           # check
  .venv/bin/python scripts/export-contract-check.py --write   # refresh the sample
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from psychopomp.export import SCHEMA, observation_records
from psychopomp.interventions import COUNTERFACTUAL_SOURCE
from psychopomp.sim import Init, Kick, SimConfig, run

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "research" / "fixtures" / "observation-v1.sample.jsonl"
REQUIRED = {"schema", "subject", "kind", "at", "props", "provenance", "evidence", "seq"}
PROVENANCE = {"source", "config_sha256", "seed", "episode"}
ORACLE_ONLY = {"kick_skipped"}


def episode(swapped: bool = False, marker: bool = False, kick: bool = True):
    a = ((20.0, 45.0), (3.0, 0.0))
    b = ((80.0, 51.0), (-3.0, 0.0))
    if swapped:
        a, b = b, a
    cfg = SimConfig(steps=120, o=(40.0, 60.0, 35.0, 65.0),
                    o2=(46.0, 54.0, 35.0, 65.0), identity_marker=marker)
    # A kick is tied to a body, so swapping bodies makes a *different world*; the
    # relabelling check must use a kick-free episode (see the card's own test).
    kicks = (Kick(20, 0, (0.0, 1.5)),) if kick else ()
    return run(cfg, 0, episode=0,
               init=Init(x=(a[0][0], b[0][0]), y=(a[0][1], b[0][1]), v=(a[1], b[1])),
               kicks=kicks)


def lines(records) -> list:
    return [json.dumps(r, sort_keys=True) for r in records]


def main() -> int:
    records = observation_records(episode())
    failures = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    check("records exist", len(records) > 0, f"{len(records)} records")
    check("schema string", all(r["schema"] == SCHEMA for r in records), SCHEMA)
    check("required keys", all(set(r) == REQUIRED for r in records))
    check("provenance keys", all(set(r["provenance"]) == PROVENANCE for r in records))
    check("identity-free subjects",
          all("b0" not in r["subject"] and "b1" not in r["subject"] for r in records))
    check("no oracle-only kinds", all(r["kind"] not in ORACLE_ONLY for r in records))
    check("no oracle fields",
          all(not ({"hidden", "oracle", "ball"} & set(r["props"])) for r in records))

    keys = [(r["at"], r["kind"], json.dumps(r["props"], sort_keys=True), r["subject"])
            for r in records]
    check("canonical order", keys == sorted(keys))
    check("seq matches order", [r["seq"] for r in records] == list(range(len(records))))
    check("evidence is OBSERVED", all(r["evidence"] == "OBSERVED" for r in records))

    again = observation_records(episode())
    check("deterministic export", lines(records) == lines(again))

    swapped = observation_records(episode(swapped=True, kick=False))
    plain = observation_records(episode(kick=False))
    check("relabelling-invariant export (kick-free)", lines(plain) == lines(swapped),
          "two identical bodies, labels exchanged")
    check("a kick is identity-bearing", lines(records) != lines(swapped),
          "kicking body 0 is not the same world as kicking body 1")

    marked = observation_records(episode(marker=True))
    check("marker records carry a tag only",
          all("tag" in r["props"] for r in marked if r["kind"] == "marker"))

    try:
        bad = run(SimConfig(steps=60, o=(40.0, 60.0, 35.0, 65.0)), 0,
                  episode=0, init=Init(x=(20.0, 80.0), y=(45.0, 51.0),
                                       v=((3.0, 0.0), (-3.0, 0.0))),
                  kicks=(Kick(20, 0, (0.0, 1.5)),), source=COUNTERFACTUAL_SOURCE)
        observation_records(bad)
        check("counterfactual refused", False, "export accepted a counterfactual")
    except ValueError:
        check("counterfactual refused", True)

    if "--write" in sys.argv:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text("\n".join(lines(records)) + "\n")
        print(f"wrote {FIXTURE.relative_to(ROOT)} ({len(records)} records)")

    print()
    if failures:
        print(f"export contract: FAIL ({len(failures)} checks)")
        return 1
    print(f"export contract: PASS ({len(records)} records verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
