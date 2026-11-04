"""ov_parents.py: which map overlay (0xA0000 slot) names each sub-scene (0x40000 slot) id: immediates and u16/u32 tables.

Prints `sub  parents...` and writes work/qa/ov_parents.tsv. A sub-scene runs on top of its parent's room and objects, so a
warp must load the right parent. Hits in data are only candidates: ids are small numbers and can match by chance.
"""
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import res

ROOT = Path(__file__).resolve().parents[2]
maps, subs = {}, {}
for i, o, s, b in res.entries():
    if b[:4] == b"\x02\0\0\0":
        (maps if s == 0xA0000 else subs)[i] = b

imm, jal, tab = defaultdict(set), defaultdict(set), defaultdict(set)
for i, b in maps.items():
    total, _, sec2 = struct.unpack_from("<3I", b, 4)
    code_end = min(sec2, len(b) - 8) & ~3
    for p in range(0x10, code_end, 4):
        w = struct.unpack_from("<I", b, p)[0]
        op, rs = w >> 26, (w >> 21) & 31
        if op in (9, 13) and rs == 0 and (w & 0xFFFF) in subs:
            imm[w & 0xFFFF].add(i)
    # shortcut: tables searched only in the code section's tail and data before the part directory, u16-aligned runs of 2+ ids
    for p in range(0x10, code_end, 2):
        v, n = struct.unpack_from("<2H", b, p)
        if v in subs and (n in subs or n == 0 or n == 0xFFFF):
            tab[v].add(i)

with open(ROOT / "work/qa/ov_parents.tsv", "w") as f:
    for s in sorted(subs):
        size = struct.unpack_from("<I", subs[s], 4)[0]
        line = f"{s}\t{size:#x}\timm={sorted(imm[s])}\ttab={sorted(tab[s])}"
        print(line)
        f.write(line + "\n")
