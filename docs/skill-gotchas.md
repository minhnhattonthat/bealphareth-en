# Skill gotchas

- references/emulator-qa.md: PCSX-Redux: poking new code into RAM after loading an old build's savestate (Lua `getMemPtr` writes, then `PCSX.invalidateCache()`, with or without `--debugger`) does not take for code the game already ran: breakpoints at the new addresses fire with registers of the old code. Code changes need a cold boot (warp, then save a fresh state).
- references/emulator-qa.md: PCSX-Redux's default dynarec ignores MIPS load delay slots, DuckStation and hardware don't: hand-written asm with `lw ra` then `jr ra` ran fine in Redux and froze in DuckStation. Run new asm once with `--debugger` (interpreter honours the delay) and lint load-then-use.
- references/graphics.md: PS1 BS stills of 320x480 are shown 640 wide; text typeset square in image pixels comes out 2x wide on screen. Lay it out on a 2x-wide canvas and squeeze it back, and review stills stretched to display aspect.
