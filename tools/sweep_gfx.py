"""sweep_gfx.py OUTDIR: static sweep of MAIN.RES images into numbered sheets with entry ids. Prints every class it skips and why.

Sprite sheets are decoded by gfx.py; other classes render as raw 4bpp after their palette. Greyscale, half size."""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import gfx
import res

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
COLS, ROWS, T = 12, 8, 128
thumbs, skip = [], {}
for i, o, s, b in res.entries():
    head = struct.unpack_from("<I", b, 0)[0]
    if head == 2:
        skip.setdefault("scene overlay: swept by scan_overlays, not here", []).append(i)
    elif b[2:4] == b"\x00\x38":
        skip.setdefault("MDEC BS still: tools/bs.py", []).append(i)
    elif b[12:16] == b"SShd":
        skip.setdefault("VAB", []).append(i)
    elif b[:2] == b"M4":
        skip.setdefault("message bank", []).append(i)
    elif head == 0x30:
        skip.setdefault("0x30 frame table, pixels live in the sheet before it", []).append(i)
    else:
        sheets = gfx.sprite_sheets(b)
        if sheets:
            for k, (w, h, r, _) in enumerate(sheets):
                thumbs.append((f"{i}.{k}", gfx.to_grey(w, h, r)))
        elif head == 0x100000 and len(b) > 0x40:
            w, h = struct.unpack_from("<2H", b, 0x30)
            thumbs.append((f"{i}b", gfx.to_grey(w, h, b[0x34:0x34 + w * h // 2])) if 0 < w <= 1024 and 0 < h <= 512 else (f"{i}?", np.zeros((8, 8), np.uint8)))
        elif b[:2] == b"\0\0" and len(b) >= 2048:
            h = min(256, (len(b) - 32) * 2 // 256)
            thumbs.append((f"{i}t", gfx.to_grey(256, h, b[32:32 + 128 * h])))
        else:
            skip.setdefault(f"unknown head {head:08x}", []).append(i)
print("thumbs", len(thumbs))
for k, v in sorted(skip.items(), key=lambda kv: -len(kv[1])):
    print("skipped", k, len(v), "e.g.", v[:5])
sheet = 0
for start in range(0, len(thumbs), COLS * ROWS):
    canvas = Image.new("L", (COLS * (T + 3), ROWS * (T + 11)), 30)
    dr = ImageDraw.Draw(canvas)
    for k, (name, px) in enumerate(thumbs[start:start + COLS * ROWS]):
        im = Image.fromarray(px)
        im.thumbnail((T, T), Image.BILINEAR)
        x, y = (k % COLS) * (T + 3), (k // COLS) * (T + 11)
        canvas.paste(im, (x, y + 10))
        dr.text((x + 1, y - 1), name, fill=255)
    canvas.save(OUT / f"s{sheet:03d}.png")
    print(f"s{sheet:03d}.png", thumbs[start][0], thumbs[min(start + COLS * ROWS, len(thumbs)) - 1][0])
    sheet += 1
print("sheets", sheet)
