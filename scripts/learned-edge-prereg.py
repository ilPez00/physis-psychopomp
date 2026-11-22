"""R-P1.36 — the first licensed learned arm: a correction to the edge estimate.

Prereg: docs/2026-11-22-PREREG-R-P1.36-learned-edge.md, registered before this
script existed (claim registered before the run).

The model reads only what the deterministic estimator reads (crossing-bound
statistics and the known noise level) and predicts the *signed margin* between the
estimate and the truth. It is judged against the deterministic inner bound and
against a shuffled-target control, on held-out corpora including an unseen sigma.

Usage: .venv/bin/python scripts/learned-edge-prereg.py
"""
from __future__ import annotations

import random
import statistics
import sys

import numpy as np

sys.path.insert(0, ".")

from psychopomp.selfmodel import collect_edge_bounds
from psychopomp.sim import Init, SimConfig, run

O = (40.0, 60.0, 35.0, 65.0)
O2 = (46.0, 54.0, 35.0, 65.0)
TRUE = {"x0": 46.0, "x1": 54.0, "y0": 35.0, "y1": 65.0}
STEP = 0.3
PARKED = (3.0, 97.0)
TRAIN_SIGMAS = (0.2, 0.3, 0.5, 0.7, 1.0)
HELD_SIGMAS = (0.3, 1.0, 1.5)
TRAIN_CORPORA = 200
HELD_CORPORA = 20
EPOCHS = 400
SEED = 20261122
EDGES = ("x0", "x1", "y0", "y1")


def corpus(noise: float, realization: int):
    eps = []
    for i, lane in enumerate((40.0, 44.0, 48.0, 52.0, 56.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, noise=noise), 0,
                       episode=10000 * realization + i,
                       init=Init(x=(start, PARKED[0]), y=(lane, PARKED[1]),
                                 v=((v, 0.0), (0.0, 0.0)))))
    for i, column in enumerate((47.0, 50.0, 53.0)):
        start, v = ((10.0, 3.0) if i % 2 == 0 else (95.0, -3.0))
        eps.append(run(SimConfig(steps=400, o=O, o2=O2, noise=noise), 0,
                       episode=10000 * realization + 100 + i,
                       init=Init(x=(column, PARKED[0]), y=(start, PARKED[1]),
                                 v=((0.0, v), (0.0, 0.0)))))
    return eps


def estimate(bounds, edge: str) -> float | None:
    values = bounds.get(edge) or []
    if not values:
        return None
    return min(values) if edge in ("x0", "y0") else max(values)


def signed_margin(edge: str, est: float) -> float:
    """> 0 means the estimate is inside the truth (optimistic), < 0 pessimistic."""
    return (est - TRUE[edge]) if edge in ("x0", "y0") else (TRUE[edge] - est)


def features(bounds, edge: str, sigma: float) -> list:
    values = sorted(bounds.get(edge) or [])
    if not values:
        return [0.0] * 10 + [0.0, sigma]
    def q(p):
        return values[int(p * (len(values) - 1))]
    return [values[0], q(0.1), q(0.25), q(0.5), q(0.75), q(0.9), values[-1],
            statistics.mean(values), statistics.pstdev(values), float(len(values)),
            values[-1] - values[0], sigma]


def dataset(sigmas, corpora, seed_offset: int):
    rows_x, rows_y = [], []
    for sigma in sigmas:
        for r in range(corpora):
            bounds = collect_edge_bounds(corpus(sigma, seed_offset + r), STEP)
            for edge in EDGES:
                est = estimate(bounds, edge)
                if est is None:
                    continue
                rows_x.append(features(bounds, edge, sigma))
                rows_y.append(signed_margin(edge, est))
    return rows_x, rows_y


class Net:
    """12 -> 24 -> 1 ReLU MLP with Adam, in numpy: no new project dependency."""

    def __init__(self, rng, hidden: int = 24):
        self.w1 = rng.normal(0, (2.0 / 12) ** 0.5, (12, hidden))
        self.b1 = np.zeros(hidden)
        self.w2 = rng.normal(0, (2.0 / hidden) ** 0.5, (hidden, 1))
        self.b2 = np.zeros(1)

    def forward(self, x):
        h = np.maximum(0.0, x @ self.w1 + self.b1)
        return (h @ self.w2 + self.b2).ravel()

    def step(self, x, y, state, lr=0.01, b1=0.9, b2=0.999, eps=1e-8):
        h = np.maximum(0.0, x @ self.w1 + self.b1)
        pred = (h @ self.w2 + self.b2).ravel()
        err = pred - y
        n = x.shape[0]
        grads = {
            "w2": (h.T @ err[:, None]) * 2.0 / n,
            "b2": np.array([2.0 * err.mean()]),
        }
        dh = (err[:, None] @ self.w2.T) * (h > 0)
        grads["w1"] = (x.T @ dh) * 2.0 / n + 1e-4 * self.w1
        grads["b1"] = dh.mean(axis=0) * 2.0
        for k, g in grads.items():
            m, v, t = state[k]
            m[...] = b1 * m + (1 - b1) * g
            v[...] = b2 * v + (1 - b2) * g * g
            mhat = m / (1 - b1 ** (t + 1))
            vhat = v / (1 - b2 ** (t + 1))
            getattr(self, k)[...] -= lr * mhat / (np.sqrt(vhat) + eps)
            state[k] = (m, v, t + 1)


def train(xs, ys, shuffle_targets: bool = False):
    rng = np.random.default_rng(SEED)
    data_y = list(ys)
    if shuffle_targets:
        random.Random(SEED).shuffle(data_y)
    x = np.asarray(xs, dtype=np.float64)
    y = np.asarray(data_y, dtype=np.float64)
    net = Net(rng)
    state = {"w1": (np.zeros_like(net.w1), np.zeros_like(net.w1), 0),
             "b1": (np.zeros_like(net.b1), np.zeros_like(net.b1), 0),
             "w2": (np.zeros_like(net.w2), np.zeros_like(net.w2), 0),
             "b2": (np.zeros_like(net.b2), np.zeros_like(net.b2), 0)}
    for _ in range(EPOCHS):
        net.step(x, y, state)
    return net


def evaluate(net, xs, ys) -> dict:
    pred = net.forward(np.asarray(xs, dtype=np.float64)).tolist()
    corrected = [y - p for y, p in zip(ys, pred)]
    baseline_margins = ys
    return {
        "n": len(ys),
        "baseline_pessimistic": sum(1 for m in baseline_margins if m < -1e-9) / len(ys),
        "learned_pessimistic": sum(1 for m in corrected if m < -1e-9) / len(corrected),
        "baseline_mae": statistics.mean(abs(m) for m in baseline_margins),
        "learned_mae": statistics.mean(abs(m) for m in corrected),
    }


def main() -> int:
    print("building training data ...", flush=True)
    xs, ys = dataset(TRAIN_SIGMAS, TRAIN_CORPORA, seed_offset=0)
    net = train(xs, ys)
    ctrl = train(xs, ys, shuffle_targets=True)
    print(f"training rows {len(xs)} (4 edges x {TRAIN_CORPORA} corpora x "
          f"{len(TRAIN_SIGMAS)} sigmas)")

    results = {}
    print("| held-out σ | baseline pessimistic | learned | shuffled control | baseline MAE | learned MAE |")
    print("|---|---|---|---|---|---|")
    for sigma in HELD_SIGMAS:
        hx, hy = dataset((sigma,), HELD_CORPORA, seed_offset=90000)
        base = evaluate(net, hx, hy)
        ctrl_r = evaluate(ctrl, hx, hy)
        results[sigma] = {**base, "control_pessimistic": ctrl_r["learned_pessimistic"],
                          "control_mae": ctrl_r["learned_mae"]}
        print(f"| {sigma:.1f} | {base['baseline_pessimistic']:.2f} | "
              f"{base['learned_pessimistic']:.2f} | {ctrl_r['learned_pessimistic']:.2f} | "
              f"{base['baseline_mae']:.3f} | {base['learned_mae']:.3f} |")

    l1 = results[1.0]["learned_pessimistic"] < results[1.0]["baseline_pessimistic"]
    l2 = (results[1.0]["learned_pessimistic"] < results[1.0]["control_pessimistic"]
          and abs(results[1.0]["control_pessimistic"]
                  - results[1.0]["baseline_pessimistic"]) <= 0.10)
    l3 = results[1.5]["learned_pessimistic"] < results[1.5]["baseline_pessimistic"]
    l4 = all(results[s]["learned_mae"] <= results[s]["baseline_mae"] + 0.05
             for s in HELD_SIGMAS)

    print()
    print(f"L1 beats the deterministic baseline at σ=1.0: {'UPHELD' if l1 else 'FALSIFIED'}")
    print(f"L2 beats its shuffled control at σ=1.0: {'UPHELD' if l2 else 'FALSIFIED'}")
    print(f"L3 transfers to the unseen σ=1.5: {'UPHELD' if l3 else 'FALSIFIED'}")
    print(f"L4 no accuracy regression on any held-out σ: {'UPHELD' if l4 else 'FALSIFIED'}")
    ok = all((l1, l2, l3, l4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
