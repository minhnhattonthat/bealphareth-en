"""glyph_probe.py VRAM.bin: print the first glyph cells of the text cache at VRAM (896,0), then search the disc files for them as 1bpp."""
import sys
from pathlib import Path

import numpy as np

import res

v = np.fromfile(sys.argv[1], dtype="<u2").reshape(-1, 1024)
X, Y = int(sys.argv[2]) if len(sys.argv) > 2 else 896, int(sys.argv[3]) if len(sys.argv) > 3 else 0
W, H = 96, 24  # pixels
r = v[Y:Y + H, X:X + W // 4]
px = np.zeros((H, W), np.uint8)
for i in range(4):
    px[:, i::4] = (r >> (4 * i)) & 15
print("values", sorted(set(px.flatten().tolist())))
for row in px[:14]:
    print("".join(".123456789abcdef"[c] for c in row))

# candidate glyph: row bitmaps of each non-empty 12-wide column block
cells = []
for cx in range(0, 96, 12):
    c = px[0:12, cx:cx + 12] != 0
    if c.sum() > 4:
        cells.append((cx, c))
srcs = [("MAIN.EXE", (res.ROOT / "work/disc/tree/MAIN.EXE").read_bytes()),
        ("PSX.EXE", (res.ROOT / "work/disc/tree/PSX.EXE").read_bytes()),
        ("SCPS", (res.ROOT / "work/disc/tree/SCPS_101.38").read_bytes())]
srcs += [(f"RES#{i}", b) for i, o, s, b in res.entries()]
ram = Path(sys.argv[4]).read_bytes() if len(sys.argv) > 4 else None
if ram:
    srcs.insert(0, ("RAM", ram))
for cx, c in cells[:4]:
    pats = {}
    rows = [int("".join("1" if b else "0" for b in row), 2) for row in c]
    pats["16msb"] = b"".join((x << 4).to_bytes(2, "big") for x in rows)
    pats["16le"] = b"".join((x << 4).to_bytes(2, "little") for x in rows)
    rrows = [int("".join("1" if b else "0" for b in row[::-1]), 2) for row in c]
    pats["16rev"] = b"".join(x.to_bytes(2, "little") for x in rrows)
    bits = "".join("1" if b else "0" for row in c for b in row)
    pats["pack"] = int(bits, 2).to_bytes(18, "big")
    bits = "".join("1" if b else "0" for row in c for b in row[::-1])
    pats["packr"] = int(bits, 2).to_bytes(18, "big")
    for nm, p in pats.items():
        for name, b in srcs:
            i = b.find(p)
            if i >= 0:
                print("cell", cx, nm, name, hex(i))
print("done")
