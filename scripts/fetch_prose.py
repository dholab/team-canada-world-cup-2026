#!/usr/bin/env python3
"""Fetch the manuscript prose from the (link-viewable) Google Doc and normalize
it into manuscript/_prose.md for Quarto.

Run with no arguments to fetch from the Doc export endpoint, or pass a local
markdown file to normalize that instead (useful for offline testing):

    python scripts/fetch_prose.py                 # fetch from Google Docs
    python scripts/fetch_prose.py raw_export.md   # normalize a local file

Why this exists: the Doc is authored with front-matter, submission boilerplate,
and empty divider headers that should not appear on the rendered page. This
script keeps the manuscript body (Abstract through the required end statements)
and strips the rest. The interactive/static figures and the References section
are supplied by manuscript/index.qmd, not by the Doc.
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


def fetch(source: str | None) -> str:
    if source:
        return Path(source).read_text(encoding="utf-8")
    req = urllib.request.Request(EXPORT_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def normalize(md: str) -> str:
    start = BODY_START.search(md)
    if not start:
        raise SystemExit("Could not find '## Abstract' — Doc structure changed?")
    end = BODY_END.search(md, start.end())
    body = md[start.start(): end.start() if end else None]

    # Drop empty divider headers ("## " on their own line, from Doc page breaks).
    body = re.sub(r"^#{1,6}\s*$\n?", "", body, flags=re.M)

    # Inject Quarto cross-references where the prose names the figures, so the
    # actual embedded figures (defined in index.qmd) render inline.
    body = body.replace(
        "Figure 1 \\[merged heat-map\\]", "[Figure 1](#fig-detections)"
    ).replace(
        "Figure 2 \\[per-room heat-map\\]", "[Figure 2](#fig-houston)"
    )

    # Collapse >2 blank lines.
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"

    header = (
        "<!-- AUTO-GENERATED from the manuscript Google Doc by "
        "scripts/fetch_prose.py. Do not edit by hand; edit the Doc. -->\n\n"
    )
    return header + body


def extract_legends(md: str) -> dict[str, str]:
    """Pull each figure legend from the Doc's '## Figure legends' and
    '## Online supplemental figure legends' sections. Returns {key: caption},
    with the leading 'Figure N.' label stripped and the escaped '\\.' cleaned,
    so index.qmd can include the caption under a Quarto-numbered figure.
    Keys: fig1, fig2, fig3, supp1, ...  Only 'Figure' and 'Online supplemental
    figure' paragraphs are kept (a 'Central Figure' paragraph, which has no
    number, is skipped here and stays authored in index.qmd)."""
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
        m = LEGEND_LEAD.match(para)
        if not m:
            continue  # e.g. the unnumbered "**Central Figure: ...**" paragraph
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


def write_legends(legends: dict[str, str]) -> None:
    LEGENDS_DIR.mkdir(exist_ok=True)
    banner = ("<!-- AUTO-GENERATED from the manuscript Google Doc by "
              "scripts/fetch_prose.py. Do not edit by hand; edit the Doc. -->\n\n")
    for key, caption in legends.items():
        (LEGENDS_DIR / f"{key}.md").write_text(banner + caption + "\n",
                                               encoding="utf-8")
    print(f"wrote {len(legends)} legends to {LEGENDS_DIR}: "
          + ", ".join(sorted(legends)))


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    raw = fetch(source)
    write_legends(extract_legends(raw))
    md = normalize(raw)
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT} ({len(md)} bytes)")


if __name__ == "__main__":
    main()
