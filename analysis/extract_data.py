#!/usr/bin/env python3
"""Build data/cartridges_long.csv from the raw LabKey results export.

Source of truth: analysis/raw/API_PER_ROOM.html — the "Pathogen heat map by
room" dashboard exported from LabKey (dho/projects/evirus, program CANA). It
embeds, per facility, both a `points` array (ECharts render data, with
authoritative start/end epochs and a result-band code) and a `csv` payload (the
raw per-target rows with Qualitative Result and Average Result). We join the two
by (cartridge, target):

  - start / end        <- points  (epoch ms; blank in the CSV for some rows)
  - ct / qual          <- csv     (Average Result / Qualitative Result)
  - spc / spc_ct       <- csv     (SPC row's Qualitative Result / Average Result)

The four respiratory targets are emitted as 4 rows per cartridge. Every
cartridge carries a `status` of either:
  - valid     SPC positive and not flagged as invalid by the authors
  - invalid   SPC did not amplify, a probe error (SPC Ct < 5), or an author
              override (see FORCE_INVALID)

Author corrections (see REMOVE / FORCE_INVALID) are applied on every run so the
dataset is reproducible from the raw export. Cartridges recorded only as
"(invalid - no valid test data)" are dropped. Norovirus-only cartridges remain
out of scope.

The figures plot valid runs only; invalid rows are for the data table.

Detection rule (matches the study definition): a reported Ct with 0 < Ct < 99
counts as a detection regardless of the instrument's qualitative call; 99 (or a
blank / 0 average) means the target did not amplify.

Run:  python extract_data.py     (from analysis/, or via `uv run`)
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "raw" / "API_PER_ROOM.html"
OUT = HERE / "data" / "cartridges_long.csv"

# Manual corrections not derivable from the raw export (applied on every run so
# the corrected dataset is reproducible from raw/API_PER_ROOM.html):
#
# REMOVE — cartridges excluded from the dataset entirely (these were the
# "(invalid - no valid test data)" cartridges; per author review they are
# dropped rather than retained as no_valid_data rows).
REMOVE = {
    "IB000010008679", "IB000010008467", "IB000010008659", "IB000010008466",
    "IB000010008471", "IB000010006962", "IB000010006678", "IB000010006975",
    "IB000010006980", "IB000010006965", "IB000010006974",
}
# FORCE_INVALID — cartridges the export reports as valid (SPC positive) but that
# the authors have determined are invalid on external grounds.
FORCE_INVALID = {"IB000010008416"}

# LabKey assay-target names -> the short virus labels used in the figures/CSV.
VIRUS = {
    "SARS-CoV-2": "SARS-CoV-2",
    "Influenza A virus": "Influenza A",
    "Influenza B virus": "Influenza B",
    "Respiratory syncytial virus": "RSV",
}
COLUMNS = ["city", "room", "sampler", "cartridge", "start", "end", "dur_h",
           "virus", "ct", "qual", "detected", "spc", "spc_ct", "status"]


def load_facilities(html: str) -> list[dict]:
    m = re.search(r"var\s+FACILITIES\s*=\s*(\[.*?\])\s*;\s*var\s+resultColors",
                  html, re.S)
    if not m:
        raise SystemExit("FACILITIES array not found — export format changed?")
    return json.loads(m.group(1))


def iso_local(ms: int) -> str:
    """Epoch ms -> naive local wall-clock ISO string.

    The dashboard stores each city's local wall-clock time as a UTC epoch, so
    decoding as UTC recovers the intended local time (verified against the
    export's own 'Time (local)' strings)."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(
        tzinfo=None).isoformat()


def ct_value(avg: str) -> str:
    """Average Result -> Ct string, blank when the target did not amplify."""
    avg = (avg or "").strip()
    try:
        val = float(avg)
    except ValueError:
        return ""
    return avg if 0 < val < 99 else ""


def spc_status(cart: str, spc_call: str, spc_avg: str) -> tuple[str, str]:
    """Return (spc_ct, status) for a tested cartridge from its SPC row.

    A positive SPC gives a real Ct (~28-30) and status 'valid', unless the
    cartridge is in FORCE_INVALID. Any non-positive SPC (no amplification or a
    Ct < 5 probe error) is 'invalid' with a blank spc_ct."""
    if cart in FORCE_INVALID:
        return ct_value(spc_avg), "invalid"
    if (spc_call or "").strip().lower() == "positive":
        return ct_value(spc_avg), "valid"
    return "", "invalid"


def main() -> None:
    facilities = load_facilities(SRC.read_text(encoding="utf-8", errors="replace"))

    # csv payloads: (cartridge, target) -> row; per-cartridge SPC call + Ct.
    csv_rows: dict[tuple[str, str], dict] = {}
    spc: dict[str, str] = {}
    spc_avg: dict[str, str] = {}
    for f in facilities:
        text = f.get("csv", "")
        if not text.strip():
            continue
        for r in csv.DictReader(io.StringIO(text)):
            csv_rows[(r["Cartridge Id"], r["Assay Target"])] = r
            if r["Assay Target"] == "SPC":
                spc[r["Cartridge Id"]] = r["Qualitative Result"]
                spc_avg[r["Cartridge Id"]] = r["Average Result"]

    out_rows = []
    for f in facilities:
        for p in f.get("points", []):
            target = p.get("target")
            if target not in VIRUS:
                continue
            cart = p["cartridge"]
            if cart in REMOVE:
                continue
            meta = csv_rows.get((cart, target), {})
            ct = ct_value(meta.get("Average Result", ""))
            dur_h = round((p["end"] - p["start"]) / 3_600_000, 2)
            spc_ct, status = spc_status(cart, spc.get(cart, ""),
                                        spc_avg.get(cart, ""))
            out_rows.append({
                "city": p["city"],
                "room": f["roomType"],
                "sampler": f["sampler"],
                "cartridge": cart,
                "start": iso_local(p["start"]),
                "end": iso_local(p["end"]),
                "dur_h": f"{dur_h:.2f}",
                "virus": VIRUS[target],
                "ct": ct,
                "qual": meta.get("Qualitative Result", ""),
                "detected": 1 if ct else 0,
                "spc": spc.get(cart, ""),
                "spc_ct": spc_ct,
                "status": status,
            })

    # Stable order: city, room, sampler, cartridge start, then a fixed virus order.
    vorder = {v: i for i, v in enumerate(
        ["RSV", "Influenza B", "SARS-CoV-2", "Influenza A"])}
    out_rows.sort(key=lambda r: (r["city"], r["room"], r["sampler"],
                                 r["start"], vorder.get(r["virus"], 9)))

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out_rows)

    dets = sum(r["detected"] for r in out_rows)
    carts = len({r["cartridge"] for r in out_rows})
    invalid = len({r["cartridge"] for r in out_rows if r["status"] == "invalid"})
    print(f"wrote {OUT}  ({len(out_rows)} rows, {carts} cartridges, {dets} "
          f"detections, {invalid} invalid cartridges)")


if __name__ == "__main__":
    main()
