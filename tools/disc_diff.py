"""disc_diff.py: the build changed only what it may (phase 7 check, in place of a whole-image romdiff: every file moves in a
rebuilt disc). work/en/tree against work/disc/tree. Exits 1 on any change outside:
  MAIN.RES  entries with script text, still pages, sprite sheets, the logo; never a size
  PSX.EXE   the system block
  MAIN.EXE  the armips .org areas of asm/vwf.asm, the loose-string pool, pointer slots of relocated strings
  PROLO.STR video sectors; XA audio stays byte for byte
  anything else: unchanged."""
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import extract  # noqa: E402
import insert  # noqa: E402
import res  # noqa: E402
import sprites  # noqa: E402
import stills  # noqa: E402
import strfmv  # noqa: E402
import titlelogo  # noqa: E402

OLD, NEW = ROOT / "work/disc/tree", ROOT / "work/en/tree"
ASM_ROOM = 0x2000  # bytes after an .org that may belong to it; a run further out is reported


def runs(a, b):
    """(start, end) of the differing stretches, joined across gaps under 16 bytes."""
    out = []
    i, n = 0, min(len(a), len(b))
    step = 4096
    while i < n:
        if a[i:i + step] == b[i:i + step]:
            i += step
            continue
        for j in range(i, min(i + step, n)):
            if a[j] != b[j]:
                if out and j - out[-1][1] < 16:
                    out[-1][1] = j + 1
                else:
                    out.append([j, j + 1])
        i += step
    return out


def check_res(a, b, bad):
    table = res.table(a)
    ok = {titlelogo.ENTRY, titlelogo.END_ENTRY, insert.SYSTEM_RES}
    for path in (ROOT / "script").glob("res*.json"):
        ok.add(json.loads(path.read_text(encoding="utf8"))["entry"])
    ok |= {p["entry"] for p in stills.pages()}
    wanted = {}
    for p in sprites.pages():
        wanted[p["sheet"]] = p
    keys = set()
    rows = list(sprites.all_sheets(a, table))
    import hashlib
    for sid, entry, at, w, h, comp, raw, pal, flags in rows:
        if sid in wanted:
            keys.add(hashlib.md5(raw).hexdigest())
    for sid, entry, at, w, h, comp, raw, pal, flags in rows:
        if hashlib.md5(raw).hexdigest() in keys:
            ok.add(entry)
    changed = 0
    for e, (o, s) in enumerate(table):
        if a[o:o + s] != b[o:o + s]:
            changed += 1
            if e not in ok:
                bad.append(f"MAIN.RES #{e} changed, nothing should touch it")
    end = max(o + s for o, s in table)
    if a[:table[0][0]] != b[:table[0][0]]:
        bad.append("MAIN.RES table changed")
    if a[end:] != b[end:]:
        bad.append("MAIN.RES tail changed")
    return changed


def check_main(a, b, bad):
    src = (ROOT / "asm/vwf.asm").read_text(encoding="utf8")
    orgs = sorted(int(m, 16) - insert.MAIN_FILE_BASE for m in re.findall(r"\.org\s+0x([0-9A-Fa-f]+)", src))
    n = 0
    for s, e in runs(a, b):
        n += 1
        if any(lo <= s and e <= hi for lo, hi in extract.MAIN_TEXT):
            continue
        if extract.MAIN_TABLE[0] <= s and e <= extract.MAIN_TABLE[1]:  # slots of repointed strings
            continue
        before = [o for o in orgs if o <= s]
        if before and s - before[-1] <= ASM_ROOM:
            continue
        bad.append(f"MAIN.EXE {s:#x}-{e:#x}: no .org or text area covers it")
    return n


def check_str(a, b, bad):
    n = 0
    for i in range(len(a) // strfmv.SECTOR):
        x, y = a[i * strfmv.SECTOR:(i + 1) * strfmv.SECTOR], b[i * strfmv.SECTOR:(i + 1) * strfmv.SECTOR]
        if x != y:
            n += 1
            if struct.unpack_from("<I", x, strfmv.SUB)[0] != strfmv.MAGIC:
                bad.append(f"PROLO.STR sector {i} is not video but changed")
    return n


def main():
    bad = []
    report = []
    for old in sorted(p for p in OLD.rglob("*") if p.is_file()):
        rel = old.relative_to(OLD)
        new = NEW / rel
        a, b = old.read_bytes(), new.read_bytes()
        if len(a) != len(b):
            bad.append(f"{rel} changed size")
        elif a == b:
            continue
        elif rel.name == "MAIN.RES":
            report.append(f"MAIN.RES {check_res(a, b, bad)} entries")
        elif rel.name == "MAIN.EXE":
            report.append(f"MAIN.EXE {check_main(a, b, bad)} runs")
        elif rel.name == "PSX.EXE":
            for s, e in runs(a, b):
                if not (insert.SYSTEM_DELTA <= s and e <= insert.SYSTEM_DELTA + insert.SYSTEM_SIZE):
                    bad.append(f"PSX.EXE {s:#x}-{e:#x} outside the system block")
            report.append("PSX.EXE system block")
        elif rel.name == "PROLO.STR":
            report.append(f"PROLO.STR {check_str(a, b, bad)} sectors")
        else:
            bad.append(f"{rel} changed")
    print("; ".join(report))
    for line in bad[:60]:
        print(line)
    print(f"{len(bad)} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
