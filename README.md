# Team Canada air-sampling manuscript

Source for *"Air sampling in team congregate spaces for early detection of
respiratory virus threats"* (Team Canada, 2026 FIFA World Cup) — an interactive
single-page manuscript plus a static submission PDF, both built from one source.

- **Read it:** [`PREVIEW.md`](PREVIEW.md) (text + figures, viewable in the repo).
- **Submission PDF:** [`docs/team-canada-air-sampling.pdf`](docs/team-canada-air-sampling.pdf) — the bioRxiv/BJSM build, rebuilt and committed by CI.

## How it fits together

| Input | Output |
| --- | --- |
| Prose + legends — the [Google Doc](https://docs.google.com/document/d/15X-Ae_qRDW37zmpdA9_6WPI9GPfRsK0hiWC7FYlwy4c/edit), pulled by [`scripts/fetch_prose.py`](scripts/fetch_prose.py) into `_prose.md` / `_frontmatter.md` / `_legends/` | Interactive HTML site (`_site/`) and the submission PDF (`docs/…pdf`), rendered by Quarto from [`index.qmd`](index.qmd) |
| Data — `analysis/data/*.csv` → figures by [`analysis/`](analysis/) scripts | Figures 1–3 + online supplemental figure 1 |

House style (cream/teal/terracotta, Georgia + Arial) lives in
[`theme-house.scss`](theme-house.scss) (HTML) and
[`house-preamble.tex`](house-preamble.tex) (PDF, white background).

## Building

**In CI (preferred).** Run the **Render manuscript** workflow on demand
(Actions tab → *Run workflow*), or push to `main`. It pulls the Doc, rebuilds
figures and both outputs, and commits the synced content + PDF back. It is
**not** scheduled — trigger it when you've made edits (e.g. before submitting a
new preprint version). The submission PDF uses open, metric-compatible font
clones (Gelasio ≈ Georgia, Arimo ≈ Arial) so it builds reproducibly.

**Locally.** Requires [Quarto](https://quarto.org), [uv](https://docs.astral.sh/uv/),
and [tectonic](https://tectonic-typesetting.github.io/).

```bash
python scripts/fetch_prose.py                                   # pull the Doc
cd analysis && uv sync && uv run python make_figures.py \
  && uv run python make_figure3_sequencing.py && cd ..          # figures
python scripts/build_house_fonts.py                             # Gelasio (→ fonts/)
quarto render                                                   # → _site/ (HTML + PDF)
python scripts/build_preview.py                                 # → PREVIEW.md
```

> **Note — a private repo's GitHub Pages site is still public.** Publishing Pages
> makes the site world-readable via its URL. Keep it held back until the
> manuscript is ready; use [`PREVIEW.md`](PREVIEW.md) for private review.
