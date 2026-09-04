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


def test_verified_links_override_the_derived_doi():
    """A DOI that resolves to the publisher's 404 must be replaced.

    The Emerging Infectious Diseases entry ("Non-SARS-CoV-2 Respiratory Viruses
    in Athletes at Major Winter Sport Events") has a DOI that returns HTTP 200
    but lands on the publisher's error page, so
    scripts/resolve_citation_links.py records the PubMed record instead.
    Confirm the cache actually wins over the derived DOI.

    The reference is found by title, and checked against the live bibliography
    rather than the fixture: the override is keyed by reference number, and
    those shift whenever references are added or removed, so pinning a number
    here made this test fail for a reason unrelated to what it checks."""
    import json
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    # _references.md is rendered output ("12. Author A, ..."), not a Doc export,
    # so read the numbering straight off it.
    refs = re.findall(r"^(\d+)\. (.+)$",
                      (root / "_references.md").read_text(), re.M)
    links = json.loads((root / "_citation_links.json").read_text())

    target = [n for n, text in refs
              if "Non-SARS-CoV-2 Respiratory Viruses" in text]
    assert target, "the dead-DOI EID reference is no longer in the bibliography"
    assert links[target[0]].startswith("https://pubmed.ncbi.nlm.nih.gov/"), (
        "expected the dead EID DOI to fall back to its PubMed record; "
        "re-run scripts/resolve_citation_links.py"
    )


def test_every_citation_still_has_a_link(doc_md):
    urls = fetch_prose.citation_urls(fetch_prose.extract_references(doc_md))
    assert len(urls) == 49
    assert all(u.startswith("https://") for u in urls.values())


def test_references_parse_with_paperpiles_escaped_period(doc_md):
    """Paperpile's numbered style emits "## 1\\. \t[...]", not "## 1 \t[...]".

    The Doc switched to that style when the bibliography was reformatted for
    submission, and it silently broke reference parsing twice over: the entry
    regex did not allow the escaped period, and the section-boundary regex read
    each numbered entry as the start of a new section, truncating the list to
    nothing. Both are easy to reintroduce, so pin the behaviour here."""
    escaped = doc_md.replace("\n## 1 \t[", "\n## 1\\. \t[") \
                    .replace("\n## 2 \t[", "\n## 2\\. \t[")
    assert "## 1\\. \t[" in escaped, "fixture format changed; update this test"
    refs = fetch_prose.extract_references(escaped)
    plain = fetch_prose.extract_references(doc_md)
    assert [n for n, _ in refs] == [n for n, _ in plain]
    assert refs[0][1] == plain[0][1]


def test_supplement_heading_matches_either_journals_wording(doc_md):
    """The Doc carried BJSM's "Online supplemental methods" and now carries
    Eurosurveillance's "Supplementary material". Both must resolve, or the
    supplement silently vanishes from the build."""
    renamed = doc_md.replace("## Online supplemental methods",
                             "## Supplementary material")
    body = fetch_prose.extract_supplement(renamed)
    assert "wastewater" in body.lower()
    assert "## Supplementary material" not in body


def test_preprint_note_falls_back_when_the_doc_drops_the_section(doc_md):
    """The Eurosurveillance reformat removed the Doc's "Preprint only" section.
    The medRxiv build still needs the pointer, so a default stands in rather
    than the note silently disappearing."""
    without = doc_md.replace("### Preprint only", "### Removed section")
    assert fetch_prose._section_body(without, "Preprint only") in (None, "")
    assert "dholab.github.io" in fetch_prose.DEFAULT_PREPRINT_NOTE


def test_doi_is_recognised_in_both_bibliography_styles():
    """The Doc's original style wrote "doi: 10.xxxx/yyy"; the reformatted
    bibliography writes "Available from: http://dx.doi.org/10.xxxx/yyy".

    resolve_citation_links.py only understood the first, so after the reformat
    every reference resolved to no DOI, the run aborted before writing, and the
    committed link cache silently stayed on the OLD numbering — which
    mislabelled every citation past the point the bibliography changed."""
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "rcl", root / "scripts" / "resolve_citation_links.py")
    rcl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rcl)

    old = ("Serner A, et al. Time-loss injuries. Sci Med Footb. 2025;9:275-82. "
           "doi: 10.1080/24733938.2024.2357568")
    new = ("Serner A, et al. Time-loss injuries. Sci Med Footb [Internet]. "
           "2025 Aug;9(3):275-82. Available from: "
           "http://dx.doi.org/10.1080/24733938.2024.2357568")
    assert rcl.doi_of(old) == "10.1080/24733938.2024.2357568"
    assert rcl.doi_of(new) == "10.1080/24733938.2024.2357568"


def test_citation_link_cache_covers_exactly_the_current_references():
    """A cache keyed by stale numbering is worse than no cache: it silently
    points citations at the wrong papers. Keep the committed map in step with
    the committed bibliography."""
    import json
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    refs = re.findall(r"^(\d+)\. ", (root / "_references.md").read_text(), re.M)
    links = json.loads((root / "_citation_links.json").read_text())
    assert set(links) == set(refs), (
        "_citation_links.json is out of step with _references.md; "
        "re-run scripts/resolve_citation_links.py"
    )


def test_key_public_health_message_is_kept_in_the_body():
    """Eurosurveillance requires the "Key public health message" box, and it
    sits AHEAD of the Abstract in the Doc. Anchoring the body to "## Abstract"
    silently dropped a mandatory section from both PDFs."""
    doc = ("## Key public health message\n\nWhat did we address?\n\n"
           "## Abstract\n\n**Background.** Text.\n\n"
           "Detections are summarized in Figure 1.\n\n"
           "Houston accounted for 7 of the 13 detections.\n\n"
           "We used metagenomic sequencing with Illumina VSP2.\n\n"
           "Figure 4 summarises the study design.\n\n"
           "## References\n")
    body = fetch_prose.normalize(doc)
    assert "Key public health message" in body
    assert "## Abstract" in body


def test_body_still_starts_at_abstract_without_a_key_message_box():
    doc = ("## Abstract\n\n**Background.** Text.\n\n"
           "Detections are summarized in Figure 1.\n\n"
           "Houston accounted for 7 of the 13 detections.\n\n"
           "We used metagenomic sequencing with Illumina VSP2.\n\n"
           "Figure 4 summarises the study design.\n\n"
           "## References\n")
    body = fetch_prose.normalize(doc)
    assert body.lstrip().startswith("<!-- AUTO-GENERATED")
    assert "## Abstract" in body


def test_alt_text_is_stripped_from_rendered_output():
    """"Alt text:" paragraphs are submission metadata for the typesetter. They
    belong in the Doc but not in the site or the PDFs, where repeating each
    figure description under its caption just duplicates the legend."""
    body = ("**Figure 1. A caption.** Some description.\n\n"
            "Alt text: A grid of coloured rectangles spanning\n"
            "two source lines.\n\n"
            "The next real paragraph.\n")
    out = fetch_prose.strip_alt_text(body)
    assert "Alt text" not in out
    assert "two source lines" not in out
    assert "**Figure 1. A caption.**" in out
    assert "The next real paragraph." in out


def test_anonymised_manuscript_carries_no_author_identifiers():
    """Eurosurveillance reviews anonymised manuscripts: "All author-identifiable
    information - authors' names, affiliations and contributions, as well as any
    acknowledgements - should NOT be included in the document."

    The subtle leaks are not the author list (obvious) but the institutional
    review board, the sequencing core, and the Data availability URLs, which
    resolve to the authors' own GitHub organisation and institutional host.
    Self-citations in the reference list are unavoidable and are not checked."""
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "esdocx", root / "scripts" / "build_eurosurveillance_docx.py")
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except ModuleNotFoundError:          # python-docx not installed in this env
        import pytest
        pytest.skip("python-docx not available")

    sections = mod.parse_sections((root / "_prose.md").read_text())
    dropped = {h for _, h, _ in sections} & mod.DROP_SECTIONS
    assert dropped, "expected identifying sections to be present before removal"

    kept = []
    for _, head, paras in sections:
        if head in mod.DROP_SECTIONS or head == "Key public health message":
            continue
        for para in paras:
            text = mod.clean(para)
            if head == "Data availability":
                text = mod.DATA_AVAILABILITY_ANON
            else:
                for pat, rep in mod.DEIDENTIFY:
                    import re
                    text = re.sub(pat, rep, text)
            kept.append(text)
    body = "\n".join(kept)

    for leak in ["Wisconsin", "Madison", "dholab", "dholk", "wisc.edu",
                 "Pathogenuity", "Melbourne", "Inkfish", "Heart of Racing",
                 "PRJNA", "github.com"]:
        assert leak not in body, f"{leak!r} leaks into the anonymised manuscript"


def test_anonymised_manuscript_includes_every_figure_legend():
    """Eurosurveillance takes figures as separate files, so the legends in the
    manuscript are where a reviewer reads what each figure shows. They live in
    _legends/figN.md (and, for the supplementary figure, inside _supplement.md)
    rather than in _prose.md, so they are easy to omit from a .docx built only
    from the prose -- which is exactly what happened."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for n in (1, 2, 3, 4):
        assert (root / "_legends" / f"fig{n}.md").exists(), f"fig{n} legend missing"
    supp = (root / "_supplement.md").read_text()
    assert "Supplementary Figure S1" in supp, "supplementary legend missing"
