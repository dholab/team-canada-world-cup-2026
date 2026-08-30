#!/usr/bin/env python3
"""Collect the journal submission figure files into submission/figures/.

Eurosurveillance wants each figure as a separate file, in vector form where
possible, not embedded in the manuscript document. This script gathers the
figures the analysis scripts already build, names them the way a submission
system expects (Figure_1.pdf, ...), and reports anything that is raster-only so
it can be fixed before upload rather than discovered by an editor.

Run the figure scripts first:

    cd analysis && uv sync \\
      && uv run python make_figures_1_2_detections.py \\
      && uv run python make_figure_3_sequencing.py \\
      && uv run python make_supplement_1_wastewater.py

then from the repo root:

    python scripts/build_submission_figures.py

Exit status is non-zero if any required figure is missing, so CI can gate on it.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "analysis" / "figures"
CENTRAL = ROOT / "analysis" / "central_figure"
OUT = ROOT / "submission" / "figures"

# (submission name, preferred vector source, raster fallback)
# The vector source is used when present; the raster is copied only as a
# fallback and is reported as a warning, because journals prefer vector.
FIGURE_SOURCES = [
    ("Figure_1", FIGURES / "figure1_detections_static.pdf",
     FIGURES / "figure1_detections_static.png"),
    ("Figure_2", FIGURES / "figure2_houston.pdf",
     FIGURES / "figure2_houston.png"),
    ("Figure_3", FIGURES / "figure3_sequencing.pdf",
     FIGURES / "figure3_sequencing.png"),
    # Figure 4 (the former Central Figure) is assembled in Illustrator and only
    # its raster export is kept in this repo; the editable .ai and its vector
    # PDF export live in the manuscript's Google Drive folder. If a vector PDF
    # has been dropped in beside the PNG it is used; otherwise the PNG is copied
    # and flagged. See analysis/central_figure/README.md.
    ("Figure_4", CENTRAL / "central_figure.pdf",
     CENTRAL / "central_figure.png"),
    ("Supplementary_Figure_S1", FIGURES / "supplement1_wastewater.pdf",
     FIGURES / "supplement1_wastewater.png"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*"):
        if stale.is_file():
            stale.unlink()

    missing: list[str] = []
    raster_only: list[str] = []
    written: list[Path] = []

    for name, vector, raster in FIGURE_SOURCES:
        if vector.exists():
            dest = OUT / f"{name}{vector.suffix}"
            shutil.copy2(vector, dest)
            written.append(dest)
        elif raster.exists():
            dest = OUT / f"{name}{raster.suffix}"
            shutil.copy2(raster, dest)
            written.append(dest)
            raster_only.append(f"{name}: no vector at {vector.relative_to(ROOT)}, "
                               f"copied raster {raster.relative_to(ROOT)}")
        else:
            missing.append(f"{name}: neither {vector.relative_to(ROOT)} nor "
                           f"{raster.relative_to(ROOT)} exists")

    for dest in written:
        size_kb = dest.stat().st_size / 1024
        print(f"  {dest.relative_to(ROOT)}  ({size_kb:,.0f} KB)")

    if raster_only:
        print("\nWARNING - raster only, journals ask for vector:")
        for line in raster_only:
            print(f"  {line}")
        print("  Export a vector PDF from the Illustrator master and place it "
              "at the path above, then re-run.")

    if missing:
        print("\nERROR - missing figures:", file=sys.stderr)
        for line in missing:
            print(f"  {line}", file=sys.stderr)
        print("\nRun the analysis figure scripts first (see this file's "
              "docstring).", file=sys.stderr)
        return 1

    print(f"\n{len(written)} figure file(s) in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
