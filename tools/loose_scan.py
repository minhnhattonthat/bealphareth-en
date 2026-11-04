"""loose_scan.py [OUT.tsv]: Japanese names in scene overlays outside every extracted string, reached by a data word (object
tables: 0x3C stride, name at +0; the boss gauge reads these, RES#32:0x8e70). Prints entry, offset, pointer offset, text."""
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

JP = re.compile(r"[ぁ-ヿ一-鿿]")
MAP_RAM, SUB_RAM = 0x800D6C00, 0x80136C00


def covered():
    """{entry: [(start, end)]} of what extract.py already holds."""
    out = defaultdict(list)
    for path in (ROOT / "script").glob("res*.json"):
        doc = json.loads(path.read_text(encoding="utf8"))
        for s in doc["strings"]:
            out[doc["entry"]].append((s["off"], s["off"] + s["len"]))
    return out


def word_refs(b, ram):
    """{target offset: [word offset]} for data words pointing into this overlay, up to section 2."""
    sec2 = struct.unpack_from("<I", b, 12)[0]
    out = defaultdict(list)
    for i in range(0x10, min(sec2, len(b) - 4), 4):
        w = struct.unpack_from("<I", b, i)[0]
        if ram <= w < ram + len(b):
            out[w - ram].append(i)
    return out


def name_at(b, off):
    """The string at off, if it starts with a mode byte and decodes to short text."""
    if b[off] not in (2, 3):
        return None
    end = b.find(b"\0", off)
    if end < 0 or end - off > 40:
        return None
    try:
        text = textcodec.decode(b[off:end])
    except (KeyError, IndexError, ValueError):
        return None
    text = re.sub(r"\{0[123]\}", "", text)
    return text if len(text) >= 2 and JP.search(text) and "{" not in text else None


def scan(d, table):
    have = covered()
    rows = []
    for entry, (o, s) in enumerate(table):
        b = bytes(d[o:o + s])
        if len(b) < 16 or struct.unpack_from("<I", b, 0)[0] != 2:
            continue
        spans = have.get(entry, [])
        ram = SUB_RAM if s == 0x40000 else MAP_RAM
        for off, words in sorted(word_refs(b, ram).items()):
            if any(a <= off < e for a, e in spans):
                continue
            text = name_at(b, off)
            if text:
                rows.append((entry, off, words, text))
    return rows


if __name__ == "__main__":
    d = res.load()
    rows = scan(d, res.table(d))
    lines = [f"{e}\t{o:#x}\t{','.join(hex(w) for w in ws)}\t{t}" for e, o, ws, t in rows]
    print(len(rows), "strings in", len({r[0] for r in rows}), "entries;", len({r[3] for r in rows}), "distinct")
    print("\n".join(sorted({r[3] for r in rows})))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text("\n".join(lines) + "\n", encoding="utf8")
