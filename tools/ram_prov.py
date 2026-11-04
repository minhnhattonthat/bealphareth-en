"""ram_prov.py RAM.bin: which disc data sits where in RAM. Prints RAM range <- file+offset runs. Finds raw (uncompressed) sources."""
import sys
from pathlib import Path

import res

W = 64


def main():
    ram = Path(sys.argv[1]).read_bytes()
    idx = {}
    for i in range(0, len(ram) - W):
        w = ram[i:i + W]
        if len(set(w)) > 8:
            idx.setdefault(hash(w), i)
    srcs = [("MAIN.EXE", (res.ROOT / "work/disc/tree/MAIN.EXE").read_bytes()),
            ("PSX.EXE", (res.ROOT / "work/disc/tree/PSX.EXE").read_bytes()),
            ("SCPS_101.38", (res.ROOT / "work/disc/tree/SCPS_101.38").read_bytes())]
    srcs += [(f"RES#{i}", b) for i, o, s, b in res.entries()]
    hits = []
    for name, b in srcs:
        off = 0
        while off < len(b) - W:
            r = idx.get(hash(b[off:off + W]))
            if r is not None and ram[r:r + W] == b[off:off + W]:
                n = W
                while off + n < len(b) and r + n < len(ram) and b[off + n] == ram[r + n]:
                    n += 1
                k = 0
                while off - k > 0 and r - k > 0 and b[off - k - 1] == ram[r - k - 1]:
                    k += 1
                hits.append((r - k, n + k, name, off - k))
                off += n
            else:
                off += W
    hits.sort()
    for r, n, name, off in hits:
        if n >= 256:
            print(f"{0x80000000 + r:08x} len {n:#8x} <- {name}+{off:#x}")


main()
