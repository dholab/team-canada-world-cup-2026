#!/usr/bin/env python3
"""Build figure_timeline.svg — a single-line detection timeline as an editable
Illustrator asset for the Central Figure.

One horizontal line spans the tournament (3 June to 4 July 2026, true linear
time). A tick marks every sampling window in which ANY of the four respiratory
viruses was detected (all pathogens, rooms, and cities collapsed onto one line).
Unlike a glance-only sparkline, this version is labelled: date ticks along the
axis and city labels grouped under their detection clusters, so it can stand on
its own inside a larger figure.

Illustrator-friendliness:
  - Explicit width/height in points (imports at a real size, not 100%).
  - Every tick is a discrete, fully-opaque <line> (stroked) — select/nudge/
    delete any one. Same-day detections stack into a visibly thicker mark.
  - Elements grouped into labelled <g> layers (baseline, ticks, date axis,
    city labels) so the Illustrator Layers panel is tidy.
  - Real <text> (not outlined) so labels stay editable; font is a plain family.

This is NOT a manuscript figure — it is a standalone asset to be imported into
Adobe Illustrator as one element of the study's Central Figure. It is therefore
not embedded in the interactive site or the preview.

Run:  uv run python central_figure/make_timeline.py   (from analysis/)
"""
from __future__ import annotations

import csv
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "data" / "cartridges_long.csv"
OUT = HERE / "timeline.svg"

# Canvas geometry, in points (1pt units in the viewBox).
W, H = 720, 180
PAD_X = 40
BASE_Y = 70
TICK_H = 30                 # tick height, centred on the baseline
INK = "#6E8B91"             # tick colour (matches Figure 1's detection scale)
LINE = "#B9B2A4"            # baseline / axis colour
TEXT = "#3A3A38"            # label colour
TICK_W = 2.4

# Date gridline positions along the axis (weekly), labelled.
def week_ticks(lo: datetime, hi: datetime) -> list[datetime]:
    ticks, t = [], lo.replace(hour=0, minute=0, second=0, microsecond=0)
    while t <= hi:
        if t >= lo:
            ticks.append(t)
        t += timedelta(days=7)
    return ticks


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def main() -> None:
    rows = list(csv.DictReader(CSV.open()))
    dets = [r for r in rows if r["detected"] == "1"]

    span_lo = min(parse(r["start"]) for r in rows)
    span_hi = max(parse(r["end"]) for r in rows)
    total = (span_hi - span_lo).total_seconds()

    def x_of(t: datetime) -> float:
        return PAD_X + (t - span_lo).total_seconds() / total * (W - 2 * PAD_X)

    # One tick per detection window (midpoint of its sampling window).
    windows = OrderedDict()
    for r in dets:
        k = (r["start"], r["end"])
        w = windows.setdefault(k, {"city": r["city"]})
    ticks = []
    for (s, e), w in windows.items():
        mid = parse(s) + (parse(e) - parse(s)) / 2
        ticks.append((mid, w["city"]))
    ticks.sort()

    # City label groups: place each city's label at the mean x of its ticks,
    # with the city's detection date range. Cities in tournament order.
    city_ticks: "OrderedDict[str, list[datetime]]" = OrderedDict()
    for mid, city in ticks:
        city_ticks.setdefault(city, []).append(mid)

    # --- assemble SVG layers ---
    baseline = (
        f'<g id="baseline">'
        f'<line x1="{PAD_X}" y1="{BASE_Y}" x2="{W - PAD_X}" y2="{BASE_Y}" '
        f'stroke="{LINE}" stroke-width="1.5"/>'
        f'</g>'
    )

    date_axis_parts = []
    for t in week_ticks(span_lo, span_hi):
        x = x_of(t)
        date_axis_parts.append(
            f'<line x1="{x:.1f}" y1="{BASE_Y + TICK_H/2 + 4:.1f}" '
            f'x2="{x:.1f}" y2="{BASE_Y + TICK_H/2 + 10:.1f}" '
            f'stroke="{LINE}" stroke-width="1"/>'
            f'<text x="{x:.1f}" y="{BASE_Y + TICK_H/2 + 24:.1f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="10" '
            f'fill="{TEXT}" text-anchor="middle">{t:%b %-d}</text>'
        )
    date_axis = f'<g id="date-axis">{"".join(date_axis_parts)}</g>'

    tick_parts = [
        f'<line x1="{x_of(t):.1f}" y1="{BASE_Y - TICK_H/2:.1f}" '
        f'x2="{x_of(t):.1f}" y2="{BASE_Y + TICK_H/2:.1f}" '
        f'stroke="{INK}" stroke-width="{TICK_W}" stroke-linecap="round"/>'
        for t, _ in ticks
    ]
    tick_layer = f'<g id="detection-ticks">{"".join(tick_parts)}</g>'

    city_parts = []
    for city, mids in city_ticks.items():
        cx = sum(x_of(m) for m in mids) / len(mids)
        lo, hi = min(mids), max(mids)
        rng = f"{lo:%b %-d}" if lo.date() == hi.date() else f"{lo:%b %-d}–{hi:%b %-d}"
        city_parts.append(
            f'<text x="{cx:.1f}" y="{BASE_Y - TICK_H/2 - 14:.1f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="11" '
            f'font-weight="600" fill="{TEXT}" text-anchor="middle">{city}</text>'
            f'<text x="{cx:.1f}" y="{BASE_Y - TICK_H/2 - 3:.1f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="9" '
            f'fill="{LINE}" text-anchor="middle">{rng}</text>'
        )
    city_layer = f'<g id="city-labels">{"".join(city_parts)}</g>'

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}pt" height="{H}pt" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Detection timeline across the tournament, with date axis '
        f'and city labels.">'
        f'{baseline}{date_axis}{tick_layer}{city_layer}'
        f'</svg>\n'
    )
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT}  ({len(ticks)} detection ticks, "
          f"{len(city_ticks)} cities, {span_lo.date()} to {span_hi.date()})")


if __name__ == "__main__":
    main()
