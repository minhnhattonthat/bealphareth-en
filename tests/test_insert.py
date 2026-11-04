"""Text insertion: an empty rebuild gives the original bytes; new text lands in the right bank; the font is sound."""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import insert  # noqa: E402
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


def test_overflow_raises():
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    blob = scene(doc)
    s = next(s for s in doc["strings"] if s["jp"] and "{1c" in s["jp"])
    try:
        insert.rebuild_scene(blob, doc, {s["off"]: b"A" * 0x10000})
    except insert.Overflow:
        return
    raise AssertionError("a 64 KB string fit an M2")


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
