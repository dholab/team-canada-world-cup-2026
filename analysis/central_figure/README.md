# Central Figure

The study's **Central figure** and the source graphics assembled into it in
Adobe Illustrator.

## `central_figure.ai` / `central_figure.png`

`central_figure.ai` is the editable Illustrator master (the layout that combines
the sampling workflow, the detection timeline, and the response-action icons).
`central_figure.png` is a trimmed raster export of it, embedded at the top of
the manuscript in both `index.qmd` (interactive site) and `PREVIEW.md`.

After editing the `.ai`, re-export the PNG. If Illustrator is available, export
directly (best quality). Otherwise a quick trimmed raster can be made with:

```bash
qlmanage -t -s 3000 -o /tmp "analysis/central_figure/central_figure.ai"
magick "/tmp/central_figure.ai.png" -background white -flatten -fuzz 2% \
  -trim +repage analysis/central_figure/central_figure.png
```

For final journal submission, export a high-resolution PNG or a vector PDF
straight from Illustrator rather than using the quick raster above.

## Source graphics

The remaining files are the individual elements composed into the `.ai`. They
are editable source assets, not manuscript figures on their own.

## `timeline.svg`

A single-line detection timeline: one horizontal line spanning the tournament
(3 June to 4 July 2026, true linear time) with a tick at every sampling window
in which any of the four respiratory viruses was detected. Date axis below,
city labels above their detection clusters.

Built for Illustrator editing:

- Explicit size (720 × 180 pt) so it imports at a real scale.
- Every tick is a discrete, fully-opaque stroked `<line>` — select, nudge, or
  delete any one; same-day detections stack into a visibly thicker mark.
- Elements are grouped into named layers (`baseline`, `date-axis`,
  `detection-ticks`, `city-labels`) that map to the Illustrator Layers panel.
- Labels are live `<text>` (not outlined), in a plain font family, so they stay
  editable on import.

Regenerate from the current data:

```bash
cd analysis
uv run python central_figure/make_timeline.py
```

It reads `../data/cartridges_long.csv`, so it always reflects the latest
corrected dataset.

## `icons/` — response-action silhouettes

Seven solid-silhouette SVG icons, one per low-regret action the manuscript names
as a response to a positive detection (Discussion), for arraying horizontally in
the Central Figure:

`ventilation`, `purifier`, `far_uvc`, `mask`, `access`, `exclude_ill`,
`vigilance`.

Each is a standalone 64 × 64 pt SVG with a single fill colour (edit `FILL` in
`make_action_icons.py`, or recolour in Illustrator). `action_icons_strip.svg`
lays all seven in a row. Regenerate:

```bash
cd analysis
uv run python central_figure/make_action_icons.py
```
