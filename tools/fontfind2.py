"""fontfind2.py SHOT.png RAM.bin X Y N: cut N 11x11 glyph cells from a screenshot row at (X,Y) spaced by SP and locate each in RAM (stride 11, MSB)."""
import sys

import numpy as np
from PIL import Image

shot, rampath, X, Y, N = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
SP = int(sys.argv[6]) if len(sys.argv) > 6 else 12
img = np.array(Image.open(shot).convert("L"))
ram = np.fromfile(rampath, dtype=np.uint8)
msb = np.unpackbits(ram).tobytes().translate(bytes([48, 49]) + bytes(254))
TH = 110
for k in range(N):
    cell = img[Y:Y + 12, X + k * SP:X + k * SP + 12] > TH
    if not cell.any():
        print(k, "empty")
        continue
    rows = np.where(cell.any(axis=1))[0]
    cols = np.where(cell.any(axis=0))[0]
    crop = cell[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    h, w = crop.shape
    found = []
    for pad in range(0, 11 - w + 1):
        s = "".join("0" * pad + "".join("1" if x else "0" for x in row) + "0" * (11 - w - pad) for row in crop).encode()
        i = msb.find(s)
        while i >= 0 and len(found) < 8:
            found.append((pad, i, hex(0x80000000 + i // 8), i % 8))
            i = msb.find(s, i + 1)
    print(k, "bbox", (cols[0], cols[-1], rows[0], rows[-1]), found[:6])
    for row in crop:
        print("   ", "".join("#" if x else "." for x in row))
