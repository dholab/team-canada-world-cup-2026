#!/usr/bin/env python3
"""Make the cream-background Central Figure used by the Quarto site.

The Central Figure is exported from Illustrator on a white ground (the editable
.ai master lives in the manuscript's Google Drive folder, not this repo). The
submission PDF wants that white ground, but on the Quarto site every other
figure paints the house cream, so a white Central Figure reads as a white
rectangle pasted onto the cream page.

So this keeps BOTH:

  central_figure.png       white  — the Illustrator export, used by the PDF
  central_figure_cream.png cream  — generated here, used by the HTML site

It rewrites only the *background*: it flood-fills inward from the image border
and recolors the connected near-white region, so white elements *inside* the
artwork (the sampler photos, the elution tube, the white icon tiles) keep their
white. A global white->cream replace would wreck those, which is why this walks
the connected region instead.

    uv run python central_figure/recolor_background.py
"""
from __future__ import annotations

import pathlib
import sys
from collections import deque

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
# Source: the Illustrator export on white. Used as-is by the submission PDF.
PNG = HERE / "central_figure.png"
# Generated: the same artwork on cream, used by the Quarto HTML site.
OUT = HERE / "central_figure_cream.png"

CREAM = (248, 244, 233)
# How far from pure white a pixel may be and still count as page background.
# Kept tight so anti-aliased artwork edges are not eaten.
WHITE_MIN = 244


def is_background(px: tuple[int, int, int, int]) -> bool:
    r, g, b = px[0], px[1], px[2]
    return r >= WHITE_MIN and g >= WHITE_MIN and b >= WHITE_MIN


def main() -> None:
    if not PNG.exists():
        raise SystemExit(f"missing {PNG}")

    im = Image.open(PNG).convert("RGBA")
    w, h = im.size
    px = im.load()

    if not is_background(px[0, 0]):
        raise SystemExit(
            f"{PNG.name} has a {px[0, 0][:3]} border, not white. This script "
            "expects the white Illustrator export as its source; re-export it "
            "from the .ai master before running."
        )

    # Flood fill inward from every border pixel. Only background-connected
    # near-white is recolored; enclosed white stays white.
    seen = bytearray(w * h)
    q: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        i = y * w + x
        if not seen[i]:
            seen[i] = 1
            if is_background(px[x, y]):
                q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    filled = 0
    while q:
        x, y = q.popleft()
        a = px[x, y][3]
        px[x, y] = (CREAM[0], CREAM[1], CREAM[2], a)
        filled += 1
        if x > 0:
            push(x - 1, y)
        if x < w - 1:
            push(x + 1, y)
        if y > 0:
            push(x, y - 1)
        if y < h - 1:
            push(x, y + 1)

    im.save(OUT)
    pct = 100.0 * filled / (w * h)
    print(f"wrote {OUT}  ({filled:,} px recolored to cream, {pct:.1f}% of image)")


if __name__ == "__main__":
    sys.exit(main())
