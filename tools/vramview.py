"""vramview.py VRAM.bin OUT.png [--4bpp x,y,w,h] [--zoom N]: PS1 VRAM dump to PNG. Whole page as 15-bit, or a rect as greyscale 4bpp."""
import argparse

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vram")
    ap.add_argument("out")
    ap.add_argument("--4bpp", dest="bpp4", help="x,y,w,h in VRAM halfwords/lines")
    ap.add_argument("--zoom", type=int, default=1)
    a = ap.parse_args()
    v = np.fromfile(a.vram, dtype="<u2").reshape(1024 if len(open(a.vram, "rb").read()) > 1100000 else 512, 1024)[:512]
    if a.bpp4:
        x, y, w, h = map(int, a.bpp4.split(","))
        r = v[y:y + h, x:x + w]
        px = np.zeros((h, w * 4), np.uint8)
        for i in range(4):
            px[:, i::4] = ((r >> (4 * i)) & 15) * 17
        img = Image.fromarray(px, "L")
    else:
        rgb = np.stack([(v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3], axis=-1).astype(np.uint8)
        img = Image.fromarray(rgb, "RGB")
    if a.zoom > 1:
        img = img.resize((img.width * a.zoom, img.height * a.zoom), Image.NEAREST)
    img.save(a.out)


main()
