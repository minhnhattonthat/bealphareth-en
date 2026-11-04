# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| disc.md | disc files, MAIN.RES archive, scene overlays, free space | archive and overlay layout verified; free space partly guessed |
| text.md | encoding, control codes, M4/M2 banks, font, reader routines | verified on decoded lines; argument counts need the phase 4 roundtrip |
| graphics.md | formats and the survey of Japanese drawn as graphics | static sweep done; mid-game screens need the debug tool |
