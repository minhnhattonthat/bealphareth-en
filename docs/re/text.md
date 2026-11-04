# Text: encoding, banks, font

No Shift-JIS game text anywhere; a raw SJIS scan finds only debug and save-title strings. Finding method: on-screen 「今回はお前で」 searched in RAM, then `tools/lua` watch on readers.

## Message banks (verified: code at 0x80050950-0x80050A88, and `tools/mscan.py` parses the whole disc)

```
'M4' u16 n, u32 off[n+1]   // offsets from the bank start; each part is an M2 bank
'M2' u16 n, u16 off[n+1]   // offsets from the bank start; each string is NUL-terminated
```
`lbu 0(a0)=='M'`; second byte '4' or '2' picks the width. Lookup: 0x80050974 (bank, i), 0x80050B84 (bank, id), 0x80050C1C (id, from the global bank pointer at 0x800BEAB0 = 0x801BE52C at run time).

`tools/mscan.py` (+ `work/qa/banks.tsv`): 15 M4 and 325 M2 banks, **60,464 unique strings, 2.78 MB** (66,579 / 3.0 MB with duplicates; repeated banks: e.g. #1194/1195/1196/1198, #6/#7). Its M4 count is low: it only accepts an M4 whose parts are all M2, so the usual scene form (glyphs + M2) is counted through its M2. Strings are correct; some early M2 hits may be false (phase 4 proves them by roundtrip). M4 parts may be glyphs (see E0xx) or images (#1049 part 1 is a palette + tiles).
- The M2 in a scene holds the event script: each string is one event chunk (text + inline script opcodes).
- `PSX.EXE` +0x1B4C0 M4 (7 parts, 1,737 strings, 30,660 bytes): system text: items, skills, status. **`RES#3927` holds a second copy of the same M4**: keep in sync.
- **`MAIN.EXE` has raw strings too**, NUL-separated with no bank, e.g. file 0x3725 `01 48 50 02 ...` (status help). Phase 4 needs a sweep for these, and for literal tables in scene code, with `jp_left`-style checks.

## Encoding (verified: 今 80EB, 回 82CF, は 4F, お 2A, で 47, decoded lines match the screen)

Byte stream, mode-shifted:
| Byte | Meaning |
|---|---|
| `00` | end of string |
| `01` / `02` / `03` | mode: ASCII / hiragana / katakana (sticky; every string starts in hiragana) |
| `0A` | newline. `1A` page break (waits for a press) |
| `07 08 09 0B 1B 1C` + 1 byte | two-byte codes: `0B 08`/`0B 09` colour on/off around the name; `1C nn` portrait/box |
| `0C len ...` | inline script opcode, **`len` counts from the 0C... skipping `len` bytes from the length byte** (see the skip at 0x8005084C) |
| `0E 0F 10-1A` | variables and printer codes; `10-1A` print a string variable (0x8004FCFC, table 0x800BE5D0, stride 48: 10 = hero name) |
| `7C` `|` | field separator: an alternative terminator (choice lists, random lines; 0x800508C0, 0x80050FF0) |
| `20-7F` | one glyph, by mode. Hiragana ぁ=0x21 ... ろ, わ, を, ん, in JIS order without ゎゐゑ; katakana the same with its own extras; 0x78 ・, 0x79 、, 0x7A 。 Table in `tools/textdec.py` needs its tail corrected (わ/を/ん shift by one) |
| `80-9E xx`, `A0-FC xx` | two-byte kanji, font index `(hi-0x80)*112 + (lo-0x80)` |
| `9F xx` | large glyph, 88 bytes per cell, from a separate table (0x80031610) |
| `FD-FF` | one-byte codes (0x8005088C) |

**`E0 xx` = per-scene extra kanji (verified):** a scene's `M4` part 0 is a bank of 16-byte 11x11 glyphs, cell `lo-0x80`: glyph 0 of #1023's part 0 (scene +0x22FDC) is 老, and 老 is E080 in 初老の男 on screen. Part 1 is the M2 script. So a kanji decode table is per scene for E0xx (read glyphs, not codes), and English builds can drop part 0.

Arg counts above are from 0x8004FBA4-0x8004FD8C and 0x800507C8-0x800508E8 (string copy and measure). Phase 4 must prove them with a roundtrip over all banks.

## Font (verified)

- 11x11, MSB-first packed 121 bits in a 16-byte cell. Kanji base **RAM 0x801BAD4C** (`PSX.EXE` file 0x17CE0): 今 at +0x6B0 and 回 at +0x12F0 match the screen bit for bit (`tools/fontfind2.py`). 896 cells (hi 80-87, lo 80-EF, 112 per row) end near 0x801BE54C, just before the system M4 at 0x801BE52C (overlap: check phase 4).
- One-byte font: a0+0xBE8+idx*16 (0x800314CC), with idx from 0x80031648: mode 0 (ASCII) c-0x21; other modes through table 0x80087EE4 and offsets. ア at 0x801BA7EC.
- Drawing: 0x800317F8 (code, height 0xB) with font pointer at gp+0x8E4; caller 0x8004F244 advances **12 px per full glyph, 6 px when bit 0 of s3 is set (half-width mode exists)**. Rasterised 4bpp into a VRAM text cache around x=896, y=0 (`tools/vramview.py --4bpp 896,0,128,256`).
- No per-glyph width table seen. English needs VWF or the half-width path: phase 5.

## Reader map

0x8004FB7C: string copy/expand with variables. 0x800507A0: measure. 0x800511D8: find a code. 0x8004F1D0-0x8004F444: draw loop. 0x8004F9C0: text pager.

## Debug leftovers

`MAIN.EXE` strings `ITEM SET`/`TIME SET` (file 0xDC4), `KURI DEBUG` (0xDD0), `Not found attack mask` style messages: these belong to the leftover debug menu, which exists and opens with R2+Cross (`docs/re/warp.md`).
