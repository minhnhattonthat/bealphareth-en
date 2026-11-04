"""gfx_part.py OUT.png ENTRY+PARTHEX ..: render a sprite sheet embedded in a scene overlay (ids from sweep_overlays), labelled, side by side, full size."""
import struct
import sys

from PIL import Image, ImageDraw

import gfx
import res

d = res.load()
t = res.table(d)
ims = []
for a in sys.argv[2:]:
    i, off = a.split("+")
    o, s = t[int(i)]
    b = d[o:o + s]
    sec = struct.unpack_from("<I", b, 12)[0]
    at = sec + 16 + int(off, 16)
    for k, (w, h, r, _) in enumerate(gfx.sprite_sheets(b[at:at + 0x40000])):
        ims.append((f"{a}.{k} {w}x{h}", gfx.to_grey(w, h, r)))
c = Image.new("L", (sum(p.shape[1] + 4 for _, p in ims), max(p.shape[0] for _, p in ims) + 12), 40)
dr = ImageDraw.Draw(c)
x = 0
for name, p in ims:
    c.paste(Image.fromarray(p), (x, 12))
    dr.text((x + 1, 0), name, fill=255)
    x += p.shape[1] + 4
c.save(sys.argv[1])
