"""Tests for scripts/fetch_prose.py — the Doc -> repo boundary."""
import fetch_prose


def test_title_is_parsed_from_the_doc(doc_md):
    m = fetch_prose.DOC_TITLE.search(doc_md)
    assert m is not None
    assert "Air sampling in team congregate spaces" in m.group("title")


def test_legends_include_all_four_figures(doc_md):
    legends = fetch_prose.extract_legends(doc_md)
    assert set(legends) == {"central", "fig1", "fig2", "fig3", "supp1"}


def test_body_starts_at_abstract_and_stops_at_references(doc_md):
    body = fetch_prose.normalize(doc_md)
    assert body.lstrip().startswith("<!-- AUTO-GENERATED")
    assert "## Abstract" in body
    assert "## References" not in body
