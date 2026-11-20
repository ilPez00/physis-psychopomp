# Reproducibility manifest — Psychopomp v0.1

## Environment

- Python 3.12 (pin; other versions untested — `random.Random` and float
  formatting are the determinism surface).
- v0.1 core is stdlib-only (no numpy/torch/clingo). Dev dep: pytest>=8.
- Install:

```bash
cd ~/dev/psychopomp
uv venv --python 3.12 .venv
uv pip install -e '.[dev]'
.venv/bin/pytest -q
```

## Determinism

- Seeded via `random.Random(hash((seed, episode)) % 2**63)` — int hashing is
  stable; no `PYTHONHASHSEED` sensitivity.
- Floats serialized with `round(..., 6)` and `sort_keys=True`.
- Same (config, seed, episode, init, kicks) ⇒ identical observable/oracle
  JSONL, asserted by `tests/test_sim.py::test_determinism_same_seed`.
- Occluder must sit strictly inside the walls; one step must not cross the
  whole occluder (asserted at runtime — `speed * dt < o_hi - o_lo`).

## Canonical scenarios (fixed)

| name | config | seed | init | expects |
|---|---|---|---|---|
| straight | SimConfig(steps=45) | 0 | x=(20,80) v=(4,4) | 1 enter (left,+4), 1 exit (right,+4), 1 world |
| swap | SimConfig(steps=45) | 0 | x=(30,70) v=(4,-4) | hidden contact in oracle only, 2 consistent worlds |
| teleport (synthetic) | — | — | fabricated log | 0 worlds, C4 violation |

## GPU phase (future, unpinned)

Not started. Before scheduling: confirm omo GPU availability. Pins for
numpy/torch/EB-JEPA/clingo get added to this file at that point, not before.
