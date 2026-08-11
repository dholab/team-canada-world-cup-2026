---
name: manuscript-figure
description: Use when building or revising a figure for the Team Canada air-sampling manuscript (this repo) so it matches the house format. Covers the palette, fonts, the interactive-Plotly + static-matplotlib + transparent-PNG output trio, the committed-CSV data pattern, legend conventions, and how figures embed in index.qmd. Trigger on any request to make, restyle, or add a figure here.
---

# Manuscript figures (Team Canada air-sampling study)

Every figure in this manuscript is built by a Python script from a committed
tidy CSV, and ships three outputs: a self-contained interactive HTML (embedded
in the Quarto site), a static PNG on cream (the manuscript PDF), and a
transparent-background PNG (slides). Figure 3 (`analysis/make_figure3_sequencing.py`)
is the reference implementation for a heatmap; Figures 1 and 2
(`analysis/make_figures.py`) are the reference for time-interval charts.

## Non-negotiables

1. **Data comes from a committed CSV** in `analysis/data/`, one tidy row per
   observation. The figure script reads only that CSV, so the figure always
   reflects deposited data. Never hardcode values in the plotting script.
2. **Three outputs per figure**, written into `analysis/`:
   `figureN_<name>.html` (interactive), `figureN_<name>.png` (static, cream),
   `figureN_<name>_transparent.png` (static, alpha). Build with `uv run python`.
3. **House palette** (below), Georgia titles, Arial labels. No other colors for
   chrome.
4. **Verify the render before claiming done.** Read the PNG back and look at it.
   Copy the HTML into the repo root as `.preview.html`, open it in the browser,
   screenshot it, then delete the preview. Never assert alignment or correctness
   from the code alone.
5. **Column/row header alignment**: build headers as fixed-coordinate text in
   matplotlib (each label at an explicit y), never rely on flex/vertical-align
   bottom in HTML tables — single-line labels drift out of register otherwise.
   This was a repeatedly-hit bug; the matplotlib static figure is the alignment
   source of truth.

## Palette (shared with docs/template.html)

```
TEAL   = "#163139"   # titles, body, labels (the "Deep Teal")
TERRA  = "#C16A3C"   # accents, sampler names, eyebrows (the "Terracotta")
CREAM  = "#F8F4E9"   # page + figure background (never pure white)
RULE   = "#dcd3c2"   # hairlines, hover-label borders
```

Data-series color is separate from chrome. Detection/abundance heatmaps use a
light-to-deep **blue** ramp (deep = more), matching the GeneXpert Ct figures:
`["#E6F1FB","#B5D4F4","#85B7EB","#378ADD","#185FA5","#0C447C"]`. Cells that were
tested-but-negative read `0`; cells not assessed are left the tan empty color
`#efe8da`. Never red-amber-green.

## Fonts

- Titles and any large display numbers: **Georgia** (serif), bold, sentence case,
  left-aligned, in TEAL. Title text is prefixed with the bold figure number,
  e.g. `<b>Figure 3</b>  Human viruses detected ...`.
- Everything else (labels, captions, hover): **Arial**, in TEAL, with TERRA for
  accent sub-labels (sampler names, eyebrows). Captions/labels are often ALL CAPS
  and lightly letter-spaced.

## Interactive (Plotly) conventions

- `fig.write_html(out, include_plotlyjs="cdn", full_html=True, config={"displayModeBar": False})`
  — self-contained, loads Plotly from CDN, no toolbar.
- `paper_bgcolor` and `plot_bgcolor` = CREAM. `template` is irrelevant once these
  are set; do not rely on `simple_white` for background.
- Rich `hovertemplate` with `<extra></extra>` to suppress the trace box, and a
  white `hoverlabel` bordered in RULE. Hover is the primary interaction (no
  click-to-FASTA in this manuscript).
- Heatmap row order: pin the headline viruses on top, then order by total signal.
  Use natural data order plus `yaxis autorange="reversed"` so the first row is at
  the top. Do NOT also pre-reverse the arrays — that double-flips (a hit bug).

## Static (matplotlib) conventions

- `matplotlib.use("Agg")` at import. `dpi=300`, `bbox_inches="tight"`.
- One `build_static(..., transparent: bool)` function produces both the cream and
  the transparent PNG. For transparent: `savefig(..., transparent=True,
  facecolor=None)` and set every patch edge to CREAM so the grid gaps read on any
  slide background. For cream: `facecolor=CREAM`.
- Confirm the transparent PNG truly has alpha (corner pixel alpha == 0) with PIL
  before delivering it for Keynote.

## Legends

- The full legend paragraph goes in `analysis/figure_legends.md`, and a condensed
  version is repeated as the caption under the figure in `index.qmd`.
- **Author punctuation rule (binding): no em dashes, no colons, no semicolons.**
  Rewrite around them. Times are local wall-clock for each host city.
- Legend prose is one paragraph, opens with the bold `**Figure N. Title.**`,
  then describes columns, rows, the color encoding, what empty vs zero cells
  mean, and the interactive hover contents.

## Embedding in index.qmd

Each figure is a Quarto div with an HTML iframe for the site and a PDF-only
static image:

```
::: {#fig-<slug>}

​```{=html}
<iframe src="analysis/figureN_<name>.html" width="100%" height="600"
        style="border:none;" loading="lazy"
        title="Figure N: ..."></iframe>
​```

::: {.content-visible when-format="pdf"}
![](analysis/figureN_<name>.png)
:::

**Figure N. Title.** <condensed caption> ...

:::
```

Cross-reference figures in prose with `@fig-<slug>`. Add the script + data links
to the "Data and code" list.

## Build & commit

```bash
cd analysis && uv run python make_figureN_<name>.py
```

Commit the script, the CSV, and all three output files together with the
`index.qmd` and `figure_legends.md` edits. The repo is **private** during
co-author review; pushing to `main` triggers the render workflow that deploys the
review site, so only push when the figure has been visually verified.

## Numbering caution

`make_figure3.py` already exists and builds the **wastewater** supplement
("Online supplemental figure 1" in the legends). Do not reuse that filename.
Give each new figure a distinct, descriptive module name
(`make_figure3_sequencing.py`, not `make_figure3.py`).
