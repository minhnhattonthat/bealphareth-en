"""ramscan.py RAM.bin [min_chars]: list Shift-JIS runs with kana in a PS1 RAM dump, as KSEG0 addresses."""
import re
import sys

RUN = re.compile(rb"(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){4,}")


def main():
    d = open(sys.argv[1], "rb").read()
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    for m in RUN.finditer(d):
        b = m.group()
        try:
            t = b.decode("cp932")
        except UnicodeDecodeError:
            continue
        kana = sum("ぁ" <= c <= "ヿ" for c in t)
        if len(t) >= n and kana >= 2:
            print(f"{0x80000000 + m.start():08x} {t}")


main()
