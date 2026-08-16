---
name: manuscript-rebuild
description: Use when the Google Doc, the data, or a figure script changed and the manuscript outputs need regenerating in this repo — refreshing the preprint/journal PDF, the GitHub Pages site, or the committed figures, or when asked to produce an updated version of the manuscript or its artifacts.
---

# Rebuilding the manuscript and its artifacts

Every deliverable here — the bioRxiv PDF, the BJSM submission PDF, the GitHub
Pages site — is generated. The Google Doc is canonical for all manuscript text;
`analysis/data/*.csv` is canonical for all figures. You never edit prose, legends,
references, keywords, or author names in this repo. You regenerate them.

## The rule that protects the manuscript

**Never claim a rebuild succeeded without looking at the PDF pages.**

A build that exits 0 can still ship a broken manuscript: a clipped file path, a
missing bibliography, a grey box where a figure should be. These are invisible to
`grep` and to the exit code. Open the PDF and look.

## Full rebuild

Run from the repo root, in this order. Later steps consume earlier outputs.

```bash
export PATH="$HOME/.local/quarto/bin:$HOME/miniforge3/bin:$PATH"

python scripts/fetch_prose.py          # 1. Doc → _title.yml, _frontmatter.md,
                                       #    _prose.md, _legends/, _references.md,
                                       #    _supplement.md

cd analysis && uv sync \
  && uv run python make_figures_1_2_detections.py \
  && uv run python make_figure_3_sequencing.py \
  && uv run python make_supplement_1_wastewater.py && cd ..   # 2. figures

uv run --with fonttools python scripts/build_house_fonts.py   # 3. house fonts

quarto render                          # 4. → _site/ (HTML + PDF)
```

Then verify (next section) before committing.

### Two environment traps

| Trap | Symptom | Fix |
|---|---|---|
| Quarto and tectonic are not on `PATH` | `quarto: command not found` | The `export` line above. Quarto is user-local at `~/.local/quarto/bin`; tectonic at `~/miniforge3/bin`. Do not install another copy. |
| `build_house_fonts.py` needs `fontTools`, which `uv sync` puts only in `analysis/.venv` | `ModuleNotFoundError: No module named 'fontTools'` | Run it via `uv run --with fonttools`, exactly as above and as CI does. |

**The font trap is the dangerous one.** `house-preamble.tex` degrades silently via
`\IfFileExists`: skip the font step and the PDF still builds, but with substituted
system fonts instead of the house Gelasio/Arimo clones. Nothing warns you. If
tectonic mentions absolute font paths or non-reproducible fonts, your PDF is
mis-fonted — rebuild with the font step, and do not commit the bad one.

## Verify before committing

```bash
uv run --directory analysis --with pytest pytest ../tests -v   # expect 11 passed
```

Then **read `_site/index.pdf`** and confirm, by looking at the pages:

1. Title page carries the Doc's title and the full author block.
2. References are present and numbered 1–N with no gaps, matching the Doc.
3. Online supplemental methods appear before the supplemental figure.
4. Every figure renders as artwork — Central, Figures 1–3, supplemental figure 1.
   No grey boxes, no "missing image", no raw file paths.
5. No unfilled `[confirm]`/`[TBD]` placeholders, especially in the Data sharing
   statement.
6. No text clipped at the page edge. Long paths and code spans are the usual
   offenders; a truncated path in the Data-and-code list has shipped before.

A page count that changes a lot from the last build is worth explaining before you
commit.

## Commit

```bash
cp _site/index.pdf docs/team-canada-air-sampling.pdf
```

Commit the regenerated Doc-derived files (`_title.yml`, `_frontmatter.md`,
`_prose.md`, `_legends/`, `_references.md`, `_supplement.md`), the static figure
PNGs under `analysis/figures/`, any changed CSV, and that PDF snapshot.

Never commit: `cover-letter-bjsm.md` (the author's own draft), `_site/`, `fonts/`,
or anything under `analysis/figures/` ending in `.html` or `.pdf` — those are
gitignored on purpose and CI rebuilds them.

## Partial rebuilds

| What changed | Run |
|---|---|
| Google Doc text only | step 1, then 4 |
| Nothing (verifying reproducibility) | all steps; expect zero diffs |
| A data CSV or figure script | the script that consumes it (table below), then 4 |

Which script consumes which data:

| Data file | Script | Builds |
|---|---|---|
| `data/cartridges_long.csv` | `make_figures_1_2_detections.py` | Figures 1 and 2 |
| `data/sequencing_detections.csv` | `make_figure_3_sequencing.py` | Figure 3 |
| `data/ww_*.csv` | `make_supplement_1_wastewater.py` | Online supplemental figure 1 |

`cartridges_long.csv` also feeds `central_figure/make_timeline.py`, which produces
an editable SVG for the Illustrator master — the Central figure PNG is exported by
hand, not by the build.

When unsure which data changed, run all three figure scripts. They are cheap and
deterministic: unchanged inputs produce byte-identical outputs, so a needless
rebuild shows up as zero diffs rather than as churn.

Steps 3 and 4 are always needed to refresh the PDF.

## Fixing problems the right way

The Doc is canonical. When the rendered manuscript reads wrong, fix the cause, not
the output.

- **Wrong prose, legend, author, keyword, or reference** → edit the Google Doc, then
  re-run step 1. Never hand-edit `_prose.md`, `_legends/*.md`, `_references.md`,
  `_supplement.md`, `_frontmatter.md`, or `_title.yml`. They carry an
  AUTO-GENERATED banner and your edit is destroyed on the next fetch.
- **The Doc itself has a typo or artifact** (an inconsistent product name, a stray
  autolink like `[Fastq.gz](http://Fastq.gz)`) → report it to the co-authors as a
  Doc fix. Do not add normalization to `scripts/fetch_prose.py`; silently rewriting
  the authors' words is the worst thing this pipeline could do.
- **Wrong figure content** → fix the CSV in `analysis/data/` or the figure script,
  never the rendered PNG.
- **Layout or typography** → `theme-house.scss` (HTML) or `house-preamble.tex` (PDF).

## Red flags — stop

- About to report "rebuild complete" without having viewed the PDF pages
- About to edit a file whose first line says AUTO-GENERATED
- `quarto: command not found` and you are reaching for an installer
- Skipping the font step because the PDF "built fine anyway"
- Committing a PDF you have not looked at

## If the Doc fetch fails

`scripts/fetch_prose.py` reads the Doc's public export endpoint. A failure usually
means the Doc is no longer link-viewable. Report it — do not fall back to the
committed snapshots and describe the result as a fresh rebuild. CI has its own
deliberate fallback for this; you should not silently imitate it.

## CI does all of this too

Pushing to `main` (or running the **Render manuscript** workflow) performs these
same steps on a clean runner and commits the synced content and PDF back. Use CI
for the authoritative build; use the local sequence to check work before pushing.
If you change the build, change `.github/workflows/render.yml` to match — the two
must not drift.
