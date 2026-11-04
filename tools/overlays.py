"""overlays.py: data patches in scene overlays that are not message banks. Offsets are in the part before the first bank,
which never shifts. RES#1023 holds the name entry screen (docs/re/vwf.md): every page becomes the ASCII grid."""
import struct

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


PATCHES = {1023: patch_name_entry}


def apply(entry, blob):
    patch = PATCHES.get(entry)
    return patch(blob) if patch else blob
