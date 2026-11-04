"""textcodec.py: lossless codec for Bealphareth's text byte stream (PS1, SCPS-10138).

The byte grammar is verified against the engine's own cursor-advance loop at 0x800507A0 and
its char->glyph function at 0x80031648 (see docs/re/text.md):

    00        end of string (strings are NUL-terminated, so 00 is not part of the payload)
    01/02/03  mode: ASCII / hiragana / katakana (sticky; every string starts in hiragana)
    04..06    one byte
    07/08/09  + one argument byte
    0a        newline (one byte)
    0b        + one argument byte
    0c len    inline script opcode; `len` counts from the 0x0c byte
    0d..0f    one byte
    10..19    one byte, "print string variable" (0x10 = hero name)
    1a        one byte, page break
    1b/1c     + one argument byte
    20        space (blank cells) in any mode
    21..7f    one glyph in the current mode (7c is the choice/field separator)
    80..fc    two-byte glyph: 80-87 base kanji font, 9f large font, e0.. scene font
    fd..ff    one byte

A decoded string is text plus `{...}` tokens for everything that is not a glyph:
`{07:12}` is byte 07 with argument 12, `{0c:...}` an inline opcode with hex payload,
`{1a}` a lone code byte. `\\n` stands for 0x0a and `|` for the 0x7c separator.
Mode switches are implicit (encode re-inserts 01/02/03 when the glyph class changes);
a redundant switch in the original becomes an explicit `{01}`/`{02}`/`{03}` token, so
decode/encode is exactly reversible.
"""
import re

# --- glyph tables ------------------------------------------------------------------
# Code c in a kana mode is the character at position c-0x21 of the JIS X 0208 list, except:
#   0x6e -> wa (position 78; ゎ/ヮ is skipped), 0x6f -> wo (81), 0x70 -> n (82),
#   0x71/0x72 -> vu/ka (katakana only). Verified against the decode of on-screen text
#   (は=4f, お=2a, で=47, ン=70, を=6f) and the engine's mode-1/mode-2 branch targets.
JIS_HIRA = ("ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとど"
            "なにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん")
JIS_KATA = ("ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトド"
            "ナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ")

HIRA = {0x6E: JIS_HIRA[78], 0x6F: JIS_HIRA[81], 0x70: JIS_HIRA[82]}
KATA = {0x6E: JIS_KATA[78], 0x6F: JIS_KATA[81], 0x70: JIS_KATA[82], 0x71: JIS_KATA[83], 0x72: JIS_KATA[84]}
for _i in range(0x21, 0x6E):
    HIRA[_i] = JIS_HIRA[_i - 0x21]
    KATA[_i] = JIS_KATA[_i - 0x21]

# Codes 0x73..0x7f are punctuation shared by both kana modes (engine table 0x80097ED8
# maps them to glyph indices 102,105,107,103,104,101,100,97,98,0,99,0,48).
PUNCT = {
    0x73: "ー", 0x74: "〜", 0x76: "'", 0x77: '"', 0x78: "・",
    0x79: "、", 0x7A: "。", 0x7B: "「", 0x7D: "」",
}

ARG1 = {0x07, 0x08, 0x09, 0x0B, 0x1B, 0x1C}
TOKEN_RE = re.compile(r"\{([0-9a-fA-F]*)(?::([0-9a-fA-F]*))?\}")


class Codec:
    """decode/encode with a kanji table: {(hi, lo): char} for two-byte glyph codes."""

    def __init__(self, kanji=None):
        self.kanji = dict(kanji or {})
        self.kanji_rev = {}
        for pair, ch in self.kanji.items():
            self.kanji_rev.setdefault(ch, pair)
        # char -> (mode or None, code byte). None means "no mode switch needed".
        self.rev = {" ": (None, 0x20)}
        for c in range(0x21, 0x7F):
            self.rev.setdefault(chr(c), (1, c))
        for c, ch in HIRA.items():
            self.rev.setdefault(ch, (2, c))
        for c, ch in KATA.items():
            self.rev.setdefault(ch, (3, c))
        for c, ch in PUNCT.items():
            if ch:
                self.rev.setdefault(ch, (None, c))

    # -- decode ------------------------------------------------------------------
    def decode(self, data):
        return self._decode(data, explicit=False)

    def decode_explicit(self, data):
        return self._decode(data, explicit=True)

    def _decode(self, data, explicit):
        out = []
        mode = 2
        i, n = 0, len(data)
        while i < n:
            c = data[i]
            if c in (1, 2, 3):
                if explicit:
                    out.append("{%02x}" % c)
                mode = c
                i += 1
            elif c == 0x0A:
                out.append("\n")
                i += 1
            elif c == 0x0C:
                ln = data[i + 1] if i + 1 < n else 1
                out.append("{0c:%s}" % data[i + 2:i + ln].hex())
                i += max(ln, 2)
            elif c in ARG1:
                if i + 1 < n:
                    out.append("{%02x:%02x}" % (c, data[i + 1]))
                    i += 2
                else:
                    out.append("{%02x}" % c)
                    i += 1
            elif c < 0x20:
                out.append("{%02x}" % c)
                i += 1
            elif c < 0x80:
                if c == 0x20:
                    out.append(" ")
                elif c == 0x7C:
                    out.append("|")
                elif mode == 1:
                    out.append(chr(c))
                else:
                    out.append((HIRA if mode == 2 else KATA).get(c, PUNCT.get(c, "{%02x}" % c)))
                i += 1
            elif c < 0xFD:
                if i + 1 >= n:
                    out.append("{%02x}" % c)
                    i += 1
                    continue
                ch = self.kanji.get((c, data[i + 1]))
                out.append(ch if ch else "{%02x%02x}" % (c, data[i + 1]))
                i += 2
            else:
                out.append("{%02x}" % c)
                i += 1
        return "".join(out)

    # -- encode ------------------------------------------------------------------
    def encode(self, text):
        out = bytearray()
        mode = 2
        i, n = 0, len(text)
        while i < n:
            if text[i] == "{":
                m = TOKEN_RE.match(text, i)
                if not m:
                    raise ValueError("bad token at %d: %r" % (i, text[i:i + 12]))
                code = int(m.group(1), 16) if m.group(1) else 0
                if code in (1, 2, 3):
                    out.append(code)
                    mode = code
                elif code == 0x0C:
                    payload = bytes.fromhex(m.group(2)) if m.group(2) else b""
                    out.append(0x0C)
                    out.append(2 + len(payload))
                    out.extend(payload)
                elif m.group(2) is not None:
                    out.append(code)
                    out.append(int(m.group(2), 16))
                elif 0x80 <= (code >> 8) <= 0xFC:
                    out.append(code >> 8)
                    out.append(code & 0xFF)
                else:
                    out.append(code)
                i = m.end()
                continue
            ch = text[i]
            if ch == "\n":
                out.append(0x0A)
                i += 1
                continue
            if ch == "|":
                out.append(0x7C)
                i += 1
                continue
            entry = self.rev.get(ch)
            if entry is None:
                pair = self.kanji_rev.get(ch)
                if not pair:
                    raise ValueError("no code for %r at %d" % (ch, i))
                out.append(pair[0])
                out.append(pair[1])
                i += 1
                continue
            need, code = entry
            if need is not None and need != mode:
                out.append(need)
                mode = need
            out.append(code)
            i += 1
        return bytes(out)

    # -- exact roundtrip helper ---------------------------------------------------
    def roundtrip(self, data):
        """The text for this string that encodes back to the same bytes, or None."""
        text = self.decode(data)
        try:
            if self.encode(text) == data:
                return text
        except ValueError:
            return None
        text = self.decode_explicit(data)
        try:
            return text if self.encode(text) == data else None
        except ValueError:
            return None


def decode(data, kanji=None):
    return Codec(kanji).decode(data)


def encode(text, kanji=None):
    return Codec(kanji).encode(text)
