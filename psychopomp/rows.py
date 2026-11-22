"""Map `psychopomp.observation/1` records onto a consumer-declared row template.

The consumer's row shape is theirs to declare. This module does the mapping and
nothing else: a value that is exactly `"{{field}}"` becomes that field's **typed**
value, `{{field}}` inside a longer string is string-formatted, and an unknown field
is an error rather than an empty string — a silently-missing column is worse than a
refusal.

See `docs/INTEGRATION-CONTRACT.md` and the note at
`docs/notes/2026-11-22-physis-next-ingest-note.md`.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, Iterable, List

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")
EXACT = re.compile(r"^\{\{\s*([A-Za-z0-9_.]+)\s*\}\}$")
SCHEMA = "psychopomp.observation/1"


def lookup(record: Dict[str, Any], dotted: str) -> Any:
    """Resolve a dotted field path, refusing rather than inventing a value."""
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(dotted)
        value = value[part]
    return value


def fill(template: Any, record: Dict[str, Any]) -> Any:
    if isinstance(template, dict):
        # keys starting with "_" are template annotations, never emitted
        return {k: fill(v, record) for k, v in template.items() if not k.startswith("_")}
    if isinstance(template, list):
        return [fill(v, record) for v in template]
    if isinstance(template, str):
        exact = EXACT.match(template)
        if exact:
            # copy: a row must not share structure with the source record, or a
            # caller mutating one row would corrupt the input and its siblings
            return copy.deepcopy(lookup(record, exact.group(1)))
        return PLACEHOLDER.sub(lambda m: str(lookup(record, m.group(1))), template)
    return template


def convert(records: Iterable[Dict[str, Any]], template: Any) -> List[Dict[str, Any]]:
    """One row per record, in the order given. Wrong schema is refused."""
    out = []
    for record in records:
        if record.get("schema") != SCHEMA:
            raise ValueError(f"not a {SCHEMA} record: {record.get('schema')!r}")
        out.append(fill(template, record))
    return out
