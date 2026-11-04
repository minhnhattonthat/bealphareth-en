"""Text insertion: an empty rebuild gives the original bytes; new text lands in the right bank; the font is sound."""
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT =Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import insert  # noqa: E402
import overlays  # noqa: E402
import res  # noqa: E402
import textcodec  # noqa: E402
import vwf_font  # noqa: E402


def docs():
    for path in sorted((ROOT / "script").glob("*.json")):
        yield json.loads(path.read_text(encoding="utf8"))


def scene(doc):
    d = res.load()
    o, s = res.table(d)[doc["entry"]]
    return d[o:o + s]


def test_empty_rebuild_is_identity():
    d = res.load()
    table = res.table(d)
    for doc in docs():
        if doc["kind"] != "scene":
            continue
        o, s = table[doc["entry"]]
        blob = d[o:o + s]
        assert insert.rebuild_scene(blob, doc, {}) == blob, doc["source"]
    o, s = table[insert.SYSTEM_RES]
    blob = d[o:o + s]
    system = next(doc for doc in docs() if doc["source"] == "PSX.EXE")
    assert insert.rebuild_system(blob, system, {}) == blob


def test_a_grown_part_keeps_the_next_parts_aligned():
    d = res.load()
    o, s = res.table(d)[insert.SYSTEM_RES]
    blob = d[o:o + s]
    system = next(doc for doc in docs() if doc["source"] == "PSX.EXE")
    first = system["strings"][0]
    out = insert.rebuild_system(blob, system, {first["off"] - insert.SYSTEM_DELTA: b"x" * first["len"]}, keep_cells=[828])
    bank = struct.unpack_from("<I", out, 8)[0]
    n = struct.unpack_from("<H", out, bank + 2)[0]
    assert all(v % 4 == 0 for v in struct.unpack_from(f"<{n}I", out, bank + 4))


def test_sub_scene_text_stays_below_the_buffer():
    doc = next(d for d in docs() if d["source"] == "RES#1195" or d.get("entry") == 1195)
    s = next(s for s in doc["strings"] if s["len"] > 20)
    with pytest.raises(insert.Overflow):
        insert.rebuild_scene(scene(doc), doc, {s["off"]: b"x" * 0x10000})


def test_sub_scene_keeps_what_it_cannot_hold_in_its_own_file():
    doc = next(d for d in docs() if d.get("entry") == 1195)
    blob = bytes(scene(doc))
    s = next(s for s in doc["strings"] if s["len"] > 20)
    big = b"A" * 0x8000
    report = []
    out, pool = insert.fit_scene(blob, doc, {s["off"]: big}, b"", report)
    assert pool == b"" and "sub pool" in report[0] and len(out) == len(blob)
    end = struct.unpack_from("<I", out, 4)[0]
    assert end % 4 == 0
    magic, size = struct.unpack_from("<II", out, end - 8)
    assert magic == insert.SUB_POOL_MAGIC and out[end - 8 - size:end - 8] == big + b"\0"
    bank = doc["banks"][0]
    at = bank["at"] + struct.unpack_from("<I", out, bank["at"] + 8)[0]
    index = next(i for i, x in enumerate(doc["strings"]) if x["off"] == s["off"])
    off = struct.unpack_from("<I", out, at + 4 + 4 * index)[0]
    assert (insert.SCENE_LOAD[len(blob)] + at + off) & 0xFFFFFFFF == insert.SUB_POOL_RAM


def test_shared_strings_read_back_the_same():
    doc = next(d for d in docs() if d.get("entry") == 1195)
    blob = bytes(scene(doc))
    first = next(s for s in doc["strings"] if s["len"] > 1)  # an untouched bank is copied as it is: touch one string
    out = insert.rebuild_scene(blob, doc, {first["off"]: blob[first["off"]:first["off"] + first["len"] - 1]}, share=True)
    bank = doc["banks"][0]["at"]

    def strings(b):
        part = bank + struct.unpack_from("<I", b, bank + 8)[0]
        n = struct.unpack_from("<H", b, part + 2)[0]
        width = "I" if b[part + 1] == 0x34 else "H"
        offs = struct.unpack_from(f"<{n}{width}", b, part + 4)
        return [b[part + v:b.index(0, part + v)] for v in offs]

    assert len(out) == len(blob) and strings(out) == strings(blob)
    assert struct.unpack_from("<I", out, 4)[0] < struct.unpack_from("<I", blob, 4)[0]


def test_grown_string_moves_only_what_follows():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    s = next(s for s in doc["strings"] if s["jp"] and "{1c" in s["jp"])
    text = b"\x01" + b"A" * (s["len"] + 37)
    out = insert.rebuild_scene(blob, doc, {s["off"]: text})
    assert len(out) == len(blob)

    # the new bank parses, with the new text at the same string index
    bank = doc["banks"][0]
    at = bank["at"]
    parts = extract.parse_m4(out, at)
    m2 = next(p for p in parts if p[0] == "M2")
    index = next(i for i, x in enumerate(doc["strings"]) if x["off"] == s["off"])
    spans = extract.m2_strings(out, m2[1], m2[2])
    assert len(spans) == bank["parts"][1]["strings"]
    assert out[spans[index][0]:spans[index][1] - 1] == text

    # every part after the bank moved by the same 4-byte-aligned amount and kept its bytes; the part table says so
    sec2 = struct.unpack_from("<I", blob, 12)[0]
    n = struct.unpack_from("<I", blob, sec2 + 8)[0]
    old = struct.unpack_from(f"<{n}I", blob, sec2 + 16)
    new = struct.unpack_from(f"<{n}I", out, sec2 + 16)
    delta = struct.unpack_from("<I", out, 4)[0] - struct.unpack_from("<I", blob, 4)[0]
    assert delta > 0 and delta % 4 == 0
    assert struct.unpack_from("<I", out, sec2 + 12)[0] - struct.unpack_from("<I", blob, sec2 + 12)[0] == delta
    bank_part = at - (sec2 + 16)
    for a, b in zip(old, new):
        assert b - a == (delta if a > bank_part else 0)
    last = sec2 + 16 + old[-1]
    assert out[last + delta:last + delta + 64] == blob[last:last + 64]


def test_bank_past_64k_becomes_m4_of_strings():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    bank = doc["banks"][0]
    part = bank["parts"][1]
    s = next(s for s in doc["strings"] if s["jp"] and "{1c" in s["jp"])
    index = next(i for i, x in enumerate(doc["strings"]) if x["off"] == s["off"])
    out = insert.rebuild_scene(blob, doc, {s["off"]: b"A" * 0x10000})
    at = extract.parse_m4(out, bank["at"])
    at = struct.unpack_from("<I", out, bank["at"] + 8)[0] + bank["at"]
    assert out[at:at + 2] == b"M4"
    n = struct.unpack_from("<H", out, at + 2)[0]
    assert n == part["strings"]
    offs = struct.unpack_from(f"<{n + 1}I", out, at + 4)
    old_at = part["at"]
    assert out[at + offs[index]:at + offs[index + 1]] == b"A" * 0x10000 + b"\0"
    # the base id still follows the table, where m_head (asm/vwf.asm) looks: 4n + 8 from the bank
    assert out[at + 4 * n + 8:at + 4 * n + 12] == blob[old_at + 2 * n + 6:old_at + 2 * n + 10]


def test_overflow_raises():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    s = next(s for s in doc["strings"] if s["jp"] and "{1c" in s["jp"])
    try:
        insert.rebuild_scene(blob, doc, {s["off"]: b"A" * len(blob)})
    except insert.Overflow:
        return
    raise AssertionError("a string the size of the slot fit")


def test_drop_glyphs_frees_the_scene_font():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    bank = doc["banks"][0]
    glyph, m2 = bank["parts"][0], bank["parts"][1]
    assert glyph["kind"] == "glyph"
    out = insert.rebuild_scene(blob, doc, {}, drop_glyphs=True)
    a, b = struct.unpack_from("<II", out, bank["at"] + 4)
    assert a == b  # part 0 is empty, part 1 starts where it did
    assert out[bank["at"] + b:bank["at"] + b + 64] == blob[m2["at"]:m2["at"] + 64]
    assert struct.unpack_from("<I", out, 4)[0] == struct.unpack_from("<I", blob, 4)[0] - glyph["size"]


def test_far_string_wraps_to_its_ram_address():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    bank = doc["banks"][0]
    s = next(s for s in doc["strings"] if s["jp"] and "{1c" in s["jp"])
    index = next(i for i, x in enumerate(doc["strings"]) if x["off"] == s["off"])
    addr = insert.SYSTEM_RAM + insert.SYSTEM_SIZE - 16
    out = insert.rebuild_scene(blob, doc, {s["off"]: b"A"}, far={s["off"]: addr})
    at = bank["at"] + struct.unpack_from("<I", out, bank["at"] + 8)[0]
    assert out[at:at + 2] == b"M4"
    ram = insert.SCENE_LOAD[len(blob)] + at
    off = struct.unpack_from("<I", out, at + 4 + 4 * index)[0]
    assert (ram + off) & 0xFFFFFFFF == addr  # what the lookup at 0x80050974 computes


def test_fit_scene_falls_back_to_the_far_pool():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    s = next(s for s in doc["strings"] if s["jp"] and "{1c" in s["jp"])
    big = b"A" * len(blob)
    report = []
    out, pool = insert.fit_scene(blob, doc, {s["off"]: big}, b"", report)
    assert len(out) == len(blob) and pool == big + b"\0" and "far pool" in report[0]


def test_system_keeps_the_pool_at_its_end():
    d = res.load()
    o, s = res.table(d)[insert.SYSTEM_RES]
    blob = d[o:o + s]
    system = next(doc for doc in docs() if doc["source"] == "PSX.EXE")
    out = insert.rebuild_system(blob, system, {}, keep_cells=[828], pool=b"far\0")
    assert out[insert.SYSTEM_SIZE - 4:insert.SYSTEM_SIZE] == b"far\0"
    try:
        insert.rebuild_system(blob, system, {}, pool=b"far\0")
    except insert.Overflow:
        return
    raise AssertionError("pool over a full block")


def test_name_entry_is_ascii_and_keeps_its_slots():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    out = overlays.apply(1023, blob)
    assert len(out) == len(blob)
    assert out[0xFAA8:0xFAB1] == b"\1W\1e\1l\1d\0"
    assert struct.unpack_from("<I", out, overlays.GRID_PAGE_0)[0] == struct.unpack_from("<I", blob, overlays.GRID_PAGE_0 + 4)[0]
    assert out[0xC5E8:0xC5F4] == blob[0xC5E8:0xC5F4]  # the other page words stay
    assert overlays.apply(1024, blob) == blob


def test_loose_names_leave_the_default_names_to_the_entry_screen():
    out = bytearray(b"x" * 0x10000)
    assert overlays.patch_loose_names(out, {1023: (0, 0x10000)}, [(1023, 0xFAA8, [0xC7E4], "ウェルド")], b"", 0x1000) == b""
    assert out == b"x" * 0x10000


def test_system_cells_compact_and_banks_move_down():
    d = res.load()
    o, s = res.table(d)[insert.SYSTEM_RES]
    blob = d[o:o + s]
    system = next(doc for doc in docs() if doc["source"] == "PSX.EXE")
    out = insert.rebuild_system(blob, system, {}, keep_cells=[828, 829])
    offs = struct.unpack_from("<I", blob, 8)[0]
    new = struct.unpack_from("<I", out, 8)[0]
    assert new == insert.BASE_CELLS + 32
    assert out[insert.BASE_CELLS:insert.BASE_CELLS + 16] == blob[insert.BASE_CELLS + 828 * 16:insert.BASE_CELLS + 829 * 16]
    assert out[new:new + 0x77C4] == blob[offs:offs + 0x77C4]


def test_loose_strings_pool_and_repoint():
    blob = bytearray(64) + b"one\0two\0one\0"
    doc = {"strings": [{"off": 64, "len": 4}, {"off": 68, "len": 4}, {"off": 72, "len": 4}]}
    pointers = [(0, 64), (4, 68), (8, 72)]
    out = insert.patch_loose(bytes(blob) + bytes(3), doc, {64: b"longer"}, pointers, (64, 79))
    words = struct.unpack_from("<III", out, 0)
    at = [w - insert.MAIN_FILE_BASE for w in words]
    assert out[at[0]:at[0] + 7] == b"longer\0" and out[at[1]:at[1] + 4] == b"two\0" and out[at[2]:at[2] + 4] == b"one\0"
    try:
        insert.patch_loose(bytes(blob), doc, {64: b"x" * 20}, pointers, (64, 76))
    except insert.Overflow:
        return
    raise AssertionError("pool past its area")


def test_marker_keeps_control_codes():
    jp = "{1c:17}{0b:08}【 初老の男 】{0b:09}\nそれで若い{83c7}か?{1a}合計{01}14人{02}だ。{0c:2b00091501}"
    out = insert.marker(jp, "1:2")
    assert out.count("{1c:17}") == out.count("{0b:08}") == out.count("{1a}") == 1
    assert "{0c:2b00091501}" in out and "【" in out and "】" in out and "[1:2]" in out
    assert not any(ord(c) > 0x7E for c in out.replace("【", "").replace("】", ""))
    assert insert.marker("{0c:2b0009}", "1:2") is None
    assert insert.marker("{0e} {0f}", "1:2") is None


def test_encoder_states_mode_after_a_variable():
    codec = textcodec.Codec()
    assert codec.encode("Hi", en=True) == b"\x01Hi"
    assert codec.encode("Hi {10}!", en=True) == b"\x01Hi \x10\x01!"
    assert codec.encode("{0b:08}A{0b:09}B", en=True) == b"\x0b\x08\x01A\x0b\x09B"


def test_encoder_restates_mode_for_options_and_spaces():
    codec = textcodec.Codec()
    assert codec.encode("Yes|No", en=True) == b"\x01Yes|\x01No"  # each option starts in hiragana mode
    assert codec.encode("{87ac} A", en=True) == b"\x87\xac\x01 A"  # a kana-mode space is 12 px


def test_every_glyph_has_a_reading():
    """Translators read `read`: only the large button icons may stay tokens."""
    left = {m[0] for doc in docs() for s in doc["strings"] for m in extract.GLYPH_TOKEN.findall(s.get("read") or "")}
    assert left <= {"9f"}, left


def test_font_is_complete():
    font = vwf_font.load()
    assert len(vwf_font.glyphs(font)) == 94 * 11
    w = vwf_font.widths(font)
    assert len(w) == 95 and max(w) <= 8 and min(w) >= 2


def test_main_pointers_are_all_strings():
    blob = (extract.DISC / "MAIN.EXE").read_bytes()
    pointers = extract.main_pointers(blob)
    assert len(pointers) == 172
    assert all((slot - extract.MAIN_TABLE[0]) % 0x3C in (0, 0x38) for slot, _ in pointers)
