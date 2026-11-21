"""Observable-only recoverability baseline + EPEC world accounting.

Gate answered (audit 2026-11-20): is the pre-registered task even solvable
from observable history before any JEPA training?

Reference method (oracle-free): restart the episode from the OBSERVED frame-0
state (x, y, vx, vy -- all visible) and integrate the known physics forward.
It is a well-posedness check, not a competing learned method: it uses the
same physics as the ground truth, so it measures whether the observable
history carries enough information, not whether a model can find it.

Families: `random` (crossings sampled freely; rarely contacts) and
`targeted` (aimed near the occluder centre; contains hidden contacts).
Control arm: the targeted corpus with exit payloads deranged across episodes.

Usage: .venv/bin/python scripts/recoverability.py
"""
from __future__ import annotations

import sys
from statistics import mean, median

sys.path.insert(0, ".")

from psychopomp.controls import control_report, shuffle_rules
from psychopomp.epec import consistent_worlds, summarize
from psychopomp.fixtures import random_corpus, targeted_corpus, truth_matches
from psychopomp.sim import Init, run


def reference_episode(ep):
    """Restart from the visible frame-0 state; no hidden information used."""
    init = Init(
        x=tuple(tr.x[0] for tr in ep.trajs),
        y=tuple(tr.y[0] for tr in ep.trajs),
        v=tuple((tr.vx[0], tr.vy[0]) for tr in ep.trajs),
    )
    return run(ep.config, seed=0, init=init)


def exit_sides(ep) -> dict:
    out: dict = {}
    for e in ep.oracle_log():
        if e.kind == "exit_occ":
            out.setdefault(e.subjects[0], []).append(e.attrs["side"])
    return {k: tuple(v) for k, v in out.items()}


def family_report(name: str, eps) -> None:
    n = len(eps)
    worlds, contact_req, undecided, truth_in = [], 0, 0, 0
    for ep in eps:
        s = summarize(ep.observable_log())
        worlds.append(s["n_worlds"])
        # contact_required is None when no world explains the log (or the episode
        # is truncated). Counting that as 0 conflated "undecidable" with "no
        # contact" -- the same fabrication the reporting layer stopped making.
        if s["contact_required"] is None:
            undecided += 1
        else:
            contact_req += int(s["contact_required"])
        truth = truth_matches(ep)
        if any(w.matches == truth for w in consistent_worlds(ep.observable_log())):
            truth_in += 1
    ok = tot = 0
    for ep in eps:
        pred = reference_episode(ep)
        t_sides, p_sides = exit_sides(ep), exit_sides(pred)
        for ball in sorted(t_sides):
            tot += 1
            ok += int(t_sides.get(ball) == p_sides.get(ball))
    print(f"[{name}] episodes {n}")
    print(f"  EPEC worlds: mean {mean(worlds):.2f} median {median(worlds):.0f} zero {worlds.count(0)}")
    print(f"  contact_required: {contact_req}/{n} undecided {undecided}")
    print(f"  truth-in-worlds (EPEC sanity, must be {n}): {truth_in}/{n}")
    print(f"  reference exit-side accuracy (observable-only restart, shared physics): {ok}/{tot}")


def main() -> int:
    rnd = random_corpus(8)
    tgt = targeted_corpus(6)
    family_report("random", rnd)
    family_report("targeted", tgt)

    corpus = [ep.observable_log() for ep in tgt]
    shuf = shuffle_rules(corpus, seed=12345)
    rep = control_report(corpus, shuf)
    s_worlds = [summarize(l)["n_worlds"] for l in shuf]
    s_vals = [summarize(l)["contact_required"] for l in shuf]
    s_contact = sum(1 for v in s_vals if v is True)
    s_undecided = sum(1 for v in s_vals if v is None)
    print(f"[control: targeted corpus deranged] worlds mean {mean(s_worlds):.2f} "
          f"contact_required {s_contact}/{len(tgt)} undecided {s_undecided} "
          f"marginals_preserved={rep['exit_marginals_preserved']} "
          f"alignment_changed={rep['alignment_changed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
