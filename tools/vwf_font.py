"""vwf_font.py: the English proportional font, kept as ASCII art in fonts/vwf.txt.

Each glyph is 11 rows of up to 8 columns ('#' ink, '.' blank) under a `== <char> <advance>` header; the advance is what
the pen moves after the glyph. `glyphs()` returns the bytes the engine reads: 95 x 11 bytes, one byte per row, MSB left
(slot layout of the game's half-width font, RES#3927 part 0, index c-0x21), and `widths()` one advance per 0x20..0x7E.
`python tools/vwf_font.py init` seeds fonts/vwf.txt from the game's own full-width ASCII cells (ink trimmed, 1 px gap);
never run it over a hand-edited file without --force. `python tools/vwf_font.py sheet OUT.png` draws the font.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "fonts/vwf.txt"
ROWS = 11
SPACE_ADVANCE = 4


def load(path=FONT):
    """{char: (rows [str], advance)} parsed from the art file."""
    out = {}
    cur = None
    for line in path.read_text(encoding="utf8").splitlines():
        if line.startswith("== "):
            head = line[3:]
            ch, adv = head[0], int(head[1:].strip())
            cur = out[ch] = ([], adv)
        elif cur is not None and line.strip():
            cur[0].append(line.strip())
    for ch, (rows, adv) in out.items():
        assert len(rows) == ROWS, f"{ch!r}: {len(rows)} rows"
        assert all(len(r) <= 8 and set(r) <= {"#", "."} for r in rows), f"{ch!r}: bad row"
        ink = max((r.rfind("#") + 1 for r in rows), default=0)
        assert ink <= adv <= 8, f"{ch!r}: ink {ink} wider than advance {adv}"
    missing = [chr(c) for c in range(0x20, 0x7F) if chr(c) not in out]
    assert not missing, f"missing glyphs {missing}"
    return out


def glyphs(font=None):
    """94 glyphs (0x21..0x7E), 11 bytes each."""
    font = font or load()
    out = bytearray()
    for c in range(0x21, 0x7F):
        for row in font[chr(c)][0]:
            out.append(int(row.ljust(8, ".").replace("#", "1").replace(".", "0"), 2))
    return bytes(out)


def widths(font=None):
    """95 advances for 0x20..0x7E."""
    font = font or load()
    return bytes(font[chr(c)][1] for c in range(0x20, 0x7F))


def text_width(text, font=None):
    """Pixel width of plain text in the font."""
    w = widths(font)
    return sum(w[ord(c) - 0x20] for c in text)


def init():
    data = (ROOT / "work/disc/tree/PSX.EXE").read_bytes()
    lines = []
    lines.append(f"== {' '} {SPACE_ADVANCE}")
    lines += ["." * 8] * ROWS
    for i in range(94):
        bits = int.from_bytes(data[0x16B90 + i * 16:0x16B90 + i * 16 + 16], "big")
        rows = [[(bits >> (127 - (r * 11 + c))) & 1 for c in range(11)] for r in range(ROWS)]
        cols = [c for c in range(11) if any(rows[r][c] for r in range(ROWS))]
        a, b = (cols[0], cols[-1]) if cols else (0, 0)
        if b - a + 1 > 7:
            b = a + 6  # shortcut: wide capitals lose their last column here, redraw them by hand in fonts/vwf.txt
        lines.append(f"== {chr(0x21 + i)} {b - a + 2}")
        lines += ["".join("#" if rows[r][c] else "." for c in range(a, b + 1)) for r in range(ROWS)]
    FONT.parent.mkdir(exist_ok=True)
    with open(FONT, "w", encoding="utf8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def sheet(out):
    from PIL import Image
    font = load()
    text = [" ".join(chr(c) for c in range(0x21, 0x50)), " ".join(chr(c) for c in range(0x50, 0x7F)),
            "The quick brown fox jumps over the lazy dog.", "PACK MY BOX WITH FIVE DOZEN LIQUOR JUGS!",
            "\"Well, I'm here,\" she said. (It's 1,234 gold; 56% off?)"]
    im = Image.new("L", (4 + max(text_width(t, font) for t in text), 16 * len(text)), 0)
    y = 0
    for line in text:
        x = 2
        for ch in line:
            rows, adv = font[ch]
            for r, row in enumerate(rows):
                for c, v in enumerate(row):
                    if v == "#":
                        im.putpixel((x + c, y + r), 255)
            x += adv
        y += 16
    im.resize((im.width * 3, im.height * 3), 0).save(out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["init"]:
        if FONT.exists() and "--force" not in sys.argv:
            sys.exit(f"{FONT} exists; --force overwrites hand edits")
        init()
    elif sys.argv[1:2] == ["sheet"]:
        sheet(sys.argv[2])
    else:
        sys.exit(__doc__)
