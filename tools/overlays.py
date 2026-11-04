"""overlays.py: data patches in scene overlays that are not message banks. Offsets are in the part before the first bank,
which never shifts. RES#1023 holds the name entry screen (docs/re/vwf.md): every page becomes the ASCII grid."""
import struct
from pathlib import Path

NAMES = Path(__file__).resolve().parents[1] / "tbl/loose_names.tsv"

# Names the aging man refuses, in 20-byte slots, each glyph a (mode, code) pair like a typed name.
RESERVED = {
    0xC5F4: "Ziel", 0xC618: "Eugen", 0xC62C: "Valdes", 0xC640: "Qumran", 0xC654: "Gaius", 0xC668: "Fatum", 0xC67C: "Kadmon",
    0xC690: "Klaus", 0xC6A4: "Sadiya", 0xC6B8: "Tiara", 0xC6CC: "Nada", 0xC6E0: "Ash", 0xC6F4: "Arthur", 0xC708: "Leia",
    0xC71C: "Eleanor", 0xC730: "Pasca", 0xC744: "Scharn", 0xC758: "Jessica", 0xC76C: "Orpheus", 0xC780: "Eve", 0xC794: "Dias",
    0xC7A8: "Noel", 0xC7BC: "Luca", 0xC7D0: "Sara",
}
DEFAULTS = {0xFAA8: "Weld", 0xFAB8: "Filia"}  # 16-byte slots
GRID_PAGE_0, GRID_ASCII = 0xC5E4, 0x800E65F4  # pages 0 and 1 share this table word
DRAW_MODES, STORE_MODES = 0xC608, 0xC614  # per page, 3 bytes each; ASCII is 0 to draw and 1 to store
CURSOR_MODE = 0xC60E  # the cursor cell's text, `{09:09}{03}?`: its mode byte


def typed(name):
    """A name as the entry screen stores it."""
    return b"".join(bytes((1, ord(c))) for c in name)


def _name(out, off, name, slot):
    b = typed(name)
    if len(b) + 1 > slot:
        raise ValueError(f"{name} does not fit its {slot}-byte slot")
    out[off:off + slot] = b + bytes(slot - len(b))


def patch_name_entry(blob):
    out = bytearray(blob)
    struct.pack_into("<I", out, GRID_PAGE_0, GRID_ASCII)
    out[DRAW_MODES:DRAW_MODES + 3] = bytes(3)
    out[STORE_MODES:STORE_MODES + 3] = b"\1\1\1"
    out[CURSOR_MODE] = 1
    for off, name in RESERVED.items():
        # the first slot ends where the mode tables start
        _name(out, off, name, DRAW_MODES - off if off < DRAW_MODES else 20)
    for off, name in DEFAULTS.items():
        _name(out, off, name, 16)
    return bytes(out)


def patch_loose_name(out, base, off, words, en, pool, pool_end):
    """An object name outside the message banks (tools/loose_scan.py): over the old bytes if it fits, else in the far pool
    with its table words repointed. base: the overlay's offset in out. Returns the pool."""
    b = b"\x01" + en.encode("ascii") + b"\0"
    old_end = out.index(b"\0", base + off)
    if len(b) <= old_end + 1 - (base + off):
        out[base + off:old_end + 1] = b + bytes(old_end + 1 - (base + off) - len(b))
        return pool
    at = pool.find(b)
    if at < 0 or (at and pool[at - 1] != 0):
        pool = b + pool
        at = 0
    for w in words:
        struct.pack_into("<I", out, base + w, pool_end - len(pool) + at)
    return pool


def patch_loose_names(main_res, table, rows, pool, pool_end):
    """rows: loose_scan.scan on the original disc. A new name not in tbl/loose_names.tsv raises."""
    names = dict(line.split("\t") for line in NAMES.read_text(encoding="utf8").splitlines())
    for entry, off, words, text in rows:
        if entry == 1023 and off in DEFAULTS:  # patch_name_entry's: compact bytes would put the entry cursor on the name's last letter
            continue
        pool = patch_loose_name(main_res, table[entry][0], off, words, names[text], pool, pool_end)
    return pool


PATCHES = {1023: patch_name_entry}


def apply(entry, blob):
    patch = PATCHES.get(entry)
    return patch(blob) if patch else blob
