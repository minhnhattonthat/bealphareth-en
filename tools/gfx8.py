"""gfx8.py OUT.png: render all 8bpp entries (u16 1, u16 ncolors, palette, pixels) at width 320 with their palettes, half size, labelled."""
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

import res

ims = []
for i, o, s, b in res.entries():
    a, nc = struct.unpack_from("<2H", b, 0)
    if a != 1 or not 16 <= nc <= 256 or s < 2048:
        continue
    pal = np.frombuffer(b, dtype="<u2", count=nc, offset=4)
    rgb = np.stack([(pal & 31) << 3, ((pal >> 5) & 31) << 3, ((pal >> 10) & 31) << 3], axis=-1).astype(np.uint8)
    full = np.zeros((256, 3), np.uint8)
    full[:nc] = rgb
    px = np.frombuffer(b, dtype=np.uint8, offset=4 + 2 * nc)
    w = 320
    h = min(len(px) // w, 240)
    ims.append((i, nc, s, Image.fromarray(full[px[: w * h].reshape(h, w)])))
print([(i, nc, s) for i, nc, s, _ in ims])
COLS = 7
W, H = 160, 120
rows = (len(ims) + COLS - 1) // COLS
c = Image.new("RGB", (COLS * (W + 3), rows * (H + 11)), (30, 30, 30))
dr = ImageDraw.Draw(c)
for k, (i, nc, s, im) in enumerate(ims):
    im.thumbnail((W, H), Image.BILINEAR)
    x, y = (k % COLS) * (W + 3), (k // COLS) * (H + 11)
    c.paste(im, (x, y + 10))
    dr.text((x + 1, y - 1), str(i), fill=(255, 255, 255))
c.save(sys.argv[1])
