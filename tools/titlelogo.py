"""titlelogo.py [OUT.png]: take the katakana off the title logo (docs/re/graphics.md row 12, decision D5). RES#3924: u16 1, u16 256,
palette, u32 n, u32 off[n] from there, pieces of u16 x, y, w, h + 8bpp pixels; together 320x240. Prints what it changed."""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import res  # noqa: E402

ENTRY = 3924
AREA = (140, 34, 256, 76)  # x0, y0, x1, y1 of the katakana, over the letters' tops
LETTER_TOPS = ((136, 70), (146, 53), (148, 53), (149, 76), (155, 75), (161, 70), (172, 58), (174, 58), (175, 72), (181, 76),
               (184, 83), (191, 76), (198, 77), (202, 79), (207, 74), (216, 78), (226, 77), (228, 71), (236, 63), (237, 71),
               (246, 58), (247, 72), (248, 76), (256, 80))


def pieces(b):
    """(palette RGB, [(at, x, y, w, h)])."""
    nc = struct.unpack_from("<H", b, 2)[0]
    pal = np.frombuffer(b, "<u2", nc, 4)
    rgb = np.stack([(pal & 31) << 3, ((pal >> 5) & 31) << 3, ((pal >> 10) & 31) << 3], -1).astype(np.uint8)
    base = 4 + 2 * nc
    n = struct.unpack_from("<I", b, base)[0]
    out = []
    for off in struct.unpack_from(f"<{n}I", b, base + 4):
        x, y, w, h = struct.unpack_from("<4H", b, base + 4 + off)
        out.append((base + 4 + off + 8, x, y, w, h))
    return rgb, out


def image(b):
    _, parts = pieces(b)
    im = np.zeros((240, 320), np.uint8)
    for at, x, y, w, h in parts:
        im[y:y + h, x:x + w] = np.frombuffer(b, np.uint8, w * h, at).reshape(h, w)
    return im


def mask_for(rgb):
    """Katakana: anything not purple or dark in AREA, above the letters' outline (read off a zoom)."""
    a = rgb.astype(int)
    r, g, bl = a[..., 0], a[..., 1], a[..., 2]
    x0, y0, x1, y1 = AREA
    tops = np.interp(np.arange(320), *zip(*LETTER_TOPS))
    above = np.arange(240)[:, None] < tops[None, :] - 1
    box = np.zeros(g.shape, bool)
    box[y0:y1, x0:x1] = True
    ink = (g > 45) | (r > bl + 12)
    return ndimage.binary_dilation(ink & box & above, iterations=2) & box & above


def edit(b):
    """The entry with the katakana gone; only pixels in AREA change."""
    pal, parts = pieces(b)
    im = image(b)
    rgb = pal[im]
    mask = mask_for(rgb)
    a = rgb.astype(int)
    ground = ~mask & (a[..., 1] <= 45) & (a[..., 0] <= a[..., 2] + 12)  # fill from the purple, never the letters' rims
    ind = ndimage.distance_transform_edt(~ground, return_distances=False, return_indices=True)
    filled = rgb[tuple(ind)].astype(float)
    soft = np.stack([ndimage.gaussian_filter(filled[..., c], 1.2) for c in range(3)], axis=2)
    want = soft[mask]
    idx = np.argmin(((want[:, None, :] - pal[None, :, :].astype(float)) ** 2).sum(-1), axis=1)
    new = im.copy()
    new[mask] = idx
    out = bytearray(b)
    for at, x, y, w, h in parts:
        out[at:at + w * h] = new[y:y + h, x:x + w].tobytes()
    return bytes(out), pal[new]


def apply(main_res, table):
    o, s = table[ENTRY]
    main_res[o:o + s] = edit(bytes(main_res[o:o + s]))[0]


if __name__ == "__main__":
    d = res.load()
    o, s = res.table(d)[ENTRY]
    b = bytes(d[o:o + s])
    new, rgb = edit(b)
    print(sum(x != y for x, y in zip(b, new)), "bytes changed")
    x0, y0, x1, y1 = 100, 20, 280, 100
    Image.fromarray(rgb[y0:y1, x0:x1]).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.NEAREST).save(sys.argv[1])
