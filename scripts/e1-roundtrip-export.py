"""E1 round trip, producer side: export the 24 R-P1.48 cells as real rows.

Each cell is run as its own episode, because `psychopomp.observation/1` keys a row
on `(subject, seq)` and every cell would otherwise share `episode:0:0` — the
importer's dedup would then keep the first and skip the rest, which is correct
behaviour and useless evidence.
"""
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.export import observation_records
from psychopomp.sim import Init, SimConfig, run

LAWS = (-1, 0, 1)
STATES = (-3, -1, 1, 3)
COMMANDS = (0, 2)


def episode(law: int, state: int, command: int, index: int):
    config = SimConfig(o=(40, 60, 35, 65), o2=None, n_balls=1, dt=0.1, steps=24,
                       visual_radius=0.0, allow_hidden_init=True,
                       accel=(0, law * command))
    return run(config, seed=0, episode=index,
               init=Init(x=(50,), y=(50 + state,), v=((5, 0),)))


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else
               "research/loops/results/e1-roundtrip-20261123/exit-cells.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, subjects = 0, set()
    with out.open("w") as handle:
        for index, (law, state, command) in enumerate(product(LAWS, STATES, COMMANDS)):
            ep = episode(law, state, command, index)
            for record in observation_records(ep):
                handle.write(__import__("json").dumps(record, sort_keys=True) + "\n")
                rows += 1
                subjects.add(record["subject"])
    print(f"episodes={len(list(product(LAWS, STATES, COMMANDS)))} rows={rows} "
          f"subjects={len(subjects)} -> {out}")
    return 0 if rows == len(subjects) == 24 else 1


if __name__ == "__main__":
    raise SystemExit(main())
