"""ov_calls.py ADDR [ADDR..]: list `jal ADDR` sites in every overlay, with the a0/a1/a2 immediates set just before.

Shows which scene loads or jumps to which: overlays pass scene ids as immediates.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import res

targets = {int(x, 16) for x in sys.argv[1:]}
ops = {(0x0C000000 | ((t & 0x0FFFFFFF) >> 2)): t for t in targets}
REG = {4: "a0", 5: "a1", 6: "a2", 7: "a3"}


def imms(b, p):
    """a0-a3 immediates from the delay slot and up to 8 instructions before p (addiu rX,zero,imm / ori rX,zero,imm)."""
    out = {}
    for q in [p + 4] + list(range(p - 4, max(p - 36, 0), -4)):
        w = struct.unpack_from("<I", b, q)[0]
        op, rs, rt = w >> 26, (w >> 21) & 31, (w >> 16) & 31
        if op in (9, 13) and rs == 0 and rt in REG and REG[rt] not in out:
            imm = w & 0xFFFF
            out[REG[rt]] = imm - 0x10000 if op == 9 and imm >= 0x8000 else imm
    return out


for i, o, s, b in res.entries():
    if b[:4] != b"\x02\0\0\0":
        continue
    sec2 = struct.unpack_from("<I", b, 12)[0]
    for p in range(0x10, min(sec2, len(b) - 8) & ~3, 4):
        w = struct.unpack_from("<I", b, p)[0]
        if w in ops:
            print(i, hex(s), f"+{p:#x}", f"jal {ops[w]:08x}", imms(b, p))
