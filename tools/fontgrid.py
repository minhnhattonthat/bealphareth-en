"""fontgrid.py FILE BYTEOFF COUNT OUT.png [cols] [zoom] [first_index]: 16-byte 11x11 glyphs as a grid; each row labelled with its first glyph index in hex."""
import sys

import numpy as np
from PIL import Image, ImageDraw

path, off, count, out = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), sys.argv[4]
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 32
zoom = int(sys.argv[6]) if len(sys.argv) > 6 else 2
first = int(sys.argv[7], 0) if len(sys.argv) > 7 else 0
d = np.fromfile(path, dtype=np.uint8)
CW, CH = 13, 13
LAB = 34
rows = (count + cols - 1) // cols
img = Image.new("L", (LAB + cols * CW * zoom, rows * CH * zoom), 40)
px = np.array(img)
for i in range(count):
    raw = d[off + 16 * i: off + 16 * i + 16]
    bits = np.unpackbits(raw)[:121].reshape(11, 11) * 255
    bits = np.kron(bits, np.ones((zoom, zoom), np.uint8))
    y, x = (i // cols) * CH * zoom, LAB + (i % cols) * CW * zoom
    px[y:y + bits.shape[0], x:x + bits.shape[1]] = bits
img = Image.fromarray(px)
dr = ImageDraw.Draw(img)
for r in range(rows):
    dr.text((1, r * CH * zoom), f"{first + r * cols:04x}", fill=255)
img.save(out)
