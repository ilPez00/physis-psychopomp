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
