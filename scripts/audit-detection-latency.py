"""R-P1.43 follow-up audit, not a new prereg or a replacement verdict."""
import runpy
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psychopomp.attribution import attribute
from psychopomp.interventions import Intervention
from psychopomp.law import on_boundary, predict_identifiable
from psychopomp.sim import Init, Kick, SimConfig, run


def main() -> None:
    card = runpy.run_path(str(Path(__file__).with_name("detection-latency-prereg.py")))
    tasks, t, lags = card["TASKS"], card["T_STAR"], card["LAGS"]
    starts = tuple(5.0 + 5.0 * i for i in range(len(tasks)))
    init = Init(x=starts, y=tuple(y for _, y in tasks),
                v=tuple(((x - start) / (0.1 * t), 0.0)
                        for (x, _), start in zip(tasks, starts)))
    base = SimConfig(steps=200, o=card["O"], o2=card["O2"], n_balls=len(tasks))
    predicted = {
        i: predict_identifiable(base, point, t) for i, point in enumerate(tasks)
        if not on_boundary(base, point, t)
    }
    print("predicted:", ", ".join(f"x={tasks[i][0]:g}:{'unique' if visible else 'tie'}"
                                  for i, visible in predicted.items()))
    print("L | measured off-boundary outcomes | matches | excluded task outcomes")
    for lag in lags:
        cfg = replace(base, detect_latency=lag)
        measured = {}
        for i, point in enumerate(tasks):
            true = Intervention(t=t, ball=i, dv=(0.0, 1.5))
            episode = run(cfg, 0, episode=0, init=init, kicks=(Kick(t, i, true.dv),))
            tr = episode.trajs[i]
            actual = tr.x[t], tr.y[t]
            assert all(abs(a - b) < 1e-6 for a, b in zip(actual, point)), (i, point, actual)
            assert on_boundary(cfg, actual, t) == (i not in predicted), (lag, actual)
            out = attribute(episode, [true, None], cfg, 0, init)
            measured[i] = "unique" if out["unique"] and out["best"] is true else (
                "wrong" if out["unique"] else "tie")
        matches = sum(measured[i] == ("unique" if visible else "tie")
                      for i, visible in predicted.items())
        scored = ", ".join(f"x={tasks[i][0]:g}:{measured[i]}" for i in predicted)
        excluded = ", ".join(f"x={tasks[i][0]:g}:{measured[i]}"
                             for i in measured if i not in predicted)
        print(f"{lag} | {scored} | {matches}/{len(predicted)} | {excluded}")


if __name__ == "__main__":
    main()
