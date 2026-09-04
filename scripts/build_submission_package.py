#!/usr/bin/env python3
"""Assemble the ready-to-upload submission packages.

Two destinations, built from the same CI-rendered outputs:

  submission/eurosurveillance/  cover letter, manuscript PDF, and each figure
                                as its own vector file (the journal wants
                                figures as separate files, not embedded)
  submission/medrxiv/           the preprint PDF plus the same figure files

Run after CI has rebuilt docs/*.pdf and after
scripts/build_submission_figures.py has refreshed submission/figures/:

    python scripts/build_submission_package.py

Exit status is non-zero if anything required is missing, so this can gate a
submission.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "submission" / "figures"
DOCX = ROOT / "submission" / "_docx"
OUT = ROOT / "submission"

# The Illustrator/InDesign sources live in the manuscript's Google Drive folder,
# not this repo. The cover letter is authored there, so it is copied in if
# present and reported as missing (not fatal for the preprint) if not.
DRIVE = Path.home() / (
    "Library/CloudStorage/GoogleDrive-dhoconno@wisc.edu/My Drive/Manuscripts/"
    "DHO Manuscripts/Pending/2026-07 Team Canada air sampling"
)
COVER_LETTER = DRIVE / "cover letter" / "cover letter 2026-08-30.pdf"

FIGURE_FILES = ["Figure_1.pdf", "Figure_2.pdf", "Figure_3.pdf", "Figure_4.pdf",
                "Supplementary_Figure_S1.pdf"]


def stage(dest: Path, items: list[tuple[Path, str]]) -> tuple[list[Path], list[str]]:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    written, missing = [], []
    for src, name in items:
        if src.exists():
            shutil.copy2(src, dest / name)
            written.append(dest / name)
        else:
            missing.append(f"{name}: {src}")
    return written, missing


def main() -> int:
    figures = [(FIGS / f, f) for f in FIGURE_FILES]

    packages = {
        # Eurosurveillance reviews anonymised manuscripts and cannot evaluate
        # PDFs of the text, so the manuscript goes as .docx split across
        # separate files (built by scripts/build_eurosurveillance_docx.py).
        # The rendered PDF is deliberately NOT included: it carries the author
        # list and every identifying statement.
        "eurosurveillance": [
            (COVER_LETTER, "00_Cover_letter.pdf"),
            (DOCX / "Title_page.docx", "01_Title_page.docx"),
            (DOCX / "Manuscript_anon.docx", "02_Manuscript_anonymised.docx"),
            (DOCX / "Key_public_health_message.docx",
             "03_Key_public_health_message.docx"),
            *figures,
        ],
        "medrxiv": [
            (ROOT / "docs" / "team-canada-air-sampling-preprint.pdf",
             "01_Manuscript_preprint.pdf"),
            *figures,
        ],
    }

    # Without the cover letter the Eurosurveillance folder is incomplete. CI
    # cannot see the Google Drive source, so it must not stage (and then commit)
    # a partial package over a complete one built locally.
    if not COVER_LETTER.exists():
        print(f"cover letter not found at {COVER_LETTER}")
        print("  -> skipping the eurosurveillance package; staging medrxiv only.")
        packages.pop("eurosurveillance")
        cover_letter_absent = True
    else:
        cover_letter_absent = False

    all_missing: list[str] = []
    for name, items in packages.items():
        written, missing = stage(OUT / name, items)
        print(f"\n{name}/")
        for p in written:
            print(f"  {p.name:32s} {p.stat().st_size/1024:>8,.0f} KB")
        all_missing += [f"{name}/{m}" for m in missing]

    if all_missing:
        print("\nERROR - missing:", file=sys.stderr)
        for m in all_missing:
            print(f"  {m}", file=sys.stderr)
        return 1

    if cover_letter_absent:
        # Expected on CI, which has no access to Google Drive. Not an error:
        # the medrxiv package is complete and the local run fills in the rest.
        print(f"\nmedrxiv package staged under {OUT.relative_to(ROOT)}/")
        return 0

    print(f"\nBoth packages staged under {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
