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

The four respiratory targets are emitted as 4 rows per cartridge (182 x 4 = 728
rows). In addition, cartridges recorded only as "(invalid - no valid test data)"
— real collected samples that produced no result — are appended as one row each
(11 rows), so the CSV is the complete record of collected respiratory-scope
samples. Norovirus-only cartridges remain out of scope. Total: 739 rows.

Every cartridge carries a `status` describing its validity:
  - valid          SPC positive; targets tested and reportable
  - spc_negative   SPC did not amplify (Average Result 99)
  - probe_error    SPC invalid, Ct < 5 (Average Result 0, assay error)
  - no_valid_data  cartridge produced only "(invalid - no valid test data)"

The figures plot valid runs only; the invalid rows are for the data table.

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

# LabKey assay-target names -> the short virus labels used in the figures/CSV.
VIRUS = {
    "SARS-CoV-2": "SARS-CoV-2",
    "Influenza A virus": "Influenza A",
    "Influenza B virus": "Influenza B",
    "Respiratory syncytial virus": "RSV",
}
INVALID_TARGET = "(invalid - no valid test data)"
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


def parse_local(ts: str) -> str:
    """'2026-07-04 06:20 CDT' -> naive local wall-clock ISO string.

    Used for invalid cartridges, which have no `points` entry to supply epochs.
    Drops the trailing timezone abbreviation and keeps the wall-clock time, to
    match how iso_local() decodes the epoch-based rows."""
    ts = (ts or "").strip()
    if not ts:
        return ""
    body = ts.rsplit(" ", 1)[0]  # strip 'CDT'/'PDT'/'EDT'
    return datetime.strptime(body, "%Y-%m-%d %H:%M").isoformat()


def spc_status(spc_call: str, spc_avg: str) -> tuple[str, str]:
    """Return (spc_ct, status) for a tested cartridge from its SPC row.

    A positive SPC gives a real Ct (~28-30) and status 'valid'. A negative SPC
    is either no-amplification (avg 99 -> spc_negative) or a probe error
    (avg 0, 'Ct < 5 (assay error)' -> probe_error)."""
    if (spc_call or "").strip().lower() == "positive":
        return ct_value(spc_avg), "valid"
    try:
        val = float((spc_avg or "").strip())
    except ValueError:
        val = None
    if val is not None and val < 5:
        return "", "probe_error"
    return "", "spc_negative"


def main() -> None:
    facilities = load_facilities(SRC.read_text(encoding="utf-8", errors="replace"))

    # csv payloads: (cartridge, target) -> row; per-cartridge SPC call + Ct;
    # and the invalid-only cartridges (metadata taken from their invalid row).
    csv_rows: dict[tuple[str, str], dict] = {}
    spc: dict[str, str] = {}
    spc_avg: dict[str, str] = {}
    invalid_meta: dict[str, dict] = {}
    for f in facilities:
        text = f.get("csv", "")
        if not text.strip():
            continue
        for r in csv.DictReader(io.StringIO(text)):
            csv_rows[(r["Cartridge Id"], r["Assay Target"])] = r
            if r["Assay Target"] == "SPC":
                spc[r["Cartridge Id"]] = r["Qualitative Result"]
                spc_avg[r["Cartridge Id"]] = r["Average Result"]
            elif r["Assay Target"] == INVALID_TARGET:
                invalid_meta[r["Cartridge Id"]] = r

    out_rows = []
    for f in facilities:
        for p in f.get("points", []):
            target = p.get("target")
            if target not in VIRUS:
                continue
            cart = p["cartridge"]
            meta = csv_rows.get((cart, target), {})
            ct = ct_value(meta.get("Average Result", ""))
            dur_h = round((p["end"] - p["start"]) / 3_600_000, 2)
            spc_ct, status = spc_status(spc.get(cart, ""), spc_avg.get(cart, ""))
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

    # Invalid-only cartridges: one row each, no per-virus data. Metadata comes
    # from the invalid CSV row (these have no `points` to supply epochs).
    tested = {r["cartridge"] for r in out_rows}
    for cart, meta in invalid_meta.items():
        if cart in tested:
            continue  # a cartridge that also has real target rows is not lost
        start = parse_local(meta.get("Start Time (local)", ""))
        end = parse_local(meta.get("End Time (local)", ""))
        try:
            dur_h = f"{(datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 3600:.2f}"
        except ValueError:
            dur_h = ""
        out_rows.append({
            "city": meta.get("City", ""),
            "room": meta.get("Room", ""),
            "sampler": meta.get("Sampler Name", ""),
            "cartridge": cart,
            "start": start,
            "end": end,
            "dur_h": dur_h,
            "virus": "",
            "ct": "",
            "qual": "",
            "detected": 0,
            "spc": spc.get(cart, ""),
            "spc_ct": "",
            "status": "no_valid_data",
        })

    # Stable order: city, room, sampler, cartridge start, then a fixed virus
    # order (blank-virus invalid rows sort last within their cartridge/session).
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
    invalid = sum(1 for r in out_rows if r["status"] == "no_valid_data")
    print(f"wrote {OUT}  ({len(out_rows)} rows, {carts} cartridges, {dets} "
          f"detections, {invalid} invalid-cartridge rows)")


if __name__ == "__main__":
    main()
