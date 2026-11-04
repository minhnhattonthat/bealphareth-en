"""probe_parent.py SUB MAP..: try each parent map for a sub-scene, in parallel, and report which ones draw.

A sub-scene overlay loads into the same 0x800D6C00 base as a map, so its parent is only the init code that runs
before it; a wrong parent can leave the sub drawing black. Prints `parent ok blank exit` per run and keeps the shots
under work/qa/parents/s<SUB>_m<MAP>/. Used when regen.py reports a sub with a flat final shot.
"""
import concurrent.futures as cf
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL

sys.path.insert(0, f"{SKILL}/scripts")
import sheet

CUE = ROOT / "rom/Bealphareth (Japan).cue"
OUT = ROOT / "work/qa/parents"


def one(a):
    sub, parent = a
    out = OUT / f"s{sub}_m{parent}"
    cmd = [sys.executable, "-X", "utf8", f"{SKILL}/scripts/emu.py", str(CUE), "--out", str(out),
           "--route", str(ROOT / "tools/routes/newgame.txt"), "--script", str(ROOT / "tools/debug/warp.lua"),
           "--var", f"MAP={parent}", "--var", f"SUB={sub}", "--frames", "7000",
           "--shots", "6100,6500,6800", "--timeout", "120", "--mash-key", "circle"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    final = out / "final.png"
    blank = not final.exists() or sheet.is_blank(sheet.read_png(str(final)))
    log = (out / "log.txt").read_text(errors="replace") if (out / "log.txt").exists() else ""
    subok = f"sub {sub} loaded" in log
    return parent, subok and not blank, int(blank), p.returncode


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sub, parents = int(sys.argv[1]), [int(x) for x in sys.argv[2:]]
    rows = []
    with cf.ThreadPoolExecutor(len(parents)) as ex:
        for r in ex.map(one, [(sub, m) for m in parents]):
            print(*r, flush=True)
            rows.append(r)
    print("works:", [r[0] for r in rows if r[1]])


if __name__ == "__main__":
    main()
