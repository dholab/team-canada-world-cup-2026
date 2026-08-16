# Submission-Ready Repo Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make this repo produce three complete, correct deliverables (bioRxiv PDF, BJSM PDF, GitHub Pages site) from one canonical Google Doc, with data and scripts organized for a reader arriving from the published paper.

**Architecture:** `scripts/fetch_prose.py` is the single Doc→repo boundary; it gains three new extractors (references, supplemental methods, keywords) so no manuscript text is hard-coded anywhere. `index.qmd` composes the Doc-derived includes with figures. `analysis/` is reorganized so each script name states which manuscript figure it builds, and all generated outputs land in one `analysis/figures/` directory.

**Tech Stack:** Python 3.11+ (stdlib `re`/`urllib` only for `fetch_prose.py`; pandas/plotly/matplotlib via `uv` for figures), Quarto, tectonic (PDF), GitHub Actions.

**Spec:** [`docs/superpowers/specs/2026-08-15-submission-repo-refactor-design.md`](../specs/2026-08-15-submission-repo-refactor-design.md)

## Global Constraints

- **The Google Doc is canonical for all manuscript text.** Doc ID
  `15X-Ae_qRDW37zmpdA9_6WPI9GPfRsK0hiWC7FYlwy4c`. No task may hard-code
  manuscript prose, legends, references, keywords, author names, or the title
  into any repo file. Every Doc-derived file carries the banner:
  `<!-- AUTO-GENERATED from the manuscript Google Doc by scripts/fetch_prose.py. Do not edit by hand; edit the Doc. -->`
- **`fetch_prose.py` uses the Python standard library only** — no new
  dependencies. It runs in CI before `uv sync`, with bare `python`.
- **The Doc has exactly 49 references**, numbered 1–49 with no gaps (verified
  2026-08-15). Reference parsing must fail loudly on any count mismatch.
- **House palette** (do not alter): `TEAL "#163139"`, `TERRA "#C16A3C"`,
  `CREAM "#F8F4E9"`, `RULE "#dcd3c2"`.
- **No figure content, data, or design changes.** This refactor moves and
  renames files; plotted output must be byte-comparable in content.
- **Tracking policy:** commit static PNGs, CSVs, and the Doc-derived Markdown;
  gitignore all interactive HTML and all intermediate PDFs.
- **Do not delete or commit `cover-letter-bjsm.md`** — untracked user draft.
- **Test runner:** `pytest`, run via `uv run --with pytest pytest` from
  `analysis/` (the only place with a Python environment). Tests for
  `scripts/fetch_prose.py` live in `tests/` at the repo root and are run with
  `uv run --directory analysis --with pytest pytest ../tests -v`.

---

### Task 1: Test harness for `fetch_prose.py`

Establishes a pytest setup with a frozen Doc fixture, so every later parser
change is testable offline without hitting the network.

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/doc_export.md`
- Create: `tests/test_fetch_prose.py`
- Modify: `.gitignore` (add `.pytest_cache/`)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: pytest fixture `doc_md` (a `str`, the full frozen Doc markdown
  export) available to all later tests; module import path for
  `scripts/fetch_prose.py` as module `fetch_prose`.

- [ ] **Step 1: Capture the live Doc as a frozen fixture**

```bash
mkdir -p tests/fixtures
curl -sL -A "Mozilla/5.0" \
  "https://docs.google.com/document/d/15X-Ae_qRDW37zmpdA9_6WPI9GPfRsK0hiWC7FYlwy4c/export?format=md" \
  -o tests/fixtures/doc_export.md
wc -c tests/fixtures/doc_export.md
```

Expected: roughly 56,000 bytes. If it is under 10,000 the Doc is not
link-viewable and you must stop and ask the user to check sharing settings.

- [ ] **Step 2: Write `tests/conftest.py`**

```python
"""Shared fixtures. Makes scripts/ importable and loads the frozen Doc export."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(scope="session")
def doc_md() -> str:
    """The frozen Google Doc markdown export (captured 2026-08-15)."""
    return (Path(__file__).parent / "fixtures" / "doc_export.md").read_text(
        encoding="utf-8"
    )
```

- [ ] **Step 3: Write a smoke test that the existing parsers still work**

```python
"""Tests for scripts/fetch_prose.py — the Doc -> repo boundary."""
import fetch_prose


def test_title_is_parsed_from_the_doc(doc_md):
    m = fetch_prose.DOC_TITLE.search(doc_md)
    assert m is not None
    assert "Air sampling in team congregate spaces" in m.group("title")


def test_legends_include_all_four_figures(doc_md):
    legends = fetch_prose.extract_legends(doc_md)
    assert set(legends) == {"central", "fig1", "fig2", "fig3", "supp1"}


def test_body_starts_at_abstract_and_stops_at_references(doc_md):
    body = fetch_prose.normalize(doc_md)
    assert body.lstrip().startswith("<!-- AUTO-GENERATED")
    assert "## Abstract" in body
    assert "## References" not in body
```

- [ ] **Step 4: Run the tests**

Run: `uv run --directory analysis --with pytest pytest ../tests -v`
Expected: 3 passed. These characterize existing behavior before changes.

- [ ] **Step 5: Add `.pytest_cache/` to `.gitignore`**

Append under the existing Python-environment block:

```
.pytest_cache/
```

- [ ] **Step 6: Commit**

```bash
git add tests .gitignore
git commit -m "test: add pytest harness and frozen Doc fixture for fetch_prose"
```

---

### Task 2: Extract the reference list from the Doc

Fixes blocker B1 — 49 references currently discarded, leaving 30 inline
citation markers pointing at nothing.

**Files:**
- Modify: `scripts/fetch_prose.py`
- Modify: `tests/test_fetch_prose.py`

**Interfaces:**
- Consumes: `doc_md` fixture from Task 1.
- Produces: `fetch_prose.extract_references(md: str) -> list[tuple[int, str]]`
  returning `(number, citation_text)` pairs in Doc order;
  `fetch_prose.write_references(md: str) -> None` writing `_references.md`.
  Task 4 includes that file from `index.qmd`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fetch_prose.py`:

```python
def test_extracts_all_49_references(doc_md):
    refs = fetch_prose.extract_references(doc_md)
    assert len(refs) == 49
    assert [n for n, _ in refs] == list(range(1, 50))


def test_reference_text_drops_the_paperpile_url(doc_md):
    refs = dict(fetch_prose.extract_references(doc_md))
    assert "paperpile.com" not in refs[1]
    assert refs[1].startswith("Serner A, Chamari K")
    assert "10.1080/24733938.2024.2357568" in refs[1]


def test_reference_text_unescapes_doc_export_backslashes(doc_md):
    refs = dict(fetch_prose.extract_references(doc_md))
    # The Doc export escapes the period after "Qatar 2022" as "2022\."
    assert "\\." not in refs[1]


def test_reference_count_mismatch_raises(doc_md):
    # Drop reference 49 from the text; the parser must refuse the result
    # rather than silently emitting a short list.
    broken = doc_md.replace("## 49 \t[", "## 49x \t[")
    try:
        fetch_prose.extract_references(broken)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit on a reference count mismatch")
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --directory analysis --with pytest pytest ../tests -v -k reference`
Expected: FAIL — `AttributeError: module 'fetch_prose' has no attribute 'extract_references'`

- [ ] **Step 3: Implement the extractor**

Add a module-level constant next to the other regexes in
`scripts/fetch_prose.py`:

```python
# The Doc's References section lists each entry as its own heading:
#   "## 1 \t[Serner A, … doi: 10.1080/…](http://paperpile.com/b/tA670F/58gc)"
# We keep the link text (the formatted citation) and drop the Paperpile URL,
# exactly as normalize() already does for inline citation markers.
REFERENCE_ENTRY = re.compile(
    r"^##\s+(?P<num>\d+)\s*\[(?P<text>.+?)\]\("
    r"https?://(?:www\.)?paperpile\.com/[^)]*\)\s*$",
    re.M,
)
```

Add the function after `extract_legends`:

```python
def extract_references(md: str) -> list[tuple[int, str]]:
    """Pull the numbered reference list from the Doc's '## References' section.

    Returns [(number, citation_text), ...] in Doc order. The Paperpile URL is
    dropped and the export's backslash escapes are undone, so each entry is
    plain formatted Markdown. Raises SystemExit if the numbering is not a
    complete 1..N run — a silently short bibliography would ship a manuscript
    with dangling citation markers."""
    sec = re.search(r"^##\s+References\b.*$", md, re.M)
    if not sec:
        raise SystemExit("Could not find '## References' — Doc structure changed?")
    region = md[sec.end():]
    # Stop at the first non-reference heading with actual text (e.g.
    # '## Figure legends'). The Doc emits bare '## ' divider lines from its page
    # breaks, so require a non-'#' character after the hashes.
    stop = re.search(r"^##\s+(?!\d+\s*\[)[^\s#].*$", region, re.M)
    if stop:
        region = region[: stop.start()]

    refs: list[tuple[int, str]] = []
    for m in REFERENCE_ENTRY.finditer(region):
        text = m.group("text")
        # Undo the markdown export's escaping of literal punctuation.
        text = re.sub(r"\\([.\-\[\]&#])", r"\1", text).strip()
        refs.append((int(m.group("num")), text))

    if not refs:
        raise SystemExit("Parsed zero references from the Doc's References section.")
    expected = list(range(1, len(refs) + 1))
    if [n for n, _ in refs] != expected:
        raise SystemExit(
            f"Reference numbering is not a complete 1..{len(refs)} run: "
            f"got {[n for n, _ in refs]}"
        )
    return refs
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run --directory analysis --with pytest pytest ../tests -v -k reference`
Expected: 4 passed.

- [ ] **Step 5: Add the writer**

Add the output path next to the other path constants:

```python
REFERENCES = HERE.parent / "_references.md"
```

Add the writer after `write_legends`:

```python
def write_references(md: str) -> None:
    """Write the Doc's bibliography to _references.md as a numbered list.

    Numbers are written explicitly (not left to Markdown auto-numbering) so the
    rendered list always matches the inline citation markers in the prose."""
    refs = extract_references(md)
    body = "\n\n".join(f"{num}. {text}" for num, text in refs)
    REFERENCES.write_text(BANNER + body + "\n", encoding="utf-8")
    print(f"wrote {REFERENCES} ({len(refs)} references)")
```

- [ ] **Step 6: Hoist the duplicated banner into one constant**

The banner string is currently repeated verbatim in `normalize`,
`write_legends`, and `write_frontmatter`. Add one module-level constant near
the path constants:

```python
BANNER = (
    "<!-- AUTO-GENERATED from the manuscript Google Doc by "
    "scripts/fetch_prose.py. Do not edit by hand; edit the Doc. -->\n\n"
)
```

Then replace the three inline copies with `BANNER`:
- In `normalize`, replace the local `header = (...)` assignment and use
  `return BANNER + body`.
- In `write_legends`, delete the local `banner = (...)` and use `BANNER`.
- In `write_frontmatter`, delete the local `banner = (...)` and use `BANNER`.

- [ ] **Step 7: Wire it into `main()` and run the full suite**

In `main()`, add after `write_legends(...)`:

```python
    write_references(raw)
```

Run: `uv run --directory analysis --with pytest pytest ../tests -v`
Expected: 7 passed.

- [ ] **Step 8: Generate the file and eyeball it**

```bash
python scripts/fetch_prose.py
head -8 _references.md
tail -4 _references.md
grep -c '^[0-9]*\. ' _references.md
```

Expected: banner then `1. Serner A, …`; last entry numbered 49; count is 49.

- [ ] **Step 9: Commit**

```bash
git add scripts/fetch_prose.py tests/test_fetch_prose.py _references.md
git commit -m "feat: extract the Doc's 49-entry reference list into _references.md"
```

---

### Task 3: Extract supplemental methods and keywords from the Doc

Fixes blockers B2 (supplemental methods never fetched) and B3 (keywords
hard-coded in two places).

**Files:**
- Modify: `scripts/fetch_prose.py`
- Modify: `tests/test_fetch_prose.py`

**Interfaces:**
- Consumes: `BANNER`, `_yaml_quote`, and the `HERE` path constant from Task 2.
- Produces: `fetch_prose.extract_supplement(md: str) -> str` and
  `fetch_prose.write_supplement(md: str) -> None` writing `_supplement.md`;
  `fetch_prose.extract_keywords(md: str) -> list[str]`, with `write_title`
  extended to emit a YAML `keywords:` list into `_title.yml`. Task 4 consumes
  both.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fetch_prose.py`:

```python
def test_supplement_contains_the_wastewater_methods(doc_md):
    supp = fetch_prose.extract_supplement(doc_md)
    assert "### Community wastewater comparison" in supp
    assert "PMMoV-normalized viral index" in supp
    assert "JWPCP" in supp


def test_supplement_drops_paperpile_urls(doc_md):
    supp = fetch_prose.extract_supplement(doc_md)
    assert "paperpile.com" not in supp


def test_supplement_excludes_the_figure_legends(doc_md):
    # The legends section precedes supplemental methods in the Doc and is
    # written separately to _legends/; it must not be duplicated here.
    supp = fetch_prose.extract_supplement(doc_md)
    assert "## Figure legends" not in supp


def test_keywords_come_from_the_doc(doc_md):
    assert fetch_prose.extract_keywords(doc_md) == [
        "Respiratory infection",
        "team sport",
        "athlete health",
        "public health",
    ]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --directory analysis --with pytest pytest ../tests -v -k "supplement or keyword"`
Expected: FAIL — `AttributeError: module 'fetch_prose' has no attribute 'extract_supplement'`

- [ ] **Step 3: Implement both extractors**

Add the path constant next to the others:

```python
SUPPLEMENT = HERE.parent / "_supplement.md"
```

Add both functions after `write_references`:

```python
def extract_supplement(md: str) -> str:
    """Pull the Doc's '## Online supplemental methods' section through the end
    of the document. This sits after '## References' in the Doc, so the main
    body normalizer never sees it; index.qmd renders it above the online
    supplemental figure whose methods it describes."""
    sec = re.search(r"^##\s+Online supplemental methods\b.*$", md, re.M)
    if not sec:
        raise SystemExit(
            "Could not find '## Online supplemental methods' — Doc structure changed?"
        )
    body = md[sec.start():]
    # Same Paperpile unwrapping the main body gets: keep the citation marker
    # text, drop the URL.
    body = re.sub(
        r"\[((?:[^\[\]]|\\\[|\\\])*)\]\(https?://(?:www\.)?paperpile\.com/[^)]*\)",
        r"\1", body)
    body = re.sub(r"^#{1,6}\s*$\n?", "", body, flags=re.M)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body


def write_supplement(md: str) -> None:
    body = extract_supplement(md)
    SUPPLEMENT.write_text(BANNER + body, encoding="utf-8")
    print(f"wrote {SUPPLEMENT} ({len(body)} bytes)")


def extract_keywords(md: str) -> list[str]:
    """The Doc's '### Keywords' section, one comma-separated line."""
    body = _section_body(md, "Keywords")
    if not body:
        return []
    return [kw.strip() for kw in body.replace("\n", " ").split(",") if kw.strip()]
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run --directory analysis --with pytest pytest ../tests -v -k "supplement or keyword"`
Expected: 4 passed.

- [ ] **Step 5: Emit keywords into `_title.yml`**

In `write_title`, after the `subtitle` block and before `TITLE_YML.write_text`,
add:

```python
    keywords = extract_keywords(md)
    if keywords:
        lines.append("keywords:")
        lines.extend(f"  - {_yaml_quote(kw)}" for kw in keywords)
```

- [ ] **Step 6: Wire `write_supplement` into `main()`**

In `main()`, add after `write_references(raw)`:

```python
    write_supplement(raw)
```

- [ ] **Step 7: Run the full suite and regenerate**

```bash
uv run --directory analysis --with pytest pytest ../tests -v
python scripts/fetch_prose.py
cat _title.yml
head -12 _supplement.md
```

Expected: 11 passed; `_title.yml` shows a `keywords:` list of four;
`_supplement.md` opens with the banner then
`## Online supplemental methods`.

- [ ] **Step 8: Commit**

```bash
git add scripts/fetch_prose.py tests/test_fetch_prose.py _supplement.md _title.yml
git commit -m "feat: pull supplemental methods and keywords from the canonical Doc"
```

---

### Task 4: Wire references, supplement, and keywords into `index.qmd`

Makes the three new Doc-derived files actually appear in the PDF and the site.

**Files:**
- Modify: `index.qmd`

**Interfaces:**
- Consumes: `_references.md`, `_supplement.md`, and the `keywords:` field of
  `_title.yml` from Tasks 2–3.
- Produces: the rendered manuscript structure Task 8 verifies.

- [ ] **Step 1: Remove the hard-coded keywords block**

Delete lines 5–9 of `index.qmd` (the `keywords:` list). The YAML front matter
becomes just the explanatory comments:

```yaml
---
# title, subtitle, and keywords come from the Doc via _title.yml
# (metadata-files in _quarto.yml) — do not hard-code them here; edit the
# Google Doc. No date: the Doc carries none, so the title page shows none.
---
```

- [ ] **Step 2: Add the References section**

Insert after the `#fig-sequencing` div's closing `:::` and *before* the
`## Data and code` section:

```markdown
{{< pagebreak >}}

## References

{{< include _references.md >}}
```

- [ ] **Step 3: Add supplemental methods above the supplemental figure**

In the `## Supplemental material` section, insert the include between the
heading and the `::: {#supp-wastewater}` div:

```markdown
## Supplemental material

{{< include _supplement.md >}}

::: {#supp-wastewater}
```

Note the Doc's supplement text opens with its own `## Online supplemental
methods` heading, so do not add another heading here.

- [ ] **Step 4: Verify the render**

```bash
quarto render index.qmd --to html
grep -c "Serner A" _site/index.html
grep -c "Community wastewater comparison" _site/index.html
```

Expected: each grep returns at least 1.

- [ ] **Step 5: Commit**

```bash
git add index.qmd
git commit -m "feat: render references, supplemental methods, and Doc keywords"
```

---

### Task 5: Reorganize `analysis/` — rename scripts, centralize outputs

Fixes O1 (`make_figure3.py` builds the *supplement*, not Figure 3) and O3
(outputs strewn among scripts, inconsistently tracked).

**Files:**
- Rename: `analysis/make_figures.py` → `analysis/make_figures_1_2_detections.py`
- Rename: `analysis/make_figure3_sequencing.py` → `analysis/make_figure_3_sequencing.py`
- Rename: `analysis/make_figure3.py` → `analysis/make_supplement_1_wastewater.py`
- Modify: all three (add a `FIGURES` output constant, update `main()`)
- Modify: `analysis/pyproject.toml` (the `make-figures` script entry point)
- Create: `analysis/figures/.gitkeep`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: these exact output paths, which Tasks 6 and 7 reference:
  - `analysis/figures/figure1_detections_interactive.html`
  - `analysis/figures/figure1_detections_static.pdf` / `.png`
  - `analysis/figures/figure2_houston_interactive.html`
  - `analysis/figures/figure2_houston.pdf` / `.png`
  - `analysis/figures/figure3_sequencing.html`
  - `analysis/figures/figure3_sequencing.png`
  - `analysis/figures/figure3_sequencing_transparent.png`
  - `analysis/figures/supplement1_wastewater_interactive.html`
  - `analysis/figures/supplement1_wastewater.pdf` / `.png`

- [ ] **Step 1: Rename the three scripts with git**

```bash
cd analysis
git mv make_figures.py make_figures_1_2_detections.py
git mv make_figure3_sequencing.py make_figure_3_sequencing.py
git mv make_figure3.py make_supplement_1_wastewater.py
mkdir -p figures && touch figures/.gitkeep
```

- [ ] **Step 2: Add a `FIGURES` constant to each script**

In each of the three scripts, immediately after the existing
`HERE = pathlib.Path(__file__).parent` line, add:

```python
# All generated figure outputs land in one directory so a reader can find every
# rendered figure without picking through the scripts that build them.
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)
```

- [ ] **Step 3: Point `make_figures_1_2_detections.py` at `FIGURES`**

Replace the four output paths in its `main()` (currently `HERE / "figure1_…"`):

```python
    build_interactive(df, FIGURES / "figure1_detections_interactive.html")
    build_static(df, FIGURES / "figure1_detections_static.pdf",
                 FIGURES / "figure1_detections_static.png")
    build_figure2(df, "Houston",
                  FIGURES / "figure2_houston.pdf", FIGURES / "figure2_houston.png")
    build_figure2_interactive(df, "Houston",
                              FIGURES / "figure2_houston_interactive.html")
```

Keep the surrounding call structure exactly as it is; only the path arguments
change. If `build_figure2`'s existing signature differs, preserve it and change
only the two path arguments.

- [ ] **Step 4: Point the other two scripts at `FIGURES`**

In `make_figure_3_sequencing.py` `main()`:

```python
    build_interactive(df, FIGURES / "figure3_sequencing.html")
    build_static(df, FIGURES / "figure3_sequencing.png", bg="#FFFFFF")
    build_static(df, FIGURES / "figure3_sequencing_transparent.png",
                 transparent=True)
```

In `make_supplement_1_wastewater.py` `main()`:

```python
    build_static(FIGURES / "supplement1_wastewater.pdf",
                 FIGURES / "supplement1_wastewater.png")
    build_interactive(FIGURES / "supplement1_wastewater_interactive.html")
```

- [ ] **Step 5: Update the module docstrings**

Each script's docstring names its old output files. Update the filenames in
all three to match the new paths, and correct
`make_supplement_1_wastewater.py`'s docstring to say it builds **online
supplemental figure 1**, not "figure 3".

- [ ] **Step 6: Fix the `pyproject.toml` entry point**

The `[project.scripts]` entry references the old module name:

```toml
[project.scripts]
make-figures = "make_figures_1_2_detections:main"
```

- [ ] **Step 7: Rebuild every figure and confirm the outputs**

```bash
cd analysis
uv sync
uv run python make_figures_1_2_detections.py
uv run python make_figure_3_sequencing.py
uv run python make_supplement_1_wastewater.py
ls -1 figures/
```

Expected: all 10 output files listed above are present.

- [ ] **Step 8: Remove the old output files from the repo root**

```bash
cd analysis
git rm --cached figure3_sequencing.html
rm -f figure1_interactive.html figure1_static.pdf figure1_static.png \
      figure2_houston.pdf figure2_houston.png figure2_houston_interactive.html \
      figure3_sequencing.html figure3_sequencing.png \
      figure3_sequencing_transparent.png figure3_wastewater.pdf \
      figure3_wastewater.png figure3_wastewater_interactive.html
git rm --cached figure1_static.png figure2_houston.png figure3_sequencing.png \
      figure3_sequencing_transparent.png figure3_wastewater.png
```

- [ ] **Step 9: Update `.gitignore` for the new layout**

Replace the existing "Generated figures" block with:

```
# Generated figures. Static PNGs are committed (the PDF build needs them and
# they render on GitHub); interactive HTML and intermediate PDFs are rebuilt in
# CI from analysis/data/ and are not tracked.
analysis/figures/*.html
analysis/figures/*.pdf
```

- [ ] **Step 10: Commit**

```bash
git add -A analysis .gitignore
git commit -m "refactor: name figure scripts for the figures they build; centralize outputs"
```

---

### Task 6: Update `index.qmd` and CI for the new figure paths

**Files:**
- Modify: `index.qmd`
- Modify: `.github/workflows/render.yml`

**Interfaces:**
- Consumes: the nine output paths from Task 5.
- Produces: a rendering CI pipeline Task 8 verifies end to end.

- [ ] **Step 1: Update the five figure paths in `index.qmd`**

| Old | New |
|---|---|
| `analysis/figure1_interactive.html` | `analysis/figures/figure1_detections_interactive.html` |
| `analysis/figure1_static.png` | `analysis/figures/figure1_detections_static.png` |
| `analysis/figure2_houston_interactive.html` | `analysis/figures/figure2_houston_interactive.html` |
| `analysis/figure2_houston.png` | `analysis/figures/figure2_houston.png` |
| `analysis/figure3_sequencing.html` | `analysis/figures/figure3_sequencing.html` |
| `analysis/figure3_sequencing.png` | `analysis/figures/figure3_sequencing.png` |
| `analysis/figure3_wastewater_interactive.html` | `analysis/figures/supplement1_wastewater_interactive.html` |
| `analysis/figure3_wastewater.png` | `analysis/figures/supplement1_wastewater.png` |

The Central figure path (`analysis/central_figure/central_figure.png`) is
unchanged.

- [ ] **Step 2: Update the "Data and code" script links**

In that section, replace the three stale links so they name the right script
for each figure:

```markdown
- Data: [`analysis/data/cartridges_long.csv`](https://github.com/dholab/team-canada-world-cup-2026/blob/main/analysis/data/cartridges_long.csv)
- Figures 1 and 2: [`analysis/make_figures_1_2_detections.py`](https://github.com/dholab/team-canada-world-cup-2026/blob/main/analysis/make_figures_1_2_detections.py)
- Figure 3 (sequencing): [`analysis/make_figure_3_sequencing.py`](https://github.com/dholab/team-canada-world-cup-2026/blob/main/analysis/make_figure_3_sequencing.py) with data [`analysis/data/sequencing_detections.csv`](https://github.com/dholab/team-canada-world-cup-2026/blob/main/analysis/data/sequencing_detections.csv)
- Online supplemental figure 1 (wastewater): [`analysis/make_supplement_1_wastewater.py`](https://github.com/dholab/team-canada-world-cup-2026/blob/main/analysis/make_supplement_1_wastewater.py)
```

- [ ] **Step 3: Update the CI figure-build step**

In `.github/workflows/render.yml`, the "Build figures" step must run all three
scripts (it currently omits the wastewater supplement entirely):

```yaml
      - name: Build figures
        working-directory: analysis
        run: |
          uv sync
          uv run python make_figures_1_2_detections.py
          uv run python make_figure_3_sequencing.py
          uv run python make_supplement_1_wastewater.py
```

- [ ] **Step 4: Update the CI commit file list**

Replace the `git add -A --` line's paths. `PREVIEW.md` is removed in Task 7, so
it is already absent here; the new Doc-derived files are added:

```yaml
          git add -A -- _title.yml _prose.md _frontmatter.md _references.md \
            _supplement.md _legends \
            analysis/figures/figure1_detections_static.png \
            analysis/figures/figure2_houston.png \
            analysis/figures/supplement1_wastewater.png \
            analysis/figures/figure3_sequencing.png \
            analysis/figures/figure3_sequencing_transparent.png \
            analysis/data docs/team-canada-air-sampling.pdf
```

- [ ] **Step 5: Verify the site renders with all figures**

```bash
quarto render --to html
ls _site/analysis/figures/
grep -o 'analysis/figures/[a-z0-9_]*\.\(html\|png\)' _site/index.html | sort -u
```

Expected: the four iframe HTML files are present in `_site/analysis/figures/`
and the greps show the new paths, with no `figure3_wastewater` references
remaining.

- [ ] **Step 6: Commit**

```bash
git add index.qmd .github/workflows/render.yml
git commit -m "refactor: point index.qmd and CI at the reorganized figure paths"
```

---

### Task 7: Delete stale files and rewrite both READMEs

Executes the spec's Part 5 deletions and Part 4 documentation rewrite.

**Files:**
- Delete: `PREVIEW.md`, `scripts/build_preview.py`, `CITATION_SOURCE_LOCATIONS.md`,
  `docs/data-sharing-statement.md`, `docs/wastewater-comparison-notes.md`,
  `docs/superpowers/specs/2026-07-16-spc-invalid-data-design.md`,
  `.DS_Store`, `analysis/.DS_Store`, `analysis/__pycache__/`
- Modify: `README.md`, `analysis/README.md`,
  `.claude/skills/manuscript-figure/SKILL.md`, `.github/workflows/render.yml`

**Interfaces:**
- Consumes: the final file layout from Tasks 5–6.
- Produces: the documentation a reader arriving from the paper lands on.

- [ ] **Step 1: Delete the stale files**

Do **not** touch `cover-letter-bjsm.md` — it is the user's untracked draft.

```bash
git rm PREVIEW.md scripts/build_preview.py CITATION_SOURCE_LOCATIONS.md \
       docs/data-sharing-statement.md docs/wastewater-comparison-notes.md \
       docs/superpowers/specs/2026-07-16-spc-invalid-data-design.md
rm -f .DS_Store analysis/.DS_Store
rm -rf analysis/__pycache__
```

- [ ] **Step 2: Remove the PREVIEW build step from CI**

In `.github/workflows/render.yml`, delete the
`python scripts/build_preview.py` line from the commit step's `run:` block.
Confirm nothing else references the preview:

```bash
grep -rn "build_preview\|PREVIEW" .github/ index.qmd _quarto.yml scripts/ || echo "clean"
```

Expected: `clean`.

- [ ] **Step 3: Rewrite the root `README.md`**

```markdown
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
| **Interactive version** | GitHub Pages site, with every figure explorable |
| **Submission PDF** | [`docs/team-canada-air-sampling.pdf`](docs/team-canada-air-sampling.pdf) — rebuilt and committed by CI |

## The data

| File | What it holds |
| --- | --- |
| [`analysis/data/cartridges_long.csv`](analysis/data/cartridges_long.csv) | The primary dataset. One row per cartridge × target virus (728 rows = 182 respiratory cartridges × 4 targets). |
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
python scripts/build_house_fonts.py                # Gelasio (→ fonts/)
quarto render                                      # → _site/ (HTML + PDF)
```
```

- [ ] **Step 4: Rewrite `analysis/README.md`**

Replace the Figure-1-only title and opening table with a full figure map, and
keep the existing dataset-column reference and `extract_data.py` section
verbatim — they are accurate and useful.

```markdown
# Analysis — data and figure pipelines

Every figure in the manuscript is built by a Python script from a committed
tidy CSV in `data/`, so each figure reflects exactly the deposited data. All
generated outputs are written to `figures/`.

| Manuscript figure | Script | Input CSV | Outputs in `figures/` |
| --- | --- | --- | --- |
| Figures 1 and 2 | `make_figures_1_2_detections.py` | `data/cartridges_long.csv` | `figure1_detections_interactive.html`, `figure1_detections_static.{png,pdf}`, `figure2_houston_interactive.html`, `figure2_houston.{png,pdf}` |
| Figure 3 | `make_figure_3_sequencing.py` | `data/sequencing_detections.csv` | `figure3_sequencing.html`, `figure3_sequencing.png`, `figure3_sequencing_transparent.png` |
| Online supplemental figure 1 | `make_supplement_1_wastewater.py` | `data/ww_canada.csv`, `data/ww_losangeles.csv`, `data/ww_losangeles.csv` | `supplement1_wastewater_interactive.html`, `supplement1_wastewater.{png,pdf}` |
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
```

Then append the **Data** and **Regenerating the dataset** sections from the
current `analysis/README.md` unchanged, except: correct the ww source list
typo above (the third entry is `data/ww_houston.csv`), and change the Data
section's heading level so it sits alongside Build.

- [ ] **Step 5: Update the figure skill for the new convention**

In `.claude/skills/manuscript-figure/SKILL.md`:
- Replace the trailing `## Numbering caution` section (which warned about the
  `make_figure3.py` name collision that no longer exists) with:

```markdown
## Naming convention

Script names state which manuscript figure they build:
`make_figures_1_2_detections.py`, `make_figure_3_sequencing.py`,
`make_supplement_1_wastewater.py`. A new figure gets
`make_figure_N_<slug>.py` or `make_supplement_N_<slug>.py`. All outputs are
written to `analysis/figures/`, never beside the scripts.
```

- Update the "Three outputs per figure" bullet and the "Embedding in index.qmd"
  code block to use `analysis/figures/` paths.
- Update the `figure_legends.md` references: legends now come from the Google
  Doc via `_legends/`, not a local file. Replace that bullet with: "Legend text
  is authored in the canonical Google Doc under `## Figure legends`;
  `scripts/fetch_prose.py` writes it to `_legends/<key>.md`, which `index.qmd`
  includes. Never hand-edit legend files."
- Update the "Build & commit" section to drop the PREVIEW.md reference.

- [ ] **Step 6: Confirm no dangling references remain**

```bash
grep -rn "make_figures\.py\|make_figure3\.py\|make_figure3_sequencing\.py\|figure3_wastewater\|figure1_static\|PREVIEW\|CITATION_SOURCE\|build_preview\|data-sharing-statement\|wastewater-comparison-notes" \
  --include="*.md" --include="*.qmd" --include="*.yml" --include="*.py" --include="*.toml" \
  . | grep -v "^./docs/superpowers/" || echo "clean"
```

Expected: `clean`. (The spec and plan under `docs/superpowers/` legitimately
name the old paths as history, so they are excluded.)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: rewrite READMEs for arriving readers; drop stale files"
```

---

### Task 8: Full-pipeline verification

The refactor is not done until both deliverables build and are inspected. Per
`superpowers:verification-before-completion`, every claim below must cite real
command output.

**Files:**
- Modify: none (verification only; fix-ups go back to the owning task)

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: the evidence that the three deliverables are correct.

- [ ] **Step 1: Clean-slate regeneration from the canonical Doc**

```bash
python scripts/fetch_prose.py
cd analysis && uv sync \
  && uv run python make_figures_1_2_detections.py \
  && uv run python make_figure_3_sequencing.py \
  && uv run python make_supplement_1_wastewater.py && cd ..
```

Expected: no errors; `wrote …_references.md (49 references)` appears.

- [ ] **Step 2: Run the test suite**

Run: `uv run --directory analysis --with pytest pytest ../tests -v`
Expected: 11 passed.

- [ ] **Step 3: Render the HTML site**

```bash
quarto render --to html
```

Expected: completes without error.

- [ ] **Step 4: Render the submission PDF**

```bash
python scripts/build_house_fonts.py
quarto render index.qmd --to pdf
ls -la _site/index.pdf
```

Expected: a PDF of non-trivial size (the current committed one is ~2 MB).

- [ ] **Step 5: Read the PDF back and confirm its contents**

Use the Read tool on `_site/index.pdf` and confirm, by looking at the pages:

1. The title page shows the Doc's title and the full author block including
   Isla E. Emmen and Nancy A. Wilson.
2. A **References** section exists, numbered 1 through 49, with entry 1 being
   Serner et al. and entry 49 the City of Houston dashboard.
3. An **Online supplemental methods** section with the "Community wastewater
   comparison" text appears before online supplemental figure 1.
4. All four figures render as images — no grey boxes, no "missing image"
   placeholders, no raw file paths.
5. No `[confirm]`-style placeholders remain in the Data sharing statement.

Any failure here goes back to the owning task; do not paper over it.

- [ ] **Step 6: Confirm the working tree is clean of strays**

```bash
git status --short
```

Expected: only `?? cover-letter-bjsm.md` (the user's untracked draft), and
nothing else untracked or modified.

- [ ] **Step 7: Commit the rebuilt PDF snapshot**

```bash
cp _site/index.pdf docs/team-canada-air-sampling.pdf
git add docs/team-canada-air-sampling.pdf analysis/figures/*.png _prose.md \
        _references.md _supplement.md _title.yml _frontmatter.md _legends
git commit -m "build: regenerate all outputs from the canonical Doc"
```

---

## Self-Review

**Spec coverage:**

| Spec item | Task |
|---|---|
| B1 references dropped | Task 2 |
| B2 supplemental methods dropped | Task 3 |
| B3 keywords hard-coded | Tasks 3, 4 |
| C1 legends hard-coded in build_preview | Task 7 (file deleted) |
| C2 authors hard-coded in build_preview | Task 7 (file deleted) |
| C3 stale data-sharing-statement | Task 7 |
| O1 script names lie | Task 5 |
| O2 analysis/README covers only Fig 1 | Task 7 |
| O3 outputs strewn, inconsistent tracking | Task 5 |
| O4 three parallel renderings | Task 7 |
| O5 stale files | Task 7 |
| Part 1 fetch_prose refactor | Task 2 step 6 (banner hoist), Tasks 2–3 |
| Part 6 verification | Task 8 |

**Type consistency:** `extract_references` returns `list[tuple[int, str]]`,
consumed only by `write_references`. `extract_supplement` and
`extract_keywords` return `str` and `list[str]`, consumed by
`write_supplement` and `write_title`. `BANNER`, `FIGURES`, `REFERENCES`, and
`SUPPLEMENT` are each defined once and referenced consistently.

**Placeholder scan:** No TBD/TODO. Every code step carries real code; every
verification step carries a real command and its expected output.
