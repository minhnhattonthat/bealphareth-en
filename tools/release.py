"""release.py [--version 1.0] [--force]: build, verify and package the patch into release/. Never publishes.

Stops at the first failure: build -> tests -> smoke -> disc_diff -> leftover Japanese in the script -> qa_gate on every
work/qa/**/manifest.tsv -> no unticked line in docs/polish.md -> debug tool off -> xdelta patch -> re-apply to the clean
dump and compare -> zip (patch + README only, ZIP_STORED). The playable image stays in build/."""
import argparse
import glob
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

ORIG = ROOT / "rom/Bealphareth (Japan).bin"
BUILT = ROOT / "build/bealphareth_en.bin"
OUT = ROOT / "release"
JP = re.compile(r"[぀-ヿ一-鿿]")


def run(*cmd):
    print(">", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def py(*args):
    run(sys.executable, "-X", "utf8", *args)


def hashes(path):
    data = path.read_bytes()
    return {"size": len(data), "crc32": f"{zlib.crc32(data):08X}", "md5": hashlib.md5(data).hexdigest(), "sha1": hashlib.sha1(data).hexdigest()}


def script_left():
    """Strings whose build text would still show Japanese, listed by id. Name plates and dev strings keep none either."""
    bad = []
    for path in glob.glob(str(ROOT / "script/*.json")):
        for s in json.loads(Path(path).read_text(encoding="utf8"))["strings"]:
            text = s.get("en") or s.get("read") or ""
            text = re.sub(r"\{[^{}]*\}", "", text)
            if JP.search(text):
                bad.append(s["id"])
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--force", action="store_true", help="overwrite this version's files")
    args = ap.parse_args()
    name = f"Bealphareth_EN_v{args.version}"
    patch = OUT / f"{name}.xdelta"
    zipped = OUT / f"{name}.zip"
    if (patch.exists() or zipped.exists()) and not args.force:
        sys.exit(f"{zipped} exists; --force to overwrite")

    py("tools/build.py")
    py("-m", "pytest", "-q", "tests")
    py(f"{SKILL}/scripts/emu.py", "build/bealphareth_en.cue", "--out", "work/qa/smoke", "--route", "tools/routes/boot.txt", "--smoke")
    py("tools/disc_diff.py")
    left = script_left()
    if left:
        sys.exit(f"{len(left)} strings keep Japanese: {left[:10]}")
    for manifest in glob.glob(str(ROOT / "work/qa/**/manifest.tsv"), recursive=True):
        py(f"{SKILL}/scripts/qa_gate.py", "check", manifest, str(Path(manifest).parent / "verdicts"))
    open_lines = [s for s in (ROOT / "docs/polish.md").read_text(encoding="utf8").splitlines() if s.startswith("- [ ]")]
    if open_lines:
        sys.exit(f"docs/polish.md: {len(open_lines)} unticked, first: {open_lines[0][:80]}")
    if re.search(r"^[^;\n]*0x800A0FE6|debug_on", (ROOT / "asm/vwf.asm").read_text(encoding="utf8"), re.M):
        sys.exit("asm/vwf.asm turns the debug menu on")

    OUT.mkdir(exist_ok=True)
    run("xdelta3", "-e", "-f", "-9", "-s", ORIG, BUILT, patch)
    back = ROOT / "work/release_check.bin"
    back.parent.mkdir(exist_ok=True)
    run("xdelta3", "-d", "-f", "-s", ORIG, patch, back)
    if hashes(back)["sha1"] != hashes(BUILT)["sha1"]:
        sys.exit("the patch does not rebuild the image")
    back.unlink()

    base, new = hashes(ORIG), hashes(BUILT)
    readme = (ROOT / "docs/patch-readme.txt").read_text(encoding="utf8")
    for key, value in (("VERSION", args.version), ("PATCH", patch.name), ("SIZE", base["size"]), ("CRC32", base["crc32"]), ("MD5", base["md5"]),
                       ("SHA1", base["sha1"]), ("NEW_CRC32", new["crc32"]), ("NEW_SHA1", new["sha1"])):
        readme = readme.replace("{" + key + "}", str(value))
    with zipfile.ZipFile(zipped, "w", zipfile.ZIP_STORED) as z:
        z.write(patch, patch.name)
        z.writestr("README.txt", readme.replace("\n", "\r\n"))
    print(zipped, f"{zipped.stat().st_size / 1e6:.1f} MB; image sha1 {new['sha1']}")


if __name__ == "__main__":
    main()
