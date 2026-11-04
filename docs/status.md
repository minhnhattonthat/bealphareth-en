# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 1 done, with gaps listed below. Next: 2 (debug tool). No build yet.
- **Done:** Step 0 (dump pinned, PCSX-Redux + BIOS + mkpsxiso + armips in `tools/`, check gate rejects failing tests, guard hook blocks the canary, smoke boots the original to the title, Start and a Lua probe both work). Phase 1: `docs/re/disc.md`, `text.md`, `graphics.md`, `stills.tsv`.
- **Key facts:** text is a custom mixed 1/2-byte code in `M4`/`M2` banks, about 60k strings and 2.8 MB. Font 11x11 in `PSX.EXE`; E0xx kanji are per scene. Scene overlays load at 0x800D6C00, max 0xCC46C bytes before `PSX.EXE` data. About 530 full-screen BS stills and ~60+ sprite sheets hold baked Japanese.
- **Next (phase 2):** `tools/debug/` warp: reach every scene from cold boot. Look for scene-load code (the loader near 0x8006A2A0 and the debug strings `ITEM SET`, `TIME SET`, `KURI DEBUG` in `MAIN.EXE` file 0xDC4). Careful: savestates taken just after a scene load stalled (`work/play/a`, step 5 on); take states on a quiet, loaded screen.
- **Later, known big work:** BS v2 encoder for the stills (phase 7); English engine: half-width 6 px path exists at 0x8004F244, VWF decision in phase 5; size budget per scene (`tools/slack.py`; #361, #107, #101, #76, #1951 are tightest).
- **Phase 1 gaps (see `docs/re/graphics.md`, "Not covered yet"):** 39 overlays with no part table unswept; map tile classes unread; mid-game screens untoured until phase 2 and 5; raw strings in `MAIN.EXE` need an extraction sweep in phase 4.
- **Step 0 not checked:** the PCSX-Redux GUI with a keyboard (headless only here). Dump hash not compared with Redump.
- **Open bugs:** none (no build).
- **Waiting on the user:** the safety layer blocked running a downloaded jPSXdec jar; `tools/bs.py` replaced it for the survey. Not blocking: re-inserting the prologue FMV (`PROLO.STR`) subtitles normally uses jPSXdec, so phase 7 needs either the user's approval for it or our own STR tooling.
