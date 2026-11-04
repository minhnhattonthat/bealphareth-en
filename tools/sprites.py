"""sprites.py: English on the sprite sheets inside scene overlays (docs/re/graphics.md rows 7-10, 13-16). Translations in
gfx/sprites/*.json, keyed by sheet id ENTRY+PARTHEX.K; every other sheet in MAIN.RES with the same pixels gets the same edit.

    sprites.py list [ENTRY..]            sheets: id, size, packed bytes, copies
    sprites.py grid OUT.png ID [ID..]    true colours on a dark ground, 16 px grid, for reading boxes
    sprites.py preview OUT.png FILE.json [ID..]  each sheet before and after
    sprites.py check [FILE.json ..]      overflowing boxes, Japanese in text, sheets over their packed size

A file is a list of {"sheet": "5+221d0.0", "blocks": [{"box": [x0, y0, x1, y1], "text": "...", "align": "center", "size": 14,
"bold": true}], "erase": [[x0, y0, x1, y1]]}. A box's pixels all go transparent, then the English is drawn inside it.
The game cuts its sprites from these rectangles, so stay inside the box the Japanese filled."""
import argparse
import glob
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gfx  # noqa: E402
import res  # noqa: E402

FONT = {False: ROOT / "fonts/LiberationSerif-Regular.ttf", True: ROOT / "fonts/LiberationSerif-Bold.ttf"}
SIZE_MIN = 8
JP = re.compile(r"[぀-ヿ一-鿿々]")
MAX_PACK = 0x80
PIECE_GAP = 12
CRISP = 12


def rle_encode(raw):
    """Packed form gfx.rle_decode reads: n<0x80 repeats the next byte n times, n>=0x80 copies 256-n literals."""
    out = bytearray()
    i, n = 0, len(raw)
    lit = bytearray()

    def flush():
        while lit:
            chunk = lit[:MAX_PACK]
            out.append(256 - len(chunk))
            out.extend(chunk)
            del lit[:len(chunk)]

    while i < n:
        j = i
        while j < n and raw[j] == raw[i] and j - i < MAX_PACK - 1:
            j += 1
        if j - i >= 3:
            flush()
            out += bytes([j - i, raw[i]])
        else:
            lit.extend(raw[i:j])
        i = j
    flush()
    return bytes(out)


def rle_exact(raw, size):
    """rle_encode(raw) grown to exactly `size` bytes, so a sheet's stream ends where the original's did, in tokens the originals
    use (runs of 2+, literals of 1+). Runs turn into literals, literals split, until nothing is left to pad."""
    packed = rle_encode(raw)
    spare = size - len(packed)
    if spare < 0:
        raise ValueError(f"{len(packed)} packed bytes in {size}")
    tokens, i = [], 0
    while i < len(packed):
        n = packed[i]
        step = 2 if n < 0x80 else 257 - n
        tokens.append(packed[i:i + step])
        i += step
    out = []
    for t in tokens:
        n = t[0]
        if spare >= 2 and 3 <= n < 0x80:
            m = min(n - 2, spare - 1)  # m literal bytes then a run of n - m: m + 1 bytes more
            out += [bytes([256 - m]) + t[1:2] * m, bytes([n - m]) + t[1:2]]
            spare -= m + 1
        else:
            out.append(t)
    while spare:  # one byte more per split of a literal token with 2+ bytes (header n; n + 1 means one literal fewer)
        for k, t in enumerate(out):
            if t[0] >= 0x80 and len(t) >= 3:
                out[k:k + 1] = [b"\xff" + t[1:2], bytes([t[0] + 1]) + t[2:]]
                spare -= 1
                break
        else:
            raise ValueError(f"cannot grow {len(packed)} packed bytes to {size}")
    return b"".join(out)


def sheets_in(b):
    """Every sprite sheet of a scene overlay: (part offset, index, at, flags, w, h, comp, raw, palette bytes)."""
    if len(b) < 16 or struct.unpack_from("<I", b, 0)[0] != 2:
        return
    sec = struct.unpack_from("<I", b, 12)[0]
    if sec + 12 > len(b):
        return
    n = struct.unpack_from("<I", b, sec + 8)[0]
    if not 0 < n < 400 or sec + 12 + n * 4 > len(b):
        return
    for off in struct.unpack_from(f"<{n}I", b, sec + 12):
        at = sec + 16 + off
        if at + 16 > len(b):
            continue
        yield from sheets_at(b, at, off)


def sheets_at(b, base, off):
    pal_bytes, npal = struct.unpack_from("<II", b, base)
    if pal_bytes < 0x28 or pal_bytes % 8 or not 0 < npal < 64 or 8 + npal * 32 != pal_bytes or base + pal_bytes > len(b):
        return
    pal = b[base + 8:base + pal_bytes]
    at = base + pal_bytes
    k = 0
    while at + 8 <= len(b):
        flags, w, h, _ = struct.unpack_from("<4H", b, at)
        if w == 0 or h == 0 or w > 1024 or h > 512 or w % 4:
            return
        raw = w * h // 2
        if flags & 0x8000:
            comp, rawn = struct.unpack_from("<II", b, at + 8)
            if rawn != raw or at + 8 + comp > len(b):
                return
            comp -= 8  # the field counts itself and the raw size; what follows the stream is the next part's header
            yield off, k, at, flags, w, h, comp, gfx.rle_decode(b[at + 16:at + 16 + comp], raw), pal
            at += 16 + ((comp + 3) & ~3)
        else:
            if at + 8 + raw > len(b):
                return
            yield off, k, at, flags, w, h, None, b[at + 8:at + 8 + raw], pal
            at += 8 + raw
        k += 1


def all_sheets(d, table, only=None):
    """(id, entry, at, w, h, comp, raw, pal, flags) of every sheet in MAIN.RES."""
    for entry, (o, s) in enumerate(table):
        if only and entry not in only:
            continue
        b = bytes(d[o:o + s])
        for off, k, at, flags, w, h, comp, raw, pal in sheets_in(b):
            yield f"{entry}+{off:x}.{k}", entry, at, w, h, comp, raw, pal, flags


def to_indices(w, h, raw):
    a = np.frombuffer(raw, np.uint8)
    px = np.zeros(w * h, np.uint8)
    px[0::2] = a & 15
    px[1::2] = a >> 4
    return px.reshape(h, w)


def from_indices(px):
    f = px.reshape(-1)
    return ((f[0::2] & 15) | (f[1::2] << 4)).astype(np.uint8).tobytes()


def palette_rgb(pal, n=0):
    """16 RGB colours of palette n."""
    v = struct.unpack_from("<16H", pal, n * 32)
    return np.array([[(c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8] for c in v], np.uint8)


def to_rgb(px, pal, ground=(40, 0, 40)):
    rgb = palette_rgb(pal)[px]
    v = struct.unpack_from("<16H", pal)
    transparent = np.array([c == 0 for c in v])[px]
    rgb[transparent] = ground
    return rgb


def font(size, bold):
    return ImageFont.truetype(str(FONT[bold]), size)


def wrap(text, fnt, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = f"{cur} {word}" if cur else word
            if cur and fnt.getlength(trial) > width:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def layout(block):
    """(font, lines, line height, fits) at the largest size up to the block's that fits its box."""
    x0, y0, x1, y1 = block["box"]
    w, h = x1 - x0, y1 - y0
    bold = block.get("bold", False)
    for size in range(block.get("size", 14), SIZE_MIN - 1, -1):
        fnt = font(size, bold)
        lines = wrap(block["text"], fnt, w)
        step = max(size, round(size * 1.1))
        if step * len(lines) <= h + 1 and all(fnt.getlength(s) <= w for s in lines):
            return fnt, lines, step, True
    return fnt, lines, step, False


def ramp(pal, used):
    """The indices the sheet's own lettering uses, dark to bright: a palette's other entries belong to other sprites."""
    rgb = palette_rgb(pal).astype(int)
    v = struct.unpack_from("<16H", pal)
    idx = [i for i in np.unique(used).tolist() if v[i] != 0]
    return sorted(idx, key=lambda i: rgb[i] @ np.array([299, 587, 114]))


def draw_block(px, block, pal, used):
    """Text at the lettering's brightest colour with a dark edge, as the game's has it."""
    x0, y0, x1, y1 = block["box"]
    fnt, lines, step, _ = layout(block)
    h, w = px.shape
    cover = Image.new("L", (w, h), 0)
    edge = Image.new("L", (w, h), 0)
    dc, de = ImageDraw.Draw(cover), ImageDraw.Draw(edge)
    r = ramp(pal, used)
    if block.get("dark"):  # lettering that is dark with a light edge, on parchment: bright ink would vanish into it
        r.reverse()
    small = fnt.size <= CRISP
    if small and len(r) < 6:  # smoothing small text with few greys turns it to mush
        dc.fontmode = de.fontmode = "1"
    top, bottom = fnt.getbbox("H")[1], fnt.getbbox("g")[3] + step * (len(lines) - 1)  # ink, not the line box: a tail stays in
    y = y0 + (y1 - y0 - (bottom - top)) // 2 - top
    for s in lines:
        x = x0 + (x1 - x0 - fnt.getlength(s)) / 2 if block.get("align") == "center" else x0
        dc.text((x, y), s, font=fnt, fill=255)
        de.text((x, y), s, font=fnt, fill=255, stroke_width=1, stroke_fill=255)
        y += step
    c, e = np.array(cover), np.array(edge)
    inside = np.zeros_like(px, bool)
    inside[y0:y1, x0:x1] = True
    if small and len(r) >= 6:  # no edge: it would eat the counters; coverage picks the grey
        level = np.array(r)[np.minimum(c.astype(int) * len(r) // 200, len(r) - 1)]
        px[inside & (c >= 40)] = level[inside & (c >= 40)]
        return px
    px[inside & (e > 96)] = r[0]
    for lo, hi in ((64, 128), (128, 192)):  # two steps of antialias between the dark edge and the ink
        pick = r[len(r) * lo // 256]
        px[inside & (c >= lo) & (c < hi)] = pick
    px[inside & (c >= 192)] = r[-1]
    return px


def edited(px, page, pal):
    out = px.copy()
    for x0, y0, x1, y1 in page.get("erase", []):
        out[y0:y1, x0:x1] = 0
    used = []
    for block in page.get("blocks", []):
        x0, y0, x1, y1 = block["box"]
        used.append(px[y0:y1, x0:x1].ravel())
        out[y0:y1, x0:x1] = 0
    used = np.concatenate(used) if used else px.ravel()
    for block in page.get("blocks", []):
        draw_block(out, {"dark": page.get("dark"), **block}, pal, used)
    return out


def pages(files=None):
    for path in files or sorted(glob.glob(str(ROOT / "gfx/sprites/*.json"))):
        yield from json.loads(Path(path).read_text(encoding="utf8"))


def pack_into(blob, at, flags, comp, raw):
    """Write a sheet's new pixels over the old ones. The packed size may not grow: what follows it does not move."""
    if flags & 0x8000:
        blob[at + 16:at + 16 + comp] = rle_exact(raw, comp)
    else:
        blob[at + 8:at + 8 + len(raw)] = raw


def build_all(main_res, table):
    """Apply every translated sheet to all its copies in MAIN.RES (bytearray). Returns the number of sheets written."""
    wanted = {p["sheet"]: p for p in pages()}
    if not wanted:
        return 0
    by_hash = {}
    copies = []
    for sid, entry, at, w, h, comp, raw, pal, flags in all_sheets(main_res, table):
        key = hashlib.md5(raw).hexdigest()
        copies.append((key, entry, at, w, h, comp, raw, pal, flags))
        if sid in wanted:
            by_hash[key] = wanted.pop(sid)
    if wanted:
        raise ValueError(f"no such sheets: {sorted(wanted)[:10]}")
    n = 0
    for key, entry, at, w, h, comp, raw, pal, flags in copies:
        page = by_hash.get(key)
        if not page:
            continue
        new = from_indices(edited(to_indices(w, h, raw), page, pal))
        o, s = table[entry]
        blob = bytearray(main_res[o:o + s])
        try:
            pack_into(blob, at, flags, comp, new)
        except ValueError as e:
            raise ValueError(f"{page['sheet']} copy in #{entry}: {e}") from None
        main_res[o:o + s] = blob
        n += 1
    return n


def find(d, table, ids):
    want = {s.split("+")[0] for s in ids}
    got = {}
    for sheet in all_sheets(d, table, {int(e) for e in want}):
        if sheet[0] in ids:
            got[sheet[0]] = sheet
    missing = [i for i in ids if i not in got]
    if missing:
        raise SystemExit(f"no such sheets: {missing}")
    return got


def contact(images, out, cols):
    w, h = max(a.shape[1] for _, a in images), max(a.shape[0] for _, a in images)
    rows = (len(images) + cols - 1) // cols
    c = Image.new("RGB", (cols * (w + 4), rows * (h + 14)), (60, 0, 60))
    dr = ImageDraw.Draw(c)
    for i, (label, a) in enumerate(images):
        x, y = (i % cols) * (w + 4), (i // cols) * (h + 14)
        dr.text((x + 2, y + 1), label, fill=(255, 255, 0))
        c.paste(Image.fromarray(a), (x, y + 14))
    c.save(out)


def cmd_list(args):
    d = res.load()
    table = res.table(d)
    seen = {}
    rows = []
    for sid, entry, at, w, h, comp, raw, pal, flags in all_sheets(d, table):
        key = hashlib.md5(raw).hexdigest()
        seen[key] = seen.get(key, 0) + 1
        rows.append((sid, entry, w, h, comp, key))
    for sid, entry, w, h, comp, key in rows:
        if not args.entries or entry in args.entries:
            print(f"{sid}\t{w}x{h}\t{comp}\t{seen[key]}")


def ink_boxes(px, pal):
    """Boxes around the sheet's ink, split where a wide gap or a blank row parts it. The game cuts each piece as its own
    sprite (seen in #235: three exclamations on one row show one at a time)."""
    v = struct.unpack_from("<16H", pal)
    ink = np.array([c != 0 for c in v])[px]
    wide = ndimage.binary_dilation(ink, np.ones((1, PIECE_GAP), bool))
    labels, _ = ndimage.label(wide)
    out = []
    for ys, xs in ndimage.find_objects(labels):
        part = ink[ys, xs]
        cols = np.flatnonzero(part.any(axis=0))
        out.append([xs.start + int(cols[0]), ys.start, xs.start + int(cols[-1]) + 1, ys.stop])
    return sorted(out, key=lambda b: (b[1], b[0]))


def cmd_grid(args):
    d = res.load()
    table = res.table(d)
    got = find(d, table, args.ids)
    images = []
    for sid in args.ids:
        _, _, _, w, h, _, raw, pal, _ = got[sid]
        px = to_indices(w, h, raw)
        boxes = ink_boxes(px, pal)
        print(sid, " ".join(str(b).replace(" ", "") for b in boxes))
        img = Image.fromarray(to_rgb(px, pal)).resize((w * args.zoom, h * args.zoom), Image.NEAREST)
        dr = ImageDraw.Draw(img, "RGBA")
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            dr.rectangle((x0 * args.zoom, y0 * args.zoom, x1 * args.zoom - 1, y1 * args.zoom - 1), outline=(0, 255, 255, 110))
        for x in range(0, w, 16):
            dr.line((x * args.zoom, 0, x * args.zoom, h * args.zoom), fill=(255, 255, 0, 60))
            if x % 32 == 0:
                dr.text((x * args.zoom + 1, 1), str(x), fill=(255, 255, 0))
        for y in range(0, h, 16):
            dr.line((0, y * args.zoom, w * args.zoom, y * args.zoom), fill=(255, 255, 0, 60))
            if y % 32 == 0:
                dr.text((1, y * args.zoom + 1), str(y), fill=(255, 255, 0))
        images.append((sid, np.array(img)))
    contact(images, args.out, args.cols)


def cmd_preview(args):
    d = res.load()
    table = res.table(d)
    wanted = [p for p in pages([args.file]) if not args.ids or p["sheet"] in args.ids]
    got = find(d, table, [p["sheet"] for p in wanted])
    images = []
    for page in wanted:
        _, _, _, w, h, _, raw, pal, _ = got[page["sheet"]]
        px = to_indices(w, h, raw)
        new = edited(px, page, pal)
        z = args.zoom
        for label, a in ((f"{page['sheet']} JP", px), (f"{page['sheet']} EN", new)):
            images.append((label, np.array(Image.fromarray(to_rgb(a, pal)).resize((w * z, h * z), Image.NEAREST))))
    contact(images, args.out, args.cols)


def cmd_check(args):
    d = res.load()
    table = res.table(d)
    plist = list(pages(args.files or None))
    got = find(d, table, [p["sheet"] for p in plist])
    bad = 0
    seen = set()
    for page in plist:
        sid = page["sheet"]
        if sid in seen:
            print(sid, "listed twice")
            bad += 1
        seen.add(sid)
        _, _, _, w, h, comp, raw, pal, flags = got[sid]
        for block in page.get("blocks", []):
            x0, y0, x1, y1 = block["box"]
            if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
                print(sid, "box off the sheet", block["box"])
                bad += 1
                continue
            if JP.search(block["text"]):
                print(sid, "Japanese in text", block["text"][:50])
                bad += 1
            if not layout(block)[3]:
                print(sid, "does not fit", block["box"], block["text"][:50])
                bad += 1
        if flags & 0x8000:
            packed = rle_encode(from_indices(edited(to_indices(w, h, raw), page, pal)))
            if len(packed) > comp:
                print(sid, f"{len(packed)} packed bytes in {comp}")
                bad += 1
    print(f"{len(seen)} sheets, {bad} problems")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("entries", nargs="*", type=int)
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("grid")
    p.add_argument("out")
    p.add_argument("ids", nargs="+")
    p.add_argument("--cols", type=int, default=2)
    p.add_argument("--zoom", type=int, default=2)
    p.set_defaults(fn=cmd_grid)
    p = sub.add_parser("preview")
    p.add_argument("out")
    p.add_argument("file")
    p.add_argument("ids", nargs="*")
    p.add_argument("--cols", type=int, default=2)
    p.add_argument("--zoom", type=int, default=2)
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser("check")
    p.add_argument("files", nargs="*")
    p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
