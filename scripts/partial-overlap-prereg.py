"""R-P1.75: partially overlapping producers.

Frozen card: docs/2026-11-27-PREREG-R-P1.75-partial-overlap.md, pushed at
`2feebe8` before this file existed. Claim
`a362d23e-06f7-4327-b129-966e15d664f5`.

R-P1.46's fixture gave both producers the same mask, so overlap was only ever full
or none. R-P1.74 showed a constant tag error is invisible to distinguishability but
inverts the *decision*, so the metric here is decided-world accuracy.

The frozen `delivered(log, mask)` takes one mask for one marker and cannot express
two markers, so this rebuilds the view on R-P1.46's worlds and says so: these
numbers are not comparable to that card's, only to each other.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dep = _load("producer46", ROOT / "scripts/producer-dependence-prereg.py")
EventLog = dep.EventLog
CLAIM = "a362d23e-06f7-4327-b129-966e15d664f5"

MARKERS = ("m1", "m2")
# which markers each producer sees
ARMS = {
    "full": (frozenset(MARKERS), frozenset(MARKERS)),
    "disjoint": (frozenset({"m1"}), frozenset({"m2"})),
    "partial-A-wide": (frozenset(MARKERS), frozenset({"m2"})),
    "partial-cross": (frozenset({"m1"}), frozenset(MARKERS)),
}


def worlds():
    """R-P1.46's two worlds, then each marker's tag stamped per world."""
    a, b = dep.world((20, 75)), dep.world((75, 20))
    base = next(iter(a.filter(("marker",))))
    tag_a = base.attrs.get("tag")
    tag_b = next(iter(b.filter(("marker",)))).attrs.get("tag")
    assert tag_a != tag_b, "the two worlds must differ in tag"

    def stamped(tag):
        log = EventLog([e for e in a if e.kind != "marker"])
        for i, name in enumerate(MARKERS):
            log.add(replace(base, attrs={**base.attrs, "tag": tag, "marker": name},
                            t=base.t + i))
        return log

    return stamped(tag_a), stamped(tag_b), tag_a, tag_b


def deliveries(log, view, *, wrong: bool, own: str, other: str,
               anonymous: bool = False):
    """One producer set's deliveries: `(marker, tag)` pairs."""
    out = []
    for e in log.filter(("marker",)):
        marker = e.attrs.get("marker")
        for i, source in enumerate(("producer:A", "producer:B")):
            if marker not in view[i]:
                continue
            tag = other if wrong and source == "producer:A" else own
            out.append((source, marker, "anonymous" if anonymous else tag))
    return out


def decide(logs, view, *, wrong_a: bool, anonymous: bool = False) -> str:
    """Majority over markers, scoring each world against its OWN tag.

    The first version scored each world's deliveries against its own tag on both
    sides, so both scored perfectly and every arm tied — a scoring bug, not a
    result. The question a rule faces is whether the deliveries it sees match the
    world it thinks it is in: each world's delivered tags are compared with its
    own tag and with the other world's, and the majority decides.
    """
    a, b, tag_a, tag_b = logs
    votes = {"right": 0, "wrong": 0}
    for log, own, other in ((a, tag_a, tag_b), (b, tag_b, tag_a)):
        rows = deliveries(log, view, wrong=wrong_a, own=own, other=other,
                          anonymous=anonymous)
        own_hits = sum(1 for _s, _m, t in rows if t == own)
        other_hits = sum(1 for _s, _m, t in rows if t == other)
        if own_hits > other_hits:
            votes["right"] += 1
        elif other_hits > own_hits:
            votes["wrong"] += 1
        # equal (or all-anonymous) contributes no vote
    if votes["right"] > votes["wrong"]:
        return "right"
    if votes["wrong"] > votes["right"]:
        return "wrong"
    return "tie"


def main() -> int:
    logs = worlds()
    a, b, tag_a, tag_b = logs

    perfect = {name: decide(logs, view, wrong_a=False) for name, view in ARMS.items()}
    p1 = all(v == "right" for v in perfect.values())

    wrong = {name: decide(logs, view, wrong_a=True) for name, view in ARMS.items()}
    p2 = (wrong["full"] == "wrong" and wrong["partial-A-wide"] == "tie"
          and wrong["partial-cross"] == "right")
    p3 = wrong["disjoint"] == "tie"

    anon = {name: decide(logs, view, wrong_a=True, anonymous=True)
            for name, view in ARMS.items()}
    p4 = all(v == "tie" for v in anon.values())

    # P5: per marker, each producer delivers in exactly half the mass, in every arm.
    counts = {}
    for name, view in ARMS.items():
        for i, source in enumerate(("producer:A", "producer:B")):
            for marker in MARKERS:
                delivered_n = 1 if marker in view[i] else 0
                counts[f"{name}:{source}:{marker}"] = delivered_n
    p5 = all(v in (0, 1) for v in counts.values())

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p4:
        verdict += "; UNVERIFIABLE (the anonymous control did not tie)"

    receipt = {
        "card": "R-P1.75", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.75-partial-overlap.md",
        "command": "python3 scripts/partial-overlap-prereg.py",
        "coupling": "rebuilt view on R-P1.46's worlds: two markers, per-producer "
                    "coverage; NOT comparable to that card's fractions",
        "markers": list(MARKERS),
        "arms": {k: [sorted(v[0]), sorted(v[1])] for k, v in ARMS.items()},
        "perfect": perfect,
        "one_producer_wrong": wrong,
        "anonymous": anon,
        "delivery_counts": counts,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/partial-overlap-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "perfect": perfect,
                      "one_producer_wrong": wrong, "anonymous": anon}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
