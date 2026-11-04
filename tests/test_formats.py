"""Format checks: RLE and bank parsing on synthetic data, the archive table on the real disc when present."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gfx  # noqa: E402
import mscan  # noqa: E402
import res  # noqa: E402


def test_rle_repeat_and_literals():
    assert gfx.rle_decode(bytes([3, 7, 0xFE, 1, 2]), 5) == bytes([7, 7, 7, 1, 2])


def test_m2_bank_parses_and_rejects_bad_offsets():
    good = b"M2" + struct.pack("<H3H", 2, 10, 12, 14) + b"a\0b\0"
    assert mscan.parse_m2(good, 0, len(good))[:2] == (2, 14)
    bad = b"M2" + struct.pack("<H3H", 2, 12, 10, 14) + b"a\0b\0"
    assert mscan.parse_m2(bad, 0, len(bad)) is None


@pytest.mark.skipif(not res.DEFAULT.exists(), reason="no unpacked disc")
def test_res_table_covers_the_file():
    d = res.load()
    t = res.table(d)
    assert len(t) == 5010
    assert t[0][0] == 0x5000
    assert t[-1][0] + t[-1][1] == len(d)
    assert all(o % 0x800 == 0 for o, s in t if s)
