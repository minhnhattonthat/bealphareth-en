"""gfx.py: decode MAIN.RES sprite entries. RLE: n<0x80 repeats next byte n times; n>=0x80 copies 256-n literals. See docs/re/graphics.md."""
import struct

import numpy as np


def rle_decode(b, raw_size):
    out = bytearray()
    i = 0
    while i < len(b) and len(out) < raw_size:
        n = b[i]
        i += 1
        if n < 0x80:
            out += bytes([b[i]]) * n
            i += 1
        else:
            k = 256 - n
            out += b[i:i + k]
            i += k
    return bytes(out)


def sprite_sheets(b):
    """Palette-prefixed entry -> [(w, h, 4bpp raster bytes, palette u16 list)]; [] when the layout does not match."""
    pal_bytes = struct.unpack_from("<I", b, 0)[0]
    npal = struct.unpack_from("<I", b, 4)[0]
    if pal_bytes < 0x28 or pal_bytes % 8 or not 0 < npal < 64 or 8 + npal * 32 != pal_bytes:
        return []
    pal = struct.unpack_from("<16H", b, 8)
    out = []
    at = pal_bytes
    while at + 8 <= len(b):
        flags, w, h, _ = struct.unpack_from("<4H", b, at)
        if w == 0 or h == 0 or w > 1024 or h > 512 or w % 4:
            break
        if flags & 0x8000:
            comp, raw = struct.unpack_from("<II", b, at + 8)
            if raw != w * h // 2 or at + 8 + comp > len(b):
                break
            comp -= 8  # the field counts itself and the raw size
            out.append((w, h, rle_decode(b[at + 16:at + 16 + comp], raw), pal))
            at += 16 + ((comp + 3) & ~3)
        else:
            raw = w * h // 2
            if at + 8 + raw > len(b):
                break
            out.append((w, h, b[at + 8:at + 8 + raw], pal))
            at += 8 + raw
    return out


def to_grey(w, h, raster):
    a = np.frombuffer(raster, dtype=np.uint8)
    px = np.zeros(w * h, np.uint8)
    n = min(len(a) * 2, w * h)
    px[0:n:2] = a[: (n + 1) // 2] & 15
    px[1:n:2] = a[: n // 2] >> 4
    return px.reshape(h, w) * 17
