"""E4: check a proposal against the fold before anything is declared.

Order matters. `psychopomp.graph_patch` proposes; this module asks Physis what it
already believes; only a human or an authorised caller ever writes. The verdicts
are `physis claim`'s own exit codes, and they are not interchangeable:

* `VERIFIED` — the fold already knows this edge, so the proposal is redundant;
* `NO_EVIDENCE` — nothing cites it. **Not** a refutation;
* `REFUTED` — the fold contradicts it. Keep the proposal and say so.

Nothing here upgrades a proposal to a fact. A gate that returns `VERIFIED` means
"already observed", never "your prediction was right".
"""
from __future__ import annotations

import copy
import subprocess

VERDICTS = {0: "VERIFIED", 1: "REFUTED", 2: "NO_EVIDENCE"}


def _run(world: str, source: str, predicate: str, target: str) -> tuple[int, str]:
    out = subprocess.run(["physis", "claim", source, predicate, target, "--path", world],
                         capture_output=True, text=True, timeout=60)
    first = (out.stdout + out.stderr).strip().splitlines()
    return out.returncode, first[0] if first else ""


def check(edge: tuple[str, str, str], world: str) -> dict:
    rc, line = _run(world, *edge)
    if rc not in VERDICTS:
        # An exit code outside the documented three is a broken gate, not a
        # verdict; fail closed rather than guessing what it meant.
        raise ValueError(f"physis claim returned undocumented exit code {rc}: {line}")
    return {"edge": list(edge), "verdict": VERDICTS[rc], "rc": rc, "reason": line}


def gate(plan: dict, world: str) -> dict:
    """Annotate a decoder plan with fold verdicts; never apply, never promote."""
    gated = copy.deepcopy(plan)
    kept, already_known, checks = [], [], []
    for op in gated["operations"]:
        if op.get("op") != "propose_edge":
            kept.append(op)
            continue
        edge = (op["source"], op["predicate"], op["target"])
        result = check(edge, world)
        checks.append(result)
        if result["verdict"] == "VERIFIED":
            already_known.append(result)
            continue
        if result["verdict"] == "REFUTED":
            op["contradicted_by_fold"] = True
        else:
            op["unverified_by_fold"] = True
        kept.append(op)
    gated["operations"] = kept
    gated["admission"] = {"checks": checks, "already_known": already_known,
                          "world": world, "applied": False}
    return gated
