#!/usr/bin/env python3
"""Build PREVIEW.md — a private, GitHub-viewable rendering of the manuscript.

GitHub renders markdown text and static images but strips iframes/scripts, so
this preview embeds the *static* figure PNGs (not the interactive Plotly
versions). It exists so the team can read the manuscript inside the private
repo while the public GitHub Pages site is held back.

Regenerate after editing the Google Doc:

    python scripts/fetch_prose.py      # refresh _prose.md from the Doc
    cd analysis && uv run python make_figures.py && cd ..   # refresh figures
    python scripts/build_preview.py    # rebuild PREVIEW.md
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROSE = ROOT / "_prose.md"
OUT = ROOT / "PREVIEW.md"

TITLE = "Air sampling in team congregate spaces for early detection of respiratory virus threats"
SUBTITLE = "Viral air sampling in team settings"
AUTHORS = (
    "David Simon, Timothy Locksmith, Nick Minor, Eli J. O'Connor, "
    "Shelby L. O'Connor†, David H. O'Connor† (corresponding: dhoconno@wisc.edu)"
)

FIG1 = """
![Figure 1: respiratory-virus detections across the World Cup](analysis/figure1_static.png)

**Figure 1. Respiratory-virus detections in team-space air samples across the 2026 FIFA World Cup.**
Air was sampled continuously in Team Canada congregate spaces across five host
cities from 3 June to 4 July 2026, and every cartridge was tested for
SARS-CoV-2, influenza A, influenza B, and RSV. All cities are shown on a single
continuous local-time axis. Rows are the four target viruses; each rectangle is
one cartridge tested for one virus, drawn to its exact sampling window. Rooms
are merged within each city. A box is blue if the virus was detected in any
room (fill mapped to the lowest Ct across rooms), white if no room detected it
but at least one returned a valid negative, and grey if every room was invalid.
An asterisk beneath the axis marks a session with partial room validity.
"""

FIG2 = """
![Figure 2: per-room detections during the Houston period](analysis/figure2_houston.png)

**Figure 2. Per-room detections during the Houston sampling period.**
Sampling in Houston ran from the evening of 30 June to 4 July 2026 across four
team spaces (physiotherapy room, meal room, equipment room, and a team-occupied
hallway). Rows group the four target viruses within each room; the horizontal
axis is local wall-clock time. White boxes are valid negatives, grey boxes are
invalid runs, and blue boxes are detections (fill mapped to Ct). On 1 July,
SARS-CoV-2 was detected in the meal room, physiotherapy room, and hallway, and
influenza A in the equipment room. SARS-CoV-2 returned on 3–4 July at lower Ct,
most strongly in the meal room.
"""

FIG_S1 = """
![Online supplemental figure 1: community wastewater context by host city](analysis/figure3_wastewater.png)

**Online supplemental figure 1. Community wastewater surveillance context in each host city over the 2025–2026 respiratory season.**
Each panel (A to E) is one host city, plotting publicly reported municipal
wastewater levels for the four study targets (SARS-CoV-2, influenza A, influenza
B, and RSV) from August 2025 through mid-July 2026. The shaded gold band marks
Team Canada's air-sampling window in that city. **The four data sources report
non-interchangeable quantities and are each shown on their own independent
vertical axis; levels must be read within a panel and never compared between
panels.** Panels A–C (Montreal, Toronto, Vancouver) use the PHAC wastewater
aggregate (PMMoV-normalized index); panel D (Los Angeles) uses the California
CDPH/CDC-NWSS JWPCP dataset, self-normalized to fecal load; panel E (Houston)
uses the Rice/Houston Health Department 69th Street index (SARS-CoV-2 only,
ending 22 June 2026, before the team's stay). Across all five cities the visit
windows fall in the seasonal trough, at or near each site's own lowest values,
indicating no host city was experiencing unusually high community
respiratory-virus circulation while the team was present.
"""

CENTRAL_FIGURE = """
## Central figure

![Central figure: study workflow, detection timeline across the five host cities, and possible response actions](analysis/central_figure/central_figure.png)

**Central figure. Air sampling for early detection of respiratory-virus threats
in an elite team during competition.** Continuous bioaerosol sampling ran in up
to four team congregate spaces per hotel (meal, equipment, physiotherapy, and
coaches' rooms); each cartridge's filter was eluted on-site and tested on a
Cepheid GeneXpert SARS-CoV-2/Flu/RSV cartridge (top). Across the five host
cities, viral genetic material was detected in team-hotel air in every city; the
timeline shows sampling coverage (band) and each detection (tick) over the
tournament (middle). A positive air signal can trigger low-regret responses —
masking, portable air purifiers, distancing and reduced occupancy, far-UVC,
reinforced ventilation, and excluding visibly ill personnel (bottom).
"""

BANNER = (
    "> **Private preview.** This is a static rendering of the manuscript for "
    "in-repo review while the interactive site is held back. Figures are the "
    "static (print) versions; the interactive Plotly figures appear on the "
    "GitHub Pages site once it is published. Auto-generated by "
    "`scripts/build_preview.py` — do not edit by hand; edit the Google Doc."
)


def insert_after_paragraph(prose: str, needle: str, block: str, label: str) -> str:
    """Insert `block` immediately after the paragraph that contains `needle`.

    Paragraphs are separated by blank lines. Raises if the callout is not found,
    so a Doc edit that drops or renames a figure reference fails loudly rather
    than silently placing figures in the wrong spot.
    """
    paras = prose.split("\n\n")
    for i, para in enumerate(paras):
        if needle in para:
            paras.insert(i + 1, block.strip())
            return "\n\n".join(paras)
    raise SystemExit(
        f"Could not find the {label} callout ('{needle}') in _prose.md — "
        "did the figure reference change in the Doc?"
    )


def main() -> None:
    prose = PROSE.read_text(encoding="utf-8")
    # Drop the auto-generated HTML comment header from _prose.md.
    prose = re.sub(r"<!--.*?-->\n*", "", prose, count=1, flags=re.S)
    # The Quarto anchor links don't resolve on GitHub; make them plain text.
    prose = prose.replace("[Figure 1](#fig-detections)", "Figure 1")
    prose = prose.replace("[Figure 2](#fig-houston)", "Figure 2")
    # Drop an editorial word-count note the author added to the Abstract heading.
    prose = re.sub(r"^(##\s+Abstract)\s*\([^)]*\)\s*$", r"\1", prose, flags=re.M)
    prose = prose.strip()

    # Place each figure right after the paragraph that first calls it out. In the
    # current Doc, Figure 1 is introduced in the Sampling overview and Figure 2
    # in the Detections-by-city paragraph; the wastewater supplemental figure is
    # anchored to the bridging sentence that survived in the main-text Results.
    prose = insert_after_paragraph(
        prose, "summarized in Figure 1", FIG1, "Figure 1"
    )
    prose = insert_after_paragraph(
        prose, "Houston accounted for 8 of the 15 detections (Figure 2)",
        FIG2, "Figure 2",
    )
    prose = insert_after_paragraph(
        prose, "online supplemental methods and online supplementary figure 1",
        FIG_S1, "wastewater supplemental figure",
    )

    doc = (
        f"# {TITLE}\n\n"
        f"*{SUBTITLE}*\n\n"
        f"{AUTHORS}\n\n"
        f"† equal contribution\n\n"
        f"{BANNER}\n\n"
        f"{CENTRAL_FIGURE}\n"
        "---\n\n"
        f"{prose}\n"
    )
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
