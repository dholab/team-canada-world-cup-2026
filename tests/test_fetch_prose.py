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


def test_supplement_contains_the_wastewater_methods(doc_md):
    supp = fetch_prose.extract_supplement(doc_md)
    assert "### Community wastewater comparison" in supp
    assert "PMMoV-normalized viral index" in supp
    assert "JWPCP" in supp


def test_supplement_drops_paperpile_urls(doc_md):
    supp = fetch_prose.extract_supplement(doc_md)
    assert "paperpile.com" not in supp


def test_supplement_excludes_the_figure_legends(doc_md):
    # The legends section precedes supplemental methods in the Doc and is
    # written separately to _legends/; it must not be duplicated here.
    supp = fetch_prose.extract_supplement(doc_md)
    assert "## Figure legends" not in supp


def test_keywords_come_from_the_doc(doc_md):
    assert fetch_prose.extract_keywords(doc_md) == [
        "Respiratory infection",
        "team sport",
        "athlete health",
        "public health",
    ]


def test_every_reference_resolves_to_a_link(doc_md):
    refs = fetch_prose.extract_references(doc_md)
    urls = fetch_prose.citation_urls(refs)
    # Each of the 49 entries carries either a DOI or a bare URL, so a reader can
    # click any inline citation through to its source.
    assert len(urls) == len(refs) == 49


def test_doi_is_preferred_over_a_bare_url(doc_md):
    urls = fetch_prose.citation_urls(fetch_prose.extract_references(doc_md))
    assert urls[1] == "https://doi.org/10.1080/24733938.2024.2357568"
    # Reference 49 is a dashboard with no DOI, so it falls back to its URL.
    assert urls[49] == "https://covidwwtp.spatialstudieslab.org/"


def test_citation_markers_become_links():
    body = r"early work \[1\] and later \[19,20\] and a range \[10–12\]."
    out = fetch_prose.link_citations(body, {1: "u1", 10: "u10", 12: "u12",
                                            19: "u19", 20: "u20"})
    assert "[[1](u1)]" in out
    assert "[[19](u19),[20](u20)]" in out
    assert "[[10](u10)–[12](u12)]" in out


def test_citation_without_a_url_stays_plain_text():
    out = fetch_prose.link_citations(r"see \[7\].", {})
    assert out == "see [7]."


def test_equal_contribution_marker_is_superscripted():
    # Google Docs exports the superscript affiliation digit as "²" but has no
    # superscript form for "&", so the marker arrives split. It must render as
    # one raised marker.
    assert fetch_prose._superscript_markers("O'Connor&²") == "O'Connor<sup>&amp;2</sup>"


def test_standalone_ampersand_is_left_alone():
    assert fetch_prose._superscript_markers("& denotes equal contribution") == \
        "& denotes equal contribution"


def test_supplement_drops_the_online_methods_heading(doc_md):
    supp = fetch_prose.extract_supplement(doc_md)
    assert "Online supplemental methods" not in supp
    assert "### Community wastewater comparison" in supp


def test_preprint_note_is_extracted(doc_md):
    note = fetch_prose._section_body(doc_md, "Preprint only")
    assert note and "dholab.github.io" in note


def test_preprint_note_is_not_in_the_shared_frontmatter(doc_md):
    # The note belongs to the preprint PDF and the site only, so it must not be
    # folded into _frontmatter.md, which both PDFs include.
    fm = fetch_prose.extract_frontmatter(doc_md)
    assert "recommended way to view" not in fm


def test_figure_anchors_survive_a_recount(doc_md):
    """Anchors must not embed a detection count.

    "Houston accounted for 8 of the 15 detections" broke the build the moment
    the dataset was re-extracted. Simulate a recount and confirm every figure
    still places."""
    body = fetch_prose.normalize(doc_md)
    recounted = (body.replace("7 of the 13", "5 of the 11")
                     .replace("13 filters", "11 filters"))
    placed = fetch_prose.place_figures(recounted)
    for _, partial in fetch_prose.FIGURE_ANCHORS:
        assert "{{< include " + partial + " >}}" in placed


def test_verified_links_override_the_derived_doi(doc_md):
    """A DOI that resolves to the publisher's 404 must be replaced.

    Reference 36's DOI returns HTTP 200 and lands on an Emerging Infectious
    Diseases error page, so scripts/resolve_citation_links.py records the PubMed
    record instead. Confirm the cache actually wins over the derived DOI."""
    urls = fetch_prose.citation_urls(fetch_prose.extract_references(doc_md))
    assert urls[36].startswith("https://pubmed.ncbi.nlm.nih.gov/")


def test_every_citation_still_has_a_link(doc_md):
    urls = fetch_prose.citation_urls(fetch_prose.extract_references(doc_md))
    assert len(urls) == 49
    assert all(u.startswith("https://") for u in urls.values())
