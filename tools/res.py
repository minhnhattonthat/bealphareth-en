"""res.py: MAIN.RES archive reader. Header: u32 count, u32 total size, u32 offsets[count]; entry data at offset+8, 0x800-aligned."""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "work/disc/tree/MAIN.RES"


def table(d):
    count, total = struct.unpack_from("<II", d, 0)
    offs = struct.unpack_from(f"<{count}I", d, 8)
    # stored offsets are relative to byte 8, so the last entry ends at total - 8
    return [(o + 8, (offs[i + 1] if i + 1 < count else total - 8) - o) for i, o in enumerate(offs)]


def load(path=DEFAULT):
    return Path(path).read_bytes()


def entries(d=None):
    """(index, offset, size, bytes) of every non-empty entry."""
    d = load() if d is None else d
    return [(i, o, s, d[o:o + s]) for i, (o, s) in enumerate(table(d)) if s]
