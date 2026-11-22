"""Publication formalities must not rot silently."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_citation_file_has_the_fields_a_citation_format_needs():
    text = (ROOT / "CITATION.cff").read_text()
    for key in ("cff-version", "title", "authors", "version", "repository-code"):
        assert f"{key}:" in text, key
    # No license claim: publication is not a reuse grant (IMP-2, operator).
    assert "\nlicense:" not in text


def test_citation_points_at_the_canonical_repository():
    text = (ROOT / "CITATION.cff").read_text()
    assert "https://github.com/ilPez00/physis-psychopomp" in text
    assert "ilPez00/psychopomp\"" not in text


def test_the_version_is_one_answer_everywhere():
    # Three surfaces, two answers, nothing comparing them: pyproject and
    # __version__ said 0.1.0 while CITATION and REPRO said 0.2.0.
    import re

    import psychopomp

    pyproject = (ROOT / "pyproject.toml").read_text()
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    citation = (ROOT / "CITATION.cff").read_text()
    cited = re.search(r"^version: (\S+)", citation, re.MULTILINE).group(1)
    assert declared == psychopomp.__version__
    assert declared == cited
    assert declared == "0.10.0"
