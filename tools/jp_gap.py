"""jp_gap.py TEXT [TEXT..]: is on-screen Japanese extracted? Looks for TEXT in `read` of script/*.json, then for its byte form in
every overlay, MAIN.EXE and PSX.EXE outside the string ranges script/ already covers. Backstop for leftovers the marker tour shows."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import res  # noqa: E402


def sources():
    yield "MAIN.EXE", (extract.DISC / "MAIN.EXE").read_bytes()
    yield "PSX.EXE", (extract.DISC / "PSX.EXE").read_bytes()
    d = res.load()
    for i, (o, s) in enumerate(res.table(d)):
        if s:
            yield f"RES#{i}", d[o:o + s]


def main():
    glyphs = extract.glyph_chars()
    base = extract.base_kanji(glyphs)
    docs = {}
    for p in (ROOT / "script").glob("*.json"):
        doc = json.loads(p.read_text(encoding="utf8"))
        docs[doc["source"]] = doc
    for text in sys.argv[1:]:
        hits = [s["id"] for d in docs.values() for s in d["strings"] if text in (s.get("read") or "")]
        print(f"{text}: {len(hits)} strings {hits[:4]}")
        for name, blob in sources():
            codec = extract.doc_codecs(blob, extract.find_banks(blob), glyphs, base) if name in docs else []
            for c in codec or [extract.textcodec.Codec(base)]:
                try:
                    needle = c.encode(text)
                except ValueError:
                    continue
                needle = needle.lstrip(b"\x01\x02\x03")
                at = blob.find(needle)
                covered = [(s["off"], s["off"] + s["len"]) for s in docs[name]["strings"]] if name in docs else []
                while at >= 0:
                    if not any(a <= at < b for a, b in covered):
                        print(f"  outside script/: {name} +{at:x} {blob[max(at - 8, 0):at + len(needle) + 8].hex()}")
                    at = blob.find(needle, at + 1)
                break


if __name__ == "__main__":
    main()
