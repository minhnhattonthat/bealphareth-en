"""The shipped script: every merged line passes the translators' lint, and the wrapper leaves no lone last word."""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402
import overlays  # noqa: E402


def test_every_merged_line_passes_the_lint():
    plates, terms = batches.glossary()
    seen = set()
    bad = []
    for _, doc in batches.load_docs():
        for idx, s in enumerate(doc["strings"]):
            if not s.get("tl") or s.get("status") == "placeholder":
                continue
            read = batches.read_of(s)
            form = batches.form_of(doc, read)
            m = batches.Masked(read, form)
            if (m.text, s["tl"]) in seen:
                continue
            seen.add((m.text, s["tl"]))
            e = {"text": m.text, "form": form, "limit": batches.limit_of(doc, form, idx, m.speaker(), s)}
            bad += [f"{s['id']}: {msg}" for msg in batches.check_entry(e, s["tl"], terms, plates)]
    assert not bad, "\n".join(bad[:40])


def test_loose_name_fits_in_place_else_goes_to_the_pool():
    blob = bytearray(16)
    blob[4:9] = b"\x03abc\0"
    blob[8] = 0
    pool = overlays.patch_loose_name(blob, 0, 4, [12], "Cat", b"", 0x1000)
    assert blob[4:9] == b"\x01Cat\0" and pool == b""
    pool = overlays.patch_loose_name(blob, 0, 4, [12], "Long name", b"", 0x1000)
    assert pool == b"\x01Long name\0"
    assert struct.unpack_from("<I", blob, 12)[0] == 0x1000 - len(pool)
    again = overlays.patch_loose_name(blob, 0, 4, [0], "Long name", pool, 0x1000)
    assert again == pool and struct.unpack_from("<I", blob, 0)[0] == 0x1000 - len(pool)


def test_placeholder_rule_keeps_labels_and_frees_sentences():
    doc = {"kind": "scene", "source": "RES#1"}
    def is_dev(read):
        return batches.is_placeholder(batches.Masked(read, "dlg"), doc)
    assert is_dev("パスカ\n幽霊発生装置OFF(仮)")
    assert is_dev("主人公男\n押せる石(仮)")
    assert is_dev("宝箱(仮)")
    assert not is_dev("もう開いてるぞ。(仮)")
    assert not is_dev("(仮)\nそんなに急がないでくれ。")
    assert not is_dev("空の宝箱だ(仮)")


def test_lone_last_word_is_pulled_down():
    pages = batches.wrap_pages("Weld, congratulations on getting you all the way out of there, friend, out!")
    assert " " in pages[-1][-1]
    text = "word " * 400 + "end"
    pages = batches.wrap_pages(text)
    assert " " in pages[-1][-1]
    assert sum(r.count(" ") + 1 for p in pages for r in p) == 401


def test_lone_word_on_a_new_page_takes_a_word_from_the_page_before():
    pages = batches.wrap_pages(" ".join(["aaaa"] * 17), widths=[5] * 95, box=50, last=50, max_rows=4)
    assert len(pages) == 3 and pages[-1] == ["aaaa aaaa"] and pages[-2][-1] == "aaaa"
