"""walk.py SESSION NAME "press press.." ["press..".. ]: from a play.py session's first step, run each key path and keep
its shot as work/tmp/walk/NAME_<n>.png. Undoes each path afterwards, so paths don't depend on each other."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

PLAY = f"{SKILL}/scripts/play.py"
OUT = ROOT / "work/tmp/walk"


def play(*args):
    return subprocess.run([sys.executable, "-X", "utf8", PLAY, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=ROOT)


def main():
    session, name, paths = sys.argv[1], sys.argv[2], sys.argv[3:]
    OUT.mkdir(parents=True, exist_ok=True)
    for i, path in enumerate(paths):
        keys = path.split()
        r = play(session, *keys, "--gap", "24", "--wait", "45")
        shot = r.stdout.strip().splitlines()[-1]
        shutil.copy(ROOT / shot, OUT / f"{name}_{i}.png")
        play(session, "--back", "1")
    print(OUT)


if __name__ == "__main__":
    main()
