# Submission-ready repo refactor — design

**Date:** 2026-08-15
**Goal:** Make this repo as simple and straightforward as possible for three
deliverables — the bioRxiv preprint PDF, the BJSM journal-submission PDF, and
the GitHub Pages interactive site — with the Google Doc as the single canonical
source for all manuscript text, and with data/scripts organized for a reader who
arrives from the published paper looking for more information.

**Canonical Doc:**
<https://docs.google.com/document/d/15X-Ae_qRDW37zmpdA9_6WPI9GPfRsK0hiWC7FYlwy4c/edit>

## Problem statement

Three classes of problem, in descending severity.

### 1. Submission blockers (content missing from every output)

| # | Problem | Evidence |
|---|---|---|
| B1 | **No reference list in any output.** `fetch_prose.py` `BODY_END` stops the body at `## References`, so all 49 Doc references are discarded. `_prose.md` carries 30 distinct inline citation markers (`\[1\]`, `\[10–12\]`, `\[46\]`, …) that resolve to nothing. | `scripts/fetch_prose.py:64`; `grep -o '\\\[[0-9,–-]*\\\]' _prose.md` |
| B2 | **Supplemental methods dropped.** The Doc's `## Online supplemental methods → ### Community wastewater comparison` sits *after* `## References`, so it is never fetched — yet `index.qmd` renders online supplemental figure 1, whose methods that section is. | Doc lines 347–349; `index.qmd:114-130` |
| B3 | **Keywords hard-coded, diverging from the Doc.** `index.qmd` hard-codes four keywords in YAML; the Doc has `### Keywords` carrying the same four. Two sources of truth for one field. | `index.qmd:5-9`; Doc line 33 |

### 2. Doc-canonicality violations (repo text that should come from the Doc)

| # | Problem | Evidence |
|---|---|---|
| C1 | **`build_preview.py` hard-codes full legend paragraphs** for Figure 1, Figure 2, and the Central figure, duplicating `_legends/*.md`. Already drifted: the hard-coded Figure 1 legend says "cartridge" where the Doc's current legend says "filter". | `scripts/build_preview.py:49-113` |
| C2 | **`build_preview.py` hard-codes an author list** that no longer matches the Doc-synced `_frontmatter.md` — it omits Isla E. Emmen and Nancy A. Wilson. | `scripts/build_preview.py:44-47` vs `_frontmatter.md` |
| C3 | **`docs/data-sharing-statement.md` is stale and contradicts the Doc.** It is a "copy this into the Doc" instruction file with unfilled placeholders (`[repository, e.g. NCBI GenBank/SRA]`, `[number]`). The Doc's Data sharing statement has since been completed with a real BioProject accession (PRJNA1513008) and the Lungfish archive URL. The repo file is outdated advice about an already-completed task. | `docs/data-sharing-statement.md` vs `_prose.md` Data sharing statement |

### 3. Organizational drift (a reader arriving from the paper gets lost)

| # | Problem | Evidence |
|---|---|---|
| O1 | **Script/figure names lie.** `make_figure3.py` builds the *wastewater supplement* ("Online supplemental figure 1"), while the actual Figure 3 is built by `make_figure3_sequencing.py`. The `.claude/skills/manuscript-figure/SKILL.md` even carries a "Numbering caution" section warning about this trap instead of fixing it. | `analysis/make_figure3.py`; `SKILL.md` §Numbering caution |
| O2 | **`analysis/README.md` documents only Figure 1.** Its title is "Air-sampling detections — Figure 1 (interactive + static)". Figures 2, 3, and the supplement are undocumented. | `analysis/README.md:1` |
| O3 | **Generated outputs are strewn through `analysis/`** alongside the scripts — 10 output files in the same directory as 4 scripts, with inconsistent tracking (`figure3_sequencing.html` is committed; every other interactive HTML is gitignored). | `analysis/` listing; `.gitignore` |
| O4 | **Three parallel renderings to keep in sync** — `_site/` (Pages), `docs/…pdf` (submission), and `PREVIEW.md` (40K in-repo preview). PREVIEW.md exists only because the repo is private; Pages replaces it on publication. | `PREVIEW.md`; `scripts/build_preview.py` |
| O5 | **Stale files:** `docs/wastewater-comparison-notes.md` (working notes superseded by the Doc's supplemental methods), `docs/superpowers/specs/2026-07-16-spc-invalid-data-design.md` (resolved), `CITATION_SOURCE_LOCATIONS.md` (88K), `cover-letter-bjsm.md` (untracked), `.DS_Store` ×2, `analysis/__pycache__/`. | repo listing |

## Decisions taken (user-confirmed)

- **A. Drop `PREVIEW.md`** and `scripts/build_preview.py`. Pages is the review
  surface once public; until then reviewers read the CI-built PDF artifact.
  Removes an entire third rendering and the C1/C2 drift with it.
- **B. References as a plain numbered list.** Parse the Doc's 49 reference
  entries into a Markdown ordered list. No `.bib`/CSL pipeline — the Paperpile
  markdown export does not carry structured bibliographic fields, and Quarto
  citation processing would require re-keying all 49 by hand.
- **C. Drop `CITATION_SOURCE_LOCATIONS.md`.**

## Design

### Part 1 — Make the Doc canonical for *all* text

Extend `scripts/fetch_prose.py` with three new extractors. It already writes
`_title.yml`, `_frontmatter.md`, `_legends/*.md`, and `_prose.md`; it gains:

**`_references.md`** — parse the Doc's References section. Each entry is a line
of the form:

```
## 1 \t [Serner A, Chamari K, … doi: 10.1080/…](http://paperpile.com/b/tA670F/58gc)
```

Extraction rule: from `## References` to the next `## ` that is not itself a
numbered reference heading, match `^##\s+(\d+)\s+\[(.+)\]\(https?://…paperpile…\)$`,
take the link *text* (dropping the Paperpile URL, exactly as `normalize()`
already does for inline citations), unescape the export's `\.` and `\-`, and
emit a Markdown ordered list. Numbering is taken from the Doc, not from list
auto-numbering, so a gap in the Doc surfaces as a gap rather than being silently
renumbered. Fails loudly if the count of parsed references does not match the
highest reference number seen.

**`_supplement.md`** — the Doc's `## Online supplemental methods` section
(heading and all subsections) through end of document, normalized with the same
Paperpile-unwrapping and blank-line collapsing that `normalize()` applies.

**Keywords into `_title.yml`** — read the Doc's `### Keywords` section, split on
commas, emit a YAML `keywords:` list. `index.qmd` drops its hard-coded block.

All three get the same AUTO-GENERATED banner the other outputs carry.

**Refactor while there:** `fetch_prose.py` has grown to ~250 lines of
module-level regex constants and eight functions with no shared structure.
Group the Doc-section helpers (`_section_body`, the new reference and supplement
extractors) so each output has one obvious extract-then-write pair, and give
`main()` a single ordered list of outputs. No behavior change beyond the three
additions — this is the file every future Doc change touches, so it should read
cleanly.

### Part 2 — `index.qmd` structure

Add, after the existing figure sections:

- `## References` including `_references.md` — placed after the manuscript body
  and before the supplemental material, matching journal convention.
- The supplemental methods (`_supplement.md`) inside the existing
  `## Supplemental material` section, *above* online supplemental figure 1, so
  the methods precede the figure they describe.

Remove the hard-coded `keywords:` YAML block (now supplied by `_title.yml`).

The existing "Data and code" section stays but is updated for the new script
names and paths (Part 3), and its stale reference to `make_figure3.py` as the
"Supplemental-figure pipeline" is corrected.

### Part 3 — Reorganize `analysis/` by role

```
analysis/
  README.md                        # covers all four figures
  pyproject.toml  uv.lock
  data/                            # committed tidy CSVs — inputs (unchanged)
  raw/                             # source export (unchanged)
  figures/                         # ALL generated outputs, one directory
  extract_data.py                  # raw/ → data/cartridges_long.csv
  make_figures_1_2_detections.py   # was make_figures.py     → Figures 1, 2
  make_figure_3_sequencing.py      # was make_figure3_sequencing.py → Figure 3
  make_supplement_1_wastewater.py  # was make_figure3.py     → Online supp. fig 1
  central_figure/                  # unchanged
```

Renames resolve O1: every script name states which manuscript figure it builds.
Output files move to `analysis/figures/` and are renamed to match
(`figure1_detections_static.png`, `supplement1_wastewater_interactive.html`, …).

Consequent edits: `index.qmd` iframe `src` and image paths, `_quarto.yml` if it
references any path, the CI `git add` list in `.github/workflows/render.yml`,
`.gitignore` patterns, and `.claude/skills/manuscript-figure/SKILL.md` (whose
"Numbering caution" section becomes obsolete and is replaced by the new naming
convention).

Tracking policy, made consistent: commit the static PNGs (needed by the PDF) and
the CSVs; gitignore every interactive HTML and every intermediate PDF, since CI
rebuilds them for Pages. This fixes the lone tracked `figure3_sequencing.html`.

### Part 4 — Documentation for the arriving reader

**Root `README.md`** — rewritten as the entry point a reader reaches from the
paper's data-availability statement. Answers, in order: what this study is;
where the three deliverables are; where the data is and what each column means;
which script builds which figure; how to rebuild everything.

**`analysis/README.md`** — rewritten to cover all four figures (O2), with a
table mapping each manuscript figure to its script, its input CSV, and its
outputs. Keeps the existing dataset-column documentation and the
`extract_data.py` regeneration instructions, which are good.

### Part 5 — Deletions

| Path | Reason |
|---|---|
| `PREVIEW.md`, `scripts/build_preview.py` | Decision A; removes the third rendering and its drift |
| `CITATION_SOURCE_LOCATIONS.md` | Decision C |
| `docs/data-sharing-statement.md` | C3 — stale instructions for a completed task, contradicts the Doc |
| `docs/wastewater-comparison-notes.md` | O5 — superseded by the Doc's supplemental methods |
| `docs/superpowers/specs/2026-07-16-spc-invalid-data-design.md` | O5 — resolved design doc |
| `.DS_Store`, `analysis/.DS_Store`, `analysis/__pycache__/` | O5 — never should have been present |

`cover-letter-bjsm.md` is untracked and is the user's own working draft for the
BJSM submission — **left in place, not deleted, not committed.**

CI workflow loses its `build_preview.py` step and its `PREVIEW.md` in the
`git add` list.

### Part 6 — Verification

The refactor is not complete until, locally:

1. `python scripts/fetch_prose.py` regenerates all outputs from the live Doc
   without error, and `_references.md` contains 49 entries.
2. `cd analysis && uv sync && uv run python <each of the three figure scripts>`
   writes every expected output into `analysis/figures/`.
3. `quarto render --to html` succeeds and the site loads with all four figures.
4. `quarto render index.qmd --to pdf` succeeds, and reading the PDF back
   confirms: the reference list is present and numbered 1–49; the supplemental
   methods section is present; no broken image or missing-figure boxes.
5. `git status` is clean of stray generated files.

Claims of completion must cite the actual command output, per
`superpowers:verification-before-completion`.

## Out of scope

- Rewriting any manuscript prose — the Doc is canonical; this repo renders it.
- Changing figure design, palette, or data. No figure content changes.
- Making the repo public, or configuring Pages — the user's call, at submission.
- Zenodo/DOI archiving — noted in the Doc's data sharing statement as a
  publication-time step.

## Risks

- **Doc fetch is the single point of failure.** CI already tolerates a failed
  fetch by falling back to committed snapshots; the three new outputs must be
  committed snapshots too, so that fallback still produces a complete manuscript.
- **Reference parsing is brittle to Doc restructuring.** Mitigated by failing
  loudly on a count mismatch rather than silently emitting a short list.
- **Path renames touch six files at once.** Mitigated by rendering both outputs
  before committing.
