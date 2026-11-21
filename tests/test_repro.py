"""Cross-process determinism: the failure mode a single-process test cannot see.

The noise-seed defect scored 0.17 locally and 0.33 on CI for identical inputs,
because a string entered the seed and Python randomises string hashing per
process. This runs the whole scoring pipeline in two subprocesses with different
PYTHONHASHSEED values and requires byte-identical reports.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PIPELINE = """
import json, sys
sys.path.insert(0, {root!r})
from psychopomp.epec import summarize
from psychopomp.fixtures import parallel_recrossing_corpus, random_corpus, targeted_corpus
from psychopomp.probes import m2_baseline, m2_position_continuity, m3_accuracy
from psychopomp.sim import Init, SimConfig, run

# The noisy arm is the part that can depend on PYTHONHASHSEED: a clean pipeline
# never draws from the noise RNG, so a gate without these episodes passes while
# the bug is present (measured 2026-11-21).
noisy = [
    run(SimConfig(steps=600, noise=5.0), k, init=Init(
        x=(30.0, 30.0), y=(45.0, 53.0), v=((3.0, 0.0), (3.0, 0.0))))
    for k in range(2)
]

report = []
for eps in (random_corpus(8), targeted_corpus(6), parallel_recrossing_corpus(6)):
    report.append({{
        "m2": m2_baseline(eps),
        "m3": m3_accuracy(eps),
        "a2": m2_position_continuity(eps),
        "worlds": [summarize(e.observable_log()) for e in eps],
    }})
report.append({{"noisy": [[dict(e.attrs) for e in ep.observable_log()] for ep in noisy]}})
print(json.dumps(report, sort_keys=True))
"""


def run_pipeline(hashseed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    return subprocess.run(
        [sys.executable, "-c", PIPELINE.format(root=str(ROOT))],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    ).stdout


def test_the_pipeline_is_identical_across_hash_seeds():
    a = run_pipeline("0")
    b = run_pipeline("1")
    assert a == b
    # And the report is not vacuously empty: the numbers are actually there.
    parsed = json.loads(a)
    assert len(parsed) == 4  # three corpora + the noisy arm
    assert parsed[2]["a2"]["top1"] == 1.0
    assert parsed[3]["noisy"]  # the noisy arm ran, not skipped
