"""extract.py: extract every text string on the disc into script/*.json.

Sources: MAIN.EXE (the strings its trap/ability table points at), PSX.EXE (the system M4 bank), and every MAIN.RES
scene overlay that holds a message bank (scene scripts). Each source becomes one JSON file in script/, with the strings'
byte offsets so insertion can write them back.

    python tools/extract.py            # write script/ (refuses to clobber translations)
    python tools/extract.py --force    # rewrite, keeping existing "en" fields
    python tools/extract.py --report   # only print what would be written

A string's `jp` is the decoded text (glyphs as Japanese, byte codes as {..} tokens) and
encodes back to the original bytes exactly; tests/test_text.py proves that for every string.
`read` is the same text for a human or translator: glyph tokens the font table can name become their character.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import res  # noqa: E402
import textcodec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script"
DISC = ROOT / "work/disc/tree"
BASE_FONT_OFF = 0x17CE0
BASE_FONT_CELLS = 896
GLYPH_TOKEN = re.compile(r"\{([89a-f][0-9a-f])([89a-f][0-9a-f])\}")
# MAIN.EXE: records of 0x3C bytes whose name (+0) and help (+0x38) words point at the game's only loose text. The two
# text areas are read by nothing else (no other word points there, docs/re/text.md).
MAIN_TABLE = (0x901FC, 0x91624)
MAIN_FILE_BASE = 0x8000F800
MAIN_TEXT = ((0x2D74, 0x3E60), (0x91BDC, 0x91CC0))


# --- glyph table ---------------------------------------------------------------------
def glyph_chars():
    """cell bitmap (121 bytes hex) -> character, from tbl/glyphs.tsv + glyphs_manual.tsv."""
    out = {}
    for name in ("tbl/glyphs.tsv", "tbl/glyphs_manual.tsv"):
        p = ROOT / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1].strip():
                out[parts[0].strip()] = parts[1].strip()
    return out


def cells(blob, off, count):
    import numpy as np
    out = []
    for i in range(count):
        raw = np.frombuffer(blob[off + 16 * i:off + 16 * i + 16], dtype=np.uint8)
        out.append(np.unpackbits(raw)[:121].astype(np.uint8).tobytes().hex())
    return out


def base_kanji(glyphs):
    """{(hi, lo): char} for the 896-cell base font at PSX.EXE 0x17ce0.

    The map is kept one-to-one: a second code whose glyph draws the same character stays
    unmapped, so it decodes to its `{hi lo}` token and still re-encodes exactly.
    """
    blob = (DISC / "PSX.EXE").read_bytes()
    table = cells(blob, BASE_FONT_OFF, BASE_FONT_CELLS)
    out = {}
    used = set()
    for idx, key in enumerate(table):
        ch = glyphs.get(key)
        if ch and ch not in used:
            used.add(ch)
            out[(0x80 + idx // 112, 0x80 + idx % 112)] = ch
    return out


def scene_kanji(glyphs, blob, off, count, base=None):
    """{(hi, lo): char} for a scene font: cell = (hi-0xe0)*112 + (lo-0x80)."""
    table = cells(blob, off, count)
    out = dict(base or {})
    used = set(out.values())
    for idx, key in enumerate(table):
        ch = glyphs.get(key)
        if ch and ch not in used:
            used.add(ch)
            out[(0xE0 + idx // 112, 0x80 + idx % 112)] = ch
    return out


# --- bank scanning -------------------------------------------------------------------
def parse_m4(blob, at):
    """[(kind, start, end)] for an M4 at `at`, or None. kind: 'M2' or 'glyph'."""
    n = struct.unpack_from("<H", blob, at + 2)[0]
    if not 1 <= n <= 400 or at + 4 + 4 * (n + 1) > len(blob):
        return None
    offs = struct.unpack_from(f"<{n + 1}I", blob, at + 4)
    if offs[0] < 4 + 4 * n or any(x > y for x, y in zip(offs, offs[1:])) or at + offs[-1] > len(blob):
        return None
    parts = []
    for k in range(n):
        a, e = at + offs[k], at + offs[k + 1]
        if blob[a:a + 2] == b"M2":
            kind = "M2"
        elif e > a and (e - a) % 16 == 0:
            kind = "glyph"
        else:
            kind = "data"
        parts.append((kind, a, e))
    if all(k == "data" for k, _, _ in parts):
        return None
    return parts


def parse_m2(blob, at, limit):
    n = struct.unpack_from("<H", blob, at + 2)[0]
    if not 1 <= n <= 4000 or at + 4 + 2 * (n + 1) > limit:
        return None
    offs = struct.unpack_from(f"<{n + 1}H", blob, at + 4)
    if offs[0] < 4 + 2 * n or any(x > y for x, y in zip(offs, offs[1:])) or at + offs[-1] > limit:
        return None
    if offs[-1] <= offs[0]:
        return None
    return offs


def find_banks(blob):
    """Every M4 bank and standalone M2 bank, in offset order."""
    found = []
    covered = []
    i = 0
    while True:
        j = blob.find(b"M4", i)
        if j < 0:
            break
        parts = parse_m4(blob, j)
        if parts and any(k == "M2" and parse_m2(blob, a, e) for k, a, e in parts):
            found.append(("M4", j, parts))
            covered.append((j, max(e for _, _, e in parts)))
            i = j + 4
        else:
            i = j + 1
    i = 0
    while True:
        at = blob.find(b"M2", i)
        if at < 0:
            break
        i = at + 2
        if any(s <= at < e for s, e in covered):
            continue
        offs = parse_m2(blob, at, len(blob))
        if not offs:
            continue
        found.append(("M2", at, [("M2", at, at + offs[-1])]))
        covered.append((at, at + offs[-1]))
    return sorted(found, key=lambda b: b[1])


def m2_strings(blob, at, end):
    offs = parse_m2(blob, at, end)
    if not offs:
        return []
    return [(at + offs[k], at + offs[k + 1]) for k in range(len(offs) - 1)]


# --- loose strings -------------------------------------------------------------------
def main_pointers(blob):
    """[(table file offset, string file offset)] of the MAIN.EXE words that point into its text areas."""
    out = []
    for slot in range(MAIN_TABLE[0], MAIN_TABLE[1], 4):
        target = struct.unpack_from("<I", blob, slot)[0] - MAIN_FILE_BASE
        if any(a <= target < e for a, e in MAIN_TEXT):
            out.append((slot, target))
    return out


def main_loose(blob):
    """[(start, end)] of MAIN.EXE's loose strings, NUL included."""
    return [(t, blob.index(b"\0", t) + 1) for t in sorted({t for _, t in main_pointers(blob)})]


# --- extraction ----------------------------------------------------------------------
def doc_codecs(blob, banks, glyphs, base):
    """One codec per bank: an M4's M2 parts use that M4's glyph bank; loose M2 banks use
    the overlay's first glyph bank (a scene keeps one script font). `.cells` is the bank's
    scene font, for `reading`."""
    overlay = None
    for _, _, parts in banks:
        for pkind, a, e in parts:
            if pkind == "glyph":
                overlay = (scene_kanji(glyphs, blob, a, (e - a) // 16, base), cells(blob, a, (e - a) // 16))
                break
        if overlay:
            break
    out = []
    for _, _, parts in banks:
        local, table = overlay or (base, [])
        for pkind, a, e in parts:
            if pkind == "glyph":
                local, table = scene_kanji(glyphs, blob, a, (e - a) // 16, base), cells(blob, a, (e - a) // 16)
        codec = textcodec.Codec(local)
        codec.cells = table
        out.append(codec)
    return out


def reading(text, codec, glyphs):
    """`text` for a human: glyph tokens the font table can name become their character. The exact `jp` must keep them,
    since a one-to-one codec can't give two codes one character."""
    if text is None:
        return None
    def name(m):
        hi, lo = int(m[1], 16), int(m[2], 16)
        if hi >= 0xE0:
            i = (hi - 0xE0) * 112 + lo - 0x80
            key = codec.cells[i] if i < len(codec.cells) else None
        else:
            i = (hi - 0x80) * 112 + lo - 0x80
            key = base_cells()[i] if 0 <= i < BASE_FONT_CELLS else None
        return glyphs.get(key, m[0])
    return GLYPH_TOKEN.sub(name, text)


def base_cells(_memo=[]):
    if not _memo:
        _memo.append(cells((DISC / "PSX.EXE").read_bytes(), BASE_FONT_OFF, BASE_FONT_CELLS))
    return _memo[0]


def source_codec(blob, banks, glyphs, base, bank=0):
    return doc_codecs(blob, banks, glyphs, base)[bank]


def extract_source(name, kind, blob, glyphs, base, entry=None):
    banks = find_banks(blob)
    codecs = doc_codecs(blob, banks, glyphs, base)
    strings = []
    bank_info = []
    for bi, (bkind, at, parts) in enumerate(banks):
        codec = codecs[bi]
        info = {"kind": bkind, "at": at, "parts": []}
        for pi, (pkind, a, e) in enumerate(parts):
            part = {"kind": pkind, "at": a, "size": e - a}
            if pkind == "glyph":
                part["cells"] = (e - a) // 16
            elif pkind == "M2":
                spans = m2_strings(blob, a, e)
                part["strings"] = len(spans)
                for si, (s0, s1) in enumerate(spans):
                    raw = blob[s0:s1 - 1]
                    text = codec.roundtrip(raw) if raw else ""
                    strings.append({
                        "id": f"{name}:{s0:x}",
                        "off": s0,
                        "len": s1 - s0,
                        "bank": f"{bi}.{pi}",
                        "jp": text if text is not None else None,
                        "read": reading(text, codec, glyphs),
                        "raw": None if text is not None else raw.hex(),
                        "en": "",
                        "status": "todo",
                    })
            info["parts"].append(part)
        bank_info.append(info)
    if name == "MAIN.EXE":
        rawcodec = codecs[0] if codecs else textcodec.Codec(base)
        runs = main_loose(blob)
        bank_info.append({"kind": "raw", "at": runs[0][0], "end": runs[-1][1], "runs": len(runs)})
        for s0, s1 in runs:
            raw = blob[s0:s1 - 1]
            text = rawcodec.roundtrip(raw)
            strings.append({
                "id": f"{name}:{s0:x}",
                "off": s0,
                "len": s1 - s0,
                "bank": None,
                "jp": text if text is not None else None,
                "read": reading(text, rawcodec, glyphs),
                "raw": None if text is not None else raw.hex(),
                "en": "",
                "status": "todo",
            })
    strings.sort(key=lambda s: s["off"])
    doc = {
        "source": name,
        "kind": kind,
        "banks": bank_info,
        "strings": strings,
    }
    if entry is not None:
        doc["entry"] = entry
    return doc


def extract_all(glyphs, base):
    """The extraction for every source on the disc (the same list main() writes)."""
    d = res.load()
    docs = []
    for fname in ("MAIN.EXE", "PSX.EXE"):
        blob = (DISC / fname).read_bytes()
        docs.append(extract_source(fname, "exe", blob, glyphs, base))
    for idx, (o, s) in enumerate(res.table(d)):
        if not s:
            continue
        b = d[o:o + s]
        if len(b) < 0x14 or b[:4] != b"\x02\x00\x00\x00":
            continue
        doc = extract_source(f"RES#{idx}", "scene", b, glyphs, base, entry=idx)
        if doc["strings"]:
            docs.append(doc)
    return docs


def slug(name):
    return name.replace("#", "").replace(".", "_").lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    glyphs = glyph_chars()
    base = base_kanji(glyphs)
    docs = extract_all(glyphs, base)

    total = sum(len(doc["strings"]) for doc in docs)
    bad = sum(1 for doc in docs for s in doc["strings"] if s["jp"] is None)
    print(f"sources with text: {len(docs)}, strings: {total}, not decodable: {bad}")
    if args.report:
        for doc in docs[:20]:
            print(doc["source"], len(doc["strings"]))
        return

    SCRIPT.mkdir(exist_ok=True)
    for doc in docs:
        path = SCRIPT / f"{slug(doc['source'])}.json"
        old = {}
        if path.exists():
            if not args.force:
                continue
            try:
                prev = json.loads(path.read_text(encoding="utf-8"))
                old = {s["id"]: s for s in prev.get("strings", [])}
            except Exception:
                old = {}
        for s in doc["strings"]:
            if s["id"] in old:
                s["en"] = old[s["id"]].get("en", "")
                s["status"] = old[s["id"]].get("status", "todo")
                if "tl" in old[s["id"]]:
                    s["tl"] = old[s["id"]]["tl"]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print(f"wrote {len(docs)} files to {SCRIPT}")


if __name__ == "__main__":
    main()
