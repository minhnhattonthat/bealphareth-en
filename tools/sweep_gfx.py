"""sweep_gfx.py OUTDIR: static sweep of non-scene MAIN.RES entries into numbered grey-4bpp thumbnail sheets; prints every skipped class and why.

Classes rendered: palette-prefixed bitmaps (0x28,0x48,.. = palette bytes, count) and framed sprites (0x30). shortcut: greyscale,
ignores per-frame layout, enough to spot lettering; upgrade with real frame parsing in phase 7 for entries that need editing."""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import res

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
TH = 256  # thumbnail width in pixels
ROW = 6
COLS = 8
THUMB_H = 128
items, skip = [], {}
for i, o, s, b in res.entries():
    head = struct.unpack_from("<I", b, 0)[0]
    if head == 2:
        skip.setdefault("scene overlay (code+assets, swept via its sections later)", []).append(i)
    elif b[2:4] == b"\x00\x38" or (b[0:1] == b"\x00" and b[1:2] != b"\x00" and b[3] == 0x38):
        skip.setdefault("MDEC BS still (needs decoder)", []).append(i)
    elif b[12:16] == b"SShd" or head in (0x486, 0x36e, 0x4d2):
        skip.setdefault("sound VAB", []).append(i)
    elif b[:2] == b"M4":
        skip.setdefault("message bank", []).append(i)
    elif head < 0x400 and head % 8 == 0 and head >= 0x28:
        pal = head
        items.append((i, 8 + pal if struct.unpack_from("<I", b, 4)[0] < 64 else 0, s, b))
    else:
        items.append((i, 0, s, b))
print("rendered", len(items))
for k, v in skip.items():
    print("skipped", k, len(v), "e.g.", v[:6])

W = TH // 4  # halfwords... 4bpp: 2 bytes = 4 px
sheet_i = 0
for start in range(0, len(items), ROW * COLS):
    chunk = items[start:start + ROW * COLS]
    canvas = Image.new("L", (COLS * (TH + 4), ROW * (THUMB_H + 12)), 30)
    dr = ImageDraw.Draw(canvas)
    for k, (i, off, s, b) in enumerate(chunk):
        raw = np.frombuffer(b, dtype=np.uint8, offset=off)
        h = min(THUMB_H, len(raw) * 2 // TH)
        if h <= 0:
            continue
        raw = raw[: h * TH // 2]
        px = np.zeros((h, TH), np.uint8)
        px[:, 0::2] = (raw[: h * TH // 2].reshape(h, TH // 2) & 15) * 17
        px[:, 1::2] = (raw[: h * TH // 2].reshape(h, TH // 2) >> 4) * 17
        x, y = (k % COLS) * (TH + 4), (k // COLS) * (THUMB_H + 12)
        canvas.paste(Image.fromarray(px), (x, y + 11))
        dr.text((x + 1, y), f"{i}", fill=255)
    canvas.save(OUT / f"sweep_{sheet_i:03d}.png")
    print(f"sweep_{sheet_i:03d}.png", chunk[0][0], chunk[-1][0])
    sheet_i += 1
print("sheets", sheet_i)
