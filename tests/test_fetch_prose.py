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


def test_extracts_all_49_references(doc_md):
    refs = fetch_prose.extract_references(doc_md)
    assert len(refs) == 49
    assert [n for n, _ in refs] == list(range(1, 50))


def test_reference_text_drops_the_paperpile_url(doc_md):
    refs = dict(fetch_prose.extract_references(doc_md))
    assert "paperpile.com" not in refs[1]
    assert refs[1].startswith("Serner A, Chamari K")
    assert "10.1080/24733938.2024.2357568" in refs[1]


def test_reference_text_unescapes_doc_export_backslashes(doc_md):
    refs = dict(fetch_prose.extract_references(doc_md))
    # The Doc export escapes the period after "Qatar 2022" as "2022\."
    assert "\\." not in refs[1]


def test_reference_count_mismatch_raises(doc_md):
    # Drop reference 49 from the text; the parser must refuse the result
    # rather than silently emitting a short list.
    broken = doc_md.replace("## 49 \t[", "## 49x \t[")
    try:
        fetch_prose.extract_references(broken)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit on a reference count mismatch")
