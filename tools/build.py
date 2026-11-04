"""build.py: rebuild the disc into build/bealphareth_en.bin/.cue. Checks the dump against rom.sha1 first.

work/disc/ is the unpacked disc (dumpsxiso), made once and kept pristine. With no edits yet the output is
byte-identical to the original; tests/test_identity.py holds that. Exit non-zero on any failure."""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_rom  # noqa: E402

TOOLS = ROOT / "tools/mkpsxiso/mkpsxiso-2.30-win64"
CUE = ROOT / "rom/Bealphareth (Japan).cue"
DISC = ROOT / "work/disc"
OUT = ROOT / "build/bealphareth_en.bin"


def dump(dest):
    """Unpack the original disc into dest/tree with dest/layout.xml."""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([TOOLS / "dumpsxiso.exe", "-q", "-x", dest / "tree", "-s", dest / "layout.xml", CUE], check=True)


def pack(disc, out):
    """Build out (.bin) and its .cue from disc/layout.xml; paths in the layout are relative to disc."""
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([TOOLS / "mkpsxiso.exe", "-q", "-y", "-o", out, "-c", out.with_suffix(".cue"), "layout.xml"],
                   cwd=disc, check=True)


def main():
    check_rom.check()
    if not (DISC / "layout.xml").exists():
        dump(DISC)
    pack(DISC, OUT)
    with open(OUT, "rb") as f:
        print(f"{OUT.relative_to(ROOT)} sha1 {hashlib.file_digest(f, 'sha1').hexdigest()}")


if __name__ == "__main__":
    main()
