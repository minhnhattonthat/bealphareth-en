"""loose_scan.py [OUT.tsv]: NUL-terminated katakana names in scene overlays that sit outside every extracted string (boss
gauge labels, RES#32:0x8e70). Prints entry, offset, bytes, text, pointers found in the overlay's own code."""
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import res  # noqa: E402
import textcodec  # noqa: E402

FORM = re.compile(rb"(?<=\x00)\x03[\x20-\x7f]{2,24}(?=\x00)")
KANA = re.compile(r"^[゠-ヿ]{2,}$")


def covered():
    """{entry: [(start, end)]} of what extract.py already holds."""
    out = defaultdict(list)
    for path in (ROOT / "script").glob("res*.json"):
        doc = json.loads(path.read_text(encoding="utf8"))
        entry = int(path.stem[3:])
        for s in doc["strings"]:
            out[entry].append((s["off"], s["off"] + s["len"]))
    return out


def scan(d, table):
    have = covered()
    rows = []
    for entry, (o, s) in enumerate(table):
        b = bytes(d[o:o + s])
        if len(b) < 16 or struct.unpack_from("<I", b, 0)[0] != 2:
            continue
        spans = have.get(entry, [])
        for m in FORM.finditer(b):
            if any(a <= m.start() < e for a, e in spans):
                continue
            text = textcodec.decode(m.group())
            if KANA.match(text):
                rows.append((entry, m.start(), m.group(), text))
    return rows


if __name__ == "__main__":
    d = res.load()
    rows = scan(d, res.table(d))
    lines = [f"{e}\t{o:#x}\t{b.hex()}\t{t}" for e, o, b, t in rows]
    print("\n".join(lines[:60]))
    print(len(rows), "strings in", len({r[0] for r in rows}), "entries;", len({r[3] for r in rows}), "distinct")
    print(sorted({r[3] for r in rows}))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n", encoding="utf8")
