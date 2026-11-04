"""textdec.py ENTRY HEX_START HEX_END [--raw]: decode game text bytes from a MAIN.RES entry into readable form (kanji as {hilo} until a table exists)."""
import sys

import res

HIRA = "ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん"
KATA = "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ"
EXTRA = {0x79: "、", 0x7a: "。"}


def decode(b, start=0, end=None):
    i, mode, out = start, 2, []
    end = len(b) if end is None else end
    while i < end:
        c = b[i]
        if c == 0:
            out.append("<00>\n")
            i += 1
        elif c == 1:
            mode = 1
            i += 1
        elif c == 2:
            mode = 2
            i += 1
        elif c == 3:
            mode = 3
            i += 1
        elif c == 0xa:
            out.append("/")
            i += 1
        elif c == 0xc:
            n = b[i + 1]
            out.append(f"<0c:{b[i + 1:i + n].hex()}>")
            i += n
        elif c in (7, 8, 9, 0xb, 0x1b, 0x1c):
            out.append(f"<{c:02x}:{b[i + 1]:02x}>")
            i += 2
        elif c < 0x20:
            out.append(f"<{c:02x}>")
            i += 1
        elif c >= 0x80 and c < 0xfd:
            out.append("{%02x%02x}" % (c, b[i + 1]))
            i += 2
        elif c >= 0xfd:
            out.append(f"<{c:02x}>")
            i += 1
        elif c == 0x7c:
            out.append("|")
            i += 1
        elif mode == 1:
            out.append(chr(c))
            i += 1
        elif c in EXTRA:
            out.append(EXTRA[c])
            i += 1
        else:
            t = HIRA if mode == 2 else KATA
            k = c - 0x21
            out.append(t[k] if 0 <= k < len(t) else f"[{c:02x}]")
            i += 1
    return "".join(out)


if __name__ == "__main__":
    d = res.load()
    idx = int(sys.argv[1])
    o, s = res.table(d)[idx]
    print(decode(d[o:o + s], int(sys.argv[2], 16), int(sys.argv[3], 16)))
