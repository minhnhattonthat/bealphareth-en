# Box budgets (the phase-5 width gate)

Pixels of VWF text (`tools/vwf_font.py`: `text_width`), not characters. Average English runs about 5 px per character. Text is `read`-based: `script/*.json`.

**Measured** = a ruler of exactly that width was seen whole in a zoomed cold-boot shot (`tools/width_gate.py`, shots in `work/qa/width/`). **Geometry** = read off a real shot of the screen with marker tags, not tested at the limit: re-measure if a line needs the last pixels.

| Variant | Budget | Rows | Tag | Notes |
|---|---|---|---|---|
| Dialogue, portrait (`{1c:10}`..) | 216 px | 4 | measured | text x 80; wrap at `W*6` = 216 holds, 222 wraps |
| Dialogue, last row of a page | 208 px | | measured | page arrow at x 295; a 216 px line touches it |
| Dialogue, no portrait (`{1c:63}`) | 216 px | 4 | measured | text x 48, the box has spare room to x 296, unused by the wrap limit; arrow clear of the text |
| Name plate `【 Name 】` | name 180 px | row 0 | measured | 12 + 4 + name + 4 + 12 = 216 at most. A plate takes a row: 3 text rows follow. Computed limit 184. |
| Choice list, plain (`a\|b\|c`) | 260 px | up to the 6 seen | measured | window is sized to the longest option and centred; title bar separate. Scene lists run to 12 entries: scroll check in phase 8 |
| Choice list with icons (class) | 216 px | | measured | icon column is 16 px |
| Help bar under a list | 276 px | 1 | measured | centred in a fixed 288 px box |
| Character creation answers | 190 px | | measured | re-printed on the confirm page after a right-aligned label: value starts x 100, box ends x 304. A 216 px answer ran off the box. One string, smallest budget. |
| Confirm page labels | 60 px | | geometry | label right-aligned at x 100 |
| Main menu | 48 px | 4 | measured | window sized to the longest entry, against the right edge |
| Menu tabs (`{0e} {0f}Use{0e} {0f}`) | 40 px | 5 | measured | fixed 48 px pitch: at 44 px neighbours touch |
| Item menu header help | 196 px | 1 | geometry | starts x 96 after the tab name, box ends x 304; a 276 px ruler ran off it |
| Item help bar (`片手剣/攻 1/-/`) | 276 px | 1 | measured | bottom bar, centred |
| Item row (name + count) | 124 px | | measured | name x 93, count x 212: 112 px clear, 130 px touches a 4-digit count |
| Equipped item in the status grid | 103 px | | geometry | value x 200, frame line x 304 (zoomed `menu_status`), advance includes the 1 px gap, so 103 px leaves 1 px clear. Takes the smallest budget: **equipment names 103 px**, other items 124 px. Moving the column was tried, not found: D15 |
| Status grid labels, equipment column (`武器`) | 28 px | | measured | value at fixed x 198: a 46 px ruler ran into it. Phase 7: move the value column before shortening anything (D4) |
| Status grid labels, stats (`HP`, `攻`) | 20 px | | measured | number at fixed column: 20 px just clears it |
| Party-member list | names 72 px | | geometry | the six-letter test name already runs off this window at the right edge |
| Item list window | not measured | | **open** | no way to fill the inventory yet: debug `ITEM` drops the item on the map and walking onto it did not add it. Tested the same names in the debug row above; re-check in phase 8 with a real inventory |

## Fixed-cell labels (not VWF yet, phase 7)

`0x8003A354`, `0x8003C80C`, `0x8003DE10` lay out names in 8 px cells, 48 px a slot: **6 letters** today (HUD panel, status). Phase 7 either draws them through the VWF or narrows them. D4 applies: no abbreviation before this is tried.

## Glyph torture line

All printable ASCII and double spaces render with the right widths. `"` draws as a closing quote and `\` as a yen sign (`fonts/vwf.txt`). Backtick is the game's own mark, not a quote: don't use it.

## System bank is full

The bank has no spare bytes: 18 rulers overflowed `0x12640` until a developer's room list (`PSX.EXE:20c0d`) was blanked. Phase 7 must reclaim the base kanji font, the dev-only strings and glyph cells before English goes in (`vwf.md`, Budgets).

## Encoder rules this gate found

Both are in `textcodec.encode(en=True)` and are not optional:

- The engine starts each `|` option in hiragana mode. Without a mode byte after `|`, English came out as kana.
- A space in a kana mode is 12 px. English spaces are always ASCII mode (4 px).
- Every string's closing `{0c:..}` must stay: it runs the scene on. A line that lost it stalled the opening.
