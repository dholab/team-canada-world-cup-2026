# Air-sampling detections — Figure 1 (interactive + static)

Reproducible figures for the Team Canada air-sampling study (2026 FIFA World Cup).
Both figures are built from a single tidy dataset by one script.

| Output | Purpose |
| --- | --- |
| `figure1_interactive.html` | **Interactive.** Every room in every city is explorable. A host-city selector switches between the five cities; each square is one cartridge x virus, and hovering shows the room, date, session start, virus, Ct value, and the GeneXpert qualitative call. Self-contained (Plotly loaded from CDN). Embed this in the repo / project page. |
| `figure1_static.pdf`, `figure1_static.png` | **Static.** Rooms are merged within each city for print readability (one cell per city-date-virus, filled by the lowest Ct among that day's rooms). Use in the manuscript PDF. |

## Data

`data/cartridges_long.csv` — the complete record of collected respiratory-scope
samples (739 rows), exported from the GeneXpert results. The 182 cartridges that
were tested for the four respiratory targets contribute 4 rows each (728 rows);
11 cartridges that produced no valid test data contribute one row each.

Columns: `city, room, sampler, cartridge, start, end, dur_h, virus, ct, qual, detected, spc, spc_ct, status`

- `ct` is blank when the target did not amplify (0 < Ct < 99 counts as a detection).
- `detected` = 1 for a reported Ct regardless of the instrument's qualitative call.
- `spc` is the internal Sample Processing Control call (Positive / Negative).
- `spc_ct` is the SPC control's Ct, present only when the control amplified.
- `status` is the cartridge's validity: `valid` (SPC positive), `spc_negative`
  (control did not amplify), `probe_error` (SPC Ct < 5, assay error), or
  `no_valid_data` (cartridge returned no target result; these rows have a blank
  `virus`).
- The figures show valid runs only. Invalid samples (`spc_negative`,
  `probe_error`, `no_valid_data`) are kept in this table but not plotted. Of the
  182 respiratory cartridges, 5 are invalid (2 `spc_negative`, 3 `probe_error`);
  none of the 15 detections came from those.

## Build

Requires [uv](https://docs.astral.sh/uv/). The virtual environment lives in
`.venv/` and is git-ignored — do not commit or cloud-sync it.

```bash
uv sync                      # create the environment from pyproject.toml
uv run python make_figures.py
```

This writes `figure1_interactive.html`, `figure1_static.pdf`, and
`figure1_static.png` into the project root.

## Regenerating the dataset

`data/cartridges_long.csv` is derived from the raw LabKey export in
`raw/API_PER_ROOM.html` (the "Pathogen heat map by room" dashboard). To rebuild
it after a corrected export is dropped into `raw/`:

```bash
uv run python extract_data.py
```

The extractor joins each cartridge's authoritative sampling window (from the
dashboard's `points` data) with its Ct and qualitative call (from the embedded
per-target CSV), keeps the four respiratory targets, and applies the study's
detection rule (0 < Ct < 99 counts as a detection). See `extract_data.py` for
details. Rebuilding the dataset is only needed when the source export changes;
the figures build directly from the committed CSV.
