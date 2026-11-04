"""glyph_review.py [--out DIR]: every cell the font OCR is unsure of (fuzzy or unnamed), with its uses in context and a
zoomed bitmap sheet, so a reader can settle it in tbl/glyphs_manual.tsv (then `tools/extract.py --force`).

Writes DIR/cells.txt (`index  cell  guess  iou  uses  context | context`, the cell shown as ⟦guess⟧) and DIR/sheet_NN.png
(bitmaps labelled by the same index).
"""
import argparse
import collections
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import res  # noqa: E402
import textcodec  # noqa: E402

BARE = textcodec.Codec({})
CONTEXTS = 3
PER_SHEET = 80
ZOOM = 4


def table():
    rows = {}
    for line in (ROOT / "tbl/glyphs.tsv").read_text(encoding="utf8").splitlines():
        if line and not line.startswith("#"):
            p = line.split("\t")
            rows[p[0]] = (p[1], p[2], p[3]) if len(p) >= 4 else ("", "unknown", "0")
    return rows


def uses(docs, glyphs):
    """cell -> [uses, contexts]; every two-byte glyph of every string, whatever the codec named it."""
    d = res.load()
    blobs = {"MAIN.EXE": (extract.DISC / "MAIN.EXE").read_bytes(), "PSX.EXE": (extract.DISC / "PSX.EXE").read_bytes()}
    tab = res.table(d)
    found = collections.defaultdict(lambda: [0, []])
    for doc in docs:
        src = doc["source"]
        if src in blobs:
            blob = blobs[src]
        else:
            o, s = tab[doc["entry"]]
            blob = d[o:o + s]
        codecs = extract.doc_codecs(blob, extract.find_banks(blob), glyphs, extract.base_kanji(glyphs))
        for s in doc["strings"]:
            if s["jp"] is None:
                continue
            bank = int(s["bank"].split(".")[0]) if s["bank"] else 0
            font = codecs[bank].cells if codecs else []
            def cell(m):
                hi, lo = int(m[1], 16), int(m[2], 16)
                if hi >= 0xE0:
                    i = (hi - 0xE0) * 112 + lo - 0x80
                    return font[i] if i < len(font) else None
                i = (hi - 0x80) * 112 + lo - 0x80
                return extract.base_cells()[i] if 0 <= i < extract.BASE_FONT_CELLS else None
            text = BARE.roundtrip(blob[s["off"]:s["off"] + s["len"] - 1])
            if text is None:
                continue
            parts = extract.GLYPH_TOKEN.split(text)  # text, hi, lo, text, hi, lo, ...
            keys = [cell(re.match(r"(..)(..)", parts[k] + parts[k + 1])) for k in range(1, len(parts), 3)]
            shown = [glyphs.get(k, "□") for k in keys]
            for n, key in enumerate(keys):
                rec = found[key]
                rec[0] += 1
                if len(rec[1]) < CONTEXTS:
                    left = "".join(parts[3 * j] + shown[j] for j in range(n)) + parts[3 * n]
                    right = parts[3 * n + 3] + "".join(shown[j] + parts[3 * j + 3] for j in range(n + 1, len(shown)))
                    ctx = re.sub(r"\{[^}]*\}|\s", "", left)[-9:] + "⟦" + shown[n] + "⟧" + re.sub(r"\{[^}]*\}|\s", "", right)[:9]
                    if ctx not in rec[1]:
                        rec[1].append(ctx)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="work/qa/glyphs")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    glyphs = extract.glyph_chars()
    docs = extract.extract_all(glyphs, extract.base_kanji(glyphs))
    found = uses(docs, glyphs)
    tab = table()
    manual = ROOT / "tbl/glyphs_manual.tsv"
    settled = {ln.split("\t")[0] for ln in manual.read_text(encoding="utf8").splitlines()} if manual.exists() else set()
    todo = []
    for key, (n, ctx) in found.items():
        if key is None:
            continue
        ch, method, iou = tab.get(key, ("", "unknown", "0"))
        if key in glyphs and method == "exact" or key in settled:
            continue
        todo.append((key, glyphs.get(key, ""), iou, n, ctx))
    todo.sort(key=lambda r: -r[3])
    lines = []
    for i, (key, ch, iou, n, ctx) in enumerate(todo):
        lines.append(f"{i}\t{key}\t{ch or '?'}\t{iou}\t{n}\t{' | '.join(ctx)}")
    (out / "cells.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    for page in range(0, len(todo), PER_SHEET):
        rows = todo[page:page + PER_SHEET]
        im = Image.new("L", (10 * 70, 8 * 62), 40)
        dr = ImageDraw.Draw(im)
        for j, (key, *_rest) in enumerate(rows):
            x, y = (j % 10) * 70, (j // 10) * 62
            bits = bytes.fromhex(key)
            for r in range(11):
                for c in range(11):
                    if bits[r * 11 + c]:
                        dr.rectangle((x + 8 + c * ZOOM, y + 12 + r * ZOOM, x + 8 + c * ZOOM + ZOOM - 1, y + 12 + r * ZOOM + ZOOM - 1), fill=255)
            dr.text((x + 2, y), str(page + j), fill=160)
        im.save(out / f"sheet_{page // PER_SHEET:02}.png")
    print(len(todo), "cells;", out / "cells.txt")


if __name__ == "__main__":
    main()
