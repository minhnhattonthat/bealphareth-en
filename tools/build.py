"""build.py: rebuild the disc into build/bealphareth_en.bin/.cue. Checks the dump against rom.sha1 first.

work/disc/ is the unpacked original (dumpsxiso), made once and kept pristine. A build assembles asm/vwf.asm over copies
of MAIN.EXE and the PSX.EXE font block, inserts the text, and packs work/en/ (unchanged files are hard links).

    build.py                 script/*.json `en` texts (none yet: the engine patch over the Japanese text)
    build.py --marker        every line replaced by [tag] + pangram, into build/bealphareth_marker.*
    build.py --qa ID=TEXT    override one string, repeatable ({0a}-style tokens and \\n work)

Exit non-zero on any failure, a text overflow included (a marker line shrinks instead, and the report says so)."""
import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_rom  # noqa: E402
import extract  # noqa: E402
import insert  # noqa: E402
import res  # noqa: E402
import vwf_font  # noqa: E402

TOOLS = ROOT / "tools/mkpsxiso/mkpsxiso-2.30-win64"
ARMIPS = ROOT / "tools/armips/armips.exe"
CUE = ROOT / "rom/Bealphareth (Japan).cue"
DISC = ROOT / "work/disc"
WORK = ROOT / "work/en"
OUT = ROOT / "build/bealphareth_en.bin"
OUT_MARKER = ROOT / "build/bealphareth_marker.bin"
FONT_OFF = 0x14  # half-width font cells in RES#3927
MARKER_FILLS = (1.0, 0.6, 0.3, 0.0)


def dump(dest):
    """Unpack the original disc into dest/tree with dest/layout.xml."""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([TOOLS / "dumpsxiso.exe", "-q", "-x", dest / "tree", "-s", dest / "layout.xml", CUE], check=True)


def pack(disc, out):
    """Build out (.bin) and its .cue from disc/layout.xml; paths in the layout are relative to disc."""
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([TOOLS / "mkpsxiso.exe", "-q", "-y", "-o", out, "-c", out.with_suffix(".cue"), "layout.xml"],
                   cwd=disc, check=True)


def assemble(main_exe, font_res):
    """(MAIN.EXE, RES#3927) with asm/vwf.asm and the VWF font applied."""
    tmp = WORK / "asm"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    font = vwf_font.load()
    (tmp / "MAIN.EXE").write_bytes(main_exe)
    res_patched = bytearray(font_res)
    glyphs = vwf_font.glyphs(font)
    res_patched[FONT_OFF:FONT_OFF + len(glyphs)] = glyphs
    (tmp / "FONTRES").write_bytes(res_patched)
    (tmp / "vwf_widths.bin").write_bytes(vwf_font.widths(font))
    subprocess.run([ARMIPS, ROOT / "asm/vwf.asm", "-root", tmp, "-sym", tmp / "vwf.sym"], check=True)
    return (tmp / "MAIN.EXE").read_bytes(), (tmp / "FONTRES").read_bytes()


def load_docs():
    """(doc, path) of every script file."""
    for path in sorted((ROOT / "script").glob("*.json")):
        yield json.loads(path.read_text(encoding="utf8"))


def codec_for(doc, blob, glyphs, base):
    """The codec of a source's first bank, for its new text: only the kept base-font cells have kanji codes."""
    banks = extract.find_banks(blob)
    codec = extract.source_codec(blob, banks, glyphs, base) if banks else extract.textcodec.Codec(base)
    codec.kanji_rev = {ch: (0x80, 0x80 + i) for i, ch in enumerate(insert.KEPT)}
    return codec


def kept_cells(base):
    """Old base-font cell number of each kept glyph, in insert.KEPT order."""
    cell = {ch: (hi - 0x80) * 112 + lo - 0x80 for (hi, lo), ch in base.items()}
    return [cell[ch] for ch in insert.KEPT]


def insert_marker_scene(doc, blob, codec, qa, font, report):
    """The rebuilt overlay; marker text shrinks until it fits, and the fill used goes to the report."""
    for fill in MARKER_FILLS:
        new = insert.encoded(doc, codec, fill=fill, font=font, qa=qa)
        try:
            out = insert.rebuild_scene(blob, doc, new)
        except insert.Overflow as e:
            last = e
            continue
        if fill != 1.0:
            report.append(f"{doc['source']}: marker fill {fill}")
        return out
    raise last


def build(marker=False, qa=None, out=OUT, only=None):
    check_rom.check()
    if not (DISC / "layout.xml").exists():
        dump(DISC)
    tree = DISC / "tree"
    main_exe = (tree / "MAIN.EXE").read_bytes()
    main_res = bytearray((tree / "MAIN.RES").read_bytes())
    table = res.table(main_res)
    so, ss = table[insert.SYSTEM_RES]
    main_exe, font_res = assemble(main_exe, bytes(main_res[so:so + ss]))

    glyphs = extract.glyph_chars()
    base = extract.base_kanji(glyphs)
    font = vwf_font.load()
    report = []
    changed = 0
    pool = b""
    # the system block goes last: it takes the far strings the scenes leave
    for doc in sorted(load_docs(), key=lambda d: d["source"] == "PSX.EXE"):
        src = doc["source"]
        if only and not any(fnmatch.fnmatch(src, pat) for pat in only):
            continue
        if src == "MAIN.EXE":
            blob = (tree / "MAIN.EXE").read_bytes()
            codec = codec_for(doc, blob, glyphs, base)
            new = insert.encoded(doc, codec, fill=1.0 if marker else None, font=font, qa=qa)
            if marker:
                new = insert._fit_loose(doc, new)
            main_exe = insert.patch_loose(main_exe, doc, new, extract.main_pointers(blob), extract.MAIN_TEXT[0])
        elif src == "PSX.EXE":
            blob = (tree / "PSX.EXE").read_bytes()
            codec = codec_for(doc, blob, glyphs, base)
            new = {}
            for fill in MARKER_FILLS if marker else (None,):
                new = insert.encoded(doc, codec, fill=fill, font=font, qa=qa)
                new = {off - insert.SYSTEM_DELTA: b for off, b in new.items()}
                try:
                    font_res = insert.rebuild_system(font_res, doc, new, kept_cells(base), pool)
                except insert.Overflow as e:
                    if fill == MARKER_FILLS[-1] or fill is None:
                        raise
                    report.append(f"PSX.EXE: {e}")
                    continue
                if fill not in (None, 1.0):
                    report.append(f"PSX.EXE: marker fill {fill}")
                break
        else:
            o, s = table[doc["entry"]]
            blob = bytes(main_res[o:o + s])
            codec = codec_for(doc, blob, glyphs, base)
            if marker:
                rebuilt = insert_marker_scene(doc, blob, codec, qa, font, report)
            else:
                rebuilt, pool = insert.fit_scene(blob, doc, insert.encoded(doc, codec, qa=qa), pool, report)
            if rebuilt != blob:
                assert len(rebuilt) == s
                main_res[o:o + s] = rebuilt
                changed += 1
    if len(font_res) != ss:
        raise ValueError("system entry changed size")
    main_res[so:so + ss] = font_res  # never seen loaded, kept in step in case a path does
    psx_exe = bytearray((tree / "PSX.EXE").read_bytes())
    psx_exe[insert.SYSTEM_DELTA:insert.SYSTEM_DELTA + insert.SYSTEM_SIZE] = font_res[:insert.SYSTEM_SIZE]

    shutil.rmtree(WORK / "tree", ignore_errors=True)
    for src in tree.rglob("*"):
        dst = WORK / "tree" / src.relative_to(tree)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif src.name not in ("MAIN.EXE", "MAIN.RES", "PSX.EXE"):
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.link(src, dst)
    (WORK / "tree/PSX.EXE").write_bytes(psx_exe)
    (WORK / "tree/MAIN.EXE").write_bytes(main_exe)
    (WORK / "tree/MAIN.RES").write_bytes(main_res)
    shutil.copy(DISC / "layout.xml", WORK / "layout.xml")
    pack(WORK, out)
    print(f"scenes changed {changed}; {len(report)} notes")
    for line in report[:40]:
        print(" ", line)
    with open(out, "rb") as f:
        print(f"{out.relative_to(ROOT)} sha1 {hashlib.file_digest(f, 'sha1').hexdigest()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT")
    ap.add_argument("--only", action="append", metavar="GLOB", help="insert only these sources (bisecting a hang)")
    args = ap.parse_args()
    qa = {}
    for item in args.qa:
        key, text = item.split("=", 1)
        qa[key] = text.replace("\\n", "\n")
    build(args.marker, qa, OUT_MARKER if args.marker else OUT, args.only)


if __name__ == "__main__":
    main()
