"""R-P1.37 — containment-encoding loss: can a learned arm be made safe?

Prereg: docs/2026-11-22-PREREG-R-P1.37-pinball-loss.md, registered before this
script existed (claim registered before the run).

Same data, features, architecture and split as R-P1.36; the only change is the
loss. A pinball loss at tau=0.9 charges 9x for over-prediction, so the learned
correction is pushed to leave the corrected margin on the safe side.

Runs with the host scientific python (numpy); the project venv stays stdlib-only.

Usage: PYTHONPATH=. python3 scripts/pinball-edge-prereg.py
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
TAU = 0.9
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


def estimate(bounds, edge: str):
    values = bounds.get(edge) or []
    if not values:
        return None
    return min(values) if edge in ("x0", "y0") else max(values)


def signed_margin(edge: str, est: float) -> float:
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
    xs, ys = [], []
    for sigma in sigmas:
        for r in range(corpora):
            bounds = collect_edge_bounds(corpus(sigma, seed_offset + r), STEP)
            for edge in EDGES:
                est = estimate(bounds, edge)
                if est is None:
                    continue
                xs.append(features(bounds, edge, sigma))
                ys.append(signed_margin(edge, est))
    return xs, ys


class Net:
    def __init__(self, rng, hidden: int = 24):
        self.w1 = rng.normal(0, (2.0 / 12) ** 0.5, (12, hidden))
        self.b1 = np.zeros(hidden)
        self.w2 = rng.normal(0, (2.0 / hidden) ** 0.5, (hidden, 1))
        self.b2 = np.zeros(1)

    def forward(self, x):
        h = np.maximum(0.0, x @ self.w1 + self.b1)
        return (h @ self.w2 + self.b2).ravel()


def train(xs, ys, loss: str, shuffle_targets: bool = False):
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
    n = x.shape[0]
    for epoch in range(EPOCHS):
        h = np.maximum(0.0, x @ net.w1 + net.b1)
        pred = (h @ net.w2 + net.b2).ravel()
        r = pred - y
        if loss == "mse":
            grad = 2.0 * r / n
        else:                                   # pinball at TAU: 9x for over-prediction
            grad = np.where(r >= 0.0, TAU, TAU - 1.0) / n
        grad = grad[:, None]
        g_w2 = h.T @ grad
        g_b2 = np.array([grad.sum()])
        dh = (grad @ net.w2.T) * (h > 0)
        g_w1 = x.T @ dh + 1e-4 * net.w1
        g_b1 = dh.sum(axis=0)
        for k, g in (("w1", g_w1), ("b1", g_b1), ("w2", g_w2), ("b2", g_b2)):
            m, v, t = state[k]
            m[...] = 0.9 * m + 0.1 * g
            v[...] = 0.999 * v + 0.001 * g * g
            mhat = m / (1 - 0.9 ** (t + 1))
            vhat = v / (1 - 0.999 ** (t + 1))
            getattr(net, k)[...] -= 0.01 * mhat / (np.sqrt(vhat) + 1e-8)
            state[k] = (m, v, t + 1)
    return net


def evaluate(net, xs, ys) -> dict:
    pred = net.forward(np.asarray(xs, dtype=np.float64)).tolist()
    corrected = [y - p for y, p in zip(ys, pred)]
    return {
        "pessimistic": sum(1 for m in corrected if m < -1e-9) / len(corrected),
        "median_abs": statistics.median(abs(m) for m in corrected),
        "baseline_pessimistic": sum(1 for m in ys if m < -1e-9) / len(ys),
        "baseline_median_abs": statistics.median(abs(m) for m in ys),
    }


def main() -> int:
    print("building data ...", flush=True)
    xs, ys = dataset(TRAIN_SIGMAS, TRAIN_CORPORA, seed_offset=0)
    print(f"training rows {len(xs)}")
    pin = train(xs, ys, "pinball")
    mse = train(xs, ys, "mse")
    ctrl = train(xs, ys, "pinball", shuffle_targets=True)

    rows = {}
    print("| held-out σ | det. pess | mse pess | **pinball pess** | ctrl pess | det. med | mse med | pin med |")
    print("|---|---|---|---|---|---|---|---|")
    for sigma in HELD_SIGMAS:
        hx, hy = dataset((sigma,), HELD_CORPORA, seed_offset=90000)
        p = evaluate(pin, hx, hy)
        m = evaluate(mse, hx, hy)
        c = evaluate(ctrl, hx, hy)
        rows[sigma] = {"det": p["baseline_pessimistic"], "mse": m["pessimistic"],
                       "pin": p["pessimistic"], "ctrl": c["pessimistic"],
                       "det_med": p["baseline_median_abs"], "mse_med": m["median_abs"],
                       "pin_med": p["median_abs"]}
        print(f"| {sigma:.1f} | {p['baseline_pessimistic']:.2f} | {m['pessimistic']:.2f} | "
              f"**{p['pessimistic']:.2f}** | {c['pessimistic']:.2f} | "
              f"{p['baseline_median_abs']:.3f} | {m['median_abs']:.3f} | "
              f"{p['median_abs']:.3f} |")

    r10 = rows[1.0]
    q1 = r10["pin"] < r10["det"] and r10["pin"] < r10["mse"]
    q2 = r10["pin"] < r10["ctrl"] and abs(r10["ctrl"] - r10["det"]) <= 0.10
    q3 = rows[1.5]["pin"] < rows[1.5]["det"]
    q4 = all(rows[s]["pin_med"] <= rows[s]["det_med"] + 0.15 for s in HELD_SIGMAS)

    print()
    print(f"Q1 pinball beats the deterministic bound and the MSE arm at σ=1.0: "
          f"{'UPHELD' if q1 else 'FALSIFIED'} "
          f"({r10['pin']:.2f} vs det {r10['det']:.2f}, mse {r10['mse']:.2f})")
    print(f"Q2 it beats its own shuffled control: {'UPHELD' if q2 else 'FALSIFIED'} "
          f"({r10['pin']:.2f} vs {r10['ctrl']:.2f})")
    print(f"Q3 it transfers to the unseen σ=1.5: {'UPHELD' if q3 else 'FALSIFIED'} "
          f"({rows[1.5]['pin']:.2f} vs {rows[1.5]['det']:.2f})")
    print(f"Q4 the price is bounded (accuracy, not safety): {'UPHELD' if q4 else 'FALSIFIED'}")
    ok = all((q1, q2, q3, q4))
    print("prereg run:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
