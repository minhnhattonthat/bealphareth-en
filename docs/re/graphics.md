# Graphics: formats and survey of Japanese drawn as graphics

**Scope is large.** Dialogue, menus and name entry are font text (`text.md`), but about 530 full-screen pages and about 60 scene title/ending sheets carry baked Japanese. This is the biggest cost after the script.

## Formats (verified by rendering; tools named)

- **Sprite sheet** (`tools/gfx.py`): u32 palette bytes + 8, u32 palette count, 16-colour palettes, then records `u16 flags, w, h, 0`. Flag 0x8000: `u32 packed, u32 raw`, then RLE (n<0x80: repeat next byte n times; n>=0x80: copy 256-n literals). Otherwise raw 4bpp. Stand-alone entries, and inside scene overlays.
- **Scene parts** (`tools/gfx_part.py`, `sweep_overlays.py`): in section 2, name string, u32 n, u32 off[n]; each part starts at `count_word_offset + 8 + off`, checked on #1023 (M4 text, sprite sheets at exact offsets).
- **MDEC BS v2 still** (`tools/bs.py`): `u16 codes, 0x3800, u16 qscale, u16 2`, 320x480, 600 macroblocks. Decoder is luma only and survey-grade; **no encoder yet**. Re-inserting a page needs a BS v2 encoder that fits the entry (slots are 0x800-aligned; read buffer limit not yet measured).
- **8bpp full screen** (`u16 1, u16 ncolors`, palette, pixels; `tools/gfx8.py`): #2250-2252, #3922-3926, #4108-4124. Width not pinned down (not 320).
- **Bitmap with header** (head 0x00100000, `tools/gfx_zoom.py`): palette, then w,h at +0x30, pixels at +0x34. #3942 onward.

## Survey

Sources: boot-to-first-mission tour (`work/qa/t2`, cold boot, frames to 23,500) and static sweep. Classification of stills and sheets by a read-only `codex exec` pass (`docs/re/stills.tsv`), with my own spot checks on #3150, #3190, #3970, #5+221d0, #235+1f854 agreeing.

| # | Element | Where | Format | Japanese | Plan |
|---|---|---|---|---|---|
| 1 | Item and equipment cards (title plate, picture, description, stats) | ~336 stills in #2617-#2954 | BS | Yes | Re-typeset + BS encoder |
| 2 | Document and letter pages ("PAGE n/m") | 53 stills, #4000-#4052 | BS | Yes | Re-typeset + BS encoder |
| 3 | Monster plates with Japanese text | 24 stills within #3117-#3214 (see tsv) | BS | Yes | Re-typeset + BS encoder |
| 4 | "NOW PRINTING" placeholder pages with monster name | ~47 stills within #3117-#3214 | BS | Yes (name, some description) | Re-typeset |
| 5 | Help and controller pages | ~10 stills, #3968-#3977 | BS | Yes | Re-typeset |
| 6 | Monster plates in Latin script (27 stills, e.g. #3150 "Anchor Rod") | #3117-#3164 | BS | Reported none; descriptions may be Japanese at full size | Check at full size in phase 7 |
| 7 | Mission title cards: stylised kanji title + official English subtitle + クリア条件 objectives | Scene parts in #5-#45 (34 sheets, e.g. #5+221d0) | Sprite sheet | Yes | Redraw |
| 8 | Ending text + "Fin" + date/place captions | Scene parts in #235-#260 (~45 sheets, e.g. #235+1f854) | Sprite sheet | Yes | Redraw |
| 9 | Short text and bottom captions | Scene parts, #236.. (26 sheets, codex notes "small text along bottom", "short text block") | Sprite sheet | Yes | Read at full size first |
| 10 | Handwritten lettering in map tiles | #22+4a650 | Sprite sheet | Reported, unconfirmed | Check |
| 11 | Prologue FMV subtitles (時は、後世の歴史家から...) | `STR/PROLO.STR` | Burned-in video | Yes | ffmpeg subtitles + re-encode, `platform-ps1.md` |
| 12 | Title logo: English "Bealphareth" with katakana ベアルファレス over it | #3924 (8bpp), on screen at title | 8bpp | Yes | Official English logotype exists, so remove the katakana (D5) |
| 13 | Stylised lettering among combat effects | #4355-#4501 (~23 sheets) | Sprite sheet | Reported English or unsure | Check in battle |

Already English, no work: `NEW GAME / LOAD GAME / PUSH START BUTTON` (#3946), `Game Over` (#3943), "The pulsing heartbeat dies out, faltering quietly." (#3942), HUD labels `Hp/max Lv Rest Atk Dex Exp Arm` (#3936), element labels (#3944), digits and days/time (#3954), Sony and Zealsoft logos. Character cards #2216-#2246: art only.

## Not covered yet

Say so rather than treat this as complete:

- **Mid-game screens** were not toured: only the first mission's start. Repeat after the debug tool (phase 2) and the marker build (phase 5), which reveals any Japanese that did not change.
- **39 scene overlays have no parsed part table** (`sweep_overlays.py` prints them, e.g. #10, #26, #160, #181, #196, #215-217, #222, #226, #227, #229): their sheets were not swept.
- **Map tile classes** (`00 00 xx xx`, about 300 entries, #2301-#2599, plus similar at #3327-#3396, #3729-#3793, #4700-#4803) render as noise at the guessed width: layout unknown, not read. Lettering there is unlikely, not excluded.
- **Unknown formats skipped:** 0x30 frame tables (no pixels), #1244-style 0x28 entries that fail the palette check (23), `DUMMY` #2955/#3215, #3673/#3674, #3795-3797, #3930-3938, #3947-3955.
- `codex` labels are one unverified pass at half size; spot checks agreed, but counts are approximate until phase 7 lists each entry.
- Whether these stills live in RAM buffers with a size cap, and whether a page may grow, is not measured.
