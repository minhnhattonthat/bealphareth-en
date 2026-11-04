"""ramdiff.py A.bin B.bin LO HI [--words]: list differing 32-bit words of two 2 MB RAM dumps in a RAM range (hex addresses)."""
import struct
import sys
from pathlib import Path

a, b = Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes()
lo, hi = int(sys.argv[3], 16) & 0x1FFFFF, int(sys.argv[4], 16) & 0x1FFFFF
for p in range(lo & ~3, hi, 4):
    x, y = struct.unpack_from("<I", a, p)[0], struct.unpack_from("<I", b, p)[0]
    if x != y:
        print(f"{0x80000000 + p:08x} {x:08x} {y:08x}")
