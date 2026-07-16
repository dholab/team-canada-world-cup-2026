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
  - spc                <- csv     (SPC row's Qualitative Result, per cartridge)

Only the four respiratory targets are emitted (SPC, norovirus, and invalid
placeholder rows are dropped), giving 182 cartridges x 4 viruses = 728 rows.

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
COLUMNS = ["city", "room", "sampler", "cartridge", "start", "end", "dur_h",
           "virus", "ct", "qual", "detected", "spc"]


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


def main() -> None:
    facilities = load_facilities(SRC.read_text(encoding="utf-8", errors="replace"))

    # csv payloads: (cartridge, target) -> row; and per-cartridge SPC call.
    csv_rows: dict[tuple[str, str], dict] = {}
    spc: dict[str, str] = {}
    for f in facilities:
        text = f.get("csv", "")
        if not text.strip():
            continue
        for r in csv.DictReader(io.StringIO(text)):
            csv_rows[(r["Cartridge Id"], r["Assay Target"])] = r
            if r["Assay Target"] == "SPC":
                spc[r["Cartridge Id"]] = r["Qualitative Result"]

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
    print(f"wrote {OUT}  ({len(out_rows)} rows, {carts} cartridges, {dets} detections)")


if __name__ == "__main__":
    main()
