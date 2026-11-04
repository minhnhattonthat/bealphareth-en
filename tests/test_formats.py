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
import sprites  # noqa: E402


def test_rle_repeat_and_literals():
    assert gfx.rle_decode(bytes([3, 7, 0xFE, 1, 2]), 5) == bytes([7, 7, 7, 1, 2])


def test_rle_exact_fills_the_old_size_with_no_padding():
    raw = bytes([5] * 200 + [1, 2, 3] * 20 + [0] * 90)
    base = len(sprites.rle_encode(raw))
    for spare in range(0, 200):
        packed = sprites.rle_exact(raw, base + spare)
        assert len(packed) == base + spare
        assert gfx.rle_decode(packed, len(raw)) == raw
        i = 0
        while i < len(packed):  # tokens end exactly at the end, and only shapes the original sheets use: runs of 2+
            assert packed[i] >= 2
            i += 2 if packed[i] < 0x80 else 257 - packed[i]
        assert i == len(packed)
    with pytest.raises(ValueError):
        sprites.rle_exact(raw, base - 1)


def test_sheet_stream_stops_8_bytes_short_of_its_packed_field():
    stream = bytes([4, 7])
    head = struct.pack("<4HII", 0x8000, 4, 2, 0, len(stream) + 8, 4)
    pal = struct.pack("<II", 0x28, 1) + bytes(32)
    blob = pal + head + stream + b"NEXT"
    [(_, _, at, _, _, _, comp, raw, _)] = list(sprites.sheets_at(blob, 0, 0))
    assert (comp, raw) == (2, bytes([7] * 4))
    b = bytearray(blob)
    sprites.pack_into(b, at, 0x8000, comp, bytes([9] * 4))
    assert b.endswith(bytes([4, 9]) + b"NEXT")


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
