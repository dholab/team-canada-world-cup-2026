# Team Canada air-sampling study — interactive manuscript

Source for the interactive, single-page manuscript and the static submission
PDF of *"Air sampling in team congregate spaces for early detection of
respiratory virus threats"* (Team Canada, 2026 FIFA World Cup).

**Live site:** https://dholab.github.io/team-canada-world-cup-2026/ *(after the
first Pages deploy; private until the repo is made public)*

## How it works

One source, two outputs, all built in CI:

| Piece | Where | What |
| --- | --- | --- |
| Prose | Google Docs → [`manuscript/_prose.md`](manuscript/_prose.md) | Authored in the Doc; pulled and normalized by [`scripts/fetch_prose.py`](scripts/fetch_prose.py). |
| Figures | [`analysis/`](analysis/) | `uv run python make_figures.py` builds interactive (Plotly) and static (PNG/PDF) figures from [`analysis/data/cartridges_long.csv`](analysis/data/cartridges_long.csv). |
| Manuscript | [`manuscript/index.qmd`](manuscript/index.qmd) | Includes the prose and embeds the figures inline. Rendered by Quarto to HTML (interactive) and PDF (submission). |
| Automation | [`.github/workflows/render.yml`](.github/workflows/render.yml) | Fetch Doc → build figures → `quarto render` → deploy Pages + upload PDF. |

## Editing

- **Text:** edit the [Google Doc](https://docs.google.com/document/d/15X-Ae_qRDW37zmpdA9_6WPI9GPfRsK0hiWC7FYlwy4c/edit).
  The next build (push, manual, or the daily schedule) picks it up. The Doc must
  be link-viewable for CI to fetch it.
- **Figures / data:** edit files in [`analysis/`](analysis/); figures regenerate
  on the next build.

## Build locally

```bash
# Figures
cd analysis && uv sync && uv run python make_figures.py && cd ..
# Prose (optional: refresh from the Doc)
python scripts/fetch_prose.py
# Render
quarto render          # -> _site/ (HTML) and the submission PDF
```

Requires [Quarto](https://quarto.org) and [uv](https://docs.astral.sh/uv/).

## Going public

The repo starts private. To publish: `gh repo edit dholab/team-canada-world-cup-2026 --visibility public`.
No structural change is needed.
