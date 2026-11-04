"""res_probe.py: first look at MAIN.RES (archive table, entry sizes, magic bytes). Read-only."""
import collections
import struct
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "work/disc/tree/MAIN.RES"
d = open(path, "rb").read()
count, total = struct.unpack_from("<II", d, 0)
print("count", count, "total", total, "file", len(d))
offs = struct.unpack_from(f"<{count}I", d, 8)
print("first offs", [hex(o) for o in offs[:12]], "last", [hex(o) for o in offs[-6:]])
print("monotonic", all(a <= b for a, b in zip(offs, offs[1:])), "header end", hex(8 + 4 * count))
mag = collections.Counter()
sizes = []
for i, o in enumerate(offs):
    nxt = offs[i + 1] if i + 1 < count else total
    sizes.append(nxt - o)
    mag[d[o:o + 4].hex()] += 1
print("zero-size", sum(s == 0 for s in sizes), "min/max", min(s for s in sizes if s), max(sizes))
print("top magics", mag.most_common(30))
for i in range(0, count, max(1, count // 40)):
    o = offs[i]
    print(i, hex(o), sizes[i], d[o:o + 24].hex())
