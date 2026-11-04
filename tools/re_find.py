"""re_find.py HEX [RAM.bin]: find a byte pattern in a RAM dump and in MAIN.RES entries / executables; print context."""
import sys
from pathlib import Path

import res

pat = bytes.fromhex(sys.argv[1])
ram = Path(sys.argv[2]).read_bytes() if len(sys.argv) > 2 else b""
i = -1
n = 0
while ram and (i := ram.find(pat, i + 1)) >= 0 and n < 40:
    print(f"RAM {0x80000000 + i:08x} {ram[max(0, i - 8):i + 32].hex(' ')}")
    n += 1
print("ram hits", n)
for name in ("MAIN.EXE", "PSX.EXE", "SCPS_101.38"):
    b = (res.ROOT / "work/disc/tree" / name).read_bytes()
    i = -1
    while (i := b.find(pat, i + 1)) >= 0:
        print(name, hex(i), b[i:i + 24].hex(" "))
n = 0
for idx, o, s, b in res.entries():
    i = -1
    while (i := b.find(pat, i + 1)) >= 0:
        n += 1
        if n <= 40:
            print(f"RES #{idx} @{o:#x}+{i:#x} {b[max(0, i - 8):i + 32].hex(' ')}")
print("res hits", n)
