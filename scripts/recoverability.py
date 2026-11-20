"""Observable-only recoverability baseline + EPEC world accounting.

Gate answered (audit 2026-11-20, demand 3): is the pre-registered task even
solvable from observable history before any JEPA training?

Reference method (oracle-free): restart the episode from the OBSERVED frame-0
state (x, y, vx, vy -- all visible) and integrate the known physics forward.
It is a well-posedness check, not a competing learned method: it uses the
same physics as the ground truth, so it measures whether the observable
history carries enough information, not whether a model can find it.

Two families:
  random     -- crossings sampled freely; rarely contacts (reported as such)
  targeted   -- aimed near the occluder centre; contains hidden contacts,
                the family the identifiability question is about

Reported arms (Rule 2: every number next to the arm it must beat):
  - EPEC worlds, contact_required, truth-in-worlds (sanity) per family
  - reference pairing accuracy vs oracle (per-ball exit sides)
  - shuffled-control corpus on the targeted family (marginals preserved?)

Usage: .venv/bin/python scripts/recoverability.py
"""
from __future__ import annotations

import random
import sys
from statistics import mean, median

sys.path.insert(0, ".")

from psychopomp.controls import control_report, shuffle_rules
from psychopomp.epec import consistent_worlds, summarize
from psychopomp.sim import Init, SimConfig, run

RANDOM_CFG = SimConfig(steps=300, speed=3.0)
TARGET_CFG = SimConfig(steps=200)


def build_corpus(n_random: int = 8, n_target: int = 6):
    """Cleared episodes only: every enter has its exit (filter contract).

    A truncated episode (ball still inside at the end) cannot be checked by
    C5, which needs both exit velocities; such logs are outside the filter's
    scope by construction, not silently zero-world.
    """
    rnd, seed = [], 0
    while len(rnd) < n_random and seed < 400:
        ep = run(RANDOM_CFG, seed)
        s = summarize(ep.observable_log())
        if s["enters"] >= 1 and s["enters"] == s["exits"]:
            rnd.append(ep)
        seed += 1
    tgt, rng, tries = [], random.Random(7), 0
    while len(tgt) < n_target and tries < 400:
        tries += 1
        init = Init(
            x=(rng.uniform(15, 25), rng.uniform(48, 56)),
            y=(rng.uniform(40, 50), rng.uniform(15, 27)),
            v=((3.0, rng.uniform(0.4, 1.2)), (0.0, rng.uniform(2.8, 4.0))),
        )
        ep = run(TARGET_CFG, 0, init=init)
        hidden = [e for e in ep.oracle_log() if e.kind == "ball_collide" and not e.observable]
        s = summarize(ep.observable_log())
        if hidden and s["enters"] == 2 and s["exits"] == 2:
            tgt.append(ep)
    return rnd, tgt


def truth_matches(ep) -> tuple:
    """Oracle pairing as (enter_idx, exit_idx) over the observable log order."""
    obs = ep.observable_log()
    enters = [e for e in obs if e.kind == "enter_occ"]
    exits = [e for e in obs if e.kind == "exit_occ"]
    pairs = []
    for ball in sorted({e.subjects[0] for e in ep.oracle_log() if e.kind == "enter_occ"}):
        ent = sorted(e.t for e in ep.oracle_log() if e.kind == "enter_occ" and e.subjects[0] == ball)
        exi = sorted(e.t for e in ep.oracle_log() if e.kind == "exit_occ" and e.subjects[0] == ball)
        for a, b in zip(ent, exi):
            if b > a:
                ei = next(i for i, e in enumerate(enters) if e.t == a)
                xi = next(i for i, e in enumerate(exits) if e.t == b)
                pairs.append((ei, xi))
    return tuple(sorted(pairs))


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
    worlds, contact_req, truth_in = [], 0, 0
    for ep in eps:
        s = summarize(ep.observable_log())
        worlds.append(s["n_worlds"])
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
    print(f"  contact_required: {contact_req}/{n}")
    print(f"  truth-in-worlds (EPEC sanity, must be {n}): {truth_in}/{n}")
    print(f"  reference exit-side accuracy (observable-only restart, shared physics): {ok}/{tot}")


def main() -> int:
    rnd, tgt = build_corpus()
    family_report("random", rnd)
    family_report("targeted", tgt)

    corpus = [ep.observable_log() for ep in tgt]
    shuf = shuffle_rules(corpus, seed=12345)
    rep = control_report(corpus, shuf)
    s_worlds = [summarize(l)["n_worlds"] for l in shuf]
    s_contact = sum(int(summarize(l)["contact_required"]) for l in shuf)
    print(f"[control: targeted corpus deranged] worlds mean {mean(s_worlds):.2f} "
          f"contact_required {s_contact}/{len(tgt)} "
          f"marginals_preserved={rep['exit_marginals_preserved']} "
          f"alignment_changed={rep['alignment_changed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
