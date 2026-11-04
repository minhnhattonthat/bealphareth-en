# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 6. Translate, next. Phases 0-5 done (gaps below).
- **Done:** Step 0, phases 1-4 (`docs/re/`, `tools/debug/` warps, byte-identical `tools/build.py`, `tools/extract.py`: 61,774 strings from 279 sources, exact roundtrip). **Phase 5: VWF chosen and proven in-game (`asm/vwf.asm`, `fonts/vwf.txt`, `docs/re/vwf.md`). Insertion works (`tools/insert.py`, `tests/test_insert.py`). The marker disc (`build.py --marker`) boots, passes smoke and was shot in all 308 scene-list entries, 306 + `menu_tabs`, `menu_party` added with corrected menu routes (`work/qa/marker`). Width gate done, budgets per box in `docs/re/windows.md` (`tools/width_gate.py`, `--menu`). All glyphs now readable: 394 unsure cells read by eye into `tbl/glyphs_manual.tsv`; each string has a `read` field; only `{9f82}` (button icon) stays a token.**
- **Key facts:** text is a custom mode-shifted 1/2-byte code in `M4`/`M2` banks. Translators work from `read`; `jp` keeps exact tokens for the roundtrip. Plates are `{0b:08}【 Name 】{0b:09}\n` and take one of the 4 rows. Keep every string's control codes, especially the closing `{0c:..}`: it runs the scene on. Budgets in px: dialogue 216 (last row 208), name 180, choices 260, help bar 276. Map jump is `MAIN.EXE` 0x80029838 through the request block at 0x80097B28. Debug menu: set `0x1C2(gp)`=1 (`tools/lua/debug_on.lua`), then R2+Cross; TUSSY > ITEM drops an item.
- **Next (phase 6):** build the batch tooling and glossary, dispatch translators from `read`, per `references/translation.md`. Give them `docs/re/windows.md`. The lint must measure with `vwf_font.text_width`.
- **Phase 7 must do (found in the gate):**
  - System bank is full: `0x12640`, no spare bytes, marker at full width needs `0x149F0`. Reclaim the base kanji font (14 KB), scene glyph parts and dev-only strings (`PSX.EXE:20c0d` and neighbours). Keep cells `87ac`/`87ad` (`【】`).
  - 13 scenes overflow their slot at full marker width (RES#104, 1173, 1194-1196, 1198, 178, 188, 230, 231, 361, 4106, 4107): same reclaim.
  - Fixed-cell name labels, 6 letters (HUD, status): `docs/re/windows.md`.
  - Status grid value column: labels 28 px.
  - Name entry grid is kana; text speed doubles with English glyph count (`docs/re/vwf.md`, Open).
- **Gaps:**
  - Marker tour saw each scene's first text only, one shot each, not every box. Not checked: later events, battles, shops. Phase 8 covers those.
  - Item list window not measured with real items: debug-dropped item was not picked up. Same names were tested in the debug item row. Re-check in phase 8.
  - Shots were reviewed by me at contact-sheet size, mission cards and forced sub-scenes spot-zoomed. No independent review.
  - Row 17 of `docs/re/graphics.md` (white caption on forced sub-scenes): source not found.
  - m223 and 9 sub-scenes draw nothing; forced sub-scenes often show garbled parent cards. Game over and credits are not warp-reachable (phase 8).
  - Step 0: PCSX-Redux GUI with a keyboard unchecked; dump hash not compared with Redump.
- **Later, known big work:** BS v2 encoder for the stills and all graphics rows (phase 7).
- **Open bugs:** none reported; no English text is in yet.
- **Waiting on the user:** not blocking: re-inserting the prologue FMV (`PROLO.STR`) subtitles normally uses jPSXdec, which the safety layer blocked; phase 7 needs either approval for it or our own STR tooling.
