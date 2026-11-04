"""ov_scan.py: for each scene overlay print id, slot, total size, name, parts, and jal targets beyond its own end.

Finds overlays that only run with another overlay loaded beside them (their calls land past their own image).
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import res

BASE = 0x800D6C00
for i, o, s, b in res.entries():
    if b[:4] != b"\x02\0\0\0":
        continue
    total, _, sec2 = struct.unpack("<3I", b[4:16])
    name = b[sec2:sec2 + 8].split(b"\0")[0].decode("latin1", "replace") if sec2 + 8 <= len(b) else "?"
    nparts = struct.unpack("<I", b[sec2 + 8:sec2 + 12])[0] if sec2 + 12 <= len(b) else -1
    out = {}
    for p in range(0x10, min(sec2, len(b)) & ~3, 4):
        w = struct.unpack_from("<I", b, p)[0]
        if w >> 26 == 3:
            t = 0x80000000 | ((w & 0x3FFFFFF) << 2)
            if t >= BASE + total:
                out[t] = out.get(t, 0) + 1
    ext = f"ext {min(out):08x}-{max(out):08x} n={len(out)}" if out else ""
    print(i, hex(s), hex(total), repr(name), nparts, ext)
