"""ovdis.py ENTRY RAM_START HEXLEN [RAM_START HEXLEN ..]: disassemble a scene overlay (MAIN.RES entry) at its load address."""
import struct
import sys
from pathlib import Path

import capstone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insert  # noqa: E402
import res  # noqa: E402


def main():
    d = res.load()
    o, s = res.table(d)[int(sys.argv[1])]
    b = d[o:o + s]
    base = insert.SCENE_LOAD[s]
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    args = sys.argv[2:]
    for a, n in zip(args[0::2], args[1::2]):
        a, n = int(a, 16), int(n, 16)
        print(f"--- {a:#x} file {a - base:#x}")
        for i in md.disasm(b[a - base:a - base + n], a):
            print(f"{i.address:08x} {i.mnemonic} {i.op_str}")


if __name__ == "__main__":
    main()
