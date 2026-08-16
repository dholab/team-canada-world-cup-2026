# Air sampling in team congregate spaces, 2026 FIFA World Cup

Data, analysis code, and manuscript source for a prospective environmental
surveillance study following the Canadian men's national soccer team across
five host cities during the 2026 FIFA World Cup™ (3 June to 4 July 2026).

Continuous bioaerosol sampling ran in up to four team-designated rooms per
hotel. Filters were changed roughly twice daily, eluted on-site, and tested
with the Cepheid Xpert® Xpress SARS-CoV-2/Flu/RSVplus assay. Of 176 air
filters, 15 carried detectable respiratory-virus genetic material.

## Read the manuscript

| | |
| --- | --- |
| **Interactive version** (recommended) | <https://dholab.github.io/team-canada-world-cup-2026/> — every figure explorable |
| **Journal submission PDF** | [`docs/team-canada-air-sampling.pdf`](docs/team-canada-air-sampling.pdf) — the BJSM build |
| **Preprint PDF** | [`docs/team-canada-air-sampling-preprint.pdf`](docs/team-canada-air-sampling-preprint.pdf) — the bioRxiv build, identical but for a pointer to the interactive version |

Both PDFs are rebuilt and committed by CI from the same source; they differ only
in that one-line preprint pointer.

## The data

| File | What it holds |
| --- | --- |
| [`analysis/data/cartridges_long.csv`](analysis/data/cartridges_long.csv) | The primary dataset. One row per cartridge × target virus (716 rows = 179 respiratory cartridges × 4 targets). |
| [`analysis/data/sequencing_detections.csv`](analysis/data/sequencing_detections.csv) | Distinct read counts per virus per sequenced Houston air sample. |
| [`analysis/data/ww_*.csv`](analysis/data/) | Per-city extracts of the public wastewater dashboards used for the contextual comparison. |

`cartridges_long.csv` columns: `city, room, sampler, cartridge, start, end,
dur_h, virus, ct, qual, detected, spc, spc_ct, status`. A blank `ct` means the
target did not amplify; `detected = 1` marks a reported Ct regardless of the
instrument's qualitative call; `spc`/`spc_ct` are the internal
sample-processing control's call and Ct; `status` flags each cartridge `valid`
or `invalid`. Figures show valid runs only — invalid runs are drawn grey or
marked with an asterisk rather than plotted as results.

See [`analysis/README.md`](analysis/README.md) for the full column reference and
how the dataset is regenerated from the raw instrument export.

## Which script builds which figure

| Manuscript figure | Script | Input |
| --- | --- | --- |
| Figures 1 and 2 | [`analysis/make_figures_1_2_detections.py`](analysis/make_figures_1_2_detections.py) | `data/cartridges_long.csv` |
| Figure 3 (sequencing) | [`analysis/make_figure_3_sequencing.py`](analysis/make_figure_3_sequencing.py) | `data/sequencing_detections.csv` |
| Online supplemental figure 1 | [`analysis/make_supplement_1_wastewater.py`](analysis/make_supplement_1_wastewater.py) | `data/ww_*.csv` |
| Central figure | [`analysis/central_figure/`](analysis/central_figure/) | assembled in Illustrator |

Every generated figure lands in `analysis/figures/`.

## How the manuscript is built

All manuscript text is written in a Google Doc, which is the single canonical
source. [`scripts/fetch_prose.py`](scripts/fetch_prose.py) pulls it and writes
`_title.yml`, `_frontmatter.md`, `_prose.md`, `_references.md`,
`_supplement.md`, and `_legends/`. Those files carry an AUTO-GENERATED banner —
**edit the Doc, never the files.** Quarto renders
[`index.qmd`](index.qmd) into both the interactive site and the submission PDF.

House style (cream/teal/terracotta, Georgia + Arial) lives in
[`theme-house.scss`](theme-house.scss) for HTML and
[`house-preamble.tex`](house-preamble.tex) for the PDF, which uses a white
background per journal requirement.

### Building

**In CI (preferred).** Run the **Render manuscript** workflow (Actions tab →
*Run workflow*), or push to `main`. It pulls the Doc, rebuilds every figure and
both outputs, and commits the synced content and PDF back. The PDF uses open,
metric-compatible font clones (Gelasio ≈ Georgia, Arimo ≈ Arial) so it builds
reproducibly.

**Locally.** Requires [Quarto](https://quarto.org),
[uv](https://docs.astral.sh/uv/), and
[tectonic](https://tectonic-typesetting.github.io/).

```bash
python scripts/fetch_prose.py                      # pull the canonical Doc
cd analysis && uv sync \
  && uv run python make_figures_1_2_detections.py \
  && uv run python make_figure_3_sequencing.py \
  && uv run python make_supplement_1_wastewater.py && cd ..
uv run --with pillow python analysis/central_figure/recolor_background.py
uv run --with fonttools python scripts/build_house_fonts.py  # Gelasio (→ fonts/)
quarto render                                      # → _site/ (HTML + journal PDF)
quarto render index.qmd --to pdf -M preprint:true  # → the preprint PDF
```

The two PDFs come from one source. `--to pdf` builds the journal submission;
adding `-M preprint:true` builds the bioRxiv version, which is identical except
for the Doc's "Preprint only" pointer under the title.
