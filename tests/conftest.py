"""Shared fixtures. Makes scripts/ importable and loads the frozen Doc export."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(scope="session")
def doc_md() -> str:
    """The frozen Google Doc markdown export (captured 2026-08-15)."""
    return (Path(__file__).parent / "fixtures" / "doc_export.md").read_text(
        encoding="utf-8"
    )
