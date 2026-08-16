"""Guards on the committed dataset itself.

These assert the study's headline counts, so a re-extraction that silently
changes them fails here instead of in the manuscript.
"""
import csv
from pathlib import Path

import pytest

CSV = Path(__file__).resolve().parent.parent / "analysis" / "data" / "cartridges_long.csv"


@pytest.fixture(scope="module")
def rows():
    with CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_headline_counts(rows):
    cartridges = {r["cartridge"] for r in rows}
    detections = [r for r in rows if r["detected"] == "1"]
    valid = {r["cartridge"] for r in rows if r["status"] == "valid"}
    assert len(rows) == 716
    assert len(cartridges) == 179
    assert len(valid) == 174
    assert len(detections) == 13


def test_detections_by_virus(rows):
    det = [r["virus"] for r in rows if r["detected"] == "1"]
    assert det.count("SARS-CoV-2") == 9
    assert det.count("Influenza A") == 3
    assert det.count("Influenza B") == 1
    assert det.count("RSV") == 0


def test_norovirus_sampler_is_excluded(rows):
    # "Sabalenka" ran predominantly for norovirus and only occasionally on the
    # respiratory panel to confirm another sampler's detection, so it is not
    # part of the consistently-sampled series the figures describe.
    assert {r["sampler"] for r in rows} == {"Jabeur", "Kerber", "Rybakina", "Sharpova"}


def test_every_cartridge_has_all_four_targets(rows):
    per_cartridge = {}
    for r in rows:
        per_cartridge.setdefault(r["cartridge"], set()).add(r["virus"])
    expected = {"SARS-CoV-2", "Influenza A", "Influenza B", "RSV"}
    bad = {c: v for c, v in per_cartridge.items() if v != expected}
    assert not bad, f"cartridges missing targets: {bad}"


def test_no_overlapping_sampling_windows(rows):
    """A sampler cannot run two cartridges at once.

    The Houston meal-room cartridge IB000010006680 was recorded in the dashboard
    export as 03 Jul 16:03 -> 17:03, overlapping the next cartridge; the LabKey
    cartridge metadata showed the true window was 07:37 -> 16:03 (the export had
    used the removal time as the start). FIX_WINDOW in extract_data.py corrects
    it. Guard against any overlap reappearing."""
    from collections import defaultdict
    from datetime import datetime

    seen = {}
    for r in rows:
        seen[r["cartridge"]] = (r["city"], r["room"], r["sampler"],
                                r["start"], r["end"])
    by_sampler = defaultdict(list)
    for city, room, sampler, start, end in seen.values():
        by_sampler[(city, room, sampler)].append(
            (datetime.fromisoformat(start), datetime.fromisoformat(end)))

    overlaps = []
    for key, spans in by_sampler.items():
        spans.sort()
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            if s2 < e1:
                overlaps.append((key, e1.isoformat(), s2.isoformat()))
    assert not overlaps, f"overlapping windows: {overlaps}"


def test_corrected_houston_window(rows):
    r = next(x for x in rows if x["cartridge"] == "IB000010006680")
    assert r["start"] == "2026-07-03T07:37:00"
    assert r["end"] == "2026-07-03T16:03:00"
    assert r["dur_h"] == "8.43"
