# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 7. Insert, fit, check in progress. Phases 0-6 done (gaps below).
- **Phase 7 so far (2026-11-05):** `tools/build.py` is green and the build boots, reads English in warped scenes and menus, passes smoke. Base font compacted to the 9 cells English draws (`insert.KEPT`), MAIN.EXE loose strings pooled and repointed, banks past 64 KB become M4s of strings (`m_head` in `asm/vwf.asm`), RES#361 keeps 2 strings in a far pool at the end of the system block. Text speed 2/3 frames per glyph. Name labels proportional, 48 px per name. Name entry is ASCII, defaults Weld/Filia (`tools/overlays.py`). Scripts: 38,806 strings translated, 89 recoded (plates on `!!` lines, dev menus, Weld).
- **Graphics (2026-11-05):** `tools/stills.py` (BS pages, `gfx/stills/s01-s16.json`), `tools/sprites.py` (mission cards, endings, map labels, `gfx/sprites/`), `tools/strfmv.py` (PROLO.STR, `gfx/fmv/PROLO.json`, our own BS re-encode, so no jPSXdec), `tools/titlelogo.py` (katakana off the logo, D5). `tools/disc_diff.py` replaces a whole-image romdiff: 0 problems. Translators work from `docs/stills-brief.md`, `docs/sprites-brief.md`.
- **Next:** collect the last still and sprite batches, rebuild, zoomed in-game shots of every graphics row, story pass (`work/qa/story/`, 13 sections in scene-id order), `docs/polish.md`, visual QA tour (`qa_gate.py`), playtest, `tools/release.py`.
- **Done:** Step 0, phases 1-4 (`docs/re/`, `tools/debug/` warps, byte-identical `tools/build.py`, `tools/extract.py`: 61,774 strings from 279 sources, exact roundtrip). **Phase 5: VWF chosen and proven in-game (`asm/vwf.asm`, `fonts/vwf.txt`, `docs/re/vwf.md`). Insertion works (`tools/insert.py`, `tests/test_insert.py`). The marker disc (`build.py --marker`) boots, passes smoke and was shot in all 308 scene-list entries, 306 + `menu_tabs`, `menu_party` added with corrected menu routes (`work/qa/marker`). Width gate done, budgets per box in `docs/re/windows.md` (`tools/width_gate.py`, `--menu`). All glyphs now readable: 394 unsure cells read by eye into `tbl/glyphs_manual.tsv`; each string has a `read` field; only `{9f82}` (button icon) stays a token.**
- **Key facts:** text is a custom mode-shifted 1/2-byte code in `M4`/`M2` banks. Translators work from `read`; `jp` keeps exact tokens for the roundtrip. Plates are `{0b:08}【 Name 】{0b:09}\n` and take one of the 4 rows. Keep every string's control codes, especially the closing `{0c:..}`: it runs the scene on. Budgets in px: dialogue 216 (last row 208), name 180, choices 260, help bar 276. Map jump is `MAIN.EXE` 0x80029838 through the request block at 0x80097B28. Debug menu: set `0x1C2(gp)`=1 (`tools/lua/debug_on.lua`), then R2+Cross; TUSSY > ITEM drops an item.
- **Gaps:**
  - Status label `守` is "Def": the value column at a fixed x left 20 px; moving it was not tried (D4 flag), the game's HUD graphic already says `Atk`/`Arm`.
  - Name labels were seen only with a 6-letter hero; 7-letter party names (Eleanor, Orpheus, Jessica) go through the same code, check in phase 8.
  - Marker tour saw each scene's first text only, one shot each, not every box. Not checked: later events, battles, shops. Phase 8 covers those.
  - Item list window not measured with real items: debug-dropped item was not picked up. Same names were tested in the debug item row. Re-check in phase 8.
  - Shots were reviewed by me at contact-sheet size, mission cards and forced sub-scenes spot-zoomed. No independent review.
  - Row 17 of `docs/re/graphics.md` (white caption on forced sub-scenes): source not found.
  - m223 and 9 sub-scenes draw nothing; forced sub-scenes often show garbled parent cards. Game over and credits are not warp-reachable (phase 8).
  - Step 0: PCSX-Redux GUI with a keyboard unchecked; dump hash not compared with Redump.
- **Later, known big work:** BS v2 encoder for the stills and all graphics rows (phase 7).
- **Open bugs:** none reported; no English text is in yet.
- **Waiting on the user:** nothing yet.
