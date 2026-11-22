import pytest

from psychopomp.rows import SCHEMA, convert, fill, lookup

RECORD = {
    "schema": SCHEMA, "subject": "episode:0:0", "kind": "enter_occ", "at": 8.7,
    "props": {"side": "left"}, "evidence": "OBSERVED", "seq": 1,
    "provenance": {"source": "sim:v0.2", "seed": 0},
}
TEMPLATE = {"subject": "psychopomp:{{subject}}", "kind": "{{kind}}",
            "at": "{{at}}", "props": "{{props}}", "source": "{{provenance.source}}"}


def test_substitution_is_typed_not_stringified():
    row = fill(TEMPLATE, RECORD)
    assert row["at"] == 8.7 and isinstance(row["at"], float)
    assert row["props"] == {"side": "left"}
    assert row["subject"] == "psychopomp:episode:0:0"     # inline string form
    assert row["source"] == "sim:v0.2"                    # dotted path


def test_an_unknown_field_is_an_error_not_a_blank():
    with pytest.raises(KeyError):
        fill({"x": "{{nope}}"}, RECORD)
    with pytest.raises(KeyError):
        lookup(RECORD, "provenance.missing")


def test_a_foreign_schema_is_refused():
    with pytest.raises(ValueError):
        convert([{**RECORD, "schema": "psychopomp.observation/2"}], TEMPLATE)


def test_order_is_preserved_and_rows_are_independent():
    rows = convert([RECORD, {**RECORD, "seq": 2, "kind": "exit_occ"}], TEMPLATE)
    assert [r["kind"] for r in rows] == ["enter_occ", "exit_occ"]
    assert rows[0]["at"] == rows[1]["at"]                 # no shared mutable structure
    rows[0]["props"]["side"] = "mutated"
    assert rows[1]["props"]["side"] == "left"
