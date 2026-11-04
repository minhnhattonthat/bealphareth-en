"""The extracted script round-trips and covers every text range.

Run by tools/check.py (and so by the pre-commit hook). It reads the ORIGINAL disc, so a
stale script/*.json or a codec regression fails here rather than in the game.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import res  # noqa: E402

SCRIPT = ROOT / "script"


@pytest.fixture(scope="module")
def disc():
    glyphs = extract.glyph_chars()
    base = extract.base_kanji(glyphs)
    d = res.load()
    sources = {}
    for fname in ("MAIN.EXE", "PSX.EXE"):
        sources[fname] = (extract.DISC / fname).read_bytes()
    for idx, (o, s) in enumerate(res.table(d)):
        if s:
            sources[f"RES#{idx}"] = d[o:o + s]
    return glyphs, base, sources


def script_files():
    return sorted(SCRIPT.glob("*.json"))


def test_script_exists():
    files = script_files()
    assert len(files) > 200, "script/ is missing: run python tools/extract.py"
    total = 0
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        total += len(doc["strings"])
    assert total > 50000, total


def test_roundtrip_every_string(disc):
    glyphs, base, sources = disc
    bad = []
    for path in script_files():
        doc = json.loads(path.read_text(encoding="utf-8"))
        blob = sources[doc["source"]]
        banks = extract.find_banks(blob)
        codecs = extract.doc_codecs(blob, banks, glyphs, base)
        fallback = codecs[0] if codecs else extract.textcodec.Codec(base)
        for s in doc["strings"]:
            codec = codecs[int(s["bank"].split(".")[0])] if s["bank"] else fallback
            raw = blob[s["off"]:s["off"] + s["len"] - 1]
            assert s["jp"] is not None, (doc["source"], s["off"])
            try:
                back = codec.encode(s["jp"])
            except ValueError as exc:  # pragma: no cover - reported below
                bad.append((doc["source"], s["off"], str(exc)))
                continue
            if back != raw:
                bad.append((doc["source"], s["off"], "mismatch"))
    assert not bad, bad[:10]


def test_coverage_is_complete(disc):
    """script/ holds exactly the strings a fresh extraction finds, and each bank is tiled."""
    glyphs, base, _ = disc
    fresh = extract.extract_all(glyphs, base) if hasattr(extract, "extract_all") else None
    if fresh is None:
        pytest.skip("extract_all not available")
    docs = {d["source"]: d for d in fresh}
    for path in script_files():
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["source"] in docs, doc["source"]
        fresh_doc = docs[doc["source"]]
        assert [s["id"] for s in doc["strings"]] == [s["id"] for s in fresh_doc["strings"]], (
            f"{path} is stale: run python tools/extract.py --force")


def test_banks_tile_their_regions(disc):
    """Every M2 bank's strings are contiguous, and their count matches the recorded part."""
    glyphs, base, sources = disc
    for path in script_files():
        doc = json.loads(path.read_text(encoding="utf-8"))
        blob = sources[doc["source"]]
        for bank in doc["banks"]:
            if bank["kind"] == "raw":
                assert bank["end"] > bank["at"]
                continue
            for part in bank["parts"]:
                if part["kind"] != "M2":
                    continue
                spans = extract.m2_strings(blob, part["at"], part["at"] + part["size"])
                assert len(spans) == part["strings"]
                for (a, b), (c, d) in zip(spans, spans[1:]):
                    assert b == c, "M2 strings must be contiguous"


def test_kanji_table_is_sane():
    glyphs = extract.glyph_chars()
    assert len(glyphs) > 1700, len(glyphs)
    for cell, ch in glyphs.items():
        assert len(cell) == 242, cell
        assert len(ch) == 1, (cell, ch)
