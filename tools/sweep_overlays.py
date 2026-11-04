"""sweep_overlays.py OUTDIR: find sprite sheets embedded in scene overlays via section 2's part table; dedupe by hash; thumbnail sheets. Prints counts and any scene whose table did not parse."""
import hashlib
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import gfx
import res

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
seen = {}
bad = []
nparts = 0
for i, o, s, b in res.entries():
    if struct.unpack_from("<I", b, 0)[0] != 2:
        continue
    sec = struct.unpack_from("<I", b, 12)[0]
    end = b.find(b"\0", sec)
    start = (end + 4) & ~3
    n = struct.unpack_from("<I", b, start)[0] if start + 4 <= s else 0
    if not 0 < n < 400:
        bad.append(i)
        continue
    offs = struct.unpack_from(f"<{n}I", b, start + 4)
    nparts += n
    for off in offs:
        at = start - 8 + 16 + off  # part offsets count from 8 bytes before the count word + 16 (fits name "..." + u32 n in #1023)
        if at + 16 > s:
            continue
        for w, h, r, _ in gfx.sprite_sheets(b[at:at + 0x40000]):
            key = hashlib.md5(r).hexdigest()
            seen.setdefault(key, (f"{i}+{off:x}", w, h, r))
print("scenes parsed parts", nparts, "unparsed", bad[:12], len(bad), "unique sheets", len(seen))
items = list(seen.values())
COLS, ROWS, T = 16, 8, 96
for sheet, st in enumerate(range(0, len(items), COLS * ROWS)):
    c = Image.new("L", (COLS * (T + 3), ROWS * (T + 11)), 30)
    dr = ImageDraw.Draw(c)
    for k, (name, w, h, r) in enumerate(items[st:st + COLS * ROWS]):
        im = Image.fromarray(gfx.to_grey(w, h, r))
        im.thumbnail((T, T), Image.BILINEAR)
        x, y = (k % COLS) * (T + 3), (k // COLS) * (T + 11)
        c.paste(im, (x, y + 10))
        dr.text((x + 1, y - 1), name[:15], fill=255)
    c.save(OUT / f"o{sheet:02d}.png")
print("sheets", (len(items) + COLS * ROWS - 1) // (COLS * ROWS))
