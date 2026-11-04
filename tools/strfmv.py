"""strfmv.py: English subtitles in the FMVs (docs/re/graphics.md row 11). Timed lines in gfx/fmv/NAME.json.

    strfmv.py info NAME                   frame count, sectors per frame, bytes per frame
    strfmv.py sheet OUT.png NAME FROM TO [--step N] [--crop X,Y,W,H]    frames with their numbers
    strfmv.py preview OUT.png NAME FRAME [FRAME..]      frames from the English file, before and after

A dumped .STR is 2336-byte sectors: 8 subheader, then video = 32 header (magic 0x80010160, u16 sector, u16 count, u32 frame,
u32 size, u16 w, h, ...) + 2016 data. Audio sectors stay. A frame keeps its sectors, so a new frame must fit them.
File: {"box": [x0, y0, x1, y1], "lines": [{"from": F, "to": T, "text": "..."}]}. `box` is the band the Japanese sits in."""
import argparse
import hashlib
import json
import multiprocessing as mp
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bs  # noqa: E402
import stills  # noqa: E402

TREE = ROOT / "work/disc/tree/STR"
FADE, PAD = 12, 10  # frames
CACHE = ROOT / "work/gfx/fmv"
FONT = ROOT / "fonts/LiberationSerif-Regular.ttf"
SECTOR, HEAD, DATA, SUB = 2336, 32, 2016, 8
MAGIC = 0x80010160
MB_H = 15
DEAD_ZONES = (0, 1, 2, 3, 5, 8, 12, 20)


def frames(blob):
    """{frame number: [(sector index, part)]} of the video sectors, in order."""
    out = {}
    for i in range(0, len(blob) // SECTOR):
        at = i * SECTOR + SUB
        magic, part, count, num = struct.unpack_from("<IHHI", blob, at)
        if magic == MAGIC:
            out.setdefault(num, []).append((i, part, count))
    return out


def frame_data(blob, sectors):
    return b"".join(blob[i * SECTOR + SUB + HEAD:i * SECTOR + SUB + HEAD + DATA] for i, _, _ in sectors)


def to_image(b):
    y, cb, cr, _ = bs.decode_planes(b, MB_H)
    return bs.to_rgb(y, cb, cr)


def load_spec(name):
    """The English file, each line padded over the faint ends of the Japanese fade (the times come from an edge
    threshold), never past the midpoint of the gap to its neighbour."""
    spec = json.loads((ROOT / f"gfx/fmv/{name}.json").read_text(encoding="utf8"))
    lines = spec["lines"]
    for a, b in zip(lines, lines[1:]):
        gap = b["from"] - a["to"] - 1
        pad = min(PAD, gap // 2)
        a["to"] += pad
        b["from"] -= min(PAD, gap - pad)
    lines[0]["from"] = max(1, lines[0]["from"] - PAD)
    lines[-1]["to"] += PAD
    return spec


def line_at(spec, f):
    for line in spec["lines"]:
        if line["from"] <= f <= line["to"]:
            return line
    return None


def text_mask(rgb, box):
    """Where a subtitle's Japanese sits, from a frame at its full strength: bright, unsaturated pixels above their
    surroundings, widened over the dark edge. The text holds still, so one mask serves all the line's frames."""
    x0, y0, x1, y1 = box
    region = rgb[y0:y1, x0:x1].astype(float)
    luma = region @ np.array([0.299, 0.587, 0.114])
    hit = luma - ndimage.gaussian_filter(luma, 10) > 25
    mask = np.zeros(rgb.shape[:2], bool)
    mask[y0:y1, x0:x1] = ndimage.binary_dilation(hit, iterations=3)
    return mask


def draw_line(a, spec, line, alpha):
    """White serif with a dark edge, centred in the band, faded in and out as the Japanese was."""
    x0, y0, x1, y1 = spec["box"]
    for size in range(14, 8, -1):
        fnt = ImageFont.truetype(str(FONT), size)
        rows, cur = [], ""
        for word in line["text"].split(" "):
            trial = f"{cur} {word}" if cur else word
            if cur and fnt.getlength(trial) > x1 - x0:
                rows.append(cur)
                cur = word
            else:
                cur = trial
        rows.append(cur)
        if len(rows) * (size + 2) <= y1 - y0:
            break
    h, w = a.shape[:2]
    ink, edge = Image.new("L", (w, h), 0), Image.new("L", (w, h), 0)
    di, de = ImageDraw.Draw(ink), ImageDraw.Draw(edge)
    y = y0 + (y1 - y0 - len(rows) * (size + 2)) // 2
    for s in rows:
        x = x0 + (x1 - x0 - fnt.getlength(s)) / 2
        de.text((x, y), s, font=fnt, fill=255, stroke_width=1, stroke_fill=255)
        di.text((x, y), s, font=fnt, fill=255)
        y += size + 2
    out = a.astype(float)
    ae = (np.array(edge, float) / 255 * alpha * 0.85)[..., None]
    out = out * (1 - ae)
    ai = (np.array(ink, float) / 255 * alpha)[..., None]
    out = out * (1 - ai) + 238 * ai
    return np.clip(out, 0, 255).astype(np.uint8)


def edited(spec, rgb, line, mask, f):
    """The frame with the Japanese painted out and the English drawn."""
    a = stills.inpaint(rgb, mask)
    alpha = min(1.0, (f - line["from"] + 1) / FADE, (line["to"] - f + 1) / FADE)
    return draw_line(a, spec, line, alpha)


def encode(args):
    """One frame's new stream."""
    b, spec, f, room, mask = args
    line = line_at(spec, f)
    rgb = to_image(b)
    new = edited(spec, rgb, line, mask, f)
    changed = (new != rgb).any(axis=2)
    for dead in DEAD_ZONES:
        out = bs.edit_still(b, new, changed, dead, MB_H)
        if len(out) <= room:
            return f, out
    raise ValueError(f"frame {f}: {len(out)} bytes in {room}")


def line_mask(blob, table, spec, line):
    mid = (line["from"] + line["to"]) // 2
    return text_mask(to_image(frame_data(blob, table[mid])), spec["box"])


def patch(name, blob):
    """The .STR with its English frames. Results cached by the spec and tool source."""
    spec = load_spec(name)
    code = hashlib.sha1(Path(__file__).read_bytes() + Path(bs.__file__).read_bytes() + FONT.read_bytes() + json.dumps(spec, sort_keys=True).encode()).hexdigest()
    cached = CACHE / f"{name}-{code[:16]}.str"
    if cached.exists():
        return cached.read_bytes()
    table = frames(blob)
    jobs = []
    for line in spec["lines"]:
        mask = line_mask(blob, table, spec, line)
        for f in range(line["from"], line["to"] + 1):
            jobs.append((frame_data(blob, table[f]), spec, f, len(table[f]) * DATA, mask))
    out = bytearray(blob)
    with mp.Pool() as pool:
        for f, new in pool.imap_unordered(encode, jobs, chunksize=4):
            sectors = table[f]
            data = new + bytes(len(sectors) * DATA - len(new))
            for k, (i, _, _) in enumerate(sectors):
                at = i * SECTOR + SUB
                out[at + HEAD:at + HEAD + DATA] = data[k * DATA:(k + 1) * DATA]
                struct.pack_into("<I", out, at + 12, len(new))
                out[at + 20:at + 28] = new[:8]  # the stream's header is repeated in the sector header
    CACHE.mkdir(parents=True, exist_ok=True)
    for old in CACHE.glob(f"{name}-*.str"):
        old.unlink()
    cached.write_bytes(out)
    return bytes(out)


def cmd_info(args):
    blob = (TREE / f"{args.name}.STR").read_bytes()
    t = frames(blob)
    counts = {}
    for sectors in t.values():
        counts[len(sectors)] = counts.get(len(sectors), 0) + 1
    print(f"{len(blob) // SECTOR} sectors, {len(t)} frames {min(t)}..{max(t)}, sectors per frame {sorted(counts.items())}")
    f = min(t)
    head = struct.unpack_from("<IHHIIHH", blob, t[f][0][0] * SECTOR + SUB)
    data = frame_data(blob, t[f])
    levels, bits = bs.parse_levels(data, MB_H)
    print("first header", [hex(v) for v in head], "stream bytes", bits // 8, "blocks", len(levels), "head", data[:8].hex())


def band_energy(args):
    b, y0, y1 = args
    y, _, _, _ = bs.decode_planes(b, MB_H)
    band = y[y0:y1]
    return float((np.abs(np.diff(band, axis=1)) > 40).mean())


def cmd_scan(args):
    """Share of sharp horizontal edges in the subtitle band, per frame: lines show as plateaus, for timing them."""
    blob = (TREE / f"{args.name}.STR").read_bytes()
    t = frames(blob)
    jobs = [(frame_data(blob, t[f]), args.y0, args.y1) for f in sorted(t)]
    with mp.Pool() as pool:
        e = pool.map(band_energy, jobs, chunksize=16)
    for f, v in zip(sorted(t), e):
        print(f, f"{v:.4f}")


def cmd_sheet(args):
    blob = (TREE / f"{args.name}.STR").read_bytes()
    t = frames(blob)
    crop = [int(v) for v in args.crop.split(",")] if args.crop else None
    shots = []
    for f in range(args.first, args.last + 1, args.step):
        if f in t:
            a = to_image(frame_data(blob, t[f]))
            if crop:
                a = a[crop[1]:crop[1] + crop[3], crop[0]:crop[0] + crop[2]]
            shots.append((f, a))
    w, h = shots[0][1].shape[1], shots[0][1].shape[0]
    rows = (len(shots) + args.cols - 1) // args.cols
    c = Image.new("RGB", (args.cols * (w + 2), rows * (h + 12)), (60, 0, 60))
    d = ImageDraw.Draw(c)
    for i, (f, a) in enumerate(shots):
        x, y = (i % args.cols) * (w + 2), (i // args.cols) * (h + 12)
        d.text((x + 1, y), str(f), fill=(255, 255, 0))
        c.paste(Image.fromarray(a), (x, y + 12))
    c.save(args.out)


def cmd_preview(args):
    blob = (TREE / f"{args.name}.STR").read_bytes()
    spec = load_spec(args.name)
    t = frames(blob)
    shots = []
    for f in args.frames:
        b = frame_data(blob, t[f])
        rgb = to_image(b)
        line = line_at(spec, f)
        new = None
        if line:
            _, new = encode((b, spec, f, len(t[f]) * DATA, line_mask(blob, t, spec, line)))
        shots += [(f"{f} JP", rgb), (f"{f} EN", to_image(new) if new else rgb)]
    c = Image.new("RGB", (2 * 322, (len(shots) // 2) * 252), (60, 0, 60))
    d = ImageDraw.Draw(c)
    for i, (label, a) in enumerate(shots):
        x, y = (i % 2) * 322, (i // 2) * 252
        d.text((x + 1, y), label, fill=(255, 255, 0))
        c.paste(Image.fromarray(a), (x, y + 12))
    c.save(args.out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("name")
    p.set_defaults(fn=cmd_info)
    p = sub.add_parser("scan")
    p.add_argument("name")
    p.add_argument("y0", type=int)
    p.add_argument("y1", type=int)
    p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("sheet")
    p.add_argument("out")
    p.add_argument("name")
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--step", type=int, default=30)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--crop")
    p.set_defaults(fn=cmd_sheet)
    p = sub.add_parser("preview")
    p.add_argument("out")
    p.add_argument("name")
    p.add_argument("frames", nargs="+", type=int)
    p.set_defaults(fn=cmd_preview)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
