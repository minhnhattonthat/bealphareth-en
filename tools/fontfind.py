"""fontfind.py VRAM.bin RAM.bin: bit-level search of RAM for the text-cache glyph at VRAM (896,0), any stride 8..16, both bit orders."""
import sys

import numpy as np

v = np.fromfile(sys.argv[1], dtype="<u2").reshape(-1, 1024)
ram = np.fromfile(sys.argv[2], dtype=np.uint8)
GLYPHS = [(0, 12), (12, 12), (36, 12), (48, 12)]
r = v[0:12, 896:896 + 24]
px = np.zeros((12, 96), np.uint8)
for i in range(4):
    px[:, i::4] = (r >> (4 * i)) & 15
msb = np.unpackbits(ram).astype(np.uint8).tobytes().translate(bytes([48, 49]) + bytes(254))
lsb = np.unpackbits(ram, bitorder="little").astype(np.uint8).tobytes().translate(bytes([48, 49]) + bytes(254))
for gx, gw in GLYPHS:
    cell = px[:, gx:gx + gw] != 0
    rows = [i for i in range(12) if cell[i].any()]
    cols = [i for i in range(gw) if cell[:, i].any()]
    t, b, le, ri = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    crop = cell[t:b, le:ri]
    h, w = crop.shape
    print("glyph", gx, "bbox", (le, ri, t, b))
    for stride in range(w, 25):
        for pad in range(0, stride - w + 1):
            s = "".join(("0" * pad + "".join("1" if x else "0" for x in row) + "0" * (stride - w - pad)) for row in crop)
            s = s.encode()
            for name, bits in (("msb", msb), ("lsb", lsb)):
                i = bits.find(s)
                if i >= 0:
                    print(f"  stride {stride} pad {pad} {name} bit {i} = ram {0x80000000 + i // 8:08x}.{i % 8}")
print("done")
