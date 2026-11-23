import runpy
from pathlib import Path

from psychopomp import active_loop


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "active-discovery.py"


def test_transcript_rejects_executor_posterior_even_if_resolved_law_is_correct(monkeypatch):
    update = active_loop._update

    def wrong_posterior(reading, *args):
        _, resolved = update(reading, *args)
        return (1, 1), resolved

    monkeypatch.setattr(active_loop, "_update", wrong_posterior)
    assert runpy.run_path(str(SCRIPT))["main"]() == 1


def test_transcript_rejects_reading_swapped_after_executor_update(monkeypatch):
    diagnose = active_loop.Session.diagnose

    def swapped(self, law, state, **kwargs):
        result = diagnose(self, law, state, **kwargs)
        if result["policy"] == "adaptive":
            result["reading"] *= -1
        return result

    monkeypatch.setattr(active_loop.Session, "diagnose", swapped)
    assert runpy.run_path(str(SCRIPT))["main"]() == 1
