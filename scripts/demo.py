"""Executable quickstart: the three canonical results from REPRO.md."""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from psychopomp.epec import summarize
from psychopomp.sim import Init, SimConfig, run


def main() -> int:
    cfg = SimConfig(steps=150)
    straight = run(cfg, 0, init=Init(x=(20.0, 20.0), y=(50.0, 80.0), v=((3.0, 0.0), (3.0, 0.0))))
    off_axis = run(cfg, 0, init=Init(x=(20.0, 52.0), y=(45.0, 20.0), v=((3.0, 1.0), (0.0, 3.3))))

    s1 = summarize(straight.observable_log())
    s2 = summarize(off_axis.observable_log())

    print(f"straight : worlds={s1['n_worlds']} contact_required={s1['contact_required']}")
    print(f"off-axis : worlds={s2['n_worlds']} contact_required={s2['contact_required']}")
    print("off-axis worlds:")
    for w in s2["worlds"]:
        print(f"  {w}")

    ok = (
        s1["n_worlds"] == 1
        and not s1["contact_required"]
        and s2["n_worlds"] == 2
        and s2["contact_required"]
    )
    print("demo:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
