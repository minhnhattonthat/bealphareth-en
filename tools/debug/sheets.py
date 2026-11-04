"""sheets.py [--out work/qa/scenes/sheets] [--per 24]: group the per-scene proof shots into contact sheets.

regen.py leaves work/qa/scenes/<name>/final.png for every scene it proved from a cold boot. This pages them as
maps / subs / screens sheets and writes <page>.txt next to each sheet with the tile order (sheet.py has no labels),
so a reviewer can name any tile. Exits 1 if result.tsv has no row for a scene, so a sheet can't quietly drop one.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL

sys.path.insert(0, f"{SKILL}/scripts")
import sheet

OUT = ROOT / "work/qa/scenes"


def kind(name):
    if name.startswith("m") and name[1:].isdigit():
        return "maps"
    if name.startswith("s") and name[1:].isdigit():
        return "subs"
    return "screens"


def order(name):
    return (0, int(name[1:])) if name[1:].isdigit() else (1, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=Path, default=OUT, help="the regen.py output to page")
    ap.add_argument("--out", help="default SCENES/sheets")
    ap.add_argument("--per", type=int, default=24)
    ap.add_argument("--cols", type=int, default=6)
    a = ap.parse_args()
    scenes = a.scenes
    out = Path(a.out) if a.out else scenes / "sheets"
    out.mkdir(parents=True, exist_ok=True)

    proven = {}
    res = scenes / "result.tsv"
    if res.exists():
        for line in res.read_text().splitlines()[1:]:
            f = line.split("\t")
            proven[f[0]] = f[1] == "True"
    names = sorted((p.name for p in scenes.iterdir() if (p / "final.png").exists()), key=order)
    missing = [n for n in names if n not in proven]
    if missing:
        print(f"{len(missing)} dirs without a result.tsv row: {missing[:8]}", file=sys.stderr)
    index = ["name\tok\tpage\ttile"]
    for group in ("maps", "subs", "screens"):
        names_g = [n for n in names if kind(n) == group]
        for page, i in enumerate(range(0, len(names_g), a.per), 1):
            chunk = names_g[i:i + a.per]
            imgs = [sheet.read_png(str(scenes / n / "final.png")) for n in chunk]
            path = out / f"{group}_{page:02d}.png"
            sheet.sheet(imgs, a.cols, str(path), div=2)
            (out / f"{group}_{page:02d}.txt").write_text("\n".join(chunk) + "\n")
            index += [f"{n}\t{int(proven.get(n, False))}\t{path.name}\t{j}" for j, n in enumerate(chunk)]
            print(f"{path.name}: {len(chunk)} tiles {chunk[0]}..{chunk[-1]}")
    (out / "index.tsv").write_text("\n".join(index) + "\n")
    bad = [n for n in names if not proven.get(n)]
    print(f"{len(names)} shots, {sum(1 for v in proven.values() if v)} ok, {len(bad)} failed: {bad}")
    sys.exit(1 if bad or missing else 0)


if __name__ == "__main__":
    main()
