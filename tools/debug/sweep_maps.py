"""sweep_maps.py [--ids 1,4,5] [--jobs 8] [--slot a0000|40000] [--var NAME=LUA]: warp to scene overlays from a cold boot.

Triage for the scene list: writes work/qa/sweep/<id>/ (shots, log) and work/qa/sweep/result_<slot>.tsv
(id, emu exit, reached map, frame reached). Exit 124 means the emulator paused on a CPU exception or stalled.
"""
import argparse
import concurrent.futures as cf
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import res
from skill import SKILL

ROOT = Path(__file__).resolve().parents[2]
CUE = ROOT / "rom/Bealphareth (Japan).cue"
OUT = ROOT / "work/qa/sweep"
LUA = ROOT / "tools/debug/warp.lua"
ROUTE = ROOT / "tools/routes/newgame.txt"


def one(args):
    mid, extra = args
    out = OUT / str(mid)
    cmd = [sys.executable, "-X", "utf8", f"{SKILL}/scripts/emu.py", str(CUE), "--out", str(out), "--route", str(ROUTE),
           "--script", str(LUA), "--var", f"MAP={mid}", "--frames", "6600", "--shots", "5700,6000,6300",
           "--timeout", "120"] + extra
    p = subprocess.run(cmd, capture_output=True, text=True)
    log = (out / "log.txt").read_text(errors="replace") if (out / "log.txt").exists() else ""
    hit = re.findall(r"f(\d+) map (\d+)", log)
    reached, at = (int(hit[-1][1]), int(hit[-1][0])) if hit else (-1, -1)
    return mid, p.returncode, reached, at


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--slot", default="a0000", choices=["a0000", "40000"])
    ap.add_argument("--var", action="append", default=[])
    a = ap.parse_args()
    if a.ids:
        ids = [int(x) for x in a.ids.split(",")]
    else:
        size = int(a.slot, 16)
        ids = [i for i, _, s, b in res.entries() if b[:4] == b"\x02\0\0\0" and s == size]
    extra = [x for v in a.var for x in ("--var", v)]
    rows = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r in ex.map(one, [(i, extra) for i in ids]):
            rows.append(r)
            print(*r, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"result_{a.slot}.tsv", "w") as f:
        f.write("id\texit\treached\tat\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    print("bad:", [r[0] for r in rows if r[1] != 0 or r[2] != r[0]])


if __name__ == "__main__":
    main()
