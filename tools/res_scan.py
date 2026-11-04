"""res_scan.py: per-entry survey of MAIN.RES. Prints an entry's size, first bytes, and its Shift-JIS runs with kana. Read-only."""
import collections
import re
import sys

import res

# Shift-JIS double-byte run; kana required so TIM pixels drop out
RUN = re.compile(rb"(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]){4,}")


def has_kana(b):
    kana = sum(1 for i in range(0, len(b), 2) if b[i] in (0x82, 0x83))
    return kana >= max(2, len(b) // 8)


def runs(buf):
    for m in RUN.finditer(buf):
        if has_kana(m.group()):
            try:
                yield m.start(), m.group().decode("cp932")
            except UnicodeDecodeError:
                pass


def main():
    d = res.load()
    heads = collections.Counter()
    out = open(sys.argv[1] if len(sys.argv) > 1 else "work/qa/res_entries.txt", "w", encoding="utf-8")
    hit = 0
    for i, o, s, b in res.entries(d):
        rs = list(runs(b))
        heads[b[:4].hex()] += 1
        chars = sum(len(t) for _, t in rs)
        print(i, hex(o), s, b[:16].hex(), "runs", len(rs), "chars", chars, file=out)
        if rs:
            hit += 1
            for off, t in rs[:6]:
                print("   ", hex(off), t[:60], file=out)
    print("entries", len(res.table(d)), "with text", hit)
    print(heads.most_common(25))


main()
