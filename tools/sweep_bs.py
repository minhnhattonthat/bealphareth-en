"""sweep_bs.py OUTDIR [workers]: decode every BS still in MAIN.RES to OUTDIR/<entry>.png (luma) and half-size contact sheets labelled by entry; logs dims."""
import sys
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw

import bs
import res


def one(job):
    idx, b, out = job
    px, w, h, n = bs.image(b)
    if px.size:
        Image.fromarray(px).save(Path(out) / f"{idx}.png")
    return idx, len(b), n, w, h


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    jobs = [(i, b, str(out)) for i, o, s, b in res.entries() if b[2:4] == b"\x00\x38"]
    with Pool(workers) as p, open(out / "dims.tsv", "w") as log:
        for idx, size, n, w, h in p.imap(one, jobs):
            print(idx, size, n, w, h, sep="\t", file=log, flush=True)
    COLS, ROWS, TW, TH = 12, 4, 160, 240
    names = sorted((int(p.stem) for p in out.glob("*.png") if p.stem.isdigit()))
    for sheet, start in enumerate(range(0, len(names), COLS * ROWS)):
        c = Image.new("L", (COLS * (TW + 3), ROWS * (TH + 11)), 30)
        dr = ImageDraw.Draw(c)
        for k, idx in enumerate(names[start:start + COLS * ROWS]):
            im = Image.open(out / f"{idx}.png")
            im.thumbnail((TW, TH), Image.BILINEAR)
            x, y = (k % COLS) * (TW + 3), (k // COLS) * (TH + 11)
            c.paste(im, (x, y + 10))
            dr.text((x + 1, y - 1), str(idx), fill=255)
        c.save(out / f"sheet_{sheet:02d}.png")
    print("done", len(names))


if __name__ == "__main__":
    main()
