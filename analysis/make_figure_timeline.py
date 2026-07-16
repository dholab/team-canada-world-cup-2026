#!/usr/bin/env python3
"""Build figure_timeline.svg — a minimal single-line detection timeline.

A stripped-down companion to Figure 1: one horizontal line spanning the whole
tournament (3 June to 4 July 2026, true linear time), with a tick at every
sampling window in which ANY of the four respiratory viruses was detected. All
four pathogens, all rooms, and all cities are collapsed onto the one line. No
axis, labels, or legend — the figure is meant to read at a glance as "when was
anything found," and to stand alone as an inline SVG.

Ticks are drawn semi-transparent so that same-day / overlapping detections
darken where they stack, giving a density cue without any text.

Run:  python make_figure_timeline.py   (from analysis/, or via `uv run`)
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE / "data" / "cartridges_long.csv"
OUT = HERE / "figure_timeline.svg"

# Canvas geometry (viewBox units; the SVG scales to any width).
W, H = 900, 90
PAD_X = 24
BASE_Y = H / 2
TICK_H = 26          # full tick height (centered on the baseline)
INK = "#6E8B91"      # same muted teal as the detection scale in Figure 1
LINE = "#C9C2B4"     # baseline colour


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def main() -> None:
    rows = list(csv.DictReader(CSV.open()))
    if not rows:
        raise SystemExit("cartridges_long.csv is empty")

    span_lo = min(parse(r["start"]) for r in rows)
    span_hi = max(parse(r["end"]) for r in rows)
    total = (span_hi - span_lo).total_seconds()

    # One tick per detection window, at the window midpoint.
    windows = {
        (r["start"], r["end"])
        for r in rows if r["detected"] == "1"
    }
    mids = sorted(
        (parse(s) + (parse(e) - parse(s)) / 2) for s, e in windows
    )

    def x_of(t: datetime) -> float:
        frac = (t - span_lo).total_seconds() / total
        return PAD_X + frac * (W - 2 * PAD_X)

    ticks = "".join(
        f'<line x1="{x_of(t):.1f}" y1="{BASE_Y - TICK_H/2:.1f}" '
        f'x2="{x_of(t):.1f}" y2="{BASE_Y + TICK_H/2:.1f}" '
        f'stroke="{INK}" stroke-width="3" stroke-linecap="round" '
        f'opacity="0.55"/>'
        for t in mids
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="100%" role="img" '
        f'aria-label="Timeline of respiratory-virus detections over the '
        f'tournament; ticks mark when any of four viruses was detected.">'
        f'<line x1="{PAD_X}" y1="{BASE_Y}" x2="{W - PAD_X}" y2="{BASE_Y}" '
        f'stroke="{LINE}" stroke-width="2"/>'
        f'{ticks}'
        f'</svg>\n'
    )
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT}  ({len(mids)} detection ticks over "
          f"{span_lo.date()} to {span_hi.date()})")


if __name__ == "__main__":
    main()
