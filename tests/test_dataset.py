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
