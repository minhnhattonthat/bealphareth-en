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
BASE_CELLS = 0x1D4C  # base kanji font in RES#3927 (0x801BAD4C), up to the system M4
MAIN_FILE_BASE = 0x8000F800  # RAM address of MAIN.EXE file offset 0
SYSTEM_RAM = 0x801B9000
SCENE_LOAD = {0xA0000: 0x800D6C00, 0x40000: 0x80136C00}  # RAM address of a scene by slot size (docs/re/disc.md)
# Sub-scenes: 0x80019A24 loads over 0x80156C00 as one starts, and the game reads some parts after that (#4107's map texture),
# so a part that ended below this line must stay below it. Maps have the same at 0x60000 (a sub-scene over 0x80136C00), not seen to matter.
LOAD_LINE = {0x40000: 0x20000}
SUB_POOL_RAM, SUB_POOL_SIZE = 0x8017EA00, 0x9600  # stays zero through the whole Japanese tour (tools/lua/free_probe.lua)
SUB_POOL_MAGIC = 0x424F5046  # asm/vwf.asm sub_far: a sub-scene file ending in [pool, magic, pool length]
# Every base-font glyph English draws, in new cell order: `{code}` (0x8080 + index) is what the encoder emits.
KEPT = "【】○×△□→←▽"

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


def build_m2(blob, at, end, new, far=None, ram=0, share=False):
    """The M2 at blob[at:end] with strings in `new` ({offset: bytes without NUL}) replaced. Past u16 offsets it comes back
    as an M4 of strings: the lookups read either width (`m_head` in asm/vwf.asm covers the one that did not).
    far: {offset: RAM address} of strings kept outside the scene; `ram` is this bank's address, u32 offsets wrap to them.
    share: repeated strings are stored once (the game finds a string's end by its NUL, never by the next offset)."""
    n = struct.unpack_from("<H", blob, at + 2)[0]
    offs = struct.unpack_from(f"<{n + 1}H", blob, at + 4)
    if not any(at + offs[k] in new for k in range(n)):
        return bytes(blob[at:end])
    far = far or {}
    chunks = []
    for k in range(n):
        s0, s1 = at + offs[k], at + offs[k + 1]
        chunks.append(None if s0 in far else new[s0] + b"\0" if s0 in new else bytes(blob[s0:s1]))
    extra = blob[at + 4 + 2 * (n + 1):at + offs[0]]  # the bank's base id
    wide = bool(far) or offs[0] + sum(len(c) for c in chunks if c) > M2_MAX
    pos = 4 + (4 if wide else 2) * (n + 1) + len(extra)
    table = []
    stored = {}
    body = []
    for k, chunk in enumerate(chunks):
        if chunk is None:
            table.append((far[at + offs[k]] - ram) & 0xFFFFFFFF)
            continue
        if share and chunk in stored:
            table.append(stored[chunk])
            continue
        stored[chunk] = pos
        table.append(pos)
        body.append(chunk)
        pos += len(chunk)
    table.append(pos)
    head = (b"M4" + struct.pack(f"<H{n + 1}I", n, *table)) if wide else (b"M2" + struct.pack(f"<H{n + 1}H", n, *table))
    tail = bytes(blob[at + offs[-1]:end]) if (end - at - offs[-1]) else b""
    return head + extra + b"".join(body) + tail


def build_bank(blob, bank, delta, new, drop_glyphs=False, far=None, load=0, share=False):
    """(old_start, old_end, new_bytes) of a bank; its M4 table is rewritten when a part grows."""
    if bank["kind"] == "M2":
        part = bank["parts"][0]
        a = part["at"] - delta
        return a, a + part["size"], build_m2(blob, a, a + part["size"], new, far, load + a, share)
    at = bank["at"] - delta
    n = struct.unpack_from("<H", blob, at + 2)[0]
    offs = struct.unpack_from(f"<{n + 1}I", blob, at + 4)
    out = bytearray(blob[at:at + offs[0]])
    table = []
    for k, part in enumerate(bank["parts"]):
        a, e = at + offs[k], at + offs[k + 1]
        out += bytes(-len(out) % 4)  # the game reads a part's head with lhu: an odd address raises an exception
        table.append(len(out))
        if part["kind"] == "M2":
            out += build_m2(blob, a, e, new, far, load + at + len(out), share)
        elif not (drop_glyphs and part["kind"] == "glyph"):
            out += blob[a:e]
    table.append(len(out))
    struct.pack_into(f"<{n + 1}I", out, 4, *table)
    return at, at + offs[-1], bytes(out)


def splice(blob, doc, new, delta=0, drop_glyphs=False, far=None, load=0, share=False):
    """(new blob, offset map) after replacing the banks; a grown bank pushes what follows, kept 4-byte aligned."""
    spans = []
    if far and sum(b["kind"] != "raw" for b in doc["banks"]) != 1:
        raise ValueError("far strings need one bank: a bank's address is only known for the first")
    for bank in doc["banks"]:
        if bank["kind"] == "raw":
            continue
        a, e, b = build_bank(blob, bank, delta, new, drop_glyphs, far, load, share)
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


def bank_end(blob, bank):
    if bank["kind"] == "M2":
        return bank["parts"][0]["at"] + bank["parts"][0]["size"]
    n = struct.unpack_from("<H", blob, bank["at"] + 2)[0]
    return bank["at"] + struct.unpack_from("<I", blob, bank["at"] + 4 + 4 * n)[0]


def rebuild_scene(blob, doc, new, drop_glyphs=False, far=None, share=False):
    """The scene overlay with new strings: part table and header follow the shift; the slot size does not change.
    drop_glyphs frees the scene font, which no English string draws from. far: see build_m2."""
    out, remap = splice(blob, doc, new, drop_glyphs=drop_glyphs, far=far, load=SCENE_LOAD[len(blob)], share=share)
    sec2 = struct.unpack_from("<I", blob, 12)[0]
    n, size = struct.unpack_from("<II", blob, sec2 + 8)
    base = sec2 + 16
    offs = struct.unpack_from(f"<{n}I", blob, base)
    if remap(sec2) != sec2:
        raise ValueError("a bank before the part table")
    limit = LOAD_LINE.get(len(blob))
    if limit:
        ends = [base + v for v in offs[1:]] + [base + size] + [bank_end(blob, b) for b in doc["banks"] if b["kind"] != "raw"]
        for end in ends:
            if end <= limit < remap(end):
                raise Overflow(f"data ending at {end:#x} moves to {remap(end):#x}, past {limit:#x}")
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


def sub_pool(blob, doc, new, report):
    """A sub-scene with its longest strings at the end of its own file: sub_far (asm/vwf.asm) copies them to SUB_POOL_RAM
    as it loads, before anything lands on that end. Only one sub-scene is loaded at a time, so they share the buffer."""
    far = {}
    own = b""
    last = None
    for off, b in sorted(new.items(), key=lambda kv: -len(kv[1])):
        far[off] = SUB_POOL_RAM + len(own)
        own += b + b"\0"
        if len(own) > SUB_POOL_SIZE:
            raise Overflow(f"{doc['source']}: {len(own):#x} of sub pool {SUB_POOL_SIZE:#x}")
        try:
            out = bytearray(rebuild_scene(blob, doc, new, drop_glyphs=True, far=far, share=True))
        except Overflow as e:
            last = e
            continue
        total = struct.unpack_from("<I", out, 4)[0]
        end = (total + len(own) + 8 + 3) & ~3
        if end > len(blob):
            raise Overflow(f"{doc['source']}: file with its pool ends at {end:#x}")
        out[end - 8 - len(own):end - 8] = own
        struct.pack_into("<II", out, end - 8, SUB_POOL_MAGIC, len(own))
        struct.pack_into("<I", out, 4, end)
        report.append(f"{doc['source']}: {len(far)} strings, {len(own):#x} bytes in the sub pool")
        return bytes(out)
    raise last


def fit_scene(blob, doc, new, pool, report):
    """A rebuilt scene that fits its slot: as it is, else with repeated strings stored once, else without its font, else with
    its longest strings in the far pool (the end of the system block, always in RAM). pool: bytes so far; returns (scene, pool)."""
    try:
        return rebuild_scene(blob, doc, new), pool
    except Overflow:
        pass
    try:
        out = rebuild_scene(blob, doc, new, share=True)
        report.append(f"{doc['source']}: repeated strings stored once")
        return out, pool
    except Overflow:
        pass
    try:
        out = rebuild_scene(blob, doc, new, drop_glyphs=True, share=True)
        report.append(f"{doc['source']}: scene font dropped, repeated strings stored once")
        return out, pool
    except Overflow as e:
        last = e
    if len(blob) in LOAD_LINE:
        try:
            return sub_pool(blob, doc, new, report), pool
        except Overflow as e:  # RES#361: its file is full to the slot's end
            last = e
    far = {}
    for off, b in sorted(new.items(), key=lambda kv: -len(kv[1])):
        pool = b + b"\0" + pool
        far[off] = SYSTEM_RAM + SYSTEM_SIZE - len(pool)
        try:
            out = rebuild_scene(blob, doc, new, drop_glyphs=True, far=far, share=True)
            report.append(f"{doc['source']}: scene font dropped, {len(far)} strings in the far pool")
            return out, pool
        except Overflow as e:
            last = e
    raise last


def rebuild_system(blob, doc, new, keep_cells=None, pool=b""):
    """RES#3927 = M4 [fonts, system M4, more]: the outer table follows the system bank.
    keep_cells: base-font cell numbers English draws; they become cells 0.. and the banks move down over the rest.
    pool: far strings of scenes (fit_scene), the last bytes of the block."""
    out, remap = splice(blob, doc, new, delta=SYSTEM_DELTA, share=True)
    n = struct.unpack_from("<H", blob, 2)[0]
    offs = struct.unpack_from(f"<{n + 1}I", blob, 4)
    table = [remap(v) for v in offs]
    if keep_cells is not None:
        cells = b"".join(blob[BASE_CELLS + c * 16:BASE_CELLS + (c + 1) * 16] for c in keep_cells)
        out[BASE_CELLS:table[1]] = cells
        freed = table[1] - BASE_CELLS - len(cells)
        table[1:] = [v - freed for v in table[1:]]
    struct.pack_into(f"<{n + 1}I", out, 4, *table)
    if table[-1] + len(pool) > SYSTEM_SIZE:
        raise Overflow(f"system bank needs {table[-1] + len(pool):#x} of {SYSTEM_SIZE:#x}")
    del out[table[-1]:]
    out += bytes(len(blob) - len(out))
    out[SYSTEM_SIZE - len(pool):SYSTEM_SIZE] = pool
    return bytes(out)


def patch_loose(blob, doc, new, pointers, area):
    """MAIN.EXE: strings are pooled, duplicates once, in area (start, end), and pointers [(word offset, string offset)] follow."""
    out = bytearray(blob)
    addr = {}
    pos = area[0]
    pool = {}
    for s in doc["strings"]:
        b = new.get(s["off"])
        if b is None:
            b = bytes(blob[s["off"]:s["off"] + s["len"] - 1])
        if b not in pool:
            pool[b] = pos
            pos += len(b) + 1
        addr[s["off"]] = pool[b]
    if pos > area[1]:
        raise Overflow(f"MAIN.EXE strings need {pos - area[0]:#x} of {area[1] - area[0]:#x}")
    for s in doc["strings"]:
        out[s["off"]:s["off"] + s["len"]] = bytes(s["len"])
    for b, at in pool.items():
        out[at:at + len(b)] = b
    for word, target in pointers:
        struct.pack_into("<I", out, word, addr[target] + MAIN_FILE_BASE)
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
