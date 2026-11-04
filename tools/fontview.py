"""fontview.py FILE BITOFF STRIDE ROWS OUT.png [cols] [zoom] [colrows]: draw packed MSB-first 1bpp data as columns of STRIDE-wide rows."""
import sys

import numpy as np
from PIL import Image

path, bitoff, stride, rows, out = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 16
zoom = int(sys.argv[7]) if len(sys.argv) > 7 else 2
colrows = int(sys.argv[8]) if len(sys.argv) > 8 else rows // cols
d = np.fromfile(path, dtype=np.uint8)
bits = np.unpackbits(d[bitoff // 8:bitoff // 8 + (stride * rows) // 8 + 2])[bitoff % 8:]
bits = bits[: stride * rows].reshape(-1, stride)
canvas = np.zeros((colrows, cols * (stride + 2)), np.uint8)
for c in range(cols):
    part = bits[c * colrows:(c + 1) * colrows]
    canvas[: len(part), c * (stride + 2): c * (stride + 2) + stride] = part * 255
    canvas[:, c * (stride + 2) + stride] = 90
img = Image.fromarray(canvas)
img.resize((img.width * zoom, img.height * zoom), Image.NEAREST).save(out)
