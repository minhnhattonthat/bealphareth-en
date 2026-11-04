"""vram_compare.py JP_TOUR EN_TOUR: scenes whose textures differ between two regen.py --script tools/lua/vram_final.lua tours.

English changes only the font cache and frame buffers, so any other VRAM difference is a suspect. Sprites and palettes animate:
compare the list with a look at the scene before calling one a bug. Prints scene, differing 16 px cells, first cells."""
import argparse
import sys
from pathlib import Path

import numpy as np

W, H = 1024, 512
TEXTURES = (320, 896)  # x range: the frame buffers sit left of it, the text cache (x=0x380 up) right of it
CELL = 16


def cells(a, b):
    d = (a != b)[:, TEXTURES[0]:TEXTURES[1]]
    return [(x * CELL + TEXTURES[0], y * CELL) for y in range(H // CELL) for x in range(d.shape[1] // CELL)
            if d[y * CELL:(y + 1) * CELL, x * CELL:(x + 1) * CELL].any()]


def load(path):
    return np.fromfile(path, "<u2", count=W * H).reshape(H, W)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jp", type=Path)
    ap.add_argument("en", type=Path)
    a = ap.parse_args()
    bad = 0
    for p in sorted(a.en.glob("*/vram.vram.bin")):
        q = a.jp / p.parent.name / p.name
        if not q.exists():
            print(p.parent.name, "no Japanese dump")
            continue
        c = cells(load(q), load(p))
        if c:
            bad += 1
            print(p.parent.name, len(c), c[:4])
    print(f"{bad} scenes differ")


if __name__ == "__main__":
    sys.exit(main())
