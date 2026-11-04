"""kanji_test.py RAM.bin OUT.png: draw known codes for each candidate kanji base K, to read off which K gives 今回復."""
import sys

import numpy as np
from PIL import Image, ImageDraw

BASE = 0x1b9c00
d = np.fromfile(sys.argv[1], dtype=np.uint8)
CODES = [0x80eb, 0x82cf, 0x82d0, 0x80bd]


def glyph(i):
    return np.unpackbits(d[BASE + 16 * i: BASE + 16 * i + 16])[:121].reshape(11, 11) * 255


rows = []
for K in range(0x100, 0x128):
    row = np.concatenate([glyph(K + (c >> 8 & 0x7f) * 128 + (c & 0x7f)) for c in CODES] + [np.zeros((11, 40), np.uint8)], axis=1)
    rows.append(row)
img = Image.fromarray(np.concatenate(rows, axis=0)).resize((84 * 3, 11 * len(rows) * 3), Image.NEAREST)
dr = ImageDraw.Draw(img)
for i, K in enumerate(range(0x100, 0x128)):
    dr.text((140, i * 33 + 10), hex(K), fill=255)
img.save(sys.argv[2])
