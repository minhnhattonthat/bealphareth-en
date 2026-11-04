"""The pinned dump matches rom.sha1 (skips on a clone without the disc)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_rom  # noqa: E402


@pytest.mark.skipif(not (ROOT / "rom/Bealphareth (Japan).bin").exists(), reason="no disc image")
def test_dump_matches_pin():
    check_rom.check()
