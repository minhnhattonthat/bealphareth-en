"""gfx_zoom.py OUT.png ENTRY.. : render entries' decoded sheets at 1x, side by side, labelled (ids from sweep_gfx)."""
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

import gfx
import res

d = res.load()
t = res.table(d)
ims = []
for a in sys.argv[2:]:
    i = int(a)
    o, s = t[i]
    b = d[o:o + s]
    sheets = gfx.sprite_sheets(b)
    if sheets:
        ims += [(f"{i}.{k}", gfx.to_grey(w, h, r)) for k, (w, h, r, _) in enumerate(sheets)]
    elif struct.unpack_from("<I", b, 0)[0] == 0x100000:
        w, h = struct.unpack_from("<2H", b, 0x30)
        ims.append((f"{i}b", gfx.to_grey(w, h, b[0x34:0x34 + w * h // 2])))
    else:
        ims.append((f"{i}raw", gfx.to_grey(256, min(256, s * 2 // 256), b[:128 * min(256, s * 2 // 256)])))
W = sum(p.shape[1] + 4 for _, p in ims)
H = max(p.shape[0] for _, p in ims) + 12
c = Image.new("L", (W, H), 40)
dr = ImageDraw.Draw(c)
x = 0
for name, p in ims:
    c.paste(Image.fromarray(p), (x, 12))
    dr.text((x + 1, 0), name, fill=255)
    x += p.shape[1] + 4
c.save(sys.argv[1])
