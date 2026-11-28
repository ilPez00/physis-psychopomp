"""A claim of novelty must cite the card that already measured it.

Why this exists: on 2026-11-27 two cards were written whose headline result had
already been recorded days earlier — R-P1.70's "the rect estimator is
rectangle-shaped" was in R-P1.33's receipt, and R-P1.73's radius geometry was in
R-P1.44's. Neither cited the earlier card. The receipt gate
(`check-roadmap-receipts.py`) catches a claim with no artefact; nothing caught a
claim with no *search*, which is a different failure and the one that actually
happened.

How it decides, and what it cannot do: this cannot tell whether a citation is
honest, only whether an earlier card's receipt **shares distinctive terms** with
the newer card's text. It is a prompt, not a verdict — a hit means "read that
receipt", never "you plagiarised it". A card with no hit is not thereby novel.

Exit 1 on an uncited overlap, 2 if it parses zero cards (a checker that passes on
its own parse failure is the defect this exists to prevent).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
RECEIPTS = ROOT / "research" / "loops" / "results"
CARD = re.compile(r"^(\d{4}-\d{2}-\d{2})-PREREG-(R-P1\.\d+)-(.+)\.md$")

# Words that appear in every card and therefore distinguish nothing.
STOP = set("""
the a an and or of to in for is are was were be been being with without this that
these those it its as at by from on not no but if then than so which who whom
card measure measured measurement result results prediction predictions held
failed holds pass fail per step steps test tests gives gives give one two three
four five same only also both each all any some more most less least
""".split())


def terms(text: str) -> set[str]:
    """Distinctive **multi-word phrases**, not single words.

    Single words are useless here: every card in this lane writes "blind",
    "hypothesis" and "cells", so a bag-of-words test reported 613 overlaps across
    655 pairs — 94%, i.e. no signal. A 3-gram is specific enough that a shared one
    is about content: "rectangle by construction", "observable feed only". The
    audit runs on those.
    """
    words = [w for w in re.findall(r"[a-z][a-z\-]{2,}", text.lower()) if w not in STOP]
    out = set()
    for i in range(len(words) - 2):
        gram = " ".join(words[i:i + 3])
        out.add(gram)
    return out


def cards() -> list[dict]:
    found = []
    for path in sorted(DOCS.glob("*PREREG-R-P1.*.md")):
        m = CARD.match(path.name)
        if not m:
            continue
        date, card = m.group(1), m.group(2)
        found.append({"date": date, "card": card, "path": path,
                      "text": path.read_text()})
    return found


def receipt_text(card: str) -> str:
    """Every receipt.json whose path or content names this card."""
    chunks = []
    for d in RECEIPTS.iterdir():
        if not d.is_dir():
            continue
        r = d / "receipt.json"
        if not r.is_file():
            continue
        try:
            raw = r.read_text()
        except OSError:
            continue
        if f'"{card}"' in raw or card in d.name:
            chunks.append(raw)
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-overlap", type=int, default=3,
                    help="shared 3-word phrases before a hit is reported")
    ap.add_argument("--since", default="2026-11-26",
                    help="only audit cards dated on or after this day")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    all_cards = cards()
    if len(all_cards) < 10:
        print(f"2: parsed only {len(all_cards)} cards; the glob or the naming changed",
              file=sys.stderr)
        return 2

    audited = [c for c in all_cards if c["date"] >= args.since]
    if not audited:
        print(f"2: no cards dated {args.since} or later", file=sys.stderr)
        return 2

    hits = []
    checked = 0
    for c in audited:
        own = terms(c["text"])
        cites = set(re.findall(r"R-P1\.\d+", c["text"]))
        for prior in all_cards:
            if prior["card"] == c["card"] or prior["date"] >= c["date"]:
                continue
            prior_receipt = receipt_text(prior["card"])
            if not prior_receipt:
                continue
            checked += 1
            shared = own & terms(prior_receipt)
            if len(shared) >= args.min_overlap and prior["card"] not in cites:
                hits.append({
                    "card": c["card"], "date": c["date"],
                    "prior": prior["card"], "prior_date": prior["date"],
                    "shared": sorted(shared)[:12],
                    "shared_n": len(shared),
                })
    if checked == 0:
        print("2: compared 0 (card, prior receipt) pairs; nothing was audited",
              file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"audited": [c["card"] for c in audited],
                          "pairs_checked": checked, "hits": hits}, indent=1))
    else:
        print(f"cards audited: {len(audited)}  pairs checked: {checked}  "
              f"uncited overlaps: {len(hits)}")
        for h in hits:
            print(f"  {h['card']} ({h['date']}) shares {h['shared_n']} terms with "
                  f"{h['prior']} ({h['prior_date']}) and does not cite it:")
            print(f"    {', '.join(h['shared'])}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
