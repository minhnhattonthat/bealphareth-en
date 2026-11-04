# Sprite sheets brief - Bealphareth

Mission title cards, ending captions and the world map's labels are sprite sheets: 4-bit pictures that the game cuts into rectangles and shows piece by piece. You read the Japanese from the sheet, translate it, and say where it was. `tools/sprites.py` clears it and draws your English. No subagents, no git, no tool edits.

Read first: `docs/translator-brief.md` (voice, D11 softening, name rules; ignore its batch steps), `glossary.md` (binding spellings). Short system strings: `work/qa/names.tsv`. For scene context grep `script/res<ENTRY>.json`, the scene the sheet belongs to.

## The one rule that matters

**English stays inside the box of the Japanese it replaces.** The game cuts each piece of text as its own rectangle; anything outside is not shown, and a piece of Japanese left outside your box still shows. Two pieces on one row with a wide gap are two rectangles, shown at different moments: translate them separately.

## Steps

Dispatch: a file name such as `e03` and its sheet ids.

1. `python -X utf8 tools/sprites.py grid work/qa/sp/e03_1.png ID ID --zoom 3 --cols 2`, two to four sheets a picture, and Read it. It also prints each sheet's ink boxes `[x0,y0,x1,y1]`, drawn in cyan. Yellow grid every 16 px. A picture or the cursive `Fin` can swallow neighbouring text into one big box: split it by eye.
2. Write `gfx/sprites/e03.json`, a list with one object per sheet:
   `{"sheet": "235+1f854.0", "blocks": [{"box": [4, 4, 185, 19], "text": "Big brother! Hanna! Yeah!", "align": "center", "size": 12}]}`
   - Box: the printed ink box, untrimmed. Every pixel in it is cleared, then the English is drawn, shrinking from `size` down to 8 until it fits.
   - `"align": "center"` everywhere: the game centres these on screen.
   - Sizes: ending captions `size` 12. Mission titles `"size": 20, "bold": true`, objectives and the `Objective` label `"size": 14, "bold": true`.
   - `"erase": [[x0, y0, x1, y1]]` clears Japanese with no English in its place.
   - Keep what isn't Japanese: Latin subtitles like `"First Step Of Adventurer"`, the cursive `Fin`, the sun or glow sprites, pictures, white bars at the sheet's edge. No block for those, and no box over them.
3. `python -X utf8 tools/sprites.py check gfx/sprites/e03.json` until it reports 0 problems. `does not fit`: tighten the English; never drop meaning. `packed bytes`: the sheet must compress to its old size: shorter text or a smaller size.
4. `python -X utf8 tools/sprites.py preview work/qa/sp/e03_p.png gfx/sprites/e03.json ID ID --zoom 2` and Read it, before and after. No Japanese left, text legible, art intact. Fix and repeat.

## Translating

- Mission cards: the kanji title becomes a short title; `クリア条件` is always `Objective`; objectives are terse imperatives (`Destroy the Nest, Defeat All Enemies`). Keep the same wording for a title or objective that recurs. `gfx/sprites/m05.json` is the worked example.
- Endings are the last words a player reads. Short lines, natural speech, each speaker's voice from the glossary and the scene's script. Date and place captions: plain (`One year and four months after the blast of light`; place names per glossary).
- Lines that split a sentence across rows or pieces must still read in order, one piece at a time.
- Hard to read kana: zoom (`--zoom 4`). If a sheet can't be read, list it in your report; never guess a whole line.
- Same Japanese, same English, in every sheet.
- Names not in the glossary: propose one under `New terms`, use it consistently.

## Report (your final message, under 150 words)

File written; sheets done; `check` result; pieces you could not read; `New terms` as `JP - EN`, one line each; what you did not check.
