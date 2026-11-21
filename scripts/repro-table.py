"""Generate or check the expected-output block quoted in REPRO.md.

The block used to be prose ("worlds ~1.1") that could drift from the code it
describes. It is now produced by running the gate itself; `--check` fails when
the checked-in copy disagrees, so a changed number must be acknowledged.

Usage:
  .venv/bin/python scripts/repro-table.py            # print the block
  .venv/bin/python scripts/repro-table.py --check    # exit 1 on drift
  .venv/bin/python scripts/repro-table.py --write    # rewrite REPRO.md
"""
from __future__ import annotations

import difflib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPRO = ROOT / "REPRO.md"
SCRIPT = ROOT / "scripts" / "recoverability.py"
START = "<!-- generated:recoverability:start -->"
END = "<!-- generated:recoverability:end -->"


def generate() -> str:
    run = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True
    )
    if run.returncode != 0:
        raise SystemExit(f"recoverability gate failed (exit {run.returncode}):\n{run.stderr}")
    body = [line for line in run.stdout.splitlines() if line.strip()]
    return "\n".join([START, "```", *body, "```", END])


def extract(text: str) -> str:
    i, j = text.find(START), text.find(END)
    if i < 0 or j < 0:
        raise SystemExit(f"REPRO.md has no {START} ... {END} block")
    return text[i : j + len(END)]


def main(argv: list[str]) -> int:
    block = generate()
    text = REPRO.read_text()
    current = extract(text)
    if "--write" in argv:
        REPRO.write_text(text.replace(current, block))
        print("REPRO.md updated")
        return 0
    if "--check" in argv:
        if current == block:
            print("REPRO expected-output block matches the gate")
            return 0
        diff = difflib.unified_diff(
            current.splitlines(), block.splitlines(),
            fromfile="REPRO.md", tofile="measured", lineterm="",
        )
        print("\n".join(diff))
        print("REPRO.md drifts from the gate: run scripts/repro-table.py --write and review")
        return 1
    print(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
