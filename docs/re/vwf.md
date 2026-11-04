# English engine: VWF and text insertion (phase 5)

**Decision: variable-width font**, not the 6 px half-width path. The engine composes text in one function, so a VWF costs a handful of patches and gives ~37 average letters per dialogue line instead of 36 fixed ones with wider words, and it reads far better. **verified** in the opening (`work/qa/m5m`), rulers and torture line in `tools/width_gate.py`.

## How the renderer works (verified by disassembly and the marker build)

- `0x8004EBE0(sprite, text, box)` draws a string: a2 = `{i16 W, i16 H}` in half-cells and rows (dialogue: `gp+0x598` = 36 x 4), or 0 for free text. Pen: `0x28(sp)` column, `0x2C(sp)` row, `$s7` position in the current block.
- Text goes into **48 x 12 px 4bpp blocks** (`0x180`-byte buffer, row stride 0x18), each one sprite in a chain, uploaded to the VRAM cache at `x=0x380+12*(id%5), y=12*(id/5)` by `0x8004F7A4`. A block ends when full, on a newline, or on a page end. Sprite y = row * 16.
- One-byte glyphs: `0x800317F8` paints a 4bpp cell (full-size font, or half-width font when mode bit 2 is clear), `0x8004F854` copies it into the block.
- `0x800507A0` measures a string in half-cells for centring and window sizes (31 callers through `0x80050700`).
- Three more drawers (`0x8003A354`, `0x8003C80C`, `0x8003DE10`) lay out name labels in fixed 8 px VRAM cells; they use the half-width painter. See "Open" below.

## The patch (`asm/vwf.asm`)

The pens are in **pixels**. Patches to the draw loop: sprite x is the pen; the block flush test allows 8 px more; the wrap test compares against `W*6`; `0x8004F854` now copies at any pixel with OR; the kana path moves the pen by 6/12. One-byte codes jump to `vwf_char`:

- **ASCII mode (`01`)**: the glyph is read from the half-width cells (index `c-0x21`, 11 rows, 1 byte per row, 8 px max) and painted straight into the block, then the pen moves by the width table. Space only moves the pen.
- **kana modes**: the original path. Untranslated Japanese still draws, which is what makes a partial build readable.

Measure counts pixels too and returns half-cells rounded up, so its callers keep working. A printed variable is multiplied back to pixels on the way through.

Resident code and the 95-byte width table live over **unused half-width kana cells** at `0x801B9420` (0x7DC bytes free up to `0x801B9BFC`). The font is `fonts/vwf.txt` (ASCII art, `tools/vwf_font.py`), seeded from the game's own full-width ASCII cells and hand-fixed.

## Where the bank lives (verified, it cost a hang)

`0x801B9000` is **not** loaded from `RES#3927`. `PSX.EXE` copies `0x12640` bytes from its own file offset `0x15F94` at boot (`0x800D5D1C`; the length is a word at `0x800FE54C`). `RES#3927` is a byte-identical copy of that block that no path was seen loading; the build keeps both in step. **The bank cannot grow past `0x12640`**: PSX.EXE's boot data follows it.

The bank is `M4[fonts, system M4, more]`, all reached through the M4 table.

## Text insertion (`tools/insert.py`)

- **Scene**: the M2 is rebuilt, its M4 table follows, and everything after it shifts by a 4-byte-aligned delta. Header `size_total`, part-table `size` and `off[]` follow. The slot size stays: a scene that no longer fits raises `Overflow`. `tests/test_insert.py` holds this.
- **Shift is safe**: nothing addresses a later part absolutely (`tools/ov_refs.py`; every scene loads in the marker tour).
- **M2 offsets are u16**, so a bank stops at 64 KB. The biggest is 54 KB in Japanese. An `M4` holds strings just as well to the lookup at `0x80050974` (u32 offsets), so the way out for an overlong bank is an M4 of strings, unproven until phase 7 needs it.
- **MAIN.EXE loose strings**: 172 word pointers in a 0x3C-stride table (`0x901FC..0x91620`, name at +0, help at +0x38) reach all of them, nothing else does (`extract.main_pointers`). English can be relocated by rewriting those words; the marker build cuts to the slot instead.

## Budgets for phase 7

| Item | Budget | Now |
|---|---|---|
| Scene slot | `0xA0000` map, `0x40000` sub | marker at full pangram width (a stand-in for English size) overflows 13 scenes, listed by `build.py --marker` |
| Scene M2 | 64 KB | see above |
| System bank | `0x12640` total | system M4 is `0x77C4`; marker at full width needs `0x149F0` |

**Room to reclaim:** when no Japanese is left, the base kanji font (896 cells, 14 KB, in the bank) and each scene's glyph part (2-4 KB) are free. The name-plate frames `{87ac}`/`{87ad}`/`{e080}`/`{e081}` are the only cells English still uses; move them to a low cell or use `[ ]` from the VWF font.

## Open (phase 7)

- The three fixed-cell name-label drawers: 8 px per letter with a 48 px field per name slot. Names longer than 6 letters run into the next slot's VRAM; compose them proportionally or give them a wider stride.
- Text speed: one frame wait per glyph means English (2x the glyphs) takes 2x as long in timed scenes. Wait values are at `0x8004ED14/18`, `0x8004F17C/80`, `0x8004F504/08`.
- Name entry: the grid is kana (`RES#1023`). Needs an English grid; hero name default is `PSX.EXE:1b514`.
