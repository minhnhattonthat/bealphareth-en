"""msgtab.py ENTRY: find u16 message-offset tables inside a MAIN.RES scene: rising u16 runs whose targets (from a base) follow a NUL. Read-only."""
import struct
import sys

import res

d = res.load()
idx = int(sys.argv[1])
o, s = res.table(d)[idx]
b = d[o:o + s]
# rising u16 runs
runs = []
i = 0
while i + 2 <= len(b):
    j = i
    prev = struct.unpack_from("<H", b, j)[0]
    n = 1
    while j + 4 <= len(b):
        v = struct.unpack_from("<H", b, j + 2)[0]
        if v <= prev:
            break
        prev = v
        j += 2
        n += 1
    if n >= 12:
        runs.append((i, n))
        i = j + 2
    else:
        i += 2
for start, n in runs:
    vals = struct.unpack_from(f"<{n}H", b, start)
    # base candidates: end of table, or table start
    best = None
    for base in (start, start + 2 * n):
        hit = sum(1 for v in vals if base + v < len(b) and b[base + v - 1] == 0)
        if best is None or hit > best[1]:
            best = (base, hit)
    print(f"table +{start:#x} n={n} first={vals[0]:#x} last={vals[-1]:#x} base +{best[0]:#x} nulprev {best[1]}/{n}")
