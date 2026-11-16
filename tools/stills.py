"""stills.py: English on the BS still pages (docs/re/graphics.md rows 1-6), translations in gfx/stills/*.json.

    stills.py grid OUT.png ENTRY [ENTRY..]      originals with a 40 px coordinate grid, to read text boxes from
    stills.py preview OUT.png FILE.json [ENTRY..]  each page before and after
    stills.py check [FILE.json ..]              overflowing boxes, leftover Japanese in text, pages over their slot
    stills.py sheets OUTDIR [--per 12 --cols 6] every page's English, paged for visual QA

A file is a list of pages: {"entry": 2700, "blocks": [{"box": [x0, y0, x1, y1], "ink": "light"|"dark", "text": "...",
"align": "left"|"center", "size": 15, "bold": false}], "erase": [{"box": [...], "ink": "light"|"dark"}], "lines":
[[x0, y0, x1, y1]]}. A block's box
is where the Japanese was: it is erased (only text-like pixels, so art under it survives) and the English is wrapped to fit,
shrinking if it must. `erase` blocks only remove. `\\n` in text forces a line. Untouched macroblocks keep their codes."""
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
import bs  # noqa: E402
import res  # noqa: E402

FONT = {False: ROOT / "fonts/LiberationSerif-Regular.ttf", True: ROOT / "fonts/LiberationSerif-Bold.ttf"}
CACHE = ROOT / "work/gfx/stills"
SIZE_DEFAULT, SIZE_MIN = 15, 10
SCALE = 1.6  # a block's size starts this much taller (a half-width page's Japanese stands ~20 px), shrinks to SIZE_MIN px
WIDE = 2  # pages are 320 px shown 640 wide: text is laid out on a canvas this many times wider, then squeezed back
CYAN = (140, 212, 210)  # the cards' stat and effect lines; `{..}` marks a cyan span, a block the Japanese drew all cyan is cyan
CYAN_SHARE = 0.6
LEAD = 1.1  # line step / size: the Japanese stat lines sit about this tight
ERASE_MARGIN = 8
JP = re.compile(r"[぀-ヿ一-鿿々]")
THIN_STEPS = [(1, c) for c in (64, 48, 32, 24, 16, 12, 8, 6, 4, 3, 2, 1)] + [(2, c) for c in (8, 4, 2, 1)]  # (level, from zigzag position): see bs.thin
DEAD_ZONES = (0, 1, 2, 3, 4, 5, 6, 7, 8)  # how hard a page still over its slot drops small coefficients in the touched macroblocks
PLATE_Y, PLATE_W = 46, 112  # item cards: a title box at this y sits on a plate this wide, whatever width its box says
DIM_PAGES = range(3968, 3978)  # the controls pages: pale red and blue text on a soft ground


def font(size, bold):
    return ImageFont.truetype(str(FONT[bold]), size)


def length(fnt, s):
    return fnt.getlength(s.replace("{", "").replace("}", ""))


def cyan_share(rgb, box):
    """Share of the Japanese lettering in the box that is cyan."""
    x0, y0, x1, y1 = box
    r = rgb[y0:y1, x0:x1].astype(int)
    cy = (r[:, :, 1] > r[:, :, 0] + 40) & (r[:, :, 2] > r[:, :, 0] + 40) & (r[:, :, 1] > 120)
    white = (r @ np.array([299, 587, 114]) // 1000 > 150) & ~cy & (r.max(axis=2) - r.min(axis=2) < 50)
    return cy.sum() / max(1, cy.sum() + white.sum())


def text_mask(a, box, ink, dim=False):
    """Text-like pixels of the RGB array inside a box (with a margin: boxes are read by eye), widened over their
    antialiased edge. dim: anything lighter (ink "dark": darker) than its surroundings, for dim or coloured text on a soft
    ground; it takes art in the box with it."""
    x0, y0 = max(box[0] - ERASE_MARGIN, 0), max(box[1] - ERASE_MARGIN, 0)
    x1, y1 = min(box[2] + ERASE_MARGIN, a.shape[1]), min(box[3] + ERASE_MARGIN, a.shape[0])
    region = a[y0:y1, x0:x1].astype(int)
    luma = region @ np.array([299, 587, 114]) // 1000
    chroma = region.max(axis=2) - region.min(axis=2)
    med = np.median(luma)
    cyan = (region[:, :, 1] > region[:, :, 0] + 30) & (region[:, :, 2] > region[:, :, 0] + 30)  # the cards' stat lines
    if dim:
        hit = (1 if ink == "light" else -1) * (luma - ndimage.gaussian_filter(luma.astype(float), 8)) > 10
    else:
        hit = (luma > max(110, med + 45)) & ((chroma < 70) | cyan) if ink == "light" else luma < med - 30
    grown = ndimage.binary_dilation(hit, iterations=2)
    mask = np.zeros(a.shape[:2], bool)
    mask[y0:y1, x0:x1] = grown
    return mask


def inpaint(a, mask):
    """Fill mask from its nearest good pixels, softened so no hard patch shows."""
    if not mask.any():
        return a
    ind = ndimage.distance_transform_edt(mask, return_distances=False, return_indices=True)
    filled = a[tuple(ind)].astype(float)
    soft = np.stack([ndimage.gaussian_filter(filled[:, :, c], 1.2) for c in range(3)], axis=2)
    out = a.copy()
    out[mask] = np.clip(soft[mask], 0, 255).astype(np.uint8)
    return out


def balance(words, fnt, width, count):
    """words in count rows, as even as they will go, so no row is left with a single word when another break would do."""
    best = {(len(words), 0): (0, None)}
    for rows in range(1, count + 1):
        for i in range(len(words) - 1, -1, -1):
            for j in range(i + 1, len(words) + 1):
                row = " ".join(words[i:j])
                n = length(fnt, row)
                if j > i + 1 and n > width:
                    break
                if (j, rows - 1) in best:
                    cost = best[(j, rows - 1)][0] + (width - n) ** 2 + (width ** 2 if j == i + 1 else 0)
                    if (i, rows) not in best or cost < best[(i, rows)][0]:
                        best[(i, rows)] = (cost, j)
    out, i = [], 0
    for rows in range(count, 0, -1):
        j = best[(i, rows)][1]
        out.append(" ".join(words[i:j]))
        i = j
    return out


def wrap(text, fnt, width):
    lines = []
    for para in text.split("\n"):
        rows = []
        cur = ""
        for word in para.split(" "):
            trial = f"{cur} {word}" if cur else word
            if cur and length(fnt, trial) > width:
                rows.append(cur)
                cur = word
            else:
                cur = trial
        rows.append(cur)
        lines += balance(para.split(" "), fnt, width, len(rows)) if len(rows) > 1 else rows
    return lines


def layout(block):
    """(font, lines, line height, fits) at the largest size up to the block's that fits its box."""
    """Widths are on the WIDE canvas."""
    x0, y0, x1, y1 = block["box"]
    w, h = x1 - x0, y1 - y0
    bold = block.get("bold", False)
    top = round(block.get("size", SIZE_DEFAULT) * SCALE)
    if block.get("align") == "center" and y0 == PLATE_Y:
        w = min(w, PLATE_W)
    w *= WIDE
    if block.get("align") == "center":  # a title stays on one line while it can
        for size in range(top, SIZE_MIN - 1, -1):
            fnt = font(size, bold)
            if length(fnt, block["text"]) <= w and "\n" not in block["text"]:
                return fnt, [block["text"]], round(size * LEAD), True
    for size in range(top, SIZE_MIN - 1, -1):
        fnt = font(size, bold)
        lines = wrap(block["text"], fnt, w)
        step = round(size * LEAD)
        if step * len(lines) <= h + 2 and all(length(fnt, s) <= w for s in lines):
            return fnt, lines, step, True
    return fnt, lines, step, False


def draw_block(img, block, cyan=False):
    """Draw on a WIDE canvas, squeeze it back to the page: the screen stretches it out again. cyan: start in cyan."""
    x0, y0, x1, y1 = block["box"]
    fnt, lines, step, _ = layout(block)
    layer = Image.new("RGBA", (img.width * WIDE, img.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    light = block["ink"] == "light"
    y = y0
    if block.get("align") == "center":
        y = y0 + max(0, (y1 - y0 - step * len(lines)) // 2)
    for s in lines:
        x = WIDE * x0 + ((x1 - x0) * WIDE - length(fnt, s)) / 2 if block.get("align") == "center" else WIDE * x0
        for part in re.split(r"([{}])", s):
            if part in ("{", "}"):
                cyan = part == "{"
            if part in ("{", "}", ""):
                continue
            if light:  # outline 1 px each way on the page: WIDE px across on the canvas
                for dx in range(-WIDE, WIDE + 2):
                    for dy in (-1, 0, 1):
                        d.text((x + dx, y + dy), part, font=fnt, fill=(10, 10, 12))
            for dx in range(WIDE):  # stems one page px wider, or the squeeze leaves them grey
                d.text((x + dx, y), part, font=fnt, fill=(CYAN if cyan else (240, 240, 235)) if light else (38, 28, 18))
            x += fnt.getlength(part)
        y += step
    img.alpha_composite(layer.resize(img.size, Image.LANCZOS))


def render(page, rgb):
    """(the page's new RGB image, mask of the new lettering)."""
    a = rgb.copy()
    for block in page.get("erase", []) + page.get("blocks", []):
        dim = block.get("dim", False) or page["entry"] in DIM_PAGES
        a = inpaint(a, text_mask(a, block["box"], block["ink"], dim))
    img = Image.fromarray(a).convert("RGBA")
    for block in page.get("blocks", []):
        whole = "{" not in block["text"] and cyan_share(rgb, block["box"]) >= CYAN_SHARE
        draw_block(img, block, whole)
    for line in page.get("lines", []):  # art an erase took with the text
        ImageDraw.Draw(img).line(line, fill=(190, 190, 190))
    new = np.array(img.convert("RGB"))
    return new, (new != a).any(axis=2)


def encode_page(page, b, slot):
    """(stream, rgb) of a page, within its slot, or raises ValueError. Over the slot, the page's finest detail off the
    lettering goes first: lettering loses thin strokes to a dead zone only as a last resort."""
    y, cb, cr, _ = bs.decode_planes(b)
    rgb = bs.to_rgb(y, cb, cr)
    new, lettering = render(page, rgb)
    changed = (new != rgb).any(axis=2)
    for top, cut in THIN_STEPS:
        out = bs.edit_still(b, new, changed, keep=lettering, cut=cut, top=top)
        if len(out) <= slot:
            return out, new
    for dead in DEAD_ZONES:
        out = bs.edit_still(b, new, changed, dead)
        if len(out) <= slot:
            return out, new
    raise ValueError(f"{page['entry']}: {len(out)} bytes in a {slot} byte slot")


def pages(files=None):
    for path in files or sorted(glob.glob(str(ROOT / "gfx/stills/*.json"))):
        yield from json.loads(Path(path).read_text(encoding="utf8"))


def build_all(main_res, table):
    """Write every translated page into MAIN.RES (bytearray). Streams are cached by page text and source."""
    CACHE.mkdir(parents=True, exist_ok=True)
    fonts = b"".join(p.read_bytes() for p in FONT.values())
    code = hashlib.sha1((Path(__file__).read_bytes() + Path(bs.__file__).read_bytes() + fonts)).hexdigest()
    n = 0
    for page in pages():
        o, s = table[page["entry"]]
        b = bytes(main_res[o:o + s])
        key = hashlib.sha1((code + json.dumps(page, sort_keys=True)).encode() + b).hexdigest()
        cached = CACHE / f"{page['entry']}-{key[:16]}.bs"
        if cached.exists():
            out = cached.read_bytes()
        else:
            out, _ = encode_page(page, b, s)
            for old in CACHE.glob(f"{page['entry']}-*.bs"):
                old.unlink()
            cached.write_bytes(out)
        main_res[o:o + s] = out + bytes(s - len(out))
        n += 1
    return n


def sheet(images, out, cols):
    w, h = images[0][1].shape[1], images[0][1].shape[0]
    rows = (len(images) + cols - 1) // cols
    c = Image.new("RGB", (cols * (w + 4), rows * (h + 16)), (60, 0, 60))
    d = ImageDraw.Draw(c)
    for i, (label, a) in enumerate(images):
        x, y = (i % cols) * (w + 4), (i // cols) * (h + 16)
        d.text((x + 2, y + 2), label, fill=(255, 255, 0))
        c.paste(Image.fromarray(a), (x, y + 16))
    c.save(out)


def original(d, table, entry):
    o, s = table[entry]
    b = bytes(d[o:o + s])
    y, cb, cr, _ = bs.decode_planes(b)
    return b, s, bs.to_rgb(y, cb, cr)


def cmd_grid(args):
    d = res.load()
    table = res.table(d)
    images = []
    for e in args.entries:
        _, _, rgb = original(d, table, e)
        img = Image.fromarray(rgb)
        dr = ImageDraw.Draw(img, "RGBA")
        for x in range(0, 320, 40):
            dr.line((x, 0, x, 480), fill=(255, 255, 0, 70))
            dr.text((x + 1, 1), str(x), fill=(255, 255, 0))
        for y in range(0, 480, 40):
            dr.line((0, y, 320, y), fill=(255, 255, 0, 70))
            dr.text((1, y + 1), str(y), fill=(255, 255, 0))
        images.append((str(e), np.array(img)))
    sheet(images, args.out, args.cols)


def cmd_preview(args):
    d = res.load()
    table = res.table(d)
    images = []
    for page in pages([args.file]):
        if args.entries and page["entry"] not in args.entries:
            continue
        b, s, rgb = original(d, table, page["entry"])
        out, _ = encode_page(page, b, s)
        y, cb, cr, _ = bs.decode_planes(out)
        images += [(f"{page['entry']} JP", rgb), (f"{page['entry']} EN {len(out)}/{s}", bs.to_rgb(y, cb, cr))]
    sheet(images, args.out, args.cols)


def cmd_sheets(args):
    """Every page's English, paged for visual QA."""
    d = res.load()
    table = res.table(d)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plist = list(pages())
    for i in range(0, len(plist), args.per):
        images = []
        for page in plist[i:i + args.per]:
            b, s, _ = original(d, table, page["entry"])
            y, cb, cr, _ = bs.decode_planes(encode_page(page, b, s)[0])
            images.append((str(page["entry"]), bs.to_rgb(y, cb, cr)))
        sheet(images, out / f"stills_{i // args.per + 1:02d}.png", args.cols)


def cmd_check(args):
    d = res.load()
    table = res.table(d)
    bad = 0
    seen = set()
    for page in pages(args.files or None):
        e = page["entry"]
        if e in seen:
            print(e, "listed twice")
            bad += 1
        seen.add(e)
        for block in page.get("blocks", []):
            x0, y0, x1, y1 = block["box"]
            if not (0 <= x0 < x1 <= 320 and 0 <= y0 < y1 <= 480):
                print(e, "box off the page", block["box"])
                bad += 1
                continue
            if JP.search(block["text"]):
                print(e, "Japanese in text", block["text"][:50])
                bad += 1
            if not layout(block)[3]:
                print(e, "does not fit", block["box"], block["text"][:50])
                bad += 1
        try:
            encode_page(page, *original(d, table, e)[:2])
        except ValueError as err:
            print(err)
            bad += 1
    print(f"{len(seen)} pages, {bad} problems")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("grid")
    p.add_argument("out")
    p.add_argument("entries", nargs="+", type=int)
    p.add_argument("--cols", type=int, default=3)
    p.set_defaults(fn=cmd_grid)
    p = sub.add_parser("preview")
    p.add_argument("out")
    p.add_argument("file")
    p.add_argument("entries", nargs="*", type=int)
    p.add_argument("--cols", type=int, default=4)
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser("sheets")
    p.add_argument("out")
    p.add_argument("--per", type=int, default=12)
    p.add_argument("--cols", type=int, default=6)
    p.set_defaults(fn=cmd_sheets)
    p = sub.add_parser("check")
    p.add_argument("files", nargs="*")
    p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
