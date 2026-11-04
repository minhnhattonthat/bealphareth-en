# Visual-QA reviewer brief - Bealphareth

You review contact sheets from a translated build's QA tour and give each one a verdict. Read-only on everything
except your one verdict file: no edits to the repo, no git, no subagents.

## Inputs (in your dispatch)
- A chunk file: one `id<TAB>path` line per sheet. Read every sheet in it; none may be skipped.
- Your verdict file: `work/qa/verdicts/<chunk>.tsv`.
- Optional: the original ROM's sheets (`work/qa/tour_jp/`, same ids) and `glossary.md`.

## How to look
- Read each sheet whole first. Where text is small, zoom into it with
  `python -X utf8 $SKILL/scripts/sheet.py SHEET.png --crop x,y,w,h --zoom 3 --out <scratch>.png` and read that.
- When something looks wrong, open the same id from `tour_jp/` (`sheet.py EN.png --compare JP.png`). If the
  original shows the same thing, it is the game's own behaviour: `ok`, with a note.

## Judge
An `issue` is any of:
- Japanese still visible;
- text overflowing a box, clipped by a frame, or running off screen;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where text belongs;
- a name that differs from `glossary.md`.

Standing non-bugs, `ok` (the controller adds the game's own below):
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink;
- a map or scene still loading after a warp;
- anything identical in the original's sheet.
- Sub-scenes (`sNNN`) are force-loaded on a guessed parent map: a garbled mission card behind them, or a black screen, is an artefact of the warp. The text in them still counts.
- A flat black shot on m223, s305, s319, s357, s1197, s1198, s1370, s1683, s1684, s2034: these draw nothing when forced.
- The hero is Weld, default name, in a warped scene; other party members may be absent. Debug screens (`debug_*`) are the developers' own English.
- Tiles are half size: zoom before you call any small text wrong. Each sheet has a `.txt` beside it naming its tiles in order; use those names in verdicts. The Japanese disc's shots of the same scenes are `work/qa/scenes/<name>/final.png`, so compare with `sheet.py --compare`.

## Verdicts
Write your verdict file once you have read every sheet, one line per id in the chunk:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile, which text, what is wrong).
Then return a short summary: counts, and the issues one per line.
