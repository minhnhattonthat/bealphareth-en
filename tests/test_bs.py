"""BS stills: the encoder rebuilds originals exactly, and an edit keeps untouched macroblocks."""
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bs  # noqa: E402
import res  # noqa: E402

SAMPLES = (2216, 2617, 2700, 3117, 3968, 4000)


def still(entry):
    d = res.load()
    o, s = res.table(d)[entry]
    return bytes(d[o:o + s])


def test_stream_rebuilds_originals_byte_for_byte():
    for e in SAMPLES:
        b = still(e)
        levels, _ = bs.parse_levels(b)
        new = bs.stream(levels, struct.unpack_from("<H", b, 4)[0])
        assert new[:2] == b[:2], e
        assert new[2:] == b[2:len(new)], e


def test_edit_keeps_what_it_did_not_touch():
    b = still(4000)
    y, cb, cr, levels = bs.decode_planes(b)
    rgb = bs.to_rgb(y, cb, cr)
    changed = np.zeros(rgb.shape[:2], bool)
    changed[100:116, 64:80] = True
    new = bs.edit_still(b, rgb, changed)
    after, _ = bs.parse_levels(new)
    same = sum(a == b_ for a, b_ in zip(after, levels))
    assert len(after) == len(levels) and same >= len(levels) - 6 * 9
    y2, _, _, _ = bs.decode_planes(new)
    assert abs(y2 - y).max() < 40


def test_colour_round_trip_is_close():
    rgb = np.random.default_rng(1).integers(40, 200, (32, 32, 3), dtype=np.uint8)
    rgb = rgb.repeat(2, axis=0).repeat(2, axis=1)  # flat 2x2 cells survive the chroma average
    assert abs(bs.to_rgb(*bs.from_rgb(rgb)).astype(int) - rgb).max() <= 2
