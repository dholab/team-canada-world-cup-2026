# Analysis — data and figure pipelines

Every figure in the manuscript is built by a Python script from a committed
tidy CSV in `data/`, so each figure reflects exactly the deposited data. All
generated outputs are written to `figures/`.

| Manuscript figure | Script | Input CSV | Outputs in `figures/` |
| --- | --- | --- | --- |
| Figures 1 and 2 | `make_figures_1_2_detections.py` | `data/cartridges_long.csv` | `figure1_detections_interactive.html`, `figure1_detections_static.{png,pdf}`, `figure2_houston_interactive.html`, `figure2_houston.{png,pdf}` |
| Figure 3 | `make_figure_3_sequencing.py` | `data/sequencing_detections.csv` | `figure3_sequencing.html`, `figure3_sequencing.png`, `figure3_sequencing_transparent.png` |
| Online supplemental figure 1 | `make_supplement_1_wastewater.py` | `data/ww_canada.csv`, `data/ww_losangeles.csv`, `data/ww_houston.csv` | `supplement1_wastewater_interactive.html`, `supplement1_wastewater.{png,pdf}` |
| Central figure | `central_figure/` | assembled in Illustrator | `central_figure/central_figure.png` |

Each figure ships an interactive Plotly HTML (embedded in the Quarto site) and
a static PNG (used by the submission PDF). Figure 3 also ships a
transparent-background PNG for slides. Interactive HTML and intermediate PDFs
are git-ignored and rebuilt by CI; the static PNGs and every CSV are committed.

## Build

Requires [uv](https://docs.astral.sh/uv/). The virtual environment lives in
`.venv/` and is git-ignored — do not commit or cloud-sync it.

```bash
uv sync
uv run python make_figures_1_2_detections.py
uv run python make_figure_3_sequencing.py
uv run python make_supplement_1_wastewater.py
```

## Data

`data/cartridges_long.csv` — one row per cartridge x target virus (716 rows =
179 respiratory cartridges x 4 viruses), exported from the GeneXpert results.

Columns: `city, room, sampler, cartridge, start, end, dur_h, virus, ct, qual, detected, spc, spc_ct, status`

- `ct` is blank when the target did not amplify (0 < Ct < 99 counts as a detection).
- `detected` = 1 for a reported Ct regardless of the instrument's qualitative call.
- `spc` is the internal Sample Processing Control call (Positive / Negative).
- `spc_ct` is the SPC control's Ct, present only when the control amplified.
- `status` is the cartridge's validity, `valid` or `invalid`. Invalid covers a
  non-amplifying SPC, a probe error (SPC Ct < 5), and author-designated invalid
  runs (see `FORCE_INVALID` in `extract_data.py`).
- The figures show valid runs only; invalid runs are drawn grey / marked with an
  asterisk but are kept in this table. Of the 179 cartridges, 5 are invalid;
  none of the 13 detections came from those.

Some cartridges that produced no valid test data are excluded from the dataset
entirely (see `REMOVE` in `extract_data.py`).

One sampler is excluded study-wide (see `EXCLUDE_SAMPLERS` in
`extract_data.py`). "Sabalenka" ran predominantly for norovirus, which this
manuscript does not report because norovirus was never detected; on a few
occasions its cartridge was additionally run on the respiratory panel to confirm
a primary detection in the same room. Those confirmatory runs are not part of
the consistently-sampled respiratory series the figures describe.

## Auditing the dataset against LabKey

`data/cartridges_long.csv` is derived from the dashboard export in `raw/`, which
is a rendering and can be wrong: one cartridge's window was recorded there with
the removal time as its start (see `FIX_WINDOW` in `extract_data.py`). To
re-check every value against the authoritative LabKey tables, export the
cartridge-metadata and qualitative-results tables as TSV and run:

```bash
python scripts/audit_against_labkey.py \
  --metadata cartridge_metadata_with_facilities.tsv \
  --results  results_summary_qualitative.tsv
```

It compares sampling windows against the deploy and removal timestamps
(converting LabKey's UTC to each host city's local time), every Ct value and
detection call, the SPC call and validity, and the sampler, room, and duration.
Cartridges from other studies in the same export are ignored. It exits non-zero
on any discrepancy.

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
