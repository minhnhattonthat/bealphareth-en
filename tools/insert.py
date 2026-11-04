"""insert.py: put new text into the game's files; docs/re/vwf.md has the layout rules.

Each source JSON (script/*.json) maps to one blob: a scene overlay in MAIN.RES, RES#3927 for PSX.EXE's system bank, or
MAIN.EXE's loose strings (in place, length fixed). A string's new bytes come from its `en`, or from `marker()` in a
marker build. Unchanged strings keep their exact bytes, so rebuilding with no new text gives the original blob.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textcodec  # noqa: E402
import vwf_font  # noqa: E402

SYSTEM_RES = 3927
SYSTEM_DELTA = 0x15F94  # PSX.EXE offset of the block RES#3927 holds
SYSTEM_SIZE = 0x12640  # bytes PSX.EXE copies to 0x801B9000 at boot (0x800D5D1C, length at 0x800FE54C); boot data follows
M2_MAX = 0xFFFF  # M2 offsets are u16

TOKEN = re.compile(r"\{[^{}]*\}")
GLYPH_TOKEN = re.compile(r"\{([89a-f][0-9a-f]{3})\}")
PLATE = "【】"  # name-plate frames (base font 87ac/87ad): English keeps them, the codec finds them in every scene
FILLER = "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. "


class Overflow(ValueError):
    pass


def split_runs(jp):
    """[(is_text, piece)] of a decoded string: text is glyphs and glyph tokens, the rest is control codes, \\n and |."""
    out = []
    i = 0
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            out.append((True, buf))
            buf = ""

    while i < len(jp):
        ch = jp[i]
        if ch == "{":
            m = TOKEN.match(jp, i)
            g = GLYPH_TOKEN.fullmatch(m.group())
            if g and not g.group(1).startswith("9f"):
                buf += m.group()
            elif m.group() in ("{01}", "{02}", "{03}"):
                pass
            else:
                flush()
                out.append((False, m.group()))
            i = m.end()
        elif ch in "\n|" + PLATE:
            flush()
            out.append((False, ch))
            i += 1
        else:
            buf += ch
            i += 1
    flush()
    return out


def jp_px(text):
    """Pixels the Japanese run took: 12 per full glyph, 6 per one-byte Latin glyph or space."""
    plain = GLYPH_TOKEN.sub("あ", text)
    return sum(6 if c.isascii() else 12 for c in plain)


def fill_to(px, start, font):
    w = vwf_font.widths(font)
    out = ""
    i = start
    while True:
        ch = FILLER[i % len(FILLER)]
        adv = w[ord(ch) - 0x20]
        if adv > px:
            return out, i
        out += ch
        px -= adv
        i += 1


def marker(jp, tag, fill=1.0, font=None):
    """The string's control codes with its text replaced by `[tag]` plus pangram to the Japanese width; None = no text."""
    if jp is None or "{00}" in jp:
        return None
    runs = split_runs(jp)
    if not any(t and p.strip() for t, p in runs):
        return None
    out = []
    first = True
    pos = 0
    for is_text, piece in runs:
        if not is_text or not piece.strip():
            out.append(piece)
            continue
        px = jp_px(piece) * fill
        s = ""
        if first:
            s = f"[{tag}]"
            px -= vwf_font.text_width(s, font)
            first = False
        pad, pos = fill_to(px, pos, font)
        out.append(s + pad)
    return "".join(out)


def build_m2(blob, at, end, new):
    """The M2 at blob[at:end] with strings in `new` ({offset: bytes without NUL}) replaced."""
    n = struct.unpack_from("<H", blob, at + 2)[0]
    offs = struct.unpack_from(f"<{n + 1}H", blob, at + 4)
    if not any(at + offs[k] in new for k in range(n)):
        return bytes(blob[at:end])
    data = bytearray(blob[at + offs[0]:at + offs[0]])
    table = []
    pos = offs[0]
    for k in range(n):
        s0, s1 = at + offs[k], at + offs[k + 1]
        chunk = new[s0] + b"\0" if s0 in new else bytes(blob[s0:s1])
        table.append(pos)
        data += chunk
        pos += len(chunk)
    table.append(pos)
    if pos > M2_MAX:
        raise Overflow(f"M2 at {at:#x}: {pos:#x} bytes")
    head = blob[at:at + 2] + struct.pack(f"<H{n + 1}H", n, *table) + blob[at + 4 + 2 * (n + 1):at + offs[0]]
    tail = bytes(blob[at + offs[-1]:end]) if (end - at - offs[-1]) else b""
    return head + bytes(data) + tail


def build_bank(blob, bank, delta, new):
    """(old_start, old_end, new_bytes) of a bank; its M4 table is rewritten when a part grows."""
    if bank["kind"] == "M2":
        part = bank["parts"][0]
        a = part["at"] - delta
        return a, a + part["size"], build_m2(blob, a, a + part["size"], new)
    at = bank["at"] - delta
    n = struct.unpack_from("<H", blob, at + 2)[0]
    offs = struct.unpack_from(f"<{n + 1}I", blob, at + 4)
    out = bytearray(blob[at:at + offs[0]])
    table = []
    for k, part in enumerate(bank["parts"]):
        a, e = at + offs[k], at + offs[k + 1]
        table.append(len(out))
        out += build_m2(blob, a, e, new) if part["kind"] == "M2" else blob[a:e]
    table.append(len(out))
    struct.pack_into(f"<{n + 1}I", out, 4, *table)
    return at, at + offs[-1], bytes(out)


def splice(blob, doc, new, delta=0):
    """(new blob, offset map) after replacing the banks; a grown bank pushes what follows, kept 4-byte aligned."""
    spans = []
    for bank in doc["banks"]:
        if bank["kind"] == "raw":
            continue
        a, e, b = build_bank(blob, bank, delta, new)
        if (len(b) - (e - a)) % 4:
            b += b"\0" * (4 - (len(b) - (e - a)) % 4)
        spans.append((a, e, b))
    spans.sort()
    out = bytearray()
    pos = 0
    shifts = []
    for a, e, b in spans:
        out += blob[pos:a]
        out += b
        pos = e
        shifts.append((e, len(b) - (e - a)))
    out += blob[pos:]

    def remap(off):
        return off + sum(d for e, d in shifts if e <= off)
    return out, remap


def rebuild_scene(blob, doc, new):
    """The scene overlay with new strings: part table and header follow the shift; the slot size does not change."""
    out, remap = splice(blob, doc, new)
    sec2 = struct.unpack_from("<I", blob, 12)[0]
    n, size = struct.unpack_from("<II", blob, sec2 + 8)
    base = sec2 + 16
    offs = struct.unpack_from(f"<{n}I", blob, base)
    if remap(sec2) != sec2:
        raise ValueError("a bank before the part table")
    struct.pack_into(f"<I{n}I", out, sec2 + 12, remap(base + size) - base, *[remap(base + v) - base for v in offs])
    total = struct.unpack_from("<I", blob, 4)[0]
    struct.pack_into("<I", out, 4, remap(total))
    tail = len(out) - len(blob)
    if tail > 0:
        if any(out[len(blob):]):
            raise Overflow(f"scene needs {len(out.rstrip(bytes(1))):#x} of {len(blob):#x}")
        del out[len(blob):]
    else:
        out += bytes(-tail)
    return bytes(out)


def rebuild_system(blob, doc, new):
    """RES#3927 = M4 [fonts, system M4, more]: the outer table follows the system bank."""
    out, remap = splice(blob, doc, new, delta=SYSTEM_DELTA)
    n = struct.unpack_from("<H", blob, 2)[0]
    offs = struct.unpack_from(f"<{n + 1}I", blob, 4)
    struct.pack_into(f"<{n + 1}I", out, 4, *[remap(v) for v in offs])
    if remap(offs[-1]) > SYSTEM_SIZE:
        raise Overflow(f"system bank needs {remap(offs[-1]):#x} of {SYSTEM_SIZE:#x}")
    del out[SYSTEM_SIZE:]
    out += bytes(len(blob) - len(out))
    return bytes(out)


def patch_loose(blob, doc, new):
    """MAIN.EXE: loose strings stay in their slots; bank strings are not expected there."""
    out = bytearray(blob)
    for s in doc["strings"]:
        b = new.get(s["off"])
        if b is None:
            continue
        if len(b) + 1 > s["len"]:
            raise Overflow(f"{s['id']}: {len(b) + 1} bytes in a {s['len']} byte slot")
        out[s["off"]:s["off"] + s["len"]] = b + bytes(s["len"] - len(b))
    return bytes(out)


def tag_of(doc, index):
    """A short id for a marker: source letter or entry number, then the string's index in its file."""
    src = doc["source"]
    head = {"MAIN.EXE": "M", "PSX.EXE": "P"}.get(src, src.replace("RES#", ""))
    return f"{head}:{index}"


def encoded(doc, codec, fill=None, font=None, qa=None):
    """{offset: new bytes} for a source: `en` texts, or markers when fill is given; qa overrides by id."""
    new = {}
    for index, s in enumerate(doc["strings"]):
        text = (qa or {}).get(s["id"])
        if text is None:
            text = marker(s.get("read") or s["jp"], tag_of(doc, index), fill, font) if fill is not None else s.get("en")
        if not text:
            continue
        new[s["off"]] = codec.encode(text, en=True)
    return new


def _fit_loose(doc, new):
    """Marker build only: cut a marker to its fixed slot."""
    limits = {s["off"]: s["len"] - 1 for s in doc["strings"]}
    return {off: _cut(b, limits[off]) for off, b in new.items()}


def _cut(b, limit):
    """Cut encoded bytes at a limit without splitting an inline opcode or a two-byte code."""
    if len(b) <= limit:
        return b
    i = 0
    while True:
        c = b[i]
        step = b[i + 1] if c == 0x0C else 2 if c in textcodec.ARG1 or c >= 0x80 else 1
        if i + step > limit:
            return b[:i]
        i += step
