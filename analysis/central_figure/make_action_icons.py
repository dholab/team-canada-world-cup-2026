#!/usr/bin/env python3
"""Build the response-action icon set for the Central Figure.

One solid silhouette icon per low-regret action the manuscript names as a
response to a positive air-sample detection (Discussion, "low-cost, low-regret
actions"):

  1. ventilation   - reinforce ventilation (airflow through a vent)
  2. purifier       - add a portable air purifier (floor unit, clean-air plume)
  3. far_uvc        - far-UVC lighting (ceiling luminaire casting rays)
  4. mask           - masking in the implicated space (respirator)
  5. access         - review who has access to team areas (badged door)
  6. exclude_ill    - exclude visibly ill personnel (person + exclusion ring)
  7. vigilance      - heighten clinical vigilance (eye + pulse)

Each icon is a standalone editable SVG on a shared 64x64 artboard, so they drop
into Adobe Illustrator and array horizontally at a uniform size. Silhouettes
are a single fill colour (currentColor via a fill attribute) so recolouring is
one edit. A combined `action_icons_strip.svg` lays all seven in a row for quick
placement.

These are NOT manuscript figures; they are Central Figure source assets and are
not part of the site or preview build.

Run:  uv run python central_figure/make_action_icons.py   (from analysis/)
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "icons"
FILL = "#2C2C2A"          # silhouette colour; change once here (or in Illustrator)
BOX = 64                   # artboard size in points

# Each entry: (slug, human label, inner SVG markup drawn on a 0..64 canvas).
# Markup uses solid <path>/<rect>/<circle>/<polygon> — no strokes, no text.
ICONS: list[tuple[str, str, str]] = [
    (
        "ventilation", "Reinforce ventilation",
        # A square wall vent (louvred grille) with two bold airflow arrows
        # sweeping out to the right.
        '<rect x="8" y="16" width="22" height="32" rx="3"/>'
        '<rect x="12" y="21" width="14" height="3.2" fill="#FFFFFF"/>'
        '<rect x="12" y="27" width="14" height="3.2" fill="#FFFFFF"/>'
        '<rect x="12" y="33" width="14" height="3.2" fill="#FFFFFF"/>'
        '<rect x="12" y="39" width="14" height="3.2" fill="#FFFFFF"/>'
        '<path d="M34 26 q12 -1 15 -8" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.6" stroke-linecap="round"/>'
        '<path d="M49 18 l1 6 l-6 0" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M34 40 q12 1 15 8" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.6" stroke-linecap="round"/>'
        '<path d="M49 48 l1 -6 l-6 0" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>',
    ),
    (
        "purifier", "Portable air purifier",
        # A tall rounded floor unit with a slotted intake and a bold clean-air
        # plume rising from the top vent.
        '<rect x="20" y="26" width="24" height="32" rx="6"/>'
        '<rect x="25" y="33" width="14" height="3" rx="1.5" fill="#FFFFFF"/>'
        '<rect x="25" y="39" width="14" height="3" rx="1.5" fill="#FFFFFF"/>'
        '<rect x="25" y="45" width="14" height="3" rx="1.5" fill="#FFFFFF"/>'
        '<rect x="27" y="24" width="10" height="3" rx="1.5"/>'
        '<path d="M32 22 C26 18 26 12 32 8" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.4" stroke-linecap="round"/>'
        '<path d="M32 8 l4 1 l-1 4" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>',
    ),
    (
        "far_uvc", "Far-UVC lighting",
        # A ceiling-mounted luminaire with a fan of downward rays.
        '<rect x="18" y="10" width="28" height="9" rx="2.5"/>'
        '<rect x="29" y="6" width="6" height="5" rx="1.5"/>'
        '<path d="M24 22 L20 40" stroke="#2C2C2A" stroke-width="3.2" '
        'stroke-linecap="round"/>'
        '<path d="M30 22 L28 44" stroke="#2C2C2A" stroke-width="3.2" '
        'stroke-linecap="round"/>'
        '<path d="M34 22 L36 44" stroke="#2C2C2A" stroke-width="3.2" '
        'stroke-linecap="round"/>'
        '<path d="M40 22 L44 40" stroke="#2C2C2A" stroke-width="3.2" '
        'stroke-linecap="round"/>'
        '<circle cx="24" cy="50" r="2.2"/><circle cx="32" cy="53" r="2.2"/>'
        '<circle cx="40" cy="50" r="2.2"/>',
    ),
    (
        "mask", "Masking",
        # A respirator/face mask: pleated cup with two ear loops.
        '<path d="M18 26 '
        'C14 24 12 25 12 30 C12 36 14 38 18 38 Z"/>'
        '<path d="M46 26 C50 24 52 25 52 30 C52 36 50 38 46 38 Z"/>'
        '<path d="M18 22 '
        'C26 20 38 20 46 22 '
        'C48 22 49 24 49 27 '
        'L49 37 C49 43 42 48 32 48 '
        'C22 48 15 43 15 37 L15 27 C15 24 16 22 18 22 Z"/>'
        '<rect x="16" y="28" width="32" height="2.6" rx="1.3" fill="#FFFFFF"/>'
        '<rect x="16" y="34" width="32" height="2.6" rx="1.3" fill="#FFFFFF"/>',
    ),
    (
        "access", "Review access to team areas",
        # A door within a frame, with an access badge / card.
        '<rect x="16" y="8" width="24" height="48" rx="2.5"/>'
        '<rect x="20" y="12" width="16" height="40" rx="1.5" fill="#FFFFFF"/>'
        '<circle cx="33" cy="32" r="2.4"/>'
        '<rect x="42" y="30" width="14" height="18" rx="2.5"/>'
        '<rect x="45" y="34" width="8" height="2.6" rx="1.3" fill="#FFFFFF"/>'
        '<rect x="45" y="39" width="8" height="2.6" rx="1.3" fill="#FFFFFF"/>',
    ),
    (
        "exclude_ill", "Exclude visibly ill personnel",
        # A person silhouette crossed by an exclusion ring (no-entry).
        '<circle cx="26" cy="18" r="7"/>'
        '<path d="M14 50 C14 38 20 32 26 32 C32 32 38 38 38 50 Z"/>'
        '<circle cx="44" cy="42" r="13" fill="none" stroke="#2C2C2A" '
        'stroke-width="4"/>'
        '<rect x="34.5" y="40" width="19" height="4" rx="2" '
        'transform="rotate(45 44 42)"/>',
    ),
    (
        "vigilance", "Heighten clinical vigilance",
        # A stethoscope: earpiece tubing down to a chestpiece, with a small
        # pulse mark inside it — clinical watchfulness.
        '<circle cx="16" cy="12" r="3.4"/>'
        '<circle cx="30" cy="12" r="3.4"/>'
        '<path d="M16 15 C16 30 23 34 23 40" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.2" stroke-linecap="round"/>'
        '<path d="M30 15 C30 30 40 32 40 40" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.2" stroke-linecap="round"/>'
        '<path d="M23 40 a8 8 0 0 0 16 0" fill="none" stroke="#2C2C2A" '
        'stroke-width="3.2" stroke-linecap="round"/>'
        '<circle cx="44" cy="44" r="9"/>'
        '<path d="M40 44 h3 l1.5 -3 l2 6 l1.5 -3 h3" fill="none" '
        'stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"/>',
    ),
]


def wrap(inner: str, label: str) -> str:
    # A group with the shared fill; per-shape white "cutouts" and explicit
    # strokes override it. currentColor-friendly: set fill on the root <g>.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BOX}" height="{BOX}" '
        f'viewBox="0 0 {BOX} {BOX}" role="img" aria-label="{label}">'
        f'<g fill="{FILL}">{inner}</g></svg>\n'
    )


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for slug, label, inner in ICONS:
        (OUT_DIR / f"{slug}.svg").write_text(wrap(inner, label), encoding="utf-8")

    # Combined horizontal strip: seven 64-wide cells with a small gutter.
    gutter = 20
    cell = BOX + gutter
    strip_w = cell * len(ICONS) - gutter
    cells = []
    for i, (slug, label, inner) in enumerate(ICONS):
        cells.append(
            f'<g transform="translate({i * cell},0)" fill="{FILL}">'
            f'<g role="img" aria-label="{label}">{inner}</g></g>'
        )
    strip = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{strip_w}" '
        f'height="{BOX}" viewBox="0 0 {strip_w} {BOX}" role="img" '
        f'aria-label="Response actions to a positive air-sample detection.">'
        f'{"".join(cells)}</svg>\n'
    )
    (OUT_DIR / "action_icons_strip.svg").write_text(strip, encoding="utf-8")

    print(f"wrote {len(ICONS)} icons + strip to {OUT_DIR}")


if __name__ == "__main__":
    main()
