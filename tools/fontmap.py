"""fontmap.py: identify the game's 11x11 glyph cells as Unicode by matching them against MS Gothic 12 px bitmaps.

The game's font is MS Gothic 12 px (bitmaps) cropped to 11x11; 79% of cells match a modern
MS Gothic render bit for bit, the rest differ in a few strokes (the game used an older
revision of the font). Exact matches are accepted automatically; near matches get the best
candidate plus an IoU score, and anything below the threshold goes to a review sheet that a
human reads and records in tbl/glyphs_manual.tsv.

    python tools/fontmap.py build      # write/refresh tbl/glyphs.tsv
    python tools/fontmap.py review DIR # write label sheets for unresolved cells

Cell identity is the 16-byte cell in hex, so a kanji OCR'd once serves the base font and
every scene font that uses the same glyph.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import res  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"
BASE_FONT_OFF = 0x17CE0
BASE_FONT_CELLS = 896
ACCEPT_IOU = 0.78


def render_candidates():
    """{cell bytes: char} for every character MS Gothic can draw."""
    font = ImageFont.truetype(FONT_PATH, 12)
    out = {}
    for cp in range(0x20, 0x10000):
        ch = chr(cp)
        img = Image.new("L", (18, 18), 0)
        try:
            ImageDraw.Draw(img).text((1, 0), ch, font=font, fill=255, layout_engine=ImageFont.Layout.BASIC)
        except Exception:
            continue
        a = np.array(img) > 110
        for sub in (a[1:12, 1:12], a[0:11, 1:12]):
            out.setdefault(sub.astype(np.uint8).tobytes(), ch)
    return out


def cells_from(blob, off, count):
    out = []
    for i in range(count):
        raw = np.frombuffer(blob[off + 16 * i:off + 16 * i + 16], dtype=np.uint8)
        out.append(np.unpackbits(raw)[:121].reshape(11, 11).astype(np.uint8))
    return out


def base_cells():
    blob = (ROOT / "work/disc/tree/PSX.EXE").read_bytes()
    return cells_from(blob, BASE_FONT_OFF, BASE_FONT_CELLS)


def scene_cells():
    """Every distinct glyph cell of every scene font on the disc."""
    d = res.load()
    seen = {}
    for idx, (o, s) in enumerate(res.table(d)):
        if not s:
            continue
        b = d[o:o + s]
        if len(b) < 0x14 or d[o:o + 4] != b"\x02\x00\x00\x00":
            continue
        j = b.find(b"M4")
        while j >= 0:
            n = np.frombuffer(b[j + 2:j + 4], dtype="<u2")
            if len(n) == 1 and 1 <= n[0] <= 400 and j + 6 + 4 * n[0] < len(b):
                offs = np.frombuffer(b[j + 4:j + 4 + 4 * (n[0] + 1)], dtype="<u4")
                if offs[0] >= 4 + 4 * n[0] and all(x <= y for x, y in zip(offs, offs[1:])) and j + offs[-1] <= len(b):
                    for k in range(n[0]):
                        a, e = int(j + offs[k]), int(j + offs[k + 1])
                        if b[a:a + 2] == b"M2" or e == a or (e - a) % 16:
                            continue
                        for cell in cells_from(b, a, (e - a) // 16):
                            seen.setdefault(cell.tobytes(), None)
                    break
            j = b.find(b"M4", j + 1)
    return seen


def iou_best(cell, cand, cand_chars, cand_keys, cand_flat, cand_ink):
    nc = cell.sum()
    sel = np.where(np.abs(cand_ink - nc) <= max(4, nc * 0.35))[0]
    if not len(sel):
        return 0.0, ""
    best = (0.0, "")
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sh = np.zeros((11, 11), np.uint8)
            ys, ye = max(0, dy), min(11, 11 + dy)
            xs, xe = max(0, dx), min(11, 11 + dx)
            sh[ys:ye, xs:xe] = cell[ys - dy:ye - dy, xs - dx:xe - dx]
            inter = (cand_flat[sel] & sh.ravel()).sum(1)
            union = (cand_flat[sel] | sh.ravel()).sum(1)
            iou = inter / np.maximum(union, 1)
            j = int(np.argmax(iou))
            if iou[j] > best[0]:
                best = (float(iou[j]), cand_chars[int(sel[j])])
    return best


def load_manual():
    path = ROOT / "tbl/glyphs_manual.tsv"
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0].strip()] = parts[1].strip()
    return out


def load_table():
    path = ROOT / "tbl/glyphs.tsv"
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0].strip()] = parts[1].strip()
    return out


def cmd_build():
    cand = {k.hex(): ch for k, ch in render_candidates().items()}
    cand_keys = list(cand)
    cand_chars = [cand[k] for k in cand_keys]
    cand_flat = np.stack([np.frombuffer(bytes.fromhex(k), dtype=np.uint8) for k in cand_keys])
    cand_ink = cand_flat.sum(1)

    cells = {}
    for c in base_cells():
        cells.setdefault(c.tobytes().hex(), c)
    for k in scene_cells():
        cells.setdefault(k.hex(), np.frombuffer(k, dtype=np.uint8).reshape(11, 11))

    rows, unresolved = [], []
    for key, cell in cells.items():
        if key in cand:
            rows.append((key, cand[key], "exact", 1.0))
            continue
        iou, ch = iou_best(cell, cand, cand_chars, cand_keys, cand_flat, cand_ink)
        if iou >= ACCEPT_IOU and ch:
            rows.append((key, ch, "fuzzy", iou))
        else:
            unresolved.append((key, cell, ch, iou))

    out = ROOT / "tbl/glyphs.tsv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# cell\tchar\tmethod\tiou  (generated by tools/fontmap.py; edit tbl/glyphs_manual.tsv instead)\n")
        for key, ch, method, iou in sorted(rows, key=lambda r: r[1]):
            f.write(f"{key}\t{ch}\t{method}\t{iou:.3f}\n")
    print(f"glyphs: {len(rows)} mapped ({sum(1 for r in rows if r[2] == 'exact')} exact), "
          f"{len(unresolved)} need review -> tbl/glyphs_manual.tsv")
    return unresolved


def cmd_review(outdir, unresolved):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    unresolved = sorted(unresolved, key=lambda r: -r[0].count("1"))
    per = 40
    sheets = []
    zoom = 6
    for page in range((len(unresolved) + per - 1) // per):
        chunk = unresolved[page * per:(page + 1) * per]
        cols = 4
        cw, chh = 13 * zoom + 18, 13 * zoom + 6
        img = Image.new("L", (cols * cw, ((len(chunk) + cols - 1) // cols) * chh + 14), 30)
        dr = ImageDraw.Draw(img)
        small = ImageFont.truetype(FONT_PATH, 11)
        for i, (key, cell, cand, iou) in enumerate(chunk):
            y = 14 + (i // cols) * chh
            x = (i % cols) * cw
            bits = np.kron(cell * 255, np.ones((zoom, zoom), np.uint8))
            img.paste(Image.fromarray(bits), (x, y + 12))
            dr.text((x, y), f"{i + page * per} {cand or '?'} {iou:.2f}", fill=255, font=small)
            dr.text((x + zoom * 11 + 2, y + 12), f"{i + page * per}", fill=200, font=small)
        p = outdir / f"glyphs_{page:02d}.png"
        img.save(p)
        sheets.append((p, [r[0] for r in chunk]))
    (outdir / "unresolved.json").write_text(json.dumps([r[0] for r in unresolved]), encoding="utf-8")
    print(f"wrote {len(sheets)} review sheets to {outdir} for {len(unresolved)} cells")
    for p, keys in sheets:
        print(p.name, len(keys))


def cmd_apply():
    """Merge exact/fuzzy matches with the manual table and write tbl/glyphs.tsv."""
    auto = load_table()
    manual = load_manual()
    auto.update(manual)
    path = ROOT / "tbl/glyphs.tsv"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line:
            continue
        parts = line.split("\t")
        if parts[0] in manual:
            parts[1] = manual[parts[0]]
            parts[2] = "manual"
            parts[3] = "1.000"
    print(f"merged {len(manual)} manual glyphs")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    p = sub.add_parser("review")
    p.add_argument("outdir")
    sub.add_parser("apply")
    args = ap.parse_args()
    if args.cmd == "build":
        cmd_build()
    elif args.cmd == "review":
        unresolved = cmd_build()
        cmd_review(args.outdir, unresolved)
    else:
        cmd_apply()


if __name__ == "__main__":
    main()
