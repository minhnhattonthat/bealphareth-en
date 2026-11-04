"""gfx_raw.py OUT.png WIDTH_HW ENTRY[:SKIP].. : show entries as 15-bit images (WIDTH_HW halfwords wide), labelled, for formats sweep_gfx does not know."""
import sys

import numpy as np
from PIL import Image, ImageDraw

import res

d = res.load()
t = res.table(d)
W = int(sys.argv[2])
ims = []
for a in sys.argv[3:]:
    i, _, skip = a.partition(":")
    o, s = t[int(i)]
    skip = int(skip or 0, 0)
    n = (s - skip) // 2
    h = min(n // W, 256)
    v = np.frombuffer(d, dtype="<u2", count=W * h, offset=o + skip).reshape(h, W)
    rgb = np.stack([(v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3], axis=-1).astype(np.uint8)
    ims.append((a, rgb))
c = Image.new("RGB", (sum(p.shape[1] + 4 for _, p in ims), max(p.shape[0] for _, p in ims) + 12), (40, 40, 40))
dr = ImageDraw.Draw(c)
x = 0
for name, p in ims:
    c.paste(Image.fromarray(p), (x, 12))
    dr.text((x + 1, 0), name, fill=(255, 255, 255))
    x += p.shape[1] + 4
c.save(sys.argv[1])
