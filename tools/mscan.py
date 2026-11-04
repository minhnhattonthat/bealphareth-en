"""mscan.py: find every M4/M2 message bank in MAIN.RES entries and the executables. M4: 'M4', u16 n, u32 off[n+1]. M2: 'M2', u16 n, u16 off[n+1]. Offsets from the bank start."""
import re
import struct
import sys
from collections import Counter

import res


def parse_m2(b, at, limit):
    """(count, end) if a sane M2 bank sits at b[at:], else None."""
    if b[at:at + 2] != b"M2":
        return None
    n = struct.unpack_from("<H", b, at + 2)[0]
    if not 1 <= n <= 4000 or at + 4 + 2 * (n + 1) > limit:
        return None
    offs = struct.unpack_from(f"<{n + 1}H", b, at + 4)
    if offs[0] < 4 + 2 * n or any(x > y for x, y in zip(offs, offs[1:])) or at + offs[-1] > limit:
        return None
    if offs[-1] <= offs[0]:
        return None
    return n, at + offs[-1], offs


def parse_m4(b, at, limit):
    if b[at:at + 2] != b"M4":
        return None
    n = struct.unpack_from("<H", b, at + 2)[0]
    if not 1 <= n <= 4000 or at + 4 + 4 * (n + 1) > limit:
        return None
    offs = struct.unpack_from(f"<{n + 1}I", b, at + 4)
    if offs[0] < 4 + 4 * n or any(x > y for x, y in zip(offs, offs[1:])) or at + offs[-1] > limit:
        return None
    return n, at + offs[-1], offs


def banks(b):
    """Top-level M4 banks, plus M2 banks not inside one."""
    out = []
    covered = []
    for m in re.finditer(b"M4", b):
        at = m.start()
        p = parse_m4(b, at, len(b))
        if not p:
            continue
        n, end, offs = p
        subs = [parse_m2(b, at + offs[k], at + offs[k + 1]) for k in range(n) if offs[k + 1] > offs[k]]
        ok = sum(1 for s in subs if s)
        if subs and ok == len(subs):
            strings = sum(s[0] for s in subs)
            out.append(("M4", at, end, n, strings))
            covered.append((at, end))
    for m in re.finditer(b"M2", b):
        at = m.start()
        if any(s <= at < e for s, e in covered):
            continue
        p = parse_m2(b, at, len(b))
        if p:
            n, end, offs = p
            # text check: every string ends in NUL
            ends = sum(1 for k in range(n) if offs[k + 1] > offs[k] and b[at + offs[k + 1] - 1] == 0)
            if ends >= n * 0.9:
                out.append(("M2", at, end, n, n))
    return sorted(out, key=lambda r: r[1])


def main():
    report = open(sys.argv[1] if len(sys.argv) > 1 else "work/qa/banks.tsv", "w", encoding="utf-8")
    total = Counter()
    srcs = [(name, (res.ROOT / "work/disc/tree" / name).read_bytes()) for name in ("MAIN.EXE", "PSX.EXE", "SCPS_101.38")]
    srcs += [(f"RES#{i}", b) for i, o, s, b in res.entries()]
    seen = {}
    for name, b in srcs:
        for kind, at, end, n, strings in banks(b):
            print(name, kind, hex(at), hex(end), end - at, n, strings, sep="\t", file=report)
            total[kind + " banks"] += 1
            total["strings"] += strings
            total["bytes"] += end - at
            import hashlib
            h = hashlib.md5(b[at:end]).hexdigest()
            if h not in seen:
                seen[h] = name
                total["unique bytes"] += end - at
                total["unique strings"] += strings
    print(dict(total))


if __name__ == "__main__":
    main()
