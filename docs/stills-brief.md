# Still pages brief - Bealphareth

Item cards, letters, monster plates and help pages are full-screen pictures (320x480) with Japanese baked into them. You read the Japanese from the picture, translate it, and say where it was. `tools/stills.py` erases it and typesets your English. No subagents, no git.

Read first: `docs/translator-brief.md` (voice, D11 softening, name rules), `glossary.md` (binding spellings). Item names and stat words must match the game's menus: `grep` them in `work/qa/names.tsv` (`Japanese<TAB>English`, every short system string). Use those exact English names for titles and for items named in text.

## Steps

Dispatch: a file name such as `s03` and its entries.

1. `python -X utf8 tools/stills.py grid work/qa/still/s03_1.png E1 E2 E3 E4 E5 E6 --cols 3`, six entries a sheet, and Read the PNG. Yellow lines every 40 px, labelled in pixels of the page.
2. Write `gfx/stills/s03.json`, a list with one object per page:
   `{"entry": 2700, "blocks": [{"box": [80, 56, 210, 88], "ink": "dark", "text": "Wood Chip", "align": "center", "bold": true, "size": 18}, {"box": [44, 205, 154, 290], "ink": "light", "text": "A chip of wood that would make good kindling."}]}`
   - `box` = [x0, y0, x1, y1] around the Japanese of that block. English starts at its top left and wraps to its width, so make it as wide as the free space allows. A box may be taller than the Japanese if the English needs it, but must not run over art you'd rather keep.
   - `ink`: `light` for white or coloured text on a dark ground; `dark` for dark text on parchment or a pale plate. Mixed pages take one block per ink.
   - Title plates: `"align": "center", "bold": true, "size": 18`. Body text: the default size 15; set a smaller `size` only for dense pages. A block shrinks by itself to fit, down to 10.
   - Keep stat lines as separate lines (`\n`) in the order of the original: `Attack 18\nFire attribute\nCold resistance -`. Use the menu's stat words.
   - `"erase": [{"box": [...], "ink": "light"}]` removes Japanese with no English in its place (a second copy, a stray label).
   - Dim or coloured Japanese that survives the erase: add `"dim": true` to that block or erase entry. It clears anything lighter than its surroundings, so keep such boxes off button pictures and art.
   - Latin text in the art (`PAGE 1/6`, `NEXT`, `END`, the monster's Latin scrawl, button pictures) stays: no block.
3. `python -X utf8 tools/stills.py check gfx/stills/s03.json` until it reports 0 problems. `does not fit`: widen the box or tighten the English; never drop meaning.
4. `python -X utf8 tools/stills.py preview work/qa/still/s03_p1.png gfx/stills/s03.json E1 E2 E3 E4 E5 E6 --cols 4` (six entries at a time) and Read it: pairs of before and after. Check that no Japanese is left, text sits on the page and reads clearly, and no art lost a chunk. Fix the boxes and repeat.

## Translating

- English for a player reading an in-game encyclopedia: plain and vivid, no padding. Letters keep the writer's voice.
- A page whose Japanese overlaps itself or the art (two layers of text printed on top of each other): make out what you can, erase all of it, and typeset one clean text. If it can't be read, describe the item from its title and the readable part, and list the entry in your report.
- `NOW PRINTING` placeholder pages: translate only the Japanese on them (usually the monster's name), leave `NOW PRINTING`.
- Same text on several pages: same English.
- Names not in the glossary: propose one under `New terms` in your report, and use it consistently.

## Report (your final message, under 150 words)

File written; entries done; `check` result; entries you could not read; `New terms` as `JP - EN`, one line each. Don't paste the translations.
