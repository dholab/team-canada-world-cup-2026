"""Build the interactive and static Figure 1 for the Team Canada air-sampling study.

Both figures use *real time*: sampling gaps are shown, not collapsed.

  * figure1_interactive.html  - every cartridge is drawn as a horizontal bar
                                spanning its actual start->end sampling window,
                                per room, per city (host-city selector). Hovering
                                a bar shows the room, exact window, duration,
                                virus results, Ct values, and GeneXpert calls.
  * figure1_static.pdf / .png - rooms merged within each city on a continuous
                                real-time axis, so travel gaps and within-city
                                gaps appear as blank space. Detections are drawn
                                at the interval midpoint, filled by the lowest Ct.

Run:  uv run python make_figures.py
"""

from __future__ import annotations

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data" / "cartridges_long.csv"

CITY_ORDER = ["Montreal", "Toronto", "Vancouver", "Los Angeles", "Houston"]
VIRUS_ORDER = ["SARS-CoV-2", "Influenza A", "Influenza B", "RSV"]
ROOM_ORDER = ["Physio room", "Meal room", "Equipment/Kit room",
              "Coaches room", "Hallway/Lounge"]
CT_MIN, CT_MAX = 34.0, 46.0
NEG_COLOR = "#ffffff"     # sampled, valid, virus not detected -> white
NEG_EDGE = "#c8c8c8"      # thin outline so white boxes read against white bg
INVALID_COLOR = "#bdbdbd"  # invalid run (SPC not positive) -> grey
GRID = "#f2f2f2"

# Ct colour scale: light blue (high Ct = little virus) -> deep blue (low Ct).
# Reversed so LOW Ct maps to the DEEP end.
CT_CMAP = matplotlib.colors.LinearSegmentedColormap.from_list(
    "ct_blues", ["#08306b", "#4292c6", "#c6dbef", "#f2f8fd"])  # low Ct -> high Ct
CT_NORM = matplotlib.colors.Normalize(CT_MIN, CT_MAX)


def ct_hex(ct: float) -> str:
    return matplotlib.colors.to_hex(CT_CMAP(CT_NORM(ct)))


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    # The dataset also records cartridges that produced no valid test data
    # (status "no_valid_data", blank virus). Those are for the data table only;
    # the figures show the four respiratory targets on tested cartridges.
    df = df[df["virus"].notna() & (df["virus"].astype(str).str.strip() != "")]
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["mid"] = df["start"] + (df["end"] - df["start"]) / 2
    df["ct"] = pd.to_numeric(df["ct"], errors="coerce")
    df["city"] = pd.Categorical(df["city"], CITY_ORDER, ordered=True)
    df["virus"] = pd.Categorical(df["virus"], VIRUS_ORDER, ordered=True)
    return df


# --------------------------------------------------------------------------- #
# Interactive: one bar per cartridge = its real start->end sampling interval    #
# --------------------------------------------------------------------------- #
def build_interactive(df: pd.DataFrame, out: pathlib.Path) -> None:
    # collapse the four virus rows to one row per cartridge; carry the detection
    # summary and the strongest Ct so each interval is one bar per room.
    cart = (df.sort_values(["cartridge", "virus"])
              .groupby(["city", "room", "sampler", "cartridge", "start", "end"],
                       observed=True)
              .apply(lambda g: pd.Series({
                  "dur_h": g["dur_h"].iloc[0],
                  "spc": g["spc"].iloc[0],
                  "n_det": int(g["detected"].sum()),
                  "min_ct": g.loc[g["detected"] == 1, "ct"].min()
                            if g["detected"].sum() else np.nan,
                  "results": "<br>".join(
                      f"{r.virus}: " + (f"Ct {r.ct:.1f} ({r.qual})"
                                        if r.detected else "not detected")
                      for r in g.itertuples()),
              }), include_groups=False)
              .reset_index())

    fig = go.Figure()
    city_traces: dict[str, list[int]] = {}

    for ci, city in enumerate(CITY_ORDER):
        sub = cart[cart["city"] == city]
        if sub.empty:
            continue
        rooms = [r for r in ROOM_ORDER if r in sub["room"].unique()]
        ypos = {room: i for i, room in enumerate(rooms)}

        idxs = []
        # split into: detections, valid negatives (white), invalid runs (grey)
        is_invalid = sub["spc"].astype(str).str.strip().str.lower().ne("positive")
        det = sub[sub["n_det"] > 0]
        neg = sub[(sub["n_det"] == 0) & (~is_invalid)]
        inv = sub[(sub["n_det"] == 0) & (is_invalid)]

        # blue Ct scale (low Ct = deep blue), matching the static figure
        ct_scale = [[0.0, "#08306b"], [0.33, "#4292c6"],
                    [0.66, "#c6dbef"], [1.0, "#f2f8fd"]]

        for grp, kind in ((det, "det"), (neg, "neg"), (inv, "inv")):
            if grp.empty:
                fig.add_trace(go.Bar(x=[], y=[], visible=(ci == 0),
                                     showlegend=False))
                idxs.append(len(fig.data) - 1)
                continue
            base = grp["start"]
            width_ms = (grp["end"] - grp["start"]).dt.total_seconds() * 1000
            yy = grp["room"].map(ypos)
            if kind == "det":
                marker = dict(color=grp["min_ct"], colorscale=ct_scale,
                              cmin=CT_MIN, cmax=CT_MAX,
                              line=dict(color="white", width=1),
                              colorbar=dict(title="Ct<br>(lower=<br>more virus)",
                                            x=1.02, len=0.55))
            elif kind == "neg":
                marker = dict(color="#ffffff",
                              line=dict(color="#c8c8c8", width=0.6))
            else:  # invalid
                marker = dict(color=INVALID_COLOR,
                              line=dict(color="white", width=0.5))
            custom = np.stack([
                grp["room"], grp["sampler"],
                grp["start"].dt.strftime("%d %b %H:%M"),
                grp["end"].dt.strftime("%d %b %H:%M"),
                grp["dur_h"].astype(str), grp["results"], grp["spc"]], axis=-1)
            fig.add_trace(go.Bar(
                base=base, x=width_ms, y=yy, orientation="h",
                width=0.7, marker=marker, visible=(ci == 0), showlegend=False,
                customdata=custom,
                hovertemplate=(
                    "<b>%{customdata[0]}</b>  (sampler %{customdata[1]})<br>"
                    "%{customdata[2]} &#8594; %{customdata[3]}"
                    "  (%{customdata[4]} h)<br>%{customdata[5]}"
                    "<br><i>SPC: %{customdata[6]}</i><extra></extra>"),
            ))
            idxs.append(len(fig.data) - 1)
        city_traces[city] = idxs

    # dropdown: pick host city, updating visibility + y ticks + x range + title
    buttons = []
    for city in CITY_ORDER:
        if city not in city_traces:
            continue
        vis = [False] * len(fig.data)
        for k in city_traces[city]:
            vis[k] = True
        sub = cart[cart["city"] == city]
        rooms = [r for r in ROOM_ORDER if r in sub["room"].unique()]
        xr = [sub["start"].min() - pd.Timedelta(hours=6),
              sub["end"].max() + pd.Timedelta(hours=6)]
        buttons.append(dict(
            label=city, method="update",
            args=[{"visible": vis},
                  {"title": f"Sampling intervals and detections — {city}",
                   "yaxis": {"tickmode": "array",
                             "tickvals": list(range(len(rooms))),
                             "ticktext": rooms, "autorange": "reversed"},
                   "xaxis": {"range": [xr[0], xr[1]], "type": "date"}}]))

    first = CITY_ORDER[0]
    s0 = cart[cart["city"] == first]
    rooms0 = [r for r in ROOM_ORDER if r in s0["room"].unique()]
    fig.update_layout(
        title=f"Sampling intervals and detections — {first}",
        template="simple_white", height=440, width=940,
        barmode="overlay", bargap=0.35,
        margin=dict(l=150, r=120, t=90, b=50),
        yaxis=dict(tickmode="array", tickvals=list(range(len(rooms0))),
                   ticktext=rooms0, autorange="reversed", showgrid=False),
        xaxis=dict(type="date", showgrid=True, gridcolor=GRID,
                   range=[s0["start"].min() - pd.Timedelta(hours=6),
                          s0["end"].max() + pd.Timedelta(hours=6)]),
        updatemenus=[dict(buttons=buttons, direction="down", showactive=True,
                          x=0.0, xanchor="left", y=1.18, yanchor="top")],
        annotations=[dict(text="Host city:", x=-0.16, y=1.18, xref="paper",
                          yref="paper", showarrow=False, xanchor="left",
                          font=dict(size=12))])
    fig.write_html(out, include_plotlyjs="cdn", full_html=True)
    print(f"wrote {out}")


# --------------------------------------------------------------------------- #
# Static: rooms merged, continuous real-time axis so gaps are visible          #
# --------------------------------------------------------------------------- #
def _draw_box(ax, r, y_center, row_h):
    """Draw one cartridge x virus rectangle. Identical geometry/stroke for every
    category so negatives, invalids, and detections are the same size and edge;
    only the fill differs."""
    x0 = mdates.date2num(r.start)
    w = mdates.date2num(r.end) - x0
    invalid = str(r.spc).strip().lower() != "positive"
    if r.detected:
        fc = ct_hex(r.ct)
    elif invalid:
        fc = INVALID_COLOR
    else:
        fc = NEG_COLOR
    ax.add_patch(plt.Rectangle(
        (x0, y_center - row_h / 2), w, row_h,
        facecolor=fc, edgecolor=NEG_EDGE, linewidth=0.5, zorder=2))


def _assign_sessions(df: pd.DataFrame, gap_h: float = 1.5) -> pd.DataFrame:
    """Assign a session id per city. A session is a cluster of cartridges whose
    start times are close together (the four rooms are started within minutes of
    each other); a new session begins when the gap to the previous start exceeds
    gap_h hours. This keeps each real sampling interval separate instead of
    collapsing the daytime and overnight runs into one daily box."""
    df = df.sort_values(["city", "start"]).copy()
    sess = {}
    for city, g in df.groupby("city", observed=True):
        starts = g.drop_duplicates("cartridge")[["cartridge", "start"]] \
                  .sort_values("start")
        sid = 0
        prev = None
        for c, s in zip(starts["cartridge"], starts["start"]):
            if prev is not None and (s - prev) > pd.Timedelta(hours=gap_h):
                sid += 1
            sess[c] = f"{city}#{sid}"
            prev = s
    df["session"] = df["cartridge"].map(sess)
    return df


def _merge_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Merge rooms for Figure 1, one cell per city x session x virus, so every
    actual sampling interval is shown separately. Precedence within a cell: any
    detection wins (fill = lowest Ct across rooms); else a valid negative in any
    room makes the cell a valid negative (white); only if every room that session
    was invalid is the cell invalid (grey). The cell's time span is the union of
    the contributing rooms' windows."""
    df = _assign_sessions(df)
    df["invalid"] = df["spc"].astype(str).str.strip().str.lower().ne("positive")

    rows = []
    for (city, session, virus), g in df.groupby(["city", "session", "virus"],
                                                observed=True):
        n_det = int(g["detected"].sum())
        n_validneg = int(((g["detected"] == 0) & (~g["invalid"])).sum())
        if n_det > 0:
            status, ct = "det", g.loc[g["detected"] == 1, "ct"].min()
        elif n_validneg > 0:
            status, ct = "neg", float("nan")
        else:
            status, ct = "inv", float("nan")
        rows.append(dict(city=city, virus=virus, start=g["start"].min(),
                         end=g["end"].max(), status=status, ct=ct))
    return pd.DataFrame(rows)


def build_static(df: pd.DataFrame, out_pdf: pathlib.Path, out_png: pathlib.Path) -> None:
    # ALL cities on ONE continuous local-time axis, so every gap - within a city
    # and between cities (travel days) - is drawn to true elapsed-time scale.
    # Rooms are MERGED: one box per city x session-day x virus (see _merge_cells
    # for the detection > valid-negative > invalid precedence).
    cities = [c for c in CITY_ORDER if c in df["city"].unique()]
    yorder = list(reversed(VIRUS_ORDER))
    ypos = {v: i for i, v in enumerate(yorder)}
    ROW_H = 0.86

    t0 = df["start"].min() - pd.Timedelta(hours=12)
    t1 = df["end"].max() + pd.Timedelta(hours=12)

    fig, ax = plt.subplots(figsize=(13, 3.1))
    ax.set_xlim(mdates.date2num(t0), mdates.date2num(t1))
    ax.set_ylim(-0.6, len(yorder) - 0.4)

    # One box per session x virus. Every box carries the same thin light-grey
    # border so individual sampling intervals stay visible. Valid negatives are
    # white; detections are filled by Ct and invalids grey, and sit on top.
    cells = _merge_cells(df)
    for r in cells[cells.status == "neg"].itertuples():
        x0 = mdates.date2num(r.start)
        ax.add_patch(plt.Rectangle(
            (x0, ypos[r.virus] - ROW_H / 2), mdates.date2num(r.end) - x0, ROW_H,
            facecolor=NEG_COLOR, edgecolor=NEG_EDGE, linewidth=0.4, zorder=1))
    for r in cells[cells.status != "neg"].itertuples():
        x0 = mdates.date2num(r.start)
        fc = ct_hex(r.ct) if r.status == "det" else INVALID_COLOR
        ax.add_patch(plt.Rectangle(
            (x0, ypos[r.virus] - ROW_H / 2), mdates.date2num(r.end) - x0, ROW_H,
            facecolor=fc, edgecolor=NEG_EDGE, linewidth=0.5, zorder=3))

    # asterisk beneath each cartridge that had an invalid run (SPC did not
    # amplify), placed at the run's real time on the axis. These sessions still
    # have valid negative results in other rooms, so their cells are not grey;
    # the asterisk flags that one or more rooms could not be evaluated.
    inv_carts = (df[df["spc"].astype(str).str.strip().str.lower().ne("positive")]
                 .drop_duplicates("cartridge"))
    for r in inv_carts.itertuples():
        cmid = r.start + (r.end - r.start) / 2
        ax.annotate("*", xy=(mdates.date2num(cmid), 0),
                    xycoords=("data", "axes fraction"),
                    xytext=(0, -32), textcoords="offset points",
                    ha="center", va="top", fontsize=12, fontweight="bold",
                    color="#666666", annotation_clip=False)

    # city labels + faint dividers at the midpoint of each city's travel gap
    per_cart = (df.groupby("cartridge", observed=True)
                  .agg(city=("city", "first"), start=("start", "first"),
                       end=("end", "first")).reset_index())
    spans = {c: (per_cart[per_cart.city == c]["start"].min(),
                 per_cart[per_cart.city == c]["end"].max()) for c in cities}
    for i, c in enumerate(cities):
        cmid = spans[c][0] + (spans[c][1] - spans[c][0]) / 2
        ax.text(mdates.date2num(cmid), len(yorder) - 0.25, c,
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for lab in ax.get_xticklabels():
        lab.set(rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(yorder)))
    ax.set_yticklabels(yorder, fontsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)

    sm = matplotlib.cm.ScalarMappable(cmap=CT_CMAP, norm=CT_NORM)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.012, pad=0.01, shrink=0.7)
    cbar.set_label("Ct value (lower = more virus)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    fig.subplots_adjust(bottom=0.26)
    handles = [plt.Rectangle((0, 0), 1, 1, fc=NEG_COLOR, ec=NEG_EDGE, lw=0.5)]
    fig.legend(handles,
               ["Sampled, no viral genetic material detected        "
                "*  one or more rooms invalid this session (SPC did not amplify)"],
               loc="lower center", ncol=1, frameon=False, fontsize=7.5,
               bbox_to_anchor=(0.5, -0.02))

    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    print(f"wrote {out_pdf} and {out_png}")


# --------------------------------------------------------------------------- #
# Figure 2 (static): the Houston multi-room episode, per room                   #
# --------------------------------------------------------------------------- #
def build_figure2(df: pd.DataFrame, city: str,
                  out_pdf: pathlib.Path, out_png: pathlib.Path) -> None:
    sub = df[df.city == city].copy()
    rooms = [r for r in ROOM_ORDER if r in sub["room"].unique()]
    # y = room x virus (four virus sub-rows per room), grouped by room with a
    # blank gap between room blocks so the groups read as distinct.
    ROOM_GAP = 1.2                 # extra blank rows between room blocks
    n_v = len(VIRUS_ORDER)
    # Assign a y-coordinate to each (room, virus). Rooms stack top-to-bottom, so
    # the first room gets the highest y-values.
    ypos, yticks, yticklabels = {}, [], []
    room_span = {}
    n_rooms = len(rooms)
    slot = 0.0
    for room in rooms:
        block_positions = []
        for v in VIRUS_ORDER:
            block_positions.append(slot)
            slot += 1.0
        # invert so the first virus sits at the top of its block
        top_slot = block_positions[0]
        bot_slot = block_positions[-1]
        for v, s in zip(VIRUS_ORDER, block_positions):
            ypos[(room, v)] = s
            yticks.append(s)
            yticklabels.append(v)
        room_span[room] = (top_slot, bot_slot)
        slot += ROOM_GAP
    total = slot - ROOM_GAP
    # flip vertically so first room is on top
    def flip(y):
        return total - y
    ypos = {k: flip(v) for k, v in ypos.items()}
    yticks = [flip(t) for t in yticks]
    room_span = {r: (flip(a), flip(b)) for r, (a, b) in room_span.items()}

    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(rooms) * n_v + 1.2))
    c0, c1 = sub["start"].min(), sub["end"].max()
    pad = pd.Timedelta(hours=4)
    ax.set_xlim(mdates.date2num(c0 - pad), mdates.date2num(c1 + pad))
    ROW_H = 0.82

    for r in sub.itertuples():
        yk = (r.room, r.virus)
        if yk not in ypos:
            continue
        _draw_box(ax, r, ypos[yk], ROW_H)

    # y tick labels: virus name per sub-row, bold room label centred on the block
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels, fontsize=8)
    for room in rooms:
        a, b = room_span[room]
        ymid = (a + b) / 2
        ax.text(-0.135, ymid, room, transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=9, fontweight="bold")

    ax.set_ylim(min(ypos.values()) - 0.7, max(ypos.values()) + 0.7)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for lab in ax.get_xticklabels():
        lab.set(rotation=45, ha="right", fontsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(f"{city} respiratory-virus detections by room", fontsize=11,
                 fontweight="bold")

    sm = matplotlib.cm.ScalarMappable(cmap=CT_CMAP, norm=CT_NORM)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Ct value (lower = more virus)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    handles = [
        plt.Rectangle((0, 0), 1, 1, fc=NEG_COLOR, ec=NEG_EDGE, lw=0.5),
        plt.Rectangle((0, 0), 1, 1, fc=INVALID_COLOR, ec=NEG_EDGE, lw=0.5)]
    fig.legend(handles, ["Sampled, not detected", "Invalid run (SPC−)"],
               loc="lower center", ncol=2, frameon=False, fontsize=7.5,
               bbox_to_anchor=(0.5, -0.04))

    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    print(f"wrote {out_pdf} and {out_png}")


def build_figure2_interactive(df: pd.DataFrame, city: str, out: pathlib.Path) -> None:
    sub = df[df.city == city].copy()
    rooms = [r for r in ROOM_ORDER if r in sub["room"].unique()]
    # y rows = room x virus, grouped by room (four virus rows per room)
    ycats = [f"{room}  |  {v}" for room in rooms for v in VIRUS_ORDER]
    yindex = {lab: k for k, lab in enumerate(ycats)}
    sub["ylab"] = sub["room"] + "  |  " + sub["virus"].astype(str)
    sub["yy"] = sub["ylab"].map(yindex)
    sub["invalid"] = sub["spc"].astype(str).str.strip().str.lower().ne("positive")

    ct_scale = [[0.0, "#08306b"], [0.33, "#4292c6"],
                [0.66, "#c6dbef"], [1.0, "#f2f8fd"]]
    fig = go.Figure()

    def add(grp, kind):
        if grp.empty:
            return
        base = grp["start"]
        width_ms = (grp["end"] - grp["start"]).dt.total_seconds() * 1000
        if kind == "det":
            marker = dict(color=grp["ct"], colorscale=ct_scale,
                          cmin=CT_MIN, cmax=CT_MAX,
                          line=dict(color="#c8c8c8", width=0.6),
                          colorbar=dict(title="Ct<br>(lower=<br>more virus)",
                                        x=1.02, len=0.55))
            res = [f"Ct {c:.1f} ({q})" for c, q in zip(grp["ct"], grp["qual"])]
        elif kind == "inv":
            marker = dict(color=INVALID_COLOR, line=dict(color="#c8c8c8", width=0.6))
            res = ["invalid run"] * len(grp)
        else:
            marker = dict(color="#ffffff", line=dict(color="#c8c8c8", width=0.6))
            res = ["not detected"] * len(grp)
        custom = np.stack([
            grp["room"], grp["virus"].astype(str),
            grp["start"].dt.strftime("%d %b %H:%M"),
            grp["end"].dt.strftime("%d %b %H:%M"),
            grp["dur_h"].astype(str), res, grp["spc"]], axis=-1)
        fig.add_trace(go.Bar(
            base=base, x=width_ms, y=grp["yy"], orientation="h", width=0.72,
            marker=marker, showlegend=False, customdata=custom,
            hovertemplate=(
                "<b>%{customdata[0]} &#124; %{customdata[1]}</b><br>"
                "%{customdata[2]} &#8594; %{customdata[3]} (%{customdata[4]} h)<br>"
                "%{customdata[5]}<br><i>SPC %{customdata[6]}</i><extra></extra>")))

    add(sub[sub.detected == 1], "det")
    add(sub[(sub.detected == 0) & (~sub.invalid)], "neg")
    add(sub[(sub.detected == 0) & (sub.invalid)], "inv")

    fig.update_layout(
        title=f"{city} respiratory-virus detections by room",
        template="simple_white", height=26 * len(ycats) + 140, width=900,
        barmode="overlay", bargap=0.3,
        margin=dict(l=200, r=120, t=70, b=50),
        yaxis=dict(tickmode="array", tickvals=list(range(len(ycats))),
                   ticktext=ycats, autorange="reversed", showgrid=False),
        xaxis=dict(type="date", showgrid=True, gridcolor=GRID))
    fig.write_html(out, include_plotlyjs="cdn", full_html=True)
    print(f"wrote {out}")


def main() -> None:
    df = load()
    build_interactive(df, HERE / "figure1_interactive.html")
    build_static(df, HERE / "figure1_static.pdf", HERE / "figure1_static.png")
    build_figure2(df, "Houston",
                  HERE / "figure2_houston.pdf", HERE / "figure2_houston.png")
    build_figure2_interactive(df, "Houston", HERE / "figure2_houston_interactive.html")

    # Figure 3: community wastewater context per host city (own module; reads the
    # committed per-city extracts in data/ww_*.csv).
    import make_figure3
    make_figure3.main()


if __name__ == "__main__":
    main()
