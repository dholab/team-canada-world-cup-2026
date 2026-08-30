"""Build Figure 3 (interactive + static) for the Team Canada air-sampling study.

Figure 3 is the metagenomic-sequencing confirmation of the Houston GeneXpert
episode: EsViritu viral read classification shown as a virus x room heatmap of
distinct (deduplicated) read counts.

Six Houston cartridges were sequenced, but the figure shows only the four from
the samplers that ran the four-plex respiratory panel (see FOURPLEX_SAMPLERS).
Six columns against the four samplers described elsewhere in the manuscript
would be confusing; all six samples remain in data/sequencing_detections.csv.

  * figure3_sequencing.html - interactive Plotly heatmap. Hovering a cell reports
                              the virus, room, sampler, distinct read count, total
                              mapped reads, sampling window, and elapsed duration.
                              Self-contained (Plotly from CDN). Embed in the site.
  * figure3_sequencing.png  - static raster (matplotlib, 300 dpi) for the PDF.
  * figure3_sequencing_transparent.png - same static raster with a transparent
                              background (Keynote-ready).

Both read the committed tidy CSV data/sequencing_detections.csv (one row per
room x detected virus), so the figure always reflects the deposited data.

Run:  uv run python make_figure_3_sequencing.py
"""

from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = pathlib.Path(__file__).parent
# All generated figure outputs land in one directory so a reader can find every
# rendered figure without picking through the scripts that build them.
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)
DATA = HERE / "data" / "sequencing_detections.csv"

# House palette (shared with the manuscript template).
TEAL = "#163139"
TERRA = "#C16A3C"
CREAM = "#F8F4E9"
RULE = "#dcd3c2"

# Column order. Both the suffixed and un-suffixed forms are listed because
# load() strips a "1"/"2" index once only one cartridge from that room survives
# the four-plex filter.
ROOM_ORDER = ["Meal room", "Meal room 1", "Meal room 2",
              "Physio room", "Physio room 1", "Physio room 2",
              "Hallway", "Equipment room"]

# The four samplers that ran the four-plex respiratory panel throughout the
# study. Figure 3 shows only these, so its columns match the four samplers
# described everywhere else in the manuscript (see load()).
FOURPLEX_SAMPLERS = {"Jabeur", "Kerber", "Rybakina", "Sharpova"}

# Row order: Merkel and SARS-CoV-2 pinned on top, then by total distinct reads.
ROW_PIN = ["Merkel cell polyomavirus", "SARS-CoV-2"]

# Blue distinct-read scale (light -> deep). Deep = more distinct reads.
BLUES = ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5", "#0C447C"]


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA, dtype={"sc2_status": str})
    df["unique_reads"] = pd.to_numeric(df["unique_reads"], errors="coerce").fillna(0).astype(int)
    df["total_reads"] = pd.to_numeric(df["total_reads"], errors="coerce").fillna(0).astype(int)
    df["sc2_status"] = df["sc2_status"].fillna("").astype(str).str.strip()
    df.loc[df["sc2_status"].str.lower() == "nan", "sc2_status"] = ""

    # Six cartridges were sequenced, but two came from samplers outside the
    # four-plex respiratory series the rest of the manuscript describes:
    # "Sabalenka" (run predominantly for norovirus, excluded study-wide) and
    # "Barty" (not part of the respiratory series at all). Showing six columns
    # here against four samplers everywhere else is confusing, so the figure is
    # restricted to the four. The full six-sample table stays in
    # data/sequencing_detections.csv.
    kept = df[df["sampler"].isin(FOURPLEX_SAMPLERS)].copy()
    dropped = sorted(set(df["sampler"]) - set(kept["sampler"]))
    if dropped:
        print(f"  excluding non-four-plex sampler(s): {', '.join(dropped)}")

    # With the second meal and physio cartridges gone, the "1"/"2" suffixes that
    # distinguished them are misleading — there is no room 2 left to contrast
    # with. Drop the index wherever only one cartridge from that room remains.
    base = kept["room"].str.replace(r"\s+\d+$", "", regex=True)
    # How many distinct cartridges still share each un-suffixed room name.
    remaining = kept.assign(_base=base).groupby("_base")["room"].nunique()
    kept["room"] = [b if remaining[b] == 1 else r
                    for b, r in zip(base, kept["room"])]
    return kept


def virus_order(df: pd.DataFrame) -> list[str]:
    totals = df.groupby("virus")["unique_reads"].sum().sort_values(ascending=False)
    rest = [v for v in totals.index if v not in ROW_PIN]
    return ROW_PIN + rest


def bucket(v: int) -> int:
    if v >= 100:
        return 5
    if v >= 25:
        return 4
    if v >= 10:
        return 3
    if v >= 5:
        return 2
    if v >= 2:
        return 1
    return 0


def room_headers(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    """One header record per room: sampler, sc2 status, start, elapsed."""
    h = {}
    for room in ROOM_ORDER:
        sub = df[df["room"] == room]
        if sub.empty:
            continue
        r = sub.iloc[0]
        h[room] = dict(sampler=r["sampler"], sc2=str(r.get("sc2_status", "") or ""),
                       start=r["start"], elapsed=r["elapsed_hhmm"])
    return h


# --------------------------------------------------------------------------- #
# Interactive Plotly heatmap                                                    #
# --------------------------------------------------------------------------- #
def build_interactive(df: pd.DataFrame, out: pathlib.Path) -> None:
    rooms = [r for r in ROOM_ORDER if r in df["room"].unique()]
    viruses = virus_order(df)
    hdr = room_headers(df)

    # matrices indexed [virus][room]
    uniq = {(v, r): 0 for v in viruses for r in rooms}
    total = {(v, r): 0 for v in viruses for r in rooms}
    present = {(v, r): False for v in viruses for r in rooms}
    for row in df.itertuples():
        if row.room in rooms and row.virus in viruses:
            uniq[(row.virus, row.room)] += row.unique_reads
            total[(row.virus, row.room)] += row.total_reads
            present[(row.virus, row.room)] = True

    # cell_text collects per-cell labels with an explicit color so text on dark
    # cells is white and text on light cells is deep navy (readable on both).
    # Non-detection cells are left empty (no number, no fill) in every column,
    # including negative SARS-CoV-2 cells.
    DARK_TEXT = "#042C53"
    z, custom, cell_text = [], [], []
    for v in viruses:
        zr, cr = [], []
        for r in rooms:
            u = uniq[(v, r)]
            if present[(v, r)]:
                b = bucket(u)
                zr.append(b)
                label, tcolor = str(u), ("#FFFFFF" if b >= 3 else DARK_TEXT)
                cell_text.append(dict(x=rooms.index(r), y=v, text=label, tcolor=tcolor))
            else:
                zr.append(None)  # transparent cell, no label
            h = hdr.get(r, {})
            cr.append([v, r, u, total[(v, r)], h.get("start", ""), h.get("elapsed", "")])
        z.append(zr)
        custom.append(cr)

    # Natural order (Merkel first); yaxis autorange="reversed" puts it on top.
    colorscale = [[i / (len(BLUES) - 1), c] for i, c in enumerate(BLUES)]

    # x categories are plain indices; the full header is drawn as annotations
    # below so line spacing is controlled (avoids the cramped tick-label stack).
    xcats = list(range(len(rooms)))

    fig = go.Figure(go.Heatmap(
        z=z, x=xcats, y=viruses,
        customdata=custom,
        colorscale=colorscale, zmin=0, zmax=5, showscale=False,
        xgap=3, ygap=3,
        hovertemplate=(
            "<b>%{customdata[0]}</b> in <b>%{customdata[1]}</b><br>"
            "Distinct reads %{customdata[2]}  (total mapped %{customdata[3]})<br>"
            "Start %{customdata[4]}  &#183;  elapsed %{customdata[5]}"
            "<extra></extra>"),
        hoverlabel=dict(bgcolor="white", bordercolor=RULE,
                        font=dict(family="Arial", size=12, color=TEAL)),
    ))

    # Column headers as stacked annotations, one line per field with even
    # spacing: room name (bold teal), SC2 status, start time, elapsed. Sampler
    # names are intentionally omitted (internal-only). Each line is its own
    # annotation at a fixed paper-y so the rows align across every column.
    ann = []
    # per-cell number labels, colored for contrast (white on dark, navy on light)
    for c in cell_text:
        ann.append(dict(x=c["x"], y=c["y"], xref="x", yref="y", showarrow=False,
                        text=c["text"], font=dict(family="Arial", size=13,
                                                  color=c["tcolor"]),
                        xanchor="center", yanchor="middle"))

    # Header lines: room name (one or two), SC2 status, cartridge runtime.
    # Start/end clock times are omitted (they read as confusing); runtime alone
    # conveys how long each cartridge sampled.
    # Paper-space baselines for the stacked column header. The runtime line must
    # clear y=1.0 or it overprints the first heat-map row.
    LINE_Y = {"room1": 1.150, "room2": 1.105, "sc2": 1.062, "runtime": 1.020}
    for i, r in enumerate(rooms):
        h = hdr.get(r, {})
        words = r.upper().split(" ")
        # wrap room name to two balanced lines (e.g. "MEAL / ROOM 1")
        if len(words) >= 2:
            line1 = words[0]
            line2 = " ".join(words[1:])
        else:
            line1, line2 = r.upper(), ""
        ann.append(dict(x=i, y=LINE_Y["room1"], xref="x", yref="paper",
                        showarrow=False, text=f"<b>{line1}</b>",
                        font=dict(family="Arial", size=10, color=TEAL),
                        xanchor="center", yanchor="middle"))
        if line2:
            ann.append(dict(x=i, y=LINE_Y["room2"], xref="x", yref="paper",
                            showarrow=False, text=f"<b>{line2}</b>",
                            font=dict(family="Arial", size=10, color=TEAL),
                            xanchor="center", yanchor="middle"))
        # Always occupy the SC2 slot (blank when no same-room GeneXpert) so the
        # runtime line stays on one baseline across every column.
        sc2 = h.get("sc2", "")
        ann.append(dict(x=i, y=LINE_Y["sc2"], xref="x", yref="paper",
                        showarrow=False, text=(sc2 if sc2 else "&#160;"),
                        font=dict(family="Arial", size=10, color=TEAL),
                        xanchor="center", yanchor="middle"))
        # Runtime as the bare h:mm value. Repeating the word "runtime" in every
        # column collides once the figure scales to the page width; the row
        # label to the left names the unit once instead.
        ann.append(dict(x=i, y=LINE_Y["runtime"], xref="x", yref="paper",
                        showarrow=False, text=h.get("elapsed", ""),
                        font=dict(family="Arial", size=10, color=TERRA),
                        xanchor="center", yanchor="middle"))
    # One label for the runtime row, in the left margin.
    ann.append(dict(x=0, y=LINE_Y["runtime"], xref="paper", yref="paper",
                    showarrow=False, text="RUNTIME (h:mm)", xshift=-12,
                    font=dict(family="Arial", size=9, color=TERRA),
                    xanchor="right", yanchor="middle"))

    fig.update_layout(
        # No in-plot title: the legend beneath the figure carries "Figure 3. ...".
        paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        font=dict(family="Arial", color=TEAL),
        autosize=True, height=560,
        margin=dict(l=195, r=40, t=96, b=30),
        xaxis=dict(side="top", showticklabels=False,
                   showgrid=False, zeroline=False, ticks="",
                   range=[-0.5, len(rooms) - 0.5]),
        yaxis=dict(autorange="reversed", tickfont=dict(family="Arial", size=12, color=TEAL),
                   showgrid=False, zeroline=False, ticks=""),
        annotations=ann,
    )
    fig.write_html(out, include_plotlyjs="cdn", full_html=True,
                   config={"displayModeBar": False})
    print(f"wrote {out}")


# --------------------------------------------------------------------------- #
# Static matplotlib heatmap (300 dpi PNG)                                       #
# transparent=True gives a Keynote-ready alpha PNG; False gives cream.          #
# --------------------------------------------------------------------------- #
def build_static(df: pd.DataFrame, out_png: pathlib.Path, *,
                 transparent: bool = False, bg: str = CREAM) -> None:
    # bg is the background + cell-gap color for the opaque PNG (CREAM by default,
    # "#FFFFFF" for the manuscript/PDF version). Ignored when transparent=True.
    edge = bg
    rooms = [r for r in ROOM_ORDER if r in df["room"].unique()]
    viruses = virus_order(df)
    hdr = room_headers(df)

    uniq = {(v, r): None for v in viruses for r in rooms}
    for row in df.itertuples():
        if row.room in rooms and row.virus in viruses:
            uniq[(row.virus, row.room)] = (uniq[(row.virus, row.room)] or 0) + row.unique_reads

    cmap = mcolors.LinearSegmentedColormap.from_list("blues6", BLUES)
    norm = mcolors.BoundaryNorm([0, 2, 5, 10, 25, 100, 10_000], cmap.N)

    nrow, ncol = len(viruses), len(rooms)
    fig, ax = plt.subplots(figsize=(0.95 * ncol + 3.4, 0.42 * nrow + 2.2))

    for i, v in enumerate(viruses):
        for j, r in enumerate(rooms):
            u = uniq[(v, r)]
            y = nrow - 1 - i
            if u is None:
                continue  # no detection -> draw nothing (transparent / bg color)
            fc = cmap(norm(u))
            ax.add_patch(plt.Rectangle((j, y), 0.92, 0.92, facecolor=fc,
                                       edgecolor=edge, linewidth=2, zorder=2))
            b = bucket(u)
            tc = "#FFFFFF" if b >= 3 else "#042C53"
            ax.text(j + 0.46, y + 0.46, str(u), ha="center", va="center",
                    fontsize=10, color=tc, family="Arial", zorder=3)

    ax.set_xlim(-0.05, ncol)
    ax.set_ylim(-1.2, nrow + 0.9)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    # virus row labels (left)
    for i, v in enumerate(viruses):
        y = nrow - 1 - i
        weight = "bold" if v in ROW_PIN else "normal"
        ax.text(-0.15, y + 0.46, v, ha="right", va="center", fontsize=9.5,
                family="Arial", color=TEAL, fontweight=weight)

    # room headers (top): room bold + sampler/start/elapsed
    # Column headers: room name (bold) / SC2 status / cartridge runtime (h:mm).
    # Sampler names are intentionally omitted (internal-only). Extra gap above
    # the runtime line separates it from the SC2 status.
    for j, r in enumerate(rooms):
        h = hdr.get(r, {})
        ax.text(j + 0.46, nrow + 0.64, r.upper(), ha="center", va="bottom",
                fontsize=8.5, family="Arial", color=TEAL, fontweight="bold")
        sc2 = h.get("sc2", "")
        if sc2:
            ax.text(j + 0.46, nrow + 0.40, sc2, ha="center", va="bottom",
                    fontsize=7.2, family="Arial", color=TEAL)
        ax.text(j + 0.46, nrow + 0.10, f"{h.get('elapsed','')} runtime",
                ha="center", va="bottom", fontsize=7, family="Arial", color=TERRA)

    # legend strip beneath the grid: blue ramp, plus a note that blank = not
    # detected (blank cells no longer carry a fill to point at).
    ramp_y = -0.85
    ramp_x0 = 0.0
    for k, c in enumerate(BLUES):
        ax.add_patch(plt.Rectangle((ramp_x0 + k * 0.34, ramp_y), 0.34, 0.30,
                                   facecolor=c, edgecolor="none",
                                   clip_on=False, zorder=3))
    ax.text(ramp_x0, ramp_y - 0.12, "fewer", ha="left", va="top",
            fontsize=7, family="Arial", color=TEAL)
    ax.text(ramp_x0 + len(BLUES) * 0.34, ramp_y - 0.12, "more distinct reads",
            ha="left", va="top", fontsize=7, family="Arial", color=TEAL)
    note_x = ramp_x0 + len(BLUES) * 0.34 + 2.6
    ax.text(note_x, ramp_y + 0.15, "blank = virus not detected in this room",
            ha="left", va="center", fontsize=7, family="Arial", color=TEAL)

    fig.patch.set_facecolor("none" if transparent else bg)
    ax.set_facecolor("none")
    fig.savefig(out_png, dpi=300, bbox_inches="tight", transparent=transparent,
                facecolor=(None if transparent else bg))
    print(f"wrote {out_png}" + (" (transparent)" if transparent else f" (bg {bg})"))
    # Journals want vector art. The other figure scripts already emit a PDF
    # alongside the raster; do the same here so every main figure has a vector
    # master for submission. Skipped for the transparent variant, which exists
    # only for the web page.
    if not transparent:
        out_pdf = out_png.with_suffix(".pdf")
        fig.savefig(out_pdf, bbox_inches="tight", facecolor=bg)
        print(f"wrote {out_pdf}")


def main() -> None:
    df = load()
    build_interactive(df, FIGURES / "figure3_sequencing.html")
    # Manuscript / PDF version on a white background.
    build_static(df, FIGURES / "figure3_sequencing.png", bg="#FFFFFF")
    build_static(df, FIGURES / "figure3_sequencing_transparent.png",
                 transparent=True)


if __name__ == "__main__":
    main()
