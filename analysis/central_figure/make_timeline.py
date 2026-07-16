#!/usr/bin/env python3
"""Build timeline.svg — a single-line detection timeline as an editable
Illustrator asset for the Central Figure.

The line spans the tournament (3 June to 4 July 2026, true linear time) and
shows three states so sampling coverage is distinguishable from detections:

  1. Not sampling  -> bare baseline (the inter-city travel gaps show as breaks).
  2. Sampling, negative -> a low coverage band drawn to each cartridge's exact
     start->end window.
  3. Sampling, positive -> a tick above the band at each window in which any of
     the four respiratory viruses was detected.

So a quiet stretch under the band reads as "sampled, nothing found," while a
break in the band reads as "not sampling" — the two are no longer confused.

This is NOT a manuscript figure — it is a standalone asset to be imported into
Adobe Illustrator as one element of the study's Central Figure. It is therefore
not embedded in the interactive site or the preview.

Illustrator-friendliness:
  - Explicit width/height in points (imports at a real size, not 100%).
  - Coverage windows are individual <rect>s; detections are individual <line>s;
    both fully opaque and editable. Same-day detections stack into a thicker
    mark.
  - Elements grouped into named <g> layers (baseline, coverage, detection-ticks,
    date-axis, city-labels) that map to the Illustrator Layers panel.
  - Real <text> (not outlined) so labels stay editable.

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

# Canvas geometry, in points.
W, H = 720, 180
PAD_X = 40
BASE_Y = 78
TICK_H = 30                 # detection tick height, centred on the baseline
BAND_H = 8                  # sampling-coverage band thickness
INK = "#6E8B91"             # detection colour (matches Figure 1's scale)
BAND = "#D9D3C6"            # sampling-coverage colour (recessive)
LINE = "#B9B2A4"            # baseline / axis colour
TEXT = "#3A3A38"            # label colour
TICK_W = 2.4


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def week_ticks(lo: datetime, hi: datetime) -> list[datetime]:
    ticks, t = [], lo.replace(hour=0, minute=0, second=0, microsecond=0)
    while t <= hi:
        if t >= lo:
            ticks.append(t)
        t += timedelta(days=7)
    return ticks


def main() -> None:
    rows = list(csv.DictReader(CSV.open()))

    span_lo = min(parse(r["start"]) for r in rows)
    span_hi = max(parse(r["end"]) for r in rows)
    total = (span_hi - span_lo).total_seconds()

    def x_of(t: datetime) -> float:
        return PAD_X + (t - span_lo).total_seconds() / total * (W - 2 * PAD_X)

    # Unique sampling windows (one per cartridge collection), flagged detected.
    windows = OrderedDict()
    for r in rows:
        k = (r["start"], r["end"])
        w = windows.setdefault(k, {"city": r["city"], "det": False})
        if r["detected"] == "1":
            w["det"] = True

    coverage, ticks = [], []
    city_ticks: "OrderedDict[str, list[datetime]]" = OrderedDict()
    for (s, e), w in windows.items():
        a, b = parse(s), parse(e)
        coverage.append((a, b))
        if w["det"]:
            mid = a + (b - a) / 2
            ticks.append(mid)
            city_ticks.setdefault(w["city"], []).append(mid)
    ticks.sort()

    # --- layers ---
    baseline = (
        f'<g id="baseline"><line x1="{PAD_X}" y1="{BASE_Y}" '
        f'x2="{W - PAD_X}" y2="{BASE_Y}" stroke="{LINE}" stroke-width="1"/></g>'
    )

    cov_parts = []
    for a, b in coverage:
        x1, x2 = x_of(a), x_of(b)
        cov_parts.append(
            f'<rect x="{x1:.1f}" y="{BASE_Y - BAND_H/2:.1f}" '
            f'width="{max(x2 - x1, 0.6):.1f}" height="{BAND_H}" '
            f'fill="{BAND}"/>'
        )
    coverage_layer = f'<g id="coverage">{"".join(cov_parts)}</g>'

    tick_parts = [
        f'<line x1="{x_of(t):.1f}" y1="{BASE_Y - TICK_H/2:.1f}" '
        f'x2="{x_of(t):.1f}" y2="{BASE_Y + TICK_H/2:.1f}" '
        f'stroke="{INK}" stroke-width="{TICK_W}" stroke-linecap="round"/>'
        for t in ticks
    ]
    tick_layer = f'<g id="detection-ticks">{"".join(tick_parts)}</g>'

    axis_parts = []
    for t in week_ticks(span_lo, span_hi):
        x = x_of(t)
        axis_parts.append(
            f'<line x1="{x:.1f}" y1="{BASE_Y + TICK_H/2 + 6:.1f}" '
            f'x2="{x:.1f}" y2="{BASE_Y + TICK_H/2 + 12:.1f}" '
            f'stroke="{LINE}" stroke-width="1"/>'
            f'<text x="{x:.1f}" y="{BASE_Y + TICK_H/2 + 26:.1f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="10" '
            f'fill="{TEXT}" text-anchor="middle">{t:%b %-d}</text>'
        )
    date_axis = f'<g id="date-axis">{"".join(axis_parts)}</g>'

    city_parts = []
    for city, mids in city_ticks.items():
        cx = sum(x_of(m) for m in mids) / len(mids)
        lo, hi = min(mids), max(mids)
        rng = f"{lo:%b %-d}" if lo.date() == hi.date() else f"{lo:%b %-d}–{hi:%b %-d}"
        city_parts.append(
            f'<text x="{cx:.1f}" y="{BASE_Y - TICK_H/2 - 15:.1f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="11" '
            f'font-weight="600" fill="{TEXT}" text-anchor="middle">{city}</text>'
            f'<text x="{cx:.1f}" y="{BASE_Y - TICK_H/2 - 4:.1f}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="9" '
            f'fill="{LINE}" text-anchor="middle">{rng}</text>'
        )
    city_layer = f'<g id="city-labels">{"".join(city_parts)}</g>'

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}pt" height="{H}pt" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Detection timeline. A coverage band shows when sampling '
        f'occurred; ticks mark windows in which any of four viruses was '
        f'detected; breaks in the band are travel gaps with no sampling.">'
        f'{baseline}{coverage_layer}{tick_layer}{date_axis}{city_layer}'
        f'</svg>\n'
    )
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT}  ({len(coverage)} sampling windows, {len(ticks)} "
          f"detections, {len(city_ticks)} cities)")


if __name__ == "__main__":
    main()
