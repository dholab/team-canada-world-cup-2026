"""Build Figure 3 (interactive + static) for the Team Canada air-sampling study.

Figure 3 is the metagenomic-sequencing confirmation of the Houston GeneXpert
episode. EsViritu viral read classification of the six Houston air cartridges
that were pulled for sequencing, shown as a virus x room heatmap of distinct
(deduplicated) read counts.

  * figure3_sequencing.html - interactive Plotly heatmap. Hovering a cell reports
                              the virus, room, sampler, distinct read count, total
                              mapped reads, sampling window, and elapsed duration.
                              Self-contained (Plotly from CDN). Embed in the site.
  * figure3_sequencing.png  - static raster (matplotlib, 300 dpi) for the PDF.

Both read the committed tidy CSV data/sequencing_detections.csv (one row per
room x detected virus), so the figure always reflects the deposited data.

Run:  uv run python make_figure3_sequencing.py
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
DATA = HERE / "data" / "sequencing_detections.csv"

# House palette (shared with the manuscript template).
TEAL = "#163139"
TERRA = "#C16A3C"
CREAM = "#F8F4E9"
RULE = "#dcd3c2"

# Column order: rooms left to right, grouped meal / physio / hallway / equipment.
ROOM_ORDER = ["Meal room 1", "Meal room 2", "Physio room 1", "Physio room 2",
              "Hallway", "Equipment room"]

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
    return df


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

    # SARS-CoV-2 was tested in every room; tested-but-absent cells read 0.
    tested_zero = {"SARS-CoV-2"}

    z, text, custom = [], [], []
    for v in viruses:
        zr, tr, cr = [], [], []
        for r in rooms:
            u = uniq[(v, r)]
            if present[(v, r)]:
                zr.append(bucket(u))
                tr.append(str(u))
            elif v in tested_zero:
                zr.append(None)
                tr.append("0")
            else:
                zr.append(None)
                tr.append("")
            h = hdr.get(r, {})
            cr.append([v, r, h.get("sampler", ""), u, total[(v, r)],
                       h.get("start", ""), h.get("elapsed", "")])
        z.append(zr)
        text.append(tr)
        custom.append(cr)

    # Natural order (Merkel first); yaxis autorange="reversed" puts it on top.
    colorscale = [[i / (len(BLUES) - 1), c] for i, c in enumerate(BLUES)]

    xlabels = [f"<b>{r}</b>" for r in rooms]

    fig = go.Figure(go.Heatmap(
        z=z, x=xlabels, y=viruses,
        text=text, texttemplate="%{text}", textfont=dict(size=13, color=TEAL),
        customdata=custom,
        colorscale=colorscale, zmin=0, zmax=5, showscale=False,
        xgap=3, ygap=3,
        hovertemplate=(
            "<b>%{customdata[0]}</b> in <b>%{customdata[1]}</b><br>"
            "Sampler %{customdata[2]}<br>"
            "Distinct reads %{customdata[3]}  (total mapped %{customdata[4]})<br>"
            "Start %{customdata[5]}  &#183;  elapsed %{customdata[6]}"
            "<extra></extra>"),
        hoverlabel=dict(bgcolor="white", bordercolor=RULE,
                        font=dict(family="Arial", size=12, color=TEAL)),
    ))

    # room sub-labels (sampler + sc2 + start + elapsed) as x annotations
    ann = []
    for i, r in enumerate(rooms):
        h = hdr.get(r, {})
        sub = f"<i>{h.get('sampler','')}</i>"
        sc2 = h.get("sc2", "")
        if sc2:
            sub += f"  {sc2}"
        sub += f"<br>{h.get('start','')}  &#916;{h.get('elapsed','')}"
        ann.append(dict(x=i, y=1.045, xref="x", yref="paper", showarrow=False,
                        text=sub, font=dict(family="Arial", size=10, color=TERRA),
                        xanchor="center", yanchor="bottom"))

    fig.update_layout(
        title=dict(
            text="<b>Figure 3</b>  Human viruses detected by sequencing of Houston air samples",
            font=dict(family="Georgia, serif", size=19, color=TEAL),
            x=0.0, xanchor="left", y=0.98),
        paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        font=dict(family="Arial", color=TEAL),
        width=940, height=560,
        margin=dict(l=210, r=40, t=140, b=40),
        xaxis=dict(side="top", tickfont=dict(family="Arial", size=11, color=TEAL),
                   showgrid=False, zeroline=False, ticks=""),
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
                 transparent: bool = False) -> None:
    rooms = [r for r in ROOM_ORDER if r in df["room"].unique()]
    viruses = virus_order(df)
    hdr = room_headers(df)

    uniq = {(v, r): None for v in viruses for r in rooms}
    for row in df.itertuples():
        if row.room in rooms and row.virus in viruses:
            uniq[(row.virus, row.room)] = (uniq[(row.virus, row.room)] or 0) + row.unique_reads
    for r in rooms:  # SARS tested everywhere -> explicit 0
        if uniq[("SARS-CoV-2", r)] is None:
            uniq[("SARS-CoV-2", r)] = 0

    cmap = mcolors.LinearSegmentedColormap.from_list("blues6", BLUES)
    norm = mcolors.BoundaryNorm([0, 2, 5, 10, 25, 100, 10_000], cmap.N)

    nrow, ncol = len(viruses), len(rooms)
    fig, ax = plt.subplots(figsize=(0.95 * ncol + 3.4, 0.42 * nrow + 2.2))

    for i, v in enumerate(viruses):
        for j, r in enumerate(rooms):
            u = uniq[(v, r)]
            y = nrow - 1 - i
            if u is None:
                ax.add_patch(plt.Rectangle((j, y), 0.92, 0.92, facecolor="#efe8da",
                                           edgecolor=CREAM, linewidth=2, zorder=1))
                continue
            fc = cmap(norm(u))
            ax.add_patch(plt.Rectangle((j, y), 0.92, 0.92, facecolor=fc,
                                       edgecolor=CREAM, linewidth=2, zorder=2))
            b = bucket(u)
            tc = "#FFFFFF" if b >= 3 else "#042C53"
            ax.text(j + 0.46, y + 0.46, str(u), ha="center", va="center",
                    fontsize=10, color=tc, family="Arial", zorder=3)

    ax.set_xlim(-0.05, ncol)
    ax.set_ylim(-1.2, nrow + 0.85)
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
    for j, r in enumerate(rooms):
        h = hdr.get(r, {})
        ax.text(j + 0.46, nrow + 0.60, r.upper(), ha="center", va="bottom",
                fontsize=8.5, family="Arial", color=TEAL, fontweight="bold")
        sc2 = h.get("sc2", "")
        sub = h.get("sampler", "")
        line2 = f"{h.get('start','')}  Δ{h.get('elapsed','')}"
        ax.text(j + 0.46, nrow + 0.44, sub + ("  " + sc2 if sc2 else ""),
                ha="center", va="bottom", fontsize=7.2, family="Arial",
                color=TERRA, style="italic")
        ax.text(j + 0.46, nrow + 0.14, line2, ha="center", va="bottom",
                fontsize=7, family="Arial", color=TEAL)

    # legend strip beneath the grid: blue ramp + not-detected swatch
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
    nd_x = ramp_x0 + len(BLUES) * 0.34 + 2.6
    ax.add_patch(plt.Rectangle((nd_x, ramp_y), 0.34, 0.30, facecolor="#efe8da",
                               edgecolor="none", clip_on=False, zorder=3))
    ax.text(nd_x + 0.44, ramp_y + 0.15, "virus not detected in this room",
            ha="left", va="center", fontsize=7, family="Arial", color=TEAL)

    face = "none" if transparent else CREAM
    fig.patch.set_facecolor(face if not transparent else "none")
    ax.set_facecolor("none")
    fig.savefig(out_png, dpi=300, bbox_inches="tight", transparent=transparent,
                facecolor=(None if transparent else CREAM))
    print(f"wrote {out_png}" + (" (transparent)" if transparent else ""))


def main() -> None:
    df = load()
    build_interactive(df, HERE / "figure3_sequencing.html")
    build_static(df, HERE / "figure3_sequencing.png")
    build_static(df, HERE / "figure3_sequencing_transparent.png", transparent=True)


if __name__ == "__main__":
    main()
