# Text: encoding, banks, font

No Shift-JIS game text anywhere; a raw SJIS scan finds only debug and save-title strings. Finding method: on-screen 「今回はお前で」 searched in RAM, then `tools/lua` watch on readers.

## Message banks (verified: code at 0x80050950-0x80050A88, and `tools/mscan.py` parses the whole disc)

```
'M4' u16 n, u32 off[n+1]   // offsets from the bank start; each part is an M2 bank
'M2' u16 n, u16 off[n+1]   // offsets from the bank start; each string is NUL-terminated
```
`lbu 0(a0)=='M'`; second byte '4' or '2' picks the width. Lookup: 0x80050974 (bank, i), 0x80050B84 (bank, id), 0x80050C1C (id, from the global bank pointer at 0x800BEAB0 = 0x801BE52C at run time).

`tools/mscan.py` (+ `work/qa/banks.tsv`): 15 M4 and 325 M2 banks, **60,464 unique strings, 2.78 MB** (66,579 / 3.0 MB with duplicates; repeated banks: e.g. #1194/1195/1196/1198, #6/#7). Its M4 count is low: it only accepts an M4 whose parts are all M2, so the usual scene form (glyphs + M2) is counted through its M2. **The scene form is `M4 [glyph part, M2 part]` and occurs 264 times** (`tools/extract.py` scans for it); `tools/extract.py` is the authoritative scanner now.
- The M2 in a scene holds the event script: each string is one event chunk (text + inline script opcodes).
- `PSX.EXE` +0x1B4C0 M4 (7 parts, 1,737 strings, 30,660 bytes): system text: items, skills, status. **`RES#3927` holds a second copy of the same M4**: keep in sync.
- **`MAIN.EXE` has raw strings too**, NUL-separated with no bank (196 of them: ability/trap help at 0x3400, debug labels): phase 4 extracts them (`raw_blocks` in `tools/extract.py`).

## Encoding (verified: 今 80EB, 回 82CF, は 4F, お 2A, で 47, decoded lines match the screen)

Byte stream, mode-shifted. The grammar below is **verified against the engine's own code**, not guessed: `0x800507A0` is the measure loop (it walks the string to compute width) and `0x80031648` maps a byte to a glyph index; both were disassembled and the branch targets read (see `tools/textcodec.py`, which mirrors them).
| Byte | Meaning |
|---|---|
| `00` | end of string |
| `01` / `02` / `03` | mode: ASCII / hiragana / katakana (sticky; every string starts in hiragana) |
| `04` `05` `06` `0D` `0E` `0F` | one-byte codes |
| `07 08 09 0B 1B 1C` + 1 byte | two-byte codes: `0B 08`/`0B 09` colour on/off around the name; `1C nn` portrait/box |
| `0A` | newline. `1A` page break (waits for a press) |
| `0C len ...` | inline script opcode, **`len` counts from the 0C byte** (the measure loop does `s0 += len`) |
| `10`-`19` | one-byte "print string variable" codes (0x8004FCFC, table 0x800BE5D0, stride 48: 10 = hero name) |
| `20` | space (blank cells in any mode; the drawer special-cases it) |
| `21`-`7F` | one glyph in the current mode. `7C` is also the choice/field separator (an alternative terminator at 0x800508C0) |
| `80`-`FC` xx | two-byte glyph, font index `(hi-0x80)*112 + (lo-0x80)` for hi 80-87; `9F` large glyph (88 bytes/cell, table 0x80031610); `E0`+ scene font |
| `FD`-`FF` | one-byte codes |

**Kana tables (verified).** In a kana mode the byte is the character at position `c-0x21` of the JIS X 0208 list, except at the tail, where the engine skips the archaic kana:

| byte | hiragana | katakana |
|---|---|---|
| `6E` | わ | ワ |
| `6F` | を | ヲ |
| `70` | ん | ン |
| `71` | – | ヴ |
| `72` | – | ヵ |

`6E` is the engine's special case (mode 1 returns 0xBA, mode 2 0x10D) and `6F`+ get `+0x4E`/`+0xA1`; that shift is what makes `6F` を and `70` ン rather than ゐ/ヰ. **The old table in this file (JIS order to the end) decoded を as わ and ン as ヰ** — corrected here, proven by the system message bank reading 「ボタンでアイテムを…」.

Bytes `73`-`7F` are punctuation shared by both kana modes; the engine looks them up in a small table at `0x80097ED8` (glyph indices 102,105,107,103,104,101,100,97,98,0,99,0,48):

`73`=ー `74`=〜 `76`=' `77`=" `78`=・ `79`=、 `7A`=。 `7B`=「 `7D`=」 (`7C` is the separator, no glyph; `75`/`7E`/`7F` are unused and kept as tokens).

Arg counts above are from the disassembly; the roundtrip in `tests/test_text.py` proves them on all 61,794 extracted strings.

## Font 11x11 (verified, and now read automatically)

- 11x11, MSB-first packed 121 bits in a 16-byte cell. Kanji base **RAM 0x801BAD4C** (`PSX.EXE` file 0x17CE0), 896 cells = 8 rows of 112 (`(hi-0x80)*112 + (lo-0x80)`). Verified: 今 at +0x6B0 and 回 at +0x12F0 match screenshots.
- **The font is MS Gothic 12 px, cropped to 11x11** (the glyph's ink covers x 1..11, y 0..10 of the 12 px cell). 1513 of the 1909 distinct glyph cells on the disc match a modern MS Gothic render *bit for bit*; the rest differ by a few strokes (the game shipped an older revision of the same font). `tools/fontmap.py` matches every cell against an MS Gothic 12 px bitmap set, accepts near matches by IoU, and writes `tbl/glyphs.tsv`; low-confidence cells go to label sheets and `tbl/glyphs_manual.tsv`. Verified by reading decoded text: 名前を入力してください / 初老の男 / 今からする質問に答えろ.
- One-byte fonts: ASCII at file 0x16B90 (idx = c-0x21), hiragana at 0x17250 (108), katakana at 0x17780 (191); all inside the same 16-byte-cell table addressed as `fontbase + 0xBE8 + idx*16` (draw 0x800314CC, font pointer = `*(gp+0x8E4)` set at 0x8004FEC4 from bank 0 of 0x801B9000). The kana glyphs are a custom pixel font, not MS Gothic, so their code order comes from the engine code above, not OCR.
- Scene fonts: a scene's M4 part 0 is a glyph bank of 16-byte cells, addressed by `E0`+ codes as `(hi-0xE0)*112 + (lo-0x80)`. 264 scene fonts hold 1,399 distinct glyph bitmaps; all but 115 are identified.
- Drawing: 0x800317F8 (code, height 0xB) with the font pointer at gp+0x8E4; caller 0x8004F244 advances **12 px per full glyph, 6 px when bit 0 of s3 is set (half-width mode exists)**. Rasterised 4bpp into a VRAM text cache around x=896, y=0 (`tools/vramview.py --4bpp 896,0,128,256`).
- No per-glyph width table seen. English needs VWF or the half-width path: phase 5.

## Extraction (phase 4)

`tools/extract.py` writes `script/<source>.json`: one file per message-bank source (MAIN.EXE, PSX.EXE, RES#N), one entry per string with `id` (source:file offset), `off`, `len`, `bank`, `jp`, `en`, `status`. Ids are address-based and the JSON keeps `jp` beside `en` for diffs.
- **61,794 strings from 279 sources**: 1,737 in the PSX.EXE system M4 (items, skills, names, status), 154-880 per scene overlay, 196 loose strings in MAIN.EXE (ability/trap help, NUL-separated outside any bank).
- **Roundtrip is exact for all 61,794** (`tests/test_text.py`, run from the original disc). Strings whose original stream carried a redundant mode switch keep it as an explicit `{01}`/`{02}`/`{03}` token, so nothing is lost.
- 2.2% of glyph instances decode to a `{hi lo}` token because that cell's character is not yet identified (115 distinct cells, see the review sheets `work/qa/glyphs/`). Same for the 16 `9F` large-glyph cells.
- Coverage: every M4/M2 bank on the disc is found and its strings tile the bank (test), and `script/` is regenerated from the disc in the test, so a stale dump fails. Loose text outside banks is found by a density heuristic (`raw_blocks`), which is the one place a string could still be missed; the phase-5 marker build with `jp_left.py` is the backstop for that.


## Reader map

0x8004FB7C: string copy/expand with variables. 0x800507A0: measure. 0x800511D8: find a code. 0x8004F1D0-0x8004F444: draw loop. 0x8004F9C0: text pager.

## Debug leftovers

`MAIN.EXE` strings `ITEM SET`/`TIME SET` (file 0xDC4), `KURI DEBUG` (0xDD0), `Not found attack mask` style messages: these belong to the leftover debug menu, which exists and opens with R2+Cross (`docs/re/warp.md`).
