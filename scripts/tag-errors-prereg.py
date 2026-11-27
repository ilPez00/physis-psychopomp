"""R-P1.74: incorrect tags at matched delivery marginals.

Frozen card: docs/2026-11-27-PREREG-R-P1.74-tag-errors.md, pushed at `65fcb42`
before this file existed. Claim `8ad30edd-8bab-47ad-b9c8-f76b3905290a`.

R-P1.46's fixture is imported rather than reimplemented: same worlds, same masks,
same `delivered(...)`. The only new thing is **which tag a producer carries**. So
every arm keeps delivery counts and sources identical and only payload varies —
"matched marginals" is then a thing the receipt can check rather than assert.
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
MASKS = dep.MASKS
ARMS = dep.ARMS

CLAIM = "8ad30edd-8bab-47ad-b9c8-f76b3905290a"


def worlds():
    return dep.world((20, 75)), dep.world((75, 20))


def delivered_with_error(logs, index: int, mask, *, wrong: tuple[bool, bool],
                         anonymous: bool = False):
    """`dep.delivered` with per-producer tag error.

    `wrong[i]` says producer i delivers the *other* world's tag for every delivery
    it makes. A constant offset, not noise: that is what W1/W2 test.
    """
    log = logs[index]
    other = logs[1 - index]
    out = EventLog([e for e in log if e.kind != "marker"])
    own_tag = next(iter(log.filter(("marker",)))).attrs.get("tag")
    other_tag = next(iter(other.filter(("marker",)))).attrs.get("tag")
    assert own_tag != other_tag, "the two worlds must differ in tag"
    for e in log.filter(("marker",)):
        for i, source in enumerate(("producer:A", "producer:B")):
            if not mask[i]:
                continue
            tag = other_tag if wrong[i] else own_tag
            attrs = {**e.attrs, "tag": "anonymous" if anonymous else tag}
            out.add(replace(e, attrs=attrs,
                            provenance=replace(e.provenance, source=source)))
    return list(out)


def resolves(logs, mask, wrong, anonymous=False) -> bool:
    a = delivered_with_error(logs, 0, mask, wrong=wrong, anonymous=anonymous)
    b = delivered_with_error(logs, 1, mask, wrong=wrong, anonymous=anonymous)
    return a != b


def decides_world(logs, mask, wrong) -> str:
    """Which world a tag-matching rule would pick, given the delivered tags."""
    a = delivered_with_error(logs, 0, mask, wrong=wrong)
    b = delivered_with_error(logs, 1, mask, wrong=wrong)
    a_tags = [e.attrs.get("tag") for e in a if e.kind == "marker"]
    return "world0" if a_tags and all(t == a_tags[0] for t in a_tags) else "mixed"


def arm_fractions(logs, wrong_for, *, random_wrong: bool = False) -> dict:
    out = {}
    for name, masks in ARMS.items():
        vals = []
        for mask in masks:
            wrong = wrong_for(name, mask)
            if random_wrong:
                # A is wrong with probability 1/2 per delivery; the other world's
                # tag is a single value, so the two equiprobable cases are
                # "all A deliveries wrong" and "none", averaged at 1/2 each only
                # if the mask delivers once — stated as measured, not assumed.
                vals.append(Fraction(1, 2) * resolves(logs, mask, (False, False))
                            + Fraction(1, 2) * resolves(logs, mask, (True, False)))
            else:
                vals.append(1 if resolves(logs, mask, wrong) else 0)
        out[name] = sum(vals, Fraction(0)) / len(vals)
    return out


def counts_and_sources(logs, mask, wrong) -> dict:
    """Delivery counts and sources, which must not move with the payload."""
    rows = []
    for i in (0, 1):
        d = delivered_with_error(logs, i, mask, wrong=wrong)
        rows.append({
            "world": i,
            "markers": sum(1 for e in d if e.kind == "marker"),
            "sources": sorted({e.provenance.source for e in d if e.kind == "marker"}),
        })
    return rows


def main() -> int:
    logs = worlds()

    # P1: the anchor, perfect content.
    anchor = arm_fractions(logs, lambda name, mask: (False, False))
    p1 = anchor == {"shared": Fraction(1, 2), "independent": Fraction(3, 4),
                    "complementary": Fraction(1)}

    # W1/P2: one producer systematically wrong.
    w1 = arm_fractions(logs, lambda name, mask: (True, False))
    p2 = all(v == 1 for v in w1.values())

    # W2/P3: both producers wrong, and the decided world inverts.
    w2 = arm_fractions(logs, lambda name, mask: (True, True))
    inverted = {name: all(
        decides_world(logs, mask, (True, True)) == "world0"
        and delivered_with_error(logs, 0, mask, wrong=(True, True))[0].attrs.get("tag")
        == delivered_with_error(logs, 1, mask, wrong=(False, False))[0].attrs.get("tag")
        for mask in masks) for name, masks in ARMS.items()}
    p3 = all(v == 1 for v in w2.values()) and any(inverted.values())

    # W3/P4: A wrong at random damages the independent arm more.
    w3 = arm_fractions(logs, lambda name, mask: (False, False), random_wrong=True)
    p4 = w3["independent"] < w3["shared"] and w3["shared"] < 1

    # W4/P5: anonymous ties everywhere; W5: tag shuffle is information-neutral.
    w4 = {name: sum(1 for mask in masks if resolves(logs, mask, (True, False),
                                                   anonymous=True))
          for name, masks in ARMS.items()}
    w5 = arm_fractions(logs, lambda name, mask: (False, True))
    p5 = all(v == 0 for v in w4.values()) and w5 == w1

    # matched marginals: counts and sources identical across every payload rule
    matched = {}
    for name, masks in ARMS.items():
        for mask in masks:
            base = counts_and_sources(logs, mask, (False, False))
            for wrong in ((True, False), (True, True), (False, True)):
                assert counts_and_sources(logs, mask, wrong) == base, (name, mask, wrong)
            matched[f"{name}{mask}"] = base

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p5:
        verdict += "; UNVERIFIABLE (a control did not hold, so tags are not isolated)"

    def frac(d):
        return {k: str(v) for k, v in d.items()}

    receipt = {
        "card": "R-P1.74", "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.74-tag-errors.md",
        "command": "python3 scripts/tag-errors-prereg.py",
        "anchor_perfect": frac(anchor),
        "w1_one_wrong": frac(w1),
        "w2_both_wrong": frac(w2),
        "w2_inverts": inverted,
        "w3_random_wrong": frac(w3),
        "w4_anonymous_ties": w4,
        "w5_tag_shuffle": frac(w5),
        "matched_marginals": matched,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/tag-errors-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "anchor": frac(anchor),
                      "w1": frac(w1), "w2": frac(w2), "w3": frac(w3),
                      "w4_ties": w4, "w5": frac(w5)}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
