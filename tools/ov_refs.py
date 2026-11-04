"""ov_refs.py ENTRY [--sub]: does an overlay's code address its parts by absolute RAM address? Lists lui/addiu-style pairs
and pointer words that land past the first message bank, against the part table. A shift of those parts would break them."""
import argparse
import struct
import sys
from pathlib import Path

import capstone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract  # noqa: E402
import res  # noqa: E402


def part_table(b):
    sec2 = struct.unpack_from("<I", b, 12)[0]
    n = struct.unpack_from("<I", b, sec2 + 8)[0]
    return sec2, [sec2 + 16 + v for v in struct.unpack_from(f"<{n}I", b, sec2 + 16)]


def refs(b, ram):
    """(kind, offset, target file offset) of absolute references inside the image."""
    sec2, _ = part_table(b)
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = False
    out = []
    hi = {}
    for i in range(0x10, sec2, 4):
        w = struct.unpack_from("<I", b, i)[0]
        if ram <= w < ram + len(b):
            out.append(("word", i, w - ram))
        op = w >> 26
        rs, rt, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 0x0F:  # lui
            hi[rt] = (imm << 16, i)
        elif op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B) and rs in hi and i - hi[rs][1] < 64:
            s = imm - 0x10000 if imm >= 0x8000 and op != 0x0D else imm
            t = (hi[rs][0] + s) & 0xFFFFFFFF
            if ram <= t < ram + len(b):
                out.append(("pair", i, t - ram))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entry", type=int)
    ap.add_argument("--sub", action="store_true")
    args = ap.parse_args()
    d = res.load()
    o, s = res.table(d)[args.entry]
    b = d[o:o + s]
    ram = 0x80136C00 if s == 0x40000 else 0x800D6C00
    sec2, parts = part_table(b)
    print("sec2", hex(sec2), "parts", [hex(p) for p in parts])
    banks = extract.find_banks(b)
    print("banks", [(k, hex(a)) for k, a, _ in banks])
    first = min(a for _, a, _ in banks)
    late = [r for r in refs(b, ram) if r[2] >= first]
    print(len(late), "refs past the first bank")
    for kind, off, t in late[:40]:
        print(f"  {kind} at {off:#x} -> {t:#x} (ram {t + ram:#x})")


if __name__ == "__main__":
    main()
