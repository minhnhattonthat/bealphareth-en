"""res_types.py: classify MAIN.RES entries by first dword; print counts, size range, index range and a hex sample per class. Read-only."""
import collections
import struct

import res

cls = collections.defaultdict(list)
for i, o, s, b in res.entries():
    cls[struct.unpack_from("<I", b, 0)[0]].append((i, s, b[:40]))
for k, v in sorted(cls.items(), key=lambda kv: -len(kv[1]))[:40]:
    idx = [x[0] for x in v]
    sz = [x[1] for x in v]
    print(f"{k:08x} n={len(v):5d} size {min(sz)}..{max(sz)} idx {idx[0]}..{idx[-1]} sample#{idx[0]} {v[0][2].hex(' ')}")
print("classes", len(cls))
