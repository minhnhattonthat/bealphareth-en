"""re_diff.py A B [--base HEX] [--dis]: changed byte ranges between two files; with --dis, disassemble them (MIPS, words)."""
import argparse
from pathlib import Path

import capstone


def spans(a, b, gap=8):
    out = []
    i, n = 0, min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            last = i
            while j < n and j - last <= gap:
                if a[j] != b[j]:
                    last = j
                j += 1
            out.append((i, last + 1))
            i = last + 1
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--base", type=lambda s: int(s, 16), default=0)
    ap.add_argument("--dis", action="store_true")
    args = ap.parse_args()
    a, b = Path(args.a).read_bytes(), Path(args.b).read_bytes()
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    if len(a) != len(b):
        print("sizes", len(a), len(b))
    for s, e in spans(a, b):
        print(f"{s + args.base:08X}..{e + args.base:08X} ({e - s})")
        if args.dis:
            s &= ~3
            for ins in md.disasm(b[s:(e + 3) & ~3], s + args.base):
                print(f"  {ins.address:08X} {ins.mnemonic} {ins.op_str}")


if __name__ == "__main__":
    main()
