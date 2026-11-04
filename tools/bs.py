"""bs.py: decode PS1 MDEC BS v2 stills (MAIN.RES entries 'xx xx 00 38') to greyscale, luma only. For lettering surveys, not for re-encoding.

    python tools/bs.py OUT.png ENTRY [ENTRY..]   # luma sheet, width/height inferred from the macroblock count
Layout: u16 mdec_codes, u16 0x3800, u16 qscale, u16 version=2; bitstream as LE u16 words, MSB first; blocks Cr Cb Y1 Y2 Y3 Y4; DC = 10-bit signed."""
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

import res

_T = """11 0 1|011 1 1|0100 0 2|0101 2 1|00101 0 3|00111 3 1|00110 4 1|000110 1 2|000111 5 1|000101 6 1|000100 7 1
0000110 0 4|0000100 2 2|0000111 8 1|0000101 9 1|00100110 0 5|00100001 0 6|00100101 1 3|00100100 3 2|00100111 10 1
00100011 11 1|00100010 12 1|00100000 13 1|0000001010 0 7|0000001100 1 4|0000001011 2 3|0000001111 4 2|0000001001 5 2
0000001110 14 1|0000001101 15 1|0000001000 16 1|000000011101 0 8|000000011000 0 9|000000010011 0 10|000000010000 0 11
000000011011 1 5|000000010100 2 4|000000011100 3 3|000000010010 4 3|000000011110 6 2|000000010101 7 2|000000010001 8 2
000000011111 17 1|000000011010 18 1|000000011001 19 1|000000010111 20 1|000000010110 21 1|0000000011010 0 12
0000000011001 0 13|0000000011000 0 14|0000000010111 0 15|0000000010110 1 6|0000000010101 1 7|0000000010100 2 5
0000000010011 3 4|0000000010010 5 3|0000000010001 9 2|0000000010000 10 2|0000000011111 22 1|0000000011110 23 1
0000000011101 24 1|0000000011100 25 1|0000000011011 26 1|00000000011111 0 16|00000000011110 0 17|00000000011101 0 18
00000000011100 0 19|00000000011011 0 20|00000000011010 0 21|00000000011001 0 22|00000000011000 0 23|00000000010111 0 24
00000000010110 0 25|00000000010101 0 26|00000000010100 0 27|00000000010011 0 28|00000000010010 0 29|00000000010001 0 30
00000000010000 0 31|000000000011000 0 32|000000000010111 0 33|000000000010110 0 34|000000000010101 0 35|000000000010100 0 36
000000000010011 0 37|000000000010010 0 38|000000000010001 0 39|000000000010000 0 40|000000000011111 1 8|000000000011110 1 9
000000000011101 1 10|000000000011100 1 11|000000000011011 1 12|000000000011010 1 13|000000000011001 1 14
0000000000010011 1 15|0000000000010010 1 16|0000000000010001 1 17|0000000000010000 1 18|0000000000010100 6 3
0000000000011010 11 2|0000000000011001 12 2|0000000000011000 13 2|0000000000010111 14 2|0000000000010110 15 2
0000000000010101 16 2|0000000000011111 27 1|0000000000011110 28 1|0000000000011101 29 1|0000000000011100 30 1|0000000000011011 31 1"""
VLC = {}
for item in _T.replace("\n", "|").split("|"):
    code, run, level = item.split()
    VLC[code] = (int(run), int(level))
MAXLEN = max(map(len, VLC))
ZZ = np.array([0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
               35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63])
IQ = np.array([2, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37, 19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27, 29, 34, 37, 40,
               22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58, 26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38, 46, 56, 69, 83])
C = np.array([[np.cos((2 * x + 1) * u * np.pi / 16) * (np.sqrt(0.125) if u == 0 else 0.5) for u in range(8)] for x in range(8)])


def blocks(b):
    """Yield 8x8 coefficient arrays until the stream ends or a code is unknown."""
    qs = struct.unpack_from("<H", b, 4)[0]
    words = np.frombuffer(b, dtype="<u2", offset=8, count=(len(b) - 8) // 2)
    bits = "".join(f"{w:016b}" for w in words.tolist())
    p, n = 0, len(bits)
    while p + 10 < n:
        dc = int(bits[p:p + 10], 2)
        p += 10
        if dc >= 512:
            dc -= 1024
        co = np.zeros(64)
        co[0] = dc * IQ[0]
        k = 0
        while True:
            if p + 2 > n:
                return
            if bits[p:p + 2] == "10":
                p += 2
                break
            if bits[p:p + 6] == "000001":
                run = int(bits[p + 6:p + 12], 2)
                lev = int(bits[p + 12:p + 22], 2)
                if lev >= 512:
                    lev -= 1024
                p += 22
            else:
                for L in range(2, MAXLEN + 1):
                    hit = VLC.get(bits[p:p + L])
                    if hit:
                        run, lev = hit
                        p += L
                        if bits[p] == "1":
                            lev = -lev
                        p += 1
                        break
                else:
                    return
            k += run + 1
            if k > 63:
                return
            z = ZZ[k]
            co[z] = lev * IQ[z] * qs / 8
        yield co.reshape(8, 8)


def luma(b):
    """(mb count, list of 16x16 luma macroblocks) in stream order (columns first)."""
    mbs, cur = [], []
    for i, co in enumerate(blocks(b)):
        if i % 6 < 2:
            continue
        cur.append(C @ co @ C.T)
        if len(cur) == 4:
            mbs.append(np.block([[cur[0], cur[1]], [cur[2], cur[3]]]))
            cur = []
    return mbs


def image(b):
    mbs = luma(b)
    n = len(mbs)
    # game stills: pick the common height that divides the macroblock count
    for h in (30, 15, 16, 14, 32, 8, 10, 12, 7, 6, 5, 4, 3, 2, 1):  # 600 mbs = 320x480, verified by eye on #2216
        if n and n % h == 0 and n // h <= 40:
            break
    else:
        h = 1
    w = n // h if n else 0
    a = np.zeros((h * 16, w * 16))
    for i, m in enumerate(mbs[: w * h]):
        a[(i % h) * 16:(i % h) * 16 + 16, (i // h) * 16:(i // h) * 16 + 16] = m
    return np.clip(a + 128, 0, 255).astype(np.uint8), w * 16, h * 16, n


if __name__ == "__main__":
    d = res.load()
    t = res.table(d)
    ims = []
    for a in sys.argv[2:]:
        o, s = t[int(a)]
        px, w, h, n = image(d[o:o + s])
        print(a, "size", s, "mbs", n, "dims", w, h, flush=True)
        ims.append((a, px))
    W = sum(max(p.shape[1], 1) + 3 for _, p in ims)
    H = max(p.shape[0] for _, p in ims) + 11
    c = Image.new("L", (W, H), 40)
    dr = ImageDraw.Draw(c)
    x = 0
    for name, p in ims:
        if p.size:
            c.paste(Image.fromarray(p), (x, 11))
        dr.text((x + 1, 0), name, fill=255)
        x += max(p.shape[1], 1) + 3
    c.save(sys.argv[1])
