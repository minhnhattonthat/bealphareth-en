"""regen.py [names|glob..] [--rom CUE] [--jobs 8] [--out work/qa/scenes]: prove every scene in scenes.lua from a cold boot.

Each scene gets its own emulator run. Pass = emulator exit 0, the RAM log shows its map (and sub-scene) reached, and the
final shot is not one flat colour. Writes OUT/<scene>/ and OUT/result.tsv, prints fails, exits 1 if any fail.
Names are matched with fnmatch: `regen.py "s1*" menu_main`. --state saves work/states/<scene>.sstate at the end of each run.
"""
import argparse
import concurrent.futures as cf
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL

sys.path.insert(0, f"{SKILL}/scripts")
import sheet

SCENES = ROOT / "tools/debug/scenes.lua"
WARP = ROOT / "tools/debug/warp.lua"
NEWGAME = ROOT / "tools/routes/newgame.txt"
OPENING_FRAMES, FIELD_FRAMES = 7000, 34000  # English reached field control at about f30000 (Japanese f26200)


def parse_scenes():
    """The fields regen needs, read from scenes.lua text: name -> dict. Generated loops are expanded by hand here."""
    t = SCENES.read_text(encoding="utf8")
    out = {}
    maps = re.search(r"local MAPS = \{(.*?)\n\}", t, re.S).group(1)
    for x in re.findall(r"\d+", maps):
        out[f"m{x}"] = {"map": int(x)}
    chain = re.search(r"for _, id in ipairs\(\{([^}]*)\}\) do S\[\"m\"", t).group(1)
    for x in re.findall(r"\d+", chain):
        out[f"m{x}"]["chain"] = True
    subs = re.search(r"local SUBS = \{(.*?)\n\}", t, re.S).group(1)
    for sub, parent in re.findall(r"\[(\d+)\]=(\d+)", subs):
        out[f"s{sub}"] = {"map": int(parent), "sub": int(sub)}
    for name, body in re.findall(r"^S\.(\w+) = (.*(?:\n  .*)*)$", t, re.M):
        d = {}
        if body.startswith("field("):
            m = re.search(r"map = (\d+)", body)
            d.update(map=int(m.group(1)) if m else 171, base="field")
        elif 'base = "route"' in body or "route =" in body:
            d["base"] = "route"
        m = re.search(r"frames = (\d+)", body)
        if m:
            d["frames"] = int(m.group(1))
        if "mash = true" in body:
            d["mash"] = True
        r = re.search(r'route = "([^"]+)"', body)
        if r:
            d["route"] = r.group(1)
        out[name] = d
    for m in re.finditer(r"^S\.(\w+)\.frames = (\d+)", t, re.M):
        out[m.group(1)]["frames"] = int(m.group(2))
    for m in re.finditer(r"^S\.(\w+)\.blank = true", t, re.M):
        out[m.group(1)]["blank"] = True
    for m in re.finditer(r'ipairs\(\{([^}]*)\}\) do S\["([ms])" \.\. id\]\.blank = true', t):
        for x in re.findall(r"\d+", m.group(1)):
            out[f"{m.group(2)}{x}"]["blank"] = True
    return out


def one(a):
    name, sc, rom, outdir, state, every, length = a
    out = outdir / name
    if sc.get("base") == "route":
        route = ROOT / sc.get("route", NEWGAME)
        frames = sc["frames"]
    else:
        route = NEWGAME
        if sc.get("base") == "field":
            # field base: 28000 frames to hand control, then the scene's own budget (game_over needs ~2400 to die)
            frames = FIELD_FRAMES + 1500 + (sc.get("frames") or 0)
        else:
            frames = sc.get("frames") or OPENING_FRAMES
    frames = length or frames
    cmd = [sys.executable, "-X", "utf8", f"{SKILL}/scripts/emu.py", str(rom), "--out", str(out), "--route", str(route),
           "--script", str(WARP), "--var", f"SCENES_LUA=[[{SCENES.as_posix()}]]", "--var", f"SCENE='{name}'",
           "--frames", str(frames), "--shots", ",".join(str(frames - d) for d in (900, 600, 300)),
           "--timeout", "280", "--mash-key", "circle"]
    if every:
        cmd += ["--shot-every", str(every)]
    if sc.get("mash"):
        cmd += ["--mash", "60"]
    if state:
        cmd += ["--state-out", str(ROOT / f"work/states/{name}.sstate")]
    p = subprocess.run(cmd, capture_output=True, text=True)
    log = (out / "log.txt").read_text(errors="replace") if (out / "log.txt").exists() else ""
    want = sc.get("map")
    visited = want is None or re.search(rf"^f\d+ map {want}$", log, re.M) is not None
    subok = "sub" not in sc or f"sub {sc['sub']} loaded" in log
    final = out / "final.png"
    flat = not final.exists() or sheet.is_blank(sheet.read_png(str(final)))
    ok = p.returncode == 0 and visited and subok and (not flat or sc.get("blank"))
    return name, ok, p.returncode, int(visited), int(subok), int(flat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--rom", default="rom/Bealphareth (Japan).cue")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", default="work/qa/scenes")
    ap.add_argument("--state", action="store_true")
    ap.add_argument("--field-frames", type=int, help="frames to hand control (longer text in a marker build takes longer)")
    ap.add_argument("--every", type=int, help="also a shot every N frames: cards and captions come and go")
    ap.add_argument("--frames", type=int, help="run length instead of the scene's own")
    a = ap.parse_args()
    if a.field_frames:
        global FIELD_FRAMES
        FIELD_FRAMES = a.field_frames
    scenes = parse_scenes()
    names = [n for n in scenes if not a.names or any(fnmatch.fnmatch(n, p) for p in a.names)]
    outdir = ROOT / a.out
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r in ex.map(one, [(n, scenes[n], ROOT / a.rom, outdir, a.state, a.every, a.frames) for n in names]):
            rows.append(r)
            print(*r, flush=True)
    res = outdir / "result.tsv"
    old = {}
    if res.exists():
        for line in res.read_text().splitlines()[1:]:
            old[line.split("\t")[0]] = line
    for r in rows:
        old[r[0]] = "\t".join(map(str, r))
    res.write_text("name\tok\texit\tvisited\tsub\tflat\n" + "\n".join(old[k] for k in sorted(old)) + "\n")
    bad = [r[0] for r in rows if not r[1]]
    print(f"{len(rows) - len(bad)}/{len(rows)} ok; failed: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
