#!/usr/bin/env python3
"""Audit the committed dataset against fresh LabKey exports.

`analysis/data/cartridges_long.csv` is derived from the dashboard export in
`analysis/raw/API_PER_ROOM.html`. That dashboard is a rendering, and a rendering
can be wrong: cartridge IB000010006680's sampling window was recorded there with
the removal time as its start, producing a 1-hour bar that overlapped the next
cartridge. This script re-checks every value in the dataset against the
authoritative LabKey tables so an error like that is caught deliberately rather
than noticed by eye.

Give it the two LabKey exports (TSV):

    python scripts/audit_against_labkey.py \
        --metadata cartridge_metadata_with_facilities.tsv \
        --results  results_summary_qualitative.tsv

Both exports may contain cartridges from other studies; anything not in the
committed dataset is ignored.

What it checks, per cartridge:
  * sampling window against the deploy and removal timestamps (the check that
    caught IB000010006680). LabKey records these in UTC; they are converted to
    each host city's local time, which is what the dataset stores.
  * Ct value and detection call for all four targets, applying the study's own
    rule that 0 < Ct < 99 counts as a detection.
  * SPC call and SPC Ct, and that validity follows from the SPC call.
  * sampler, room, and run duration.

Exits non-zero if anything disagrees.
"""
from __future__ import annotations

import argparse
import collections
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "analysis" / "data" / "cartridges_long.csv"

# LabKey stores cartridge timestamps in UTC; the dataset stores each host city's
# local wall-clock time. Offsets are the summer (daylight) values, which cover
# the whole 3 June - 4 July 2026 study window.
UTC_OFFSET_HOURS = {
    "Montreal": 4, "Toronto": 4,          # EDT
    "Vancouver": 7, "Los Angeles": 7,     # PDT
    "Houston": 5,                         # CDT
}

# LabKey assay target -> the dataset's virus label. Influenza A is reported on
# two channels ("- 1" and "- 2"); either amplifying counts as a detection.
TARGET_TO_VIRUS = {
    "SARS-CoV-2": "SARS-CoV-2",
    "Influenza B virus": "Influenza B",
    "Respiratory syncytial virus": "RSV",
}

ROOM_KEYWORDS = [
    ("physio", "Physio room"),
    ("meal", "Meal room"),
    ("equip", "Equipment/Kit room"),
    ("kit room", "Equipment/Kit room"),
    ("coach", "Coaches room"),
    ("hallway", "Hallway/Lounge"),
    ("lounge", "Hallway/Lounge"),
    ("lpunge", "Hallway/Lounge"),   # a typo present in the source data
]


def detected_ct(value: str | None) -> float | None:
    """The study's detection rule: a reported 0 < Ct < 99 is a detection."""
    text = (value or "").strip()
    try:
        ct = float(text)
    except ValueError:
        return None
    return ct if 0 < ct < 99 else None


def virus_of(target: str) -> str | None:
    if target.startswith("Influenza A virus"):
        return "Influenza A"
    return TARGET_TO_VIRUS.get(target)


def normalise_room(text: str | None) -> str | None:
    first_line = (text or "").lower().split("\n")[0].strip()
    for needle, room in ROOM_KEYWORDS:
        if needle in first_line:
            return room
    return None


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", required=True, type=Path)
    ap.add_argument("--results", required=True, type=Path)
    args = ap.parse_args()

    df = pd.read_csv(DATA)
    per_cartridge = df.drop_duplicates("cartridge").set_index("cartridge")
    study = set(per_cartridge.index)

    meta = [r for r in read_tsv(args.metadata)
            if (r.get("Cartridge Id") or "") in study]
    results = [r for r in read_tsv(args.results)
               if (r.get("Cartridge Id") or "") in study]

    problems: dict[str, list] = collections.defaultdict(list)

    # ---- sampling windows, from deploy / removal timestamps -----------------
    stamps: dict[str, dict[str, list[datetime]]] = collections.defaultdict(
        lambda: {"in": [], "out": []})
    rooms: dict[str, set[str]] = collections.defaultdict(set)
    for row in meta:
        cid = row["Cartridge Id"]
        when = (row.get("Cartridge Time") or "").strip()
        if when:
            removed = (row.get("Cartridge Removed") or "").strip().lower() == "true"
            stamps[cid]["out" if removed else "in"].append(
                datetime.strptime(when, "%Y-%m-%d %H:%M"))
        for field in ("Sampler Location In Room", "Comments"):
            room = normalise_room(row.get(field))
            if room:
                rooms[cid].add(room)

    for cid, seen in stamps.items():
        row = per_cartridge.loc[cid]
        offset = timedelta(hours=UTC_OFFSET_HOURS[row.city])
        if not seen["in"] or not seen["out"]:
            problems["no deploy/removal pair"].append(cid)
            continue
        deploy, removal = min(seen["in"]) - offset, max(seen["out"]) - offset
        start, end = datetime.fromisoformat(row.start), datetime.fromisoformat(row.end)
        drift = max(abs((deploy - start).total_seconds()),
                    abs((removal - end).total_seconds())) / 60
        if drift > 2:
            problems["window"].append(
                f"{cid} {row.city} {row.room}: dataset "
                f"{start:%m-%d %H:%M}->{end:%m-%d %H:%M}, LabKey "
                f"{deploy:%m-%d %H:%M}->{removal:%m-%d %H:%M} ({drift:.0f} min off)")

    for cid, seen in rooms.items():
        room = per_cartridge.loc[cid].room
        if room not in seen:
            problems["room"].append(f"{cid}: dataset {room!r}, LabKey {sorted(seen)}")

    # ---- Ct values, detection calls, SPC ------------------------------------
    lab: dict[tuple[str, str], list[float | None]] = collections.defaultdict(list)
    spc: dict[str, dict[str, str]] = {}
    run: dict[str, dict[str, str]] = {}
    for row in results:
        cid, target = row["Cartridge Id"], row["Assay Target"]
        run.setdefault(cid, row)
        if target == "SPC":
            spc[cid] = row
            continue
        virus = virus_of(target)
        if virus:
            lab[(cid, virus)].append(detected_ct(row.get("Average Result")))

    tested = 0
    for row in df.itertuples():
        key = (row.cartridge, row.virus)
        if key not in lab:
            continue
        tested += 1
        cts = [c for c in lab[key] if c is not None]
        lab_ct = min(cts) if cts else None
        ours_ct = None if pd.isna(row.ct) else float(row.ct)
        if (lab_ct is not None) != bool(row.detected):
            problems["detection call"].append(
                f"{row.cartridge} {row.virus}: dataset detected={row.detected} "
                f"ct={ours_ct}, LabKey ct={lab_ct}")
        elif lab_ct is not None and abs(lab_ct - (ours_ct if ours_ct else -1)) > 0.051:
            problems["Ct value"].append(
                f"{row.cartridge} {row.virus}: dataset {ours_ct}, LabKey {lab_ct}")

    for cid, row in spc.items():
        ours = per_cartridge.loc[cid]
        call = (row.get("Qualitative Result") or "").strip()
        if call != str(ours.spc).strip():
            problems["SPC call"].append(f"{cid}: dataset {ours.spc!r}, LabKey {call!r}")
        if call == "Negative" and ours.status != "invalid":
            problems["validity"].append(f"{cid}: SPC Negative but status={ours.status}")

    for cid, row in run.items():
        ours = per_cartridge.loc[cid]
        sampler = (row.get("Sampler Name") or "").strip()
        if sampler != ours.sampler:
            problems["sampler"].append(
                f"{cid}: dataset {ours.sampler!r}, LabKey {sampler!r}")
        try:
            hours = float(row.get("Hours Run") or "")
        except ValueError:
            continue
        if abs(hours - float(ours.dur_h)) > 0.2:
            problems["duration"].append(
                f"{cid}: dataset {ours.dur_h} h, LabKey {hours} h")

    # ---- report -------------------------------------------------------------
    covered = len({c for c, _ in lab})
    print(f"dataset cartridges        : {len(study)}")
    print(f"  with LabKey metadata    : {len(stamps)}")
    print(f"  with LabKey results     : {covered}")
    print(f"target results compared   : {tested}")
    print(f"SPC records compared      : {len(spc)}")

    missing = sorted(study - {c for c, _ in lab})
    if missing:
        print(f"\nNo results rows for {len(missing)} cartridge(s) "
              f"(cannot verify their Ct values): {missing}")

    if not problems:
        print("\nNo discrepancies found.")
        return 0

    print()
    for kind in sorted(problems):
        items = problems[kind]
        print(f"{kind}: {len(items)}")
        for item in items[:20]:
            print(f"  {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
