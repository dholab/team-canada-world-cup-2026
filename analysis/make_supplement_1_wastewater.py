"""Build online supplemental figure 1 (static + interactive): community
wastewater context for each host city over the full 2025-2026 respiratory season.

This builds **online supplemental figure 1**, not Figure 3. Output filenames
use the `supplement1_wastewater` stem to match, per BJSM style.

The point of this figure is NOT to compare absolute virus levels between cities
-- the four public dashboards report incompatible quantities (see below) and
that comparison would be meaningless. The point is to show, *within each site's
own history*, that the levels during Team Canada's visit were not unusually high.
Each panel therefore plots one city on its own y-axis, in its own native metric,
with the team's sampling window shaded.

Sources and metrics (one per panel), all filtered to weeks on/after 2025-08-01:

  * Montreal, Toronto, Vancouver -- Public Health Agency of Canada wastewater
    aggregate (health-infobase). Quantity: a PMMoV-normalized viral index
    (dimensionless). Vancouver is reported as "Metro Vancouver". All four study
    targets (SARS-CoV-2 = covN2, influenza A, influenza B, RSV) are available.
  * Los Angeles -- California (CDPH / CDC NWSS) open data, Joint Water Pollution
    Control Plant (JWPCP, Carson), the plant serving the South Bay / Torrance
    where the team stayed. Quantity: target concentration (copies/L) divided by
    the reported human fecal marker concentration (hum_frac_mic_conc), x1e6, so
    it is self-normalized to fecal load. Influenza B was not reported at JWPCP
    this season.
  * Houston -- Rice University / Houston Health Department dashboard
    (spatialstudieslab ArcGIS), 69th Street plant, the sewershed serving the
    downtown / Main Street hotel. Quantity: the published viral-load index
    (vl_est; 100 = the July-2020 baseline). SARS-CoV-2 only at plant level. The
    public per-plant feed now covers the team's 30 Jun-4 Jul stay (weekly points
    of 11 for the week of 2026-06-29 and 7 for 2026-07-06, near the seasonal
    low), refreshed 2026-08-15 from the WWTP_gdb feature service
    (services.arcgis.com/lqRTrQp2HrfnJt8U, layer WWTP, field vl_est), which then
    extended through 2026-07-27.

Because each panel is on its own metric and scale, the y-axes are deliberately
independent and unlabelled with absolute numbers -- reading across panels
compares *shape and relative height within a site*, never absolute level.

Run:  uv run python make_supplement_1_wastewater.py
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
from plotly.subplots import make_subplots

HERE = pathlib.Path(__file__).parent
# All generated figure outputs land in one directory so a reader can find every
# rendered figure without picking through the scripts that build them.
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)
DATA = HERE / "data"

# Panel order A-E. Canada cities first (matching Figure 1's city order), then US.
PANELS = ["Montreal", "Toronto", "Vancouver", "Los Angeles", "Houston"]

# One colour per virus, used identically in every panel. The palette is tuned to
# sit with Figures 1-2, which are built on a deep-navy -> pale-blue Ct ramp
# (#08306b .. #4292c6). SARS-CoV-2 keeps that same navy so the primary virus
# reads consistently across all three figures; the other three are muted,
# colourblind-safe tones (an Okabe-Ito-derived set) chosen to harmonise rather
# than clash with the cool, desaturated look of the earlier figures.
VIRUS_LABEL = {"covN2": "SARS-CoV-2", "fluA": "Influenza A",
               "fluB": "Influenza B", "rsv": "RSV"}
VIRUS_ORDER = ["covN2", "fluA", "fluB", "rsv"]
VIRUS_COLOR = {"covN2": "#08306b",   # deep navy, matches the Fig 1-2 Ct ramp
               "fluA": "#c98a2b",    # muted ochre / goldenrod
               "fluB": "#9e4a5c",    # dusty wine
               "rsv": "#4c9a86"}     # soft teal-green

# House canvas. The interactive figure paints cream so it sits flush inside the
# cream page on the Quarto site; the static PNG/PDF exports keep matplotlib's
# white ground, which the submission PDF requires.
CREAM = "#F8F4E9"

# Team Canada sampling window per city (from cartridges_long.csv). The Houston
# 69th St feed now spans the visit window (refreshed 2026-08-15), so no gap
# caveat is needed.
VISIT = {
    "Montreal": ("2026-06-03", "2026-06-06"),
    "Toronto": ("2026-06-07", "2026-06-11"),
    "Vancouver": ("2026-06-14", "2026-06-24"),
    "Los Angeles": ("2026-06-27", "2026-06-28"),
    "Houston": ("2026-06-30", "2026-07-04"),
}

# Non-detect floor values in the Canadian aggregate (detection-limit
# substitutions); anything at/below these is plotted but flagged as non-detect.
CA_FLOOR = {"fluA": 0.0122287520131786, "fluB": 0.0087553658126273,
            "rsv": 0.0082133841834729}

SOURCE_FILES = {
    "Montreal": "ww_canada.csv", "Toronto": "ww_canada.csv",
    "Vancouver": "ww_canada.csv", "Los Angeles": "ww_losangeles.csv",
    "Houston": "ww_houston.csv",
}
METRIC_LABEL = {
    "pmmov_index": "PMMoV-normalized index",
    "fecal_normalized": "copies/L ÷ fecal marker (×10⁶)",
    "houston_vl_index": "viral-load index (100 = Jul 2020)",
}


def load_city(city: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / SOURCE_FILES[city])
    df = df[df["city"] == city].copy()
    df["week"] = pd.to_datetime(df["week"])
    df = df.sort_values(["target", "week"])
    return df


def _plot_series_mpl(ax, sub: pd.DataFrame) -> list:
    """Plot each available virus series on ax; return the targets drawn."""
    drawn = []
    for tgt in VIRUS_ORDER:
        s = sub[sub["target"] == tgt]
        if s.empty:
            continue
        # mark non-detect points (at/below floor) so a flat floor line is not
        # read as a real low-level signal
        floor = CA_FLOOR.get(tgt)
        y = s["value"].to_numpy()
        ax.plot(s["week"], y, "-", color=VIRUS_COLOR[tgt], lw=1.4,
                label=VIRUS_LABEL[tgt], zorder=3)
        if floor is not None:
            nd = y <= floor * 1.05
            if nd.any():
                ax.plot(s["week"][nd], y[nd], "o", ms=2.5,
                        color=VIRUS_COLOR[tgt], mfc="white", mew=0.8, zorder=4)
        drawn.append(tgt)
    return drawn


def build_static(out_pdf: pathlib.Path, out_png: pathlib.Path) -> None:
    fig, axes = plt.subplots(5, 1, figsize=(9.2, 12.4), sharex=True)
    xmin = pd.Timestamp("2025-08-01")
    xmax = pd.Timestamp("2026-07-15")

    # Shared y-limit for the three Canadian panels (A-C), which all report the
    # same PMMoV-normalized index and so are directly comparable. LA and Houston
    # use different, non-interchangeable metrics and keep their own autoscale.
    CANADA = ["Montreal", "Toronto", "Vancouver"]
    ca_max = max(load_city(c)["value"].max() for c in CANADA)
    ca_ylim = ca_max * 1.12

    for i, city in enumerate(PANELS):
        ax = axes[i]
        sub = load_city(city)
        drawn = _plot_series_mpl(ax, sub)
        metric = sub["metric"].iloc[0]

        # visit shading. Short visits (1-4 d) render as a thin sliver, so widen
        # the drawn band to a minimum readable width centred on the true window.
        # (The band is identified by the legend and the panel title, so no
        # per-panel "visit" text label is needed.)
        v0, v1 = (pd.Timestamp(VISIT[city][0]), pd.Timestamp(VISIT[city][1]))
        min_days = 3
        if (v1 - v0).days < min_days:
            mid = v0 + (v1 - v0) / 2
            d0 = mid - pd.Timedelta(days=min_days / 2)
            d1 = mid + pd.Timedelta(days=min_days / 2)
        else:
            d0, d1 = v0, v1
        # Solid gold band marking Team Canada's stay in every city. (In Houston
        # the public feed ends before the visit, which is stated in the legend,
        # so the band itself stays solid rather than hatched.)
        ax.axvspan(d0, d1, color="#f2c94c", alpha=0.55, zorder=1, lw=0)

        # panel letter + city + metric, placed just ABOVE the plot area (in the
        # inter-panel gap) so long virus lines never collide with the label
        ax.text(0.0, 1.045, f"({chr(65 + i)})  {city}",
                transform=ax.transAxes, fontsize=11, fontweight="bold",
                va="bottom", ha="left")
        ax.text(0.27, 1.055, METRIC_LABEL[metric], transform=ax.transAxes,
                fontsize=8, color="#555555", va="bottom", ha="left",
                style="italic")

        if city in CANADA:
            ax.set_ylim(0, ca_ylim)          # shared Canadian scale
        else:
            ax.set_ylim(bottom=0)
            ax.margins(y=0.12)
        ax.grid(axis="y", color="#f0f0f0", zorder=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0, labelsize=8)
        ax.set_ylabel("relative\nlevel", fontsize=7.5, color="#777777")

    axes[-1].set_xlim(xmin, xmax)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    for lab in axes[-1].get_xticklabels():
        lab.set(fontsize=8)

    # single shared virus legend + a visit-band key, across the top
    virus_handles = [plt.Line2D([0], [0], color=VIRUS_COLOR[t], lw=2,
                                label=VIRUS_LABEL[t]) for t in VIRUS_ORDER]
    band = plt.Rectangle((0, 0), 1, 1, fc="#f2c94c", alpha=0.55,
                         label="Team Canada sampling window")
    nd = plt.Line2D([0], [0], marker="o", color="#888", mfc="white", mew=0.8,
                    ls="none", ms=5, label="non-detect (at detection floor)")
    fig.legend(handles=virus_handles + [band, nd], loc="upper center",
               ncol=3, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, 1.005))

    fig.subplots_adjust(top=0.935, hspace=0.42, left=0.09, right=0.985,
                        bottom=0.045)
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    print(f"wrote {out_pdf} and {out_png}")


def build_interactive(out: pathlib.Path) -> None:
    titles = [f"({chr(65 + i)}) {c}, {METRIC_LABEL[load_city(c)['metric'].iloc[0]]}"
              for i, c in enumerate(PANELS)]
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True,
                        subplot_titles=titles, vertical_spacing=0.055)

    CANADA = ["Montreal", "Toronto", "Vancouver"]
    ca_ylim = max(load_city(c)["value"].max() for c in CANADA) * 1.12

    seen_legend = set()
    for i, city in enumerate(PANELS, start=1):
        sub = load_city(city)
        for tgt in VIRUS_ORDER:
            s = sub[sub["target"] == tgt]
            if s.empty:
                continue
            show = tgt not in seen_legend
            seen_legend.add(tgt)
            fig.add_trace(go.Scatter(
                x=s["week"], y=s["value"], mode="lines",
                name=VIRUS_LABEL[tgt], legendgroup=tgt, showlegend=show,
                line=dict(color=VIRUS_COLOR[tgt], width=1.8),
                hovertemplate=(f"<b>{city}, {VIRUS_LABEL[tgt]}</b><br>"
                               "week of %{x|%d %b %Y}<br>"
                               "level %{y:.3g}<extra></extra>")),
                row=i, col=1)
        # visit band
        v0, v1 = VISIT[city]
        fig.add_vrect(x0=v0, x1=v1, fillcolor="#f2c94c", opacity=0.55,
                      line_width=0, row=i, col=1)
        # shared y-range for the three Canadian panels; own scale otherwise
        if city in CANADA:
            fig.update_yaxes(range=[0, ca_ylim], title_text="rel. level",
                             title_font=dict(size=9), row=i, col=1)
        else:
            fig.update_yaxes(rangemode="tozero", title_text="rel. level",
                             title_font=dict(size=9), row=i, col=1)

    fig.update_layout(
        template="simple_white", height=1250, width=900,
        paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        title="Online supplemental figure 1. Community wastewater context by host city, 2025–2026 season",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, x=0.5,
                    xanchor="center"),
        margin=dict(l=70, r=40, t=110, b=50))
    fig.update_xaxes(range=["2025-08-01", "2026-07-15"], row=5, col=1)
    fig.write_html(out, include_plotlyjs="cdn", full_html=True)
    print(f"wrote {out}")


def main() -> None:
    build_static(FIGURES / "supplement1_wastewater.pdf",
                 FIGURES / "supplement1_wastewater.png")
    build_interactive(FIGURES / "supplement1_wastewater_interactive.html")


if __name__ == "__main__":
    main()
