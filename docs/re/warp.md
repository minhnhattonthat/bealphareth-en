# Scene warp and the leftover debug menu (phase 2)

The debug tool reaches every scene from a **cold boot**, with no user save and no playthrough: one emulator run per
scene, booted from the disc, scripted through the new-game route, then a single write to the game's own map-jump
request block; `tools/debug/regen.py` verified it over the whole list in `tools/debug/scenes.lua`: 306 scenes (136 maps,
160 sub-scenes, 10 screens), every run exits 0, logs its map id (and `sub <id> loaded`), and its final shot is not a
flat colour (10 load-only scenes are flagged `blank`, see below). Result table: `work/qa/scenes/result.tsv`; grouped
shots: `work/qa/scenes/sheets/`.

## Entry points

| Path | Command |
|---|---|
| One scene, with shots | `python -X utf8 tools/debug/regen.py m171 s1621` (fnmatch patterns; `--state` also saves `work/states/<scene>.sstate`) |
| Whole list | `python -X utf8 tools/debug/regen.py --jobs 8` (name globs narrow it: `"m*"`, `"s1*"`, `menu_main`) |
| Contact sheets | `python -X utf8 tools/debug/sheets.py` (`work/qa/scenes/sheets/`) |
| One-off warp | `emu.py build.cue --route tools/routes/newgame.txt --script tools/debug/warp.lua --var MAP=183 [--var SUB=555] [--var "FLAGS={0x293}"]` |
| Leftover debug menu | open the game, then R2+Cross (needs `tools/lua/debug_on.lua`: `0x1C2(gp)` = 1) |

## The boot route

`tools/routes/newgame.txt` is title (Start) -> New Game -> Start skips the prologue FMV. At 8x speed: map 1023
(opening room) at **f4860**, map 1024 (name entry) at **f10248**, map 140 at **f24016**, and hand control on 140 at
**f26216** (mode flags at 0x80177CA8 == 0x01900000). `warp.lua` has two bases:

- `base = "opening"` (default, ~15 s): fire at f5260, after the opening room's first shot and **before its first text
  box** — a box left open blocks the next scene's event. Fast, but the hero is not placed, so no menu opens.
- `base = "field"` (~70 s): mash to hand control on map 140, then fire. Needed for menus and dungeon rooms.

## Map jump

`MAIN.EXE` 0x80029838 is the game's own "go to map" function (disassembly verified):

```
a0 = map id | something<<24   a1 = entrance/floor   a2 = fade (3 seen in game code)
request block at 0x80097B28: u16 +0xC map, u16 +0xE entrance, u16 +0x10 fade
then calls 0x8002850C / 0x8002853C(0x80097B28) / 0x80028548
```

The map loader polls through the pointer at `GP+0x7C8` (`GP` = 0x800A0E24, so 0x800A15EC). `warp.lua` writes the three
request fields, clears `GP+0x7B8`, stores the request address in `GP+0x7C8` and sets `GP+0x7AE` = 1. The loader picks
it up within ~120 frames. Writing the block directly is enough; the helper calls only queue/refresh the request.

Map ids are MAIN.RES scene overlays in the 0xA0000 slot. There are 140; **136 are real maps**. Four carry the same
0x02 header but are not rooms and are left out of the list:

| Id | Size | Why it is not a scene |
|---|---|---|
| 226 | 0xB4 | code stub, no part table |
| 229 | 0x2E90 | no valid part table; loading it jumps to the BIOS reset vector at f5548 (`pause_probe.lua`) |
| 1000 | 0x515C | part table inside the code; jumps to the BIOS reset vector at f5586 |
| 1002 | 0x592D4 | part table offset inside the header; CPU exception at 0x800D6DD0 (ra 0x80028994) |

`m223` is a real overlay but **code-only** (2 parts: code + one data blob, no room art); it loads and logs map 223 but
draws black with no HUD on every cold entry tried (fade 0 and 7, entrance 0, opening and field bases). It is kept in
the list as `S.m223.blank = true` so its black shot counts as proof of the load, not as a failure.

## Sub-scenes

Sub-scenes are the 0x40000-slot overlays (184; **160 real**, the other 24 are identical 0x9C-byte stubs). A sub overlay
loads at **0x80136C00** (verified: the file's bytes appear at 0x80136C10 in a RAM dump), above the map at 0x800D6C00,
so it runs on top of a parent map's room and objects. `tools/debug/ov_parents.py` guesses the parent from immediates
and u16 tables in each map's code; `scenes.lua` holds the hand-checked result (`S["s<id>"] = { map = parent, sub = id }`).
Direct `jal 0x800279A0` sites give the reliable links (160 -> 1334, 183 -> 350/555, 66 -> 571, ...); a tab hit alone is
a guess.

A cold boot never asks for most subs, so `force_sub` patches the loader instead of waiting for an event:

- `0x800279A0` (sub-scene load request): first stub forces `a0 = id` and jumps back into the original function.
- `0x80029EC8` and `0x8002A098` (the two map-init `jal` sites that wait for a sub load): second stub asks for `id`
  only when the map asked for none and the sub callback at `0x15A0(gp)` is 0, then continues to the original wait.
- Both stubs live in the 0x100-byte hole at **0x800D6B00** (between MAIN.EXE's BSS end 0x800D6AF8 and the overlay base
  0x800D6C00), so no game data is touched.

The log line `f<n> sub <id> loaded` (callback non-zero and the load id back to 0xFFFF) is what regen checks. Parent
choice is only a guess for subs with no immediate in the parent's code; the shot shows the sub's own content.

Nine subs (305, 319, 357, 1197, 1198, 1370, 1683, 1684, 2034) load but draw nothing on their guessed parent: their
final shot is flat and the parent's own screen is unchanged. They are event/script overlays whose content only appears
inside their event, so they are marked `blank` in `scenes.lua` (load proved by the log, visual check deferred to the
phase-5 marker tour). Changing their parent to 42/44/219 only shows that parent's own mission card, so a wrong parent
is not the cause.

**Known limit:** a forced load skips the event state the sub normally runs under, so some subs draw the parent's
mission card with garbled text (e.g. s300 on 183) instead of the screen the event would show. The load is proven; the
visible content has to be checked when the event runs (phase 5/8). The subs whose loader call site names them
(160 -> 1334, 183 -> 350/555, 66 -> 571) do show a proper room or card.

## Story flags and other state

- Story flags are a bit array at **0x80177864** (`0x8002C4F0` sets one): `warp.lua`'s `FLAGS`/`UNFLAGS` take flag ids
  and set/clear the bit before the warp. Used for scene variants; not yet tied to a visible test.
- Hero HP is at **+0x6A** of the leader object (`0x800A1814` points at it). Writing 0 there does not run the death
  check (tested: 40k frames on the opening map, nothing happens), so game over and the credits are not warp-reachable
  this way; they wait for a battle wipe / ending run in phase 8 (the field base exists for the menus that do need it).
- Hand control = mode flags 0x80177CA8 == 0x01900000; this is how `base = "field"` knows to fire.

## Leftover debug menu (Aug 24 2000)

Setting `0x1C2(gp)` (0x800A0FE6) to 1 and pressing **R2+Cross** in the field opens the developers' menu: `Debug`,
`JumpNo`, `JumpName`, `Kuma`, `Y.0`, `TUSSY`, `KURI DEBUG`. `JumpNo` is the same map-id jump in 4 digits; `JumpName`
has `Move / Town & House / Dungeon / Developer's room` lists; `Kuma` opens `RETRY / DB / DB2 / SAVE / LOAD`. The menu's
screens are English and were never in the retail text (nothing to translate). `debug_save` / `debug_load` in
`scenes.lua` reach the save and load screens this way; `debug_menu` stops at the main page.

## Gotchas

- **Never warp to the map that is already loaded**: it restarts the map mid-scene and the screen stays blank. `warp.lua`
  now recognises "already at MAP" and skips the write (this was the opening map's blank shot).
- A savestate taken just after a scene load stalled (`work/play/a`, step 5 on): take states on a quiet, loaded screen.
- The opening's first text box, if left open, blocks the next scene's event; `base = "opening"` fires before it.
- A scene whose map content is text-free still needs its parent's room; a sub-scene shot with no room behind it means
  the parent guess is wrong, not that the sub is broken.
