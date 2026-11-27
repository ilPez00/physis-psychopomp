"""R-P1.66: is a late report with a stale position a null instrument?

Frozen card: docs/2026-11-27-PREREG-R-P1.66-true-delay.md, pushed at `068a721`
before this file existed. Claim `6f4e59e9-4aba-4e4f-b285-5421c43301d2`.

R-P1.43 measured a **lagging sampler** (reports the body's position at t + L) and
argued, in an amendment, that the other instrument — a late report carrying the
**stale** position at t — would be null because ordering was already
canonicalised. That argument was never measured. This measures it.

The three arms run on identical episodes and seeds:

  A  no delay                       (baseline, must reproduce R-P1.43's L = 0)
  B  lagging sampler, detect_latency (R-P1.43's instrument, re-measured here)
  C  true delay: A's positions, timestamps shifted by L   (this card)

C is built by shifting the event time on the no-delay log rather than by adding a
third simulator mode: the instrument is "same content, later clock", and post-
processing states that exactly without touching R-P1.43's measured code path.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psychopomp.attribution import attribute
from psychopomp.eventlog import EventLog
from psychopomp.interventions import Intervention
from psychopomp.selfmodel import estimate_blind_region
from psychopomp.sim import Init, Kick, SimConfig, run

CLAIM = "6f4e59e9-4aba-4e4f-b285-5421c43301d2"
O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TRUE = O2
STEP = 0.3
PARKED = (3.0, 97.0)   # R-P1.43: the parked body sits outside the occluder
LAGS = (0, 1, 2, 3)
CORPORA = 20
SEEDS = (0, 1, 2, 3, 4)
T_STAR = 90
TASKS = ((42.0, 45.0), (46.0, 45.0), (48.0, 45.0), (52.0, 45.0))


def corpus(lag: int, realization: int, instrument: str = "lagging"):
    """Five horizontal lanes and three vertical columns, as R-P1.43 built them."""
    eps = []
    cfg = SimConfig(steps=400, o=O, o2=O2,
                    detect_latency=lag if instrument == "lagging" else 0)
    for i, lane in enumerate((40.0, 44.0, 48.0, 52.0, 56.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=1000 * realization + i,
                       init=Init(x=(start, PARKED[0]), y=(lane, PARKED[1]),
                                 v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((47.0, 50.0, 53.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(cfg, 0, episode=1000 * realization + 100 + i,
                       init=Init(x=(column, PARKED[0]), y=(start, PARKED[1]),
                                 v=((0.0, v), (0.0, 0.0)))))
    if instrument == "true_delay":
        eps = [stale(ep, lag) for ep in eps]
    return eps


def stale(ep, lag: int):
    """The same episode with every crossing reported `lag` steps late, same position.

    The report's clock moves (`seq`/`t`), the content does not: this is the
    instrument R-P1.43's amendment called a null instrument.
    """
    if lag == 0:
        return ep
    shifted: list = []
    for ev in ep.observable_log().events:
        attrs = dict(ev.attrs)
        attrs["at"] = round(ev.t + lag * ep.config.dt, 6)
        shifted.append(replace(ev, seq=ev.seq + lag, attrs=attrs))
    log = EventLog(shifted)
    from psychopomp.sim import SimEpisode
    return SimEpisode(ep.config, ep.seed, ep.episode, ep.trajs,
                      ep.applied_kicks, ep.skipped_kicks, ep.init, log,
                      ep.oracle_log())


def margins(arm: str, lag: int) -> list:
    """Signed margin per edge: > 0 inside the truth, < 0 outside."""
    out = []
    for r in range(CORPORA):
        rect = estimate_blind_region(corpus(lag, r, arm), STEP).as_rect()
        if rect is None:
            continue
        out.extend([rect[0] - TRUE[0], TRUE[1] - rect[1],
                    rect[2] - TRUE[2], TRUE[3] - rect[3]])
    return out


def reported_positions(arm: str, lag: int, realization: int) -> list:
    """Crossing positions as the estimator sees them, in event order."""
    eps = corpus(lag, realization, arm)
    rows = []
    for ep in eps:
        for ev in ep.observable_log().events:
            pos = ev.attrs.get("pos")
            if pos is not None:
                rows.append(tuple(round(float(c), 6) for c in pos))
    return sorted(rows)


def verdict_counts(arm: str, lag: int) -> list:
    """Tie/unique verdict per seed on the fixed task set."""
    out = []
    cfg = SimConfig(steps=200, o=O, o2=O2,
                    detect_latency=lag if arm == "lagging" else 0,
                    n_balls=len(TASKS))
    starts = tuple(5.0 + 5.0 * i for i in range(len(TASKS)))
    speeds = tuple((p[0] - s) / (0.1 * T_STAR) for p, s in zip(TASKS, starts))
    init = Init(x=starts, y=tuple([45.0] * len(TASKS)),
                v=tuple((v, 0.0) for v in speeds))
    for seed in SEEDS:
        for i in range(len(TASKS)):
            true = Intervention(t=T_STAR, ball=i, dv=(0.0, 1.5))
            ep = run(cfg, seed, episode=0, init=init,
                     kicks=(Kick(T_STAR, i, (0.0, 1.5)),))
            probe = stale(ep, lag) if arm == "true_delay" else ep
            res = attribute(probe, [true, None], cfg, seed, init)
            out.append(bool(res["unique"] and res["best"] is true))
    return out


def oracle_identical(arm: str, lag: int) -> bool:
    """Neither delayed instrument may touch the oracle log."""
    for r in range(2):
        base = corpus(0, r, "none")
        armd = corpus(lag, r, arm)
        for a, b in zip(base, armd):
            oa = [(e.kind, round(e.t, 9), tuple(e.attrs.get("pos") or ()))
                  for e in a.oracle_log().events]
            ob = [(e.kind, round(e.t, 9), tuple(e.attrs.get("pos") or ()))
                  for e in b.oracle_log().events]
            if oa != ob:
                return False
    return True


def main() -> int:
    summary = {}
    for arm in ("lagging", "true_delay"):
        summary[arm] = {}
        for lag in LAGS:
            m = margins(arm, lag)
            summary[arm][f"L{lag}"] = {
                "samples": len(m),
                "mean_margin": statistics.fmean(m) if m else None,
                "mean_negative": (statistics.fmean([-x for x in m if x < 0])
                                  if any(x < 0 for x in m) else None),
                "optimistic": sum(1 for x in m if x > 1e-9),
            }
    base = {}
    for lag in LAGS:
        m = margins("none", 0)
        base[f"L{lag}"] = {"mean_margin": statistics.fmean(m) if m else None}
        break

    # P1: a stale report must not reorder the estimator's input positions.
    order_ok = {}
    for lag in LAGS:
        a = reported_positions("none", 0, 0)
        c = reported_positions("true_delay", lag, 0)
        order_ok[f"L{lag}"] = (a == c)
    p1 = all(order_ok.values())

    # P2: but the edge estimate still moves.
    base_mean = summary["lagging"]["L0"]["mean_margin"]
    p2 = any(
        abs((summary["true_delay"][f"L{lag}"]["mean_margin"] or 0.0) - base_mean) > 1e-9
        for lag in LAGS if lag >= 1)

    # P3: the two instruments must be distinguishable on reported positions.
    distinguishable = {}
    for lag in LAGS:
        b = reported_positions("lagging", lag, 0)
        c = reported_positions("true_delay", lag, 0)
        distinguishable[f"L{lag}"] = (b != c)
    p3 = all(v for k, v in distinguishable.items() if k != "L0")

    # P4: identifiability is a predicate on the true geometry.
    verdicts = {arm: {f"L{lag}": verdict_counts(arm, lag) for lag in LAGS}
                for arm in ("none", "lagging", "true_delay")}
    p4 = all(verdicts[arm][k] == verdicts["none"][k]
             for arm in ("lagging", "true_delay") for k in verdicts["none"])

    # P5: the oracle is untouched.
    p5 = all(oracle_identical(arm, lag) for arm in ("lagging", "true_delay")
             for lag in LAGS if lag >= 1)

    verdict = ", ".join(
        f"{name}={'HELD' if ok else 'FAILED'}"
        for name, ok in (("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5))
    )
    if not p3:
        verdict += "; UNVERIFIABLE (the two instruments are not distinguishable)"

    receipt = {
        "card": "R-P1.66",
        "claim_id": CLAIM,
        "prereg": "docs/2026-11-27-PREREG-R-P1.66-true-delay.md",
        "command": "python3 scripts/true-delay-prereg.py",
        "lags": list(LAGS), "corpora": CORPORA, "seeds": list(SEEDS),
        "lagging": summary["lagging"],
        "true_delay": summary["true_delay"],
        "order_preserved": order_ok,
        "distinguishable_positions": distinguishable,
        "verdicts": verdicts,
        "verdict": verdict,
    }
    out = ROOT / "research/loops/results/true-delay-20261127"
    out.mkdir(parents=True, exist_ok=True)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "lagging": summary["lagging"],
                      "true_delay": summary["true_delay"],
                      "distinguishable": distinguishable}, indent=1))
    print(f"receipt: {out.relative_to(ROOT)}/receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
