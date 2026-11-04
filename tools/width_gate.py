"""width_gate.py [--no-build|--menu]: the phase-5 width test. Builds a stress disc (build/bealphareth_en.bin) with rulers in the
opening scene's boxes, plays the opening, and leaves shots in work/qa/width/. --menu rulers the system bank's menu strings and
walks the field menus into work/tmp/walk/gate_*.png. Results: docs/re/windows.md.

A ruler is a line of exact pixel width ending in ']': read the last column that still shows on a zoomed shot.
Boxes: portrait, no portrait ({1c:63}), name plate, last row beside the page arrow, choice windows, the torture line.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import vwf_font  # noqa: E402
from skill import SKILL  # noqa: E402

OUT = ROOT / "work/qa/width"
FONT = vwf_font.load()
TORTURE = ["!\"#$%&'()*+,-./0123456789:;<=>?@", "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_", "abcdefghijklmnopqrstuvwxyz  double  sp"]


def ruler(px):
    """Text exactly px wide: 'n's, dots to make up the rest, ']' last."""
    n, dot, close = FONT["n"][1], FONT["."][1], FONT["]"][1]
    count = (px - close) // n
    rest = px - close - count * n
    while rest % dot:
        count -= 1
        rest += n
    text = "n" * count + "." * (rest // dot) + "]"
    assert vwf_font.text_width(text, FONT) == px
    return text


def rulers(*px):
    return "\n".join(ruler(p) for p in px)


def plate(px):
    return "{0b:08}【 " + ruler(px) + " 】{0b:09}\n"


def overrides(by_index):
    """{string id: text}: the boxes the opening plays in order, each string keeping its own leading control codes."""
    s = by_index
    head = s[16]["read"][:s[16]["read"].index("{0b:08}")]
    # the closing {0c:..} runs the scene on: without it the event stalls
    tail8, tail16 = (s[i]["read"][s[i]["read"].rindex("{0c:"):] for i in (8, 16))
    return {
        # no portrait: rulers on one page, overlong on the next
        s[8]["id"]: "{1c:63}" + "{1a}".join([rulers(216, 210, 204, 216), rulers(222, 216, 216), rulers(240, 248)]) + tail8,
        # plate at the computed limit (216 - 32 px of frames and spaces), then past it
        s[16]["id"]: head + plate(176) + "{1a}".join([rulers(216, 216, 208), plate(180) + rulers(216, 216, 216),
                                                     "\n".join(TORTURE), "M" * 26 + "\n" + "W" * 26 + "\niiii llll ...."]) + tail16,
        s[141]["id"]: ruler(120) + "|" + ruler(216),
        s[143]["id"]: "|".join([ruler(120), ruler(180), ruler(216)] + ["Country"] * (s[143]["read"].count("|") - 2)),
        s[145]["id"]: "|".join([ruler(90), ruler(120), ruler(216)] + ["Class"] * (s[145]["read"].count("|") - 2)),
        s[146]["id"]: "|".join([ruler(100), ruler(150)] + ["Weapon"] * (s[146]["read"].count("|") - 1)),
        s[148]["id"]: "|".join([ruler(276), ruler(240)] + ["Help"] * (s[148]["read"].count("|") - 1)),
        s[150]["id"]: "|".join([ruler(216), ruler(260)] + ["Reason"] * (s[150]["read"].count("|") - 1)),
        s[151]["id"]: "|".join([ruler(276), ruler(240)] + ["Help"] * (s[151]["read"].count("|") - 1)),
    }


def menu_overrides(s):
    """System bank, by index in psx_exe.json: tab, status label, item and help-line rulers."""
    tab = "{0e} {0f}%s{0e} {0f}"
    return {
        "PSX.EXE:20c0d": "-",  # the bank has no spare bytes: this developer's room list makes room for the rulers
        s[51]["id"]: ruler(48), s[52]["id"]: ruler(44), s[55]["id"]: ruler(44), s[48]["id"]: ruler(44),
        s[1496]["id"]: tab % ruler(40), s[1497]["id"]: tab % ruler(44), s[1498]["id"]: tab % ruler(44), s[1500]["id"]: tab % ruler(40),
        s[1499]["id"]: ruler(44), s[1501]["id"]: " " + ruler(276), s[1502]["id"]: " " + ruler(276),
        s[1527]["id"]: "{0e}" + ruler(20), s[1529]["id"]: ruler(20), s[1488]["id"]: ruler(46), s[1487]["id"]: ruler(46),
        s[277]["id"]: ruler(112), s[306]["id"]: ruler(130), s[727]["id"]: ruler(276),
    }


def menu_gate():
    """Field menus need the hero in hand: cold boot to a savestate, then walk the menus with play.py from it."""
    doc = json.loads((ROOT / "script/psx_exe.json").read_text(encoding="utf8"))
    build.build(False, menu_overrides(doc["strings"]), build.OUT, ["PSX.EXE"])
    cue = str(build.OUT.with_suffix(".cue"))
    py = [sys.executable, "-X", "utf8"]
    subprocess.run(py + [str(ROOT / "tools/debug/regen.py"), "field_tavern", "--rom", cue, "--out", "work/qa/width_menu", "--jobs", "1",
                         "--field-frames", "32000", "--state"], check=True, cwd=ROOT)
    session = "work/qa/width_menu/session"
    shutil.rmtree(ROOT / session, ignore_errors=True)
    subprocess.run(py + [f"{SKILL}/scripts/play.py", session, "--rom", cue, "--state", "work/states/field_tavern.sstate", "--script",
                         str(ROOT / "tools/lua/debug_on.lua"), "--wait", "30"], check=True, cwd=ROOT, stdin=subprocess.DEVNULL)
    item = "r2+cross down down down down down circle down down down circle"
    subprocess.run(py + [str(ROOT / "tools/debug/walk.py"), session, "gate", "start", "start circle", "start circle circle",
                         "start circle right circle", item, item + " circle down"], check=True, cwd=ROOT)


def main():
    if "--menu" in sys.argv:
        return menu_gate()
    doc = json.loads((ROOT / "script/res1023.json").read_text(encoding="utf8"))
    if "--no-build" not in sys.argv:
        build.build(False, overrides(doc["strings"]), build.OUT, ["RES#1023"])
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-X", "utf8", f"{SKILL}/scripts/emu.py", str(build.OUT.with_suffix(".cue")), "--out", str(OUT),
           "--route", str(ROOT / "tools/routes/newgame.txt"), "--frames", "22000", "--mash", "100", "--mash-key", "circle",
           "--shot-every", "100", "--timeout", "240"]
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
