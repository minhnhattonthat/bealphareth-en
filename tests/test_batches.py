"""Batch tooling: masking keeps every code, wrapping stays in budget, the checker catches what translators get wrong."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402
import textcodec  # noqa: E402
import vwf_font  # noqa: E402

PLATES = {"クムラン": "Qumran"}
SCENE = {"kind": "scene", "source": "RES#1"}
EXE = {"kind": "exe", "source": "PSX.EXE"}


def masked(read, doc=SCENE):
    return batches.Masked(read, batches.form_of(doc, read))


def test_frame_codes_survive():
    m = masked("{1c:10}{0b:08}【 クムラン 】{0b:09}\n今日は{09:06}晴れ{09:01}です。{1a}{10}さん。{0c:5102}")
    assert m.text == "今日は[1]晴れ[2]です。 // [HERO]さん。"
    en = batches.unmask(m, "Today is [1]sunny[2]. // [HERO]-san.", PLATES)
    assert en.startswith("{1c:10}{0b:08}【 Qumran 】{0b:09}\n")
    assert en.endswith("{0c:5102}")
    assert "{09:06}sunny{09:01}" in en and "{1a}{10}-san." in en
    textcodec.Codec({(0x87, 0xAC): "【", (0x87, 0xAD): "】"}).encode(en, en=True)


def test_repeat_dialogue_is_not_a_choice():
    read = "長い文章です。\nまだ続きます。|{0b:07}{0b:08}【 クムラン 】{0b:09}\nまだ何か?"
    m = masked(read)
    assert m.form == "dlg"
    long = " ".join(["word"] * 80)
    en = batches.unmask(m, long + "|[1][クムラン:]Anything else?", PLATES)
    first, second = en.split("|")
    assert "\n" in first and "【 Qumran 】" in second
    assert masked("はい|いいえ").form == "choice"


def test_wrap_stays_in_budget():
    text = "The quick brown fox jumps over the lazy dog and keeps running until the page runs out, " * 6
    for plate in (False, True):
        for page in batches.wrap_pages(text, plate):
            assert len(page) <= (3 if plate else 4)
            for n, row in enumerate(page):
                limit = batches.LAST_W if n == len(page) - 1 and len(page) == (3 if plate else 4) else batches.BOX_W
                assert batches.page_px(row) <= limit, row
                assert vwf_font.text_width(row) == batches.page_px(row)


def test_check_entry_catches_mistakes():
    e = {"id": "x", "speaker": "-", "form": "dlg", "limit": "216px*4r", "text": "[HERO]さん、[1]行こう。"}
    good = "[HERO]-san, [1]let's go."
    assert batches.check_entry(e, good, [], PLATES) == []
    assert batches.check_entry(e, "", [], PLATES) == ["empty"]
    assert any("structure" in x for x in batches.check_entry(e, "[HERO]-san, let's go.", [], PLATES))
    assert any("variables" in x for x in batches.check_entry(e, "[1]Let's go.", [], PLATES))
    assert any("honorific" in x for x in batches.check_entry(e, "[HERO], [1]let's go.", [], PLATES))
    assert any("non-ASCII" in x for x in batches.check_entry(e, "[HERO]-san, [1]行こう", [], PLATES))
    assert any("ordinal" in x for x in batches.check_entry(dict(e, text="[VAR14][1]番目"), "[VAR14]th[1]", [], PLATES))
    item = {"id": "y", "speaker": "-", "form": "menu", "limit": "100px", "text": "鉄の剣"}
    assert any("100px" in x for x in batches.check_entry(item, "A very long name for an iron sword indeed", [], PLATES))


def test_placeholder_only_in_scenes():
    m = masked("パスカ\n歯車OFF(仮)")
    assert batches.is_placeholder(m, SCENE)
    assert not batches.is_placeholder(masked("どくーん(仮)", EXE), EXE)


def test_pipe_resets_to_hiragana():
    # bytes: ascii "A" | then 2f = く in hiragana, never the ascii "/"
    codec = textcodec.Codec()
    data = b"\x01A\x7c\x2f"
    assert codec.decode(data) == "A|く"
    assert codec.encode(codec.decode(data)) == data
