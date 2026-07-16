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


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    md = normalize(fetch(source))
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT} ({len(md)} bytes)")


if __name__ == "__main__":
    main()
