"""Map `psychompomp.observation/1` records onto a consumer-declared row template.

The consumer's observation row shape is **theirs to declare** — I could not measure
it (see docs/notes/2026-11-22-physis-next-ingest-note.md), and guessing it would make
this exporter a source of plausible-looking wrong data. So the shape comes in as a
JSON template and this tool substitutes typed values into it.

Template rules (deliberately small):

* a value that is exactly `"{{field}}"` is replaced by that field's **typed** value
  (number, list, object, string) — the template stays valid JSON;
* inside a longer string, `{{field}}` is string-formatted (`"episode:{{subject}}"`);
* an unknown field name is an error, never an empty string;
* output is one JSON object per line, in the input's canonical order.

Usage:
  .venv/bin/python scripts/to-physis-rows.py --template row.json \
      research/fixtures/observation-v1.sample.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psychopomp.rows import SCHEMA, convert  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("source", nargs="?", help="JSONL file (default: stdin)")
    args = ap.parse_args()

    template = json.loads(Path(args.template).read_text())
    raw = Path(args.source).read_text() if args.source else sys.stdin.read()
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not records:
        print("no records", file=sys.stderr)
        return 1
    bad_schema = [r for r in records if r.get("schema") != SCHEMA]
    if bad_schema:
        print(f"refusing: {len(bad_schema)} records are not psychopomp.observation/1",
              file=sys.stderr)
        return 1
    try:
        rows = convert(records, template)
    except KeyError as exc:
        print(f"template asks for a field the records do not carry: {exc}", file=sys.stderr)
        return 1
    for row in rows:
        print(json.dumps(row, sort_keys=True))
    print(f"{len(rows)} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
