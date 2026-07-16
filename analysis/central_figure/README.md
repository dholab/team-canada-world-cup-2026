# Central Figure assets

Standalone graphics to be assembled into the study's **Central Figure** in Adobe
Illustrator. These are *not* manuscript figures — they are not embedded in the
interactive site or in `PREVIEW.md`, and are not part of the automated figure
build. They are editable source elements for hand-composition.

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
