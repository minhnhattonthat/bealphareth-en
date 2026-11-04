"""batches.py: translation batches. See docs/translator-brief.md for the format translators see.

    python -X utf8 tools/batches.py split [--chars 3500 --entries 120]   new batches for every string with no `tl` yet
    python -X utf8 tools/batches.py check b001 [b002..]                  validate work/tl/<batch>.out.tsv, exit 1 on errors
    python -X utf8 tools/batches.py merge b001 [b002..]                  check, then write `tl` and `en` into script/*.json
    python -X utf8 tools/batches.py rewrap                               regenerate every `en` from `tl` (after a width change)
    python -X utf8 tools/batches.py placeholders                         fill the scene tables' (仮) dev lines with "..."
    python -X utf8 tools/batches.py fit "English text" [--plate]         show the wrapped pages of one box
    python -X utf8 tools/batches.py status                               strings and JP characters done / left

A string is masked before a translator sees it: leading and trailing codes vanish, each run of inner codes becomes [n],
a lone page break //, a JP line break " / " in dialogue, a mid-string name plate [Name:], variables [HERO], [VAR14].
`tl` holds the English as written (masked), `en` is what the build inserts: `tl` with the codes back and the name plates
translated, word-wrapped to the box by `wrap_pages` (pixel widths from vwf_font). Strings with the same masked text
share one translation.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import vwf_font  # noqa: E402

SCRIPT = ROOT / "script"
TL = ROOT / "work/tl"
TERMS = ROOT / "build"
GLOSSARY = ROOT / "glossary.md"

BOX_W = 216
LAST_W = 208  # the page arrow takes the end of the last row
ROWS = 4
CHOICE_W = 260
MENU_W = 276
PLATE_W = 180
BOOK_W = 252  # original rows run 21-22 kanji (252-264 px); not measured at the limit yet (phase 8)
PARTY_NAME_W = 72
ITEM_NAME_W = 100
SPELL_NAME_W = 124

# Width to reserve for a printed variable: longest hero name, item name, number.
VAR_W = {"10": 56, "11": 72, "12": 72, "13": 100, "14": 100, "15": 72, "16": 72, "17": 72, "18": 72, "19": 30}

# Examine tables hold one line per party slot, in this order (bank order of PSX.EXE names, hero twice for M and F).
SLOTS = ["Hero (male)", "Hero (female)", "Ash", "Arthur", "Leia", "Eleanor", "Pasca", "Rebecca (cut character)",
         "Felcad (cut character)", "Scharn", "Caim (cut character)", "Jessica", "Orpheus", "Eve", "Dias", "Noel",
         "Maleficus (cut character)", "Stella Mira (cut character)", "Luca", "Sara"]

# Developer leftovers: phase 7 blanks these to reclaim bank space, nobody translates them.
DEV_STRINGS = {"PSX.EXE:20b13", "PSX.EXE:20b84", "PSX.EXE:20c0d"}

TOKEN = re.compile(r"\{[^{}]*\}")
JP = re.compile(r"[぀-ヿ一-鿿々]")
GLYPH = re.compile(r"\{[89a-f][0-9a-f]{3}\}")
PLATE_RE = re.compile(r"\{0b:08\}(?:\{0[123]\})?【\s*(.*?)\s*】\{0b:09\}\n?")
SYMBOLS = "○×△□→←▽↑↓"  # drawn from the base font: they travel with the codes around them
MODE = {"{01}", "{02}", "{03}"}
STRUCT = re.compile(r"\[\d+\]|//|\||\[[^\[\]]*:\]")
PLATE_TOKEN = re.compile(r"\[([^\[\]]*):\]")
VAR_MASK = re.compile(r"\[(HERO|VAR1[1-9])\]")


def var_name(token):
    return "HERO" if token == "{10}" else f"VAR{token[1:3]}"


def var_token(name):
    return "{10}" if name == "HERO" else "{" + name[3:] + "}"


def plain_plate(name):
    return re.sub(r"\{0[123]\}", "", name)


def parse(read):
    """Items of a string: ('text', s), ('code', raw), ('page',), ('sep',), ('nl',), ('var', tok), ('plate', jp_name, raw)."""
    items = []
    i = 0
    while i < len(read):
        m = PLATE_RE.match(read, i)
        if m:
            items.append(("plate", plain_plate(m.group(1)), m.group(0)))
            i = m.end()
            continue
        ch = read[i]
        if ch == "{":
            m = TOKEN.match(read, i)
            t = m.group()
            i = m.end()
            if t in MODE:
                continue
            if t == "{1a}":
                items.append(("page",))
            elif re.fullmatch(r"\{1[0-9]\}", t):
                items.append(("var", t))
            else:
                items.append(("code", t))
        elif ch == "\n":
            items.append(("nl",))
            i += 1
        elif ch == "|":
            items.append(("sep",))
            i += 1
        elif ch in SYMBOLS:
            items.append(("code", ch))
            i += 1
        else:
            if items and items[-1][0] == "text":
                items[-1] = ("text", items[-1][1] + ch)
            else:
                items.append(("text", ch))
            i += 1
    return items


def form_of(doc, read):
    if doc["kind"] == "exe":
        return "menu"
    if "{0b:06}" in read and "\n" in read:
        return "book"  # Qumran's library: one scrolling page
    if ":" in TOKEN.sub("", read) and any(page.count("\n") >= 4 for page in read.split("{1a}")):
        return "menu"  # the character sheet keeps its rows
    if "|" not in read:
        return "dlg"
    # first-visit|repeat dialogue also uses |: it wraps like dialogue, a choice list has one row per option
    body = PLATE_RE.sub("", read)
    multi = "\n" in body or "{1a}" in body or PLATE_RE.search(read.split("|", 1)[1])
    return "dlg" if multi else "choice"


class Masked:
    """A string split into what the translator sees and the frame the build keeps."""

    def __init__(self, read, form):
        self.form = form
        self.items = parse(read)
        kinds = [k[0] for k in self.items]
        texty = [n for n, k in enumerate(kinds) if k in ("text", "var")]
        self.has_text = bool(texty)
        if not texty:
            self.head, self.body, self.tail = self.items, [], []
        else:
            self.head = self.items[:texty[0]]
            self.body = self.items[texty[0]:texty[-1] + 1]
            self.tail = self.items[texty[-1] + 1:]
        self.codes = []
        out = []
        n = 0
        run = None
        for it in self.body:
            k = it[0]
            if k == "code":
                if run is None:
                    n += 1
                    run = []
                    self.codes.append(run)
                    out.append(f"[{n}]")
                run.append(it[1])
                continue
            run = None
            if k == "text":
                out.append(it[1])
            elif k == "page":
                out.append(" // ")
            elif k == "sep":
                out.append("|")
            elif k == "nl":
                out.append(r"\n" if form in ("menu", "book") else " / ")
            elif k == "var":
                out.append(f"[{var_name(it[1])}]")
            elif k == "plate":
                out.append(f"[{it[1]}:]")
        self.text = "".join(out)

    def speaker(self):
        for it in self.head:
            if it[0] == "plate":
                return it[1]
        return None

    def starts_portrait(self):
        return any(it[0] == "code" and it[1].startswith("{1c:") for it in self.head)

    def structure(self):
        return STRUCT.findall(self.text)


def is_translatable(m, sid):
    return m.has_text and bool(JP.search(m.text)) and sid not in DEV_STRINGS and "{00}" not in "".join(
        it[1] for it in m.items if it[0] == "code")


def is_placeholder(m, doc):
    """Unfinished examine lines in scene tables ("Pasca / ghost generator OFF (tentative)"): no translator, `...` in-game."""
    return doc["kind"] == "scene" and "(仮)" in m.text


def load_docs():
    return [(p, json.loads(p.read_text(encoding="utf8"))) for p in sorted(SCRIPT.glob("*.json"), key=doc_order)]


def doc_order(path):
    name = path.stem
    if name == "psx_exe":
        return (0, 0)
    if name == "main_exe":
        return (0, 1)
    return (1, int(name[3:]))


def write_doc(path, doc):
    with open(path, "w", encoding="utf8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def read_of(s):
    return s.get("read") or s.get("jp")


# -- glossary -------------------------------------------------------------------------------------------------------

def glossary():
    """(plates {jp: en}, terms [(jp, en, avoid [..], max_px)]) from glossary.md's tables."""
    plates = {}
    terms = []
    section = ""
    for line in GLOSSARY.read_text(encoding="utf8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| JP"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0]:
            continue
        if section.startswith("Name plates"):
            plates[cells[0]] = cells[1]
            continue
        avoid = [a.strip() for a in cells[4].split(",") if a.strip()] if len(cells) > 4 else []
        max_px = int(cells[2]) if len(cells) > 2 and cells[2].isdigit() else None
        for jp in cells[0].split("/"):
            terms.append((jp.strip(), cells[1], avoid, max_px, section))
    return plates, terms


NOT_TERM = re.compile(r"エステル化|新しい世界地図|デューラー公国")  # chemistry, a plain new map, the Duchy of Durer: not Esther, the New World, the Duke


def term_hits(jp_text, terms):
    """Glossary rows whose JP stands in the text as a whole kana run (ミン never matches inside タイミング)."""
    jp_text = NOT_TERM.sub("", jp_text)
    hits = []
    for row in terms:
        jp = row[0]
        for m in re.finditer(re.escape(jp), jp_text):
            a, b = m.start(), m.end()
            left = jp_text[a - 1] if a else ""
            right = jp_text[b] if b < len(jp_text) else ""
            if is_kata(jp[0]) and is_kata(left):
                continue
            if is_kata(jp[-1]) and is_kata(right):
                continue
            if is_hira(jp[0]) and is_hira(left):
                continue
            if is_hira(jp[-1]) and is_hira(right):
                continue
            hits.append(row)
            break
    return hits


def is_kata(c):
    return bool(c) and ("ァ" <= c <= "ヺ" or c == "ー")


def is_hira(c):
    return bool(c) and "ぁ" <= c <= "ゖ"


# -- wrapping -------------------------------------------------------------------------------------------------------

def piece_width(piece, w):
    return sum(w[ord(c) - 0x20] for c in piece)


def wrap_pages(tl, plate_first=False, widths=None, box=BOX_W, last=LAST_W, max_rows=ROWS):
    """Greedy word wrap of one masked page text into rows; returns a list of pages, each a list of row strings.

    [n], plates and variables stay glued to their word. An explicit \\n forces a row end. A plate takes a row."""
    w = widths or vwf_font.widths()

    def word_width(word):
        px = 0
        for part in re.split(r"(\[[^\[\]]*\])", word):
            if not part:
                continue
            if part.startswith("[") and part.endswith("]"):
                v = VAR_MASK.fullmatch(part)
                if v:
                    px += VAR_W["10" if v.group(1) == "HERO" else v.group(1)[3:]]
                continue
            px += piece_width(part, w)
        return px

    space = w[0]
    pages = []
    rows = []
    row = ""
    row_px = 0
    limit_rows = max_rows - (1 if plate_first else 0)

    def row_limit():
        return last if len(rows) == limit_rows - 1 else box

    def flush_row():
        nonlocal row, row_px, rows
        rows.append(row)
        row = ""
        row_px = 0
        if len(rows) >= limit_rows:
            pages.append(rows)
            rows = []
            return True
        return False

    for token in re.split(r"(\\n| )", tl):
        if token in ("", " "):
            continue
        if token == r"\n":
            flush_row()
            continue
        px = word_width(token)
        need = px if not row else row_px + space + px
        if need > row_limit() and row:
            flush_row()
            need = px
        row = token if not row else row + " " + token
        row_px = need
    if row:
        rows.append(row)
    if rows:
        pages.append(rows)
    return pages


def page_px(row, widths=None):
    w = widths or vwf_font.widths()
    px = 0
    for part in re.split(r"(\[[^\[\]]*\])", row):
        if part.startswith("[") and part.endswith("]"):
            v = VAR_MASK.fullmatch(part)
            if v:
                px += VAR_W["10" if v.group(1) == "HERO" else v.group(1)[3:]]
            continue
        px += piece_width(part, w)
    return px


# -- unmask: masked English back to a full string --------------------------------------------------------------------

def raw_items(items, plates):
    out = []
    for it in items:
        k = it[0]
        if k == "code":
            out.append("{02}{75}" if it[1] == "{75}" else it[1])
        elif k == "page":
            out.append("{1a}")
        elif k == "sep":
            out.append("|")
        elif k == "nl":
            out.append("\n")
        elif k == "var":
            out.append(it[1])
        elif k == "plate":
            out.append(plate_code(it[1], plates))
        elif k == "text":
            out.append(it[1])
    return "".join(out)


def plate_code(jp_name, plates):
    if jp_name not in plates:
        raise KeyError(f"name plate not in glossary: {jp_name}")
    return "{0b:08}【 " + expand_vars(plates[jp_name]) + " 】{0b:09}\n"


def expand_vars(text):
    return VAR_MASK.sub(lambda m: var_token(m.group(1)), text)


def unmask(m, tl, plates):
    """The `en` string for masked string m with English tl."""
    head = raw_items(m.head, plates)
    tail = raw_items(m.tail, plates)
    # a plate in the frame shortens that page by a row
    plate_first = any(it[0] == "plate" for it in m.head)
    out = [head]
    if m.form == "book":
        rows = wrap_pages(tl, widths=vwf_font.widths(), box=BOOK_W, last=BOOK_W, max_rows=1 << 30)[0]
        body = re.sub(r"\[(\d+)\]", lambda g: "".join("{02}{75}" if c == "{75}" else c for c in m.codes[int(g.group(1)) - 1]), "\n".join(rows))
        return head + expand_vars(body) + tail
    if m.form != "dlg":
        body = tl
        body = re.sub(r"\[(\d+)\]", lambda g: "".join("{02}{75}" if c == "{75}" else c for c in m.codes[int(g.group(1)) - 1]), body)
        body = re.sub(r"\[([^\[\]]*):\]", lambda g: plate_code(g.group(1), plates), body)
        body = body.replace(r"\n", "\n").replace(" // ", "{1a}").replace("//", "{1a}")
        out.append(expand_vars(body))
        out.append(tail)
        return "".join(out)
    out.append(wrap_dialog(m, tl, plates, plate_first))
    out.append(tail)
    return "".join(out)


def wrap_dialog(m, tl, plates, plate_first):
    """Wrap page by page. Inner [n] codes hold their place in the word stream; a code run that holds a plate or a page
    break starts a new page in the original, and the same // or [Name:] structure is kept here."""
    pieces = re.split(r"(\s*//\s*|\s*\|\s*|\[[^\[\]]*:\])", tl)
    out = []
    plate = plate_first
    w = vwf_font.widths()
    for piece in pieces:
        if not piece:
            continue
        if piece.strip() == "|":
            out.append("|")
            plate = False
            continue
        if re.fullmatch(r"\s*//\s*", piece):
            out.append("{1a}")
            plate = False
            continue
        pl = re.fullmatch(r"\[([^\[\]]*):\]", piece)
        if pl:
            out.append(plate_code(pl.group(1), plates))
            plate = True
            continue
        text = piece.strip()
        if not text:
            continue
        pages = wrap_pages(text, plate, w)
        rendered = "{1a}".join("\n".join(rows) for rows in pages)
        out.append(rendered)
        plate = False
    body = "".join(out)
    body = re.sub(r"\[(\d+)\]", lambda g: "".join("{02}{75}" if c == "{75}" else c for c in m.codes[int(g.group(1)) - 1]), body)
    return expand_vars(body)


# -- examine tables -------------------------------------------------------------------------------------------------

def slot_labels(strings):
    """{index: slot} for party-comment tables: 20 code-less strings per object, slots 0/1 (hero M/F) usually identical."""
    labels = {}
    i = 0
    n = len(strings)

    def simple(s):
        r = read_of(s) or ""
        return "{" not in r.replace("{1a}", "").replace("{10}", "") and "【" not in r and "|" not in r

    while i < n:
        if not simple(strings[i]):
            i += 1
            continue
        j = i
        while j < n and simple(strings[j]):
            j += 1
        run = strings[i:j]
        if len(run) >= 20:
            best = None
            for off in range(20):
                blocks = range(off, len(run) - 19, 20)
                hits = sum(1 for b in blocks if read_of(run[b]) == read_of(run[b + 1]) and read_of(run[b]))
                if blocks and (best is None or hits > best[0]):
                    best = (hits, off, len(blocks))
            # most blocks must open with the identical hero pair: 3-lines-per-character runs pass a looser test by chance
            if best and best[0] * 5 >= best[2] * 4:
                _, off, _ = best
                for k in range(off, len(run) - 19, 20):
                    for slot in range(20):
                        labels[i + k + slot] = SLOTS[slot]
        i = j
    return labels


# -- split ----------------------------------------------------------------------------------------------------------

def collect():
    """Unique untranslated masked strings in story order: [{id, speaker, form, limit, text}]."""
    plates, terms = glossary()
    seen = {}
    done = {}
    for path, doc in load_docs():
        for s in doc["strings"]:
            if s.get("tl"):
                read = read_of(s)
                done[Masked(read, form_of(doc, read)).text] = s["tl"]
    entries = []
    for path, doc in load_docs():
        labels = slot_labels(doc["strings"])
        last = None
        for idx, s in enumerate(doc["strings"]):
            read = read_of(s)
            if not read:
                continue
            form = form_of(doc, read)
            m = Masked(read, form)
            sp = m.speaker()
            if sp:
                last = sp
            if not is_translatable(m, s["id"]) or is_placeholder(m, doc):
                continue
            if m.text in seen or m.text in done:
                continue
            seen[m.text] = True
            speaker = sp or labels.get(idx) or (f"~{last}" if last and m.starts_portrait() else "-")
            entries.append({"id": s["id"], "speaker": speaker, "form": form, "limit": limit_of(doc, form, idx, sp, s), "text": m.text})
    return entries, terms


def limit_of(doc, form, idx, plate, s=None):
    if form == "book":
        return f"{BOOK_W}px"
    if form == "choice":
        # a long list is the help bar of the choice list before it
        help_bar = max(len(o) for o in visible_jp(read_of(s) or "").split("|")) > 16 if s else False
        return f"{MENU_W if help_bar else CHOICE_W}px"
    if form == "menu":
        return f"{exe_limit(doc, idx, s)}px"
    return f"{BOX_W}px*{ROWS - 1 if plate else ROWS}r"


def exe_limit(doc, idx, s):
    """Tightest box a system string is drawn in (docs/re/windows.md). Bank 0.3 is 440 item names, then 440 help lines;
    0.2 is name, help, name, help."""
    if doc["kind"] != "exe" or s is None or doc["source"] != "PSX.EXE":
        return MENU_W
    bank = [x for x in doc["strings"] if x["bank"] == s["bank"]]
    pos = bank.index(s)
    if s["bank"] == "0.0":
        return PARTY_NAME_W
    if s["bank"] == "0.3" and pos < len(bank) // 2:
        return ITEM_NAME_W
    if s["bank"] == "0.2" and pos % 2 == 0:
        return SPELL_NAME_W
    return MENU_W


def visible_jp(text):
    return re.sub(r"\[[^\]]*\]", "", text)


def write_terms(name, text, terms):
    with open(TERMS / f"terms_{name}.txt", "w", encoding="utf8", newline="\n") as f:
        for row in sorted(set((h[0], h[1]) for h in term_hits(text, terms))):
            f.write(f"{row[0]} -> {row[1]}\n")


def cmd_terms(_args):
    """Refresh every batch's term list after a glossary change."""
    _, terms = glossary()
    names = sorted(p.stem for p in TL.glob("b[0-9][0-9][0-9].tsv"))
    for name in names:
        write_terms(name, "\n".join(r["text"] for r in read_batch(name)), terms)
    print(f"{len(names)} term lists")


def cmd_split(args):
    TL.mkdir(parents=True, exist_ok=True)
    TERMS.mkdir(exist_ok=True)
    existing = sorted(int(p.stem[1:]) for p in TL.glob("b[0-9][0-9][0-9]*.tsv") if ".out" not in p.name)
    num = (existing[-1] if existing else 0) + 1
    pending = set()
    for p in TL.glob("b[0-9][0-9][0-9]*.tsv"):
        if ".out" not in p.name:
            for line in p.read_text(encoding="utf8").splitlines():
                pending.add(line.split("\t")[-1])
    entries, terms = collect()
    entries = [e for e in entries if e["text"] not in pending and e["id"].startswith(args.only)]
    batch = []
    chars = 0
    made = 0

    def flush():
        nonlocal batch, chars, num, made
        if not batch:
            return
        name = f"b{num:03d}"
        path = TL / f"{name}.tsv"
        if path.exists():
            sys.exit(f"{path} exists")
        with open(path, "w", encoding="utf8", newline="\n") as f:
            for e in batch:
                f.write("\t".join((e["id"], e["speaker"], e["form"], e["limit"], e["text"])) + "\n")
        text = "\n".join(e["text"] for e in batch)
        write_terms(name, text, terms)
        num += 1
        made += 1
        batch = []
        chars = 0

    for e in entries:
        n = len(visible_jp(e["text"]))
        if batch and (chars + n > args.chars or len(batch) >= args.entries):
            flush()
        batch.append(e)
        chars += n
    flush()
    print(f"{len(entries)} entries in {made} new batches, last b{num - 1:03d}")


# -- check ----------------------------------------------------------------------------------------------------------

def read_batch(name):
    rows = []
    for line in (TL / f"{name}.tsv").read_text(encoding="utf8").splitlines():
        p = line.split("\t")
        rows.append({"id": p[0], "speaker": p[1], "form": p[2], "limit": p[3], "text": "\t".join(p[4:])})
    return rows


def read_out(name):
    out = TL / f"{name}.out.tsv"
    if not out.exists():
        return None
    res = []
    for n, line in enumerate(out.read_text(encoding="utf8").splitlines(), 1):
        if not line.strip():
            continue
        if "\t" not in line:
            res.append((f"line{n}", None))
            continue
        i, en = line.split("\t", 1)
        res.append((i, en))
    return res


HONORIFIC = re.compile(r"([ァ-ヺー]|\[HERO\])(さん|ちゃん|くん|君|さま|様|殿)")
NOT_HONORIFIC = re.compile(r"オレ様|カドモン様|アネさん|アニさん|オジさん|オバさん|オヤジさん|オニイさん|オネエさん|ニイちゃん|ネエちゃん|バアさん|ジイさん")  # words, not names
HON_EN = {"さん": "-san", "ちゃん": "-chan", "くん": "-kun", "君": "-kun", "さま": "-sama", "様": "-sama", "殿": "-dono"}
ORDINAL = re.compile(r"\[[^\]]*\](st|nd|rd|th)\b")


def check_entry(e, en, terms, plates):
    """Errors for one entry."""
    errs = []
    jp = e["text"]
    if en is None or not en.strip():
        return ["empty"]
    bare = PLATE_TOKEN.sub("", en)  # a mid-string plate token stays as given, Japanese name included
    if any(not (32 <= ord(c) < 127) for c in bare):
        bad = sorted({c for c in bare if not 32 <= ord(c) < 127})
        errs.append(f"non-ASCII {bad}")
    if "`" in bare:
        errs.append("backtick is not a quote in this font")
    if re.search(r"\\(?!n)", bare):
        errs.append("backslash other than \\n")
    if "{" in bare or "}" in bare:
        errs.append("braces: control codes are [n] here")
    if " / " in bare:
        errs.append("' / ' is a Japanese line break marker; the tool wraps English, drop it")
    a, b = STRUCT.findall(jp), STRUCT.findall(en)
    if a != b:
        errs.append(f"structure {a} != {b}")
    for t in PLATE_TOKEN.findall(en):
        if t not in plates:
            errs.append(f"name plate {t} not in glossary")
    va, vb = sorted(VAR_MASK.findall(jp)), sorted(VAR_MASK.findall(en))
    if va != vb:
        errs.append(f"variables {va} != {vb}")
    if ORDINAL.search(en):
        errs.append("ordinal suffix glued to a variable")
    if e["form"] == "book":
        return errs + [f"glossary: {r[0]} -> {r[1]}" for r in term_hits(jp, terms) if r[1].lower() not in en.lower()]
    if e["form"] == "menu" and jp.count(r"\n") != en.count(r"\n"):
        errs.append("line count differs from the original (menu text keeps its \\n)")
    if e["form"] == "choice" or e["form"] == "menu":
        limit = int(e["limit"].rstrip("px").split("*")[0])
        for opt in re.split(r"\||\\n", en):
            px = page_px(opt)
            # shortcut: two variables at full budget at once are not a real row; phase 7 measures the actual values
            if px > limit and len(VAR_MASK.findall(opt)) < 2:
                errs.append(f"{opt!r} is {px}px, limit {limit}px")
    for row in term_hits(PLATE_TOKEN.sub("", jp), terms):  # a mid-string plate is copied as is
        jp_term, en_term = row[0], row[1]
        first, _, rest = en_term.partition(" ")
        exact = en_term in en or (rest and f"{first}s {rest}" in en) or (row[4].startswith("Items") and en_term.lower() in en.lower())  # "Pillars of Sheol"
        if not exact:
            errs.append(f"glossary: {jp_term} -> {en_term}")
    for row in terms:
        for av in row[2]:
            if re.search(rf"\b{re.escape(av)}\b", en):
                errs.append(f"avoid spelling {av!r} (use {row[1]})")
    named = NOT_HONORIFIC.sub("", jp)
    for hon in HON_EN:
        n = sum(1 for m in HONORIFIC.finditer(named) if m.group(2) == hon)
        if n and en.count(HON_EN[hon]) < n:
            errs.append(f"honorific {hon}: expected {HON_EN[hon]}")
    return errs


def cmd_check(args):
    plates, terms = glossary()
    bad = 0
    for name in args.batch:
        errors = check_batch(name, plates, terms)
        for e in errors:
            print(e)
        if errors:
            bad += 1
        else:
            print(f"{name} OK")
    sys.exit(1 if bad else 0)


def check_batch(name, plates, terms):
    rows = read_batch(name)
    out = read_out(name)
    if out is None:
        return [f"{name}: no {name}.out.tsv"]
    errors = []
    want = [r["id"] for r in rows]
    got = [i for i, _ in out]
    if want != got:
        miss = set(want) - set(got)
        extra = set(got) - set(want)
        dup = {i for i in got if got.count(i) > 1}
        errors.append(f"{name}: ids differ: missing {sorted(miss)[:8]} extra {sorted(extra)[:8]} dup {sorted(dup)[:8]}"
                      + (" (same set, wrong order)" if not (miss or extra or dup) else ""))
    en = dict(out)
    for r in rows:
        if r["id"] in en:
            for msg in check_entry(r, en[r["id"]], terms, plates):
                errors.append(f"{r['id']}: {msg}")
    return errors


# -- merge ----------------------------------------------------------------------------------------------------------

def cmd_merge(args):
    plates, terms = glossary()
    new = {}
    for name in args.batch:
        errors = check_batch(name, plates, terms)
        if errors:
            for e in errors:
                print(e)
            sys.exit(f"{name}: refusing to merge")
        en = dict(read_out(name))
        for r in read_batch(name):
            new[r["text"]] = en[r["id"]]
    total = 0
    for path, doc in load_docs():
        changed = False
        for s in doc["strings"]:
            read = read_of(s)
            if not read:
                continue
            m = Masked(read, form_of(doc, read))
            if m.text in new and is_translatable(m, s["id"]):
                tl = new[m.text]
                s["tl"] = tl
                s["en"] = unmask(m, tl, plates)
                s["status"] = "done"
                changed = True
                total += 1
        if changed:
            write_doc(path, doc)
    print(f"merged {len(new)} translations into {total} strings")


def cmd_rewrap(_args):
    plates, _ = glossary()
    total = 0
    for path, doc in load_docs():
        changed = False
        for s in doc["strings"]:
            if s.get("tl"):
                read = read_of(s)
                m = Masked(read, form_of(doc, read))
                en = unmask(m, s["tl"], plates) if not is_placeholder(m, doc) else s.get("en")
                if en != s.get("en"):
                    s["en"] = en
                    changed = True
                    total += 1
        if changed:
            write_doc(path, doc)
    print(f"rewrapped {total} strings")


def cmd_placeholders(_args):
    plates, _ = glossary()
    total = 0
    for path, doc in load_docs():
        changed = False
        for s in doc["strings"]:
            read = read_of(s)
            if not read:
                continue
            m = Masked(read, form_of(doc, read))
            if is_translatable(m, s["id"]) and is_placeholder(m, doc) and not s.get("tl"):
                s["tl"] = "..."
                s["en"] = "".join(raw_items(part, plates) for part in (m.head,)) + "..." + raw_items(m.tail, plates)
                s["status"] = "placeholder"
                changed = True
                total += 1
        if changed:
            write_doc(path, doc)
    print(f"filled {total} placeholder strings")


def cmd_fit(args):
    pages = wrap_pages(args.text, args.plate)
    for p, rows in enumerate(pages, 1):
        for row in rows:
            print(f"p{p} {page_px(row):3d}px {row}")
    print(f"{len(pages)} page(s)")


def cmd_status(_args):
    done = todo = done_c = todo_c = 0
    for path, doc in load_docs():
        for s in doc["strings"]:
            read = read_of(s)
            if not read:
                continue
            m = Masked(read, form_of(doc, read))
            if not is_translatable(m, s["id"]):
                continue
            n = len(visible_jp(m.text))
            if s.get("tl"):
                done += 1
                done_c += n
            else:
                todo += 1
                todo_c += n
    print(f"done {done} strings, {done_c} JP chars; left {todo} strings, {todo_c} JP chars")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("split")
    p.add_argument("--chars", type=int, default=3500)
    p.add_argument("--entries", type=int, default=120)
    p.add_argument("--only", default="", help="id prefix, e.g. RES#1023: for one source")
    p.set_defaults(func=cmd_split)
    p = sub.add_parser("check")
    p.add_argument("batch", nargs="+")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("merge")
    p.add_argument("batch", nargs="+")
    p.set_defaults(func=cmd_merge)
    sub.add_parser("rewrap").set_defaults(func=cmd_rewrap)
    sub.add_parser("placeholders").set_defaults(func=cmd_placeholders)
    sub.add_parser("terms").set_defaults(func=cmd_terms)
    p = sub.add_parser("fit")
    p.add_argument("text")
    p.add_argument("--plate", action="store_true")
    p.set_defaults(func=cmd_fit)
    sub.add_parser("status").set_defaults(func=cmd_status)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
