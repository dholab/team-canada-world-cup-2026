#!/usr/bin/env python3
"""Fetch the manuscript content from the (link-viewable) Google Doc and
normalize it into six files at the repo root, for Quarto.

Run with no arguments to fetch from the Doc export endpoint, or pass a local
markdown file to normalize that instead (useful for offline testing):

    python scripts/fetch_prose.py                 # fetch from Google Docs
    python scripts/fetch_prose.py raw_export.md   # normalize a local file

This writes six outputs from the Doc: `_title.yml` (title, optional subtitle,
keywords), `_frontmatter.md` (authors, affiliations, ORCID iDs, corresponding
author), `_prose.md` (the manuscript body, Abstract through the required end
statements), `_legends/*.md` (one file per figure legend), `_references.md`
(the numbered bibliography), and `_supplement.md` (the online supplemental
methods).

Why this exists: the Doc is authored with front-matter, submission boilerplate,
and empty divider headers that should not appear on the rendered page. This
script keeps the manuscript body and strips the rest. The interactive/static
figures are supplied by index.qmd, not by the Doc; the references and
supplemental methods are pulled from the Doc by this script.
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

DOC_ID = "15X-Ae_qRDW37zmpdA9_6WPI9GPfRsK0hiWC7FYlwy4c"
EXPORT_URL = f"https://docs.google.com/document/d/{DOC_ID}/export?format=md"

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "_prose.md"
LEGENDS_DIR = HERE.parent / "_legends"
FRONTMATTER = HERE.parent / "_frontmatter.md"
REFERENCES = HERE.parent / "_references.md"
SUPPLEMENT = HERE.parent / "_supplement.md"

BANNER = (
    "<!-- AUTO-GENERATED from the manuscript Google Doc by "
    "scripts/fetch_prose.py. Do not edit by hand; edit the Doc. -->\n\n"
)
# Quarto metadata file carrying the Doc's title + running head, fed to the
# render via `metadata-files` in _quarto.yml so index.qmd hard-codes neither.
TITLE_YML = HERE.parent / "_title.yml"

# The Doc's title is its single top-level "# " heading; the running head follows
# as "**Short title / running head:** ...". Both are pulled so the title page
# tracks the Doc rather than a hand-edited copy in index.qmd.
DOC_TITLE = re.compile(r"^#\s+(?P<title>\S.*?)\s*$", re.M)
DOC_RUNNING = re.compile(
    r"^\*\*\s*Short title\s*/\s*running head:\s*\*\*\s*(?P<sub>.+?)\s*$", re.M | re.I)

# Author front matter lives in its own Doc sections before the Abstract. We pull
# Authors, Affiliations, ORCID iDs, and Corresponding author so the title-page
# block comes from the Doc (Twitter handles and Manuscript metrics are Doc-only
# working notes and are intentionally skipped).
FRONTMATTER_SECTIONS = ["Authors", "Affiliations", "ORCID iDs", "Corresponding author"]

# The Doc's "Preprint only" section points readers at the interactive site. It
# belongs in the bioRxiv/preprint PDF and on the site, but NOT in the journal
# submission PDF, so it is written to its own file and included conditionally
# rather than folded into _frontmatter.md.
PREPRINT_NOTE = HERE.parent / "_preprint_note.md"

# The figure legends live in their own Doc sections, after References. Each is a
# bold-led paragraph "**Figure N. Title.** body...". We pull them so the
# manuscript's captions come from the Doc, not from hand-edited copies. Quarto
# supplies its own "Figure N" number, so we strip the leading "Figure N." label
# and keep the bold title plus body.
#   key "fig1"  <- "Figure 1. ..."
#   key "supp1" <- "Online supplemental figure 1. ..."
LEGEND_LEAD = re.compile(
    r"^\*\*\s*(?P<kind>Online supplemental figure|Figure)\s+(?P<num>\d+)\s*\\?\.\s*")

# The body we keep starts at "## Abstract" and ends just before the trailing
# boilerplate sections that Quarto supplies itself.
# The Abstract heading may carry a trailing note such as "(233 words)", so match
# the heading prefix rather than requiring the line to end at "Abstract".
BODY_START = re.compile(r"^##\s+Abstract\b.*$", re.M)
# Everything from "## References" onward is boilerplate/placeholder in the Doc.
BODY_END = re.compile(r"^##\s+References\b.*$", re.M)

# The Doc's References section lists each entry as its own heading:
#   "## 1 \t[Serner A, … doi: 10.1080/…](http://paperpile.com/b/tA670F/58gc)"
# We keep the link text (the formatted citation) and drop the Paperpile URL,
# exactly as normalize() already does for inline citation markers.
REFERENCE_ENTRY = re.compile(
    r"^##\s+(?P<num>\d+)\s*\[(?P<text>.+?)\]\("
    r"https?://(?:www\.)?paperpile\.com/[^)]*\)\s*$",
    re.M,
)


def fetch(source: str | None) -> str:
    if source:
        return Path(source).read_text(encoding="utf-8")
    req = urllib.request.Request(EXPORT_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def normalize(md: str, cite_urls: dict[int, str] | None = None) -> str:
    start = BODY_START.search(md)
    if not start:
        raise SystemExit("Could not find '## Abstract' — Doc structure changed?")
    end = BODY_END.search(md, start.end())
    body = md[start.start(): end.start() if end else None]

    # Drop empty divider headers ("## " on their own line, from Doc page breaks).
    body = re.sub(r"^#{1,6}\s*$\n?", "", body, flags=re.M)

    # Unwrap Paperpile hyperlinks: the Doc exports each citation number as a link
    # to paperpile.com, e.g. "[\[1\]](https://paperpile.com/...)". Keep the link
    # text (the citation number, which itself contains escaped brackets) and drop
    # the URL, so the PDF shows plain citation numbers. The interactive version
    # will link to the actual manuscripts instead. The link text is everything
    # from the opening "[" up to the "](http...paperpile...)" tail.
    body = re.sub(
        r"\[((?:[^\[\]]|\\\[|\\\])*)\]\(https?://(?:www\.)?paperpile\.com/[^)]*\)",
        r"\1", body)

    # Inject Quarto cross-references where the prose names the figures, so the
    # actual embedded figures (defined in index.qmd) render inline.
    body = body.replace(
        "Figure 1 \\[merged heat-map\\]", "[Figure 1](#fig-detections)"
    ).replace(
        "Figure 2 \\[per-room heat-map\\]", "[Figure 2](#fig-houston)"
    )

    if cite_urls:
        body = link_citations(body, cite_urls)

    body = place_figures(body)

    # Collapse >2 blank lines.
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"

    return BANNER + body


# Each figure is placed immediately after the paragraph that first cites it, so
# a reader meets the figure where it is discussed instead of finding all of them
# stacked at the end. The anchor is a distinctive phrase from that paragraph;
# the figure markup itself lives in the hand-editable _figN.md partials.
# Anchors are matched as regexes and deliberately avoid any count or Ct value:
# those change whenever the data is re-extracted, and an anchor that embeds one
# breaks the build on every such edit.
FIGURE_ANCHORS = [
    (r"summarized in Figure 1", "_fig1.md"),
    (r"Houston accounted for .{0,20}detections", "_fig2.md"),
    (r"Metagenomic sequencing of air samples", "_fig3.md"),
]


def place_figures(body: str) -> str:
    """Insert each figure include after the paragraph that first cites it.

    Raises if an anchor is missing: a silently unplaced figure would drop it
    from the manuscript entirely, which is far worse than a loud failure."""
    paras = body.split("\n\n")
    for anchor, partial in FIGURE_ANCHORS:
        pat = re.compile(anchor)
        for i, para in enumerate(paras):
            if pat.search(para):
                paras.insert(i + 1, "{{< include " + partial + " >}}")
                break
        else:
            raise SystemExit(
                f"Could not find the anchor for {partial!r} ({anchor!r}) in the "
                "Doc prose. The wording changed — update FIGURE_ANCHORS."
            )
    return "\n\n".join(paras)


# A citation marker in the Doc export is a bracketed run of reference numbers,
# with the brackets backslash-escaped: "\[1\]", "\[19,20\]", "\[10–12\]" (en dash).
CITATION = re.compile(r"\\\[((?:\d+)(?:\s*[,–-]\s*\d+)*)\\\]")


def link_citations(body: str, cite_urls: dict[int, str]) -> str:
    """Turn each inline citation marker into per-number hyperlinks to the source.

    "\\[19,20\\]" becomes "[[19](url),[20](url)]" so a reader can click straight
    through to the paper instead of hunting the reference list. Ranges are kept
    as written ("10–12" stays a range) but each endpoint links; numbers with no
    resolvable URL are left as plain text."""
    def one(num_text: str) -> str:
        n = int(num_text)
        url = cite_urls.get(n)
        return f"[{num_text}]({url})" if url else num_text

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        # Rebuild the run, linking each number and preserving its separators.
        out = re.sub(r"\d+", lambda d: one(d.group(0)), inner)
        return f"[{out}]"

    return CITATION.sub(repl, body)


# A reference entry usually ends with "doi: 10.xxxx/yyyy"; the handful without a
# DOI (dashboards, websites) carry a bare URL instead.
REF_DOI = re.compile(r"doi:\s*(10\.\d{4,9}/\S+?)(?:[.,;)\]]*)$", re.I)
REF_URL = re.compile(r"(https?://[^\s)\]]+?)(?:[.,;)\]]*)(?:\s|$)")


def citation_urls(refs: list[tuple[int, str]]) -> dict[int, str]:
    """Map each reference number to the best link for its source.

    Prefers the DOI (resolves to the publisher's full text, and is the stable
    identifier); falls back to the first plain URL in the entry for the
    dashboards and websites that have no DOI."""
    urls: dict[int, str] = {}
    for num, text in refs:
        m = REF_DOI.search(text.rstrip())
        if m:
            urls[num] = "https://doi.org/" + m.group(1).rstrip(".,;)]")
            continue
        u = REF_URL.search(text)
        if u:
            urls[num] = u.group(1).rstrip(".,;)]")
    return urls


def extract_legends(md: str) -> dict[str, str]:
    """Pull every figure legend from the Doc's '## Figure legends' and
    '## Online supplemental figure legends' sections. Returns {key: caption}.
    For Quarto-numbered main figures the leading 'Figure N.' label is stripped
    (Quarto supplies the number). The unnumbered Central Figure and the
    supplemental figures keep their full label. All figure captions come from
    the Doc; index.qmd includes these files and hard-codes no caption text.
    Keys: central, fig1, fig2, fig3, supp1, ..."""
    # Take everything from the first legends section to the next '## ' that is
    # not itself a legends section (e.g. '## Online supplemental methods').
    sec = re.search(r"^##\s+Figure legends\b.*$", md, re.M)
    if not sec:
        return {}
    region = md[sec.end():]
    # Stop at 'Online supplemental methods' or end of doc; keep both legend
    # subsections in between.
    stop = re.search(r"^##\s+Online supplemental methods\b", region, re.M)
    region = region[: stop.start()] if stop else region

    legends: dict[str, str] = {}
    for para in re.split(r"\n\s*\n", region):
        para = para.strip()
        if not para.startswith("**"):
            continue
        # The Central Figure legend is unnumbered ("**Central Figure: ...**").
        # It is not Quarto-numbered, so keep it verbatim under key "central".
        if re.match(r"^\*\*\s*Central Figure\b", para, re.I):
            legends["central"] = para
            continue
        m = LEGEND_LEAD.match(para)
        if not m:
            continue
        num = m.group("num")
        is_supp = m.group("kind").startswith("Online")
        key = ("supp" if is_supp else "fig") + num
        if is_supp:
            # Supplemental figures are not Quarto-numbered, so keep their full
            # "Online supplemental figure N. ..." label, cleaning the escaped
            # "\." the Doc export inserts after the number.
            caption = re.sub(r"(figure\s+\d+)\\\.", r"\1.", para)
        else:
            # Main figures are Quarto-numbered; drop the "Figure N." label and
            # re-open the bold on the title so the number is not duplicated.
            caption = "**" + para[m.end():].strip()
        legends[key] = caption
    return legends


def extract_references(md: str) -> list[tuple[int, str]]:
    """Pull the numbered reference list from the Doc's '## References' section.

    Returns [(number, citation_text), ...] in Doc order. The Paperpile URL is
    dropped and the export's backslash escapes are undone, so each entry is
    plain formatted Markdown. Raises SystemExit if the numbering is not a
    complete 1..N run — a silently short bibliography would ship a manuscript
    with dangling citation markers."""
    sec = re.search(r"^##\s+References\b.*$", md, re.M)
    if not sec:
        raise SystemExit("Could not find '## References' — Doc structure changed?")
    region = md[sec.end():]
    # Stop at the first non-reference heading with actual text (e.g.
    # '## Figure legends'). The Doc emits bare '## ' divider lines from its page
    # breaks, so require a non-'#' character after the hashes. A heading that
    # merely starts with digits (e.g. a corrupted "## 49x [...") also counts as
    # a stop candidate here — it is filtered back out below if it turns out to
    # be a malformed reference entry rather than a genuine section boundary, so
    # a corrupted/dropped final entry is caught instead of silently truncating.
    stop = re.search(r"^##\s+(?!\d+\s*\[)[^\s#].*$", region, re.M)
    boundary = stop.start() if stop else len(region)
    region_for_refs = region[:boundary]

    refs: list[tuple[int, str]] = []
    for m in REFERENCE_ENTRY.finditer(region_for_refs):
        text = m.group("text")
        # Undo the markdown export's escaping of literal punctuation. The Doc
        # export also escapes a literal ")" in dashboard/URL references like
        # "(accessed 16 July 2026\)", so ")" is included alongside the brief's
        # original set.
        text = re.sub(r"\\([.\-\[\]&#)])", r"\1", text).strip()
        refs.append((int(m.group("num")), text))

    if not refs:
        raise SystemExit("Parsed zero references from the Doc's References section.")
    expected = list(range(1, len(refs) + 1))
    # A heading that stopped the scan but still looks like a numbered reference
    # entry (leading digits, e.g. a corrupted "## 49x [...") means an entry was
    # dropped rather than the section genuinely ending — treat that as a count
    # mismatch too, rather than silently accepting the shorter, still-sequential
    # list that precedes it.
    stopped_on_numbered_heading = bool(stop and re.match(r"^##\s+\d", stop.group()))
    if [n for n, _ in refs] != expected or stopped_on_numbered_heading:
        raise SystemExit(
            f"Reference numbering is not a complete 1..{len(refs)} run: "
            f"got {[n for n, _ in refs]}"
        )
    return refs


def write_legends(legends: dict[str, str]) -> None:
    LEGENDS_DIR.mkdir(exist_ok=True)
    for key, caption in legends.items():
        (LEGENDS_DIR / f"{key}.md").write_text(BANNER + caption + "\n",
                                               encoding="utf-8")
    print(f"wrote {len(legends)} legends to {LEGENDS_DIR}: "
          + ", ".join(sorted(legends)))


def write_references(md: str) -> None:
    """Write the Doc's bibliography to _references.md as a numbered list.

    Numbers are written explicitly (not left to Markdown auto-numbering) so the
    rendered list always matches the inline citation markers in the prose."""
    refs = extract_references(md)
    body = "\n\n".join(f"{num}. {text}" for num, text in refs)
    REFERENCES.write_text(BANNER + body + "\n", encoding="utf-8")
    print(f"wrote {REFERENCES} ({len(refs)} references)")


def extract_supplement(md: str, cite_urls: dict[int, str] | None = None) -> str:
    """Pull the Doc's '## Online supplemental methods' section through the end
    of the document. This sits after '## References' in the Doc, so the main
    body normalizer never sees it.

    The Doc's own '## Online supplemental methods' heading is dropped: index.qmd
    supplies the section heading, and on a page that IS the online version the
    word "online" is redundant. The subsections (e.g. '### Community wastewater
    comparison') are kept."""
    sec = re.search(r"^##\s+Online supplemental methods\b.*$", md, re.M)
    if not sec:
        raise SystemExit(
            "Could not find '## Online supplemental methods' — Doc structure changed?"
        )
    body = md[sec.end():]
    # Same Paperpile unwrapping the main body gets: keep the citation marker
    # text, drop the URL.
    body = re.sub(
        r"\[((?:[^\[\]]|\\\[|\\\])*)\]\(https?://(?:www\.)?paperpile\.com/[^)]*\)",
        r"\1", body)
    if cite_urls:
        body = link_citations(body, cite_urls)
    body = re.sub(r"^#{1,6}\s*$\n?", "", body, flags=re.M)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body


def write_supplement(md: str, cite_urls: dict[int, str] | None = None) -> None:
    body = extract_supplement(md, cite_urls)
    SUPPLEMENT.write_text(BANNER + body, encoding="utf-8")
    print(f"wrote {SUPPLEMENT} ({len(body)} bytes)")


def extract_keywords(md: str) -> list[str]:
    """The Doc's '### Keywords' section, one comma-separated line."""
    body = _section_body(md, "Keywords")
    if not body:
        return []
    return [kw.strip() for kw in body.replace("\n", " ").split(",") if kw.strip()]


def _section_body(md: str, name: str) -> str | None:
    """Return the text of a '### <name>' section, up to the next ## or ### heading."""
    m = re.search(rf"^###\s+{re.escape(name)}\s*$", md, re.M)
    if not m:
        return None
    rest = md[m.end():]
    nxt = re.search(r"^#{2,3}\s+\S", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    # Collapse trailing hard-break spaces the Doc export leaves on each line.
    body = re.sub(r"[ \t]+$", "", body, flags=re.M).strip()
    return body


# The Doc superscripts both the affiliation number and the "&" equal-contribution
# marker, but the markdown export can only carry the digits: Unicode has
# superscript forms for 0-9 (¹²³…) and none for "&", so the marker flattens to a
# plain "&" sitting on the baseline next to a raised digit. Re-raise it, and fold
# the neighbouring Unicode superscript digits into the same <sup> so the whole
# marker sits on one line.
SUPERSCRIPT_DIGITS = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
                      "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
MARKER_RUN = re.compile(r"&([" + "".join(SUPERSCRIPT_DIGITS) + r"]*)")


def _superscript_markers(text: str) -> str:
    """Render "&²" as a single superscript "&2" marker.

    Only touches a "&" that is directly followed by superscript digits or that
    directly follows one, which is how the equal-contribution marker appears; a
    standalone ampersand in prose (e.g. the "& denotes equal contribution"
    legend) is left alone."""
    def repl(m: re.Match[str]) -> str:
        digits = "".join(SUPERSCRIPT_DIGITS[c] for c in m.group(1))
        return f"<sup>&amp;{digits}</sup>" if digits else m.group(0)

    return MARKER_RUN.sub(repl, text)


def extract_frontmatter(md: str) -> str:
    """Build the title-page author block from the Doc's Authors / Affiliations /
    ORCID iDs / Corresponding author sections. Returns Markdown with bold section
    labels, matching how the block renders on the title page."""
    parts = []
    labels = {
        "Authors": "Authors",
        "Affiliations": "Affiliations",
        "ORCID iDs": "ORCID iDs",
        "Corresponding author": "Corresponding author",
    }
    for name in FRONTMATTER_SECTIONS:
        body = _section_body(md, name)
        if not body:
            continue
        # Unescape the Doc export's "\[confirm\]" so ORCID placeholders read cleanly.
        body = body.replace("\\[", "[").replace("\\]", "]")
        if name == "Authors":
            body = _superscript_markers(body)
        parts.append(f"**{labels[name]}**\n\n{body}")
    return "\n\n".join(parts)


def write_preprint_note(md: str) -> None:
    """Write the Doc's 'Preprint only' section to its own file.

    Absent from the Doc, an empty file is written so the include in index.qmd
    still resolves — a missing include is a hard Quarto error."""
    body = _section_body(md, "Preprint only") or ""
    if body:
        body = body.replace("\\[", "[").replace("\\]", "]")
    PREPRINT_NOTE.write_text(BANNER + body + "\n", encoding="utf-8")
    print(f"wrote {PREPRINT_NOTE} ({len(body)} bytes)"
          + ("" if body else " — no 'Preprint only' section in the Doc"))


def write_frontmatter(md: str) -> None:
    block = extract_frontmatter(md)
    FRONTMATTER.write_text(BANNER + block + "\n", encoding="utf-8")
    print(f"wrote {FRONTMATTER} ({len(block)} bytes)")


def _yaml_quote(s: str) -> str:
    """Double-quote a scalar for YAML, escaping backslashes and quotes."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_title(md: str) -> None:
    """Pull the Doc's title (its single '# ' heading) and running head into a
    Quarto metadata file, so index.qmd carries no hard-coded title/subtitle.
    The Doc's markdown export escapes some characters (e.g. a literal '#'); undo
    the ones that appear in titles."""
    tm = DOC_TITLE.search(md)
    if not tm:
        raise SystemExit("Could not find the Doc's '# ' title heading.")
    title = tm.group("title").replace("\\#", "#").replace("\\&", "&").strip()
    lines = [
        "# AUTO-GENERATED from the manuscript Google Doc by "
        "scripts/fetch_prose.py. Do not edit by hand; edit the Doc.",
        f"title: {_yaml_quote(title)}",
    ]
    sm = DOC_RUNNING.search(md)
    if sm:
        sub = sm.group("sub").replace("\\#", "#").replace("\\&", "&").strip()
        lines.append(f"subtitle: {_yaml_quote(sub)}")
    keywords = extract_keywords(md)
    if keywords:
        lines.append("keywords:")
        lines.extend(f"  - {_yaml_quote(kw)}" for kw in keywords)
    TITLE_YML.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {TITLE_YML}: title={title!r}"
          + (f", subtitle={sub!r}" if sm else ""))


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    raw = fetch(source)
    write_title(raw)
    write_frontmatter(raw)
    write_preprint_note(raw)
    write_legends(extract_legends(raw))
    write_references(raw)
    # Inline citation markers link straight to each source, so the rendered
    # manuscript is navigable rather than carrying bare numbers.
    cite_urls = citation_urls(extract_references(raw))
    write_supplement(raw, cite_urls)
    md = normalize(raw, cite_urls)
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT} ({len(md)} bytes, {len(cite_urls)} citation links)")


if __name__ == "__main__":
    main()
