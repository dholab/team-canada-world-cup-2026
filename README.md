# Team Canada air-sampling study — interactive manuscript

Source for the interactive, single-page manuscript and the static submission
PDF of *"Air sampling in team congregate spaces for early detection of
respiratory virus threats"* (Team Canada, 2026 FIFA World Cup).

**📄 Read the manuscript privately:** [`PREVIEW.md`](PREVIEW.md) — a static
rendering (text + figures) viewable right here in the private repo. Use this
while the public site is held back.

**Live site:** *not published yet.* The interactive GitHub Pages site is
intentionally offline until the manuscript is ready (see
[Publishing](#publishing-going-live) below).

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
  When the site is live, the next build (push, manual, or the daily schedule)
  picks it up. The Doc must be link-viewable for CI to fetch it.
- **Figures / data:** edit files in [`analysis/`](analysis/); figures regenerate
  on the next build.
- **Refresh the private preview** (while the site is held back and CI is
  disabled): regenerate [`PREVIEW.md`](PREVIEW.md) locally —

  ```bash
  python scripts/fetch_prose.py                          # pull latest text
  cd analysis && uv sync && uv run python make_figures.py && cd ..   # figures
  python scripts/build_preview.py                        # rebuild PREVIEW.md
  ```

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

## Publishing (going live)

The interactive GitHub Pages site is currently **held back**: the Pages site is
deleted and the render workflow is disabled, so nothing is served publicly. Read
the manuscript in the meantime via [`PREVIEW.md`](PREVIEW.md).

> ⚠️ **Important — a private repo's Pages site is still fully public.** On GitHub
> Free/Team, GitHub Pages has no access control: once published, anyone with the
> URL can read the site even though this repo is private. There is no
> "share with only these people" option. For a truly access-controlled preview,
> use [`PREVIEW.md`](PREVIEW.md) (visible only to people with repo access), or
> host elsewhere with authentication (e.g. Netlify password protection). Only
> publish Pages when you are comfortable with the manuscript being world-readable.

When you are ready to publish the interactive site:

```bash
gh workflow enable  "Render manuscript" --repo dholab/team-canada-world-cup-2026
gh api -X POST repos/dholab/team-canada-world-cup-2026/pages -f build_type=workflow
gh workflow run     "Render manuscript" --repo dholab/team-canada-world-cup-2026
```

To make the **repository** itself public (separate from the site):
`gh repo edit dholab/team-canada-world-cup-2026 --visibility public`.
